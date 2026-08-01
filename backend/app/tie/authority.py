# app/tie/authority.py — la frontera de autoridad de una misión (R4, doc 23 Δ6)
#
# EL PROBLEMA QUE RESUELVE: desde R4 un agente ya no ejecuta una demo fija, sino
# una misión REAL del TIE con el bucle de tool-use de R1. Eso significa que un
# modelo elige herramientas en tiempo de ejecución. Sin una frontera explícita,
# delegar en el TIE AMPLÍA permisos en silencio: un agente al que el usuario dio
# solo `filesystem` acabaría con acceso al catálogo entero, y el orquestador de
# un proyecto podría tocar los agentes y las carpetas de otro.
#
# DÓNDE VIVE (decisión de diseño, R4): la autoridad viaja DENTRO del TaskGraph,
# que es lo que el executor persiste en `orchestrator_traces.plan` en cada
# transición (T3). No en la `Mission`, que es implícita y se reconstruye al
# reanudar a partir de `tracer.get_meta()` — solo mission_id/channel/state. Una
# frontera que viviera solo en memoria DESAPARECERÍA al reiniciar el backend, y
# la misión reanudada correría sin límites. Guardarla en el grafo la hace
# correcta por construcción también en el camino de `resume_pending()`.
#
# POR QUÉ AQUÍ SE DENIEGA Y NO SE PREGUNTA (matiz importante frente a la regla
# del usuario de 2026-07-19, "siempre preguntar, nunca denegar en silencio"):
# esa regla gobierna los PERMISOS — cosas que el usuario puede conceder, y que
# por tanto hay que preguntarle (lo hace `toolloop._ask_permission` vía el
# ApprovalGate). La autoridad es otra cosa: es el ALCANCE del encargo. Que el
# orquestador del proyecto A toque los agentes del proyecto B no es un permiso
# que al usuario se le olvidó dar, es algo fuera de lo que pidió. Preguntarlo
# sería ruido. Lo que sí se respeta al 100% es la otra mitad de la regla: NADA
# se deniega en silencio — el motivo vuelve al modelo como observación, queda en
# `tool_calls` y por tanto en la traza de la misión, y acaba en la respuesta
# final. El usuario siempre se entera.
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

# Acciones de `aithera_tool` (R3) que operan sobre UN agente concreto. Para
# éstas hay que comprobar que el agente objetivo pertenece al mismo proyecto.
# [2026-08-02] `update_agent`/`delete_agent` entran AQUÍ el mismo día que se
# exponen como acciones de `aithera_tool`: son las dos operaciones más
# peligrosas sobre un agente (reconfigurarlo o borrarlo), así que sin esta
# línea el orquestador del proyecto A podría editar o eliminar los agentes del
# proyecto B — exactamente la brecha que `_check_project_scope` existe para
# cerrar. Una acción nueva sobre un agente concreto SIEMPRE se añade aquí.
_AITHERA_AGENT_ACTIONS = {"assign_tools", "run_agent_task", "update_agent", "delete_agent"}

# Tools cuyo alcance es el sistema de archivos: si la misión tiene una carpeta
# de proyecto asignada, no pueden salirse de ella.
#
# [2026-07-27, doc 34 — bug reportado en vivo] Este dict solo cubría
# `filesystem`/`git`. `document` (lectura/escritura de .docx/.xlsx/.pdf) y
# `download` (descarga a disco) escriben archivos exactamente igual que
# `filesystem.write_file`, pero como no estaban aquí, un agente con carpeta de
# proyecto asignada podía escribir un .docx fuera de esa carpeta sin que
# `Authority.check()` lo viera — el caso real: un agente del proyecto
# "Cordyceps" escribió `Cordyceps_Wiki.docx` en `C:\Users\...\` en vez de
# dentro de la carpeta del proyecto. `browser` se añade también, pero SOLO
# para sus dos acciones que bajan algo a disco (`download_file`/
# `upload_file`, únicas con parámetro `path`); navegar/hacer clic/escribir en
# una web sigue sin restricción de carpeta a propósito (el usuario lo pidió
# explícitamente: "aunque hagan búsquedas web fuera de la carpeta" — internet
# es externo por naturaleza, el disco local no).
_PATH_PARAMS = {
    "filesystem": ("path", "src", "dest"),
    "git": ("repo_path",),
    "document": ("path",),
    "download": ("path",),
    "browser": ("path",),
}


@dataclass(frozen=True)
class Authority:
    """El alcance de una misión. Todos los campos son OPCIONALES y `None`
    significa "sin restricción por este eje" — así el chat del usuario (que no
    tiene ninguna frontera) sigue funcionando exactamente igual que antes, sin
    ninguna regresión.

    - `allowed_tools`: la whitelist heredada del agente. Se aplica en el
      planner (clamp del grafo) y de nuevo aquí; ver `check`.
    - `project_id`: el orquestador/agente solo puede tocar agentes de ESTE
      proyecto.
    - `repo_path`: las tools de archivos no pueden salir de esta carpeta.
    - `skills` [PU2, doc 35]: NO es una frontera de seguridad — es descriptivo
      (las especialidades del agente, del catálogo de `skills_catalog.py`).
      Vive aquí, no en un campo nuevo de `TaskGraph`, porque `Authority` ya es
      el único vehículo que sobrevive al checkpoint y llega a CADA nodo
      (`graph.authority` → `AgentTask.authority`, T3/T4a) — reusar el canal
      que ya existe es más simple que inventar uno paralelo para lo mismo.
      Nunca participa en `check()` ni en `is_unrestricted`: una misión con
      SOLO skills (sin tools/proyecto/carpeta) sigue sin restricción."""

    project_id: Optional[int] = None
    repo_path: Optional[str] = None
    allowed_tools: Optional[list[str]] = field(default=None)
    skills: Optional[list[str]] = field(default=None)

    @property
    def is_unrestricted(self) -> bool:
        return self.project_id is None and self.repo_path is None and self.allowed_tools is None

    def to_dict(self) -> dict:
        return {"project_id": self.project_id, "repo_path": self.repo_path,
                "allowed_tools": list(self.allowed_tools) if self.allowed_tools is not None else None,
                "skills": list(self.skills) if self.skills is not None else None}

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "Authority":
        if not d:
            return cls()
        tools = d.get("allowed_tools")
        skills = d.get("skills")
        return cls(
            project_id=d.get("project_id"),
            repo_path=d.get("repo_path"),
            allowed_tools=[str(t) for t in tools] if isinstance(tools, list) else None,
            skills=[str(s) for s in skills] if isinstance(skills, list) else None,
        )

    # ------------------------------------------------------------------

    def check(self, tool_id: str, action: str, params: dict) -> Optional[str]:
        """¿Puede esta misión ejecutar esto? Devuelve `None` si sí, o el MOTIVO
        (texto legible, accionable) si no.

        El motivo se le devuelve al modelo tal cual, así que tiene que explicar
        el límite lo bastante bien como para que pueda buscar otra vía o
        contárselo al usuario."""
        if self.is_unrestricted:
            return None

        # Las tools INTERNAS (operar la propia Aithera) no pasan por la whitelist
        # del agente: no son capacidades concedidas, son de la casa. Sí siguen
        # sujetas a la frontera de proyecto de más abajo, que es lo que impide
        # que el orquestador de un proyecto toque otro.
        if (self.allowed_tools is not None
                and tool_id not in self.allowed_tools
                and tool_id not in _internal_tool_ids()):
            permitidas = ", ".join(self.allowed_tools) if self.allowed_tools else "(ninguna)"
            return (f"'{tool_id}' está fuera de las herramientas de este encargo. "
                    f"Permitidas: {permitidas}.")

        if self.project_id is not None and tool_id == "aithera":
            reason = self._check_project_scope(action, params)
            if reason:
                return reason

        if self.repo_path:
            reason = self._check_path_scope(tool_id, params)
            if reason:
                return reason

        return None

    # ------------------------------------------------------------------

    def _check_project_scope(self, action: str, params: dict) -> Optional[str]:
        """Un agente/orquestador con proyecto asignado solo manda sobre lo de su
        propio proyecto (doc 14 §4.3c)."""
        if action in _AITHERA_AGENT_ACTIONS:
            # [2026-08-02] El DESTINO de un `update_agent` también es alcance.
            # Hasta aquí solo se miraba de quién ERA el agente, así que el
            # orquestador del proyecto A podía coger un agente suyo y, con
            # `project_id=B`, REGALÁRSELO a otro proyecto — la misma frontera
            # que este método existe para cerrar, saltada por el otro lado.
            # También es lo que hace segura la adopción de un huérfano de más
            # abajo: solo se puede adoptar HACIA el proyecto propio.
            destino = params.get("project_id")
            if destino is not None and not _same_project(destino, self.project_id):
                return (f"no puedes mover un agente al proyecto {destino}: tu autoridad se "
                        f"limita a tu propio proyecto (id {self.project_id}).")

            agent_id = params.get("agent_id")
            if agent_id is None:
                return None      # sin objetivo concreto: lo rechazará la propia tool por `missing`
            found, owner = _agent_owner(agent_id)
            if not found:
                # No se pudo leer: fail-closed, igual que el resto del módulo.
                return (f"no he podido comprobar a qué proyecto pertenece el agente {agent_id}. "
                        f"Compruébalo con 'list_agents' antes de tocarlo.")
            if owner is None:
                # [2026-08-02] AGENTE SIN PROYECTO. No pertenece a nadie, así
                # que tocarlo no cruza ninguna frontera — y bloquearlo era lo
                # que dejaba la misión en un callejón sin salida: el agente
                # huérfano ni se podía configurar ni se podía reutilizar su
                # nombre (es único), así que el modelo daba vueltas entre las
                # dos paredes. Adoptarlo solo puede llevarlo a ESTE proyecto,
                # por la comprobación de destino de arriba.
                return None
            if not _same_project(owner, self.project_id):
                return (f"el agente {agent_id} no pertenece a este proyecto "
                        f"(id {self.project_id}); tu autoridad se limita a los agentes de tu "
                        f"propio proyecto. Informa al usuario en vez de intentarlo por otra vía.")
            return None

        # Acciones que nombran un proyecto explícitamente (crear tarea/hito,
        # consultar estado…): tiene que ser el suyo.
        target = params.get("project_id")
        if target is not None and not _same_project(target, self.project_id):
            return (f"el proyecto {target} no es el tuyo (id {self.project_id}); "
                    f"tu autoridad se limita a tu propio proyecto.")
        return None

    def _check_path_scope(self, tool_id: str, params: dict) -> Optional[str]:
        """Las tools de archivos quedan dentro de la carpeta del proyecto."""
        keys = _PATH_PARAMS.get(tool_id)
        if not keys:
            return None
        raiz = os.path.abspath(os.path.expanduser(self.repo_path))
        for key in keys:
            value = params.get(key)
            if not value or not isinstance(value, str):
                continue
            destino = os.path.abspath(os.path.expanduser(value))
            # `commonpath` sobre rutas ya normalizadas cierra el `..`: no basta
            # con `startswith`, que dejaría pasar "/repo-otro" como hijo de "/repo".
            try:
                dentro = os.path.commonpath([raiz, destino]) == raiz
            except ValueError:      # unidades distintas en Windows (C: vs D:)
                dentro = False
            if not dentro:
                return (f"la ruta '{value}' está fuera de la carpeta de este proyecto "
                        f"({self.repo_path}). No puedes salir de ahí.")
        return None


def _same_project(a: Any, b: Any) -> bool:
    """¿Los dos ids apuntan al mismo proyecto? Un valor que ni siquiera es un
    número entero NO es el proyecto propio (fail-closed): un `int()` suelto
    sobre lo que dijo el modelo levantaría un ValueError que reventaría el
    `check()` entero en vez de denegar limpiamente."""
    try:
        return int(a) == int(b)
    except (TypeError, ValueError):
        return False


def _internal_tool_ids() -> set:
    """Tools internas de Aithera (ver `BaseTool.internal`). Ante cualquier fallo
    devuelve un conjunto vacío: eso hace que la whitelist se aplique tal cual, es
    decir, MÁS restrictivo — fail-closed, igual que el resto de este módulo."""
    try:
        from app.tools import tool_manager

        return tool_manager.internal_tool_ids()
    except Exception:
        return set()


def orchestrator_of(project_id: int) -> Optional[dict]:
    """El agente ORQUESTADOR de un proyecto, si lo hay (doc 14 §4.3c): un agente
    activo de ese proyecto con `role="orchestrator"`. La columna `Agent.role`
    existe desde V0.87 (W2e) pero hasta R4 no tenía ninguna lógica detrás.

    Devuelve `{id, name, allowed_tools, repo_path}` — un dict y no el objeto ORM
    a propósito: quien lo usa lo hace fuera de la sesión de BD.

    Si un proyecto tuviera VARIOS orquestadores (la UI no lo impide), se coge el
    más antiguo: determinista, y evita que crear uno nuevo cambie en silencio
    quién manda."""
    try:
        import json as _json

        from app.db.database import Agent, Project, SessionLocal

        db = SessionLocal()
        try:
            agent = (db.query(Agent)
                       .filter(Agent.project_id == project_id,
                               Agent.role == "orchestrator",
                               Agent.is_active.is_(True))
                       .order_by(Agent.id.asc())
                       .first())
            if agent is None:
                return None
            try:
                tools = _json.loads(agent.allowed_tools or "[]")
            except (ValueError, TypeError):
                tools = []
            project = db.get(Project, project_id)
            return {
                "id": agent.id,
                "name": agent.name,
                "allowed_tools": tools if isinstance(tools, list) else [],
                "repo_path": (project.repo_path or None) if project else None,
            }
        finally:
            db.close()
    except Exception:
        return None


# [hotfix 2026-08-02] Herramientas con las que nace un orquestador creado
# automáticamente. Deliberadamente MÍNIMAS, porque el usuario acotó el encargo:
# "que SOLO pueda dar órdenes a los agentes de ese proyecto y trabajar sobre la
# carpeta del proyecto".
#   · dar órdenes a sus agentes → NO hace falta listarla: `aithera` es una tool
#     INTERNA y `Authority.check` la deja pasar siempre (no es una capacidad
#     concedida, es de la casa), pero SÍ queda sujeta a `_check_project_scope`,
#     que es justo lo que impide que toque agentes de otro proyecto.
#   · trabajar sobre la carpeta → `filesystem` + `document`, ambas en
#     `_PATH_PARAMS`, así que `_check_path_scope` las encierra en `repo_path`.
# El usuario puede ampliarlas luego desde la ficha del agente como en cualquier
# otro; esto es solo el punto de partida seguro.
ORCHESTRATOR_DEFAULT_TOOLS = ["filesystem", "document"]


def ensure_orchestrator(project_id: int) -> Optional[dict]:
    """El orquestador de un proyecto, creándolo si aún no existe.

    Devuelve el mismo dict que `orchestrator_of` (o `None` si el proyecto no
    existe). Idempotente: si ya hay uno, NO crea otro ni lo modifica — mismo
    criterio que la siembra de reglas predefinidas del AE (`rules_builtin`).

    POR QUÉ EXISTE (petición del usuario, 2026-08-02): la columna `Agent.role`
    y el enrutado por orquestador (`pipeline.submit_mission`) están desde W2e/R4,
    pero NADA creaba nunca un agente con ese rol, así que en la práctica ningún
    proyecto tenía orquestador y la ruta estaba muerta. El chat del proyecto lo
    materializa a la primera pregunta.

    DÓNDE SE IMPONE SU ALCANCE (importante, para no prometer de más): en
    `Authority`, no en el `system_prompt`. El camino agente→TIE
    (`agent_manager._delegate_to_tie`) pasa `allowed_tools`, `project_id` y
    `repo_path`, y NO el system_prompt — así que la frontera es real y
    verificable aunque el modelo ignore cualquier instrucción de texto."""
    existing = orchestrator_of(project_id)
    if existing:
        return existing

    try:
        from app.agents.agent_manager import agent_manager
        from app.db.database import Project, SessionLocal

        db = SessionLocal()
        try:
            project = db.get(Project, project_id)
            if project is None:
                return None
            project_name = project.name or f"proyecto {project_id}"
        finally:
            db.close()

        agent_manager.create_agent(
            name=f"Orquestador · {project_name}",
            agent_type="orchestrator",
            description=(
                "Coordina el proyecto: reparte trabajo entre los agentes de este "
                "proyecto y trabaja sobre su carpeta. Creado automáticamente al "
                "abrir el chat del proyecto."
            ),
            allowed_tools=list(ORCHESTRATOR_DEFAULT_TOOLS),
            project_id=project_id,
            icon="🧠",
            role="orchestrator",
        )
    except Exception as e:      # noqa: BLE001 — nunca romper el chat por esto
        import logging

        logging.getLogger("aithera").warning(
            f"[authority] no se pudo crear el orquestador del proyecto {project_id}: {e!r}"
        )
        return orchestrator_of(project_id)

    # Se relee en vez de construir el dict a mano: una sola forma de leer quién
    # manda (y, si dos peticiones simultáneas crearan dos, `orchestrator_of`
    # devuelve siempre el más antiguo — determinista).
    return orchestrator_of(project_id)


def _agent_owner(agent_id: Any) -> tuple[bool, Optional[int]]:
    """`(se_pudo_leer, project_id)` del agente objetivo.

    [2026-08-02] Antes esto devolvía un `Optional[int]` a secas y `None`
    significaba TRES cosas incompatibles: "el agente no tiene proyecto", "el
    agente no existe" y "falló la consulta". Como todas se comparaban con un
    `project_id` concreto, las tres denegaban — fail-closed, sí, pero también
    imposible distinguir el caso legítimo (un agente sin dueño) del fallo. Con
    la tupla, quien pregunta decide: no-leído sigue denegando, sin-dueño no."""
    try:
        from app.db.database import Agent, SessionLocal

        db = SessionLocal()
        try:
            agent = db.get(Agent, int(agent_id))
            if agent is None:
                return False, None
            return True, agent.project_id
        finally:
            db.close()
    except Exception:
        return False, None
