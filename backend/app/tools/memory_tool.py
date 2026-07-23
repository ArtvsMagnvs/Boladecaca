# backend/app/tools/memory_tool.py
#
# V1.0/1.1 (Tools): wrapper FINO sobre el MOS (app.memory.memory_router) para
# que un agente pueda buscar/guardar/actualizar/eliminar memoria por su cuenta,
# sin saltarse la capa MemoryRouter -> IMemoryStore -> ChromaDB (doc 07 §2,
# inviolable: nadie salta capas). Deliberadamente simple: 4 acciones, nada mas.
#
# "Actualizar" reusa el mismo mecanismo de dedup_key que ya tiene store()
# (doc 07/M1): el id de un item es SIEMPRE "{memory_type}:{dedup_key}", asi que
# actualizar = volver a hacer store() con el dedup_key extraido del id
# existente. No se inventa ningun metodo nuevo en el contrato congelado del MOS.
#
# Acciones:
#   search_memory  -> memory_router.search()
#   save_memory    -> memory_router.store()
#   update_memory  -> retrieve() + store() con el mismo dedup_key (sobreescribe)
#   delete_memory  -> memory_router.forget() (filtro de metadata, tal cual el contrato)

from typing import Dict, Any, List, Optional

from .base import BaseTool
from app.memory import MemoryType, memory_router, ACTIVE_TYPES

# [2026-07-23] Fiabilidad de memoria (CRITICO pre-1.0): `MemoryType` tiene 5
# tipos ACTIVOS (buscados por defecto) + 6 RESERVADOS (mem_knowledge, mem_tool,
# mem_working...) que solo existen como esqueleto para fases futuras y que
# escriben sistemas internos concretos (el AE escribe mem_automation/mem_error,
# decision_service escribe mem_decision). Antes, `list_actions()` anunciaba los
# 11 por igual y `_parse_memory_type` los aceptaba todos: un modelo que guardaba
# un hecho con `memory_type="mem_knowledge"` (semanticamente tentador) lo hacia
# con exito, pero ese item queda INVISIBLE para cualquier busqueda por defecto
# (`search()`/`context()` filtran a `ACTIVE_TYPES` si no se especifica lo
# contrario) -- el dato "se guarda pero no se recupera", diagnosticado en
# testeos reales del task-bench. Fix: la tool de memoria de proposito general
# (la que usan agentes/toolloop) solo conoce los tipos activos.
_ACTIVE_VALUES = {t.value for t in ACTIVE_TYPES}


def _parse_memory_type(value: str) -> Optional[MemoryType]:
    """Acepta tanto el valor completo ('mem_personal') como el nombre corto
    ('personal') -- mas comodo para quien llama a la tool. Solo devuelve un
    tipo ACTIVO: los reservados (mem_knowledge, mem_tool...) son invisibles
    para la busqueda por defecto y no son responsabilidad de esta tool."""
    if not value:
        return None
    for candidate in (value, f"mem_{value}"):
        if candidate in _ACTIVE_VALUES:
            return MemoryType(candidate)
    return None


class MemoryTool(BaseTool):
    tool_id = "memory"
    name = "Memory Tool"
    description = (
        "Busca, guarda, actualiza y elimina memoria semantica del MOS "
        "(preferencias, contexto personal, proyectos, decisiones)."
    )
    requires_confirmation = False  # depende de la accion

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            handler = {
                "search_memory": self._search,
                "save_memory": self._save,
                "update_memory": self._update,
                "delete_memory": self._delete,
            }.get(action)
            if not handler:
                return {
                    "success": False, "result": None,
                    "error": f"Accion desconocida: {action}. Disponibles: search_memory, save_memory, update_memory, delete_memory",
                }
            return await handler(params)
        except Exception as e:
            return {"success": False, "result": None, "error": f"{type(e).__name__}: {e}"}

    def list_actions(self) -> List[Dict[str, Any]]:
        # Solo se anuncian los tipos ACTIVOS: son los unicos que la busqueda
        # por defecto recorre. Los reservados (mem_knowledge, mem_tool...) no
        # se ofrecen aqui a proposito -- ver nota junto a _ACTIVE_VALUES.
        types = ", ".join(sorted(_ACTIVE_VALUES))
        return [
            {
                "id": "search_memory",
                "description": "Busqueda semantica en la memoria del MOS.",
                "requires_confirmation": False,
                "params": {
                    "query": "string",
                    "memory_types": f"lista opcional de: {types} (default: todos)",
                    "top_k": "int opcional (default 5)",
                },
            },
            {
                "id": "save_memory",
                "description": "Guarda un hecho nuevo en la memoria. Con dedup_key, sobreescribe si ya existia.",
                "requires_confirmation": False,
                "params": {
                    "content": "string",
                    "memory_type": f"string, uno de: {types}",
                    "source": "string (ej. 'agent', 'chat', 'user')",
                    "metadata": "dict opcional",
                    "dedup_key": "string opcional (mismo key = actualiza en vez de duplicar)",
                },
            },
            {
                "id": "update_memory",
                "description": "Actualiza el contenido de un item existente (por su id).",
                "requires_confirmation": False,
                "params": {"item_id": "string (id devuelto por search/save)", "content": "string"},
            },
            {
                "id": "delete_memory",
                "description": "Elimina items que coincidan con un filtro de metadata.",
                "requires_confirmation": True,
                "params": {
                    "memory_type": f"string, uno de: {types}",
                    "filters": "dict (filtro de metadata ChromaDB, ej. {'source': 'agent'})",
                },
            },
        ]

    # ------------------------------------------------------------------

    async def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = params.get("query", "")
        if not query:
            return {"success": False, "result": None, "error": "falta parametro: query"}
        types_raw = params.get("memory_types")
        types = None
        if types_raw:
            types = [t for t in (_parse_memory_type(v) for v in types_raw) if t]
        top_k = int(params.get("top_k", 5))

        items = await memory_router.search(query, memory_types=types, top_k=top_k)
        return {
            "success": True,
            "result": {
                "items": [
                    {"id": it.id, "content": it.content, "memory_type": it.memory_type.value,
                     "source": it.source, "score": it.score, "metadata": it.metadata}
                    for it in items
                ],
                "count": len(items),
            },
            "error": None,
        }

    async def _save(self, params: Dict[str, Any]) -> Dict[str, Any]:
        content = params.get("content", "")
        if not content:
            return {"success": False, "result": None, "error": "falta parametro: content"}
        mt = _parse_memory_type(params.get("memory_type", ""))
        if mt is None:
            return {"success": False, "result": None, "error": f"memory_type invalido: {params.get('memory_type')!r}"}
        source = params.get("source") or "agent"

        item_id = await memory_router.store(
            content, mt, source,
            metadata=params.get("metadata"), dedup_key=params.get("dedup_key"),
        )
        if not item_id:
            return {"success": False, "result": None, "error": "no se pudo guardar (memoria no disponible)"}
        return {"success": True, "result": {"id": item_id}, "error": None}

    async def _update(self, params: Dict[str, Any]) -> Dict[str, Any]:
        item_id = params.get("item_id", "")
        content = params.get("content", "")
        if not item_id or not content:
            return {"success": False, "result": None, "error": "faltan parametros: item_id y content"}

        existing = await memory_router.retrieve(item_id)
        if existing is None:
            return {"success": False, "result": None, "error": f"no existe el item: {item_id}"}

        if ":" not in item_id:
            return {"success": False, "result": None, "error": f"id con formato inesperado: {item_id}"}
        dedup_key = item_id.split(":", 1)[1]

        new_id = await memory_router.store(
            content, existing.memory_type, existing.source,
            metadata=existing.metadata, dedup_key=dedup_key,
        )
        return {"success": True, "result": {"id": new_id, "updated": True}, "error": None}

    async def _delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        mt = _parse_memory_type(params.get("memory_type", ""))
        if mt is None:
            return {"success": False, "result": None, "error": f"memory_type invalido: {params.get('memory_type')!r}"}
        filters = params.get("filters") or {}

        count = await memory_router.forget(mt, filters)
        return {"success": True, "result": {"deleted_count": count}, "error": None}
