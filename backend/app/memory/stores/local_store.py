# app/memory/stores/local_store.py — LocalMemoryStore(IMemoryStore) sobre ChromaDB
#
# V0.85 (MOS M1). Implementacion de referencia del contrato IMemoryStore.
# Usa el cliente ChromaDB compartido del MemoryManager legacy (una sola carga
# de sentence-transformers). Una coleccion por MemoryType; la creacion es lazy.
#
# DISENO:
#   - CONVERSATIONAL aliasa la coleccion legacy 'conversations' (sin migracion
#     de datos: doc 07 §4). El resto usa el .value del MemoryType como nombre.
#   - Todas las operaciones ChromaDB son sincronas y potencialmente lentas
#     (embedding); se envuelven en asyncio.to_thread para no bloquear el loop.
#   - Degradacion graceful (08 RFC-002): si la memoria no esta sana, store()
#     devuelve "", las lecturas devuelven [] / None / "" — nunca se lanza.
#   - ChromaDB solo acepta metadata escalar (str/int/float/bool, sin None ni
#     listas): _clean_metadata() sanea antes de escribir.
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date, datetime
from typing import Any, Optional

from app.memory.interfaces import IMemoryStore, MemoryItem, MemoryType
from app.memory.memory_manager import memory_manager

# CONVERSATIONAL reutiliza la coleccion legacy creada en V0.6 (alias, doc 07 §4).
_COLLECTION_ALIASES: dict[MemoryType, str] = {
    MemoryType.CONVERSATIONAL: "conversations",
}

# Tipos activos en V0.85 (los reservados se crean lazy al primer store si se usan).
ACTIVE_TYPES: tuple[MemoryType, ...] = (
    MemoryType.CONVERSATIONAL,
    MemoryType.PERSONAL,
    MemoryType.PROJECT,
    MemoryType.SKILL,
    MemoryType.DECISION,
)


def _collection_name(memory_type: MemoryType) -> str:
    return _COLLECTION_ALIASES.get(memory_type, memory_type.value)


def _clean_metadata(meta: dict) -> dict[str, Any]:
    """ChromaDB solo admite valores escalares no nulos. Serializa listas/dicts a
    JSON, descarta None y castea el resto a str. Determinista y sin perdidas
    (las listas se recuperan con json.loads en el consumidor)."""
    clean: dict[str, Any] = {}
    for k, v in meta.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            clean[k] = v
        elif isinstance(v, (list, dict)):
            clean[k] = json.dumps(v, ensure_ascii=False)
        else:
            clean[k] = str(v)
    return clean


def _score_from_distance(distance: Optional[float]) -> Optional[float]:
    """Convierte la distancia de ChromaDB (0 = idéntico) en relevancia (0,1]."""
    if distance is None:
        return None
    try:
        return 1.0 / (1.0 + float(distance))
    except (TypeError, ValueError):
        return None


class LocalMemoryStore(IMemoryStore):
    """IMemoryStore sobre ChromaDB local (una coleccion por MemoryType)."""

    def __init__(self):
        # Cache de colecciones ya resueltas (name -> Collection). Se rellena lazy.
        self._collections: dict[str, Any] = {}

    # -- salud / colecciones -------------------------------------------------

    @property
    def healthy(self) -> bool:
        return memory_manager.is_healthy()

    def _collection(self, memory_type: MemoryType):
        """Coleccion ChromaDB para un tipo (lazy, cacheada). None si no hay memoria."""
        name = _collection_name(memory_type)
        col = self._collections.get(name)
        if col is not None:
            return col
        col = memory_manager.get_or_create_collection(name)
        if col is not None:
            self._collections[name] = col
        return col

    # -- IMemoryStore --------------------------------------------------------

    async def store(
        self,
        content: str,
        memory_type: MemoryType,
        source: str,
        metadata: Optional[dict] = None,
        dedup_key: Optional[str] = None,
    ) -> str:
        if not self.healthy or not content:
            return ""

        now = datetime.utcnow()
        item_id = (
            f"{memory_type.value}:{dedup_key}"
            if dedup_key
            else f"{memory_type.value}:{uuid.uuid4().hex}"
        )
        meta = _clean_metadata(
            {
                "source": source,
                "memory_type": memory_type.value,
                "created_at_iso": now.isoformat(),
                "date": now.date().isoformat(),
                **(metadata or {}),
            }
        )

        def _work() -> str:
            col = self._collection(memory_type)
            if col is None:
                return ""
            # Idempotencia por dedup_key: si el id ya existe, ACTUALIZA.
            existing = col.get(ids=[item_id])
            if existing and existing.get("ids"):
                col.update(ids=[item_id], documents=[content], metadatas=[meta])
            else:
                col.add(ids=[item_id], documents=[content], metadatas=[meta])
            return item_id

        try:
            return await asyncio.to_thread(_work)
        except Exception as e:  # degradacion graceful
            print(f"[LocalMemoryStore] store({memory_type.value}) error: {e}")
            return ""

    async def search(
        self,
        query: str,
        memory_types: Optional[list[MemoryType]] = None,
        top_k: int = 5,
        filters: Optional[dict] = None,
    ) -> list[MemoryItem]:
        if not self.healthy or not query:
            return []
        types = list(memory_types) if memory_types else list(ACTIVE_TYPES)
        where = filters or None

        def _work() -> list[MemoryItem]:
            items: list[MemoryItem] = []
            for mt in types:
                col = self._collection(mt)
                if col is None:
                    continue
                count = col.count()
                if count == 0:
                    continue
                res = col.query(
                    query_texts=[query],
                    n_results=min(top_k, count),
                    **({"where": where} if where else {}),
                )
                items.extend(_results_to_items(mt, res))
            # Mezcla entre colecciones: mayor score (menor distancia) primero.
            items.sort(key=lambda it: (it.score if it.score is not None else 0.0), reverse=True)
            return items[:top_k]

        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            print(f"[LocalMemoryStore] search error: {e}")
            return []

    async def retrieve(self, item_id: str) -> Optional[MemoryItem]:
        if not self.healthy or not item_id:
            return None
        # El id lleva prefijo 'mem_xxx:...'; se resuelve la coleccion por prefijo.
        prefix = item_id.split(":", 1)[0] if ":" in item_id else ""
        try:
            memory_type = MemoryType(prefix)
        except ValueError:
            memory_type = None

        def _work() -> Optional[MemoryItem]:
            cols = (
                [self._collection(memory_type)]
                if memory_type is not None
                else [self._collection(mt) for mt in ACTIVE_TYPES]
            )
            for col in cols:
                if col is None:
                    continue
                got = col.get(ids=[item_id])
                if got and got.get("ids"):
                    mt = memory_type or _type_from_meta(got.get("metadatas", [{}])[0])
                    return _single_to_item(mt, item_id, got)
            return None

        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            print(f"[LocalMemoryStore] retrieve error: {e}")
            return None

    async def summarize(
        self, memory_type: MemoryType, date_from: date, date_to: date
    ) -> str:
        """V0.85 M1: resumen determinista minimo (conteo + primeras lineas del
        rango). El resumen rico Ollama-first llega en M3 (summarizer.py) y se
        cachea como item kind=daily_summary; este metodo lo preferira entonces."""
        if not self.healthy:
            return ""
        f_iso, t_iso = date_from.isoformat(), date_to.isoformat()

        def _work() -> str:
            col = self._collection(memory_type)
            if col is None:
                return ""
            got = col.get(where={"date": {"$gte": f_iso, "$lte": t_iso}})
            docs = got.get("documents", []) if got else []
            if not docs:
                return ""
            head = [d[:120] for d in docs[:5]]
            lines = "\n".join(f"- {h}" for h in head)
            return (
                f"{len(docs)} elementos en {memory_type.value} "
                f"({f_iso}..{t_iso}):\n{lines}"
            )

        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            print(f"[LocalMemoryStore] summarize error: {e}")
            return ""

    async def forget(self, memory_type: MemoryType, filters: dict) -> int:
        if not self.healthy:
            return 0

        def _work() -> int:
            col = self._collection(memory_type)
            if col is None:
                return 0
            got = col.get(**({"where": filters} if filters else {}))
            ids = got.get("ids", []) if got else []
            if ids:
                col.delete(ids=ids)
            return len(ids)

        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            print(f"[LocalMemoryStore] forget error: {e}")
            return 0

    async def context(
        self,
        query: str,
        max_tokens: int = 1500,
        memory_types: Optional[list[MemoryType]] = None,
    ) -> str:
        """Bloque de contexto con ATRIBUCION de fuente por linea. Presupuesto de
        tokens aproximado por caracteres (~4 chars/token). El chat (M4) envuelve
        esta llamada con un timeout de 300 ms."""
        items = await self.search(query, memory_types=memory_types, top_k=8)
        if not items:
            return ""
        budget_chars = max(200, max_tokens * 4)
        parts: list[str] = []
        used = 0
        for it in items:
            when = it.created_at.date().isoformat() if it.created_at else ""
            attribution = f"[{it.source}" + (f" · {when}" if when else "") + "]"
            line = f"{attribution} {it.content.strip()}"
            if used + len(line) > budget_chars:
                break
            parts.append(line)
            used += len(line) + 1
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Helpers de conversion ChromaDB -> MemoryItem
# ---------------------------------------------------------------------------
def _type_from_meta(meta: Optional[dict]) -> MemoryType:
    if meta:
        raw = meta.get("memory_type")
        if raw:
            try:
                return MemoryType(raw)
            except ValueError:
                pass
    return MemoryType.PERSONAL


def _parse_dt(meta: Optional[dict]) -> datetime:
    if meta and meta.get("created_at_iso"):
        try:
            return datetime.fromisoformat(str(meta["created_at_iso"]))
        except (ValueError, TypeError):
            pass
    return datetime.utcnow()


def _results_to_items(memory_type: MemoryType, res: dict) -> list[MemoryItem]:
    """Convierte la salida de collection.query (listas anidadas) en MemoryItems."""
    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    items: list[MemoryItem] = []
    for i, doc_id in enumerate(ids):
        meta = metas[i] if i < len(metas) and metas[i] else {}
        dist = dists[i] if i < len(dists) else None
        items.append(
            MemoryItem(
                id=doc_id,
                content=docs[i] if i < len(docs) else "",
                memory_type=memory_type,
                source=str(meta.get("source", "")),
                created_at=_parse_dt(meta),
                metadata=dict(meta),
                score=_score_from_distance(dist),
            )
        )
    return items


def _single_to_item(memory_type: MemoryType, item_id: str, got: dict) -> MemoryItem:
    """Convierte la salida de collection.get(ids=[id]) (listas planas) en MemoryItem."""
    docs = got.get("documents") or []
    metas = got.get("metadatas") or []
    meta = metas[0] if metas and metas[0] else {}
    return MemoryItem(
        id=item_id,
        content=docs[0] if docs else "",
        memory_type=memory_type,
        source=str(meta.get("source", "")),
        created_at=_parse_dt(meta),
        metadata=dict(meta),
        score=None,
    )
