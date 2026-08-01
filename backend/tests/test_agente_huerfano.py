# tests/test_agente_huerfano.py — el caso "CordycepsDev" (2026-08-02)
#
# EL FALLO REAL, tal como lo reportó el usuario: le pidió al orquestador del
# proyecto Cordyceps que creara un agente de desarrollo de videojuegos. La
# misión acabó con (a) un agente HUÉRFANO (sin `project_id`) que su propio
# creador ya no podía configurar, (b) un nodo con el check verde cuyo texto
# decía "No he podido completar el objetivo del paso", (c) otro nodo cuyo
# "resultado" eran dos líneas de JSON crudo, y (d) un resumen final que
# afirmaba que todo había ido bien. Cuatro causas independientes, una por
# bloque de este archivo.
#
# Lo único fake aquí es la BD de tests (SQLite del conftest); `Authority`, el
# `AgentManager`, `aithera_tool` y `_extract_json` son los REALES.
from __future__ import annotations

import json

import pytest

from app.agents.agent_manager import agent_manager
from app.core.grounding import is_surrender
from app.db.database import (Agent, AgentExecution, Base, Project, SessionLocal,
                             engine as db_engine)
from app.tie.authority import Authority
from app.tie.intents import _extract_json
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


def _mk_project(name="Cordyceps") -> int:
    db = SessionLocal()
    try:
        p = Project(name=name, status="active")
        db.add(p)
        db.commit()
        db.refresh(p)
        return p.id
    finally:
        db.close()


def _agent_row(agent_id: int):
    db = SessionLocal()
    try:
        return db.get(Agent, agent_id)
    finally:
        db.close()


# ===========================================================================
# A — dos tool-calls en un mismo mensaje ya no dejan JSON crudo en el log
# ===========================================================================
class TestExtraccionDeJsonMultiple:
    def test_dos_objetos_sueltos_se_resuelven_al_primero(self):
        """La repro EXACTA del nodo 2 del log del usuario."""
        texto = (
            "Voy a explorar primero qué skills existen realmente en el catálogo.\n\n"
            '{"tool": {"tool_id": "aithera", "action": "list_agents", "params": {"project_id": 17}}}\n'
            '{"tool": {"tool_id": "aithera", "action": "list_agents", "params": {}}}'
        )
        data = _extract_json(texto)
        assert data is not None, "el mensaje tenía tool-calls válidos y se trató como prosa"
        assert data["tool"]["action"] == "list_agents"
        assert data["tool"]["params"] == {"project_id": 17}

    def test_objeto_anidado_profundo_no_se_corta_a_medias(self):
        texto = ('{"tool": {"tool_id": "a", "action": "b", "params": {"x": {"y": {"z": 1}}}}}\n'
                 '{"tool": {"tool_id": "c", "action": "d"}}')
        assert _extract_json(texto)["tool"]["params"] == {"x": {"y": {"z": 1}}}

    def test_llaves_dentro_de_una_cadena_no_confunden_el_conteo(self):
        texto = '{"answer": "usa {esto} y \\"{aquello}\\""}\n{"tool": {"tool_id": "z", "action": "w"}}'
        assert _extract_json(texto)["answer"].startswith("usa {esto}")

    # --- no-regresión de los caminos que YA funcionaban ---
    @pytest.mark.parametrize("texto,esperado", [
        ('{"tool": {"tool_id": "a", "action": "b"}}', {"tool": {"tool_id": "a", "action": "b"}}),
        ('```json\n{"answer": "hola"}\n```', {"answer": "hola"}),
        ('[{"tool": {"tool_id": "a", "action": "b"}}, {"tool": {"tool_id": "c", "action": "d"}}]',
         {"tool": {"tool_id": "a", "action": "b"}}),
        ('[TOOL_CALL]\n{tool: {"tool_id": "a", "action": "b"}}\n[/TOOL_CALL]',
         {"tool": {"tool_id": "a", "action": "b"}}),
    ])
    def test_no_regresion(self, texto, esperado):
        assert _extract_json(texto) == esperado

    @pytest.mark.parametrize("texto", ["No hay ningún json aquí.", 'texto {"tool": {"tool_id": "a"', ""])
    def test_sin_json_sigue_siendo_none(self, texto):
        assert _extract_json(texto) is None


# ===========================================================================
# B — "no he podido completar…" ES una rendición (nodo en rojo, no en verde)
# ===========================================================================
class TestRendicionEnPasado:
    @pytest.mark.parametrize("texto", [
        # La frase LITERAL del nodo 3 del log del usuario.
        "No he podido completar el objetivo del paso. He intentado tres veces modificar el agente.",
        "No he podido completar esta tarea porque falta la herramienta.",
        "No pude completar el paso: el agente no pertenece a este proyecto.",
        "No he conseguido completar el encargo.",
        "No he logrado realizar la tarea.",
        "I couldn't complete this task.",
        "I could not complete this step.",
    ])
    def test_se_detecta(self, texto):
        assert is_surrender(texto) is True

    @pytest.mark.parametrize("texto", [
        # Parcial HONESTO: hizo la mayor parte y nombra lo que faltó. No es
        # rendición — marcarlo pondría en rojo un trabajo real.
        "He leído el GDD y he escrito el resumen. No he podido completar la sección de arte "
        "porque falta el archivo, pero el resto está entregado.",
        "He creado el agente correctamente con las skills pedidas.",
        "El paso se ha completado: 3 tareas creadas.",
        "No he podido evitar reírme con el nombre del proyecto, pero aquí está el listado.",
    ])
    def test_no_hay_falso_positivo(self, texto):
        assert is_surrender(texto) is False


# ===========================================================================
# C — crear un agente nunca deja un huérfano ni un error opaco
# ===========================================================================
class TestCreateAgentSinHuerfanos:
    @pytest.mark.anyio
    async def test_sin_project_id_no_se_crea_nada(self):
        res = await AitheraTool().execute("create_agent", {"name": "CordycepsDev"})
        assert res["success"] is False
        assert "project_id" in res.get("missing", [])
        db = SessionLocal()
        try:
            assert db.query(Agent).count() == 0, "se creó un agente huérfano pese al rechazo"
        finally:
            db.close()

    @pytest.mark.anyio
    async def test_proyecto_inexistente_no_se_crea_nada(self):
        res = await AitheraTool().execute("create_agent", {"name": "X", "project_id": 999999})
        assert res["success"] is False
        assert "no existe" in res["error"]
        db = SessionLocal()
        try:
            assert db.query(Agent).count() == 0
        finally:
            db.close()

    @pytest.mark.anyio
    async def test_con_proyecto_nace_vinculado(self):
        pid = _mk_project()
        res = await AitheraTool().execute("create_agent", {
            "name": "CordycepsDev", "project_id": pid,
            "allowed_tools": ["filesystem", "document"],
        })
        assert res["success"] is True
        assert res["result"]["project_id"] == pid
        assert _agent_row(res["result"]["id"]).project_id == pid

    @pytest.mark.anyio
    async def test_nombre_duplicado_dice_cual_es_el_agente_que_ya_existe(self):
        """Antes reventaba con un IntegrityError crudo del driver: el modelo no
        podía saber que el problema era el nombre, ni cuál era el id con el que
        arreglarlo, así que se ponía a dar vueltas."""
        pid = _mk_project()
        primero = await AitheraTool().execute("create_agent", {"name": "CordycepsDev", "project_id": pid})
        res = await AitheraTool().execute("create_agent", {"name": "CordycepsDev", "project_id": pid})
        assert res["success"] is False
        assert "ya existe" in res["error"]
        assert str(primero["result"]["id"]) in res["error"]
        assert "update_agent" in res["error"]

    def test_el_manager_tambien_protege_al_endpoint_http(self):
        pid = _mk_project()
        agent_manager.create_agent(name="Uno", project_id=pid)
        with pytest.raises(ValueError, match="ya existe"):
            agent_manager.create_agent(name="Uno", project_id=pid)


# ===========================================================================
# D — la autoridad del orquestador: todo lo suyo, nada de otros
# ===========================================================================
class TestAutoridadDelOrquestador:
    def _agent(self, name, project_id):
        db = SessionLocal()
        try:
            a = Agent(name=name, agent_type="generic", is_active=True,
                      allowed_tools=json.dumps([]), project_id=project_id)
            db.add(a)
            db.commit()
            db.refresh(a)
            return a.id
        finally:
            db.close()

    def test_un_agente_sin_proyecto_se_puede_adoptar(self):
        """El callejón sin salida del caso real: el huérfano no se podía tocar
        (no era 'de este proyecto') NI se podía reutilizar su nombre (es
        único), así que la misión se quedaba atrapada entre las dos paredes.
        Un agente que no es de NADIE no cruza ninguna frontera."""
        pid = _mk_project()
        huerfano = self._agent("Huérfano", None)
        authority = Authority(project_id=pid, allowed_tools=["aithera"])
        assert authority.check("aithera", "update_agent",
                               {"agent_id": huerfano, "project_id": pid}) is None

    def test_pero_solo_hacia_el_proyecto_propio(self):
        """La adopción no puede convertirse en una vía para regalar agentes."""
        pid, otro = _mk_project("A"), _mk_project("B")
        huerfano = self._agent("Huérfano", None)
        authority = Authority(project_id=pid, allowed_tools=["aithera"])
        razon = authority.check("aithera", "update_agent",
                                {"agent_id": huerfano, "project_id": otro})
        assert razon is not None and str(otro) in razon

    def test_un_agente_propio_no_se_puede_regalar_a_otro_proyecto(self):
        """El agujero que quedaba abierto: `update_agent` comprobaba de quién
        ERA el agente, nunca a dónde iba."""
        pid, otro = _mk_project("A"), _mk_project("B")
        propio = self._agent("Propio", pid)
        authority = Authority(project_id=pid, allowed_tools=["aithera"])
        assert authority.check("aithera", "update_agent",
                               {"agent_id": propio, "project_id": otro}) is not None
        # Editarlo sin moverlo, o "moverlo" a su propio proyecto: adelante.
        assert authority.check("aithera", "update_agent",
                               {"agent_id": propio, "skills": []}) is None
        assert authority.check("aithera", "update_agent",
                               {"agent_id": propio, "project_id": pid}) is None

    def test_el_de_otro_proyecto_sigue_denegado(self):
        pid, otro = _mk_project("A"), _mk_project("B")
        ajeno = self._agent("Ajeno", otro)
        authority = Authority(project_id=pid, allowed_tools=["aithera"])
        for accion, params in [
            ("assign_tools", {"agent_id": ajeno, "allowed_tools": []}),
            ("run_agent_task", {"agent_id": ajeno, "task": "x"}),
            ("delete_agent", {"agent_id": ajeno}),
        ]:
            assert authority.check("aithera", accion, params) is not None, accion

    def test_agente_inexistente_sigue_fail_closed(self):
        """No leerlo no es lo mismo que 'no tiene proyecto': el primero deniega."""
        authority = Authority(project_id=_mk_project(), allowed_tools=["aithera"])
        assert authority.check("aithera", "assign_tools",
                               {"agent_id": 999999, "allowed_tools": []}) is not None

    def test_project_id_basura_no_revienta_el_check(self):
        pid = _mk_project()
        propio = self._agent("Propio", pid)
        authority = Authority(project_id=pid, allowed_tools=["aithera"])
        # No lanza: deniega.
        assert authority.check("aithera", "update_agent",
                               {"agent_id": propio, "project_id": "no-soy-un-id"}) is not None

    def test_el_orquestador_puede_dar_tools_a_un_agente_suyo(self):
        """El encargo que falló: asignarle al agente nuevo sus herramientas."""
        pid = _mk_project()
        propio = self._agent("CordycepsDev", pid)
        authority = Authority(project_id=pid, allowed_tools=["filesystem", "document"])
        # `aithera` es INTERNA: no necesita estar en la whitelist del orquestador.
        assert authority.check("aithera", "assign_tools",
                               {"agent_id": propio, "allowed_tools": ["filesystem", "document"]}) is None
