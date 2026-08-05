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
# Importante: el AgentManager NO decide QUE herramientas usar ni COMO hacer la
# tarea. Desde R4 (doc 23) delega la ejecucion real en el TIE
# (`tie.submit_mission`) pasandole la whitelist de tools del agente y su
# proyecto: el agente hereda las 14 tools, el planner, el bucle de tool-use y el
# MEL sin logica propia. Lo que este modulo aporta es la FRONTERA — un agente
# nunca puede tocar mas de lo que tiene asignado.
#
# [Historico] Hasta R4 esto era el placeholder de V0.5: ignoraba la tarea del
# usuario y ejecutaba acciones de demo fijas (list_dir/list_scripts/git status)
# segun las tools asignadas. Ya no queda nada de eso.

import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.db.database import SessionLocal
from app.db.models import Agent, AgentExecution
# V0.4 (Fase 2 AgentManager + ToolSystem): usamos ToolManager.
# V0.5 anade whitelist por agente + log de auditoria.
from app.tools import tool_manager
# [2026-08-04] Solo la API pública del MEL (doc 16): `app.agents` nunca importa
# internos del MEL ni `ai_manager`. Sirve para decidir si el modelo elegido es
# un agente CLI autosuficiente, al que se le delega la tarea entera.
from app.mel import is_cli_agent_model as mel_is_cli_agent


def _tool_ids_existentes() -> set:
    """Las tools que EXISTEN de verdad, internas incluidas.

    [2026-08-02] La validación de `allowed_tools` miraba solo
    `tool_manager.list_tools()`, que excluye las internas — así que asignar
    `aithera` (interna) reventaba con "tool desconocida" aunque exista. Salió
    al dar TODAS las herramientas al orquestador. Lo que esta comprobación
    tiene que impedir es una tool INVENTADA, no una que existe.

    Que sea asignable por CÓDIGO no la hace visible en la UI: el catálogo que
    pinta el frontend sigue viniendo de `GET /api/tools/`, sin internas."""
    ids = {t["tool_id"] for t in tool_manager.list_tools()}
    try:
        return ids | tool_manager.internal_tool_ids()
    except Exception:
        return ids


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
        ExecutionEngine; si alguno no existe, lanza ValueError.

        [PU2, doc 35] Misma validación para `skills`, contra el catálogo real
        (`skills_catalog.py`) — antes cualquier string colaba, así que un
        agente creado por chat ("créame un agente con skills de X e Y") podía
        acabar con skills inventadas que no significaban nada. Se
        CANONICALIZA (respeta las mayúsculas reales del catálogo) antes de
        persistir. Cubre a la vez el endpoint HTTP y `aithera_tool.
        create_agent`: los dos llaman aquí."""
        if allowed_tools:
            available = _tool_ids_existentes()
            unknown = set(allowed_tools) - available
            if unknown:
                raise ValueError(
                    f"Tools desconocidas en allowed_tools: {sorted(unknown)}. "
                    f"Disponibles: {sorted(available)}"
                )
        if skills:
            from app.agents import skills_catalog

            skills = skills_catalog.validate_skills(skills)

        db = SessionLocal()
        try:
            # [2026-08-02] `agents.name` es UNIQUE. Chocar contra ese índice
            # levantaba un `IntegrityError` crudo que NADIE traducía: ni el
            # endpoint HTTP (solo captura ValueError) ni `aithera_tool.
            # _create_agent`. El modelo recibía un error de driver
            # ininteligible y se ponía a dar vueltas probando variantes en vez
            # de ver lo único que importaba: ya existe uno con ese nombre, y
            # cuál es su id (que es justo lo que necesita para corregirlo con
            # `update_agent`). Se comprueba ANTES de insertar — así el mensaje
            # puede llevar el id, y de paso no se ensucia la sesión con un
            # rollback.
            clash = db.query(Agent).filter(Agent.name == name).first()
            if clash is not None:
                raise ValueError(
                    f"ya existe un agente llamado '{name}' (id {clash.id}, "
                    f"project_id={clash.project_id}). Los nombres son únicos: usa "
                    f"'update_agent' sobre el id {clash.id} para corregirlo, o elige otro nombre."
                )
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
                # [2026-08-02] Al ORQUESTADOR no se le quitan herramientas
                # (petición explícita del usuario). Se deja pasar la escritura
                # que le pone TODAS —es la que usa `ensure_orchestrator` para
                # re-sincronizar— y se rechaza cualquier recorte.
                if agent.role == "orchestrator":
                    # Por el barrel, no por el interno: `app.tie.authority` es
                    # privado del TIE (doc 16, lo vigila test_module_boundaries).
                    from app.tie import orchestrator_tools

                    completas = set(orchestrator_tools())
                    if not completas.issubset(set(tools)):
                        raise ValueError(
                            f"'{agent.name}' es el orquestador de su proyecto: siempre tiene todas "
                            f"las herramientas y no se le pueden quitar. Su alcance lo limita la "
                            f"carpeta del proyecto, no la lista de tools."
                        )
                available = _tool_ids_existentes()
                unknown = set(tools) - available
                if unknown:
                    raise ValueError(
                        f"Tools desconocidas: {sorted(unknown)}. "
                        f"Disponibles: {sorted(available)}"
                    )
                kwargs["allowed_tools"] = json.dumps(tools)

            if "skills" in kwargs and kwargs["skills"] is not None:
                from app.agents import skills_catalog

                if not isinstance(kwargs["skills"], list):
                    raise ValueError("skills debe ser una lista")
                kwargs["skills"] = skills_catalog.validate_skills(kwargs["skills"])

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
        """Elimina un agente. Si tiene ejecuciones en curso, las cancela.

        [2026-08-02] EL ORQUESTADOR DE UN PROYECTO NO SE BORRA (petición
        explícita del usuario: "todo proyecto tiene su orquestador"). Se lanza
        `ValueError` en vez de devolver False para que la diferencia entre "no
        existe" y "no se puede" llegue clara al endpoint, al chat y a la UI."""
        db = SessionLocal()
        try:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                return False
            if agent.role == "orchestrator":
                raise ValueError(
                    f"'{agent.name}' es el orquestador de su proyecto y no se puede eliminar: "
                    f"todo proyecto tiene el suyo. Si ya no lo quieres activo, desactívalo."
                )
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

    def reconcile_orphan_executions(self) -> int:
        """[FIX 2026-08-02] Cierra las ejecuciones que quedaron colgadas de un
        proceso que ya no existe. Se llama UNA vez al arrancar.

        EL FALLO REAL (reportado por el usuario): en la tarjeta del proyecto
        Cordyceps, el orquestador y el investigador aparecian "escribiendo…"
        indefinidamente. La UI pinta ese indicador cuando el agente tiene una
        `AgentExecution` en `pending`/`running` (W2e), y habia DOS filas asi:
        una desde el 28-jul y otra desde el 1-ago.

        LA CAUSA: `status='running'` es la afirmacion de que hay una
        `asyncio.Task` viva trabajando en ello. Al reiniciar el backend —algo
        que en este proyecto pasa constantemente— esa task muere con el
        proceso, pero NADIE tocaba la fila: se quedaba diciendo "running" para
        siempre. El TIE ya tenia su reconciliacion de arranque
        (`executor.resume_pending`, T3); las ejecuciones de agente no tenian
        ninguna.

        Se marcan como `failed`, no como `cancelled`: el usuario no las
        cancelo, se interrumpieron. Y no se intenta reanudarlas — la corrutina
        que esperaba el resultado ya no existe, asi que fingir que siguen vivas
        seria repetir el mismo problema con otro nombre. Si la MISION del TIE
        que habia detras era reanudable, el TIE la reanuda por su cuenta y se
        ve en Mission Control."""
        db = SessionLocal()
        try:
            huerfanas = db.query(AgentExecution).filter(
                AgentExecution.status.in_(["pending", "running"])).all()
            for ex in huerfanas:
                ex.status = "failed"
                ex.error_message = (
                    "Interrumpida al reiniciarse el backend. Vuelve a lanzarla "
                    "si sigue haciendo falta."
                )
                ex.completed_at = datetime.utcnow()
            if huerfanas:
                db.commit()
            return len(huerfanas)
        except Exception as e:      # noqa: BLE001 — arrancar nunca debe romperse por esto
            db.rollback()
            import logging

            logging.getLogger("aithera").error(
                f"[agent_manager] no se pudieron reconciliar las ejecuciones huerfanas: {e!r}")
            return 0
        finally:
            db.close()

    def create_execution(self, agent_id: int, task: str,
                         model: Optional[str] = None) -> AgentExecution:
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
                model=model or None,
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
                agent_skills = list(agent.skills) if agent.skills else None
                # [2026-08-02] Carpetas extra concedidas a mano + politica de
                # aprobacion de ESTE agente (el selector del chat).
                agent_extra_paths = list(agent.extra_paths) if agent.extra_paths else None
                agent_autonomy = agent.autonomy or "manual"
                # El modelo que el usuario eligio para ESTE mensaje viaja en la
                # propia ejecucion (columna `model`), no en el agente: es una
                # decision por interaccion, no una configuracion.
                model = getattr(execution, "model", None) or None
                # [2026-08-02] El prompt de comportamiento del agente (lo unico
                # editable del ORQUESTADOR, y opcional para cualquier otro
                # agente) — viajaba en BD desde hacia tiempo pero nadie lo leia
                # al ejecutar.
                agent_prompt = agent.system_prompt or None
                task_text = execution.task_description or ""

                # [hotfix 2026-08-02] SOLTAR LA SESIÓN ANTES DE LA MISIÓN.
                #
                # EL BUG (reportado por el usuario: "en el chat pone
                # 'trabajando' desde hace rato, pero la misión ya sale como
                # completada"): el comentario de arriba decía desde siempre que
                # no se quería "mantener una conexión abierta" durante la
                # misión... pero el código NO lo hacía: `db` seguía abierta y
                # `execution` era un objeto ORM atado a ella durante MINUTOS
                # (una misión con gates puede durar horas). Si esa conexión se
                # perdía por el camino —timeout de Postgres, reciclado del
                # pool—, el `db.commit()` final fallaba, y el `except` que debía
                # marcarla como fallida usaba LA MISMA sesión rota, así que
                # también reventaba: la fila se quedaba en "running" PARA
                # SIEMPRE. La misión terminaba bien, pero el chat seguía
                # diciendo "Trabajando…" eternamente.
                #
                # Ahora la sesión se cierra aquí y el resultado se escribe con
                # una sesión NUEVA (`_finish_execution`), que además es
                # idempotente y no depende de nada vivo desde antes del await.
                db.close()
                db = None

                # [2026-08-02] RASTRO EN VIVO. El chat del orquestador sondea
                # esta fila (no hay SSE por aqui), asi que las frases de "lo
                # que estoy haciendo" hay que PERSISTIRLAS segun llegan. La
                # cola se liga ANTES de crear la tarea de drenaje y de lanzar
                # la mision: las dos heredan el contexto y comparten cola.
                from app.tie import progress as _progress

                cola = _progress.bind()
                drenador = asyncio.ensure_future(
                    self._drain_progress(execution_id, cola))
                try:
                    mission = await self._delegate_to_tie(
                        task=task_text,
                        allowed_tools=allowed_tools,
                        project_id=agent_project_id,
                        skills=agent_skills,
                        extra_paths=agent_extra_paths,
                        autonomy=agent_autonomy,
                        model=model,
                        agent_prompt=agent_prompt,
                    )
                finally:
                    drenador.cancel()
                    _progress.unbind()

                # La mision puede acabar esperando una aprobacion del usuario
                # (gate del plan de T4a). Eso NO es "completada": el agente sigue
                # a la espera, y decir lo contrario seria mentir en la UI.
                if mission.state == "waiting":
                    self._finish_execution(
                        execution_id, status="running",
                        result=mission.outcome or "Esperando tu aprobacion para continuar.",
                        tool_calls=self._tool_calls_of(mission), completed=False,
                    )
                else:
                    fallo = mission.state == "failed"
                    self._finish_execution(
                        execution_id, status="failed" if fallo else "completed",
                        result=mission.outcome or "",
                        error=(mission.outcome or "la mision no pudo completarse") if fallo else None,
                        tool_calls=self._tool_calls_of(mission), completed=True,
                    )

            except asyncio.CancelledError:
                self._finish_execution(execution_id, status="cancelled",
                                       error="cancelado por el usuario", completed=True)
                raise
            except Exception as e:
                self._finish_execution(execution_id, status="failed",
                                       error=f"{type(e).__name__}: {e}", completed=True)
            finally:
                self._running_tasks.pop(execution_id, None)
        finally:
            if db is not None:
                db.close()

    @staticmethod
    async def _drain_progress(execution_id: int, cola) -> None:
        """[2026-08-02] Vuelca el rastro de la mision en la fila de la ejecucion
        segun llega, para que el chat del orquestador (que SONDEA, no escucha un
        stream) pueda pintarlo en vivo.

        Best-effort de principio a fin: es observacion. Se agrupan las lineas
        que lleguen juntas para no escribir en BD una vez por frase, y cualquier
        fallo de escritura se traga — narrar jamas puede tumbar una mision.
        Termina por cancelacion cuando la mision acaba (el caller la cancela)."""
        import json as _json

        lineas: List[str] = []
        try:
            while True:
                lineas.append(await cola.get())
                # Ráfaga: se recoge lo que ya esté en la cola sin esperar más.
                while not cola.empty():
                    try:
                        lineas.append(cola.get_nowait())
                    except Exception:
                        break
                db = SessionLocal()
                try:
                    ex = db.query(AgentExecution).filter(
                        AgentExecution.id == execution_id).first()
                    if ex is not None:
                        ex.progress = _json.dumps(lineas[-200:], ensure_ascii=False)
                        db.commit()
                except Exception:
                    db.rollback()
                finally:
                    db.close()
        except asyncio.CancelledError:
            raise
        except Exception:
            return

    @staticmethod
    def _finish_execution(execution_id: int, *, status: str, result: Optional[str] = None,
                          error: Optional[str] = None, tool_calls: Optional[List[Dict[str, Any]]] = None,
                          completed: bool = True) -> None:
        """[hotfix 2026-08-02] Escribe el desenlace de una ejecucion con una
        sesion NUEVA y de vida corta.

        Es la otra mitad del arreglo de "Trabajando… para siempre": antes esto
        se hacia sobre la sesion abierta ANTES de la mision, que podia llevar
        minutos u horas muerta. Al abrir una sesion aqui, el resultado se
        persiste aunque la conexion original se haya perdido — y si algo falla,
        falla SOLO el registro, nunca deja la fila a medias en un estado
        intermedio invisible."""
        db = SessionLocal()
        try:
            execution = db.query(AgentExecution).filter(AgentExecution.id == execution_id).first()
            if execution is None:
                return
            execution.status = status
            if result is not None:
                execution.result = result
            if error is not None:
                execution.error_message = error
            if tool_calls is not None:
                execution.tool_calls = json.dumps(tool_calls, ensure_ascii=False, default=str)
            if completed:
                execution.completed_at = datetime.utcnow()
            db.commit()
        except Exception as e:      # noqa: BLE001 — registrar nunca debe propagar
            import logging

            logging.getLogger("aithera").error(
                f"[agent_manager] no se pudo cerrar la ejecucion {execution_id}: {e!r}"
            )
        finally:
            db.close()

    async def _delegate_to_tie(self, *, task: str, allowed_tools: List[str],
                               project_id: Optional[int],
                               skills: Optional[List[str]] = None,
                               extra_paths: Optional[List[str]] = None,
                               autonomy: Optional[str] = None,
                               model: Optional[str] = None,
                               agent_prompt: Optional[str] = None):
        """Convierte la tarea del agente en una mision del TIE, acotada a lo que
        ese agente puede hacer.

        `allowed_tools` se pasa SIEMPRE, incluso vacia: una lista vacia significa
        "este agente no tiene herramientas" y el TIE lo respetara (el bucle de R1
        trata la whitelist vacia como 'ninguna', nunca como 'todas'). Pasar None
        aqui seria el agujero: el planner veria el catalogo entero.

        `skills` [PU2, doc 35]: las especialidades del agente (ya validadas
        contra el catalogo al crear/editar el agente). Antes de PU2 se
        guardaban en BD y morian ahi — este parametro es lo que las hace
        llegar de verdad al contexto de ejecucion (ver `executor._execute_node`).

        `agent_prompt` [2026-08-02]: el prompt de comportamiento libre del
        agente (`Agent.system_prompt`) — mismo canal y mismo destino que
        `skills`. Antes este campo existia en el schema/BD pero no lo leia
        NADIE al ejecutar; ahora llega al mismo bloque de contexto."""
        import app.tie as tie

        repo_path = _project_repo_path(project_id) if project_id else None

        # [2026-08-04, corrección de diseño del usuario] AGENTE CLI = SE LE
        # DELEGA LA TAREA ENTERA, no se le mete en el bucle de tools.
        #
        # Claude Code y Codex YA SON agentes: leen y escriben ficheros, ejecutan
        # comandos y buscan en el repo con SUS propias herramientas. Meterlos en
        # el bucle de Aithera era envolver un agente dentro de otro — de ahí
        # salían las respuestas del tipo "soy Claude Code, no tengo acceso a...":
        # se les pedía usar herramientas ajenas teniendo las suyas.
        #
        # Aquí se les da la tarea y la CARPETA DEL PROYECTO, y su salida vuelve
        # tal cual al chat del agente. Que se presenten como "Claude" da igual;
        # lo que importa es que el trabajo quede hecho donde toca.
        if mel_is_cli_agent(model):
            return await self._delegate_to_cli_agent(
                task=task, model=model, repo_path=repo_path,
                skills=skills, agent_prompt=agent_prompt,
            )

        return await tie.submit_mission(
            task,
            source="agent",
            project_id=project_id,
            allowed_tools=list(allowed_tools),
            repo_path=repo_path,
            skills=skills,
            # [2026-08-02] Carpetas extra concedidas a mano, politica de
            # aprobacion de ESTE agente, y el modelo que el usuario eligio en
            # el selector del chat para ESTE mensaje.
            extra_paths=extra_paths,
            autonomy=autonomy,
            model=model,
            agent_prompt=agent_prompt,
        )

    async def _delegate_to_cli_agent(self, *, task: str, model: str,
                                     repo_path: Optional[str],
                                     skills: Optional[List[str]] = None,
                                     agent_prompt: Optional[str] = None):
        """[2026-08-04] Delega la tarea COMPLETA a un agente CLI (Claude Code,
        Codex) trabajando en la carpeta del proyecto.

        No hay planner, ni grafo, ni bucle de tools de Aithera: ese es justo el
        punto. El CLI recibe el encargo y lo resuelve con SUS herramientas en
        `repo_path`; su salida vuelve tal cual al chat del agente.

        La capacidad que se pide es CODE (no AGENTIC): AGENTIC significa "usa el
        bucle de herramientas de Aithera", que es exactamente lo que aquí NO se
        quiere — y por eso el veto de AGENTIC para estos proveedores sigue
        siendo correcto y se mantiene intacto.

        Devuelve un objeto con la misma forma mínima que una misión
        (`state`/`outcome`/`id`) para que `_run_execution` no tenga que
        distinguir de dónde vino el resultado."""
        from dataclasses import dataclass

        import app.mel as mel

        @dataclass
        class _CliRun:
            id: str
            state: str
            outcome: str

        # El encargo lleva delante quién es y dónde trabaja. Sin la carpeta, el
        # CLI trabajaría donde corra el backend — eso sí sería un fallo grave,
        # así que se dice explícitamente cuando no la hay.
        partes: List[str] = []
        if agent_prompt:
            partes.append(agent_prompt.strip())
        if skills:
            partes.append("Tus especialidades: " + ", ".join(skills) + ".")
        if repo_path:
            partes.append(f"Trabajas dentro de la carpeta del proyecto: {repo_path}. "
                          "Usa tus propias herramientas para leerla y modificarla.")
        else:
            partes.append("Este proyecto no tiene carpeta asignada, así que NO "
                          "modifiques ficheros: responde solo con lo que se te pide.")
        system_prompt = "\n\n".join(partes) or None

        res = await mel.complete(mel.ExecutionRequest(
            capability=mel.Capability.CODE,
            prompt=task,
            system_prompt=system_prompt,
            model_override=model,
            workdir=repo_path,
        ))

        texto = (res.text or "").strip()
        if not res.ok or not texto:
            return _CliRun(id="", state="failed",
                           outcome=res.error or "el agente CLI no devolvió respuesta")
        return _CliRun(id="", state="done", outcome=texto)

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
