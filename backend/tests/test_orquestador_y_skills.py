# tests/test_orquestador_y_skills.py — puntos 1, 2 y 5 (2026-08-02)
#
# Los tres fallos reportados por el usuario:
#   (2) el orquestador creaba agentes SIN skills y volcaba todo el diseño en la
#       descripción — no era terquedad: nunca vio el catálogo de 254 nombres.
#   (5) el orquestador nacía con 2 tools, se le podían quitar, y se podía borrar.
#   (1) los agentes no se podían eliminar desde su ficha.
from __future__ import annotations

import json

import pytest

from app.agents.agent_manager import agent_manager
from app.db.database import (Agent, AgentExecution, Base, Project, SessionLocal,
                             engine as db_engine)
from app.tie.authority import ensure_orchestrator, orchestrator_tools
from app.tools.aithera_tool import AitheraTool


@pytest.fixture(autouse=True)
def _clean():
    Base.metadata.create_all(bind=db_engine)
    _wipe()
    yield
    _wipe()


def _wipe():
    s = SessionLocal()
    try:
        s.query(AgentExecution).delete()
        s.query(Agent).delete()
        s.query(Project).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


def _mk_project(name="Cordyceps", repo=None) -> int:
    db = SessionLocal()
    try:
        p = Project(name=name, status="active", repo_path=repo)
        db.add(p)
        db.commit()
        db.refresh(p)
        return p.id
    finally:
        db.close()


# ===========================================================================
# 2 — El catálogo de skills se puede CONSULTAR (la causa raíz)
# ===========================================================================
class TestBuscarSkills:
    @pytest.mark.anyio
    async def test_busca_por_tecnologia(self):
        r = await AitheraTool().execute("search_skills", {"query": "unity"})
        assert r["success"], r
        nombres = [s["name"] for s in r["result"]["skills"]]
        assert nombres, "no encontró ninguna skill de Unity"
        assert any("Unity" in n for n in nombres)

    @pytest.mark.anyio
    async def test_busca_por_categoria(self):
        r = await AitheraTool().execute("search_skills", {"query": "game"})
        nombres = [s["name"] for s in r["result"]["skills"]]
        assert nombres and "categoría" in (r["result"]["found_in"] or "")

    @pytest.mark.anyio
    async def test_sin_resultados_orienta_en_vez_de_dejarte_a_ciegas(self):
        r = await AitheraTool().execute("search_skills", {"query": "zzzzqqq"})
        assert r["success"]
        assert r["result"]["skills"] == []
        # Lo importante: se le dicen las categorías reales para reintentar.
        assert r["result"]["categories"], "no ofreció ninguna vía de salida"

    @pytest.mark.anyio
    async def test_sin_query_lo_dice(self):
        r = await AitheraTool().execute("search_skills", {})
        assert r["success"] is False and "query" in r.get("missing", [])

    @pytest.mark.anyio
    async def test_el_circulo_completo_buscar_luego_crear(self):
        """Lo que el orquestador NO podía hacer: buscar skills reales y crear
        el agente con ellas, sin inventarse nombres ni rendirse."""
        tool = AitheraTool()
        pid = _mk_project()
        encontradas = (await tool.execute("search_skills", {"query": "unity", "limit": 3}))["result"]["skills"]
        nombres = [s["name"] for s in encontradas]

        r = await tool.execute("create_agent", {
            "name": "CordycepsDev", "project_id": pid, "skills": nombres,
            "allowed_tools": ["filesystem", "document"],
        })
        assert r["success"], r
        db = SessionLocal()
        try:
            agente = db.get(Agent, r["result"]["id"])
            assert agente.skills == nombres, "las skills no llegaron a la BD"
        finally:
            db.close()


# ===========================================================================
# 5 — El orquestador: todas las tools, y no se le quitan ni se borra
# ===========================================================================
class TestOrquestador:
    def test_nace_con_todas_las_tools(self):
        pid = _mk_project(repo="C:/repos/cordyceps")
        orq = ensure_orchestrator(pid)
        assert orq is not None
        assert set(orq["allowed_tools"]) == set(orchestrator_tools())
        # Decisión explícita del usuario: shell incluido.
        assert "shell" in orq["allowed_tools"]
        assert "aithera" in orq["allowed_tools"]
        # Y sigue encerrado en la carpeta del proyecto.
        assert orq["repo_path"] == "C:/repos/cordyceps"

    def test_un_orquestador_viejo_se_re_sincroniza(self):
        """Los proyectos creados antes de esta decisión tienen el orquestador
        con 2 tools. Sin re-sincronizar se quedarían mutilados para siempre."""
        pid = _mk_project()
        viejo = agent_manager.create_agent(
            name="Orquestador antiguo", agent_type="orchestrator",
            allowed_tools=["filesystem", "document"], project_id=pid, role="orchestrator")

        orq = ensure_orchestrator(pid)
        assert orq["id"] == viejo.id, "creó otro en vez de arreglar el que había"
        assert set(orq["allowed_tools"]) == set(orchestrator_tools())

    def test_no_se_le_pueden_quitar_tools(self):
        pid = _mk_project()
        orq = ensure_orchestrator(pid)
        with pytest.raises(ValueError, match="no se le pueden quitar"):
            agent_manager.update_agent(orq["id"], allowed_tools=["filesystem"])
        # Pero editar OTRA cosa sigue funcionando.
        assert agent_manager.update_agent(orq["id"], description="nueva") is not None

    def test_no_se_puede_borrar(self):
        pid = _mk_project()
        orq = ensure_orchestrator(pid)
        with pytest.raises(ValueError, match="no se puede eliminar"):
            agent_manager.delete_agent(orq["id"])
        assert agent_manager.get_agent(orq["id"]) is not None

    @pytest.mark.anyio
    async def test_el_chat_recibe_un_motivo_legible_al_intentar_borrarlo(self):
        pid = _mk_project()
        orq = ensure_orchestrator(pid)
        r = await AitheraTool().execute("delete_agent", {"agent_id": orq["id"]})
        assert r["success"] is False
        assert "orquestador" in r["error"] and "no se puede eliminar" in r["error"]


# ===========================================================================
# 1 — Un agente NORMAL sí se borra
# ===========================================================================
class TestBorrarAgente:
    def test_un_agente_normal_se_borra(self):
        pid = _mk_project()
        a = agent_manager.create_agent(name="Peón", project_id=pid)
        assert agent_manager.delete_agent(a.id) is True
        assert agent_manager.get_agent(a.id) is None

    def test_borrar_uno_que_no_existe_devuelve_false_no_revienta(self):
        assert agent_manager.delete_agent(999999) is False

    @pytest.mark.anyio
    async def test_el_endpoint_distingue_no_existe_de_no_se_puede(self):
        from fastapi.testclient import TestClient

        from app.main import app

        pid = _mk_project()
        orq = ensure_orchestrator(pid)
        normal = agent_manager.create_agent(name="Normal", project_id=pid)
        with TestClient(app) as client:
            assert client.delete(f"/api/agents/{orq['id']}").status_code == 409
            assert client.delete(f"/api/agents/{normal.id}").status_code == 204
            assert client.delete("/api/agents/999999").status_code == 404


# ===========================================================================
# Autonomía POR AGENTE + carpetas extra (2026-08-02, decisión del usuario)
# ===========================================================================
# «Esas dos tools (shell/powershell), el agente u orquestador que quiera
# usarlas pedirá permiso. Pero [...] un selector con "Aprobar manualmente" y
# "Omitir todas las aprobaciones", para decidir en cada orquestador y en cada
# agente si quiere que le pregunten o si quiere full automático.»
class TestAutonomiaPorAgente:
    def test_por_defecto_pregunta(self):
        from app.tie.authority import Authority

        assert Authority().auto_approves is False
        assert Authority(autonomy="manual").auto_approves is False

    def test_en_auto_no_pregunta(self):
        from app.tie.authority import Authority

        assert Authority(autonomy="auto").auto_approves is True
        assert Authority(autonomy="AUTO").auto_approves is True   # tolerante

    def test_viaja_en_el_checkpoint(self):
        """La autonomía tiene que sobrevivir a un reinicio: viaja dentro de
        `Authority`, que es lo que el executor persiste en el grafo."""
        from app.tie.authority import Authority

        a = Authority(project_id=1, autonomy="auto", extra_paths=["/tmp/x"])
        b = Authority.from_dict(a.to_dict())
        assert b.auto_approves is True
        assert b.extra_paths == ["/tmp/x"]

    @pytest.mark.anyio
    async def test_en_auto_se_concede_y_QUEDA_RASTRO(self, monkeypatch):
        """La regla de oro de A3b: automático NUNCA significa silencioso."""
        from app.tie import toolloop

        registrados: list = []

        class GateFalso:
            async def request_approval(self, **kw):
                registrados.append(kw)
                return "gate-1"

            async def resolve(self, gate_id, approved, note=""):
                registrados.append({"resolve": gate_id, "approved": approved, "note": note})

        ok, motivo = await toolloop._ask_permission(
            {"tool_id": "shell", "action": "run"}, {}, GateFalso(),
            instruction="compila el proyecto", agent_auto=True)

        assert ok is True and "no preguntar" in motivo
        assert any("resolve" in r for r in registrados), "se concedió SIN dejar rastro"
        assert any(r.get("approved") is True for r in registrados if "resolve" in r)


class TestCarpetasExtra:
    def test_una_carpeta_extra_amplia_la_del_proyecto(self, tmp_path):
        from app.tie.authority import Authority

        proyecto = tmp_path / "repo"
        extra = tmp_path / "otra"
        proyecto.mkdir()
        extra.mkdir()

        a = Authority(project_id=1, repo_path=str(proyecto), allowed_tools=["filesystem"],
                      extra_paths=[str(extra)])
        # Dentro del proyecto: siempre.
        assert a.check("filesystem", "write_file", {"path": str(proyecto / "a.txt")}) is None
        # Dentro de la carpeta concedida a mano: también.
        assert a.check("filesystem", "write_file", {"path": str(extra / "b.txt")}) is None
        # Fuera de las dos: NO.
        assert a.check("filesystem", "write_file", {"path": str(tmp_path / "c.txt")}) is not None

    def test_sin_carpetas_extra_el_comportamiento_no_cambia(self, tmp_path):
        from app.tie.authority import Authority

        proyecto = tmp_path / "repo"
        proyecto.mkdir()
        a = Authority(project_id=1, repo_path=str(proyecto), allowed_tools=["filesystem"])
        assert a.check("filesystem", "write_file", {"path": str(proyecto / "a.txt")}) is None
        assert a.check("filesystem", "write_file", {"path": str(tmp_path / "fuera.txt")}) is not None
