# backend/app/orchestrator/__init__.py — API PÚBLICA del Orquestador (R2)
#
# [doc 16] Disciplina modular: este __init__ ES la API pública del paquete. El
# resto de la app importa SOLO desde `app.orchestrator` — nunca de contracts/
# decomposer/conductor/consolidator/store/models.
#
# DEPENDENCIA EN UN SOLO SENTIDO: el orquestador usa la API pública del TIE
# (`app.tie`), y `app.tie` NUNCA importa `app.orchestrator`. Un ciclo aquí
# rompería el arranque. Lo vigila `tests/test_module_boundaries.py`.
#
# LA REGLA DE NO-REGRESIÓN (doc 23 §0): el ~80% de los mensajes tiene UN solo
# objetivo. Para ellos `handle()` delega en `tie.handle` tal cual — mismo camino
# corto, mismo streaming, CERO llamadas extra al LLM. La capa nueva solo se
# activa cuando el clasificador ya ha visto que hay varios encargos, y esa
# detección viaja gratis en la llamada que el TIE ya hacía.
from __future__ import annotations

import asyncio
from typing import Optional

from app.core.logging_config import get_system_logger
from app.core.strings import t as _t
# Importar el modelo aquí (y no solo de forma diferida dentro de `store`) es lo
# que registra `orchestration_runs` en `Base.metadata` a tiempo para el
# `create_all` del arranque y de los tests. Mismo patrón que el resto de módulos.
from app.orchestrator import models as _models  # noqa: F401
from app.orchestrator import consolidator as _consolidator
from app.orchestrator import conductor as _conductor
from app.orchestrator import decomposer as _decomposer
from app.orchestrator import store as _store
from app.orchestrator.contracts import Objective, OrchestrationRun

logger = get_system_logger("orchestrator")

# [A·VOZ-4] Orquestaciones multi-objetivo lanzadas en segundo plano (modo
# conversación). Retener la referencia evita que el GC cancele la tarea.
_BG_RUNS: set = set()


async def handle(envelope) -> str:
    """Punto de entrada del Gateway (misma firma que `tie.handle`: un envelope,
    un string de respuesta). Decide entre delegar en el TIE o orquestar.

    Nunca lanza: ante cualquier fallo de esta capa, delega en el TIE — el usuario
    siempre recibe una respuesta."""
    text = (getattr(envelope, "text", "") or "").strip()
    if not text:
        return await _tie_handle(envelope)

    try:
        import app.tie as tie

        intent = await tie.classify(text, channel=getattr(envelope, "channel", None))
        # 0 o 1 objetivo → el camino de siempre. `Intent.objectives` ya viene
        # normalizado a [] cuando hay uno solo (ver `intents._objectives`).
        if len(intent.objectives) < 2:
            return await _tie_handle(envelope)

        return await _orchestrate(
            message=text,
            objectives_hint=intent.objectives,
            channel=getattr(envelope, "channel", None),
        )
    except Exception as e:
        logger.error(f"[orchestrator] fallo en la capa, delego en el TIE: {type(e).__name__}: {e}")
        return await _tie_handle(envelope)


async def _tie_handle(envelope) -> str:
    import app.tie as tie
    return await tie.handle(envelope)


async def handle_stream(text: str, *, channel: str = "web", session_id: Optional[str] = None,
                        conversational: bool = False):
    """Entrada STREAMING del chat — la MISMA decisión que `handle()`, pero
    emitiendo eventos `(kind, payload)` como `tie.handle_stream`.

    `conversational` [A·VOZ-4]: modo conversación (voz). Un solo encargo → se
    delega en `tie.handle_stream(conversational=…)`, que acusa recibo y ejecuta en
    segundo plano. Varios encargos → se acusa recibo YA y la orquestación entera
    corre detrás, avisando al terminar (misiones de fondo, sin bloquear el
    diálogo). En modo texto (default), comportamiento clásico e inline.

    [Fix 2026-07-19] EL HUECO QUE CIERRA: `/api/chat/stream` llamaba directamente
    a `tie.handle_stream`, así que el chat —la interfaz principal— NUNCA pasaba
    por el Orquestador. Todo R2 (descomposición en varios encargos y misiones en
    paralelo) solo se activaba desde el Gateway/Telegram. Resultado real
    reportado por el usuario: "envía un email ... también abre YouTube y pon una
    canción" acababa en UNA misión con un plan de 2 pasos secuenciales, en vez de
    dos misiones independientes a la vez.

    NO-REGRESIÓN (doc 23 §0): con 0 o 1 objetivo se delega en `tie.handle_stream`
    tal cual, y se le PASA el intent ya calculado para no pagar una segunda
    llamada al clasificador. El ~80% de los mensajes no nota ninguna diferencia,
    ni en comportamiento ni en coste.
    """
    import app.tie as tie

    text = (text or "").strip()
    if not text:
        async for ev in tie.handle_stream(text, channel=channel, session_id=session_id,
                                          conversational=conversational):
            yield ev
        return

    # [A·VOZ-6] CHARLA OBVIA = 0 fricción. El pre-clasificador determinista (0 LLM)
    # resuelve saludos/cortesía sin tocar el modelo; en ese caso NO se emite
    # "analizando" (una charla no es una misión y no debe parecerlo) y se delega
    # DIRECTAMENTE en el TIE con el intent ya resuelto — cero llamadas al LLM
    # clasificador, cero status intermedio, el camino corto arranca a responder ya.
    pre = tie.fast_precheck(text)
    if pre is not None:
        async for ev in tie.handle_stream(text, channel=channel, intent=pre,
                                          session_id=session_id, conversational=conversational):
            yield ev
        return

    # [2026-07-24] Pregunta de LISTADO sobre los datos propios ("¿qué proyectos
    # tengo?"): respuesta DETERMINISTA de la BD, 0 LLM, 0 alucinación. Es el
    # arreglo definitivo del fallo real reportado (el modelo decía "no tengo
    # acceso a tus proyectos" o se los inventaba).
    import asyncio as _asyncio
    quick = await _asyncio.to_thread(tie.quick_answer, text)
    if quick:
        yield ("text", quick)
        return

    # No es charla obvia: hay que clasificar con el modelo. AHÍ sí tiene sentido
    # "analizando" (cubre la latencia del clasificador).
    yield ("status", _t("status.analyzing"))

    try:
        intent = await tie.classify(text, channel=channel)
    except Exception as e:
        logger.error(f"[orchestrator] clasificación falló, delego en el TIE: {type(e).__name__}: {e}")
        async for ev in tie.handle_stream(text, channel=channel, session_id=session_id,
                                          conversational=conversational):
            yield ev
        return

    if len(intent.objectives) < 2:
        # [R6.5b] Un solo encargo = una charla: lleva el hilo de la conversación.
        # Varios encargos (abajo) son misiones de fondo independientes; ahí el
        # historial del chat no pinta nada.
        async for ev in tie.handle_stream(text, channel=channel, intent=intent,
                                          session_id=session_id, conversational=conversational):
            yield ev
        return

    # --- Varios encargos: se hacen A LA VEZ ---
    # [A·VOZ-4] En modo conversación, la orquestación entera va a segundo plano:
    # acuse recibo YA y aviso al terminar (sin bloquear el diálogo por voz).
    if conversational:
        yield ("status", _t("orchestrator.status_multi", n=len(intent.objectives)))
        task = asyncio.create_task(
            _orchestrate_and_report(text, intent.objectives, channel, session_id))
        _BG_RUNS.add(task)
        task.add_done_callback(_BG_RUNS.discard)
        yield ("text", tie.conversation.acuse_text())   # vía barrel, no import de interno
        return

    try:
        async for ev in _orchestrate_stream(text, intent.objectives, channel):
            yield ev
    except Exception as e:
        logger.error(f"[orchestrator] la orquestación falló, delego en el TIE: {type(e).__name__}: {e}")
        async for ev in tie.handle_stream(text, channel=channel, intent=intent):
            yield ev


async def _orchestrate_stream(text: str, objectives_hint: list[str], channel: Optional[str]):
    """Descompone, lanza todo en paralelo y va contando el avance.

    El conductor corre en una tarea de fondo y aquí se sondea el estado
    persistido: así el usuario ve progreso real ("1 de 2 listos") en vez de
    quedarse minutos mirando un cursor parpadeando."""
    objetivos = await _decomposer.decompose(text, objectives_hint=objectives_hint)
    run = OrchestrationRun(
        id=OrchestrationRun.new_id(), user_message=text,
        objectives=objetivos, channel=channel, source="user",
    )
    n = len(objetivos)
    logger.info(f"[orchestrator] chat → run {run.id}: {n} objetivos en paralelo")

    yield ("status", _t("orchestrator.status_multi", n=n))

    tarea = asyncio.create_task(_conductor.run_objectives(run))

    # Progreso mientras corre. Se leen los ids de misión en cuanto existen para
    # que el usuario pueda abrirlas desde el chat sin esperar al final.
    anunciadas: set[str] = set()
    ultimo_hechos = -1
    while not tarea.done():
        await asyncio.sleep(1.0)
        actual = _store.load(run.id)
        if actual is None:
            continue
        for o in actual.objectives:
            # [2026-07-22, fix mismatch doc 31] El evento SSE "mission" debe
            # llevar el TRACE_ID, no el mission_id — es lo que ya usan
            # `/api/tie/missions/{id}` y `Missions.tsx` (el camino corto del
            # TIE ya lo hacía así; aquí faltaba alinear el Orquestador). Se
            # anuncia por `o.mission_id` (se conoce un instante antes) pero se
            # EMITE `o.trace_id`, con fallback defensivo si por lo que sea
            # faltara (nunca debería, `submit_mission` siempre lo estampa).
            if o.mission_id and o.mission_id not in anunciadas:
                anunciadas.add(o.mission_id)
                yield ("mission", o.trace_id or o.mission_id)
        hechos = sum(1 for o in actual.objectives if o.state in ("done", "failed", "skipped", "cancelled"))
        if hechos != ultimo_hechos and hechos < n:
            ultimo_hechos = hechos
            yield ("status", _t("orchestrator.status_progress", done=hechos, n=n))

    run = await tarea
    run.outcome = await _consolidator.consolidate(run)
    _store.save(run)
    yield ("text", run.outcome or _t("pipeline.no_response"))


async def _orchestrate_and_report(text: str, objectives_hint: list[str],
                                  channel: Optional[str], session_id: Optional[str]):
    """[A·VOZ-4] Orquestación multi-objetivo en segundo plano: ejecuta todo y, al
    terminar, empuja el resumen consolidado por el canal (mismo camino de entrega
    que las misiones de fondo del TIE). Best-effort: un fallo aquí no rompe nada,
    la orquestación ya quedó guardada."""
    import app.tie as tie

    try:
        outcome = await _orchestrate(message=text, objectives_hint=objectives_hint,
                                     channel=channel, source="user")
    except Exception as e:
        logger.error(f"[orchestrator] orquestación de fondo falló: {type(e).__name__}: {e}")
        outcome = _t("conversation.report_error")
    report = _t("conversation.report_done", outcome=(outcome or _t("pipeline.generic_done")))
    await tie.conversation.deliver_report(report, session_id=session_id, channel=channel)


async def _orchestrate(*, message: str, objectives_hint: list[str],
                       channel: Optional[str], source: str = "user") -> str:
    """Descompone → ejecuta en paralelo → consolida."""
    objetivos = await _decomposer.decompose(message, objectives_hint=objectives_hint)
    run = OrchestrationRun(
        id=OrchestrationRun.new_id(), user_message=message,
        objectives=objetivos, channel=channel, source=source,
    )
    logger.info(f"[orchestrator] run {run.id}: {len(objetivos)} objetivos")

    run = await _conductor.run_objectives(run)
    run.outcome = await _consolidator.consolidate(run)
    _store.save(run)
    return run.outcome


async def submit(message: str, *, channel: Optional[str] = None,
                 source: str = "automation") -> OrchestrationRun:
    """Entrada PROGRAMÁTICA (AE, WPMS, cron): orquesta un encargo aunque venga de
    un canal sin conversación. Devuelve el run completo, no solo el texto."""
    import app.tie as tie

    intent = await tie.classify(message, channel=channel)
    objetivos = (
        await _decomposer.decompose(message, objectives_hint=intent.objectives)
        if len(intent.objectives) >= 2
        else [Objective(id="o1", goal=message)]
    )
    run = OrchestrationRun(
        id=OrchestrationRun.new_id(), user_message=message,
        objectives=objetivos, channel=channel, source=source,
    )
    run = await _conductor.run_objectives(run)
    run.outcome = await _consolidator.consolidate(run)
    _store.save(run)
    return run


def recent_runs(limit: int = 30) -> list[dict]:
    """Runs recientes (los vivos primero) — lo consume la UI."""
    return _store.recent(limit)


def get_run(run_id: str) -> Optional[dict]:
    run = _store.load(run_id)
    return run.to_dict() if run else None


def cancel_run(run_id: str) -> bool:
    """Kill-switch del run: deja de lanzar objetivos nuevos. Las misiones ya en
    vuelo las corta el kill-switch del propio TIE."""
    return _store.mark_cancelled(run_id)


__all__ = [
    # contratos
    "Objective", "OrchestrationRun",
    # API pública
    "handle", "handle_stream", "submit", "recent_runs", "get_run", "cancel_run",
]
