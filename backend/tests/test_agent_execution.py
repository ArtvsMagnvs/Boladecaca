# tests/test_agent_execution.py — R4: agentes reales + frontera de autoridad
# (doc 23 §3·R4, cierra Δ4/Δ5/Δ6)
#
# Los 4 criterios de éxito del sprint, más los casos de seguridad que los
# rodean. Lo único fake es la FRONTERA DEL LLM (`mel.complete`, enrutado por
# capacidad): el ToolManager, el filesystem, el planner, el executor, el bucle de
# tool-use y la BD son REALES — si no, esto no probaría nada de lo que importa.
#
# La prueba clave del sprint es negativa: un agente NO puede usar una herramienta
# que no tiene, ni tocar lo de otro proyecto. Una autoridad que no se comprueba
# no existe.
from __future__ import annotations

import json
import os

import pytest

from app.db.database import (Agent, AgentExecution, Base, OrchestratorTrace,
                             Project, SessionLocal, engine as db_engine)
from app.tie.authority import Authority, orchestrator_of


@pytest.fixture(autouse=True)
def _clean():
    Base.metadata.create_all(bind=db_engine)
    yield
    s = SessionLocal()
    try:
        s.query(AgentExecution).delete()
        s.query(Agent).delete()
        s.query(Project).delete()
        s.query(OrchestratorTrace).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _mk_agent(*, name="Agente", tools=None, project_id=None, role=None) -> int:
    db = SessionLocal()
    try:
        a = Agent(name=name, agent_type="generic", is_active=True,
                  allowed_tools=json.dumps(tools if tools is not None else []),
                  max_execution_time=60, project_id=project_id, role=role)
        db.add(a)
        db.commit()
        db.refresh(a)
        return a.id
    finally:
        db.close()


def _mk_project(*, name="Proyecto", repo_path=None) -> int:
    db = SessionLocal()
    try:
        p = Project(name=name, status="active", repo_path=repo_path)
        db.add(p)
        db.commit()
        db.refresh(p)
        return p.id
    finally:
        db.close()


def _mk_execution(agent_id: int, task: str) -> int:
    db = SessionLocal()
    try:
        e = AgentExecution(agent_id=agent_id, task_description=task, status="pending")
        db.add(e)
        db.commit()
        db.refresh(e)
        return e.id
    finally:
        db.close()


def _fake_llm(monkeypatch, *, plan_tools, agentic_script):
    """Frontera del LLM. `plan_tools` son las tools que el planner PIDE para el
    nodo (a propósito se le deja pedir de más en algún test: así se comprueba que
    el recorte de seguridad no depende de que el modelo se porte bien).
    `agentic_script` es la lista de respuestas del bucle de tool-use, en orden."""
    import app.mel as mel
    from app.mel import Capability, ExecutionResult, ServedBy, Usage

    state = {"agentic_calls": 0, "plan_prompts": []}

    def _res(text: str) -> ExecutionResult:
        return ExecutionResult(text=text, ok=True, served_by=ServedBy("fake", "fake"),
                               usage=Usage(tokens=5))

    async def _complete(req):
        cap = req.capability
        if cap == Capability.CLASSIFY:
            return _res(json.dumps({
                "type": "execute", "goal": "hacer la tarea del agente",
                "domain": [], "confidence": 0.9, "requires_planning": True,
                "requires_tools": [], "requires_browser": False, "requires_computer": False,
                "requires_automation": False, "requires_memory": False,
                "memory_types": [], "context_query": None, "model_capability": "reason",
            }))
        if cap == Capability.REASON:
            state["plan_prompts"].append(req.system_prompt or "")
            return _res(json.dumps({"nodes": [
                {"id": "n1", "goal": "hacer la tarea", "depends_on": [],
                 "tools": plan_tools, "approval_required": False},
            ]}))
        if cap == Capability.AGENTIC:
            i = state["agentic_calls"]
            state["agentic_calls"] += 1
            return _res(agentic_script[min(i, len(agentic_script) - 1)])
        if cap == Capability.SUMMARIZE:
            return _res("Resumen de la misión.")
        return _res("ok")

    monkeypatch.setattr(mel, "complete", _complete)
    return state


def _no_context(monkeypatch):
    from app.tie import enricher as enricher_mod

    async def _enrich(*a, **k):
        return ""
    monkeypatch.setattr(enricher_mod, "enrich", _enrich)
    enricher_mod._cache.clear()


# ===========================================================================
# Criterio 1 — el agente HACE la tarea real (Δ5): ejecuta filesystem de verdad
# ===========================================================================
@pytest.mark.anyio
async def test_agente_ejecuta_la_tarea_real_con_su_tool(monkeypatch, tmp_path):
    from app.agents.agent_manager import agent_manager

    # Carpeta real con 3 archivos: la respuesta tiene que salir de aquí.
    for n in ("uno.txt", "dos.txt", "tres.txt"):
        (tmp_path / n).write_text("x", encoding="utf-8")

    _no_context(monkeypatch)
    _fake_llm(
        monkeypatch,
        plan_tools=["filesystem"],
        agentic_script=[
            json.dumps({"tool": {"tool_id": "filesystem", "action": "list_dir",
                                 "params": {"path": str(tmp_path)}}}),
            json.dumps({"answer": "La carpeta tiene 3 archivos."}),
        ],
    )
    # El FilesystemTool solo deja leer dentro de HOME: se apunta HOME a tmp.
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))

    agent_id = _mk_agent(name="Contador", tools=["filesystem"])
    exec_id = _mk_execution(agent_id, f"cuenta los archivos de {tmp_path}")

    await agent_manager._run_execution(exec_id)

    db = SessionLocal()
    try:
        row = db.get(AgentExecution, exec_id)
        assert row.status == "completed", row.error_message
        # Rastro REAL: se ejecutó la tool, no una demo fija.
        calls = json.loads(row.tool_calls or "[]")
        assert any(c.get("tool_id") == "filesystem" and c.get("action") == "list_dir"
                   and c.get("ok") for c in calls), calls
        # Y ya NO aparece nada del placeholder de V0.5.
        assert "demo V0.5" not in (row.result or "")
    finally:
        db.close()


# ===========================================================================
# Criterio 2 — un agente NO puede usar una tool que no tiene (el corazón de R4)
# ===========================================================================
@pytest.mark.anyio
async def test_agente_sin_filesystem_no_puede_usarlo(monkeypatch, tmp_path):
    from app.agents.agent_manager import agent_manager

    # El agente tiene `git` (para que el bucle SÍ arranque y podamos observar qué
    # hace), pero NO `filesystem`. El planner pide las dos y el bucle intenta
    # usar filesystem igualmente: los dos se comportan mal a propósito.
    state = _fake_llm(
        monkeypatch,
        plan_tools=["git", "filesystem"],
        agentic_script=[
            json.dumps({"tool": {"tool_id": "filesystem", "action": "list_dir",
                                 "params": {"path": str(tmp_path)}}}),
            json.dumps({"answer": "no pude leer la carpeta"}),
        ],
    )
    _no_context(monkeypatch)

    # HOME apunta a tmp: si `filesystem` llegara a ejecutarse, FUNCIONARÍA. Así
    # el test falla si la frontera no actúa, en vez de pasar de rebote porque la
    # ruta estuviera fuera de HOME (que es un rechazo de OTRO mecanismo).
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "hay_un_archivo.txt").write_text("x", encoding="utf-8")

    agent_id = _mk_agent(name="Sin manos", tools=["git"])   # solo git
    exec_id = _mk_execution(agent_id, "lista mis archivos")

    await agent_manager._run_execution(exec_id)

    db = SessionLocal()
    try:
        row = db.get(AgentExecution, exec_id)
        calls = json.loads(row.tool_calls or "[]")
    finally:
        db.close()

    # (a) filesystem NUNCA se ejecutó.
    assert not any(c.get("tool_id") == "filesystem" and c.get("ok") for c in calls), calls
    # (b) Y se rechazó POR LA WHITELIST, no de rebote: hay una denegación
    #     explícita cuyo motivo nombra la frontera. Sin esto, el test pasaría
    #     igual si el paso hubiera fallado por cualquier otra razón.
    denegadas = [c for c in calls if c.get("tool_id") == "filesystem" and c.get("denied")]
    assert denegadas, f"se esperaba una denegación explícita de filesystem: {calls}"
    assert "git" in denegadas[0]["reason"], denegadas[0]["reason"]

    # (c) El recorte fue determinista, no una súplica al modelo: el prompt del
    #     planner solo le ofreció las tools del agente.
    assert state["plan_prompts"], "el planner no llegó a ejecutarse"
    assert "'filesystem'" not in state["plan_prompts"][0]


def test_el_recorte_de_tools_es_por_codigo_no_por_prompt():
    """Aunque el LLM devuelva un nodo con tools que el agente no tiene, el grafo
    que se PERSISTE ya viene recortado. Es lo que hace que una reanudación tras
    reinicio no pueda recuperar permisos que la misión nunca tuvo."""
    from app.tie import graph as graph_mod
    from app.tie.contracts import TaskNode

    authority = Authority(allowed_tools=["git"])
    nodes = [TaskNode(id="n1", goal="x", tools=["git", "shell", "filesystem"])]
    for n in nodes:
        n.tools = [t for t in n.tools if t in authority.allowed_tools]

    g = graph_mod.build("m1", nodes, created_by="planner")
    g.authority = authority.to_dict()

    assert g.nodes["n1"].tools == ["git"]
    # Y sobrevive al round-trip del checkpoint (esto es lo que lee resume_pending).
    from app.tie.contracts import TaskGraph
    revivido = TaskGraph.from_dict(json.loads(json.dumps(g.to_dict())))
    assert revivido.nodes["n1"].tools == ["git"]
    assert Authority.from_dict(revivido.authority).allowed_tools == ["git"]


# ===========================================================================
# Criterio 3 — el AE delega y NO se bloquea (Δ4)
# ===========================================================================
@pytest.mark.anyio
async def test_ae_agent_task_no_bloquea_al_motor(monkeypatch):
    """Una misión puede durar minutos. `AgentTaskAction` tiene que volver
    enseguida — si esperase, congelaría la evaluación de las demás reglas."""
    import asyncio

    import app.tie as tie
    from app.agents.agent_manager import agent_manager
    from app.automation import AgentTaskAction
    from app.automation.triggers import TriggerEvent

    arrancada = asyncio.Event()

    async def _slow_submit(goal, **kwargs):
        arrancada.set()
        await asyncio.sleep(30)      # una misión lenta de verdad
        raise AssertionError("no se debería haber esperado a que terminase")

    monkeypatch.setattr(tie, "submit_mission", _slow_submit)

    agent_id = _mk_agent(name="Lento", tools=["git"])
    res = await asyncio.wait_for(
        AgentTaskAction().execute({"agent_id": agent_id, "task": "haz algo largo"},
                                  TriggerEvent(name="test", event_key="k1")),
        timeout=3.0,     # si bloquease esperando la misión, esto reventaría
    )
    assert res.ok and res.data["execution_id"]

    # La misión SÍ se lanzó (en background), simplemente no se esperó.
    await asyncio.wait_for(arrancada.wait(), timeout=3.0)

    # Limpieza: cortar la tarea de fondo para no dejarla colgando en el teardown.
    for task in list(agent_manager._running_tasks.values()):
        task.cancel()
    agent_manager._running_tasks.clear()


@pytest.mark.anyio
async def test_ae_sin_agent_id_no_lanza_una_mision_sin_frontera():
    """Una regla sin agente produciría una misión SIN whitelist (catálogo
    entero). La regla predefinida `agent_task` (A3) nace con `agent_id=None`, así
    que esto es lo que la mantiene inofensiva si alguien la activa sin
    configurarla."""
    from app.automation import AgentTaskAction
    from app.automation.triggers import TriggerEvent

    res = await AgentTaskAction().execute({"task": "haz algo"},
                                          TriggerEvent(name="test", event_key="k0"))
    assert res.ok is False
    assert "agent_id" in res.detail


@pytest.mark.anyio
async def test_ae_con_agent_id_pasa_por_el_agente(monkeypatch):
    """Con `agent_id`, el AE delega a través del agente — que es lo que aplica su
    whitelist. Saltárselo sería darle a la regla más permisos que al agente."""
    from app.automation import AgentTaskAction
    from app.automation.triggers import TriggerEvent
    from app.agents.agent_manager import agent_manager

    visto = {}

    def _create_execution(agent_id, task):
        visto["agent_id"] = agent_id
        visto["task"] = task

        class _E:
            id = 4242
        return _E()

    monkeypatch.setattr(agent_manager, "create_execution", _create_execution)

    agent_id = _mk_agent(name="Delegado", tools=["git"])
    res = await AgentTaskAction().execute(
        {"agent_id": agent_id, "task": "revisa el repo"},
        TriggerEvent(name="test", event_key="k2"),
    )
    assert res.ok and res.data["execution_id"] == 4242
    assert visto["agent_id"] == agent_id


# ===========================================================================
# Criterio 4 — el orquestador de proyecto no puede tocar otro proyecto (Δ6)
# ===========================================================================
def test_orquestador_no_puede_tocar_agentes_de_otro_proyecto():
    proyecto_a = _mk_project(name="Proyecto A")
    proyecto_b = _mk_project(name="Proyecto B")
    ajeno = _mk_agent(name="Agente de B", tools=[], project_id=proyecto_b)
    propio = _mk_agent(name="Agente de A", tools=[], project_id=proyecto_a)

    authority = Authority(project_id=proyecto_a, allowed_tools=["aithera"])

    # Sobre el suyo: adelante.
    assert authority.check("aithera", "run_agent_task",
                           {"agent_id": propio, "task": "x"}) is None

    # Sobre el de otro proyecto: DENEGADO, y con un motivo que lo explica.
    razon = authority.check("aithera", "run_agent_task", {"agent_id": ajeno, "task": "x"})
    assert razon is not None
    assert str(ajeno) in razon


def test_orquestador_no_puede_crear_cosas_en_otro_proyecto():
    authority = Authority(project_id=7, allowed_tools=["aithera"])
    assert authority.check("aithera", "create_task",
                           {"project_id": 7, "title": "x"}) is None
    assert authority.check("aithera", "create_task",
                           {"project_id": 8, "title": "x"}) is not None


def test_agente_inexistente_se_deniega_fail_closed():
    """Un `agent_id` que no existe no puede colarse. [2026-08-02] El motivo ya
    no es "su proyecto es None" — desde el fix del huérfano, no tener proyecto
    SÍ se permite (ver `test_agente_huerfano.py`); lo que deniega aquí es que
    la fila no se pudo leer, que es un caso distinto. Fail-closed igual que A3b."""
    authority = Authority(project_id=1, allowed_tools=["aithera"])
    assert authority.check("aithera", "assign_tools",
                           {"agent_id": 999999, "allowed_tools": []}) is not None


def test_orchestrator_of_encuentra_solo_el_del_proyecto():
    proyecto = _mk_project(name="Con jefe", repo_path="C:/repos/x")
    _mk_agent(name="Peón", tools=["git"], project_id=proyecto)
    jefe = _mk_agent(name="Jefe", tools=["aithera", "git"],
                     project_id=proyecto, role="orchestrator")

    found = orchestrator_of(proyecto)
    assert found is not None
    assert found["id"] == jefe
    assert set(found["allowed_tools"]) == {"aithera", "git"}
    assert found["repo_path"] == "C:/repos/x"

    # Un proyecto sin orquestador no inventa uno.
    assert orchestrator_of(_mk_project(name="Sin jefe")) is None


@pytest.mark.anyio
async def test_la_mision_de_un_proyecto_adopta_el_alcance_de_su_orquestador(monkeypatch):
    """Δ6: si el proyecto tiene orquestador, la misión se enruta a él y hereda su
    whitelist — sin que el caller tenga que saberlo."""
    import app.tie as tie

    proyecto = _mk_project(name="Con jefe", repo_path="C:/repos/x")
    _mk_agent(name="Jefe", tools=["git"], project_id=proyecto, role="orchestrator")

    capturado = {}

    async def _fake_complex(text, intent, mission, trace_id, context, *, force_model=None, authority=None):
        capturado["authority"] = authority
        mission.outcome = "ok"

    from app.tie import pipeline as pipeline_mod
    monkeypatch.setattr(pipeline_mod, "_complex_path", _fake_complex)
    _no_context(monkeypatch)
    _fake_llm(monkeypatch, plan_tools=[], agentic_script=['{"answer":"x"}'])

    await tie.submit_mission("haz algo del proyecto", source="workspace", project_id=proyecto)

    auth = capturado["authority"]
    assert auth.allowed_tools == ["git"]
    assert auth.project_id == proyecto
    assert auth.repo_path == "C:/repos/x"


# ===========================================================================
# No-regresión: el chat del usuario NO tiene frontera
# ===========================================================================
def test_sin_autoridad_no_hay_restriccion():
    a = Authority()
    assert a.is_unrestricted
    assert a.check("shell", "run_command", {"command": "python -V"}) is None
    assert a.check("filesystem", "read_file", {"path": "C:/cualquier/sitio.txt"}) is None


def test_rutas_fuera_del_repo_se_deniegan():
    a = Authority(repo_path=os.path.join("C:", os.sep, "repos", "mio"))
    dentro = os.path.join("C:", os.sep, "repos", "mio", "src", "x.py")
    fuera = os.path.join("C:", os.sep, "repos", "otro", "x.py")
    assert a.check("filesystem", "read_file", {"path": dentro}) is None
    assert a.check("filesystem", "read_file", {"path": fuera}) is not None
    # Un prefijo parecido NO es un hijo ("…/mio-copia" no está dentro de "…/mio").
    hermano = os.path.join("C:", os.sep, "repos", "mio-copia", "x.py")
    assert a.check("filesystem", "read_file", {"path": hermano}) is not None
    # Y el `..` tampoco cuela.
    traversal = os.path.join("C:", os.sep, "repos", "mio", "..", "otro", "x.py")
    assert a.check("filesystem", "read_file", {"path": traversal}) is not None


def test_documentos_fuera_del_repo_se_deniegan():
    """[2026-07-27, doc 34] Regresión del bug reportado en vivo: un agente del
    proyecto "Cordyceps" con carpeta asignada escribió `Cordyceps_Wiki.docx`
    fuera de esa carpeta porque `document` no estaba en `_PATH_PARAMS`. Mismo
    caso que `filesystem`, pero con la tool de documentos de oficina."""
    a = Authority(repo_path=os.path.join("C:", os.sep, "repos", "cordyceps"))
    dentro = os.path.join("C:", os.sep, "repos", "cordyceps", "wiki.docx")
    fuera = os.path.join("C:", os.sep, "Users", "Alejandro", "Cordyceps_Wiki.docx")
    assert a.check("document", "write_docx", {"path": dentro}) is None
    assert a.check("document", "write_docx", {"path": fuera}) is not None
    # Lectura también queda dentro de la carpeta, no solo la escritura.
    assert a.check("document", "read_pdf", {"path": fuera}) is not None


def test_descargas_fuera_del_repo_se_deniegan():
    """`download.download_url` baja archivos a disco igual que `filesystem.
    write_file` — mismo alcance de carpeta."""
    a = Authority(repo_path=os.path.join("C:", os.sep, "repos", "cordyceps"))
    dentro = os.path.join("C:", os.sep, "repos", "cordyceps", "logo.png")
    fuera = os.path.join("C:", os.sep, "Users", "Alejandro", "Downloads", "logo.png")
    assert a.check("download", "download_url", {"url": "https://x.com/logo.png", "path": dentro}) is None
    assert a.check("download", "download_url", {"url": "https://x.com/logo.png", "path": fuera}) is not None


def test_browser_solo_restringe_descarga_no_navegacion():
    """`browser` solo queda acotado por carpeta en sus acciones que escriben a
    disco (`download_file`/`upload_file`, único parámetro `path`); navegar,
    hacer clic o buscar en la web sigue sin restricción — internet es externo
    por naturaleza, el disco local no (petición explícita del usuario)."""
    a = Authority(repo_path=os.path.join("C:", os.sep, "repos", "cordyceps"))
    fuera = os.path.join("C:", os.sep, "Users", "Alejandro", "descarga.pdf")
    # Descargar a disco SÍ queda acotado a la carpeta del proyecto.
    assert a.check("browser", "download_file", {"tab_id": "t1", "selector": "a", "path": fuera}) is not None
    # Navegar, buscar y hacer clic NO tienen `path`: sin restricción de carpeta.
    assert a.check("browser", "open_url", {"tab_id": "t1", "url": "https://youtube.com"}) is None
    assert a.check("browser", "google_search", {"tab_id": "t1", "query": "cordyceps"}) is None
    assert a.check("browser", "click", {"tab_id": "t1", "selector": "#play"}) is None


# ---------------------------------------------------------------------------
# [FIX 2026-08-02] Ejecuciones huerfanas de un reinicio del backend
#
# EL FALLO REAL (reportado por el usuario): en la tarjeta del proyecto
# Cordyceps, el orquestador y el investigador salian "escribiendo…" sin parar.
# La UI pinta ese indicador con `pending`/`running` (W2e), y en la BD real habia
# dos filas asi: una desde hacia CINCO DIAS.
#
# `running` significa "hay una asyncio.Task viva trabajando en esto". Tras
# reiniciar el backend eso es falso para TODAS, porque el proceso que las
# llevaba ya no existe — pero nadie tocaba la fila. El TIE ya reconciliaba sus
# misiones al arrancar (`executor.resume_pending`, T3); las ejecuciones de
# agente no tenian equivalente.
# ---------------------------------------------------------------------------
def _mk_execution(agent_id: int, status: str) -> int:
    db = SessionLocal()
    try:
        ex = AgentExecution(agent_id=agent_id, task_description="tarea", status=status)
        db.add(ex)
        db.commit()
        db.refresh(ex)
        return ex.id
    finally:
        db.close()


def _status_of(execution_id: int) -> str:
    db = SessionLocal()
    try:
        return db.query(AgentExecution).filter(AgentExecution.id == execution_id).first().status
    finally:
        db.close()


def test_una_ejecucion_colgada_de_un_reinicio_se_cierra_al_arrancar():
    """La reproduccion exacta: la fila decia 'running' y el agente salia
    'escribiendo…' indefinidamente."""
    from app.agents.agent_manager import agent_manager

    aid = _mk_agent(name="Orquestador de prueba")
    corriendo = _mk_execution(aid, "running")
    esperando = _mk_execution(aid, "pending")

    cerradas = agent_manager.reconcile_orphan_executions()

    assert cerradas == 2
    assert _status_of(corriendo) == "failed"
    assert _status_of(esperando) == "failed"


def test_no_toca_las_ejecuciones_ya_terminadas():
    """Cero regresion sobre el historial: lo que ya acabo no se reescribe."""
    from app.agents.agent_manager import agent_manager

    aid = _mk_agent(name="Agente con historial")
    ok = _mk_execution(aid, "completed")
    ko = _mk_execution(aid, "failed")
    cancelada = _mk_execution(aid, "cancelled")

    agent_manager.reconcile_orphan_executions()

    assert _status_of(ok) == "completed"
    assert _status_of(ko) == "failed"
    assert _status_of(cancelada) == "cancelled"


def test_la_ejecucion_cerrada_explica_por_que():
    """Honestidad: el usuario tiene que poder distinguir "fallo la tarea" de
    "se corto el backend a media faena"."""
    from app.agents.agent_manager import agent_manager

    aid = _mk_agent(name="Agente interrumpido")
    eid = _mk_execution(aid, "running")

    agent_manager.reconcile_orphan_executions()

    db = SessionLocal()
    try:
        ex = db.query(AgentExecution).filter(AgentExecution.id == eid).first()
        assert "reinici" in (ex.error_message or "").lower()
        assert ex.completed_at is not None
    finally:
        db.close()


def test_sin_huerfanas_no_hace_nada():
    """Idempotente: pasarla dos veces seguidas no cambia nada la segunda."""
    from app.agents.agent_manager import agent_manager

    aid = _mk_agent(name="Agente limpio")
    _mk_execution(aid, "running")

    assert agent_manager.reconcile_orphan_executions() == 1
    assert agent_manager.reconcile_orphan_executions() == 0
