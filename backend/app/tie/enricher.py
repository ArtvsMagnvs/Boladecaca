# app/tie/enricher.py — Context Builder del TIE (doc 11-B §B.1/§B.2, T2)
#
# El "Memory Bridge" del briefing ELIMINADO (doc 14 §3.1): esto NO es un puente,
# es una llamada al Context API del MOS con presupuesto. Trae contexto con
# atribución de fuente para alimentar al planner (y, por-nodo, al executor en T3).
#
# Dos garantías (doc 11 B.2 / doc 14 §6):
#   - PRESUPUESTO DE LATENCIA DURO (`TIE_CONTEXT_BUDGET_MS`, 300 ms): si el MOS
#     tarda más, se devuelve contexto vacío — el TIE NUNCA espera (mismo patrón
#     que chat_service en V0.85 M4).
#   - CACHÉ 60 s por (query, tipos): pre-fetchs repetidos no repiten el trabajo.
#
# Pre-fetch: el enricher se lanza EN PARALELO con `intents.classify` (doc 11 B.2)
# — esa orquestación (asyncio.gather) vive en el pipeline (`handle`, T4). Aquí la
# función es autónoma y testeable en aislamiento.
from __future__ import annotations

import asyncio
import time
from typing import Optional

from app.core.config import settings
from app.core.logging_config import get_system_logger

logger = get_system_logger("tie.enricher")

_CACHE_TTL_S = 60.0
# caché simple en memoria: {(query, tipos_ordenados): (contexto, expira_monotonic)}
_cache: dict[tuple, tuple[str, float]] = {}


def _map_memory_types(names: Optional[list[str]]):
    """Traduce los strings del Intent (p.ej. 'mem_project') a MemoryType. Ignora
    los desconocidos (nunca lanza). None/[] → None = todos los tipos activos."""
    if not names:
        return None
    from app.memory import MemoryType

    valid_by_value = {mt.value: mt for mt in MemoryType}
    out = []
    for n in names:
        mt = valid_by_value.get(n)
        if mt is not None:
            out.append(mt)
    return out or None


async def enrich(
    query: str,
    *,
    memory_types: Optional[list[str]] = None,
    budget_ms: Optional[int] = None,
    max_tokens: int = 1500,
) -> str:
    """Bloque de contexto del MOS para `query`, con atribución de fuente, dentro
    del presupuesto de latencia. Devuelve "" si no hay memoria, si se agota el
    presupuesto, o ante cualquier error — el caller (planner/pipeline) sigue sin
    contexto en vez de esperar o romper."""
    query = (query or "").strip()
    if not query:
        return ""

    types_key = tuple(sorted(memory_types)) if memory_types else ()
    key = (query, types_key, max_tokens)
    now = time.monotonic()

    cached = _cache.get(key)
    if cached and cached[1] > now:
        return cached[0]

    budget_s = (budget_ms if budget_ms is not None else settings.TIE_CONTEXT_BUDGET_MS) / 1000.0
    try:
        from app.memory import memory_router

        mts = _map_memory_types(memory_types)
        ctx = await asyncio.wait_for(
            memory_router.context(query, max_tokens=max_tokens, memory_types=mts),
            timeout=budget_s,
        )
        ctx = ctx or ""
    except asyncio.TimeoutError:
        logger.info(f"[enricher] presupuesto de {budget_s*1000:.0f}ms agotado — contexto vacío")
        ctx = ""
    except Exception as e:
        logger.error(f"[enricher] context() falló (contexto vacío): {type(e).__name__}: {e}")
        ctx = ""

    _cache[key] = (ctx, now + _CACHE_TTL_S)
    return ctx


def clear_cache() -> None:
    """Limpia la caché (tests / cambios de memoria que invalidan el contexto)."""
    _cache.clear()
