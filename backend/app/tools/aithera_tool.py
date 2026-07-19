# backend/app/tools/aithera_tool.py — R3 del bloque Orquestrador (doc 23 §3 R3)
#
# "Aithera se opera a sí misma": una tool que le da al TIE/Orquestrador manos
# sobre el propio backend — Workspace, Agentes, Automatización y Email —, para
# que un plan del TIE con esta tool asignada pueda de verdad crear un proyecto
# con tareas, dar de alta un agente, o programar un recordatorio, en vez de
# solo hablar de ello.
#
# REGLA DE ORO (doc 23 R3): esto es un ADAPTADOR, nunca reimplementa lógica de
# negocio. Cada acción de escritura delega en el servicio/manager que YA existe
# y usa el endpoint HTTP correspondiente:
#   - tareas          -> app.automation.WorkspaceAction (mismos side effects
#                        que POST/PUT /api/tasks: progreso + eventos WPMS)
#   - proyectos/hitos  -> construcción directa (igual que hace el propio
#                        endpoint: no hay una capa de servicio que envolver)
#   - agentes          -> app.agents.agent_manager (create_agent/update_agent/
#                        create_execution, tal cual usa /api/agents)
#   - reglas/cron      -> fila AutomationRule directa (único patrón que existe
#                        en el código, usado también por rules_builtin.py) +
#                        automation_engine.arm_rule/disarm_rule
#   - auto-respuesta   -> delega en EmailTool.add_auto_reply_rule tal cual
#
# Si falta un campo obligatorio, la acción devuelve success=False con
# `missing: [...]` — nunca se inventa un valor. El toolloop (R1) convierte eso
# en una pregunta al usuario.
#
# Todas las acciones de ESCRITURA llevan requires_confirmation=True (doc 23,
# regla de seguridad heredada de R1: las sensibles siempre se PREGUNTAN, nunca
# se deniegan en silencio — el toolloop las resuelve vía ApprovalGate, con
# auto-resolución si el usuario ya las pre-autorizó en Permisos/A3b).

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseTool


def _missing(params: Dict[str, Any], required: List[str]) -> List[str]:
    """Campos ausentes o vacíos. OJO: un {} o [] presente es un valor válido
    (p.ej. action_config={} para una acción sin parámetros) — solo None,
    ausencia real, o string vacío cuentan como "falta"."""
    out = []
    for f in required:
        v = params.get(f)
        if v is None or (isinstance(v, str) and not v.strip()):
            out.append(f)
    return out


class AitheraTool(BaseTool):
    tool_id = "aithera"
    name = "Aithera Tool"
    description = (
        "Aithera se opera a sí misma: crea y gestiona proyectos, hitos, tareas, "
        "agentes, reglas de automatización (incl. recordatorios programados) y "
        "reglas de auto-respuesta de email — directamente desde el chat."
    )
    requires_confirmation = False  # depende de la acción
    # NO es una tool que se asigne a un agente: es la capacidad del Orquestador
    # sobre la propia Aithera (ver `BaseTool.internal`). No aparece en el
    # catálogo público ni en la UI de agentes; el TIE la tiene siempre a mano, y
    # cuando el Orquestador encarga a un agente algo de esto, el agente puede
    # hacerlo sin que nadie le haya marcado ninguna casilla.
    internal = True

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        handler = {
            # Workspace
            "list_projects": self._list_projects,
            "project_status": self._project_status,
            "create_project": self._create_project,
            "create_milestone": self._create_milestone,
            "create_task": self._create_task,
            "update_task": self._update_task,
            # Agentes
            "create_agent": self._create_agent,
            "assign_tools": self._assign_tools,
            "list_agents": self._list_agents,
            "run_agent_task": self._run_agent_task,
            # Automatización
            "create_rule": self._create_rule,
            "create_cron_job": self._create_cron_job,
            "list_rules": self._list_rules,
            "toggle_rule": self._toggle_rule,
            # Email
            "create_auto_reply_rule": self._create_auto_reply_rule,
        }.get(action)
        if not handler:
            return {"success": False, "result": None, "error": f"Acción desconocida: {action}"}
        try:
            return await handler(params)
        except Exception as e:
            return {"success": False, "result": None, "error": f"{type(e).__name__}: {e}"}

    def list_actions(self) -> List[Dict[str, Any]]:
        return [
            # ---- Workspace ----
            {"id": "list_projects", "description": "Lista los proyectos (no archivados por defecto).",
             "requires_confirmation": False,
             "params": {"include_archived": "bool opcional (default false)"}},
            {"id": "project_status", "description": "Estado de un proyecto: progreso, hitos y tareas abiertas.",
             "requires_confirmation": False, "params": {"project_id": "int"}},
            {"id": "create_project", "description": "Crea un proyecto nuevo.",
             "requires_confirmation": True,
             "params": {"name": "string", "description": "string opcional", "repo_path": "string opcional",
                        "current_version": "string opcional", "target_version": "string opcional",
                        "tags": "lista de strings opcional"}},
            {"id": "create_milestone", "description": "Crea un hito (eje de versión) dentro de un proyecto.",
             "requires_confirmation": True,
             "params": {"project_id": "int", "name": "string", "version": "string opcional",
                        "description": "string opcional", "target_date": "ISO datetime opcional"}},
            {"id": "create_task", "description": "Crea una tarea (recalcula el progreso del proyecto).",
             "requires_confirmation": True,
             "params": {"project_id": "int", "title": "string", "description": "string opcional",
                        "status": "'pending'|'in_progress'|'done' (default pending)",
                        "priority": "string opcional (default medium)", "milestone_id": "int opcional"}},
            {"id": "update_task", "description": "Actualiza/cierra/mueve una tarea existente.",
             "requires_confirmation": True,
             "params": {"task_id": "int", "op": "'update_task'|'close_task'|'move_task' (default update_task)",
                        "title": "string opcional", "description": "string opcional",
                        "status": "string opcional", "priority": "string opcional",
                        "project_id": "int opcional (para move_task)", "milestone_id": "int opcional"}},
            # ---- Agentes ----
            {"id": "create_agent", "description": "Crea un agente nuevo.",
             "requires_confirmation": True,
             "params": {"name": "string", "agent_type": "string opcional (default generic)",
                        "description": "string opcional", "allowed_tools": "lista de tool_id opcional",
                        "project_id": "int opcional", "skills": "lista de strings opcional"}},
            {"id": "assign_tools", "description": "Cambia las tools permitidas de un agente existente.",
             "requires_confirmation": True,
             "params": {"agent_id": "int", "allowed_tools": "lista de tool_id"}},
            {"id": "list_agents", "description": "Lista los agentes (opcionalmente de un proyecto).",
             "requires_confirmation": False, "params": {"project_id": "int opcional"}},
            {"id": "run_agent_task", "description": "Lanza una ejecución asíncrona de un agente con una tarea.",
             "requires_confirmation": True, "params": {"agent_id": "int", "task": "string"}},
            # ---- Automatización ----
            {"id": "create_rule", "description": "Crea una regla de automatización (disparador+condición+acción).",
             "requires_confirmation": True,
             "params": {"name": "string", "trigger_type": "'schedule'|'event'",
                        "trigger_config": "dict (p.ej. {'cron':{'hour':8,'minute':0}} o {'event_name':'task.closed'})",
                        "action_type": "string (uno de los registrados, ver error si no coincide)",
                        "action_config": "dict", "condition_config": "dict opcional",
                        "project_id": "int opcional", "cooldown_s": "int opcional (default 0)",
                        "enabled": "bool opcional (default false — nace desactivada, HITL)"}},
            {"id": "create_cron_job", "description": (
                "Atajo de create_rule para un recordatorio/acción diaria a una hora fija "
                "(reutiliza el mismo mecanismo — sin scheduler paralelo). Queda ACTIVO."),
             "requires_confirmation": True,
             "params": {"name": "string", "hour": "int 0-23", "minute": "int 0-59 (default 0)",
                        "action_type": "string", "action_config": "dict",
                        "enabled": "bool opcional (default true — el usuario lo ha pedido)"}},
            {"id": "list_rules", "description": "Lista las reglas de automatización.",
             "requires_confirmation": False, "params": {"project_id": "int opcional"}},
            {"id": "toggle_rule", "description": "Activa o desactiva una regla (arma/desarma en caliente).",
             "requires_confirmation": True, "params": {"rule_id": "int", "enabled": "bool"}},
            # ---- Email ----
            {"id": "create_auto_reply_rule", "description": "Crea una regla de auto-respuesta de email.",
             "requires_confirmation": True,
             "params": {"name": "string", "sender_emails": "lista opcional", "sender_domains": "lista opcional",
                        "pattern": "string opcional", "matching": "'sender_contains'|'subject_contains'|'sender_domain'",
                        "action": "'auto_send'|'create_draft'|'alert_only' (default auto_send)",
                        "reply_template": "string opcional", "ai_prompt": "string opcional",
                        "autonomy": "'propose'|'auto' (default propose)"}},
        ]

    # ------------------------------------------------------------------
    # Workspace
    # ------------------------------------------------------------------

    async def _list_projects(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.db.database import Project, SessionLocal

        db = SessionLocal()
        try:
            q = db.query(Project)
            if not params.get("include_archived"):
                q = q.filter(Project.archived_at.is_(None))
            projects = q.order_by(Project.id.desc()).all()
            return {"success": True, "result": {"projects": [
                {"id": p.id, "name": p.name, "status": p.status, "progress": p.progress,
                 "current_version": p.current_version, "archived": p.archived_at is not None}
                for p in projects
            ]}, "error": None}
        finally:
            db.close()

    async def _project_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.db.database import Project, SessionLocal, Task
        from app.workspace import Milestone

        missing = _missing(params, ["project_id"])
        if missing:
            return {"success": False, "result": None, "error": "faltan parámetros", "missing": missing}

        db = SessionLocal()
        try:
            project = db.get(Project, int(params["project_id"]))
            if project is None:
                return {"success": False, "result": None, "error": f"proyecto {params['project_id']} no existe"}
            milestones = db.query(Milestone).filter(Milestone.project_id == project.id).all()
            open_tasks = (db.query(Task)
                          .filter(Task.project_id == project.id, Task.status != "done")
                          .order_by(Task.priority.desc()).limit(20).all())
            return {"success": True, "result": {
                "id": project.id, "name": project.name, "status": project.status,
                "progress": project.progress, "current_version": project.current_version,
                "milestones": [{"id": m.id, "name": m.name, "status": m.status} for m in milestones],
                "open_tasks": [{"id": t.id, "title": t.title, "status": t.status} for t in open_tasks],
            }, "error": None}
        finally:
            db.close()

    async def _create_project(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.db.database import Project, SessionLocal

        missing = _missing(params, ["name"])
        if missing:
            return {"success": False, "result": None, "error": "faltan parámetros", "missing": missing}

        db = SessionLocal()
        try:
            project = Project(
                name=params["name"], description=params.get("description"),
                status="active", repo_path=params.get("repo_path"),
                current_version=params.get("current_version"), target_version=params.get("target_version"),
                tags=params.get("tags"),
            )
            db.add(project)
            db.commit()
            db.refresh(project)
            return {"success": True, "result": {"id": project.id, "name": project.name}, "error": None}
        finally:
            db.close()

    async def _create_milestone(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.db.database import Project, SessionLocal
        from app.workspace import Milestone

        missing = _missing(params, ["project_id", "name"])
        if missing:
            return {"success": False, "result": None, "error": "faltan parámetros", "missing": missing}

        db = SessionLocal()
        try:
            if db.get(Project, int(params["project_id"])) is None:
                return {"success": False, "result": None, "error": f"proyecto {params['project_id']} no existe"}
            milestone = Milestone(
                project_id=int(params["project_id"]), name=params["name"],
                version=params.get("version"), description=params.get("description"),
                status="planned",
            )
            db.add(milestone)
            db.commit()
            db.refresh(milestone)
            return {"success": True, "result": {"id": milestone.id, "name": milestone.name}, "error": None}
        finally:
            db.close()

    async def _create_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.automation import WorkspaceAction
        from app.automation import TriggerEvent

        missing = _missing(params, ["project_id", "title"])
        if missing:
            return {"success": False, "result": None, "error": "faltan parámetros", "missing": missing}

        config = {
            "op": "create_task", "title": params["title"], "description": params.get("description"),
            "status": params.get("status", "pending"), "priority": params.get("priority", "medium"),
            "project_id": int(params["project_id"]),
        }
        if params.get("milestone_id"):
            config["milestone_id"] = int(params["milestone_id"])

        res = await WorkspaceAction().execute(config, TriggerEvent(name="aithera_tool", event_key="n/a"))
        if not res.ok:
            return {"success": False, "result": None, "error": res.detail}
        return {"success": True, "result": res.data, "error": None}

    async def _update_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.automation import WorkspaceAction
        from app.automation import TriggerEvent

        missing = _missing(params, ["task_id"])
        if missing:
            return {"success": False, "result": None, "error": "faltan parámetros", "missing": missing}

        op = params.get("op", "update_task")
        if op not in {"update_task", "close_task", "move_task"}:
            return {"success": False, "result": None, "error": f"op inválida: {op!r}"}

        config: Dict[str, Any] = {"op": op, "task_id": int(params["task_id"])}
        for field in ("title", "description", "status", "priority", "project_id", "milestone_id"):
            if field in params and params[field] is not None:
                config[field] = params[field]

        res = await WorkspaceAction().execute(config, TriggerEvent(name="aithera_tool", event_key="n/a"))
        if not res.ok:
            return {"success": False, "result": None, "error": res.detail}
        return {"success": True, "result": res.data, "error": None}

    # ------------------------------------------------------------------
    # Agentes
    # ------------------------------------------------------------------

    async def _create_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.agents.agent_manager import agent_manager

        missing = _missing(params, ["name"])
        if missing:
            return {"success": False, "result": None, "error": "faltan parámetros", "missing": missing}
        try:
            agent = agent_manager.create_agent(
                name=params["name"], agent_type=params.get("agent_type", "generic"),
                description=params.get("description"), allowed_tools=params.get("allowed_tools"),
                project_id=params.get("project_id"), skills=params.get("skills"),
            )
        except ValueError as e:
            return {"success": False, "result": None, "error": str(e)}
        return {"success": True, "result": {"id": agent.id, "name": agent.name}, "error": None}

    async def _assign_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.agents.agent_manager import agent_manager

        missing = _missing(params, ["agent_id", "allowed_tools"])
        if missing:
            return {"success": False, "result": None, "error": "faltan parámetros", "missing": missing}
        try:
            agent = agent_manager.update_agent(int(params["agent_id"]), allowed_tools=params["allowed_tools"])
        except ValueError as e:
            return {"success": False, "result": None, "error": str(e)}
        if agent is None:
            return {"success": False, "result": None, "error": f"agente {params['agent_id']} no existe"}
        return {"success": True, "result": {"id": agent.id, "allowed_tools": agent.allowed_tools}, "error": None}

    async def _list_agents(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.agents.agent_manager import agent_manager

        project_id = params.get("project_id")
        agents = agent_manager.list_agents(project_id=int(project_id) if project_id else None)
        return {"success": True, "result": {"agents": [
            {"id": a.id, "name": a.name, "agent_type": a.agent_type, "is_active": a.is_active}
            for a in agents
        ]}, "error": None}

    async def _run_agent_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.agents.agent_manager import agent_manager

        missing = _missing(params, ["agent_id", "task"])
        if missing:
            return {"success": False, "result": None, "error": "faltan parámetros", "missing": missing}
        try:
            execution = agent_manager.create_execution(int(params["agent_id"]), params["task"])
        except ValueError as e:
            return {"success": False, "result": None, "error": str(e)}
        return {"success": True, "result": {"execution_id": execution.id, "status": execution.status}, "error": None}

    # ------------------------------------------------------------------
    # Automatización
    # ------------------------------------------------------------------

    def _validate_rule_fields(self, params: Dict[str, Any], required: List[str]) -> Optional[Dict[str, Any]]:
        from app.automation import DEFAULT_ACTIONS

        missing = _missing(params, required)
        if missing:
            return {"success": False, "result": None, "error": "faltan parámetros", "missing": missing}
        action_type = params.get("action_type")
        if action_type not in DEFAULT_ACTIONS:
            return {"success": False, "result": None,
                    "error": f"action_type desconocido: {action_type!r}. Disponibles: {sorted(DEFAULT_ACTIONS)}"}
        return None

    async def _insert_rule(self, *, name: str, trigger_type: str, trigger_config: dict,
                            action_type: str, action_config: dict, condition_config: Optional[dict],
                            project_id: Optional[int], cooldown_s: int, enabled: bool) -> Dict[str, Any]:
        from app.automation import AutomationRule, automation_engine
        from app.db.database import SessionLocal

        db = SessionLocal()
        try:
            rule = AutomationRule(
                name=name, enabled=bool(enabled), trigger_type=trigger_type,
                trigger_config=trigger_config, condition_config=condition_config or {},
                action_type=action_type, action_config=action_config,
                project_id=int(project_id) if project_id else None, cooldown_s=int(cooldown_s or 0),
                created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
            )
            db.add(rule)
            db.commit()
            db.refresh(rule)
            rule_id = rule.id
        finally:
            db.close()

        armada = False
        if enabled:
            # Armar es un detalle de EJECUCION; lo que importa ya esta en la BD.
            # Si el planificador no esta arriba (scripts, tests, un arranque a
            # medias), la regla NO se pierde: `load_rules()` la arma en el
            # siguiente arranque. Fallar aqui diria "no se pudo crear" cuando si
            # se creo — mentir sobre lo que ha pasado.
            try:
                automation_engine.arm_rule(rule_id, trigger_type, trigger_config)
                armada = True
            except Exception as e:
                from app.core.logging_config import get_system_logger

                get_system_logger("tools.aithera").info(
                    f"[aithera] regla {rule_id} creada pero no armada ahora "
                    f"({type(e).__name__}); se armara al arrancar: {e}"
                )
        return {"success": True,
                "result": {"id": rule_id, "enabled": bool(enabled), "armed": armada},
                "error": None}

    async def _create_rule(self, params: Dict[str, Any]) -> Dict[str, Any]:
        err = self._validate_rule_fields(params, ["name", "trigger_type", "trigger_config", "action_type", "action_config"])
        if err:
            return err
        return await self._insert_rule(
            name=params["name"], trigger_type=params["trigger_type"], trigger_config=params["trigger_config"],
            action_type=params["action_type"], action_config=params["action_config"],
            condition_config=params.get("condition_config"), project_id=params.get("project_id"),
            cooldown_s=params.get("cooldown_s", 0), enabled=bool(params.get("enabled", False)),
        )

    async def _create_cron_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        err = self._validate_rule_fields(params, ["name", "hour", "action_type", "action_config"])
        if err:
            return err
        hour = int(params["hour"])
        if not (0 <= hour <= 23):
            return {"success": False, "result": None, "error": "hour debe estar entre 0 y 23"}
        minute = int(params.get("minute", 0))
        if not (0 <= minute <= 59):
            return {"success": False, "result": None, "error": "minute debe estar entre 0 y 59"}

        # [R5] Nace ACTIVO, al revés que `create_rule`. No es una excepción a la
        # regla HITL, es la regla bien entendida: las 5 reglas predefinidas de A3
        # nacen desactivadas porque NADIE las pidió (se siembran solas), mientras
        # que esto es un recordatorio concreto que el usuario acaba de pedir Y
        # confirmar en el ApprovalGate. Un recordatorio que hay que ir a activar
        # a otra pantalla, y que mientras tanto no suena, es un bug desde el
        # punto de vista del usuario. Queda persistido en `automation_rules`, así
        # que `load_rules()` lo vuelve a armar en cada arranque.
        return await self._insert_rule(
            name=params["name"], trigger_type="schedule", trigger_config={"cron": {"hour": hour, "minute": minute}},
            action_type=params["action_type"], action_config=params["action_config"],
            condition_config=None, project_id=None, cooldown_s=0,
            enabled=bool(params.get("enabled", True)),
        )

    async def _list_rules(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.automation import AutomationRule
        from app.db.database import SessionLocal

        db = SessionLocal()
        try:
            q = db.query(AutomationRule)
            if params.get("project_id"):
                q = q.filter(AutomationRule.project_id == int(params["project_id"]))
            rules = q.order_by(AutomationRule.id.desc()).all()
            return {"success": True, "result": {"rules": [
                {"id": r.id, "name": r.name, "enabled": r.enabled, "trigger_type": r.trigger_type,
                 "action_type": r.action_type}
                for r in rules
            ]}, "error": None}
        finally:
            db.close()

    async def _toggle_rule(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.automation import AutomationRule, automation_engine
        from app.db.database import SessionLocal

        missing = _missing(params, ["rule_id"])
        if missing or "enabled" not in params:
            return {"success": False, "result": None, "error": "faltan parámetros",
                    "missing": missing or ["enabled"]}

        db = SessionLocal()
        try:
            rule = db.get(AutomationRule, int(params["rule_id"]))
            if rule is None:
                return {"success": False, "result": None, "error": f"regla {params['rule_id']} no existe"}
            rule.enabled = bool(params["enabled"])
            rule.updated_at = datetime.utcnow()
            db.commit()
            out = {"id": rule.id, "enabled": rule.enabled, "trigger_type": rule.trigger_type,
                   "trigger_config": rule.trigger_config}
        finally:
            db.close()

        if out["enabled"]:
            automation_engine.arm_rule(out["id"], out["trigger_type"], out["trigger_config"] or {})
        else:
            automation_engine.disarm_rule(out["id"])
        return {"success": True, "result": {"id": out["id"], "enabled": out["enabled"]}, "error": None}

    # ------------------------------------------------------------------
    # Email
    # ------------------------------------------------------------------

    async def _create_auto_reply_rule(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from .email_tool import EmailTool

        return await EmailTool().execute("add_auto_reply_rule", params)
