# app/memory/stores/distributed_store.py — STUB (V2.0+)
#
# Placeholder del store distribuido de la era de red (nodo aislado de Private
# Memory, 08 RFC-001). Implementa IMemoryStore para que el contrato quede
# cerrado desde V0.85, pero cada operacion lanza NotImplementedError: nadie lo
# instancia ni lo registra en el MemoryRouter todavia. Cuando llegue V2.0, esta
# clase se rellena y pasa la MISMA suite test_memory_contracts (08 RFC-006).
from __future__ import annotations

from datetime import date
from typing import Optional

from app.memory.interfaces import IMemoryStore, MemoryItem, MemoryType

_MSG = "DistributedMemoryStore: disponible en V2.0+ (capa de red, 08 RFC-001)."


class DistributedMemoryStore(IMemoryStore):
    """Stub del store distribuido. Firma viva, cuerpo en V2.0+."""

    async def store(
        self,
        content: str,
        memory_type: MemoryType,
        source: str,
        metadata: Optional[dict] = None,
        dedup_key: Optional[str] = None,
    ) -> str:
        raise NotImplementedError(_MSG)

    async def search(
        self,
        query: str,
        memory_types: Optional[list[MemoryType]] = None,
        top_k: int = 5,
        filters: Optional[dict] = None,
    ) -> list[MemoryItem]:
        raise NotImplementedError(_MSG)

    async def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        raise NotImplementedError(_MSG)

    async def summarize(
        self, memory_type: MemoryType, date_from: date, date_to: date
    ) -> str:
        raise NotImplementedError(_MSG)

    async def forget(self, memory_type: MemoryType, filters: dict) -> int:
        raise NotImplementedError(_MSG)

    async def context(
        self,
        query: str,
        max_tokens: int = 1500,
        memory_types: Optional[list[MemoryType]] = None,
    ) -> str:
        raise NotImplementedError(_MSG)
