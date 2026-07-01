# /api/memory - Endpoints del sistema de memoria semantica (V0.6 Fase 3)
#
# Endpoints:
#   GET    /api/memory/stats              -> stats de las 3 colecciones
#   POST   /api/memory/context            -> guarda/actualiza una preferencia
#   GET    /api/memory/context/list       -> lista todas las preferencias
#   GET    /api/memory/context/search?q=  -> busca preferencias relevantes
#   DELETE /api/memory/context/{key}      -> elimina una preferencia
#   POST   /api/memory/documents          -> indexa un documento
#   GET    /api/memory/documents/search?q=-> busca documentos relevantes
#   POST   /api/memory/conversations/clear -> borra el historial de conversaciones
#
# NOTA: si ChromaDB no esta disponible, todos los endpoints devuelven 503
# (excepto /stats que devuelve el error en el cuerpo).

from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.memory.memory_manager import memory_manager

router = APIRouter(prefix="/memory", tags=["memory"])


def _check_healthy():
    """Helper: lanza 503 si la memoria no esta disponible."""
    if not memory_manager.is_healthy():
        raise HTTPException(
            status_code=503,
            detail=f"Memory system no disponible: {memory_manager.get_init_error() or 'unknown'}",
        )


# ----------------------------------------------------------------------
# Stats
# ----------------------------------------------------------------------

@router.get("/stats")
def get_stats():
    """Devuelve las estadisticas de las 3 colecciones de ChromaDB."""
    return memory_manager.get_stats()


# ----------------------------------------------------------------------
# user_context (preferencias, decisiones)
# ----------------------------------------------------------------------

class ContextItem(BaseModel):
    key: str
    content: str
    category: str = "preference"


@router.post("/context", status_code=201)
def store_context(item: ContextItem):
    """Guarda o actualiza una preferencia del usuario."""
    _check_healthy()
    if not item.key.strip() or not item.content.strip():
        raise HTTPException(status_code=400, detail="key y content son obligatorios")
    doc_id = memory_manager.store_user_context(
        key=item.key.strip(),
        content=item.content.strip(),
        category=item.category.strip() or "preference",
    )
    if not doc_id:
        raise HTTPException(status_code=500, detail="No se pudo guardar la preferencia")
    return {"id": doc_id, "stored": True, "key": item.key.strip()}


@router.get("/context/list")
def list_context():
    """Lista todas las preferencias guardadas (para la UI de Settings)."""
    _check_healthy()
    items = memory_manager.list_user_context()
    return {"items": items, "count": len(items)}


@router.get("/context/search")
def search_context(q: str = Query(..., min_length=1), n_results: int = Query(3, ge=1, le=20)):
    """Busca preferencias relevantes para una query (semantica)."""
    _check_healthy()
    results = memory_manager.search_user_context(q, n_results=n_results)
    return {"items": results, "count": len(results)}


@router.delete("/context/{key}", status_code=204)
def delete_context(key: str):
    """Elimina una preferencia por su key."""
    _check_healthy()
    ok = memory_manager.delete_user_context(key)
    if not ok:
        raise HTTPException(status_code=404, detail=f"preferencia no encontrada: {key}")
    return None


# ----------------------------------------------------------------------
# documents (documentos indexados)
# ----------------------------------------------------------------------

class DocumentItem(BaseModel):
    id: str
    title: str
    content: str
    path: Optional[str] = None


@router.post("/documents", status_code=201)
def index_document(item: DocumentItem):
    """Indexa un documento para busqueda semantica."""
    _check_healthy()
    if not item.id.strip() or not item.content.strip():
        raise HTTPException(status_code=400, detail="id y content son obligatorios")
    doc_id = memory_manager.index_document(
        doc_id=item.id.strip(),
        content=item.content.strip(),
        title=item.title.strip() or item.id.strip(),
        path=item.path,
    )
    if not doc_id:
        raise HTTPException(status_code=500, detail="No se pudo indexar el documento")
    return {"id": doc_id, "indexed": True}


@router.get("/documents/search")
def search_documents(q: str = Query(..., min_length=1), n_results: int = Query(5, ge=1, le=20)):
    """Busca documentos relevantes para una query (semantica)."""
    _check_healthy()
    results = memory_manager.search_documents(q, n_results=n_results)
    return {"items": results, "count": len(results)}


# ----------------------------------------------------------------------
# conversations
# ----------------------------------------------------------------------

@router.post("/conversations/clear")
def clear_conversations():
    """Borra todo el historial de conversaciones de ChromaDB."""
    _check_healthy()
    count_before = memory_manager.clear_conversations()
    return {"cleared": True, "count_before": count_before}


# ----------------------------------------------------------------------
# Test / health del modulo
# ----------------------------------------------------------------------

@router.get("/health")
def memory_health():
    """Diagnostico del sistema de memoria."""
    return {
        "healthy": memory_manager.is_healthy(),
        "init_error": memory_manager.get_init_error(),
        "stats": memory_manager.get_stats(),
    }