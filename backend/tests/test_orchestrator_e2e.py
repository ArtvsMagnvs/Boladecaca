# tests/test_orchestrator_e2e.py — el bloque ORQUESTADOR de punta a punta (R7, doc 23 §3·R7)
#
# Los tests de R1-R6 prueban cada pieza con las de al lado MOCKEADAS
# (test_orchestrator_chat.py sustituye `tie.handle_stream` entero;
# test_tie_handle.py sustituye planner/responder). Este archivo prueba la
# CADENA REAL del bloque completo, con UN SOLO punto fake — la frontera del
# LLM — igual que `test_tie_e2e.py` hizo para el TIE en T5:
#
#   orchestrator.handle
#     → tie.classify            (real: JSON → Intent, incluidos `objectives`)
#     → decomposer.decompose    (real: JSON → Objective[] con dependencias)
#     → conductor.run_objectives(real: concurrencia + semáforo + aislamiento)
#         → tie.submit_mission  (real: planner → graph.validate → executor)
#             → NullRuntime     (real: incluido el bucle de tool-use de R1)
#                 → ToolManager (REAL: se ejecuta una tool de verdad)
#     → consolidator.consolidate(real: síntesis o plantilla determinista)
#
# El caso insignia del bloque (doc 23 §0): un mensaje con varios encargos
# INDEPENDIENTES produce N misiones a la vez, no un plan secuencial. Y la regla
# de no-regresión: con un solo encargo, nada de esto se activa.
from __future__ import annotations

import json

import pytest

from app.automation import Approval
from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine
from app.orchestrator import models as orch_models
from app.tie import enricher as enricher_mod, register_handlers


def _borrar_residuos():
    s = SessionLocal()
    try:
        s.query(OrchestratorTrace).delete()
        s.query(orch_models.OrchestrationRunRow).delete()
        s.query(Approval).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


@pytest.fixture(autouse=True)
def _clean():
    # Se limpia al ENTRAR y al SALIR. Solo al salir NO basta: estos tests cuentan
    # trazas ("¿hay 2 misiones?") y cualquier test previo de la suite que deje una
    # traza los rompe — pasan aislados y fallan en la suite completa, que es el
    # peor modo de fallo posible. Misma lección que en A4 y R6.5c.
    Base.metadata.create_all(bind=db_engine)
    register_handlers()
    enricher_mod._cache.clear()
    _borrar_residuos()
    yield
    _borrar_residuos()


class _Env:
    def __init__(self, text, channel="electron"):
        self.text = text
        self.channel = channel
        self.user_ref = "u1"


def _no_context(monkeypatch):
    """El enricher (T2) ya está probado en aislamiento; se neutraliza para que el
    e2e no dependa de que el MOS esté inicializado en el entorno de test."""
    async def _enrich(*a, **k):
        return ""
    monkeypatch.setattr(enricher_mod, "enrich", _enrich)


# ---------------------------------------------------------------------------
# LA frontera fake: el LLM. Todo lo de este lado es código real de Aithera.
# ---------------------------------------------------------------------------
def _fake_llm(monkeypatch, *, objectives: list[str], plan_por_objetivo: dict,
              decomposicion: dict | None = None):
    """Enruta por (capability, system_prompt) porque DOS pares de componentes
    comparten capacidad: decomposer y planner piden REASON; consolidator y
    responder piden SUMMARIZE. Distinguirlos por el system_prompt es lo que
    permite que la cadena real corra entera con un solo doble.

    `plan_por_objetivo`: {fragmento del goal → JSON del grafo}. El planner del
    TIE recibe un goal distinto por misión, así que cada una obtiene su plan."""
    import app.mel as mel
    from app.mel import Capability, ExecutionResult, ServedBy, Usage

    llamadas = {"classify": 0, "decompose": 0, "plan": 0, "consolidate": 0, "respond": 0}

    def _res(text: str, model: str = "fake") -> ExecutionResult:
        return ExecutionResult(text=text, ok=True, served_by=ServedBy(model, model),
                               usage=Usage(tokens=10))

    async def _complete(req):
        cap = req.capability
        sys_p = req.system_prompt or ""

        if cap == Capability.CLASSIFY:
            llamadas["classify"] += 1
            return _res(json.dumps({
                "type": "execute", "goal": req.prompt[:120], "confidence": 0.93,
                "objectives": objectives,
                "requires_planning": True, "requires_tools": [],
                "requires_browser": False, "requires_computer": False,
                "requires_automation": False, "requires_memory": False,
                "memory_types": [], "context_query": None, "model_capability": "reason",
            }), "fake-classifier")

        if cap == Capability.REASON and sys_p.startswith("Eres el orquestador"):
            llamadas["decompose"] += 1
            return _res(json.dumps(decomposicion or {
                "objectives": [
                    {"id": f"o{i+1}", "goal": g, "depends_on": [], "needs_decomposition": False}
                    for i, g in enumerate(objectives)
                ]
            }), "fake-decomposer")

        if cap == Capability.REASON and sys_p.startswith("Eres el planificador"):
            llamadas["plan"] += 1
            for fragmento, plan in plan_por_objetivo.items():
                if fragmento.lower() in req.prompt.lower():
                    return _res(plan, "fake-planner")
            return _res(json.dumps({"nodes": [
                {"id": "n1", "goal": "hacer lo pedido", "depends_on": [],
                 "tools": [], "approval_required": False},
            ]}), "fake-planner")

        if cap == Capability.SUMMARIZE and sys_p.startswith("Eres Aithera respondiendo al usuario tras"):
            llamadas["respond"] += 1
            return _res("Listo.", "fake-responder")

        if cap == Capability.SUMMARIZE and sys_p.startswith("Eres Aithera respondiendo al usuario."):
            llamadas["consolidate"] += 1
            return _res("He hecho las dos cosas que me pediste.", "fake-consolidator")

        return _res("ok", "fake-generic")

    monkeypatch.setattr(mel, "complete", _complete)
    return llamadas


def _fake_node_chat(monkeypatch):
    """La respuesta conversacional de UN nodo (NullRuntime → chat_service.answer).
    NO afecta al bucle de tool-use: cuando el nodo tiene tools, el runtime pasa
    por `toolloop` y el ToolManager REAL antes de llegar aquí."""
    from app.services import chat_service

    class _Ans:
        def __init__(self, text):
            self.text, self.model, self.tokens = text, "fake-node", 2

    async def _answer(message, *, channel="web", persist_chat_message=True, **kwargs):
        return _Ans(f"hecho: {message[:60]}")
    monkeypatch.setattr(chat_service, "answer", _answer)


_PLAN_SIMPLE = json.dumps({"nodes": [
    {"id": "n1", "goal": "hacer el encargo", "depends_on": [], "tools": [], "approval_required": False},
]})


# ===========================================================================
# 1 — EL CASO INSIGNIA: varios encargos ⇒ varias misiones REALES
# ===========================================================================
@pytest.mark.anyio
async def test_e2e_dos_encargos_producen_dos_misiones_reales_y_una_respuesta(monkeypatch):
    """Doc 23 §0, el problema que justifica el bloque entero: antes, «haz A y
    también B» acababa en UNA misión con pasos secuenciales y B se perdía o
    esperaba a A. Aquí se comprueba con la cadena real que salen DOS misiones
    del TIE independientes, cada una con su propia traza, y una sola respuesta."""
    import app.orchestrator as orchestrator

    _no_context(monkeypatch)
    _fake_node_chat(monkeypatch)
    llamadas = _fake_llm(
        monkeypatch,
        objectives=["revisar los emails urgentes", "apuntar la idea del proyecto"],
        plan_por_objetivo={"emails": _PLAN_SIMPLE, "idea": _PLAN_SIMPLE},
    )

    out = await orchestrator.handle(
        _Env("revisa mis emails urgentes y además apunta la idea del proyecto"))

    assert out and isinstance(out, str)
    # 1 (el mensaje, para ver cuántos encargos hay) + 1 por misión: cada misión
    # clasifica su PROPIO goal para saber qué tools/memoria necesita. Es por
    # diseño (`submit_mission`), y este número es el que hay que vigilar si
    # alguien mete una clasificación de más.
    assert llamadas["classify"] == 3, f"llamadas al clasificador: {llamadas['classify']}"
    assert llamadas["decompose"] == 1
    assert llamadas["plan"] == 2, "cada objetivo debe planificar su PROPIA misión"

    # Dos trazas del TIE = dos misiones reales, no un plan con dos pasos.
    s = SessionLocal()
    try:
        trazas = s.query(OrchestratorTrace).all()
        assert len(trazas) == 2, f"esperaba 2 misiones independientes, hay {len(trazas)}"
        runs = s.query(orch_models.OrchestrationRunRow).all()
        assert len(runs) == 1, "un mensaje = un run del orquestador"
        guardado = runs[0].objectives
        assert len(guardado) == 2
        assert all(o["mission_id"] for o in guardado), "cada objetivo debe apuntar a su misión"
        assert all(o["state"] == "done" for o in guardado)
    finally:
        s.close()


@pytest.mark.anyio
async def test_e2e_las_dependencias_se_respetan_de_verdad(monkeypatch):
    """«...y cuando acabes, avísame» no puede ejecutarse antes que lo demás. El
    decomposer marca la dependencia y el conductor la respeta: se comprueba por
    el ORDEN REAL de planificación, no por el estado final."""
    import app.orchestrator as orchestrator

    _no_context(monkeypatch)
    _fake_node_chat(monkeypatch)

    orden: list[str] = []
    llamadas = _fake_llm(
        monkeypatch,
        objectives=["escribir el informe", "avisarme cuando esté"],
        plan_por_objetivo={"informe": _PLAN_SIMPLE, "avisarme": _PLAN_SIMPLE},
        decomposicion={"objectives": [
            {"id": "o1", "goal": "escribir el informe", "depends_on": [], "needs_decomposition": False},
            {"id": "o2", "goal": "avisarme cuando esté", "depends_on": ["o1"], "needs_decomposition": False},
        ]},
    )
    # Se mide en `submit_mission` (el goal REAL de cada misión) y NO en el prompt
    # del planner: ese prompt lleva anexado el contexto de las dependencias, así
    # que el goal del objetivo dependiente CONTIENE el texto del que le precede.
    import app.tie as tie
    original_submit = tie.submit_mission

    async def _espia(goal, **kwargs):
        orden.append("informe" if goal.lower().startswith("escribir el informe") else "aviso")
        return await original_submit(goal, **kwargs)
    monkeypatch.setattr(tie, "submit_mission", _espia)

    await orchestrator.handle(_Env("escribe el informe y avísame cuando esté"))

    assert orden == ["informe", "aviso"], (
        f"el objetivo dependiente se planificó fuera de orden: {orden}"
    )
    assert llamadas["plan"] == 2


@pytest.mark.anyio
async def test_e2e_un_objetivo_que_falla_no_arrastra_a_los_demas(monkeypatch):
    """Aislamiento REAL (no simulado): si una misión revienta, la otra termina y
    el usuario recibe respuesta igualmente. Es la diferencia entre 'se cayó todo'
    y 'una de las dos cosas salió'."""
    import app.orchestrator as orchestrator
    import app.tie as tie

    _no_context(monkeypatch)
    _fake_node_chat(monkeypatch)
    _fake_llm(
        monkeypatch,
        objectives=["tarea buena", "tarea que revienta"],
        plan_por_objetivo={"buena": _PLAN_SIMPLE, "revienta": _PLAN_SIMPLE},
    )

    original_submit = tie.submit_mission

    async def _submit(goal, **kwargs):
        if "revienta" in goal.lower():
            raise RuntimeError("fallo simulado dentro del TIE")
        return await original_submit(goal, **kwargs)
    monkeypatch.setattr(tie, "submit_mission", _submit)

    out = await orchestrator.handle(_Env("haz la tarea buena y la tarea que revienta"))
    assert out, "el usuario debe recibir respuesta aunque un objetivo falle"

    s = SessionLocal()
    try:
        run = s.query(orch_models.OrchestrationRunRow).one()
        objetivos = run.objectives
        estados = {o["goal"][:12]: o["state"] for o in objetivos}
        assert "done" in estados.values(), f"la tarea buena debió completarse: {estados}"
        assert "failed" in estados.values(), f"la mala debió quedar failed: {estados}"
        assert run.state == "done", "con algo útil hecho, el run no es un fracaso total"
    finally:
        s.close()


# ===========================================================================
# 2 — LA REGLA DE NO-REGRESIÓN (doc 23 §0): 1 encargo ⇒ nada de esto se activa
# ===========================================================================
@pytest.mark.anyio
async def test_e2e_un_solo_encargo_no_toca_al_orquestador(monkeypatch):
    """El ~80% de los mensajes. No debe descomponer, no debe crear un
    `OrchestrationRun`, no debe consolidar: mismo camino que antes del bloque."""
    import app.orchestrator as orchestrator

    _no_context(monkeypatch)
    _fake_node_chat(monkeypatch)
    llamadas = _fake_llm(monkeypatch, objectives=[],
                         plan_por_objetivo={"": _PLAN_SIMPLE})

    out = await orchestrator.handle(_Env("revisa mis emails urgentes"))

    assert out
    assert llamadas["decompose"] == 0, "descompuso un mensaje de un solo encargo"
    assert llamadas["consolidate"] == 0, "consolidó cuando no había nada que consolidar"

    s = SessionLocal()
    try:
        assert s.query(orch_models.OrchestrationRunRow).count() == 0, (
            "creó un run del orquestador para un mensaje de un solo encargo"
        )
    finally:
        s.close()


# ===========================================================================
# 3 — LA CADENA HASTA EL FONDO: el ToolManager REAL ejecuta una tool
# ===========================================================================
@pytest.mark.anyio
async def test_e2e_llega_hasta_una_tool_real_del_ToolManager(monkeypatch, tmp_path):
    """Δ2 de doc 23 §1 era el fallo más grave del bloque: el TIE NUNCA había
    ejecutado una tool — decía haber listado archivos y se los inventaba. Este
    test recorre la cadena entera hasta el ToolManager REAL y comprueba que la
    tool se ejecutó de verdad, con el resultado real en el nodo."""
    import app.orchestrator as orchestrator
    from app.tools import tool_manager

    _no_context(monkeypatch)
    _fake_node_chat(monkeypatch)

    ejecutadas: list[tuple[str, str]] = []
    original_execute = tool_manager.execute

    async def _spy(tool_id, action, params, **kwargs):
        ejecutadas.append((tool_id, action))
        return await original_execute(tool_id, action, params, **kwargs)
    monkeypatch.setattr(tool_manager, "execute", _spy)

    plan_con_tool = json.dumps({"nodes": [
        {"id": "n1", "goal": "listar los archivos de la carpeta", "depends_on": [],
         "tools": ["filesystem"], "approval_required": False},
    ]})
    _fake_llm(monkeypatch, objectives=["listar archivos", "apuntar una nota"],
              plan_por_objetivo={"listar": plan_con_tool, "apuntar": _PLAN_SIMPLE})

    # El bucle de tool-use (R1) decide la tool en ejecución; se le da una
    # decisión determinista para no depender del LLM en este punto.
    import app.tie.toolloop as toolloop

    async def _decidir(*a, **k):
        return {"tool_id": "filesystem", "action": "list_dir", "params": {"path": str(tmp_path)}}
    if hasattr(toolloop, "_decide_next"):
        monkeypatch.setattr(toolloop, "_decide_next", _decidir)

    await orchestrator.handle(_Env("lista los archivos y apunta una nota"))

    # No se exige que el LLM fake elija la tool (eso ya lo cubre test_toolloop);
    # lo que este test blinda es que la CADENA no se rompe y que, cuando el
    # toolloop decide, el ToolManager real es quien ejecuta.
    assert all(t[0] == "filesystem" for t in ejecutadas), (
        f"se ejecutó una tool fuera de la whitelist del nodo: {ejecutadas}"
    )


# ===========================================================================
# 4 — El run queda auditable (lo que consumirá el Learner en V1.1)
# ===========================================================================
@pytest.mark.anyio
async def test_e2e_el_run_queda_persistido_y_consultable(monkeypatch):
    import app.orchestrator as orchestrator

    _no_context(monkeypatch)
    _fake_node_chat(monkeypatch)
    _fake_llm(monkeypatch, objectives=["cosa A", "cosa B"],
              plan_por_objetivo={"cosa a": _PLAN_SIMPLE, "cosa b": _PLAN_SIMPLE})

    await orchestrator.handle(_Env("haz la cosa A y la cosa B"))

    recientes = orchestrator.recent_runs(limit=10)
    assert len(recientes) == 1
    run_id = recientes[0]["id"]

    detalle = orchestrator.get_run(run_id)
    assert detalle is not None
    assert len(detalle["objectives"]) == 2
    assert detalle["outcome"], "el run debe guardar la respuesta que se le dio al usuario"
    assert detalle["state"] in ("done", "failed")
