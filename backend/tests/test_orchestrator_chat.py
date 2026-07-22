# tests/test_orchestrator_chat.py — los 5 fallos reportados por el usuario
# (2026-07-19) con su caso real: "envía un email a X ... también abre YouTube y
# pon la canción Y".
#
# Lo que pasó de verdad, verificado contra su Postgres antes de tocar nada:
#   A) el chat llamaba a `tie.handle_stream` DIRECTO → nunca pasaba por el
#      Orquestador → un mensaje con 2 encargos independientes acababa en UNA
#      misión con 2 pasos secuenciales en vez de 2 misiones a la vez;
#   B) el clasificador devolvía `objectives: []` para ese mensaje;
#   C) el bucle pedía permiso con `tool.email.send_email`, id que NO existe en el
#      catálogo (`email.send`) → fail-closed → el perfil "Autónomo" no servía;
#   D) aprobar el PLAN no eximía a las acciones del bucle → volvía a preguntar;
#   E) abortar el stream dejaba la traza en `running` para siempre ("En curso").
from __future__ import annotations

import pytest

from app.tie.contracts import Intent, IntentType


@pytest.fixture
def _runs_reales():
    """Crea la tabla `orchestration_runs` en la BD de tests y limpia los runs
    que el test genere. Mismo patrón que `test_orchestrator.py::_limpia_runs`
    (init_db corre antes de que los modelos del orquestador se registren, así
    que create_all de entrada es obligatorio en SQLite de tests). Sin la tabla,
    `store.save` falla en silencio (best-effort) y el bucle de sondeo de
    `_orchestrate_stream` nunca ve los objetivos — el test de los eventos
    "mission" necesita el store FUNCIONANDO, no mudo."""
    from app.db.database import Base, SessionLocal, engine as db_engine
    from app.orchestrator import store

    Base.metadata.create_all(bind=db_engine)
    creados: list[str] = []
    original = store.save

    def _spy(run, **kwargs):
        if run.id not in creados:
            creados.append(run.id)
        return original(run, **kwargs)

    store.save = _spy
    yield
    store.save = original
    from app.orchestrator.models import OrchestrationRunRow
    db = SessionLocal()
    try:
        for rid in creados:
            row = db.get(OrchestrationRunRow, rid)
            if row is not None:
                db.delete(row)
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# A) El chat pasa por el Orquestador
# ---------------------------------------------------------------------------
def test_el_chat_entra_por_el_orquestador_no_por_el_tie_directo():
    """El endpoint del chat debe usar `orchestrator.handle_stream`. Si alguien
    vuelve a llamar a `tie.handle_stream` sin pasar por la capa de arriba, el
    Orquestador se queda otra vez sin activarse desde la interfaz principal."""
    from pathlib import Path

    src = (Path(__file__).resolve().parent.parent / "app" / "api" / "endpoints" / "chat.py").read_text(
        encoding="utf-8"
    )
    assert "orchestrator.handle_stream" in src, (
        "el chat ya no entra por el Orquestador — R2 deja de aplicarse al chat"
    )


def test_el_orquestador_expone_handle_stream():
    import app.orchestrator as orchestrator

    assert hasattr(orchestrator, "handle_stream")
    assert "handle_stream" in orchestrator.__all__


@pytest.mark.anyio
async def test_un_solo_encargo_delega_en_el_tie_sin_reclasificar(monkeypatch):
    """NO-REGRESIÓN (doc 23 §0): con 1 objetivo, el ~80% de los mensajes, no se
    puede pagar una segunda llamada al clasificador ni cambiar el camino."""
    import app.orchestrator as orchestrator
    import app.tie as tie

    llamadas = {"classify": 0, "tie_stream": 0, "intent_recibido": None}

    async def _classify(text, channel=None):
        llamadas["classify"] += 1
        return Intent(type=IntentType.CONVERSATIONAL, goal=text, confidence=0.9)

    async def _tie_stream(text, *, channel="web", intent=None, session_id=None):
        llamadas["tie_stream"] += 1
        llamadas["intent_recibido"] = intent
        llamadas["session_recibida"] = session_id
        yield ("text", "respuesta corta")

    monkeypatch.setattr(tie, "classify", _classify)
    monkeypatch.setattr(tie, "handle_stream", _tie_stream)

    eventos = [ev async for ev in orchestrator.handle_stream("hola que tal",
                                                            session_id="s-1")]

    assert ("text", "respuesta corta") in eventos
    assert llamadas["tie_stream"] == 1
    assert llamadas["classify"] == 1, "se clasificó más de una vez"
    assert llamadas["intent_recibido"] is not None, (
        "no se reutilizó el intent: el TIE volvería a clasificar (llamada extra al LLM)"
    )
    assert llamadas["session_recibida"] == "s-1", (
        "[R6.5b] el Orquestador se comió la sesión: el chat perdería el hilo al "
        "pasar por él, que es justo el camino que usa la interfaz principal"
    )


@pytest.mark.anyio
async def test_dos_encargos_independientes_lanzan_misiones_en_paralelo(monkeypatch, _runs_reales):
    """EL CASO DEL USUARIO. Dos encargos que no dependen entre sí → dos misiones
    a la vez, no un plan de 2 pasos secuenciales."""
    import asyncio

    import app.orchestrator as orchestrator
    import app.tie as tie
    from app.orchestrator import decomposer as decomposer_mod
    from app.orchestrator.contracts import Objective

    async def _classify(text, channel=None):
        return Intent(
            type=IntentType.EXECUTE, goal="hacer dos cosas", confidence=0.95,
            requires_planning=True,
            objectives=["Enviar un email a X", "Abrir YouTube y poner una canción"],
        )

    async def _decompose(message, *, objectives_hint, depth=0):
        return [Objective(id="o1", goal=objectives_hint[0]),
                Objective(id="o2", goal=objectives_hint[1])]

    en_vuelo = {"actual": 0, "max": 0}

    class _M:
        def __init__(self, i):
            self.id = f"mission-{i}"
            self.trace_id = f"trace-{i}"
            self.outcome = f"hecho {i}"
            self.state = "done"

    contador = {"n": 0}

    async def _submit_mission(goal, **kwargs):
        contador["n"] += 1
        i = contador["n"]
        en_vuelo["actual"] += 1
        en_vuelo["max"] = max(en_vuelo["max"], en_vuelo["actual"])
        try:
            await asyncio.sleep(0.25)
            return _M(i)
        finally:
            en_vuelo["actual"] -= 1

    async def _consolidate(run):
        return "He hecho las dos cosas."

    monkeypatch.setattr(tie, "classify", _classify)
    monkeypatch.setattr(tie, "submit_mission", _submit_mission)
    monkeypatch.setattr(decomposer_mod, "decompose", _decompose)
    from app.orchestrator import consolidator as consolidator_mod
    monkeypatch.setattr(consolidator_mod, "consolidate", _consolidate)

    eventos = [ev async for ev in orchestrator.handle_stream(
        'envia un email a X y tambien abre youtube y pon una cancion')]

    assert contador["n"] == 2, f"se lanzaron {contador['n']} misiones, se esperaban 2"
    assert en_vuelo["max"] >= 2, (
        "las misiones NO corrieron a la vez: se ejecutaron uma detrás de otra"
    )
    textos = [p for k, p in eventos if k == "text"]
    assert textos and "dos cosas" in textos[-1]

    # [fix mismatch mission_id/trace_id, 2026-07-22] El evento SSE "mission"
    # debe llevar el TRACE_ID (lo que `/api/tie/missions/{id}` y Missions.tsx
    # ya esperan), no el `mission.id`. Antes de este fix se emitía
    # `mission-1`/`mission-2` (el mission_id) y el frontend nunca encontraba
    # esa misión en la lista — abría la primera de la lista en su lugar.
    ids_emitidos = {p for k, p in eventos if k == "mission"}
    assert ids_emitidos == {"trace-1", "trace-2"}, (
        f"se emitieron mission_id en vez de trace_id: {ids_emitidos}"
    )


# ---------------------------------------------------------------------------
# C) Permisos: la traducción que faltaba
# ---------------------------------------------------------------------------
def test_las_acciones_de_tool_se_traducen_a_permisos_del_catalogo():
    from app.automation import permission_service as p

    # Lo que el bucle pide  ->  lo que el usuario ve en Ajustes → Permisos
    assert p.permission_for_tool_action("email", "send_email") == "email.send"
    assert p.permission_for_tool_action("browser", "click") == "browser.use"
    assert p.permission_for_tool_action("desktop", "type") == "computer.use"
    assert p.permission_for_tool_action("shell", "run_command") == "shell.run"


def test_una_tool_sin_permiso_asociado_sigue_preguntando():
    """Fail-closed: si una acción no está cubierta por ningún permiso del
    catálogo, se pregunta. Nunca se asume autorizado."""
    from app.automation import permission_service as p

    assert p.permission_for_tool_action("tool_que_no_existe", "x") is None
    assert p.is_tool_action_pre_authorized("tool_que_no_existe", "x") is False


def test_run_agent_task_pide_agent_execute_no_workspace_write():
    """Poder crear tareas NO debe implicar poder ejecutar agentes."""
    from app.automation import permission_service as p

    assert p.permission_for_tool_action("aithera", "run_agent_task") == "agent.execute"
    assert p.permission_for_tool_action("aithera", "create_task") == "workspace.write"


@pytest.mark.anyio
async def test_con_el_permiso_activado_el_bucle_no_pregunta(monkeypatch):
    """El bug exacto del usuario: perfil Autónomo con email.send activado, y aun
    así el bucle abría un gate porque el id no casaba."""
    from app.automation import permission_service
    from app.tie import toolloop

    monkeypatch.setattr(
        permission_service, "is_tool_action_pre_authorized",
        lambda tool_id, action: tool_id == "email" and action == "send_email",
    )

    class _GateQueNoDebeUsarse:
        async def request_approval(self, **kw):
            raise AssertionError("no debería abrir un gate: ya estaba autorizado")

    granted, motivo = await toolloop._ask_permission(
        {"tool_id": "email", "action": "send_email"}, {"to": "x@y.z"},
        _GateQueNoDebeUsarse(), instruction="enviar email", wait_s=1,
    )
    assert granted is True
    assert "antemano" in motivo


# ---------------------------------------------------------------------------
# D) Aprobar el plan cubre las acciones del bucle
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_aprobar_el_plan_no_vuelve_a_preguntar_por_cada_accion():
    from app.tie import toolloop

    class _GateQueNoDebeUsarse:
        async def request_approval(self, **kw):
            raise AssertionError("el usuario ya aprobó el plan entero")

    granted, motivo = await toolloop._ask_permission(
        {"tool_id": "email", "action": "send_email"}, {},
        _GateQueNoDebeUsarse(), instruction="enviar", wait_s=1,
        pre_approved=True,
    )
    assert granted is True
    assert "aprobaste" in motivo


def test_el_executor_marca_el_nodo_ya_aprobado():
    """`gate_id` puesto = el usuario dijo que sí a ese paso (gate del plan o del
    nodo). El AgentTask tiene que llevarlo para que el bucle lo respete."""
    from app.tie.runtime import AgentTask

    t = AgentTask(id="t1", instruction="x", actions_pre_approved=True)
    assert t.actions_pre_approved is True
    assert AgentTask(id="t2", instruction="x").actions_pre_approved is False


# ---------------------------------------------------------------------------
# E) Traza zombi
# ---------------------------------------------------------------------------
def test_una_traza_running_sin_plan_se_cierra_en_vez_de_quedarse_en_curso():
    """Caso real: traza `running`, sin plan y sin outcome, visible para siempre
    como "En curso" en Misiones. Al no tener grafo no se puede reanudar, así que
    hay que cerrarla — antes se quedaba igual arranque tras arranque."""
    import asyncio

    from app.db.database import Base, SessionLocal, OrchestratorTrace, engine as db_engine
    from app.tie import executor, tracer
    from app.tie.missions import new_mission

    Base.metadata.create_all(bind=db_engine)
    m = new_mission("misión abortada", source="user", channel="web")
    trace_id = tracer.record_start(m, channel="web")
    tracer.set_state(trace_id, "running")

    try:
        asyncio.run(executor.resume_pending())
        meta = tracer.get_meta(trace_id)
        assert meta["state"] == "cancelled", (
            f"la traza huérfana sigue en {meta['state']} — reaparecerá como 'En curso'"
        )
    finally:
        s = SessionLocal()
        try:
            row = s.get(OrchestratorTrace, trace_id)
            if row:
                s.delete(row)
                s.commit()
        finally:
            s.close()


def test_el_pipeline_tiene_guardia_para_streams_abortados():
    from app.tie import pipeline

    assert hasattr(pipeline, "_close_if_orphan")
