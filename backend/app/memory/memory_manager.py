"""
MemoryManager - Sistema de memoria semantica de Aithera (V0.6 Fase 3).

ChromaDB persiste en: %APPDATA%/Aithera/chroma/

Tres colecciones:
- 'conversations': historial de chat indexado semanticamente
- 'user_context': preferencias, decisiones, hechos del usuario
- 'documents': documentos indexados para busqueda

Embeddings: sentence-transformers con modelo 'all-MiniLM-L6-v2' (~80MB).
La primera vez que arranca, ChromaDB descarga el modelo (1-2 minutos).

DISENO:
- MemoryManager es un singleton: un solo cliente ChromaDB por proceso.
- Las colecciones se crean idempotentemente (get_or_create_collection).
- Si ChromaDB o sentence-transformers fallan al cargar, el sistema degrada
  gracefully: build_context_for_chat() devuelve "" y los endpoints de
  memoria devuelven error 503. Asi el chat sigue funcionando aunque
  la memoria este caida.
"""
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

# ChromaDB y sentence-transformers se importan lazy dentro del constructor
# para que un fallo en estos paquetes NO impida importar el modulo.

CHROMA_PATH = os.path.join(os.environ.get("APPDATA") or ".", "Aithera", "chroma")
os.makedirs(CHROMA_PATH, exist_ok=True)


class MemoryManager:
    """Gestiona las 3 colecciones de ChromaDB para Aithera."""

    def __init__(self):
        # Inicializacion lazy: si falla, marcamos _healthy=False y los
        # metodos devuelven resultados vacios sin lanzar excepciones.
        self._healthy = False
        self._client = None
        self._ef = None
        self._conversations = None
        self._user_context = None
        self._documents = None
        self._init_error: Optional[str] = None
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            self._client = chromadb.PersistentClient(path=CHROMA_PATH)
            self._ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            self._conversations = self._client.get_or_create_collection(
                "conversations", embedding_function=self._ef
            )
            self._user_context = self._client.get_or_create_collection(
                "user_context", embedding_function=self._ef
            )
            self._documents = self._client.get_or_create_collection(
                "documents", embedding_function=self._ef
            )
            self._healthy = True
        except Exception as e:
            # No relanzamos: degradamos gracefully.
            self._init_error = f"{type(e).__name__}: {e}"
            print(f"[MemoryManager] Inicializacion fallida: {self._init_error}")

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------

    def is_healthy(self) -> bool:
        return self._healthy

    def get_init_error(self) -> Optional[str]:
        return self._init_error

    def get_stats(self) -> Dict[str, Any]:
        if not self._healthy:
            return {
                "healthy": False,
                "error": self._init_error,
                "conversations": 0,
                "user_context": 0,
                "documents": 0,
            }
        try:
            return {
                "healthy": True,
                "chroma_path": CHROMA_PATH,
                "conversations": self._conversations.count(),
                "user_context": self._user_context.count(),
                "documents": self._documents.count(),
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": f"error leyendo stats: {type(e).__name__}: {e}",
                "conversations": 0,
                "user_context": 0,
                "documents": 0,
            }

    # ------------------------------------------------------------------
    # conversations
    # ------------------------------------------------------------------

    def store_conversation(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Guarda un mensaje de conversacion (user o assistant)."""
        if not self._healthy or not content:
            return None
        try:
            doc_id = f"conv_{datetime.utcnow().timestamp()}_{role}"
            meta = {
                "role": role,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {}),
            }
            self._conversations.add(
                documents=[content], ids=[doc_id], metadatas=[meta]
            )
            return doc_id
        except Exception as e:
            print(f"[MemoryManager] store_conversation error: {e}")
            return None

    def search_conversations(
        self, query: str, n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Busca conversaciones relevantes para una query."""
        if not self._healthy or not query:
            return []
        try:
            count = self._conversations.count()
            if count == 0:
                return []
            results = self._conversations.query(
                query_texts=[query], n_results=min(n_results, count)
            )
            docs = results.get("documents", [[]])[0] if results.get("documents") else []
            metas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
            dists = results.get("distances", [[]])[0] if results.get("distances") else []
            return [
                {
                    "content": doc,
                    "role": meta.get("role") if meta else None,
                    "timestamp": meta.get("timestamp") if meta else None,
                    "distance": dist,
                }
                for doc, meta, dist in zip(docs, metas, dists)
            ]
        except Exception as e:
            print(f"[MemoryManager] search_conversations error: {e}")
            return []

    # ------------------------------------------------------------------
    # user_context (preferencias, decisiones)
    # ------------------------------------------------------------------

    def store_user_context(
        self, key: str, content: str, category: str = "preference"
    ) -> Optional[str]:
        """Guarda o actualiza una preferencia/hecho del usuario."""
        if not self._healthy or not key or not content:
            return None
        try:
            doc_id = f"ctx_{key}"
            meta = {
                "key": key,
                "category": category,
                "updated_at": datetime.utcnow().isoformat(),
            }
            # Comprobamos primero si el ID ya existe. ChromaDB's `update` sobre
            # un ID inexistente es un no-op silencioso (no lanza), asi que el
            # patron try/except de antes nunca llegaba al `add`.
            try:
                existing = self._user_context.get(ids=[doc_id])
                if existing and existing.get("ids"):
                    self._user_context.update(
                        documents=[content], ids=[doc_id], metadatas=[meta]
                    )
                else:
                    self._user_context.add(
                        documents=[content], ids=[doc_id], metadatas=[meta]
                    )
            except Exception:
                # Si get() falla, intentamos add como fallback.
                self._user_context.add(
                    documents=[content], ids=[doc_id], metadatas=[meta]
                )
            return doc_id
        except Exception as e:
            print(f"[MemoryManager] store_user_context error: {e}")
            return None

    def search_user_context(
        self, query: str, n_results: int = 3
    ) -> List[Dict[str, Any]]:
        """Busca preferencias/hechos relevantes para una query."""
        if not self._healthy or not query:
            return []
        try:
            count = self._user_context.count()
            if count == 0:
                return []
            results = self._user_context.query(
                query_texts=[query], n_results=min(n_results, count)
            )
            docs = results.get("documents", [[]])[0] if results.get("documents") else []
            metas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
            return [
                {
                    "content": doc,
                    "key": meta.get("key") if meta else None,
                    "category": meta.get("category") if meta else None,
                }
                for doc, meta in zip(docs, metas)
            ]
        except Exception as e:
            print(f"[MemoryManager] search_user_context error: {e}")
            return []

    def list_user_context(self) -> List[Dict[str, Any]]:
        """Lista todas las preferencias almacenadas (para la UI)."""
        if not self._healthy:
            return []
        try:
            results = self._user_context.get()
            ids = results.get("ids", [])
            docs = results.get("documents", [])
            metas = results.get("metadatas", [])
            return [
                {
                    "id": doc_id,
                    "key": meta.get("key"),
                    "content": doc,
                    "category": meta.get("category"),
                    "updated_at": meta.get("updated_at"),
                }
                for doc_id, doc, meta in zip(ids, docs, metas)
            ]
        except Exception as e:
            print(f"[MemoryManager] list_user_context error: {e}")
            return []

    def delete_user_context(self, key: str) -> bool:
        """Elimina una preferencia por su key."""
        if not self._healthy or not key:
            return False
        try:
            self._user_context.delete(ids=[f"ctx_{key}"])
            return True
        except Exception as e:
            print(f"[MemoryManager] delete_user_context error: {e}")
            return False

    # ------------------------------------------------------------------
    # documents (documentos indexados)
    # ------------------------------------------------------------------

    def index_document(
        self,
        doc_id: str,
        content: str,
        title: str,
        path: Optional[str] = None,
    ) -> Optional[str]:
        """Indexa un documento para busqueda semantica."""
        if not self._healthy or not doc_id or not content:
            return None
        try:
            meta = {
                "title": title,
                "indexed_at": datetime.utcnow().isoformat(),
            }
            if path:
                meta["path"] = path
            try:
                existing = self._documents.get(ids=[doc_id])
                if existing and existing.get("ids"):
                    self._documents.update(
                        documents=[content], ids=[doc_id], metadatas=[meta]
                    )
                else:
                    self._documents.add(
                        documents=[content], ids=[doc_id], metadatas=[meta]
                    )
            except Exception:
                self._documents.add(
                    documents=[content], ids=[doc_id], metadatas=[meta]
                )
            return doc_id
        except Exception as e:
            print(f"[MemoryManager] index_document error: {e}")
            return None

    def search_documents(
        self, query: str, n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Busca documentos relevantes para una query."""
        if not self._healthy or not query:
            return []
        try:
            count = self._documents.count()
            if count == 0:
                return []
            results = self._documents.query(
                query_texts=[query], n_results=min(n_results, count)
            )
            docs = results.get("documents", [[]])[0] if results.get("documents") else []
            metas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
            return [
                {
                    "content": doc[:500],  # truncamos para no saturar el contexto
                    "title": meta.get("title") if meta else None,
                    "path": meta.get("path") if meta else None,
                }
                for doc, meta in zip(docs, metas)
            ]
        except Exception as e:
            print(f"[MemoryManager] search_documents error: {e}")
            return []

    # ------------------------------------------------------------------
    # Construccion del bloque de contexto para chat
    # ------------------------------------------------------------------

    def build_context_for_chat(self, user_message: str) -> str:
        """Construye el bloque de contexto para inyectar en el system prompt.

        Combina:
        - Preferencias/hechos del usuario (3 mas relevantes)
        - Conversaciones anteriores relevantes (2 mas relevantes)

        Devuelve string vacio si no hay nada relevante o si la memoria
        no esta disponible.
        """
        if not self._healthy or not user_message:
            return ""
        try:
            ctx_items = self.search_user_context(user_message, n_results=3)
            conv_items = self.search_conversations(user_message, n_results=2)
            parts = []
            if ctx_items:
                parts.append("Contexto del usuario (preferencias y hechos relevantes):")
                for item in ctx_items:
                    parts.append(f"- {item['content']}")
            if conv_items:
                parts.append("\nConversaciones anteriores relevantes:")
                for item in conv_items:
                    preview = item["content"][:200] if item.get("content") else ""
                    parts.append(f"- [{item['role']}]: {preview}")
            return "\n".join(parts) if parts else ""
        except Exception as e:
            print(f"[MemoryManager] build_context_for_chat error: {e}")
            return ""

    # ------------------------------------------------------------------
    # Operaciones masivas
    # ------------------------------------------------------------------

    def clear_conversations(self) -> int:
        """Borra todo el historial de conversaciones. Devuelve count_before."""
        if not self._healthy:
            return 0
        try:
            count_before = self._conversations.count()
            # ChromaDB no tiene TRUNCATE; usamos delete con todos los ids.
            if count_before > 0:
                results = self._conversations.get()
                ids = results.get("ids", [])
                if ids:
                    self._conversations.delete(ids=ids)
            return count_before
        except Exception as e:
            print(f"[MemoryManager] clear_conversations error: {e}")
            return 0


# Singleton global - se inicializa al importar.
# El constructor es lazy y degrada gracefully si chromadb/sentence-transformers
# fallan, asi que importar este modulo NUNCA rompe el backend.
memory_manager = MemoryManager()