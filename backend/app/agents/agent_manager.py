# backend/app/agents/agent_manager.py
#
# V0.5 (Fase 2 AgentManager + ExecutionEngine): CRUD + lifecycle de agentes.
#
# Responsabilidad:
# - Crear / leer / actualizar / eliminar agentes (modelo Agent en BD).
# - Lanzar tareas sobre un agente (crea un AgentExecution, registra la
#   coroutine en asyncio y la monitoriza con un asyncio.Task).
# - Permitir cancelar tareas en curso (status='cancelled').
# - Traducir entre Agent (SQLAlchemy) y AgentResponse (Pydantic).
#
# Importante: el AgentManager NO decide QUE herramientas usar. Esa decision
# la toma la IA (en V0.5 sera un placeholder; en V0.6 vendra un agente LLM
# que devuelva una lista de tool_calls). Aqui solo EJECUTAMOS lo que la IA
# decidio, con todas las validaciones.

import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.db.database import SessionLocal
from app.db.models import Agent, AgentExecution
# V0.4 (Fase 2 AgentManager + ToolSystem): usamos ToolManager.
# V0.5 anade whitelist por agente + log de auditoria.
from app.tools import tool_manager


def _project_repo_path(project_id: int) -> Optional[str]:
    """Carpeta del proyecto, para acotar ahi las tools de archivos del agente
    (R4, doc 14 §4.3c). None si el proyecto no tiene `repo_path`: sin carpeta
    declarada no hay frontera de rutas que imponer."""
    try:
        from app.db.database import Project

        db = SessionLocal()
        try:
            project = db.get(Project, int(project_id))
            return (project.repo_path or None) if project else None
        finally:
            db.close()
    except Exception:
        return None


class AgentManager:
    """Gestiona el ciclo de vida de los agentes y sus ejecuciones."""

    def __init__(self):
        # Mapa execution_id -> asyncio.Task para poder cancelar.
        self._running_tasks: Dict[int, asyncio.Task] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def list_agents(self, only_active: bool = False, project_id: Optional[int] = None) -> List[Agent]:
        db = SessionLocal()
        try:
            q = db.query(Agent)
            if only_active:
                q = q.filter(Agent.is_active == True)  # noqa: E712
            # V0.87 (WPMS W2c): filtro para la seccion "Agentes" de una tarjeta.
            if project_id is not None:
                q = q.filter(Agent.project_id == project_id)
            return q.order_by(Agent.created_at.desc()).all()
        finally:
            db.close()

    def get_agent(self, agent_id: int) -> Optional[Agent]:
        db = SessionLocal()
        try:
            return db.query(Agent).filter(Agent.id == agent_id).first()
        finally:
            db.close()

    def create_agent(
        self,
        name: str,
        agent_type: str = "generic",
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
        max_execution_time: int = 300,
        is_active: bool = True,
        project_id: Optional[int] = None,
        skills: Optional[List[str]] = None,
        icon: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Agent:
        """Crea un agente y persiste en BD.

        Valida que todos los tool_id en allowed_tools EXISTAN en el
        ExecutionEngine; si alguno no existe, lanza ValueError."""
        if allowed_tools:
            available = {t["tool_id"] for t in tool_manager.list_tools()}
            unknown = set(allowed_tools) - available
            if unknown:
                raise ValueError(
                    f"Tools desconocidas en allowed_tools: {sorted(unknown)}. "
                    f"Disponibles: {sorted(available)}"
                )

        db = SessionLocal()
        try:
            agent = Agent(
                name=name,
                agent_type=agent_type,
                description=description,
                system_prompt=system_prompt,
                allowed_tools=json.dumps(allowed_tools or []),
                max_execution_time=max(1, min(max_execution_time, 3600)),
                is_active=is_active,
                project_id=project_id,
                skills=skills,
                icon=icon,
                role=role,
            )
            db.add(agent)
            db.commit()
            db.refresh(agent)
            return agent
        finally:
            db.close()

    def update_agent(self, agent_id: int, **kwargs) -> Optional[Agent]:
        """Actualiza campos del agente. Si se pasa allowed_tools, valida
        contra el catalogo del engine. Devuelve el Agent actualizado o None
        si no existe."""
        db = SessionLocal()
        try:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                return None

            if "allowed_tools" in kwargs and kwargs["allowed_tools"] is not None:
                tools = kwargs["allowed_tools"]
                if not isinstance(tools, list):
                    raise ValueError("allowed_tools debe ser una lista")
                available = {t["tool_id"] for t in tool_manager.list_tools()}
                unknown = set(tools) - available
                if unknown:
                    raise ValueError(
                        f"Tools desconocidas: {sorted(unknown)}. "
                        f"Disponibles: {sorted(available)}"
                    )
                kwargs["allowed_tools"] = json.dumps(tools)

            if "max_execution_time" in kwargs and kwargs["max_execution_time"] is not None:
                kwargs["max_execution_time"] = max(1, min(int(kwargs["max_execution_time"]), 3600))

            for k, v in kwargs.items():
                if v is not None and hasattr(agent, k):
                    setattr(agent, k, v)

            agent.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(agent)
            return agent
        finally:
            db.close()

    def delete_agent(self, agent_id: int) -> bool:
        """Elimina un agente. Si tiene ejecuciones en curso, las cancela."""
        db = SessionLocal()
        try:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                return False
            # Cancelar ejecuciones en curso.
            for ex in db.query(AgentExecution).filter(
                AgentExecution.agent_id == agent_id,
                AgentExecution.status.in_(["pending", "running"]),
            ).all():
                ex.status = "cancelled"
                ex.error_message = "agente eliminado"
                ex.completed_at = datetime.utcnow()
            # Cancelar asyncio tasks en memoria.
            for ex_id in list(self._running_tasks.keys()):
                task = self._running_tasks.get(ex_id)
                if task and not task.done():
                    task.cancel()
                self._running_tasks.pop(ex_id, None)

            db.delete(agent)
            db.commit()
            return True
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Ejecucion
    # ------------------------------------------------------------------

    def list_executions(
        self,
        agent_id: Optional[int] = None,
        limit: int = 50,
        only_status: Optional[str] = None,
    ) -> List[AgentExecution]:
        db = SessionLocal()
        try:
            q = db.query(AgentExecution)
            if agent_id is not None:
                q = q.filter(AgentExecution.agent_id == agent_id)
            if only_status:
                q = q.filter(AgentExecution.status == only_status)
            return q.order_by(AgentExecution.created_at.desc()).limit(max(1, min(limit, 200))).all()
        finally:
            db.close()

    def get_execution(self, execution_id: int) -> Optional[AgentExecution]:
        db = SessionLocal()
        try:
            return db.query(AgentExecution).filter(AgentExecution.id == execution_id).first()
        finally:
            db.close()

    def create_execution(self, agent_id: int, task: str) -> AgentExecution:
        """Crea un AgentExecution en estado 'pending' y lo lanza como
        asyncio.Task. Devuelve el registro persistido (status='pending'
        en este punto; pasara a 'running' cuando el task empiece)."""
        db = SessionLocal()
        try:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                raise ValueError(f"agente no existe: id={agent_id}")
            if not agent.is_active:
                raise ValueError(f"agente {agent_id} no esta activo")

            execution = AgentExecution(
                agent_id=agent_id,
                task_description=task,
                status="pending",
                created_at=datetime.utcnow(),
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)

            # Lanzamos el asyncio.Task y lo guardamos para poder cancelar.
            task_coro = self._run_execution(execution.id)
            async_task = asyncio.create_task(task_coro)
            self._running_tasks[execution.id] = async_task

            return execution
        finally:
            db.close()

    async def _run_execution(self, execution_id: int) -> None:
        """Ejecuta la tarea REAL que se le pidio al agente, delegando en el TIE.

        [R4, doc 23 Delta5] Hasta aqui esto era el placeholder de V0.5: ignoraba
        por completo `task_description` y ejecutaba una demo fija (`list_dir` /
        `list_scripts` / `git status`) segun que tools tuviera el agente. Las 14
        tools existian y eran asignables, pero ningun agente decidia cual usar.

        Ahora la tarea se convierte en una MISION del TIE: planner -> grafo ->
        bucle de tool-use (R1) -> responder. El agente hereda gratis las tools,
        el MEL, los gates de aprobacion y la traza.

        FRONTERA DE SEGURIDAD: se le pasan al TIE las `allowed_tools` del agente
        y su proyecto. Sin eso, delegar AMPLIARIA los permisos en silencio (el
        planner ve el catalogo entero por defecto)."""
        db = SessionLocal()
        try:
            execution = db.query(AgentExecution).filter(AgentExecution.id == execution_id).first()
            if not execution:
                return
            agent = db.query(Agent).filter(Agent.id == execution.agent_id).first()
            if not agent:
                execution.status = "failed"
                execution.error_message = "agente eliminado durante ejecucion"
                execution.completed_at = datetime.utcnow()
                db.commit()
                return

            execution.status = "running"
            execution.started_at = datetime.utcnow()
            db.commit()

            try:
                # Parsear allowed_tools (JSON string -> list).
                try:
                    allowed_tools = json.loads(agent.allowed_tools or "[]")
                except (ValueError, TypeError):
                    allowed_tools = []

                # Datos del agente ANTES de soltar la sesion: la mision puede
                # durar minutos y no queremos mantener una conexion abierta ni
                # arrastrar objetos ORM a otro contexto.
                agent_project_id = agent.project_id
                task_text = execution.task_description or ""

                mission = await self._delegate_to_tie(
                    task=task_text,
                    allowed_tools=allowed_tools,
                    project_id=agent_project_id,
                )

                # La mision puede acabar esperando una aprobacion del usuario
                # (gate del plan de T4a). Eso NO es "completada": el agente sigue
                # a la espera, y decir lo contrario seria mentir en la UI.
                if mission.state == "waiting":
                    execution.status = "running"
                    execution.result = mission.outcome or "Esperando tu aprobacion para continuar."
                else:
                    execution.status = "completed" if mission.state != "failed" else "failed"
                    execution.result = mission.outcome or ""
                    if mission.state == "failed":
                        execution.error_message = mission.outcome or "la mision no pudo completarse"
                    execution.completed_at = datetime.utcnow()

                execution.tool_calls = json.dumps(
                    self._tool_calls_of(mission), ensure_ascii=False, default=str
                )
                db.commit()

            except asyncio.CancelledError:
                execution.status = "cancelled"
                execution.error_message = "cancelado por el usuario"
                execution.completed_at = datetime.utcnow()
                db.commit()
                raise
            except Exception as e:
                execution.status = "failed"
                execution.error_message = f"{type(e).__name__}: {e}"
                execution.completed_at = datetime.utcnow()
                db.commit()
            finally:
                self._running_tasks.pop(execution_id, None)
        finally:
            db.close()

    async def _delegate_to_tie(self, *, task: str, allowed_tools: List[str],
                               project_id: Optional[int]):
        """Convierte la tarea del agente en una mision del TIE, acotada a lo que
        ese agente puede hacer.

        `allowed_tools` se pasa SIEMPRE, incluso vacia: una lista vacia significa
        "este agente no tiene herramientas" y el TIE lo respetara (el bucle de R1
        trata la whitelist vacia como 'ninguna', nunca como 'todas'). Pasar None
        aqui seria el agujero: el planner veria el catalogo entero."""
        import app.tie as tie

        repo_path = _project_repo_path(project_id) if project_id else None
        return await tie.submit_mission(
            task,
            source="agent",
            project_id=project_id,
            allowed_tools=list(allowed_tools),
            repo_path=repo_path,
        )

    @staticmethod
    def _tool_calls_of(mission) -> List[Dict[str, Any]]:
        """Rastro real de herramientas de la mision, leido del grafo que el
        executor dejo persistido (T3). Best-effort: si no se puede leer, se
        devuelve una lista vacia — el `result` de la ejecucion ya tiene el
        resumen, y perder el detalle no debe hacer fallar al agente."""
        try:
            from app.tie import tracer

            trace_id = tracer.trace_id_for_mission(mission.id)
            if not trace_id:
                return []
            graph = tracer.load_graph(trace_id)
            if graph is None:
                return []
            calls: List[Dict[str, Any]] = []
            for node in graph.nodes.values():
                for call in (node.tool_calls or []):
                    calls.append({"node": node.id, **call})
            return calls
        except Exception:
            return []

    def cancel_execution(self, execution_id: int) -> bool:
        """Cancela una ejecucion en curso."""
        task = self._running_tasks.get(execution_id)
        if task and not task.done():
            task.cancel()
        db = SessionLocal()
        try:
            execution = db.query(AgentExecution).filter(AgentExecution.id == execution_id).first()
            if not execution:
                return False
            if execution.status in ("pending", "running"):
                execution.status = "cancelled"
                execution.error_message = "cancelado por el usuario"
                execution.completed_at = datetime.utcnow()
                db.commit()
            return True
        finally:
            db.close()

    def delete_execution(self, execution_id: int) -> bool:
        """Elimina una ejecucion del historial. No cancela si esta en curso."""
        task = self._running_tasks.get(execution_id)
        if task and not task.done():
            task.cancel()
        self._running_tasks.pop(execution_id, None)
        db = SessionLocal()
        try:
            execution = db.query(AgentExecution).filter(AgentExecution.id == execution_id).first()
            if not execution:
                return False
            db.delete(execution)
            db.commit()
            return True
        finally:
            db.close()


# Singleton: una sola instancia por proceso.
agent_manager = AgentManager()
