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

from typing import Optional

from app.core.logging_config import get_system_logger
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


async def handle_stream(text: str, *, channel: str = "web"):
    """Entrada STREAMING del chat — la MISMA decisión que `handle()`, pero
    emitiendo eventos `(kind, payload)` como `tie.handle_stream`.

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
        async for ev in tie.handle_stream(text, channel=channel):
            yield ev
        return

    yield ("status", "analizando")

    try:
        intent = await tie.classify(text, channel=channel)
    except Exception as e:
        logger.error(f"[orchestrator] clasificación falló, delego en el TIE: {type(e).__name__}: {e}")
        async for ev in tie.handle_stream(text, channel=channel):
            yield ev
        return

    if len(intent.objectives) < 2:
        async for ev in tie.handle_stream(text, channel=channel, intent=intent):
            yield ev
        return

    # --- Varios encargos: se hacen A LA VEZ ---
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
    import asyncio

    objetivos = await _decomposer.decompose(text, objectives_hint=objectives_hint)
    run = OrchestrationRun(
        id=OrchestrationRun.new_id(), user_message=text,
        objectives=objetivos, channel=channel, source="user",
    )
    n = len(objetivos)
    logger.info(f"[orchestrator] chat → run {run.id}: {n} objetivos en paralelo")

    yield ("status", f"son {n} encargos: los hago a la vez")

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
            if o.mission_id and o.mission_id not in anunciadas:
                anunciadas.add(o.mission_id)
                yield ("mission", o.mission_id)
        hechos = sum(1 for o in actual.objectives if o.state in ("done", "failed", "skipped", "cancelled"))
        if hechos != ultimo_hechos and hechos < n:
            ultimo_hechos = hechos
            yield ("status", f"{hechos} de {n} terminados")

    run = await tarea
    run.outcome = await _consolidator.consolidate(run)
    _store.save(run)
    yield ("text", run.outcome or "(sin respuesta)")


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
