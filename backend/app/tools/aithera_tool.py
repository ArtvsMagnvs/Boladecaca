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


def _json_list(raw) -> List[str]:
    """`Agent.allowed_tools` se guarda como JSON string (V0.5). Se devuelve
    como lista para que el modelo la lea sin tener que parsear nada."""
    import json as _json

    if isinstance(raw, list):
        return raw
    try:
        valor = _json.loads(raw or "[]")
        return valor if isinstance(valor, list) else []
    except (ValueError, TypeError):
        return []


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
            "update_agent": self._update_agent,
            "delete_agent": self._delete_agent,
            "search_skills": self._search_skills,
            "assign_tools": self._assign_tools,
            "list_agents": self._list_agents,
            "run_agent_task": self._run_agent_task,
            # [2026-08-02] La ejecución REAL de `ask_user` NO está aquí: la
            # intercepta `toolloop` antes de despachar (ver más abajo y el
            # comentario de `list_actions`). Este handler solo existe para que
            # una llamada fuera del bucle falle CLARO en vez de "acción
            # desconocida", que sería un diagnóstico engañoso.
            "ask_user": self._ask_user_guard,
            # Automatización
            "create_rule": self._create_rule,
            "create_cron_job": self._create_cron_job,
            "list_rules": self._list_rules,
            "toggle_rule": self._toggle_rule,
            # Email
            "create_auto_reply_rule": self._create_auto_reply_rule,
            # Configuración de la app (idioma, modelo del chat)
            "set_language": self._set_language,
            "set_chat_model": self._set_chat_model,
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
            {"id": "create_agent",
             "description": ("Crea un agente nuevo DENTRO de un proyecto. Dale de una vez todo lo "
                             "que necesite (allowed_tools y skills): así no hacen falta llamadas "
                             "extra después. Las skills NO se inventan: búscalas antes con "
                             "'search_skills' y pasa sus nombres EXACTOS."),
             "requires_confirmation": True,
             "params": {"name": "string (único en todo el sistema)",
                        "project_id": "int OBLIGATORIO — el proyecto al que pertenece",
                        "agent_type": "string opcional (default generic)",
                        "description": "string opcional — para QUÉ es el agente, en 1-3 frases. "
                                       "NO metas aquí las especialidades: eso son las skills.",
                        "allowed_tools": "lista de tool_id opcional",
                        "skills": "lista de nombres EXACTOS del catálogo (ver 'search_skills')"}},
            # [2026-08-02] EL CATÁLOGO DE SKILLS SE PUEDE CONSULTAR. Sin esto,
            # `create_agent` pedía "skills: lista de strings" sin decir CUÁLES
            # existen — 254 nombres exactos que el modelo no podía adivinar ni
            # caben en el prompt. Resultado real reportado: el orquestador
            # creaba el agente SIN skills y volcaba todo el diseño en la
            # descripción. Ahora hay dónde mirar antes de asignar.
            {"id": "search_skills",
             "description": ("Busca skills REALES del catálogo por tema, categoría o palabra "
                             "(p.ej. 'unity', 'videojuegos', 'marketing'). Devuelve los NOMBRES "
                             "EXACTOS que hay que pasar a create_agent/update_agent. Úsala SIEMPRE "
                             "antes de asignar skills: los nombres inventados se rechazan. "
                             "IMPORTANTE: pasa UNA palabra clave por llamada, no una frase larga "
                             "('unity', no 'unity UI frontend developer') — así encuentras más. "
                             "El catálogo es LIMITADO (254 skills, 17 categorías): no siempre hay "
                             "una skill perfecta para cada encargo. En cuanto tengas 2-4 candidatas "
                             "razonablemente relacionadas, ÚSALAS y sigue con create_agent — no "
                             "seguir buscando variantes de la misma idea más de 2-3 veces."),
             "requires_confirmation": False,
             "params": {"query": "string — UNA palabra o tema, no una frase larga",
                        "limit": "int opcional (default 12)"}},
            {"id": "assign_tools", "description": "Cambia las tools permitidas de un agente existente.",
             "requires_confirmation": True,
             "params": {"agent_id": "int", "allowed_tools": "lista de tool_id"}},
            {"id": "list_agents", "description": "Lista los agentes (opcionalmente de un proyecto).",
             "requires_confirmation": False, "params": {"project_id": "int opcional"}},
            {"id": "run_agent_task", "description": "Lanza una ejecución asíncrona de un agente con una tarea.",
             "requires_confirmation": True, "params": {"agent_id": "int", "task": "string"}},
            {"id": "update_agent",
             "description": ("Edita un agente YA EXISTENTE: skills, proyecto, tools, nombre, "
                             "descripción, icono o si está activo. Úsala para CORREGIR un agente "
                             "en vez de crear otro con distinto nombre."),
             "requires_confirmation": True,
             "params": {"agent_id": "int", "name": "string opcional",
                        "description": "string opcional", "agent_type": "string opcional",
                        "skills": "lista de strings opcional", "allowed_tools": "lista de tool_id opcional",
                        "project_id": "int opcional", "icon": "string opcional",
                        "is_active": "bool opcional", "max_execution_time": "int opcional"}},
            {"id": "delete_agent", "description": "Elimina un agente (cancela sus ejecuciones en curso).",
             "requires_confirmation": True, "params": {"agent_id": "int"}},
            # ---- Preguntar al usuario ----
            # [2026-08-02] La ejecuta el bucle de tool-use (`toolloop`), NO esta
            # clase: el ToolManager impone un timeout duro de 300 s como mucho y
            # la espera de una respuesta humana es INDEFINIDA (decisión explícita
            # del usuario). Se declara aquí para que aparezca en el catálogo que
            # ve el modelo, que es lo que la hace descubrible.
            {"id": "ask_user",
             "description": ("PREGUNTA algo al usuario y ESPERA su respuesta (sin límite de tiempo). "
                             "Úsala siempre que te falte un dato, tengas que elegir entre varias vías "
                             "o necesites una confirmación de criterio, EN VEZ de suponer, de rendirte "
                             "o de terminar pidiéndoselo en el resumen final. Ofrece opciones concretas "
                             "cuando las haya: el usuario podrá elegir una o escribir su propia respuesta."),
             "requires_confirmation": False,
             "params": {"question": "string — la pregunta, clara y concreta",
                        "options": "lista de strings opcional (2-4 respuestas sugeridas; la 1.ª, la recomendada)",
                        "header": "string opcional — etiqueta corta del tema (máx. 40 car.)"}},
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
            # ---- Configuración de la app ----
            {"id": "set_language", "description": (
                "Cambia el IDIOMA de la aplicación (interfaz y respuestas del chat). "
                "Úsalo cuando el usuario diga 'cambia el idioma a X' / 'ponte en inglés'."),
             "requires_confirmation": False,
             "params": {"language": "código o nombre: es/en/fr/pt o 'español'/'inglés'/'francés'/'portugués'"}},
            {"id": "set_chat_model", "description": (
                "Fija el MODELO PRINCIPAL del chat (capacidad CHAT) en la política de "
                "Inteligencia activa. Úsalo cuando el usuario diga 'pon Minimax como modelo "
                "del chat' / 'usa Claude para el chat a partir de ahora'."),
             "requires_confirmation": True,
             "params": {"model": "nombre del modelo o proveedor (p.ej. 'minimax', 'MiniMax-M3', 'claude')"}},
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
            # [2026-07-25] `repo_path` y `docs` viajan en la respuesta: son el
            # material del proyecto (carpeta local, archivos adjuntos, enlaces).
            # Sin ellos, un agente que consulta su proyecto no sabía qué
            # documentos tiene a mano para leerlos con `filesystem`/`document`.
            docs = project.docs if isinstance(project.docs, list) else []
            return {"success": True, "result": {
                "id": project.id, "name": project.name, "status": project.status,
                "progress": project.progress, "current_version": project.current_version,
                "repo_path": project.repo_path,
                "files": [d for d in docs if isinstance(d, dict) and d.get("kind") == "file"],
                "links": [d for d in docs if isinstance(d, dict) and d.get("kind") != "file"],
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
        """[2026-08-02] UN AGENTE SIEMPRE NACE DENTRO DE UN PROYECTO.

        Regla explícita del usuario tras el caso "CordycepsDev": «si el agente
        que se intenta crear no se ha podido asignar a un proyecto, la misión
        tiene que terminar eliminándolo antes de dejarlo ahí».

        Se aplica en el orden más fuerte posible — comprobar ANTES de crear, de
        modo que en el caso normal no haya nada que borrar:
          1. sin `project_id` → no se crea nada y se dice qué falta (la misión
             de un proyecto ya lo recibe inyectado por `toolloop`; en el chat
             general el modelo tiene `list_projects` y `ask_user` para
             resolverlo, en vez de suponer);
          2. `project_id` que no existe → tampoco se crea (la columna es un
             Integer suelto, sin FK: la BD aceptaría encantada un id fantasma);
          3. red de seguridad: si aun así el agente acabara sin vincular, se
             BORRA en el acto y se informa. Nunca se deja un huérfano detrás.

        El huérfano no era un detalle cosmético: su propio creador ya no podía
        ni configurarlo (`Authority` lo veía fuera de su proyecto), así que la
        misión se quedaba dando vueltas entre un agente que no podía tocar y un
        nombre que ya no podía reutilizar."""
        from app.agents.agent_manager import agent_manager
        from app.db.database import Project, SessionLocal

        missing = _missing(params, ["name"])
        if missing:
            return {"success": False, "result": None, "error": "faltan parámetros", "missing": missing}

        raw_project = params.get("project_id")
        if raw_project in (None, "", 0):
            return {"success": False, "result": None,
                    "error": ("un agente tiene que pertenecer a un proyecto: falta 'project_id'. "
                              "Consulta 'list_projects' y, si no sabes cuál quiere el usuario, "
                              "pregúntaselo con 'ask_user'. No se ha creado nada."),
                    "missing": ["project_id"]}
        try:
            project_id = int(raw_project)
        except (TypeError, ValueError):
            return {"success": False, "result": None,
                    "error": f"'project_id' debe ser un número entero, no {raw_project!r}. No se ha creado nada."}

        db = SessionLocal()
        try:
            if db.get(Project, project_id) is None:
                return {"success": False, "result": None,
                        "error": (f"el proyecto {project_id} no existe, así que el agente no se ha "
                                  f"creado. Comprueba el id con 'list_projects'.")}
        finally:
            db.close()

        try:
            agent = agent_manager.create_agent(
                name=params["name"], agent_type=params.get("agent_type", "generic"),
                description=params.get("description"), allowed_tools=params.get("allowed_tools"),
                project_id=project_id, skills=params.get("skills"),
            )
        except ValueError as e:
            return {"success": False, "result": None, "error": str(e)}

        if agent.project_id is None:
            agent_manager.delete_agent(agent.id)
            return {"success": False, "result": None,
                    "error": (f"el agente '{params['name']}' se creó sin quedar vinculado al proyecto "
                              f"{project_id}, así que se ha ELIMINADO para no dejarlo huérfano. "
                              f"Vuelve a intentarlo indicando el proyecto.")}
        return {"success": True, "result": {
            "id": agent.id, "name": agent.name, "project_id": agent.project_id,
        }, "error": None}

    async def _search_skills(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """[2026-08-02] Buscar en el catálogo REAL de skills antes de asignarlas.

        LA CAUSA RAÍZ QUE CIERRA (reportada por el usuario): el orquestador de un
        proyecto creaba agentes SIN skills y volcaba todo el diseño en la
        descripción. No era terquedad del modelo: el catálogo tiene 254 nombres
        exactos, no caben en el prompt, y `create_agent` solo decía "skills:
        lista de strings". Nadie puede elegir de una lista que no ve. La
        validación (PU2) rechazaba los inventados con candidatos, pero eso llega
        DESPUÉS del fallo; esto lo evita antes.

        Reusa `_match_category`/`_keyword_candidates`/`suggest` de
        `skills_catalog` — la misma maquinaria que ya alimenta las sugerencias
        del error, aquí como consulta de primera clase."""
        from app.agents import skills_catalog

        query = str(params.get("query") or "").strip()
        if not query:
            return {"success": False, "result": None, "error": "falta parámetros: query",
                    "missing": ["query"]}
        try:
            limit = max(1, min(int(params.get("limit") or 12), 40))
        except (TypeError, ValueError):
            limit = 12

        # 1) ¿Es una categoría entera? ("marketing", "engineering"…)
        cat = skills_catalog._match_category(query)
        encontradas = skills_catalog.skills_in_category(cat, limit=limit) if cat else []
        origen = f"categoría '{cat.get('label') or cat.get('key')}'" if cat else None
        # 2) Si no, palabra clave en nombre o descripción.
        if not encontradas:
            encontradas = skills_catalog._keyword_candidates(query, limit=limit)
            origen = f"coincidencias con '{query}'" if encontradas else None
        # 3) Ni eso: el nombre más parecido, para orientar.
        if not encontradas:
            parecidos = skills_catalog.suggest(query, limit=5)
            return {"success": True, "result": {
                "query": query, "skills": [], "categories": [
                    c.get("label") or c.get("key") for c in skills_catalog.list_categories()],
                "hint": (f"Ninguna skill casa con '{query}'. Nombres parecidos: "
                         f"{', '.join(parecidos)}." if parecidos else
                         f"Ninguna skill casa con '{query}'. Prueba con una de las categorías."),
            }, "error": None}

        return {"success": True, "result": {
            "query": query,
            "found_in": origen,
            "skills": [{"name": s.get("name"), "description": (s.get("description") or "")[:160]}
                       for s in encontradas],
            "hint": ("Pasa los 'name' TAL CUAL a create_agent/update_agent en el campo 'skills'. "
                     "Si alguna de éstas encaja razonablemente, úsala ya — no sigas buscando la "
                     "coincidencia perfecta, el catálogo no siempre la tiene."),
        }, "error": None}

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

    async def _ask_user_guard(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """`ask_user` la resuelve `toolloop` interceptándola ANTES de despachar
        (necesita esperar sin límite; aquí habría un timeout de 300 s). Si la
        ejecución llega hasta este punto es que se llamó desde fuera del bucle
        de tool-use, y eso hay que decirlo con claridad en vez de fingir."""
        return {"success": False, "result": None,
                "error": ("'ask_user' solo funciona dentro de una misión (el bucle de tool-use "
                          "es quien espera la respuesta del usuario, sin límite de tiempo). "
                          "Desde aquí no hay a quién preguntar.")}

    async def _update_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """[2026-08-02] Editar un agente YA CREADO (skills, proyecto, tools,
        nombre, descripción, activo).

        POR QUÉ EXISTE: sin esto, un agente creado con algún campo mal se
        quedaba así PARA SIEMPRE — el caso real reportado por el usuario:
        `create_agent` sin `project_id`/`skills`, el reintento con el mismo
        nombre reventando contra el índice único (`agents_name_key`), y ninguna
        acción de catálogo para arreglarlo. `agent_manager.update_agent` ya
        existía (lo usa `assign_tools`), solo que no estaba expuesta entera."""
        from app.agents.agent_manager import agent_manager

        missing = _missing(params, ["agent_id"])
        if missing:
            return {"success": False, "result": None, "error": "faltan parámetros", "missing": missing}
        campos = {k: params[k] for k in
                  ("name", "description", "agent_type", "skills", "allowed_tools",
                   "project_id", "icon", "is_active", "max_execution_time")
                  if k in params}
        if not campos:
            return {"success": False, "result": None,
                    "error": "no se indicó ningún campo que cambiar (name, description, agent_type, "
                             "skills, allowed_tools, project_id, icon, is_active, max_execution_time)"}
        try:
            agent = agent_manager.update_agent(int(params["agent_id"]), **campos)
        except ValueError as e:
            return {"success": False, "result": None, "error": str(e)}
        if agent is None:
            return {"success": False, "result": None, "error": f"agente {params['agent_id']} no existe"}
        return {"success": True, "result": {
            "id": agent.id, "name": agent.name, "project_id": agent.project_id,
            "skills": agent.skills or [], "allowed_tools": agent.allowed_tools,
            "is_active": agent.is_active,
        }, "error": None}

    async def _delete_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.agents.agent_manager import agent_manager

        missing = _missing(params, ["agent_id"])
        if missing:
            return {"success": False, "result": None, "error": "faltan parámetros", "missing": missing}
        try:
            ok = agent_manager.delete_agent(int(params["agent_id"]))
        except ValueError as e:      # el orquestador de un proyecto no se borra
            return {"success": False, "result": None, "error": str(e)}
        if not ok:
            return {"success": False, "result": None, "error": f"agente {params['agent_id']} no existe"}
        return {"success": True, "result": {"deleted": int(params["agent_id"])}, "error": None}

    async def _list_agents(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.agents.agent_manager import agent_manager

        project_id = params.get("project_id")
        agents = agent_manager.list_agents(project_id=int(project_id) if project_id else None)
        # [2026-08-02] Se devuelven TAMBIÉN project_id, skills, role y
        # allowed_tools. Antes el listado solo traía id/nombre/tipo/activo, así
        # que el modelo no tenía forma de VER que un agente había quedado sin
        # proyecto o sin skills: en el caso real reportado tuvo que deducirlo
        # ("project_id: parece no estar vinculado, el listado no lo muestra")
        # y encima acertó por casualidad. Un diagnóstico no debe ser una
        # conjetura cuando el dato existe.
        return {"success": True, "result": {"agents": [
            {"id": a.id, "name": a.name, "agent_type": a.agent_type, "is_active": a.is_active,
             "project_id": a.project_id, "skills": a.skills or [], "role": a.role,
             "allowed_tools": _json_list(a.allowed_tools)}
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

    # ------------------------------------------------------------------
    # Configuración de la app (idioma, modelo del chat)
    # ------------------------------------------------------------------

    async def _set_language(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Cambia `Config.app_language`. Acepta código (es/en/fr/pt) o nombre en
        varios idiomas. El frontend lee este Config al arrancar/refrescar; el
        idioma de respuesta del chat lo aplica `app.core.language` al instante."""
        from app.db.database import Config, SessionLocal

        raw = str(params.get("language") or "").strip().lower()
        alias = {
            "es": "es", "español": "es", "espanol": "es", "spanish": "es", "castellano": "es",
            "en": "en", "inglés": "en", "ingles": "en", "english": "en",
            "fr": "fr", "francés": "fr", "frances": "fr", "french": "fr", "français": "fr",
            "pt": "pt", "portugués": "pt", "portugues": "pt", "portuguese": "pt", "português": "pt",
        }
        code = alias.get(raw) or (raw[:2] if raw[:2] in ("es", "en", "fr", "pt") else None)
        if not code:
            return {"success": False, "result": None,
                    "error": f"idioma no soportado: {params.get('language')!r}. Usa es/en/fr/pt."}
        db = SessionLocal()
        try:
            row = db.query(Config).filter(Config.key == "app_language").first()
            if row:
                row.value = code
            else:
                db.add(Config(key="app_language", value=code))
            db.commit()
        finally:
            db.close()
        return {"success": True, "result": {"app_language": code}, "error": None}

    async def _set_chat_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fija el modelo PRIMARIO de la capacidad CHAT en la política activa del
        MEL — el mismo camino que Ajustes → Inteligencia (`set_policy_primary`),
        sin reimplementar nada."""
        from app.mel import (Capability, active_policy_name, resolve_model_name,
                             set_policy_primary)

        want = str(params.get("model") or "").strip()
        if not want:
            return {"success": False, "result": None, "error": "falta el parámetro 'model'"}
        ref = resolve_model_name(want)   # fuzzy: "minimax" -> ModelRef, o None
        if ref is None:
            return {"success": False, "result": None,
                    "error": f"no reconozco el modelo {want!r}. Dime uno de los conectados en Ajustes → Proveedores."}
        active = active_policy_name() or "economy"
        try:
            set_policy_primary(active, Capability.CHAT.value, ref.key)
        except Exception as e:
            return {"success": False, "result": None, "error": f"no se pudo fijar el modelo: {type(e).__name__}: {e}"}
        return {"success": True, "result": {"chat_model": ref.key, "policy": active}, "error": None}
