# app/orchestrator/contracts.py — CONTRATOS CONGELADOS del Orquestador (R2)
#
# Misma disciplina que el TIE (`tie/contracts.py`) y el MEL (`mel/contracts.py`):
# el contrato COMPLETO hoy; cada campo indica desde qué versión se usa de verdad.
#
# REGLA DE EVOLUCIÓN (inviolable): estas firmas NO cambian. Se EXTIENDEN con
# campos nuevos que tengan default. Es la superficie que consumirán el frontend
# (vista de orquestación), el Learner (V1.1) y quien quiera auditar un run.
#
# QUÉ MODELA (doc 23 §0): un mensaje del usuario puede contener VARIOS encargos
# independientes. El TIE ejecuta UNA misión; el Orquestador reparte N.
#
#   OrchestrationRun  = lo que el usuario pidió en un mensaje
#     └── Objective[]  = cada encargo suelto → una misión del TIE
#           └── (si es demasiado amplio, se descompone en sub-objetivos)
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Optional


# Estados de un objetivo. Deliberadamente los MISMOS nombres que usa `Mission`
# (running|waiting|done|failed|cancelled) más `pending`, para que la UI y las
# trazas no tengan que traducir entre dos vocabularios.
OBJECTIVE_STATES = ("pending", "running", "waiting", "done", "failed", "cancelled", "skipped")


@dataclass
class Objective:
    """Un encargo suelto dentro de un mensaje del usuario. Se ejecuta como UNA
    misión del TIE."""
    id: str
    goal: str                                        # imperativo y verificable
    # Ids de objetivos que deben terminar ANTES que éste. Es lo que permite
    # expresar "cuando termines todo lo demás, avisa a Héctor": ese objetivo
    # depende de los otros y el conductor no lo lanza hasta que estén `done`.
    depends_on: list[str] = field(default_factory=list)
    # True si el objetivo sigue siendo demasiado amplio para una sola misión
    # ("crea 15 canales de YouTube"): el conductor lo vuelve a descomponer, hasta
    # ORCH_MAX_DEPTH. Lo marca el decomposer.
    needs_decomposition: bool = False
    priority: int = 0                                # mayor = antes, a igualdad de dependencias

    # — estado (lo escribe SOLO el conductor) —
    state: str = "pending"
    mission_id: Optional[str] = None                 # la misión del TIE que lo resolvió
    outcome: Optional[str] = None                    # su resultado, para la consolidación
    error: Optional[str] = None
    depth: int = 0                                   # 0 = raíz; 1+ = vino de descomponer otro

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:12]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Objective":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in (data or {}).items() if k in known})


@dataclass
class OrchestrationRun:
    """Un mensaje del usuario y todo el trabajo que generó. Se persiste en
    `orchestration_runs` y se actualiza en cada transición (checkpoint), igual
    que el executor del TIE hace con su grafo: un reinicio no pierde el run."""
    id: str
    user_message: str
    objectives: list[Objective] = field(default_factory=list)
    state: str = "running"                           # running|done|failed|cancelled
    outcome: Optional[str] = None                    # la respuesta consolidada final
    channel: Optional[str] = None                    # canal de origen (para responder por él)
    source: str = "user"                             # "user"|"automation"|"workspace"

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_message": self.user_message,
            "objectives": [o.to_dict() for o in self.objectives],
            "state": self.state,
            "outcome": self.outcome,
            "channel": self.channel,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OrchestrationRun":
        return cls(
            id=data["id"],
            user_message=data.get("user_message", ""),
            objectives=[Objective.from_dict(o) for o in (data.get("objectives") or [])],
            state=data.get("state", "running"),
            outcome=data.get("outcome"),
            channel=data.get("channel"),
            source=data.get("source", "user"),
        )

    # -- consultas que usan el conductor y el consolidador --

    def by_id(self, objective_id: str) -> Optional[Objective]:
        return next((o for o in self.objectives if o.id == objective_id), None)

    def ready(self) -> list[Objective]:
        """Objetivos lanzables AHORA: pendientes cuyas dependencias ya están
        `done`. Orden determinista (prioridad desc, luego id) — mismo criterio
        que `graph.ready_set()` del TIE, para que dos ejecuciones iguales den el
        mismo orden.

        Una dependencia que acabó en `failed`/`skipped`/`cancelled` NO habilita:
        eso lo resuelve `blocked()`, que marca el objetivo como saltado en vez de
        dejarlo colgado para siempre."""
        done = {o.id for o in self.objectives if o.state == "done"}
        out = [
            o for o in self.objectives
            if o.state == "pending" and all(d in done for d in o.depends_on)
        ]
        return sorted(out, key=lambda o: (-o.priority, o.id))

    def blocked(self) -> list[Objective]:
        """Objetivos que ya NUNCA podrán ejecutarse porque alguna dependencia
        suya terminó mal. Se marcan `skipped` y la consolidación lo explica —
        nunca se quedan en `pending` fingiendo que siguen vivos."""
        muertos = {o.id for o in self.objectives if o.state in ("failed", "cancelled", "skipped")}
        return [
            o for o in self.objectives
            if o.state == "pending" and any(d in muertos for d in o.depends_on)
        ]

    def is_settled(self) -> bool:
        """¿Ha terminado todo lo que podía terminar?"""
        return all(o.state not in ("pending", "running") for o in self.objectives)
