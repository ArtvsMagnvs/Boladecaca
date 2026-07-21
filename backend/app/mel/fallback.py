# app/mel/fallback.py — clasificación de fallos + circuit breakers (doc 19 §8)
#
# Dos piezas deterministas:
#   1. `classify_failure` — un fallo (excepción o dict de error del proveedor) →
#      una ACCIÓN (saltar al siguiente candidato / reintentar el mismo / parar).
#      Es la tabla del doc 19 §8.1, aterrizada a lo que Aithera puede detectar hoy.
#   2. `CircuitBreaker` — por proveedor: se abre tras varios fallos seguidos y se
#      salta sin intentar durante un tiempo. Estado EN MEMORIA (se pierde al
#      reiniciar: correcto, reiniciar es re-sondear — doc 19 §8.2).
from __future__ import annotations

import time
from enum import Enum


class FailureAction(str, Enum):
    NEXT = "next"          # saltar al siguiente candidato de la cadena
    RETRY_ONCE = "retry"   # reintentar UNA vez el mismo modelo (respuesta vacía)
    STOP = "stop"          # NO rotar: el fallo es del request, no del proveedor


# Marcas textuales que indican que el fallo es del PROMPT/REQUEST (4xx de
# validación), no del proveedor — no tiene sentido rotar de modelo (doc 19 §8.1).
_REQUEST_FAULT_MARKS = ("invalid request", "400", "content policy", "prompt too long",
                        "context length", "max_tokens")

# Errores de red/transitorios → siguiente + cuentan para el breaker.
_TRANSIENT_MARKS = ("timeout", "timed out", "connection", "connect", "getaddrinfo",
                    "5xx", "500", "502", "503", "504", "network", "unavailable")


def classify_failure(*, exc: Exception | None = None, detail: str = "") -> tuple[FailureAction, str]:
    """Clasifica un fallo → (acción, razón corta). `exc` para excepciones reales;
    `detail` para el texto de un dict de error del proveedor. La razón se usa como
    `fallback_reason` en `mel_executions` y en la traza."""
    text = (detail or "").lower()
    if exc is not None:
        text = f"{type(exc).__name__}: {exc}".lower()

    # 1) fallo del propio request → parar (rotar no ayudaría)
    if any(m in text for m in _REQUEST_FAULT_MARKS):
        return FailureAction.STOP, "request_invalid"

    # 2) respuesta vacía (post-strip) → un reintento del mismo modelo
    if "empty" in text or text.strip() in ("", "vacío", "vacio"):
        return FailureAction.RETRY_ONCE, "empty_response"

    # 3) transitorio (red/5xx/timeout) → siguiente + cuenta para el breaker
    if any(m in text for m in _TRANSIENT_MARKS):
        return FailureAction.NEXT, "transient"

    # 4) auth (401/403) → siguiente, pero NO cuenta para el breaker (es config)
    if "401" in text or "403" in text or "unauthorized" in text or "forbidden" in text:
        return FailureAction.NEXT, "auth"

    # 5) cuota/rate (402/429) → siguiente
    if "429" in text or "402" in text or "quota" in text or "rate limit" in text:
        return FailureAction.NEXT, "quota"

    # por defecto: siguiente (un fallo desconocido no debe colgar la cadena)
    return FailureAction.NEXT, "unknown"


# Razones que cuentan para abrir el breaker (fallos del PROVEEDOR, no de config
# ni del request). Auth/quota/request_invalid no abren el breaker.
_BREAKER_REASONS = frozenset({"transient", "unknown"})


class CircuitBreaker:
    """Un breaker por proveedor. closed → open con ≥ FAILS_TO_OPEN fallos de
    proveedor en WINDOW_S; open durante OPEN_S (se salta sin intentar); tras eso
    half-open (se permite 1 sonda) → éxito cierra, fallo reabre. En memoria."""

    FAILS_TO_OPEN = 3
    WINDOW_S = 60.0
    OPEN_S = 90.0

    def __init__(self) -> None:
        # provider -> {"fails": [ts...], "open_until": float}
        self._state: dict[str, dict] = {}

    def is_closed(self, provider: str) -> bool:
        """¿Se puede intentar este proveedor ahora? (closed o half-open)."""
        st = self._state.get(provider)
        if not st:
            return True
        open_until = st.get("open_until", 0.0)
        return time.monotonic() >= open_until  # half-open cuenta como intentable

    def record_success(self, provider: str) -> None:
        self._state.pop(provider, None)   # éxito limpia el estado (cierra)

    def record_failure(self, provider: str, reason: str) -> None:
        if reason not in _BREAKER_REASONS:
            return  # auth/quota/request no abren el breaker
        now = time.monotonic()
        st = self._state.setdefault(provider, {"fails": [], "open_until": 0.0})
        st["fails"] = [t for t in st["fails"] if now - t < self.WINDOW_S]
        st["fails"].append(now)
        st["last_reason"] = reason   # [2026-07-21] para el panel de fallos de la UI
        if len(st["fails"]) >= self.FAILS_TO_OPEN:
            st["open_until"] = now + self.OPEN_S

    def open_reason(self, provider: str) -> str | None:
        """[2026-07-21] Motivo del último fallo si el breaker está ABIERTO ahora
        (None si está cerrado/sano). Alimenta los avisos de Inteligencia."""
        st = self._state.get(provider)
        if not st or time.monotonic() >= st.get("open_until", 0.0):
            return None
        return st.get("last_reason") or "unknown"

    def reset(self) -> None:
        self._state.clear()


# Singleton en memoria (doc 19 §8.2: estado efímero, se pierde al reiniciar).
breakers = CircuitBreaker()
