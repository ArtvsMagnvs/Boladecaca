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
    channel: Optional[str] = None
    constraints: dict = field(default_factory=dict)  # {timeout_s, max_tool_calls, …}
    metadata: dict = field(default_factory=dict)

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
        # tool_use básico: si el nodo pide EXACTAMENTE una tool con acción/params
        # en metadata, se ejecuta por el ToolManager inyectado (whitelist honrada).
        tool_req = task.metadata.get("tool_call") if task.metadata else None
        if tool_req and tools is not None:
            res = await tools.execute(
                tool_id=tool_req.get("tool_id"),
                action=tool_req.get("action"),
                params=tool_req.get("params", {}),
                allowed_tools=task.tools or None,
            )
            dur = int((time.monotonic() - t0) * 1000)
            return AgentResult(
                task_id=task.id, success=bool(res.get("success")),
                result=res, tool_calls=[res],
                error=res.get("error"), duration_ms=dur,
            )

        # camino de chat (el 100% del camino corto de V1.0/T1)
        try:
            answer = await chat_service.answer(
                task.instruction, channel=task.channel or "tie", persist_chat_message=False,
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
        # V1.0: streaming mínimo — un status + el resultado completo. El streaming
        # real por tokens del camino corto lo lleva /api/chat/stream (T4); aquí se
        # cumple el contrato para que el executor pueda consumirlo uniforme.
        yield AgentChunk(task_id=task.id, kind="status", payload="running")
        result = await self.execute_task(task, memory, tools, approval_gate)
        yield AgentChunk(task_id=task.id, kind="text", payload=result.output)

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
