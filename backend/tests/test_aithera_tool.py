# tests/test_aithera_tool.py — R3 del bloque Orquestrador: "Aithera se opera
# a sí misma" (doc 23 §3 R3).
#
# Criterios de cierre de R3 (doc 23): (1) pedir por chat un proyecto con
# tareas lo crea de verdad, con el progreso recalculado; (2) un campo
# obligatorio ausente nunca se inventa, se devuelve `missing`; (3) disciplina
# modular — la tool nunca importa modelos SQL sueltos donde ya existe un
# servicio (usa WorkspaceAction/agent_manager/AutomationRule tal como el resto
# del código real). Se ejercita contra la BD real de tests (mismo patrón que
# test_workspace_model.py / test_new_tools.py), sin mocks salvo lo estrictamente
# no determinista.
from __future__ import annotations

import pytest

from app.tools.tool_manager import tool_manager


@pytest.fixture(autouse=True)
def _clean_tables():
    from app.db.database import Base, engine
    Base.metadata.create_all(bind=engine)
    yield
    from app.db.database import Agent, AgentExecution, EmailAutoReplyRule, Project, SessionLocal, Task
    from app.automation import AutomationRule
    from app.workspace import Milestone

    db = SessionLocal()
    try:
        for model in (AgentExecution, Agent, Task, Milestone, Project, AutomationRule, EmailAutoReplyRule):
            try:
                db.query(model).delete()
            except Exception:
                db.rollback()
        db.commit()
    finally:
        db.close()


def test_aithera_es_INTERNA_no_asignable_a_un_agente():
    """[Correccion de diseño 2026-07-19, pedida por el usuario] Operar Aithera
    NO es una herramienta que se conceda a un agente: es la capacidad del
    Orquestador sobre su propia casa. Como casilla en la UI implicaba lo
    contrario — que un agente al que el Orquestador le encarga esto no pudiera
    hacerlo por no tenerla marcada."""
    publicas = {t["tool_id"] for t in tool_manager.list_tools()}
    assert "aithera" not in publicas, "no debe aparecer en el catalogo publico ni en la UI"

    # Pero SI existe y el TIE la ve.
    internas = {t["tool_id"] for t in tool_manager.list_tools(include_internal=True)}
    assert "aithera" in internas
    assert "aithera" in tool_manager.internal_tool_ids()
    assert tool_manager.get_tool("aithera") is not None


def test_un_agente_no_puede_asignarse_la_tool_interna():
    """La validacion de `allowed_tools` usa el catalogo PUBLICO, asi que pedir
    'aithera' a mano falla como cualquier tool inexistente."""
    from app.agents.agent_manager import agent_manager

    with pytest.raises(ValueError) as exc:
        agent_manager.create_agent(name="[test] colado", allowed_tools=["aithera"])
    assert "aithera" in str(exc.value)


def test_la_whitelist_de_un_agente_no_puede_quitar_las_internas():
    """El recorte de R4 acota las tools EXTERNAS del agente; las internas no
    dependen de esa lista. Lo que sigue acotandolas es la frontera de proyecto."""
    from app.tie.authority import Authority

    a = Authority(allowed_tools=["git"])          # un agente sin 'aithera'
    assert a.check("shell", "run_command", {}) is not None      # externa: bloqueada
    assert a.check("aithera", "list_projects", {}) is None      # interna: permitida


def test_pero_la_frontera_de_proyecto_sigue_aplicando_a_las_internas():
    """Que sea interna NO significa barra libre: el orquestador de un proyecto
    sigue sin poder tocar otro (R4 Δ6)."""
    from app.tie.authority import Authority

    a = Authority(project_id=7, allowed_tools=["git"])
    assert a.check("aithera", "create_task", {"project_id": 7}) is None
    assert a.check("aithera", "create_task", {"project_id": 8}) is not None


def test_acciones_de_escritura_piden_confirmacion():
    tool = tool_manager.get_tool("aithera")
    by_id = {a["id"]: a for a in tool.list_actions()}
    writes = {"create_project", "create_milestone", "create_task", "update_task",
              "create_agent", "assign_tools", "run_agent_task",
              "create_rule", "create_cron_job", "toggle_rule", "create_auto_reply_rule"}
    reads = {"list_projects", "project_status", "list_agents", "list_rules"}
    for action_id in writes:
        assert by_id[action_id]["requires_confirmation"] is True, action_id
    for action_id in reads:
        assert by_id[action_id]["requires_confirmation"] is False, action_id


# ---------------------------------------------------------------------------
# Workspace: proyecto + tareas de verdad, progreso recalculado (criterio 1)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_crea_proyecto_con_tareas_y_el_progreso_se_recalcula():
    r = await tool_manager.execute("aithera", "create_project", {"name": "Proyecto de prueba R3"})
    assert r["success"], r
    project_id = r["result"]["id"]

    r1 = await tool_manager.execute("aithera", "create_task",
                                     {"project_id": project_id, "title": "Tarea A"})
    r2 = await tool_manager.execute("aithera", "create_task",
                                     {"project_id": project_id, "title": "Tarea B"})
    assert r1["success"] and r2["success"]
    task_a_id = r1["result"]["task_id"]

    status = await tool_manager.execute("aithera", "project_status", {"project_id": project_id})
    assert status["success"]
    assert status["result"]["progress"] == 0.0
    assert len(status["result"]["open_tasks"]) == 2

    closed = await tool_manager.execute("aithera", "update_task",
                                         {"task_id": task_a_id, "op": "close_task"})
    assert closed["success"]

    status2 = await tool_manager.execute("aithera", "project_status", {"project_id": project_id})
    assert status2["result"]["progress"] == 0.5
    assert len(status2["result"]["open_tasks"]) == 1


@pytest.mark.anyio
async def test_crea_milestone_dentro_de_un_proyecto_real():
    r = await tool_manager.execute("aithera", "create_project", {"name": "Proyecto con hitos"})
    project_id = r["result"]["id"]

    r = await tool_manager.execute("aithera", "create_milestone",
                                    {"project_id": project_id, "name": "v1", "version": "1.0.0"})
    assert r["success"], r

    status = await tool_manager.execute("aithera", "project_status", {"project_id": project_id})
    assert len(status["result"]["milestones"]) == 1
    assert status["result"]["milestones"][0]["name"] == "v1"


@pytest.mark.anyio
async def test_list_projects_ve_lo_creado():
    await tool_manager.execute("aithera", "create_project", {"name": "Listable"})
    r = await tool_manager.execute("aithera", "list_projects", {})
    assert r["success"]
    assert any(p["name"] == "Listable" for p in r["result"]["projects"])


# ---------------------------------------------------------------------------
# Campos obligatorios ausentes -> missing, nunca inventar (criterio 2)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_create_project_sin_name_devuelve_missing():
    r = await tool_manager.execute("aithera", "create_project", {})
    assert r["success"] is False
    assert r["missing"] == ["name"]


@pytest.mark.anyio
async def test_create_task_sin_campos_devuelve_missing():
    r = await tool_manager.execute("aithera", "create_task", {"project_id": 1})
    assert r["success"] is False
    assert "title" in r["missing"]


@pytest.mark.anyio
async def test_create_agent_sin_name_devuelve_missing():
    r = await tool_manager.execute("aithera", "create_agent", {})
    assert r["success"] is False
    assert r["missing"] == ["name"]


@pytest.mark.anyio
async def test_create_rule_action_type_desconocido_no_se_inventa():
    r = await tool_manager.execute("aithera", "create_rule", {
        "name": "regla rara", "trigger_type": "schedule",
        "trigger_config": {"cron": {"hour": 8}},
        "action_type": "esto_no_existe", "action_config": {},
    })
    assert r["success"] is False
    assert "esto_no_existe" in r["error"]


# ---------------------------------------------------------------------------
# Agentes reales
# ---------------------------------------------------------------------------
def _mk_project(name="Proyecto R3") -> int:
    """[2026-08-02] Desde el fix del agente huérfano, `create_agent` EXIGE
    project_id: un agente sin proyecto no lo podía configurar ni su propio
    creador. Estos tests, escritos cuando era opcional, necesitan un proyecto
    real — lo que comprueban (asignar tools, propagar errores) no cambia."""
    from app.db.database import Project, SessionLocal

    db = SessionLocal()
    try:
        p = Project(name=name, status="active")
        db.add(p)
        db.commit()
        db.refresh(p)
        return p.id
    finally:
        db.close()


@pytest.mark.anyio
async def test_crea_agente_y_le_asigna_tools():
    r = await tool_manager.execute("aithera", "create_agent", {
        "name": "Agente R3", "allowed_tools": ["git"], "project_id": _mk_project()})
    assert r["success"], r
    agent_id = r["result"]["id"]

    r = await tool_manager.execute("aithera", "assign_tools",
                                    {"agent_id": agent_id, "allowed_tools": ["git", "filesystem"]})
    assert r["success"], r

    listed = await tool_manager.execute("aithera", "list_agents", {})
    assert any(a["id"] == agent_id for a in listed["result"]["agents"])


@pytest.mark.anyio
async def test_assign_tools_con_tool_desconocida_falla_claro():
    r = await tool_manager.execute("aithera", "create_agent", {
        "name": "Agente R3b", "project_id": _mk_project("Proyecto R3b")})
    agent_id = r["result"]["id"]
    r = await tool_manager.execute("aithera", "assign_tools",
                                    {"agent_id": agent_id, "allowed_tools": ["no_existe_esta_tool"]})
    assert r["success"] is False
    assert "no_existe_esta_tool" in r["error"]


# ---------------------------------------------------------------------------
# Automatización: crea reglas de verdad y programa un cron (sin scheduler
# paralelo -- mismo mecanismo de AutomationRule que ya usa rules_builtin.py)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_crea_regla_desactivada_por_defecto_hitl():
    r = await tool_manager.execute("aithera", "create_rule", {
        "name": "aviso diario", "trigger_type": "schedule",
        "trigger_config": {"cron": {"hour": 8, "minute": 0}},
        "action_type": "chat_query", "action_config": {"prompt": "resume mi día"},
    })
    assert r["success"], r
    assert r["result"]["enabled"] is False

    rules = await tool_manager.execute("aithera", "list_rules", {})
    assert any(x["id"] == r["result"]["id"] for x in rules["result"]["rules"])


@pytest.mark.anyio
async def test_create_cron_job_es_azucar_sobre_create_rule():
    r = await tool_manager.execute("aithera", "create_cron_job", {
        "name": "recordatorio 08:30", "hour": 8, "minute": 30,
        "action_type": "chat_query", "action_config": {"prompt": "revisa el email"},
    })
    assert r["success"], r

    from app.automation import AutomationRule
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        row = db.get(AutomationRule, r["result"]["id"])
        assert row.trigger_type == "schedule"
        assert row.trigger_config == {"cron": {"hour": 8, "minute": 30}}
    finally:
        db.close()


@pytest.mark.anyio
async def test_create_cron_job_hora_invalida_rechazada():
    r = await tool_manager.execute("aithera", "create_cron_job", {
        "name": "malo", "hour": 27, "action_type": "chat_query", "action_config": {},
    })
    assert r["success"] is False


@pytest.mark.anyio
async def test_toggle_rule_activa_y_desactiva_en_caliente(client):
    # `client` arranca el lifespan real (APScheduler incluido) — armar un
    # trigger de tipo schedule necesita el scheduler corriendo de verdad,
    # igual que test_event_trigger.py::test_schedule_trigger_arma_job_y_evaluate.
    created = await tool_manager.execute("aithera", "create_rule", {
        "name": "toggle test", "trigger_type": "schedule",
        "trigger_config": {"cron": {"hour": 9}},
        "action_type": "chat_query", "action_config": {"prompt": "x"},
    })
    rule_id = created["result"]["id"]

    on = await tool_manager.execute("aithera", "toggle_rule", {"rule_id": rule_id, "enabled": True})
    assert on["success"] and on["result"]["enabled"] is True

    from app.automation import automation_engine
    assert rule_id in automation_engine.armed_rule_ids()

    off = await tool_manager.execute("aithera", "toggle_rule", {"rule_id": rule_id, "enabled": False})
    assert off["success"] and off["result"]["enabled"] is False
    assert rule_id not in automation_engine.armed_rule_ids()


# ---------------------------------------------------------------------------
# Email: delega en EmailTool.add_auto_reply_rule tal cual (adaptador, no
# reimplementación)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_create_auto_reply_rule_delega_en_email_tool():
    r = await tool_manager.execute("aithera", "create_auto_reply_rule", {
        "name": "regla auto-reply desde el chat",
        "sender_domains": ["ejemplo.com"],
        "reply_template": "Gracias por tu mensaje.",
    })
    assert r["success"], r

    from app.db.database import EmailAutoReplyRule, SessionLocal
    db = SessionLocal()
    try:
        row = db.query(EmailAutoReplyRule).filter(
            EmailAutoReplyRule.name == "regla auto-reply desde el chat").first()
        assert row is not None
        assert row.autonomy == "propose"  # nace en propose salvo pedirlo explícito
    finally:
        db.close()
