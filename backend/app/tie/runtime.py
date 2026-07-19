# app/tie/runtime.py — AgentRuntime: la interfaz de ejecución (doc 10 §1, V1.0/T1)
#
# EL Orchestrator (el pipeline del TIE) solo depende de esta interfaz. Un runtime
# ejecuta UN nodo/tarea recibiendo memoria, tools y gate DE AITHERA por inyección
# — jamás gestiona los suyos propios (Principio 5 AOS + doc 10). Esto es lo que
# hace intercambiable el motor de agentes, igual que el AIManager hace
# intercambiables los 8 proveedores IA.
#
# V1.0 (T1): `NullRuntime` — hace el TIE completo SIN Hermes (capabilities chat +
# tool_use básico; delega el chat en `chat_service.answer`). V1.1: `HermesRuntime`
# se registra como "hermes" sin tocar el executor. El registro `{name: runtime}`
# ES el "Agent Factory" del briefing (doc 14 §3.1: un dict, no una fábrica).
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from app.core.logging_config import get_system_logger
from app.tie.authority import Authority

logger = get_system_logger("tie.runtime")


# ---------------------------------------------------------------------------
# Contratos acompañantes (doc 10; formato congelado para V1.0)
# ---------------------------------------------------------------------------
@dataclass
class AgentTask:
    """La unidad de trabajo que recibe un runtime. En V1.0 la construye el
    executor a partir de un TaskNode (o `pipeline._short_path` para el camino
    corto). `context` es el bloque ya resuelto por el enricher (MOS)."""
    id: str
    instruction: str                                 # el `goal` del nodo, imperativo
    context: str = ""                                # contexto del MOS ya resuelto (str con fuentes)
    node_id: Optional[str] = None                    # id del TaskNode origen (None en camino corto)
    tools: list[str] = field(default_factory=list)   # whitelist de tools del nodo
    model_hint: Optional[str] = None                 # "fast"|"smart"|capacidad MEL|id
    project_id: Optional[int] = None                 # [E2b] para que el MEL vea el pin de proyecto
    channel: Optional[str] = None
    constraints: dict = field(default_factory=dict)  # {timeout_s, max_tool_calls, …}
    metadata: dict = field(default_factory=dict)
    # [R4] Frontera de autoridad de la misión, serializada (ver
    # `app/tie/authority.py`). `{}` = sin restricción. La copia el executor desde
    # `graph.authority`, que es lo que sobrevive al checkpoint.
    authority: dict = field(default_factory=dict)
    # [Fix 2026-07-19] El usuario YA aprobó las acciones sensibles de este paso
    # (aprobó el PLAN entero, o el gate de este nodo). El bucle de tool-use no
    # debe volver a preguntar una por una: el usuario vio la lista completa y
    # dijo que sí. Lo pone el executor cuando `node.gate_id` no es None.
    actions_pre_approved: bool = False
    # [R6.5b] Conversacion del chat a la que pertenece esta tarea. Solo la lleva
    # el camino corto (una charla); una mision de fondo o un agente no tienen
    # conversacion, y ahi debe ser None — mezclar el historial de un chat en una
    # tarea automatica seria contaminar su contexto.
    session_id: Optional[str] = None

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex


@dataclass
class AgentResult:
    """Lo que devuelve un runtime. `learned` son candidatos a memoria/skill que el
    Learner (V1.1) evaluará — el runtime PROPONE, nunca persiste conocimiento por
    su cuenta (doc 10)."""
    task_id: str
    success: bool
    output: str = ""                                 # respuesta/entregable en texto
    result: Optional[dict] = None                    # salida estructurada (si la hay)
    tool_calls: list[dict] = field(default_factory=list)
    tokens: Optional[int] = None
    model: Optional[str] = None
    duration_ms: Optional[int] = None
    learned: list[str] = field(default_factory=list)  # candidatos a memoria/skill (V1.1)
    error: Optional[str] = None


@dataclass
class AgentChunk:
    """Un fragmento del streaming de una tarea (para la vista de misión, T4)."""
    task_id: str
    kind: str                                        # "text"|"tool_call"|"status"
    payload: Any = None


@dataclass
class RuntimeHealth:
    available: bool
    detail: str = ""
    latency_estimate_ms: Optional[int] = None
    model_loaded: Optional[str] = None


# ---------------------------------------------------------------------------
# La interfaz (doc 10 §1) — CONGELADA
# ---------------------------------------------------------------------------
class AgentRuntime(ABC):
    """El TIE SOLO depende de esta interfaz. Un runtime recibe memoria/tools/gate
    por inyección. Añadir un runtime = implementar esta interfaz + registrarlo;
    cero cambios en el executor (probado por el registro genérico)."""

    @abstractmethod
    async def execute_task(
        self,
        task: AgentTask,
        memory: Any,          # IMemoryStore/MemoryRouter (app.memory) — inyectado
        tools: Any,           # ToolManager (app.tools) — inyectado (whitelist + gate)
        approval_gate: Any,   # ApprovalGate (app.automation) — inyectado
    ) -> AgentResult:
        ...

    @abstractmethod
    async def stream_task(
        self, task: AgentTask, memory: Any, tools: Any, approval_gate: Any
    ) -> AsyncIterator[AgentChunk]:
        ...

    @abstractmethod
    async def health_check(self) -> RuntimeHealth:
        ...

    @property
    @abstractmethod
    def capabilities(self) -> set[str]:
        """p.ej. {"chat","tool_use_basic"} / {"planning","reflection",
        "skill_generation","tool_use"} — el TIE enruta por esto (V1.1)."""
        ...


# ---------------------------------------------------------------------------
# NullRuntime — el runtime que hace V1.0 completo SIN Hermes (doc 10 §1)
# ---------------------------------------------------------------------------
def _model_override_from_hint(model_hint: Optional[str]) -> Optional[str]:
    """[E2b] Un `model_hint` que es un id CONCRETO (`provider:model`, con ":")
    viene de un override explícito del usuario → se reenvía al MEL como
    `model_override` (máxima prioridad). Los hints abstractos ("fast"/"smart"/
    una capacidad) NO son overrides: los resuelve la política, no el usuario."""
    if model_hint and ":" in model_hint:
        return model_hint
    return None


class NullRuntime(AgentRuntime):
    """Capabilities `{"chat","tool_use_basic"}`. `execute_task` delega el chat en
    `chat_service.answer()` (el pipeline único, V0.85 M4 — reusa memoria del MOS
    vía `build_system_prompt`) y puede ejecutar UNA tool simple del nodo vía el
    ToolManager inyectado (whitelist + validaciones ya en el manager). Sin
    planificación ni reflexión propias — eso lo aporta el TIE alrededor."""

    @property
    def capabilities(self) -> set[str]:
        return {"chat", "tool_use_basic"}

    async def execute_task(self, task: AgentTask, memory, tools, approval_gate) -> AgentResult:
        import time

        from app.services import chat_service

        t0 = time.monotonic()

        # [R1, doc 23 Δ2] BUCLE DE TOOL-USE REAL.
        #
        # Antes aquí solo se ejecutaba una tool si el nodo traía
        # `metadata.tool_call` ya resuelto (tool_id + action + params). NADIE
        # escribía jamás ese campo —el planner solo emite `tools: [nombres]`—,
        # así que la rama era código muerto y TODO nodo caía al camino de chat:
        # de ahí que Aithera inventara datos que debía haber consultado.
        #
        # Ahora, si el nodo tiene herramientas permitidas, se delega en el bucle
        # (elegir→ejecutar→observar), que es quien decide QUÉ tool y con qué
        # parámetros en tiempo de ejecución.
        if task.tools and tools is not None:
            from app.core.config import settings
            from app.tie import toolloop

            loop_res = await toolloop.run(
                instruction=task.instruction,
                context=task.context or "",
                allowed_tools=list(task.tools),
                tool_manager=tools,
                max_iters=settings.TIE_TOOL_MAX_ITERS,
                # El gate inyectado por el executor: una acción sensible que el
                # planner no anticipó se le PREGUNTA al usuario, no se deniega.
                approval_gate=approval_gate,
                approval_wait_s=settings.TIE_TOOL_APPROVAL_WAIT_S,
                model_override=_model_override_from_hint(task.model_hint),
                project_id=task.project_id,
                timeout_s=settings.TIE_TOOL_TIMEOUT_S,
                # [R4] La frontera de autoridad de la misión (whitelist del
                # agente, proyecto, carpeta). `{}` → sin restricción, que es el
                # caso del chat del usuario: cero regresión.
                authority=Authority.from_dict(task.authority),
                # [Fix 2026-07-19] Si el usuario ya aprobó este paso (el plan
                # entero o su gate de nodo), el bucle NO vuelve a preguntar por
                # cada acción sensible de dentro.
                pre_approved=task.actions_pre_approved,
            )
            dur = int((time.monotonic() - t0) * 1000)
            # `ok=False` con motivo → nodo FALLIDO. Es deliberado: preferimos que
            # el paso falle y se vea por qué, a devolver una respuesta inventada.
            return AgentResult(
                task_id=task.id, success=loop_res.ok, output=loop_res.answer,
                tool_calls=loop_res.tool_calls, error=loop_res.error, duration_ms=dur,
            )

        # camino de chat (el 100% del camino corto de V1.0/T1)
        try:
            answer = await chat_service.answer(
                task.instruction, channel=task.channel or "tie", persist_chat_message=False,
                model_override=_model_override_from_hint(task.model_hint),  # [E2b] override explícito
                project_id=task.project_id,                                 # [E2b] pin de proyecto
            )
            dur = int((time.monotonic() - t0) * 1000)
            return AgentResult(
                task_id=task.id, success=bool(answer.text),
                output=answer.text or "", model=answer.model, tokens=answer.tokens,
                duration_ms=dur,
            )
        except Exception as e:  # nunca romper: el runtime devuelve un fallo estructurado
            dur = int((time.monotonic() - t0) * 1000)
            logger.error(f"[NullRuntime] execute_task falló: {type(e).__name__}: {e}")
            return AgentResult(
                task_id=task.id, success=False,
                error=f"{type(e).__name__}: {e}", duration_ms=dur,
            )

    async def stream_task(self, task, memory, tools, approval_gate) -> AsyncIterator[AgentChunk]:
        """[T4b] Streaming REAL por tokens: es lo que el usuario ve en el chat de
        Electron (`/api/chat/stream`). Mismo system prompt que el camino no
        streaming (`chat_service.build_system_prompt` — memoria del MOS con
        atribución de fuente).

        [E2, doc 22 §3·E2] El streaming pasa por `mel.stream` (capacidad CHAT):
        el MEL elige el modelo por la política activa y aplica el filtro
        incremental B21 (el bloque <think> NUNCA se emite) — antes ese filtro
        vivía aquí; ahora es del MEL, así que este runtime solo reenvía los
        chunks ya limpios."""
        from app.mel import Capability, ExecutionRequest, stream as mel_stream
        from app.services import chat_service

        try:
            # [R6.5b] Continuidad: los turnos previos de ESTA conversacion. Es
            # el MISMO `recent_turns` que usa `answer()` — un solo sitio, como
            # ya se hizo en M4 con el system prompt.
            history = chat_service.recent_turns(task.session_id)
            system_prompt = await chat_service.build_system_prompt(
                task.instruction, history=history)
            req = ExecutionRequest(
                capability=Capability.CHAT, prompt=task.instruction, system_prompt=system_prompt,
                messages=history,
                model_override=_model_override_from_hint(task.model_hint),  # [E2b] override explícito
            )
            async for chunk in mel_stream(req):
                if chunk:
                    yield AgentChunk(task_id=task.id, kind="text", payload=chunk)
        except Exception as e:
            logger.error(f"[NullRuntime] stream_task falló: {type(e).__name__}: {e}")
            yield AgentChunk(task_id=task.id, kind="status", payload=f"error: {e}")

    async def health_check(self) -> RuntimeHealth:
        try:
            from app.ai.ai_manager import ai_manager

            h = await ai_manager.health_check()
            healthy = bool(h.get("healthy"))
            return RuntimeHealth(
                available=healthy,
                detail=h.get("provider", "") if healthy else "proveedor IA no disponible",
                model_loaded=h.get("model"),
            )
        except Exception as e:
            return RuntimeHealth(available=False, detail=f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Registro de runtimes — el "Agent Factory" (doc 14 §3.1: un dict)
# ---------------------------------------------------------------------------
_RUNTIMES: dict[str, AgentRuntime] = {}


def register_runtime(name: str, runtime: AgentRuntime) -> None:
    """Registra un runtime bajo un nombre. V1.1 registra "hermes" aquí sin tocar
    el executor. Re-registrar es seguro (útil en tests)."""
    if not isinstance(runtime, AgentRuntime):
        raise TypeError(f"se esperaba AgentRuntime, recibió {type(runtime).__name__}")
    _RUNTIMES[name] = runtime


def get_runtime(name: Optional[str]) -> AgentRuntime:
    """Devuelve el runtime pedido; si `name` es None o desconocido, cae a "null"
    (siempre disponible). El executor (T3) llama a esto por `node.runtime`."""
    if name and name in _RUNTIMES:
        return _RUNTIMES[name]
    return _RUNTIMES["null"]


def list_runtimes() -> dict[str, set[str]]:
    """{nombre: capabilities} — para diagnóstico y el routing por capabilities (V1.1)."""
    return {name: rt.capabilities for name, rt in _RUNTIMES.items()}


# NullRuntime disponible siempre, desde el import del módulo.
register_runtime("null", NullRuntime())
