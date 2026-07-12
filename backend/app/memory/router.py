# app/memory/router.py — MemoryRouter: MemoryType -> IMemoryStore (V0.85, M1)
#
# EL punto de indireccion tecnologica del MOS (08 RFC-006). Todo consumidor
# (chat, ingesta, briefing, Orchestrator, Hermes) habla contra `memory_router`;
# JAMAS contra ChromaDB ni contra un store concreto. En V0.85 TODOS los tipos
# se enrutan a un unico LocalMemoryStore; registrar un store nuevo (Qdrant en
# V1.x, distribuido en V2.0+) es cambiar el mapa, sin tocar un solo caller.
#
# Regla de dependencias (doc 07 §2, inviolable):
#   endpoints -> MemoryRouter -> IMemoryStore -> ChromaDB.  Nadie salta capas.
from __future__ import annotations

from datetime import date
from typing import Optional

from app.memory.interfaces import IMemoryStore, MemoryItem, MemoryType
from app.memory.stores.local_store import ACTIVE_TYPES, LocalMemoryStore


class MemoryRouter:
    """Enruta cada MemoryType a su IMemoryStore. Delega los 6 metodos del
    contrato. `search`/`context` pueden abarcar varios tipos: si viven en el
    mismo store (caso V0.85), es una sola llamada; si no, agrupa y mezcla."""

    def __init__(self, default_store: IMemoryStore):
        self._default: IMemoryStore = default_store
        self._routes: dict[MemoryType, IMemoryStore] = {}

    # -- registro (el punto de intercambio tecnologico) ----------------------

    def register(self, memory_type: MemoryType, store: IMemoryStore) -> None:
        """Enruta un tipo a un store concreto. V1.x lo usa para dual-write /
        swap de motor (Chroma->Qdrant) sin tocar a los consumidores."""
        self._routes[memory_type] = store

    def _store_for(self, memory_type: MemoryType) -> IMemoryStore:
        return self._routes.get(memory_type, self._default)

    @property
    def healthy(self) -> bool:
        store = self._default
        return getattr(store, "healthy", True)

    # -- IMemoryStore (delegado) ---------------------------------------------

    async def store(
        self,
        content: str,
        memory_type: MemoryType,
        source: str,
        metadata: Optional[dict] = None,
        dedup_key: Optional[str] = None,
    ) -> str:
        return await self._store_for(memory_type).store(
            content, memory_type, source, metadata=metadata, dedup_key=dedup_key
        )

    async def search(
        self,
        query: str,
        memory_types: Optional[list[MemoryType]] = None,
        top_k: int = 5,
        filters: Optional[dict] = None,
    ) -> list[MemoryItem]:
        types = list(memory_types) if memory_types else list(ACTIVE_TYPES)
        # Agrupa tipos por store (por identidad de instancia).
        groups: dict[int, tuple[IMemoryStore, list[MemoryType]]] = {}
        for mt in types:
            store = self._store_for(mt)
            groups.setdefault(id(store), (store, []))[1].append(mt)

        if len(groups) == 1:
            store, ts = next(iter(groups.values()))
            return await store.search(query, memory_types=ts, top_k=top_k, filters=filters)

        merged: list[MemoryItem] = []
        for store, ts in groups.values():
            merged.extend(await store.search(query, memory_types=ts, top_k=top_k, filters=filters))
        merged.sort(key=lambda it: (it.score if it.score is not None else 0.0), reverse=True)
        return merged[:top_k]

    async def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        # El id lleva prefijo 'mem_xxx:...' -> resuelve el store por tipo.
        prefix = item_id.split(":", 1)[0] if ":" in item_id else ""
        try:
            store = self._store_for(MemoryType(prefix))
        except ValueError:
            store = self._default
        return await store.retrieve(item_id)

    async def summarize(
        self, memory_type: MemoryType, date_from: date, date_to: date
    ) -> str:
        return await self._store_for(memory_type).summarize(memory_type, date_from, date_to)

    async def forget(self, memory_type: MemoryType, filters: dict) -> int:
        return await self._store_for(memory_type).forget(memory_type, filters)

    async def context(
        self,
        query: str,
        max_tokens: int = 1500,
        memory_types: Optional[list[MemoryType]] = None,
    ) -> str:
        # En V0.85 todos los tipos viven en el store por defecto -> una llamada.
        # (Multi-store: la construccion del bloque con atribucion vive en el
        # store; cuando existan varios, se compondra a nivel de router — V1.x.)
        types = list(memory_types) if memory_types else list(ACTIVE_TYPES)
        stores = {id(self._store_for(mt)): self._store_for(mt) for mt in types}
        if len(stores) == 1:
            store = next(iter(stores.values()))
            return await store.context(query, max_tokens=max_tokens, memory_types=types)
        # Fallback multi-store (no ocurre en V0.85): el store por defecto.
        return await self._default.context(query, max_tokens=max_tokens, memory_types=types)


# Singleton global — mismo patron que ai_manager / memory_manager.
# El LocalMemoryStore no re-inicializa ChromaDB: reutiliza el cliente del
# memory_manager legacy via su accesor compartido (una sola carga del modelo).
memory_router = MemoryRouter(default_store=LocalMemoryStore())
