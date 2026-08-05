# tests/test_project_orchestrator.py — [hotfix 2026-08-02] El orquestador DE UN
# PROYECTO: que exista de verdad, y que su autoridad esté acotada.
#
# EL HUECO QUE CIERRA (reportado por el usuario): "en teoría los proyectos cada
# uno tiene su orquestrator, pero no hay un chat general en el proyecto para
# hablar con el orquestrator de ese proyecto". Era literal: `Agent.role=
# "orchestrator"` (W2e) y el enrutado de `submit_mission` hacia el orquestador
# (R4) existían desde hacía versiones, pero NADA creaba nunca un agente con ese
# rol — la ruta estaba escrita y muerta. `ensure_orchestrator` la materializa.
#
# Los tests negativos son los que importan: el usuario pidió que el orquestador
# "SOLO pueda dar órdenes a los agentes de ese proyecto y trabajar sobre la
# carpeta del proyecto". Una frontera que no se comprueba no existe.
from __future__ import annotations

import os
import tempfile

import pytest

from app.agents.agent_manager import agent_manager
from app.db.database import (Agent, AgentExecution, Base, OrchestratorTrace,
                             Project, SessionLocal, engine as db_engine)
from app.tie.authority import Authority, ensure_orchestrator, orchestrator_of


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


def _project(name: str = "Proyecto", repo: str | None = None) -> tuple[int, str]:
    repo = repo or tempfile.mkdtemp()
    s = SessionLocal()
    try:
        p = Project(name=name, repo_path=repo)
        s.add(p)
        s.commit()
        s.refresh(p)
        return p.id, repo
    finally:
        s.close()


# ---------------------------------------------------------------------------
# 1) Existir: crearlo si no está, y NO duplicarlo si ya está
# ---------------------------------------------------------------------------
def test_ensure_crea_el_orquestador_si_no_existe():
    pid, repo = _project("Con orquestador")
    assert orchestrator_of(pid) is None, "de partida un proyecto no tiene orquestador"

    orch = ensure_orchestrator(pid)
    assert orch is not None
    assert orch["repo_path"] == repo, "hereda la carpeta del proyecto"
    # Las mínimas del encargo: trabajar sobre la carpeta. Mandar sobre sus
    # agentes NO necesita permiso listado (`aithera` es interna) — ver test 4.
    # [2026-08-02] El contrato CAMBIÓ por decisión explícita del usuario: el
    # orquestador tiene SIEMPRE todas las herramientas (antes eran 2). Su
    # alcance lo limita la carpeta del proyecto, no la lista de tools.
    from app.tie import orchestrator_tools

    assert set(orch["allowed_tools"]) == set(orchestrator_tools())

    s = SessionLocal()
    try:
        agent = s.query(Agent).filter(Agent.id == orch["id"]).first()
        assert agent.role == "orchestrator"
        assert agent.project_id == pid
        assert agent.is_active is True
    finally:
        s.close()


def test_ensure_es_idempotente():
    pid, _ = _project()
    primero = ensure_orchestrator(pid)
    segundo = ensure_orchestrator(pid)
    assert primero["id"] == segundo["id"]

    s = SessionLocal()
    try:
        n = s.query(Agent).filter(Agent.project_id == pid, Agent.role == "orchestrator").count()
    finally:
        s.close()
    assert n == 1, "una segunda llamada no puede crear un orquestador nuevo"


def test_ensure_reutiliza_el_orquestador_existente_y_le_completa_las_tools():
    """[2026-08-02] Antes este test afirmaba que `ensure` NO tocaba un
    orquestador ya creado. El contrato cambió: al orquestador no se le pueden
    quitar herramientas, así que uno anterior (con 2) se RE-SINCRONIZA en vez de
    quedarse mutilado para siempre. Lo que no cambia: no se crea otro."""
    from app.tie import orchestrator_tools

    pid, _ = _project()
    mio = agent_manager.create_agent(
        name="Mi jefe", project_id=pid, role="orchestrator", allowed_tools=["filesystem", "search"],
    )
    orch = ensure_orchestrator(pid)
    assert orch["id"] == mio.id, "creó otro en vez de reutilizar el que había"
    assert set(orch["allowed_tools"]) == set(orchestrator_tools())


def test_ensure_con_proyecto_inexistente_no_explota():
    assert ensure_orchestrator(987654) is None


# ---------------------------------------------------------------------------
# 2) La frontera — los tests que de verdad importan
# ---------------------------------------------------------------------------
def _authority_of(orch: dict, pid: int) -> Authority:
    """La MISMA autoridad que arma `submit_mission` al enrutar al orquestador."""
    return Authority(project_id=pid, repo_path=orch["repo_path"],
                     allowed_tools=orch["allowed_tools"])


def test_orquestador_manda_sobre_los_agentes_de_su_proyecto():
    pid, _ = _project()
    orch = ensure_orchestrator(pid)
    propio = agent_manager.create_agent(name="obrero", project_id=pid, allowed_tools=["filesystem"])
    auth = _authority_of(orch, pid)

    # `aithera` es INTERNA: no necesita estar en la whitelist para usarse.
    assert auth.check("aithera", "list_agents", {}) is None
    assert auth.check("aithera", "run_agent_task", {"agent_id": propio.id}) is None


def test_orquestador_NO_manda_sobre_agentes_de_otro_proyecto():
    pid_a, _ = _project("A")
    pid_b, _ = _project("B")
    orch_a = ensure_orchestrator(pid_a)
    ajeno = agent_manager.create_agent(name="obrero B", project_id=pid_b, allowed_tools=["filesystem"])

    motivo = _authority_of(orch_a, pid_a).check("aithera", "run_agent_task", {"agent_id": ajeno.id})
    assert motivo and "no pertenece a este proyecto" in motivo


def test_orquestador_NO_escribe_fuera_de_la_carpeta_del_proyecto():
    pid_a, repo_a = _project("A")
    _, repo_b = _project("B")
    auth = _authority_of(ensure_orchestrator(pid_a), pid_a)

    dentro = auth.check("filesystem", "write_file", {"path": os.path.join(repo_a, "notas.txt")})
    assert dentro is None, "dentro de su carpeta sí puede"

    fuera = auth.check("filesystem", "write_file", {"path": os.path.join(repo_b, "notas.txt")})
    assert fuera and "fuera de las carpetas" in fuera

    # `document` también (es la tool del caso real de S10: el .docx que acabó
    # en C:\Users\... en vez de dentro del proyecto).
    doc = auth.check("document", "write_docx", {"path": os.path.expanduser("~/fuera.docx")})
    assert doc and "fuera de las carpetas" in doc


def test_la_frontera_de_tools_sigue_existiendo_para_los_demas():
    """[2026-08-02] El orquestador ya las tiene TODAS, así que el caso negativo
    se prueba donde sigue aplicando: un agente normal con una whitelist corta.
    La frontera no desapareció, solo dejó de afectar al orquestador."""
    from app.tie.authority import Authority

    pid, _ = _project()
    auth = Authority(project_id=pid, allowed_tools=["filesystem"])
    motivo = auth.check("browser", "open_url", {"url": "https://x.com"})
    assert motivo and "fuera de las herramientas" in motivo


def test_el_orquestador_si_puede_usar_cualquier_tool():
    pid, _ = _project()
    auth = _authority_of(ensure_orchestrator(pid), pid)
    for tool, accion, params in [("browser", "open_url", {"url": "https://x.com"}),
                                 ("shell", "run", {"command": "python --version"}),
                                 ("search", "search_web", {"query": "x"})]:
        assert auth.check(tool, accion, params) is None, f"{tool} denegada al orquestador"


# ---------------------------------------------------------------------------
# 3) El endpoint que consume el chat del proyecto
# ---------------------------------------------------------------------------
def test_endpoint_devuelve_el_orquestador_y_es_idempotente(client):
    pid, _ = _project("Con chat")

    r1 = client.post(f"/api/projects/{pid}/orchestrator")
    assert r1.status_code == 200, r1.text
    body = r1.json()
    assert body["role"] == "orchestrator"
    assert body["project_id"] == pid
    from app.tie import orchestrator_tools

    assert set(body["allowed_tools"]) == set(orchestrator_tools())

    r2 = client.post(f"/api/projects/{pid}/orchestrator")
    assert r2.status_code == 200
    assert r2.json()["id"] == body["id"], "el endpoint no crea uno nuevo en cada llamada"


def test_endpoint_404_si_el_proyecto_no_existe(client):
    assert client.post("/api/projects/987654/orchestrator").status_code == 404
