# app/core/failures.py — taxonomía y ATRIBUCIÓN de fallos (V1.1 L2b, doc 27 §5)
#
# EL PROBLEMA QUE RESUELVE: hasta hoy un fallo se GRABA (mem_error, telemetría,
# automation_executions) pero no se ATRIBUYE. "La misión falló" puede significar
# que se cayó la red, que faltaba una API key, que el modelo razonó mal, que el
# planner no supo montar el grafo, o que hay un bug en el código de Aithera — y
# para aprender son cinco cosas COMPLETAMENTE distintas. Sin atribución,
# `model_stats` castiga a un modelo por un timeout de red y el análisis de
# patrones (L3) mezcla peras con manzanas.
#
# POR QUÉ ES DETERMINISTA Y NO LA HACE UN LLM: el código EN el punto del fallo
# ya sabe qué pasó — tiene la excepción, el código HTTP, el mensaje del
# proveedor. Pedirle a un modelo que adivine la culpa sería (a) caro en el
# camino caliente, (b) no reproducible, y (c) un modelo juzgando fallos de
# modelos: exactamente el bucle de retroalimentación que doc 15 §3.3 prohíbe.
# El LLM entra DESPUÉS (L3/ML3) a analizar fallos YA atribuidos.
#
# POR QUÉ VIVE EN `core/` Y NO EN `app/learner/`: los ESCRITORES son
# MEL/toolloop/executor/planner, y ninguno puede importar internos del Learner
# (doc 16). `core/` es la capa compartida — mismo criterio que llevó ahí a
# `grounding.py` (S2·S6) y `sanitize.py` (S9c).
#
# APPEND-ONLY: `FailureKind` es un contrato congelado, igual que `MemoryType` o
# `Capability`. Se añaden valores; no se renombran ni se borran (hay filas de
# `failure_stats` con los antiguos).
from __future__ import annotations

from enum import Enum
from typing import Any, Optional


class FailureKind(str, Enum):
    """QUÉ falló. El eje fino — para el análisis."""

    # --- Nada de esto es culpa de Aithera ni del modelo ---
    CONNECTION = "connection"              # red caída, DNS, timeout, 5xx del proveedor
    PROVIDER_AUTH = "provider_auth"        # 401/403: API key inválida o caducada
    PROVIDER_LIMIT = "provider_limit"      # 429/402: rate limit o cuota agotada
    EXTERNAL_CONTENT = "external_content"  # captcha, muro irresoluble, página bloqueada

    # --- Falta configuración: tiene arreglo, y lo hace el USUARIO ---
    CONFIG_MISSING = "config_missing"      # sin API key de búsqueda, Calendar API off…

    # --- La herramienta corrió y falló por causa propia ---
    TOOL_ERROR = "tool_error"

    # --- El modelo ---
    MODEL_REASONING = "model_reasoning"    # rendición, respuesta sin fundamento, atasco
    MODEL_FORMAT = "model_format"          # JSON inválido, respuesta no parseable

    # --- Aithera misma ---
    PLANNING = "planning"                  # PlanRejection, grafo inválido tras reintento
    SYSTEM_BUG = "system_bug"              # excepción no controlada de código propio

    # --- Ni siquiera son fallos ---
    PERMISSION_DENIED = "permission_denied"  # el usuario dijo que no: eso es mandar
    USER_CANCELLED = "user_cancelled"        # kill-switch

    # --- Lo que no se sabe atribuir. VISIBLE a propósito ---
    UNKNOWN = "unknown"


# El eje grueso — para el panel y para las stats justas. Mapeo FIJO, un solo
# sitio: que "de quién es la culpa" no se decida en cinco ficheros distintos.
_BLAME: dict[FailureKind, str] = {
    FailureKind.CONNECTION: "external",
    # [Revisión L2b] `provider_auth` pasa de "external" a "config", corrigiendo
    # el primer borrador. Un 401 significa "tu API key está mal o caducada":
    # eso NO es un servicio ajeno teniendo un mal día, es algo que el usuario
    # puede arreglar en dos clics. Con "external" el panel lo habría enterrado
    # bajo "no es culpa de Aithera" y `config_gaps` nunca habría propuesto el
    # arreglo. Para las stats da igual (los dos están excusados); para el
    # usuario es la diferencia entre un dato y una solución.
    FailureKind.PROVIDER_AUTH: "config",
    FailureKind.PROVIDER_LIMIT: "external",
    FailureKind.EXTERNAL_CONTENT: "external",
    FailureKind.CONFIG_MISSING: "config",
    FailureKind.TOOL_ERROR: "tool",
    FailureKind.MODEL_REASONING: "model",
    FailureKind.MODEL_FORMAT: "model",
    FailureKind.PLANNING: "aithera",
    FailureKind.SYSTEM_BUG: "aithera",
    FailureKind.PERMISSION_DENIED: "none",
    FailureKind.USER_CANCELLED: "none",
    FailureKind.UNKNOWN: "unknown",
}

# Los `blame` que NO cuentan contra el modelo ni contra el sistema. Es la
# petición literal del usuario ("que los fallos de conexión no cuenten como
# errores del sistema") reducida a un conjunto que `stats.py` consulta.
EXCUSED_BLAMES = frozenset({"external", "config", "none"})


def blame_of(kind: "FailureKind | str | None") -> str:
    """De quién es. Fail-safe: cualquier cosa que no reconozca es 'unknown' —
    nunca se le echa la culpa a nadie por no saber clasificarlo."""
    if kind is None:
        return "unknown"
    try:
        k = kind if isinstance(kind, FailureKind) else FailureKind(str(kind))
    except ValueError:
        return "unknown"
    return _BLAME.get(k, "unknown")


def is_excused(kind: "FailureKind | str | None") -> bool:
    """¿Este fallo debe salir del denominador de las stats del modelo?"""
    return blame_of(kind) in EXCUSED_BLAMES


# ---------------------------------------------------------------------------
# Clasificación por TEXTO (el último recurso: cuando solo hay un mensaje)
# ---------------------------------------------------------------------------
# Marcas recogidas de los mensajes REALES que este proyecto produce (logs,
# mem_error, campañas 00-02), no inventadas. Orden de evaluación deliberado:
# de lo más específico a lo más genérico.
_MARCAS_CONNECTION = (
    "getaddrinfo", "connection refused", "connection reset", "connection error",
    "connectionerror", "connecterror", "cannot connect", "timed out", "timeout",
    "network is unreachable", "temporary failure in name resolution",
    "no se pudo conectar", "sin conexión", "sin conexion",
    "502", "503", "504", "bad gateway", "service unavailable",
)
_MARCAS_AUTH = ("401", "403", "unauthorized", "forbidden", "invalid api key",
                "invalid_api_key", "api key not valid", "authentication failed")
_MARCAS_LIMIT = ("429", "402", "rate limit", "rate_limit", "quota", "too many requests",
                 "insufficient_quota", "billing")
# Nada de marcas de una sola palabra genérica aquí: "habilita" a secas casaba
# con cualquier frase que hablara de habilitar algo. Cada marca es una
# expresión que solo aparece cuando de verdad falta configurar.
_MARCAS_CONFIG = ("no configurada", "no está configurada", "no esta configurada",
                  "sin api key", "añade una api key", "anade una api key",
                  "not configured", "no configurado", "falta configurar",
                  "no está habilitada", "no esta habilitada", "no habilitada",
                  "has not been used", "accessnotconfigured")
_MARCAS_EXTERNAL_CONTENT = ("captcha", "consent", "cookie wall", "acceso denegado por el sitio",
                            "blocked by", "403 forbidden por el sitio", "robot")
_MARCAS_FORMATO = ("json", "no contenía un json", "unparseable", "no parseable",
                   "expecting value", "jsondecodeerror")
_MARCAS_BUG = ("attributeerror", "typeerror", "keyerror", "indexerror",
               "nameerror", "unboundlocalerror", "zerodivisionerror",
               "not subscriptable", "object has no attribute")


def classify_failure(source: str, error_text: str = "",
                     extra: Optional[dict] = None) -> FailureKind:
    """Clasifica un fallo a partir de su ORIGEN y su texto.

    `source` es de dónde viene el fallo — `"tool"`, `"model"`, `"planner"`,
    `"system"`, `"gate"`… — y pesa MÁS que el texto: el mismo mensaje
    ("timeout") significa una cosa dentro de una tool y otra dentro del MEL.
    Cuando el origen no basta, el texto desempata.

    NUNCA lanza: clasificar un fallo no puede convertirse en otro fallo.

    OJO — no confundir con `app.mel.fallback.classify_failure`, que responde a
    una pregunta DISTINTA (¿reintento, roto, o siguiente candidato?) para
    gobernar la cadena de fallback. Esta responde "¿de quién fue?". Se
    conectan por `kind_from_mel_reason()`, no por herencia."""
    try:
        return _classify(source or "", error_text or "", extra or {})
    except Exception:
        return FailureKind.UNKNOWN


def _classify(source: str, error_text: str, extra: dict) -> FailureKind:
    src = source.lower().strip()
    txt = (error_text or "").lower()

    # 1) Orígenes que ya SON el veredicto (el llamador ya lo sabe)
    if src in ("gate", "permission"):
        return FailureKind.PERMISSION_DENIED
    if src in ("cancel", "cancelled", "kill"):
        return FailureKind.USER_CANCELLED
    if src == "planner":
        return FailureKind.PLANNING

    # 2) LO NUESTRO PRIMERO. Un error de PROGRAMACIÓN (TypeError, KeyError…) es
    #    un bug de Aithera venga de donde venga — y se mira ANTES que lo
    #    externo por una razón de dirección del daño: si un traceback nuestro
    #    lleva la palabra "connection" dentro y lo clasificamos como red, queda
    #    EXCUSADO y desaparece de las stats para siempre. Al revés (marcar como
    #    bug algo externo) solo cuesta una revisión de más. Ante la duda, la
    #    culpa se la queda casa.
    if any(m in txt for m in _MARCAS_BUG):
        return FailureKind.SYSTEM_BUG

    # 3) Config ausente: antes que lo externo porque su texto suele arrastrar
    #    palabras de otras familias ("la API de Calendar no está habilitada"
    #    viene con un 403 detrás, pero el arreglo es del usuario, no un
    #    problema de credenciales del proveedor de IA).
    if any(m in txt for m in _MARCAS_CONFIG):
        return FailureKind.CONFIG_MISSING

    # 4) Lo externo, por texto
    if any(m in txt for m in _MARCAS_CONNECTION):
        return FailureKind.CONNECTION
    if any(m in txt for m in _MARCAS_AUTH):
        return FailureKind.PROVIDER_AUTH
    if any(m in txt for m in _MARCAS_LIMIT):
        return FailureKind.PROVIDER_LIMIT
    if any(m in txt for m in _MARCAS_EXTERNAL_CONTENT):
        return FailureKind.EXTERNAL_CONTENT

    # 5) Ahora sí, por origen
    if src == "tool":
        return FailureKind.TOOL_ERROR
    if src == "system":
        return FailureKind.SYSTEM_BUG
    if src == "model":
        return (FailureKind.MODEL_FORMAT if any(m in txt for m in _MARCAS_FORMATO)
                else FailureKind.MODEL_REASONING)

    return FailureKind.UNKNOWN


# ---------------------------------------------------------------------------
# Puentes con los vocabularios que YA existen (nada se reclasifica dos veces)
# ---------------------------------------------------------------------------
# `app/mel/fallback.py` lleva desde E1 clasificando cada fallo de proveedor en
# su propio vocabulario, para decidir la cadena de fallback. Aquí solo se
# TRADUCE — reimplementar esa detección sería tener dos verdades sobre el mismo
# error.
_MEL_REASON_TO_KIND: dict[str, FailureKind] = {
    "transient": FailureKind.CONNECTION,
    "timeout": FailureKind.CONNECTION,
    "auth": FailureKind.PROVIDER_AUTH,
    "quota": FailureKind.PROVIDER_LIMIT,
    "empty_response": FailureKind.MODEL_FORMAT,
    "context_length": FailureKind.MODEL_FORMAT,
    "content_policy": FailureKind.EXTERNAL_CONTENT,
    # Config por-modelo: el modelo apuntado no existe en ese proveedor. Tiene
    # arreglo y lo hace el usuario en Ajustes → Inteligencia.
    "bad_model": FailureKind.CONFIG_MISSING,
    "no_chain": FailureKind.CONFIG_MISSING,
    "request_invalid": FailureKind.SYSTEM_BUG,   # el request lo montamos nosotros
    "unknown": FailureKind.UNKNOWN,
}


def kind_from_mel_reason(reason: Optional[str]) -> FailureKind:
    """Razón de `mel/fallback.classify_failure` → FailureKind."""
    if not reason:
        return FailureKind.UNKNOWN
    return _MEL_REASON_TO_KIND.get(str(reason).strip().lower(), FailureKind.UNKNOWN)


# Los nombres de evento del bucle de tools (`toolloop._record_loop_event`).
# Cada uno YA describe con precisión qué pasó — solo hay que decir de quién es.
_LOOP_EVENT_TO_KIND: dict[str, FailureKind] = {
    "preflight_not_ready": FailureKind.CONFIG_MISSING,
    "invalid_json": FailureKind.MODEL_FORMAT,
    "truncated_response": FailureKind.MODEL_FORMAT,
    "answer_rejected_ungrounded": FailureKind.MODEL_REASONING,
    "stalled": FailureKind.MODEL_REASONING,
    "repeated_denial": FailureKind.MODEL_REASONING,
    "repeated_failure": FailureKind.TOOL_ERROR,
    "permission_denied": FailureKind.PERMISSION_DENIED,
    "grant_denied": FailureKind.PERMISSION_DENIED,
}

# Eventos que pasan por el MISMO funnel (`_record_loop_event` los graba con
# ok=False para que se vean en el timeline) pero que NO son fallos: el bucle
# preguntó algo al usuario y siguió su camino. Sin esta lista acabarían como
# filas de `failure_stats` — el panel de Salud contando preguntas como averías.
_NO_SON_FALLOS = frozenset({"user_question"})


def kind_from_loop_event(name: str) -> Optional[FailureKind]:
    """Nombre de evento del toolloop → FailureKind, o None si ese evento no es
    un fallo. Un nombre desconocido cae en UNKNOWN a propósito: se ve en el
    panel como "sin atribuir" en vez de desaparecer sin dejar rastro."""
    clave = str(name or "").strip().lower()
    if clave in _NO_SON_FALLOS:
        return None
    return _LOOP_EVENT_TO_KIND.get(clave, FailureKind.UNKNOWN)


# ---------------------------------------------------------------------------
# El helper que usan los 6 enganches
# ---------------------------------------------------------------------------
def annotate(detail: Optional[dict], kind: "FailureKind | str | None",
             **extra: Any) -> dict:
    """Añade la atribución al `detail` de un evento de telemetría, sin pisar
    nada de lo que ya llevara. Devuelve SIEMPRE un dict nuevo (no muta el del
    llamador) y nunca lanza — la atribución es best-effort, igual que toda la
    telemetría: perder el dueño de un fallo no puede convertirse en un fallo.

    Las dos claves son fijas y planas a propósito (`failure_kind` / `blame`):
    así una consulta agregada no tiene que abrir estructuras anidadas.

    `kind=None` significa "esto no es un fallo": el detail sale intacto, SIN
    marca. Es la vía por la que un `user_question` pasa por el mismo funnel de
    telemetría sin acabar contado como avería."""
    if kind is None:
        return dict(detail or {})
    try:
        out = dict(detail or {})
        k = kind if isinstance(kind, FailureKind) else FailureKind(str(kind))
        out["failure_kind"] = k.value
        out["blame"] = blame_of(k)
        for clave, valor in extra.items():
            if valor is not None:
                out[clave] = valor
        return out
    except Exception:
        return dict(detail or {})


# ---------------------------------------------------------------------------
# A dónde mandar al usuario cuando falta configuración
# ---------------------------------------------------------------------------
# Un `config_missing` sin destino es una queja; con destino es un arreglo de un
# clic. Las claves son las pestañas REALES de Ajustes (`SETTINGS_TABS` en
# Settings.tsx) — el panel de L4 las usa como deep-link (`location.state.tab`,
# el mismo mecanismo del banner "trabajando solo en local").
_PISTAS_AJUSTES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("serpapi", "brave", "búsqueda web", "busqueda web", "search"), "conexiones"),
    (("calendar", "gmail", "google", "oauth"), "conexiones"),
    (("telegram",), "conexiones"),
    (("api key", "api_key", "proveedor", "modelo", "ollama", "invalid model"), "ia"),
    (("permiso", "autonomía", "autonomia"), "permisos"),
    (("voz", "tts", "kokoro", "elevenlabs", "whisper"), "voz"),
)


def settings_hint(text: str) -> Optional[str]:
    """¿Qué pestaña de Ajustes arregla esto? None si no se sabe — y entonces el
    panel muestra el mensaje sin botón, que es más honesto que mandar al
    usuario a una pantalla al azar."""
    txt = (text or "").lower()
    for marcas, tab in _PISTAS_AJUSTES:
        if any(m in txt for m in marcas):
            return tab
    return None


# Prioridad para elegir el fallo DOMINANTE de una misión con varios fallos.
# Lo interno pesa más que lo externo a propósito: ante la duda, la culpa se la
# queda casa. Un número más bajo gana.
_PRIORIDAD: dict[FailureKind, int] = {
    FailureKind.SYSTEM_BUG: 0,
    FailureKind.PLANNING: 1,
    FailureKind.MODEL_REASONING: 2,
    FailureKind.MODEL_FORMAT: 3,
    FailureKind.TOOL_ERROR: 4,
    FailureKind.CONFIG_MISSING: 5,
    FailureKind.EXTERNAL_CONTENT: 6,
    FailureKind.PROVIDER_AUTH: 7,
    FailureKind.PROVIDER_LIMIT: 8,
    FailureKind.CONNECTION: 9,
    FailureKind.UNKNOWN: 10,
    # Lo que no es un fallo va al final: si en la misión pasó CUALQUIER otra
    # cosa, esa es la que explica por qué acabó mal.
    FailureKind.PERMISSION_DENIED: 20,
    FailureKind.USER_CANCELLED: 21,
}


def dominant(kinds) -> Optional[FailureKind]:
    """De todos los fallos de una misión, ¿cuál la explica? Sin ninguno,
    None (y entonces no hay nada que excusar ni que atribuir)."""
    mejor: Optional[FailureKind] = None
    mejor_p = 999
    for k in kinds or []:
        try:
            kk = k if isinstance(k, FailureKind) else FailureKind(str(k))
        except ValueError:
            continue
        p = _PRIORIDAD.get(kk, 99)
        if p < mejor_p:
            mejor, mejor_p = kk, p
    return mejor
