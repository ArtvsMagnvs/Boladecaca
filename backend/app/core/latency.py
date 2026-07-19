# app/core/latency.py — presupuestos de latencia para lo que mira la UI
#
# LA REGLA (2026-07-19): ninguna petición que la interfaz hace de forma
# periódica puede quedarse esperando a una red externa. Si el dato no está a
# tiempo, se devuelve lo último que se sabía —o nada— pero se RESPONDE.
#
# POR QUÉ EXISTE ESTE MÓDULO: el proyecto ya aplicaba esta idea suelta en dos
# sitios (`chat_service.build_system_prompt` y `tie/enricher.enrich`, ambos con
# 300 ms duros sobre el MOS), pero no en los endpoints de estado — y ahí es donde
# más dolía. Con el usuario sin internet, `GET /api/ai/status` tardaba 10-15 s
# (una petición de chat REAL al proveedor) y el Sidebar lo pedía cada 30 s desde
# TODAS las páginas. Tener la regla escrita en un solo sitio la hace aplicable y
# testeable, en vez de depender de que cada endpoint nuevo se acuerde.
#
# Lo que este módulo NO hace: no cancela el trabajo de fondo. `asyncio.wait_for`
# cancela la espera; si la tarea de dentro está bloqueada en un `getaddrinfo` del
# sistema, ese hilo seguirá ocupado hasta que el SO se rinda. Por eso el patrón
# completo es presupuesto + caché (ver `stale_while_revalidate`), no solo
# presupuesto.
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Optional, TypeVar

from app.core.logging_config import get_system_logger

logger = get_system_logger("core.latency")

T = TypeVar("T")

# Presupuesto por defecto para un endpoint de estado. Generoso para una llamada
# local (BD, disco) y tacaño para una red externa, que es justo la intención.
DEFAULT_BUDGET_MS = 1500


async def with_budget(
    awaitable: Awaitable[T],
    *,
    ms: int = DEFAULT_BUDGET_MS,
    default: T = None,
    label: str = "",
) -> T:
    """Espera `awaitable` como mucho `ms`. Si no llega a tiempo (o falla),
    devuelve `default`. NUNCA lanza: quien llama es una ruta de UI y su
    obligación es responder algo.

    El caso de timeout se registra en INFO, no en ERROR: que un proveedor
    externo no conteste no es un fallo de Aithera, y llenar el log de errores
    rojos por estar sin internet solo entierra los problemas de verdad."""
    try:
        return await asyncio.wait_for(asyncio.ensure_future(awaitable), timeout=ms / 1000)
    except asyncio.TimeoutError:
        logger.info(f"[latency] {label or 'operación'} excedió {ms} ms — devuelvo el valor por defecto")
        return default
    except Exception as e:
        logger.info(f"[latency] {label or 'operación'} falló ({type(e).__name__}: {e}) — valor por defecto")
        return default


class StaleWhileRevalidate:
    """Caché que SIEMPRE responde al instante y se refresca por detrás.

    El patrón que le faltaba a `/api/ai/status`. Su caché anterior tenía un TTL
    de 30 s y el Sidebar preguntaba cada 30 s exactos: como el tiempo entre polls
    siempre es un pelín MAYOR que el TTL (latencia + jitter del timer), la
    condición `transcurrido < TTL` fallaba casi siempre. Era una caché con ~0% de
    aciertos por construcción, y cada poll pagaba la llamada de red entera.

    Aquí el TTL solo decide CUÁNDO refrescar por detrás, nunca si se espera:
      - hay valor (fresco o rancio) -> se devuelve YA; si está rancio se lanza un
        refresco en segundo plano
      - no hay valor todavía (primer arranque) -> se espera, pero solo `first_ms`

    Un solo refresco en vuelo a la vez: sin esto, N peticiones concurrentes
    dispararían N llamadas de red a un proveedor que ya sabemos que va lento."""

    def __init__(self, *, ttl_s: float, first_ms: int = DEFAULT_BUDGET_MS):
        self._ttl_s = ttl_s
        self._first_ms = first_ms
        self._values: dict[str, tuple[float, Any]] = {}
        self._refreshing: set[str] = set()

    def peek(self, key: str) -> tuple[Optional[Any], bool]:
        """(valor, está_fresco). `valor` es None si nunca se ha calculado."""
        entry = self._values.get(key)
        if entry is None:
            return None, False
        ts, value = entry
        return value, (asyncio.get_running_loop().time() - ts) < self._ttl_s

    def put(self, key: str, value: Any) -> None:
        self._values[key] = (asyncio.get_running_loop().time(), value)

    async def get(self, key: str, factory: Callable[[], Awaitable[T]], *, default: T = None) -> T:
        """Devuelve el valor cacheado al instante; refresca por detrás si toca."""
        value, fresh = self.peek(key)
        if value is not None and fresh:
            return value

        if value is not None:
            self._spawn_refresh(key, factory)   # rancio: se sirve y se refresca
            return value

        # Primera vez: no hay nada que servir, así que toca esperar — pero poco.
        result = await with_budget(factory(), ms=self._first_ms, default=default,
                                   label=f"primer cálculo de {key}")
        if result is not None:
            self.put(key, result)
        return result

    def _spawn_refresh(self, key: str, factory: Callable[[], Awaitable[Any]]) -> None:
        if key in self._refreshing:
            return
        self._refreshing.add(key)

        async def _refresh() -> None:
            try:
                self.put(key, await factory())
            except Exception as e:
                logger.info(f"[latency] refresco en segundo plano de {key} falló: {type(e).__name__}: {e}")
            finally:
                self._refreshing.discard(key)

        try:
            asyncio.get_running_loop().create_task(_refresh())
        except RuntimeError:      # sin loop (scripts/tests sync): no se refresca
            self._refreshing.discard(key)
