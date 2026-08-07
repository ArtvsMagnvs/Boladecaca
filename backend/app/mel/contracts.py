# app/mel/contracts.py — CONTRATOS CONGELADOS del MEL (Model Execution Layer)
#
# V1.0 (E1). Misma disciplina que el TIE (contracts.py) y el MOS (interfaces.py):
# el contrato COMPLETO hoy; cada campo indica desde qué versión se usa de verdad.
# Diseño: doc 19 §2 (API pública) + los deltas 2026-07-18 (§7b model_override).
#
# REGLA DE EVOLUCIÓN (inviolable): estas firmas NO cambian. Se EXTIENDEN — nuevas
# Capability (append-only), nuevos campos con default. Es la superficie que
# consumen: el TIE (router.py → mel.complete), el resto de call-sites (E2), y en
# el futuro el Learner (mel_executions comparte model_stats, doc 19 §9.2).
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Capacidades (doc 19 §3) — la taxonomía. APPEND-ONLY (como MemoryType/NodeState)
# ---------------------------------------------------------------------------
class Capability(str, Enum):
    """Qué CLASE de tarea, no qué modelo. El caller pide una capacidad; el MEL
    elige el modelo. Una capacidad agrupa tareas que comparten perfil de
    exigencia + forma de output + sensibilidad a latencia/coste (doc 19 §3).
    APPEND-ONLY: las reservadas se activan sin migración cuando llega su turno."""
    CHAT = "chat"            # conversación general con memoria, streaming
    CLASSIFY = "classify"    # etiqueta corta, latencia mínima, volumen alto
    EXTRACT = "extract"      # estructura (JSON/fecha) desde texto, precisión literal
    SUMMARIZE = "summarize"  # condensar sin inventar, coste bajo, batch
    DRAFT = "draft"          # prosa en nombre del usuario, tono natural
    REASON = "reason"        # razonamiento profundo multi-paso, calidad ante todo
    CODE = "code"            # generación/edición de código
    ANALYZE = "analyze"      # análisis de datos/patrones, batch tolerante
    # [V1.1 LC1, doc 41 §2] EL APRENDIZAJE. Juzgar si una misión SIRVIÓ, sacar
    # la lección, decidir qué merece ser skill y redactar las propuestas. Es
    # una capacidad propia y no `analyze` porque su perfil de exigencia es
    # distinto: pide juicio con evidencia (razonamiento), tolera latencia alta
    # (todo va en segundo plano) y le sienta bien un razonador LOCAL — coste 0
    # y sin prisa. Que sea propia es además lo que permite al usuario elegir su
    # modelo por separado en Ajustes → Inteligencia ("Aprendizaje").
    LEARN = "learn"
    # — reservadas (doc 19 §3): existen en el enum, se activan en su versión —
    RESEARCH = "research"    # investigación larga (E1b la ACTIVA — auto-catálogo §5.4)
    VISION = "vision"        # multimodal (V1.5+)
    AGENTIC = "agentic"      # loops de tool-use del runtime (V1.1+)


class PolicyName(str, Enum):
    """Las políticas de ejecución (doc 19 §4; enum APPEND-ONLY). Custom es el
    lienzo editable del usuario (E2b). [2026-07-22, petición del usuario]
    SPEED y BALANCED compilan con MEDICIONES reales (mel/benchmark.py):
    velocidad pura con suelo mínimo de calidad, y el equilibrio calidad/latencia."""
    ECONOMY = "economy"      # el candidato más barato aceptable por capacidad
    QUALITY = "quality"      # orden puro por score; coste solo desempata
    OFFLINE = "offline"      # SOLO proveedores locales
    CUSTOM = "custom"        # definida por el usuario (editable, E2b)
    SPEED = "speed"          # el más RÁPIDO medido (con suelo mínimo de calidad)
    BALANCED = "balanced"    # calidad buena a velocidad decente (medido)


# ---------------------------------------------------------------------------
# Identidad de un modelo dentro del MEL
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ModelRef:
    """La identidad de un candidato: (proveedor, modelo). En Aithera V1.0 cada
    proveedor configurado tiene UN modelo, así que un ModelRef ≈ un proveedor
    con su modelo. `is_local` gobierna las políticas Offline/Economy (doc 19 §4)."""
    provider: str            # "anthropic" | "ollama" | ... (clave del ai_manager)
    model: str               # "claude-opus-4-8" | "llama3" | ...
    is_local: bool = False

    @property
    def key(self) -> str:
        """Clave estable `provider:model` — para trazas, dedup y catálogo."""
        return f"{self.provider}:{self.model}"


# ---------------------------------------------------------------------------
# Petición y resultado (doc 19 §2) — CONGELADOS
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Constraints:
    """Límites de la petición. `priority` gobierna (V1.2) el semáforo de locales
    y el orden de despacho; en V1.0 es informativo."""
    max_tokens: Optional[int] = None
    timeout_s: float = 60.0
    priority: str = "normal"           # "low" | "normal" | "high"
    idempotent: bool = False           # ¿se puede reintentar sin efectos? (fallback §8.1)


@dataclass(frozen=True)
class ExecutionRequest:
    """Lo que un caller le pide al MEL. NUNCA nombra un modelo (esa es la razón de
    existir del MEL) — salvo `model_override`, que es control EXPLÍCITO del
    USUARIO (no del caller), máxima prioridad (doc 19 §7b, activo desde E2b)."""
    capability: Capability
    prompt: str
    system_prompt: Optional[str] = None
    constraints: Constraints = field(default_factory=Constraints)
    # dominio/proyecto/origen — SOLO para métricas y aprendizaje; jamás para
    # seleccionar en v1 (evita acoplamiento negocio→MEL, doc 19 §2). `project_id`
    # aquí es lo que consulta el pin de proyecto (§7b) desde E2b.
    context_tags: dict = field(default_factory=dict)
    policy_override: Optional[str] = None   # "offline" p.ej. para jobs nocturnos; raro
    model_override: Optional[str] = None    # [E2b, §7b] id EXACTO ya resuelto por el
                                            # usuario — por encima de política y catálogo
    # [R6.5a] Turnos ANTERIORES de la conversación, formato canónico
    # [{"role": "user"|"assistant", "content": str}]. Extensión APPEND-ONLY —
    # misma disciplina que `exclude` en E1b: nunca se cambia una firma que ya
    # existe. `[]` = comportamiento idéntico al de siempre, bit a bit.
    # El turno ACTUAL sigue en `prompt` y el system en `system_prompt`: así los
    # ~15 call-sites que ya existen no se enteran de nada.
    messages: list = field(default_factory=list)
    exclude: tuple[str, ...] = ()           # [E1b, §5.4.2] model_keys a EXCLUIR de la
                                            # selección — lo usa research.py para no
                                            # dejar que un modelo se autoevalúe cuando
                                            # hay alternativa (extensión append-only,
                                            # nunca cambia una firma existente)
    # [2026-07-22, append-only] SOLO para el banco de medición
    # (scripts/model_task_bench.py): salta el filtro de aptitud del executor
    # para poder MEDIR un modelo en una capacidad donde hoy está excluido —
    # medir es el punto; sin esto la exclusión impediría re-evaluar jamás.
    # NINGÚN camino de producción lo activa (default False = comportamiento
    # idéntico al de siempre, bit a bit).
    fitness_exempt: bool = False
    # [2026-08-04, append-only] DIRECTORIO DE TRABAJO de la petición. Solo lo
    # usan los proveedores que ejecutan de verdad en una carpeta — hoy los
    # agentes CLI (Claude Code, Codex), que traen sus propias herramientas y
    # trabajan sobre el repositorio donde se les lance. Es la pieza que hace que
    # "el agente del proyecto X" toque los ficheros de X y no otros.
    # Los proveedores HTTP lo ignoran (el registry degrada solo si el proveedor
    # no lo acepta), así que `None` = comportamiento idéntico al de siempre.
    workdir: Optional[str] = None
    # [B·WEB-2, append-only] IMÁGENES de la petición, en base64 PNG/JPEG SIN el
    # prefijo `data:` (la frontera lo normaliza). Es lo que hace utilizable la
    # `Capability.VISION`, que hasta aquí existía en el enum sin transporte.
    #
    # Diferencia IMPORTANTE con `messages`/`workdir`: esos degradan en silencio
    # si el proveedor no los acepta (el historial es una mejora, no una
    # necesidad). Una imagen NO puede degradar así — un modelo que no la recibe
    # respondería igualmente, inventándose lo que "ve". Por eso el registry
    # LANZA en vez de reintentar sin ella, y el executor lo trata como fallo de
    # ese candidato y salta al siguiente (fail-closed, doc 32 B·WEB-2 paso 1).
    images: tuple[str, ...] = ()


@dataclass(frozen=True)
class ServedBy:
    """Quién atendió la petición de verdad — observabilidad, NO control (el caller
    lo lee, nunca lo decide, doc 19 §2)."""
    provider: str
    model: str
    attempts: int = 1                  # cuántos candidatos se intentaron
    fallbacks_used: int = 0            # cuántos saltos de cadena hubo


@dataclass(frozen=True)
class Usage:
    """Coste real medido de la petición. `cost_estimate` en V1.0 es relativo
    (catálogo §5.1); coste-por-token exacto es V2 (doc 19 §13)."""
    tokens: Optional[int] = None
    cost_estimate: Optional[float] = None
    latency_ms: Optional[int] = None


@dataclass(frozen=True)
class ExecutionResult:
    """Lo que el MEL devuelve. `text` ya viene limpio (strip_reasoning B21 si el
    caller lo pidió — el streaming aplica el filtro incremental). `decision_id`
    enlaza con el DecisionTrace consultable (§9.1)."""
    text: str
    ok: bool
    error: Optional[str] = None
    served_by: Optional[ServedBy] = None
    usage: Usage = field(default_factory=Usage)
    decision_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Traza de decisión (doc 19 §9.1) — explicabilidad total, sin LLM
# ---------------------------------------------------------------------------
@dataclass
class DecisionTrace:
    """Por qué el MEL eligió lo que eligió. Determinista y reproducible: misma
    petición + mismo estado ⇒ misma traza. Vive en un ring buffer en memoria
    (500) + muestreo persistido; consultable vía `mel.decision_trace(id)`."""
    capability: str
    policy: str
    chain: list[str] = field(default_factory=list)     # keys de los candidatos, en orden
    skipped: list[tuple] = field(default_factory=list)  # [(model_key, razón)]
    chosen: Optional[str] = None                        # model_key elegido, o None si nada viable
    origin: str = "policy"                              # "policy"|"user_explicit"|"project_pin"
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "capability": self.capability,
            "policy": self.policy,
            "chain": list(self.chain),
            "skipped": [list(s) for s in self.skipped],
            "chosen": self.chosen,
            "origin": self.origin,
        }
