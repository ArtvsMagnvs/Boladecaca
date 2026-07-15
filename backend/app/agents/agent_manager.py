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
        """Ejecuta una tarea de agente: marca como running, llama a la IA
        para obtener el plan, ejecuta las tools via ToolManager, y
        persiste el resultado.

        V0.5 placeholder: la IA todavia no devuelve tool_calls estructurados.
        Por ahora, cuando un agente tiene tools permitidas, ejecutamos una
        accion "list_dir" del filesystem como demo end-to-end. En V0.6 esto
        vendra del LLM."""
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

                tool_calls_log = []
                result_text = ""

                # V0.5 placeholder de "decision de la IA": si el agente
                # tiene tools, demostramos que el engine funciona ejecutando
                # una accion segura por cada tool permitida. En V0.6 esto
                # vendra de la salida del LLM (function calling).
                if allowed_tools:
                    # Si tiene filesystem, listar el home.
                    if "filesystem" in allowed_tools:
                        r = await tool_manager.execute(
                            "filesystem", "list_dir",
                            {"path": "."},
                            allowed_tools=allowed_tools,
                            timeout=agent.max_execution_time,
                            agent_id=agent.id,
                            execution_id=execution.id,
                        )
                        tool_calls_log.append({"tool_id": "filesystem", "action": "list_dir", "ok": r["success"]})

                    # Si tiene powershell, listar scripts disponibles.
                    if "powershell" in allowed_tools:
                        r = await tool_manager.execute(
                            "powershell", "list_scripts", {},
                            allowed_tools=allowed_tools,
                            timeout=10,
                            agent_id=agent.id,
                            execution_id=execution.id,
                        )
                        tool_calls_log.append({"tool_id": "powershell", "action": "list_scripts", "ok": r["success"]})

                    # Si tiene git, status del repo (si existe .git en cwd).
                    if "git" in allowed_tools:
                        # Solo si el cwd es un repo.
                        import os
                        from pathlib import Path
                        if (Path.cwd() / ".git").exists():
                            r = await tool_manager.execute(
                                "git", "status", {"repo_path": "."},
                                allowed_tools=allowed_tools,
                                timeout=10,
                                agent_id=agent.id,
                                execution_id=execution.id,
                            )
                            tool_calls_log.append({"tool_id": "git", "action": "status", "ok": r["success"]})

                    result_text = (
                        f"Ejecutadas {len(tool_calls_log)} herramientas en demo V0.5. "
                        f"En V0.6 la IA decidira que tools llamar."
                    )
                else:
                    # Agente sin tools: solo refleja el system_prompt.
                    result_text = (
                        f"Agente '{agent.name}' (sin herramientas asignadas). "
                        f"System prompt: {agent.system_prompt or '(no definido)'[:200]}"
                    )

                execution.status = "completed"
                execution.result = result_text
                execution.tool_calls = json.dumps(tool_calls_log, ensure_ascii=False)
                execution.completed_at = datetime.utcnow()
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
