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

from app.core import grounding
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
    # [S3, F-1] Id de la MISIÓN dueña de esta tarea. Lo usa el bucle para aislar
    # los recursos con estado entre misiones concurrentes — hoy la sesión del
    # navegador (pestañas y cookies propias por misión); cualquier tool con
    # estado futura se engancha aquí sin cambiar el contrato.
    mission_id: Optional[str] = None
    # [A·VOZ-8] La tarea viene de una conversación por VOZ. Campo append-only. El
    # runtime enruta la respuesta por una política RÁPIDA (VOICE_CHAT_POLICY) en
    # vez de la de calidad del usuario: en voz la fluidez manda. Solo lo pone el
    # camino corto de voz; el chat de texto lo deja en False (calidad del usuario).
    conversational: bool = False

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
    # [S11, doc 34 §S11] tool_ids que el paso pidió pero NO se le concedieron
    # (existían y el agente las tenía permitidas, pero no estaban asignadas a
    # este nodo y el usuario no las concedió a mitad de ejecución). Append-only,
    # default vacío — cero regresión. La copia el executor a
    # `node.result["limitations"]` para que el responder pueda avisar.
    limitations: list[str] = field(default_factory=list)


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


# [S2, B-1] Tools cuyo trabajo típico es CONSTRUIR (múltiples escrituras
# encadenadas): esos nodos reciben el presupuesto ampliado de iteraciones.
# Las de solo-consulta (email, calendar, search, memory, process…) se quedan
# con el presupuesto base — más vueltas ahí solo alarga un atasco.
_WRITE_TOOLS = {"filesystem", "shell", "powershell", "git", "browser", "desktop", "aithera", "download"}


def _iters_for(node_tools: list) -> int:
    """Presupuesto de iteraciones del bucle según las tools del nodo (doc 25 §S2)."""
    from app.core.config import settings

    if any(t in _WRITE_TOOLS for t in (node_tools or [])):
        return settings.TIE_TOOL_MAX_ITERS_WRITE
    return settings.TIE_TOOL_MAX_ITERS


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
                max_iters=_iters_for(task.tools),
                # El gate inyectado por el executor: una acción sensible que el
                # planner no anticipó se le PREGUNTA al usuario, no se deniega.
                approval_gate=approval_gate,
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
                # [S3, F-1] Aísla los recursos con estado (navegador) por misión.
                session_key=task.mission_id,
            )
            dur = int((time.monotonic() - t0) * 1000)
            # `ok=False` con motivo → nodo FALLIDO. Es deliberado: preferimos que
            # el paso falle y se vea por qué, a devolver una respuesta inventada.
            return AgentResult(
                task_id=task.id, success=loop_res.ok, output=loop_res.answer,
                tool_calls=loop_res.tool_calls, error=loop_res.error, duration_ms=dur,
                limitations=loop_res.limitations,
            )

        # camino de chat (el 100% del camino corto de V1.0/T1)
        try:
            answer = await chat_service.answer(
                task.instruction, channel=task.channel or "tie", persist_chat_message=False,
                model_override=_model_override_from_hint(task.model_hint),  # [E2b] override explícito
                project_id=task.project_id,                                 # [E2b] pin de proyecto
                session_id=task.session_id,                                 # [A·VOZ-7] caché de contexto por sesión
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
                task.instruction, history=history, session_id=task.session_id)
            # [A·VOZ-8] En VOZ, la respuesta se enruta por la política rápida
            # (VOICE_CHAT_POLICY, p.ej. "speed"): fluidez > máxima calidad. El chat
            # de texto (conversational=False) mantiene la política del usuario. Un
            # override explícito de modelo (el usuario nombró uno) siempre manda.
            from app.core.config import settings as _settings
            voice_policy = (
                _settings.VOICE_CHAT_POLICY
                if task.conversational and not task.model_hint else None
            ) or None
            req = ExecutionRequest(
                capability=Capability.CHAT, prompt=task.instruction, system_prompt=system_prompt,
                messages=history,
                model_override=_model_override_from_hint(task.model_hint),  # [E2b] override explícito
                policy_override=voice_policy,
            )
            # [S2·S6, doc 34] Se acumula lo emitido para poder juzgar la
            # respuesta ENTERA al final: una afirmación de acción puede
            # repartirse entre varios chunks, así que mirarlos de uno en uno
            # no serviría. Solo se guarda el texto del turno (no crece sin
            # límite: es una respuesta de chat).
            emitido: list[str] = []
            async for chunk in mel_stream(req):
                if chunk:
                    emitido.append(chunk)
                    yield AgentChunk(task_id=task.id, kind="text", payload=chunk)
            # Este camino no ejecuta NINGUNA herramienta: si el texto dice que
            # visitó una web, leyó un archivo o promete hacerlo "ahora", es
            # falso por construcción. La coletilla honesta va como un chunk
            # más, así que el usuario la ve llegar con el resto.
            # [NEW-7] `note_for` decide CUÁL toca (la coletilla suave, el aviso
            # fuerte de fabricación, o ninguna) — el mismo punto de decisión que
            # usa `with_honesty_note` en el camino sin streaming, para que las
            # dos variantes no puedan divergir.
            nota = grounding.note_for("".join(emitido))
            if nota:
                yield AgentChunk(task_id=task.id, kind="text", payload=f"\n\n{nota}")
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
