# app/tie/pipeline.py — el pipeline del TIE: handle() y submit_mission() (doc 14 §3.3)
#
# LA interfaz de orquestación. Desde T4 es el handler del Gateway
# (`gateway.set_handler(tie.handle)`) y la entrada del AE/WPMS (`submit_mission`).
#
# Flujo completo (doc 14 §3.3):
#   entrada → [clasificar ∥ pre-fetch de contexto]  (en PARALELO, doc 11 B.2)
#     ├─ camino corto (~80%): NullRuntime → respuesta      ← sin planner, sin grafo
#     └─ complejo: planner → TaskGraph validado
#                    ├─ ¿plan sensible? → gate del PLAN (HITL) → pausa
#                    └─ executor.run → responder → respuesta
#
# Firma de `handle` = `MessageHandler` del Gateway (envelope → str). Nunca lanza:
# cualquier fallo degrada a una respuesta útil (regla 11-B).
from __future__ import annotations

import asyncio
from typing import Optional

from app.core.config import settings
from app.core.logging_config import get_system_logger
from app.core.strings import t as _t
from app.tie import authority as authority_mod
from app.tie import (conversation, enricher, executor, intents, planner,
                     quick_answers, responder, tracer)
from app.tie.authority import Authority
from app.tie.contracts import Intent, Mission, NodeState, TaskGraph
from app.tie.missions import new_mission
from app.tie.runtime import AgentTask, get_runtime

logger = get_system_logger("tie.pipeline")

# action_type del gate del PLAN (distinto del gate de nodo, `tie_resume` — T3).
PLAN_ACTION_TYPE = "tie_plan"


# ---------------------------------------------------------------------------
# [S3, doc 34 §10] Presupuesto de llamadas, medido — registra el CAMINO
# ---------------------------------------------------------------------------
async def _heartbeat_until(task: "asyncio.Future", *, every_s: int):
    """[S4 · NEW-2] Emite ('status', "sigo trabajando") cada `every_s` mientras
    `task` siga en vuelo, y termina en cuanto acaba.

    EL PROBLEMA QUE CIERRA: el objetivo medible de S4 es que ningún turno de
    chat pase de un minuto sin respuesta NI evento. Los deadlines por capa
    acotan cuánto puede tardar cada llamada, pero un turno legítimamente largo
    (planner + varios pasos) seguía dejando la pantalla muda — que es
    exactamente lo que la campaña 00 leyó como "cuelgue" cuando no lo era.

    No consume el resultado: el caller hace `await task` después (así este
    helper no tiene que saber qué devuelve ni propagar sus excepciones).
    `every_s <= 0` lo desactiva (un único await, sin latidos)."""
    if every_s <= 0:
        await asyncio.wait({task})
        return
    while True:
        done, _ = await asyncio.wait({task}, timeout=every_s)
        if done:
            return
        yield ("status", _t("status.still_working"))


def _record_path(name: str, **detail) -> None:
    """Best-effort: qué camino tomó este turno (chat/direct/planned). El stage
    "path" es nuevo pero `mission_events` ya admite cualquier stage (cero
    migración). Nunca lanza — mismo criterio que el resto de la telemetría
    (doc 31): observar no puede romper el pipeline."""
    try:
        import app.telemetry as _telemetry

        _telemetry.record("path", name=name, detail=detail or None)
    except Exception:
        pass

# [A·VOZ-4] Tareas de fondo en vuelo. Retener la referencia es obligatorio:
# `asyncio.create_task` sin guardar el resultado deja la task a merced del GC,
# que puede recolectarla (y cancelar la misión) en silencio — el mismo footgun
# que `core/events._inflight`. `discard` la suelta cuando termina.
_BG_TASKS: set = set()


# ---------------------------------------------------------------------------
# Override explícito de modelo (E2b, doc 19 §7b / doc 14 §3.5)
# ---------------------------------------------------------------------------
async def _resolve_explicit_model(intent: Intent, *, project_id: Optional[int]) -> Optional[dict]:
    """Interpreta `intent.explicit_model` (el usuario nombró un modelo). Devuelve:
      - {"action": "reply", "text": …}  → responder ESO y NO ejecutar (nombre no
        resuelto, alcance por aclarar, o pin de proyecto ya aplicado).
      - {"action": "force", "model_key": …} → seguir el flujo normal forzando ese
        modelo para esta tarea.
      - None → el usuario no nombró ningún modelo; flujo normal.
    Nunca lanza (cualquier fallo → None, flujo normal)."""
    em = intent.explicit_model
    if not em or not em.get("name"):
        return None
    try:
        import app.mel as mel

        ref = mel.resolve_model_name(em["name"])
        if ref is None:
            # Nombre no resuelto → NUNCA inventar; decir qué SÍ hay (doc 19 §7b.2).
            disponibles = ", ".join(sorted({m["label"] for m in mel.list_models()})) or "ninguno configurado"
            return {"action": "reply", "text": _t(
                "pipeline.model_unknown", name=em["name"], available=disponibles,
            )}

        scope = em.get("scope", "unspecified")

        if scope == "project":
            if project_id:
                mel.set_project_override(project_id, ref.key)
                await _record_override_decision(project_id, ref.key)
                return {"action": "reply", "text": _t(
                    "pipeline.model_pinned_project", provider=ref.provider, model=ref.model,
                )}
            # Chat general sin proyecto asociado: no hay a qué fijarlo.
            return {"action": "reply", "text": _t(
                "pipeline.model_no_project_bind", provider=ref.provider,
            )}

        if scope == "unspecified":
            # [PU3, doc 35, 2026-07-30] Esta ambigüedad ("¿para esta petición o
            # para siempre?") NO es un permiso de seguridad — es una duda real
            # de interpretación, así que normalmente se pregunta (sin ejecutar
            # nada este turno, aclaración de camino corto, sin gate). Pero bajo
            # el perfil Autónomo el usuario pidió "nunca preguntes nada, sin
            # excepciones": aquí se aplica ese mismo principio por analogía,
            # asumiendo el alcance MÁS LIMITADO (solo esta tarea — el más fácil
            # de deshacer, a diferencia de fijarlo al proyecto entero) y
            # avisando de qué se asumió en la propia respuesta — nunca en
            # silencio, mismo principio que el resto de la autonomía (A3b).
            try:
                from app.automation import permission_service

                if permission_service.autonomy_is_full():
                    logger.info(
                        f"[tie] alcance de modelo sin especificar para {ref.provider}/"
                        f"{ref.model}; perfil Autónomo → asumo 'task' sin preguntar"
                    )
                    return {"action": "force", "model_key": ref.key, "note": _t(
                        "pipeline.model_scope_auto_task", provider=ref.provider, model=ref.model,
                    )}
            except Exception:
                pass  # fail-safe: si algo falla consultando el perfil, se sigue preguntando

            return {"action": "reply", "text": _t(
                "pipeline.model_scope_unspecified", provider=ref.provider, model=ref.model,
            )}

        # scope == "task": forzar ese modelo para esta tarea/turno.
        return {"action": "force", "model_key": ref.key}
    except Exception as e:
        logger.error(f"[tie] _resolve_explicit_model falló (sigo sin override): {type(e).__name__}: {e}")
        return None


async def _record_override_decision(project_id: int, model_key: str) -> None:
    """Deja rastro del pin de proyecto en la Decision API (mismo patrón que el
    planner con sus planes) — best-effort, nunca rompe."""
    try:
        from app.services import decision_service

        await decision_service.store_decision(
            title=f"Pin de modelo del proyecto {project_id}",
            body=f"Modelo fijado: {model_key} (override explícito del usuario)",
            reason="El usuario pidió usar este modelo para todo el proyecto.",
            project=str(project_id),
        )
    except Exception as e:
        logger.info(f"[tie] no se pudo registrar la decisión del pin (no crítico): {e!r}")


# ---------------------------------------------------------------------------
# Entradas públicas
# ---------------------------------------------------------------------------
async def handle(envelope) -> str:
    """Entrada channel-agnostic. Es el handler que el Gateway usa desde T4: el
    chat de Telegram (y cualquier canal futuro) pasa por aquí."""
    text = getattr(envelope, "text", "") or ""
    channel = getattr(envelope, "channel", None)
    try:
        return await _run_pipeline(text, source="user", channel=channel)
    except Exception as e:  # el Gateway ya hace fail-soft, pero el TIE no delega su honestidad
        logger.error(f"[tie] handle falló de forma inesperada: {type(e).__name__}: {e}")
        return _t("pipeline.internal_error_retry")


async def handle_stream(text: str, *, channel: str = "web", intent: Optional[Intent] = None,
                        session_id: Optional[str] = None, conversational: bool = False):
    """[T4b] Entrada STREAMING — la que usa `/api/chat/stream` (el chat de
    Electron). Emite tuplas `(kind, payload)`:
      ("status", "analizando"|"planificando"|…)  → feedback inmediato (≤1 s, doc 11 B.5)
      ("mission", trace_id)                       → hay una misión que se puede seguir/aprobar
      ("text", token|respuesta)                   → lo que el usuario lee

    El camino corto (~80%) streamea TOKENS de verdad (mismo UX de siempre); el
    complejo emite estados gruesos y la respuesta final del responder — el detalle
    paso a paso, en vivo, se ve en la vista de misión (que sondea el grafo).

    `session_id` [R6.5b]: la conversación del chat. Solo viaja por el camino
    corto (una charla tiene hilo); una misión compleja es trabajo de fondo y su
    contexto lo aporta el planner, no el historial del chat.

    `intent` (2026-07-19): el Orquestador YA clasificó para decidir si el mensaje
    traía varios encargos. Se le pasa aquí para no pagar una SEGUNDA llamada al
    clasificador en el ~80% de mensajes que son de un solo encargo — la regla de
    no-regresión de doc 23 §0 ("el camino corto no paga ni una llamada extra").

    `conversational` [A·VOZ-4, doc 32]: modo conversación (lo pone el chat de VOZ,
    o el usuario). En este modo, una misión (acción directa o compleja) NO bloquea
    el turno: se acusa recibo al instante ("me pongo a ello"), se ejecuta en
    segundo plano y se avisa por el canal cuando termina. La charla (camino corto)
    responde igual que siempre. En modo texto (default), comportamiento clásico:
    el plan se ve/aprueba en línea, nada cambia.
    """
    from app.automation import approval_gate
    from app.memory import memory_router
    from app.tools import tool_manager

    # [2026-07-24] RESPUESTA DETERMINISTA sobre los datos propios ("¿qué
    # proyectos tengo?", "muestra mis agentes/reglas/tareas"): SQL + plantilla,
    # 0 LLM, 0 alucinación, instantánea. Es EL arreglo definitivo del fallo
    # reportado (el LLM decía "no tengo acceso a tus proyectos" o los
    # inventaba). Solo cuando el mensaje es un listado claro (conservador).
    if intent is None:
        quick = await asyncio.to_thread(quick_answers.try_answer, text)
        if quick:
            _record_path("chat")
            yield ("text", quick)
            return
        # [PU4, doc 35] "Dame el briefing"/"¿qué tengo hoy?": mismo criterio
        # determinista, async porque la respuesta puede leer la locución
        # cacheada del MOS (nunca un LLM en caliente aquí).
        quick_briefing = await quick_answers.try_answer_async(text)
        if quick_briefing:
            _record_path("chat")
            yield ("text", quick_briefing)
            return
        # [PU10, doc 35] "Guarda esto en la memoria: X" / "busca en la memoria
        # X" / "olvida esto de la memoria X": mismo criterio, con ancla
        # obligatoria (no confundir con NEW-7b, que guarda un ARCHIVO).
        from app.memory import quick_memory

        quick_mem = await quick_memory.try_answer_async(text)
        if quick_mem:
            _record_path("chat")
            yield ("text", quick_mem)
            return

    # [A·VOZ-6] Clasificar SIN emitir "analizando" todavía: el ~80% de los
    # mensajes son camino corto (charla / query simple) y NO deben mostrar
    # "analizando" — eso hacía que un simple "¿cómo estás?" pareciera una misión
    # y tapaba el hecho de que ya se está respondiendo. El status solo tiene
    # sentido para las MISIONES (cubre la latencia del planner), y se emite abajo.
    # El clasificador ya tiene su propio fast-path (0 LLM) para la charla obvia.
    try:
        if intent is None:
            # [S4] Con latido: `classify` ya tiene su propio deadline
            # (TIE_CLASSIFY_DEADLINE_S), pero mientras corre la pantalla no
            # puede quedarse muda más de TIE_HEARTBEAT_S.
            _cls = asyncio.ensure_future(intents.classify(text, channel=channel))
            async for ev in _heartbeat_until(_cls, every_s=settings.TIE_HEARTBEAT_S):
                yield ev
            intent = await _cls
    except Exception as e:
        logger.error(f"[tie] handle_stream: clasificación falló: {type(e).__name__}: {e}")
        intent = Intent.conversational_fallback(text)

    # [E2b] ¿El usuario nombró un modelo? Aclaración/pin/forzado antes de nada.
    explicit = await _resolve_explicit_model(intent, project_id=None)
    if explicit and explicit["action"] == "reply":
        yield ("text", explicit["text"])   # sin ejecutar nada este turno
        return
    force_model = explicit["model_key"] if explicit else None
    # [PU3] Autónomo asumió el alcance sin preguntar (ver _resolve_explicit_
    # model) — se avisa como preámbulo del propio turno, nunca en silencio.
    if explicit and explicit.get("note"):
        yield ("text", explicit["note"] + "\n\n")

    # [A·VOZ-3/A·VOZ-6] Camino corto: SIN misión, SIN traza, SIN status y SIN
    # prefetch. Antes se pagaba `_prefetch_context` (una consulta al MOS con
    # presupuesto de 300 ms) ANTES de este check y luego se DESCARTABA — el
    # camino corto arma su propio contexto dentro de `NullRuntime.stream_task`
    # (build_system_prompt ya consulta el MOS). Era latencia muerta en el hot
    # path de cada charla. Ahora arranca a streamear tokens de inmediato.
    if intent.is_short_path:
        async for ev in _short_path_stream(text, intent, channel, memory_router,
                                           tool_manager, approval_gate, force_model,
                                           session_id, conversational=conversational):
            yield ev
        return

    # --- A partir de aquí es una MISIÓN de verdad ---
    # AHORA sí "analizando" (cubre la latencia del planner) y el prefetch de
    # contexto, que el camino complejo/de fondo sí consume.
    yield ("status", _t("status.analyzing"))
    prefetched = await _prefetch_context(text)

    mission = new_mission(goal=intent.goal or text, source="user", channel=channel)
    trace_id = tracer.record_start(mission, channel=channel)
    mission.trace_id = trace_id     # [fix mismatch, doc 31] mission.id != trace_id
    tracer.record_intent(trace_id, intent)
    tracer.emit_started(mission)

    # [A·VOZ-4, doc 32] Modo conversación: la misión NO bloquea el turno. Se acusa
    # recibo YA (para que la voz responda en < 2 s y el usuario pueda seguir
    # hablando), se lanza la ejecución real en segundo plano, y se avisa por el
    # canal cuando termine (o cuando necesite permiso). El reporte final lo entrega
    # el handler del bus de `conversation.py` al recibir `mission.completed/failed`.
    if conversational:
        conversation.register(mission.id, trace_id, session_id=session_id,
                              channel=channel, goal=mission.goal)
        task = asyncio.create_task(_run_background_mission(
            text, intent, mission, trace_id, channel, prefetched, force_model,
            session_id=session_id))
        _BG_TASKS.add(task)
        task.add_done_callback(_BG_TASKS.discard)
        yield ("mission", trace_id)              # el usuario puede abrirla/seguirla
        yield ("text", conversation.acuse_text())  # "me pongo a ello" — cierra el turno
        return

    # [Fix 2026-07-19] TRAZA ZOMBI. Si el cliente corta el stream (el botón de
    # parar, navegar a otra página, cerrar la app), este generador se cierra y
    # NADA de lo que viene después se ejecuta — incluido `record_end`. La traza
    # se quedaba en `running` PARA SIEMPRE, y aparecía en Misiones como "En
    # curso" eternamente aunque no hubiera nadie trabajando en ella (caso real
    # observado: una traza sin plan y sin outcome, huérfana).
    #
    # El `finally` la cierra pase lo que pase. Se comprueba el estado ANTES de
    # tocarla: si el flujo terminó bien, `record_end` ya la dejó en done/failed/
    # waiting y aquí no se pisa nada.
    try:
        async for ev in _stream_body(text, intent, mission, trace_id, channel,
                                     prefetched, force_model, session_id=session_id):
            yield ev
    finally:
        _close_if_orphan(trace_id)


def _close_if_orphan(trace_id: str) -> None:
    """Cierra una traza que quedó `running` porque su stream se abortó."""
    try:
        meta = tracer.get_meta(trace_id)
        if meta and meta.get("state") == "running":
            tracer.record_end(
                trace_id,
                outcome=_t("pipeline.stream_stopped"),
                state="cancelled",
            )
            logger.info(f"[tie] traza {trace_id[:8]} cerrada como cancelada (stream abortado)")
    except Exception as e:
        logger.info(f"[tie] no se pudo cerrar la traza abortada {trace_id[:8]}: {e!r}")


# [Opt latencia 2026-07-20] Herramientas del camino de acción directa. Una tarea
# de navegador casi siempre necesita BUSCAR la URL (search) y ABRIRLA (browser);
# una de escritorio, la tool desktop. Se unen a las que el clasificador detectó.
_BROWSER_DIRECT_TOOLS = ("search", "browser")
_COMPUTER_DIRECT_TOOLS = ("desktop",)


def _direct_action_tools(intent: Intent) -> list[str]:
    tools = list(intent.requires_tools or [])
    if intent.requires_browser:
        for t in _BROWSER_DIRECT_TOOLS:
            if t not in tools:
                tools.append(t)
    if intent.requires_computer:
        for t in _COMPUTER_DIRECT_TOOLS:
            if t not in tools:
                tools.append(t)
    return tools


async def _direct_action_path(
    text: str, intent: Intent, mission: Mission, trace_id: str,
    *, force_model: Optional[str] = None, channel: Optional[str] = None,
    session_id: Optional[str] = None,
) -> str:
    """[Opt latencia] Un ÚNICO bucle de tool-use resuelve una tarea mecánica
    entera —abrir, observar, actuar, responder— sin planner ni grafo multi-nodo.
    Con el modelo RÁPIDO de AGENTIC. Escribe mission.outcome. El bucle sigue
    pidiendo permiso por acción sensible si el usuario NO está en Autónomo (el
    ApprovalGate lo gobierna), así que no se salta ningún control."""
    from app.automation import approval_gate
    from app.memory import memory_router
    from app.tools import tool_manager

    t0 = __import__("time").monotonic()
    _record_path("direct")
    tools = _direct_action_tools(intent)
    runtime = get_runtime("null")
    # [2026-07-25] CONTEXTO REAL para el bucle. EL FALLO QUE CIERRA: una orden
    # como "en ESTE proyecto crea una milestone MVP y un agente" era imposible de
    # ejecutar — el bucle no sabía a qué proyecto se refería ni tenía los IDs
    # (`create_milestone` exige `project_id`), y acababa agotando iteraciones.
    # Ahora recibe (a) el estado real del workspace con IDs y (b) los últimos
    # turnos de la conversación, así que resuelve referencias ("este proyecto",
    # "el agente que acabo de crear") sin adivinar. Genérico: sirve a CUALQUIER
    # acción de `aithera_tool`, presente o futura. Best-effort.
    ctx_parts: list[str] = []
    try:
        from app.services import chat_service

        ws = await asyncio.to_thread(chat_service._workspace_block)
        if ws:
            ctx_parts.append(ws)
        turnos = await asyncio.to_thread(chat_service.recent_turns, session_id)
        if turnos:
            hist = "\n".join(f"{t['role']}: {t['content'][:300]}" for t in turnos[-6:])
            ctx_parts.append(
                "Últimos turnos de la conversación (para resolver referencias como "
                f"«este proyecto» o «ese agente»):\n{hist}"
            )
    except Exception as e:
        logger.info(f"[tie] no se pudo armar el contexto de la acción: {e!r}")

    task = AgentTask(
        id=AgentTask.new_id(),
        instruction=intent.raw_text or text,     # el texto ORIGINAL (fidelidad, S2)
        context="\n\n".join(ctx_parts),
        channel=channel or mission.channel,
        tools=tools,
        model_hint=force_model,
        mission_id=mission.id,                   # sesión de navegador por misión (F-1)
        project_id=mission.project_id,
        session_id=session_id,
    )
    result = await runtime.execute_task(
        task, memory=memory_router, tools=tool_manager, approval_gate=approval_gate,
    )
    out = result.output or (
        _t("pipeline.generic_done") if result.success
        else (result.error or _t("pipeline.generic_could_not"))
    )
    mission.outcome = out[:2000]
    mission.state = "done" if result.success else "failed"
    tracer.record_end(trace_id, outcome=mission.outcome, state=mission.state)
    if result.success:
        tracer.emit_completed(mission, ok=True, nodes=1)
    else:
        tracer.emit_failed(mission)
    dur = int((__import__("time").monotonic() - t0) * 1000)
    logger.info(f"[tie-perfil] acción directa: {dur}ms, tools={tools}, ok={result.success}")
    return out


async def _short_path_stream(text, intent, channel, memory_router, tool_manager,
                             approval_gate, force_model, session_id=None,
                             *, conversational=False):
    """[A·VOZ-3] Streaming del camino corto — SIN misión ni traza (una charla no
    es una misión, ver la nota en `handle_stream`/`_run_pipeline`). Streamea
    tokens de verdad, exactamente igual que antes; la única diferencia es que
    ya no abre ni cierra una fila en `orchestrator_traces`.

    `conversational` [A·VOZ-8]: si viene de VOZ, la respuesta se enruta por la
    política rápida (el runtime lo lee de `task.conversational`)."""
    _record_path("chat")
    task = AgentTask(id=AgentTask.new_id(), instruction=text, channel=channel,
                     tools=intent.requires_tools, model_hint=force_model,
                     session_id=session_id, conversational=conversational)
    runtime = get_runtime("null")
    # [A·VOZ-6 profiling] Tiempo hasta el PRIMER token del camino corto — la
    # métrica que importa para la fluidez de voz/chat (TTFT). Si es alto con la
    # charla, el cuello es el modelo de CHAT, no el TIE (que ya no pone traza,
    # status ni prefetch en este camino). Se loguea una sola vez por turno.
    import time as _time
    _t0 = _time.monotonic()
    _first = True
    async for chunk in runtime.stream_task(
        task, memory=memory_router, tools=tool_manager, approval_gate=approval_gate
    ):
        if chunk.kind == "text" and chunk.payload:
            if _first:
                _first = False
                logger.info(f"[tie-perfil] camino corto, primer token: "
                            f"{int((_time.monotonic() - _t0) * 1000)}ms")
            yield ("text", chunk.payload)


async def _stream_body(text, intent, mission, trace_id, channel, prefetched, force_model,
                       session_id=None):
    """El cuerpo real del streaming (acción directa / camino complejo — el corto
    ya se resolvió en `handle_stream` antes de llegar aquí, sin misión). Separado
    para que `handle_stream` pueda envolverlo en un `finally` que cierre la
    traza si el cliente se va."""
    # --- [Opt latencia] camino de ACCIÓN DIRECTA: tarea mecánica de un solo
    # encargo (abrir YouTube y poner música, crear carpeta+archivo). Sin planner
    # ni grafo: un bucle de tool-use rápido la resuelve de corrido. Colapsa ~8
    # llamadas (muchas lentas) en 3-4 rápidas. NO se emite ("mission",…) porque
    # no hay plan que revisar — es una acción, no una misión de varios pasos. ---
    # [2026-07-24] ACUSE INMEDIATO en texto natural (petición del usuario): una
    # misión tarda segundos o minutos — el chat NUNCA debe quedarse mudo mientras
    # tanto. Se emite YA un "Entendido, me pongo con ello: {goal}" y después
    # llegan los estados y el resultado (se concatenan en la misma burbuja).
    if intent.is_direct_action:
        yield ("text", _t("pipeline.ack_mission", goal=(intent.goal or text)[:120]) + "\n\n")
        yield ("status", _t("status.executing"))
        # [S4] Una acción directa encadena varias llamadas a herramientas: puede
        # tardar minutos legítimos. Con latido, nunca en silencio.
        _act = asyncio.ensure_future(_direct_action_path(
            text, intent, mission, trace_id, force_model=force_model,
            channel=channel, session_id=session_id))
        async for ev in _heartbeat_until(_act, every_s=settings.TIE_HEARTBEAT_S):
            yield ev
        try:
            out = await _act
        except Exception as e:
            logger.error(f"[tie] acción directa falló: {type(e).__name__}: {e}")
            out = _t("pipeline.generic_problem")
            mission.outcome = out
        yield ("text", mission.outcome or out)
        return

    # --- camino complejo ---
    yield ("text", _t("pipeline.ack_mission", goal=(intent.goal or text)[:120]) + "\n\n")
    yield ("status", _t("status.planning"))
    yield ("mission", trace_id)
    context = prefetched if not intent.memory_types else await _context_for(intent, text)
    # [S4] Igual que la acción directa: planner + ejecución del grafo pueden ser
    # minutos. El latido mantiene viva la conversación mientras tanto.
    _cx = asyncio.ensure_future(
        _complex_path(text, intent, mission, trace_id, context, force_model=force_model))
    async for ev in _heartbeat_until(_cx, every_s=settings.TIE_HEARTBEAT_S):
        yield ev
    try:
        await _cx
    except Exception as e:
        logger.error(f"[tie] handle_stream: pipeline complejo falló: {type(e).__name__}: {e}")
        mission.outcome = _t("pipeline.generic_problem")
    yield ("text", mission.outcome or _t("pipeline.no_response"))


async def _run_background_mission(text, intent, mission, trace_id, channel, prefetched, force_model,
                                  session_id=None):
    """[A·VOZ-4] El cuerpo de una misión de fondo (modo conversación). Corre
    detached (`asyncio.create_task`), sin stream: hace exactamente la misma
    selección de camino que `_stream_body` (acción directa o complejo) pero a
    completarse, no a emitir tokens. El reporte al usuario NO se manda aquí:

      · Terminación normal (done/failed): `_direct_action_path`/`_execute_and_respond`
        ya emiten `mission.completed`/`failed`; el handler del bus en
        `conversation.py` construye y entrega el reporte. Un solo camino, sin
        doble aviso, y cubre igual de bien la terminación TARDÍA tras aprobar un
        gate del plan (que ocurre en otra petición, fuera de esta tarea).
      · Pausa en gate (`mission.state == "waiting"`): no hay evento de terminación,
        así que se avisa aquí ("necesito tu permiso"), manteniendo la misión
        registrada para el reporte final cuando el usuario apruebe.
    """
    try:
        if intent.is_direct_action:
            await _direct_action_path(text, intent, mission, trace_id,
                                      force_model=force_model, channel=channel,
                                      session_id=session_id)
        else:
            context = prefetched if not intent.memory_types else await _context_for(intent, text)
            await _complex_path(text, intent, mission, trace_id, context, force_model=force_model)
    except Exception as e:
        logger.error(f"[tie] misión de fondo falló: {type(e).__name__}: {e}")
        # El grupo done/failed lo cubre el bus; una excepción DURA aquí (rara) no
        # emitió evento, así que se cierra la traza y se avisa como fallo honesto.
        try:
            if not mission.outcome:
                mission.outcome = _t("conversation.report_error")
            tracer.record_end(trace_id, outcome=mission.outcome, state="failed")
        except Exception:
            pass
        await conversation.report_failure(mission.id)
        return

    if mission.state == "waiting":
        await conversation.on_gate_pending(mission.id)


async def submit_mission(
    goal: str,
    *,
    source: str = "automation",
    channel: Optional[str] = None,
    project_id: Optional[int] = None,
    run_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    allowed_tools: Optional[list[str]] = None,
    repo_path: Optional[str] = None,
    intent: Optional[Intent] = None,
    skills: Optional[list[str]] = None,
) -> Mission:
    """Entrada PROGRAMÁTICA (AE `AgentTaskAction`, WPMS, Orquestador) — ya sabe
    que es una misión, así que NO hay camino corto: siempre planifica y ejecuta.
    Devuelve la Mission con su `outcome`.

    `run_id`/`parent_id` (R2) son la jerarquía: a qué orquestación pertenece esta
    misión y de qué misión más amplia nació. El TIE no los interpreta — los
    guarda en la traza para que la UI y el Learner puedan reconstruir el árbol.

    `allowed_tools`/`repo_path` (R4) acotan la misión cuando la lanza un AGENTE:
    sus herramientas, su proyecto y su carpeta. Sin ellos la misión no tiene
    frontera, que es el caso del chat del usuario. Delegar SIN pasar la whitelist
    del agente sería ampliarle los permisos en silencio.

    `skills` [PU2, doc 35]: las especialidades del agente (nombres del catálogo
    de `skills_catalog.py`, ya validados al crear/editar el agente). Viaja
    DENTRO de `Authority` (descriptivo, no de seguridad) para que sobreviva al
    checkpoint y el executor las incluya en el contexto de cada nodo — antes
    se guardaban en BD y no llegaban a ningún sitio."""
    mission = new_mission(goal=goal, source=source, channel=channel, project_id=project_id,
                          run_id=run_id, parent_id=parent_id)
    # [S2, C-1] `intent` opcional (mismo patrón que handle_stream): quien ya
    # clasificó no paga una segunda llamada NI una segunda reescritura. Si se
    # clasifica aquí, `classify` estampa raw_text=goal, así que el planner
    # trabajará sobre el goal LITERAL que nos pasaron — el texto del encargo ya
    # no muta entre el decomposer y el plan.
    if intent is None:
        intent = await intents.classify(goal, channel=channel)
    if not intent.raw_text:
        intent.raw_text = goal
    intent.requires_planning = True  # una misión explícita nunca es "charla"
    trace_id = tracer.record_start(mission, channel=channel)
    mission.trace_id = trace_id     # [fix mismatch, doc 31] mission.id != trace_id
    tracer.record_intent(trace_id, intent)
    tracer.emit_started(mission)

    # [E2b] Override de tarea si el goal nombra un modelo (el pin de PROYECTO se
    # lee solo, vía mission.project_id → context_tags). No hay turno interactivo
    # aquí: una aclaración de alcance ("reply") se ignora y se sigue normal.
    explicit = await _resolve_explicit_model(intent, project_id=project_id)
    force_model = explicit["model_key"] if explicit and explicit.get("action") == "force" else None

    # [R4] La frontera de la misión.
    #
    # ORQUESTADOR DE PROYECTO (doc 14 §4.3c): si la misión es de un proyecto que
    # tiene agente `role="orchestrator"` y nadie ha impuesto ya una frontera
    # (`allowed_tools=None`, es decir: no viene de un agente concreto), la misión
    # se enruta a ese orquestador y adopta SU alcance — sus herramientas, su
    # proyecto, su carpeta. Es lo que hace que "el proyecto tiene un responsable"
    # signifique algo ejecutable y no solo una etiqueta en una columna.
    if project_id is not None and allowed_tools is None:
        orch = authority_mod.orchestrator_of(project_id)
        if orch:
            allowed_tools = orch["allowed_tools"]
            repo_path = repo_path or orch["repo_path"]
            logger.info(
                f"[tie] misión del proyecto {project_id} enrutada a su orquestador "
                f"'{orch['name']}' (agente {orch['id']})"
            )

    # `Authority()` sin campos = sin restricción, así que el comportamiento de
    # quien no la pasa (el chat del usuario, el Orquestador de R2) no cambia.
    authority = Authority(
        project_id=project_id if (allowed_tools is not None or repo_path) else None,
        repo_path=repo_path,
        allowed_tools=allowed_tools,
        skills=skills,
    )

    context = await _context_for(intent, goal, project_id=project_id)
    await _complex_path(goal, intent, mission, trace_id, context,
                        force_model=force_model, authority=authority)
    return mission


# ---------------------------------------------------------------------------
# El pipeline
# ---------------------------------------------------------------------------
async def _run_pipeline(
    text: str, *, source: str, channel: Optional[str], project_id: Optional[int] = None
) -> str:
    # [2026-07-24] Respuesta determinista sobre los datos propios (0 LLM) —
    # mismo criterio que en handle_stream; cubre el Gateway/Telegram.
    quick = await asyncio.to_thread(quick_answers.try_answer, text)
    if quick:
        return quick
    # [PU4, doc 35] Mismo criterio, async (lee la locución cacheada del MOS).
    quick_briefing = await quick_answers.try_answer_async(text)
    if quick_briefing:
        return quick_briefing
    # [PU10, doc 35] Mini-chat de memoria con ancla — cubre el Gateway/Telegram
    # igual que los dos anteriores.
    from app.memory import quick_memory

    quick_mem = await quick_memory.try_answer_async(text)
    if quick_mem:
        return quick_mem

    # [1+2] Clasificar y pre-fetch de contexto EN PARALELO (doc 11 B.2): el
    # enricher no sabe todavía qué tipos pedir, así que hace una consulta general;
    # si el intent pide tipos concretos, el planner/nodo la afinará. Coste: una
    # llamada barata + una consulta al MOS con presupuesto duro, a la vez.
    intent_task = asyncio.create_task(intents.classify(text, channel=channel))
    ctx_task = asyncio.create_task(_prefetch_context(text))
    intent = await intent_task
    prefetched = await ctx_task

    # [E2b] ¿El usuario nombró un modelo? Aclarar/pinear/forzar antes de nada.
    explicit = await _resolve_explicit_model(intent, project_id=project_id)
    if explicit and explicit["action"] == "reply":
        return explicit["text"]   # aclaración/confirmación: no se ejecuta nada este turno
    force_model = explicit["model_key"] if explicit else None
    # [PU3] Autónomo asumió el alcance sin preguntar — se antepone como
    # preámbulo de la respuesta de este turno, nunca en silencio.
    _scope_note = explicit.get("note") if explicit else None

    # [A·VOZ-3, doc 32] Camino corto: ~80% de las queries no pagan planner ni
    # grafo (doc 14 §6) — Y AHORA TAMPOCO MISIÓN/TRAZA. Una charla no es una
    # misión: crear la fila en `orchestrator_traces` (vía `new_mission` +
    # `tracer.record_start`) era lo que hacía aparecer los saludos en Misiones
    # ("Responder al saludo / Completado") y lo que escribía en el hot path de
    # cada mensaje trivial. Solo se crea misión/traza cuando el flujo entra en
    # `is_direct_action` o en el camino complejo (misiones DE VERDAD). La
    # conversación se sigue persistiendo como conversación (session_id/
    # ChatMessage vía NullRuntime) — eso no cambia; lo que se retira es la
    # traza de misión. La telemetría no se rompe: su contexto de misión
    # (`_mission_ctx`) ya tiene (None, None) como default documentado para
    # "llamada suelta (chat corto)" — exactamente este caso.
    if intent.is_short_path:
        answer = await _short_path(text, intent, channel, model_key=force_model)
        return f"{_scope_note}\n\n{answer}" if _scope_note else answer

    mission = new_mission(goal=intent.goal or text, source=source, channel=channel)
    trace_id = tracer.record_start(mission, channel=channel)
    mission.trace_id = trace_id     # [fix mismatch, doc 31] mission.id != trace_id
    tracer.record_intent(trace_id, intent)
    tracer.emit_started(mission)

    # [Opt latencia] Acción directa: tarea mecánica de un solo encargo → un bucle
    # de tool-use rápido, sin planner (mismo criterio que el camino de streaming).
    if intent.is_direct_action:
        return await _direct_action_path(text, intent, mission, trace_id,
                                         force_model=force_model, channel=channel)

    # [4] Complejo: contexto afinado por el intent (si pidió tipos concretos) y a planificar.
    context = prefetched if not intent.memory_types else await _context_for(intent, text)
    await _complex_path(text, intent, mission, trace_id, context, force_model=force_model)
    return mission.outcome or _t("pipeline.no_response")


async def _complex_path(
    text: str, intent: Intent, mission: Mission, trace_id: str, context: str,
    *, force_model: Optional[str] = None, authority: Optional[Authority] = None,
) -> None:
    """planner → (gate del plan) → executor → responder. Escribe `mission.outcome`.
    `force_model` (E2b): si el usuario nombró un modelo para esta tarea, TODOS los
    nodos del plan lo usan (`node.model_hint` = id concreto, que el executor
    reenvía → el MEL lo trata como override).
    `authority` (R4): frontera de la misión cuando viene de un agente; el planner
    recorta el plan a sus tools y la graba en el grafo."""
    _record_path("planned")
    # [S2, C-1] EL FIX DE FIDELIDAD: se planifica sobre el TEXTO ORIGINAL del
    # usuario (`raw_text`), no sobre el goal reescrito por el clasificador.
    # `text` es el original en los caminos de handle; raw_text lo cubre además
    # en cualquier caller futuro que solo pase el intent.
    graph = await planner.plan(
        intent.raw_text or text, intent, context=context, mission_id=mission.id, trace_id=trace_id,
        authority=authority,
    )
    if isinstance(graph, planner.PlanRejection):
        # [S2, B-1] El objetivo excede las capacidades reales: se le dice AL
        # USUARIO, claro y a la primera — nunca una misión fantasma que finge.
        mission.outcome = _t("pipeline.cannot_capability", reason=graph.reason)
        mission.state = "done"   # es una RESPUESTA (honesta), no un fallo del sistema
        tracer.record_end(trace_id, outcome=mission.outcome)
        tracer.emit_completed(mission, ok=True, nodes=0)
        return
    if graph is None:
        # El planner no logró un grafo válido ni tras el reintento → degradar al
        # camino corto (regla 11-B: nunca romper; el usuario recibe algo).
        logger.info("[tie] sin plan válido — degradando a camino corto")
        out = await _short_path(text, intent, mission.channel, model_key=force_model)
        mission.outcome = out[:2000]
        mission.state = "done"
        tracer.record_end(trace_id, outcome=mission.outcome)
        tracer.emit_completed(mission, ok=True, nodes=0)
        return

    # [E2b] Override de tarea: forzar el modelo elegido en TODOS los nodos del
    # plan (el executor reenvía `node.model_hint` → el MEL lo trata como override).
    if force_model:
        for n in graph.nodes.values():
            n.model_hint = force_model

    mission.graph_ids = [graph.id]

    # ¿El plan toca algo sensible? → se aprueba EL PLAN antes de ejecutar nada
    # (transparencia estilo plan-mode; doc 14 §3.3). Nada se ha ejecutado aún:
    # planificar no tiene side effects (regla 11-B).
    if _needs_plan_approval(graph):
        await _open_plan_gate(graph, mission, trace_id)
        mission.outcome = _t(
            "pipeline.plan_needs_approval", n=len(graph.nodes), goal=mission.goal,
            plan_summary=responder.plan_summary(graph),
        )
        tracer.record_end(trace_id, outcome=mission.outcome, state="waiting")
        return

    graph.state = "approved"
    await _execute_and_respond(graph, mission, trace_id)


async def _execute_and_respond(graph: TaskGraph, mission: Mission, trace_id: str) -> None:
    """Ejecuta el grafo y sintetiza la respuesta. Compartido por el camino normal
    y por la reanudación tras aprobar el plan.

    [NEW-6, doc 34 §12.9] La síntesis del outcome (¿la misión sigue esperando
    otro gate, o hay que llamar a `responder.build()`?) vive en
    `executor.finish_and_record()` — el MISMO punto que usa la reanudación de
    un gate de NODO/checkpoint (`_apply_gate_verdict`/`_apply_checkpoint_
    verdict`, en `executor.py`). Antes esta función tenía su propia copia de
    esa lógica y la reanudación tenía otra: un gate de nodo resuelto dejaba el
    outcome con el placeholder "esperando tu confirmación" para siempre,
    aunque `mission.state` ya hubiera avanzado a "done" — cabecera
    "Completada", cuerpo de una misión que sigue esperando."""
    await executor.run(graph, mission, trace_id=trace_id)
    await executor.finish_and_record(graph, mission, trace_id)


# ---------------------------------------------------------------------------
# Camino corto
# ---------------------------------------------------------------------------
async def _short_path(
    text: str, intent: Intent, channel: Optional[str], *, model_key: Optional[str] = None
) -> str:
    """NullRuntime → respuesta. Se pasa por la interfaz AgentRuntime (no por
    chat_service directo): el camino corto ya ejercita el MISMO contrato que
    usará HermesRuntime en V1.1. `model_key` (E2b): si el usuario nombró un
    modelo para este turno, va como `model_hint` (id concreto) → override del MEL."""
    _record_path("chat")
    from app.automation import approval_gate
    from app.memory import memory_router
    from app.tools import tool_manager

    runtime = get_runtime("null")  # V1.1: routing por capabilities
    task = AgentTask(
        id=AgentTask.new_id(), instruction=text, channel=channel, tools=intent.requires_tools,
        model_hint=model_key,
    )
    result = await runtime.execute_task(
        task, memory=memory_router, tools=tool_manager, approval_gate=approval_gate,
    )
    return result.output or _t("pipeline.no_response")


async def _prefetch_context(text: str) -> str:
    try:
        return await enricher.enrich(text)
    except Exception:
        return ""


async def _context_for(intent: Intent, fallback_query: str,
                       project_id: Optional[int] = None) -> str:
    if not intent.requires_memory and not intent.memory_types:
        return ""
    try:
        return await enricher.enrich(
            intent.context_query or intent.goal or fallback_query,
            memory_types=intent.memory_types or None,
            # [S2-extra, C-1b] Aislamiento de proyecto en el contexto del plan.
            project_id=project_id,
        )
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Gate del PLAN (doc 14 §3.3) — transparencia antes de ejecutar
# ---------------------------------------------------------------------------
def _needs_plan_approval(graph: TaskGraph) -> bool:
    """El plan se aprueba entero cuando toca algo sensible. `TIE_PLAN_APPROVAL`
    permite desactivarlo (entonces cada nodo sensible pide su propio permiso —
    el gate de nodo de T3 sigue ahí)."""
    if not settings.TIE_PLAN_APPROVAL:
        return False
    return any(n.approval_required for n in graph.nodes.values())


async def _open_plan_gate(graph: TaskGraph, mission: Mission, trace_id: str) -> None:
    from app.automation import approval_gate

    gate_id = await approval_gate.request_approval(
        kind="tie.plan",
        title=_t("pipeline.plan_gate_title", n=len(graph.nodes), goal=mission.goal[:150]),
        summary=responder.plan_summary(graph),
        action_type=PLAN_ACTION_TYPE,
        action_payload={"trace_id": trace_id, "mission_id": mission.id},
        channel=mission.channel or "hub",
    )
    graph.state = "draft"
    tracer.update_graph(trace_id, graph)
    tracer.set_state(trace_id, "waiting")
    mission.state = "waiting"
    logger.info(f"[tie] plan de la misión {mission.id} esperando aprobación (gate {gate_id})")


async def _apply_plan_verdict(trace_id: str, approved: bool) -> None:
    """Aplica el veredicto del gate del PLAN. Lo invoca el handler del evento
    `approval.resolved` (en background — nunca dentro del resolve() del gate,
    que vive en un request HTTP; mismo criterio que los gates de nodo, T3)."""
    graph = tracer.load_graph(trace_id)
    meta = tracer.get_meta(trace_id)
    if graph is None or meta is None or graph.state != "draft":
        return  # ya aplicado (idempotencia) o traza inexistente

    mission = Mission(
        id=meta.get("mission_id") or graph.mission_id,
        goal=_goal_from_meta(meta),
        channel=meta.get("channel"),
        state="running",
        graph_ids=[graph.id],
    )

    if not approved:
        graph.state = "cancelled"
        for n in graph.nodes.values():
            n.state = NodeState.CANCELLED
        tracer.update_graph(trace_id, graph)
        mission.state = "cancelled"
        mission.outcome = _t("pipeline.plan_discarded")
        tracer.record_end(trace_id, outcome=mission.outcome, state="cancelled")
        tracer.emit_cancelled(mission)
        return

    # Aprobar el PLAN autoriza sus pasos sensibles: el usuario ha visto la lista
    # completa y ha dicho que sí. Se marca cada nodo con el gate del plan para que
    # el executor NO vuelva a preguntar uno por uno (`node.gate_id is None` es su
    # condición para abrir gate, T3). Queda auditado: cada nodo apunta a la
    # aprobación que lo autorizó.
    plan_gate = _find_plan_gate_id(trace_id)
    for n in graph.nodes.values():
        if n.approval_required and n.gate_id is None:
            n.gate_id = plan_gate
    graph.state = "approved"
    tracer.update_graph(trace_id, graph)
    tracer.set_state(trace_id, "running")
    await _execute_and_respond(graph, mission, trace_id)


def _find_plan_gate_id(trace_id: str, *, only_pending: bool = False) -> Optional[str]:
    """El gate del plan cuyo payload apunta a esta traza (para dejar el enlace de
    auditoría en cada nodo autorizado, y para que la API lo resuelva)."""
    from app.automation import Approval
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        q = db.query(Approval).filter(Approval.action_type == PLAN_ACTION_TYPE)
        if only_pending:
            q = q.filter(Approval.status == "pending")
        for r in q.all():
            if (r.action_payload or {}).get("trace_id") == trace_id:
                return r.id
    except Exception:
        return None
    finally:
        db.close()
    return None


async def resolve_plan(trace_id: str, approved: bool, note: str = "") -> Optional[dict]:
    """API pública para aprobar/rechazar el plan de una misión (la usa
    `/api/tie/missions/{id}/approve-plan`). Resuelve el ApprovalGate del plan; la
    ejecución arranca en background (el POST responde al instante). None si no
    hay plan pendiente para esa misión.

    Vive aquí y no en el endpoint para que la API no tenga que conocer los
    internos del TIE (doc 16: se habla con el módulo por su fachada)."""
    gate_id = _find_plan_gate_id(trace_id, only_pending=True)
    if gate_id is None:
        return None

    from app.automation import approval_gate

    result = await approval_gate.resolve(gate_id, approved, note)
    return {"gate_id": gate_id, "status": result.status, "approved": approved}


def _goal_from_meta(meta: dict) -> str:
    """El goal vive en el intent de la traza (la Mission de V1.0 es implícita)."""
    from app.db.database import OrchestratorTrace, SessionLocal

    db = SessionLocal()
    try:
        row = db.get(OrchestratorTrace, meta["id"])
        if row and row.intent:
            return row.intent.get("goal", "") or ""
        return ""
    except Exception:
        return ""
    finally:
        db.close()


async def _on_approval_resolved(event) -> None:
    """Handler del bus para el gate del PLAN. Los gates de NODO los atiende el
    executor (T3) — cada uno mira su propio `action_type` y se ignoran mutuamente."""
    payload = event.payload or {}
    if payload.get("action") != PLAN_ACTION_TYPE:
        return
    gate_id = payload.get("gate_id")
    approved = payload.get("resolution") == "approved"
    try:
        from app.automation import approval_gate

        appr = approval_gate.get(gate_id)
        if appr is None:
            return
        trace_id = (appr.action_payload or {}).get("trace_id")
        if trace_id:
            await _apply_plan_verdict(trace_id, approved)
    except Exception as e:
        logger.error(f"[tie] fallo aplicando el veredicto del plan (gate {gate_id}): {e!r}")


async def _plan_gate_executor(payload: dict) -> str:
    """Ejecutor de `tie_plan`. NO ejecuta el plan aquí: la ejecución es
    event-driven (ver `_on_approval_resolved`) para no bloquear el request HTTP
    que resuelve la aprobación. Mismo criterio que `tie_resume` (T3)."""
    return f"plan aprobado; ejecución de la misión {payload.get('mission_id')} en curso"


def register_plan_handlers() -> None:
    """Cablea el gate del PLAN con el ApprovalGate + el bus. Idempotente."""
    from app.automation import approval_gate
    from app.core.events import subscribe, unsubscribe

    approval_gate.register_executor(PLAN_ACTION_TYPE, _plan_gate_executor)
    unsubscribe("approval.resolved", _on_approval_resolved)
    subscribe("approval.resolved", _on_approval_resolved)
