# app/core/events.py — Event Bus in-process (V0.85 M2, [Δ] doc 07 §6)
#
# Especificacion canonica: PLAN_MAESTRO_2026/17_EVENT_BUS_OBSERVABILIDAD.md.
# Una notificacion, NO un mecanismo de control: nadie depende de que un evento
# sea consumido (si B necesita que A haga algo, B llama a la API publica de A).
#
# Reglas duras (doc 17 §1): sin persistencia, sin replay, sin prioridades, sin
# colas, sin red. At-most-once, best-effort. Un handler roto NUNCA afecta al
# emisor ni a otros handlers (aislamiento total).
#
# Naming: "<dominio>.<hecho_en_pasado>" (doc 17 §3), p.ej. "memory.ingested".
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Awaitable, Callable, Optional

from app.core.logging_config import get_system_logger

logger = get_system_logger("events")


@dataclass(frozen=True)
class Event:
    """Un hecho consumado. `ts` lo estampa el bus (SIEMPRE en emit, nunca el
    emisor) para que el orden temporal sea consistente por construccion."""
    name: str            # "memory.ingested"
    source: str           # modulo emisor: "mos" | "tie" | "automation" | ...
    ts: datetime           # UTC
    payload: dict = field(default_factory=dict)  # plano, pequeno, JSON-serializable


Handler = Callable[[Event], Awaitable[None]]

# Registro interno: name -> [handlers]. "*" = comodin (todos los eventos).
_subscribers: dict[str, list[Handler]] = {}


def subscribe(name: str, handler: Handler) -> None:
    """`name` = nombre exacto o "*" (todos). El comodin es el punto de conexion
    de una futura telemetria (Runtime Intelligence, V2.0+) — no hay patrones
    parciales tipo "mission.*"."""
    _subscribers.setdefault(name, []).append(handler)


def unsubscribe(name: str, handler: Handler) -> None:
    handlers = _subscribers.get(name)
    if handlers and handler in handlers:
        handlers.remove(handler)


def emit(name: str, source: str, payload: Optional[dict] = None) -> None:
    """No bloqueante y a prueba de todo. Sin suscriptores es un lookup de dict
    + return (~microsegundos) — el caso normal para la mayoria de eventos."""
    handlers = _subscribers.get(name, []) + _subscribers.get("*", [])
    if not handlers:
        return
    event = Event(name=name, source=source, ts=datetime.utcnow(), payload=payload or {})
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Sin loop corriendo (p.ej. contexto sync): no hay donde programar el
        # handler async. Se descarta — at-most-once, best-effort (doc 17 §8).
        logger.warning(f"emit({name}) sin event loop activo — evento descartado")
        return
    for handler in handlers:
        loop.create_task(_run_handler(handler, event))


async def _run_handler(handler: Handler, event: Event) -> None:
    """Aisla cada handler: una excepcion se loguea y no se propaga jamas."""
    try:
        await handler(event)
    except Exception as e:
        logger.error(f"handler de '{event.name}' fallo (ignorado): {type(e).__name__}: {e}")
