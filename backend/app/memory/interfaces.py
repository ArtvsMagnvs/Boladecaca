# app/memory/interfaces.py — CONTRATOS CONGELADOS del MOS (V0.85, sprint M1)
#
# Estos contratos son la superficie de 10 años del Memory Operating System.
# Los consumen, sin cambiar sus firmas: V0.9 (briefing/Automation), V1.0
# (Orchestrator/Context Enricher), V1.1 (adapters de Hermes) y V2.0+ (stores
# distribuidos y red GSN/CIE). Diseño: docs 07 §3, 08 RFC-002, 09 §1.1.
#
# REGLA DE EVOLUCION (inviolable): estas firmas NO cambian. Se EXTIENDEN —
# nuevos MemoryType (append-only), nuevos métodos con default, nuevas variantes.
# Nunca se altera una firma existente ni se reordena un enum en uso.
#
# El caller NUNCA sabe qué tecnología hay debajo (ChromaDB hoy, Qdrant/distribuido
# mañana): habla siempre contra IMemoryStore vía el MemoryRouter (08 RFC-006).
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Tipos de memoria (capas lógicas, NO tecnologías — P03 §9.2)
# ---------------------------------------------------------------------------
class MemoryType(str, Enum):
    """Las capas de memoria del MOS. El VALOR es el nombre de la colección
    física (ChromaDB en V0.85). APPEND-ONLY: los reservados se activan creando
    su colección de forma lazy al primer `store`; añadir uno nunca rompe nada.
    """
    # --- Activos en V0.85 ---
    CONVERSATIONAL = "mem_conversational"  # chat/gateway (alias de la colección legacy)
    PERSONAL = "mem_personal"              # contexto personal: emails/agenda/preferencias
    PROJECT = "mem_project"               # estado/decisiones de proyecto (escritor real: WPMS V0.87)
    SKILL = "mem_skill"                   # espejo semántico de skills (stub LSL)
    DECISION = "mem_decision"             # espejo semántico de la tabla `decisions`

    # --- Reservados (colección creada lazy cuando su fase los use; NO en V0.85) ---
    EPISODIC = "mem_episodic"    # V1.2+
    ERROR = "mem_error"          # V0.9 (Automation escribe errores)
    TOOL = "mem_tool"            # V1.x
    AUTOMATION = "mem_automation"  # V0.9
    KNOWLEDGE = "mem_knowledge"  # V1.2+
    WORKING = "mem_working"      # V1.1 (interno de HermesRuntime)


@dataclass(frozen=True)
class MemoryItem:
    """Una unidad de memoria recuperada. Inmutable: representa un hecho indexado
    en un instante. `score` solo viene poblado en resultados de búsqueda."""
    id: str
    content: str
    memory_type: MemoryType
    source: str                # "email" | "calendar" | "chat" | "hermes" | "user" | ...
    created_at: datetime
    metadata: dict = field(default_factory=dict)  # source_id, sender, category, project, channel...
    score: Optional[float] = None  # relevancia 0-1 en resultados de search (None fuera de search)


@dataclass(frozen=True)
class MemoryQuery:
    """Consulta estructurada — companion de `search`/`context` para callers que
    construyen consultas de forma programática (briefing V0.9, Context Enricher
    V1.0). Equivale a los parámetros explícitos de `search`; se ofrece como
    objeto-valor para pasarlo entre capas sin desempaquetar."""
    query: str
    memory_types: Optional[list[MemoryType]] = None
    top_k: int = 5
    filters: Optional[dict] = None
    max_tokens: int = 1500


class IMemoryStore(ABC):
    """Contrato ÚNICO de acceso a memoria (doc 07 §3, 08 RFC-002).

    Implementaciones: `LocalMemoryStore` (V0.85, ChromaDB), `QdrantMemoryStore`
    (V1.x), `DistributedMemoryStore` (V2.0+). El caller nunca sabe cuál hay debajo.

    Garantías transversales de TODA implementación (08 RFC-002):
      - toda escritura acepta `dedup_key` → idempotencia.
      - toda lectura acepta presupuesto (`top_k`, `max_tokens`).
      - todo error degrada a valor vacío + log; JAMAS rompe al caller.
      - toda salida de LLM interna pasa por `strip_reasoning()`.
    """

    @abstractmethod
    async def store(
        self,
        content: str,
        memory_type: MemoryType,
        source: str,
        metadata: Optional[dict] = None,
        dedup_key: Optional[str] = None,
    ) -> str:
        """Indexa `content`. Devuelve el id del item (str vacío si no se pudo,
        p.ej. memoria caída). `dedup_key` (p.ej. el email_id) hace la operación
        idempotente: si ya existe un item con ese dedup_key en ese tipo, se
        ACTUALIZA en vez de duplicar."""

    @abstractmethod
    async def search(
        self,
        query: str,
        memory_types: Optional[list[MemoryType]] = None,
        top_k: int = 5,
        filters: Optional[dict] = None,
    ) -> list[MemoryItem]:
        """Búsqueda semántica. `memory_types=None` = todos los tipos activos.
        `filters` filtra por metadata (igualdad). Devuelve [] si no hay memoria."""

    @abstractmethod
    async def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        """Recupera un item por id exacto. None si no existe o memoria caída."""

    @abstractmethod
    async def summarize(
        self, memory_type: MemoryType, date_from: date, date_to: date
    ) -> str:
        """Resumen del rango [date_from, date_to] para un tipo. Usa resúmenes
        precalculados si existen (los genera el summarizer, V0.85 M3)."""

    @abstractmethod
    async def forget(self, memory_type: MemoryType, filters: dict) -> int:
        """Borra por criterio de metadata. Devuelve nº de items borrados. La
        transparencia manda: el usuario siempre puede olvidar (con vault activo,
        borra también el .md espejo — V1.x)."""

    @abstractmethod
    async def context(
        self,
        query: str,
        max_tokens: int = 1500,
        memory_types: Optional[list[MemoryType]] = None,
    ) -> str:
        """Bloque de contexto listo para inyectar en un prompt, con ATRIBUCION
        de fuente por línea ('[email de X · martes] ...'). Es LA llamada que
        harán chat (V0.85 M4), briefing (V0.9) y Context Enricher (V1.0).
        Presupuesto de tokens duro: nunca excede `max_tokens` (aprox.)."""


# ---------------------------------------------------------------------------
# Skills (Capa 3 local — LSL). Stub en V0.85, completa en V1.1. Contratos de
# doc 09 §1.1 (con los campos de linaje [Δ] del doc 14 §4.1 / doc 15 §6).
# ---------------------------------------------------------------------------
class SkillStatus(str, Enum):
    """Ciclo de vida de una skill (doc 09 §1.2). LOCAL es el reposo normal;
    DEPRECATED se archiva (nunca se borra: guarda historia)."""
    DRAFT = "draft"
    VALIDATED = "validated"
    LOCAL = "local"
    PROPOSED = "proposed"      # propuesta a la GSN (V2.0+)
    DEPRECATED = "deprecated"


@dataclass
class LocalSkill:
    """Una skill local (doc 09 §1.1). Mutable: el LLL actualiza calidad, uso y
    linaje a lo largo de su vida. Es el MISMO shape que usará la GSN (doc 08
    RFC-004); la migración a tabla `skills` en V1.1 es un backfill mecánico."""
    id: str
    name: str
    version: str                 # semver "1.0.0"
    description: str
    definition: dict             # instrucciones/prompt/workflow (runtime-agnostic)
    input_schema: dict           # JSON Schema
    output_schema: dict
    runtime_agnostic: bool

    # Provenance (idéntico al de la GSN, pero local)
    created_by: str              # "hermes_detection" | "user" | "local_learning_loop"
    created_at: datetime
    evidence_count: int = 0      # ejecuciones con éxito
    last_used: Optional[datetime] = None
    use_count: int = 0

    # Calidad (las alimenta el LLL — V1.1)
    status: SkillStatus = SkillStatus.DRAFT
    quality_score: float = 0.0   # 0-1
    error_rate: float = 0.0      # % ejecuciones fallidas

    # Contexto
    projects: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    # Linaje [Δ doc 14 §4.1 / doc 15 §6] — el "git log" de cada skill (merge/split/deprecate)
    derived_from: list[str] = field(default_factory=list)  # ids de skills origen; [] normal
    superseded_by: Optional[str] = None                    # id del reemplazo si DEPRECATED

    # Sincronización GSN (V2.0+; None hasta entonces)
    gsn_id: Optional[str] = None
    gsn_version: Optional[str] = None
    gsn_last_sync: Optional[datetime] = None


class ISkillStore(ABC):
    """Skill API (doc 08 RFC-002). Stub funcional en V0.85 (`LocalSkillStore`
    sobre `mem_skill`); LSL completa en V1.1. `publish` es no-op hasta la GSN
    (V2.0+); `execute` requiere un AgentRuntime (V1.1)."""

    @abstractmethod
    async def create(self, skill: LocalSkill) -> str:
        """Registra una skill. Devuelve su id (idempotente por `skill.id`)."""

    @abstractmethod
    async def get(self, skill_id: str) -> Optional[LocalSkill]:
        ...

    @abstractmethod
    async def list(
        self,
        status: Optional[SkillStatus] = None,
        tags: Optional[list[str]] = None,
    ) -> list[LocalSkill]:
        ...

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> list[LocalSkill]:
        """Búsqueda semántica por descripción (sobre el espejo `mem_skill`)."""

    @abstractmethod
    async def improve(self, skill_id: str, changes: dict) -> Optional[LocalSkill]:
        """Aplica cambios (definición/versión/calidad) a una skill existente."""

    @abstractmethod
    async def validate(self, skill_id: str) -> Optional[LocalSkill]:
        """Promociona DRAFT → VALIDATED (el LLL lo hará con evidencia; V1.1)."""

    @abstractmethod
    async def publish(self, skill_id: str) -> None:
        """No-op hasta la GSN (V2.0+). Firma viva desde ya."""

    @abstractmethod
    async def execute(self, skill_id: str, inputs: dict) -> dict:
        """Ejecuta la skill vía el AgentRuntime activo (V1.1). Hasta entonces
        lanza NotImplementedError — jamás ejecuta nada 'a medias'."""
