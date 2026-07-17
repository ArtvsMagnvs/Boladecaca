# app/tie/contracts.py — CONTRATOS CONGELADOS del TIE (Task Intelligence Engine)
#
# V1.0 (T1). Misma disciplina que el MOS (interfaces.py): el contrato COMPLETO
# hoy; cada campo indica desde qué versión se usa de verdad. Los campos no
# activos llevan default y NADIE los lee hasta su versión — cero coste, cero
# migración futura. Diseño: doc 14 §3.2 (Cognitive Runtime) + doc 11-B.
#
# REGLA DE EVOLUCIÓN (inviolable): estas firmas NO cambian. Se EXTIENDEN — nuevos
# NodeState (append-only), nuevos campos con default, nuevas variantes. Nunca se
# altera una firma existente ni se reordena un enum en uso. Es la superficie que
# consumen: el Planner (T2), el Executor (T3), el Responder/handle (T4), el AE
# (submit_mission), el WPMS, el MEL (model_capability) y el Learner (traces).
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Estado de un nodo del grafo de ejecución (doc 14 §3.2)
# ---------------------------------------------------------------------------
class NodeState(str, Enum):
    """Ciclo de vida de un TaskNode. APPEND-ONLY. Los estados WAITING_* y los de
    fin se activan en su sprint; en T1 solo existen como enum (el executor es T3)."""
    PENDING = "pending"                    # aún con dependencias sin cumplir
    READY = "ready"                        # dependencias DONE; elegible para ejecutar
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"  # en manos del ApprovalGate (persiste/reanuda) — T3
    WAITING_EVENT = "waiting_event"        # espera un evento (flujos del AE) — V1.2
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"                    # una dependencia falló y la política fue degradar
    CANCELLED = "cancelled"                # kill-switch del usuario — T3


# ---------------------------------------------------------------------------
# Intención del usuario (doc 11-B §B.1, enriquecido en T1)
# ---------------------------------------------------------------------------
class IntentType(str, Enum):
    """Qué QUIERE el usuario, a alto nivel. El camino corto sirve conversational
    y query-simple sin pagar el planner (~80% de queries, doc 14 §6)."""
    CONVERSATIONAL = "conversational"  # charla / pregunta trivial → camino corto
    QUERY = "query"                    # pregunta que puede necesitar memoria o una tool
    CREATE = "create"                  # crear algo (tarea, evento, borrador, documento…)
    EXECUTE = "execute"                # ejecutar una acción / herramienta / proceso
    AUTOMATE = "automate"             # crear o gestionar una automatización (→ AE)


# Capacidades del MEL (doc 19 §3) que el TIE puede PEDIR. El MEL (bloque E1 de
# V1.0, plan aparte) es la AUTORIDAD de esta taxonomía; aquí viven como hint
# congelado para que el clasificador diga "qué modelo pedir" sin acoplar el TIE a
# nombres de modelo. `router.py` (T2) mapea este hint a fast/smart; cuando el MEL
# exista, `router` lo traduce a `mel.Capability` con un cambio de una línea.
# APPEND-ONLY, alineado con el enum del MEL.
MEL_CAPABILITIES: frozenset[str] = frozenset({
    "chat",       # conversación general con memoria (camino corto)
    "classify",   # etiqueta corta, barato (el propio intent classifier)
    "extract",    # estructura/JSON/fecha desde texto
    "summarize",  # condensar sin inventar
    "draft",      # prosa en nombre del usuario
    "reason",     # razonamiento profundo (el Planner pide esto)
    "code",       # generación/edición de código
    "analyze",    # análisis de datos/patrones
})


@dataclass
class Intent:
    """La lectura que el TIE hace de un mensaje. En T1 el clasificador ya la
    rellena por completo: es lo que permite al TIE decir, tras esta fase, QUÉ
    quiere el usuario, QUÉ necesita para resolverlo, QUÉ pedir al MEL y QUÉ al
    MOS — antes de construir planner/executor (T2-T4)."""
    # — qué quiere el usuario —
    type: IntentType
    goal: str                                       # objetivo imperativo y verificable extraído
    domain: list[str] = field(default_factory=list)  # ["email","calendar","project","system",…]
    confidence: float = 0.0                          # 0-1; <0.55 → se fuerza conversational

    # — qué necesita para resolverlo (capacidades/recursos) —
    requires_planning: bool = False    # ¿hace falta el Planner (grafo multi-paso)? → T2/T4
    requires_tools: list[str] = field(default_factory=list)  # tool_ids probables del ToolManager
    requires_browser: bool = False     # ¿navegar web? (tool futura; permiso browser.use — A3b)
    requires_computer: bool = False    # ¿controlar el PC? (tool futura; permiso computer.use — A3b)
    requires_automation: bool = False  # ¿esto debería volverse una regla del AE? (→ Automation Engine)

    # — qué contexto pedir al MOS (lo consume el enricher, T2) —
    requires_memory: bool = False      # ¿necesita contexto del MOS?
    memory_types: list[str] = field(default_factory=list)  # filtro de MemoryType (valores del MOS)
    context_query: Optional[str] = None  # consulta al Context API (si None, se usa `goal`)

    # — qué modelo pedir al MEL —
    model_capability: str = "chat"     # ∈ MEL_CAPABILITIES; el router/MEL lo resuelve a un modelo

    # — trazabilidad —
    raw: dict = field(default_factory=dict)  # respuesta cruda del clasificador (debug/trace)

    @property
    def is_short_path(self) -> bool:
        """El camino corto (NullRuntime → respuesta directa, sin grafo ni planner):
        conversational SIEMPRE; query SIMPLE (sin planning, sin browser/computer,
        sin que deba volverse automatización). CREATE/EXECUTE/AUTOMATE siempre van
        por el pipeline completo (planner→graph→executor, T4)."""
        if self.type == IntentType.CONVERSATIONAL:
            return True
        if self.type == IntentType.QUERY and not (
            self.requires_planning
            or self.requires_browser
            or self.requires_computer
            or self.requires_automation
        ):
            return True
        return False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        return d

    @classmethod
    def conversational_fallback(cls, goal: str) -> "Intent":
        """Fail-safe barato (doc 11 B.1): ante cualquier duda del clasificador
        (fallo del LLM, JSON inválido, confianza < 0.55), se trata como charla.
        Nunca romper; siempre responder algo."""
        return cls(type=IntentType.CONVERSATIONAL, goal=goal, confidence=0.0,
                   model_capability="chat")


# ---------------------------------------------------------------------------
# Grafo de tareas — el plan como DATOS (doc 14 §1.5/§3.2)
# ---------------------------------------------------------------------------
@dataclass
class TaskNode:
    """Un nodo del plan. El planner (T2) los emite; el executor (T3) los ejecuta
    y ESCRIBE su estado/resultado (los campos de la sección 'estado' son suyos —
    nadie más los toca)."""
    # — identidad y grafo (V1.0) —
    id: str
    goal: str                                       # objetivo imperativo y VERIFICABLE del nodo
    depends_on: list[str] = field(default_factory=list)  # las aristas: el grafo ES esto
    # — qué necesita (V1.0; None = el executor decide con defaults) —
    context_query: Optional[str] = None             # memoria requerida → Context API del MOS
    memory_types: Optional[list[str]] = None        # filtro de tipos MOS para el contexto
    skills: list[str] = field(default_factory=list)  # skills LSL recomendadas (V1.1)
    tools: list[str] = field(default_factory=list)   # whitelist de tools DEL NODO (⊆ ToolManager)
    runtime: Optional[str] = None                    # agente recomendado ("null"|"hermes"|…) (V1.1)
    model_hint: Optional[str] = None                 # "fast"|"smart"|capacidad MEL|id concreto
    # — prioridad y presupuestos (medir V1.0; imponer V1.2) —
    priority: int = 0
    budget_tokens: Optional[int] = None
    budget_ms: Optional[int] = None
    est_duration_ms: Optional[int] = None
    est_cost: Optional[float] = None
    # — control (V1.0) —
    approval_required: bool = False                  # → ApprovalGate (V0.9) — T3
    max_retries: int = 0                             # política real en V1.2
    # — estado y resultado (los escribe SOLO el executor, T3) —
    state: NodeState = NodeState.PENDING
    gate_id: Optional[str] = None                    # [T3] id del ApprovalGate si el nodo pidió permiso;
                                                     # persistido para que resume_pending() pueda consultar
                                                     # el veredicto tras un reinicio (extensión append-only)
    confidence: Optional[float] = None               # confianza del planner en el nodo
    result: Optional[dict] = None                    # salida estructurada del runtime
    validation: Optional[dict] = None                # {"ok":bool,"method":"schema|llm|user","notes":str}
    tokens: Optional[int] = None                     # coste real medido
    cost: Optional[float] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "TaskNode":
        d = dict(d)
        if "state" in d and d["state"] is not None:
            d["state"] = NodeState(d["state"])
        return cls(**{k: v for k, v in d.items() if k in _TASKNODE_FIELDS})


_TASKNODE_FIELDS = set(TaskNode.__dataclass_fields__.keys())


@dataclass
class TaskGraph:
    """El grafo completo, serializable a JSON. Invariantes (las valida `graph.py`
    en T2 al construir): DAG sin ciclos; `depends_on` solo a ids existentes;
    `tools` de cada nodo ⊆ catálogo del ToolManager; schema válido."""
    id: str
    mission_id: str
    nodes: dict[str, TaskNode] = field(default_factory=dict)
    created_by: str = "planner"                      # "planner"|"user"|"automation"|"learner"
    state: str = "draft"                             # draft|approved|running|done|failed|cancelled

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "created_by": self.created_by,
            "state": self.state,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaskGraph":
        nodes = {nid: TaskNode.from_dict(nd) for nid, nd in (d.get("nodes") or {}).items()}
        return cls(
            id=d["id"], mission_id=d["mission_id"], nodes=nodes,
            created_by=d.get("created_by", "planner"), state=d.get("state", "draft"),
        )


# ---------------------------------------------------------------------------
# Misión — el objetivo del usuario con entregable (doc 14 §3.2/§3.6)
# ---------------------------------------------------------------------------
@dataclass
class Mission:
    """En V1.0 la misión es IMPLÍCITA: 1 query compleja = 1 misión = 1 grafo = 1
    trace. La dataclass existe ya (contrato congelado); la tabla `missions`
    propia es V1.2 (§3.6). `source` gobierna presupuestos futuros (automation <
    user) y de dónde vino (para que el AE/WPMS deleguen sin acoplarse)."""
    id: str
    goal: str                                        # objetivo del usuario, con entregable
    source: str = "user"                             # "user"|"automation"|"learner"|"workspace"
    channel: Optional[str] = None                    # canal de origen (para responder por él)
    state: str = "running"                           # running|waiting|done|failed|cancelled
    project_id: Optional[int] = None                 # si source="workspace" (doc 14 §4.3c)
    graph_ids: list[str] = field(default_factory=list)  # V1.0: exactamente 1
    budget_tokens: Optional[int] = None              # imponer en V1.2
    spent_tokens: int = 0
    outcome: Optional[str] = None                    # resumen del resultado (lo escribe el responder)
    reflection_id: Optional[str] = None              # → aprendizaje post-misión (doc 15 §4)

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex

    def to_dict(self) -> dict:
        return asdict(self)
