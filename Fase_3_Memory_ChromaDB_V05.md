# FASE 3 — V0.6: Memory System + Contexto en Chat
## Documento de implementación para Claude Code
**Versión objetivo**: Aithera V0.6.0
**Prerrequisito**: Aithera V0.5.0 completada (AgentManager + ExecutionEngine funcionando)
**Sesiones**: 2

---

## CONTEXTO

Aithera "recuerda". ChromaDB corre en local, en el mismo proceso que FastAPI. La primera vez que arranca después de esta fase, descarga el modelo de embeddings (~80MB, 1-2 minutos). Eso es normal.

---

## SESIÓN 1: ChromaDB + MemoryManager

**Tiempo estimado**: 2-3 horas
**Empieza con**: Aithera V0.5.0 funcionando

### Paso 1 — Instalar dependencias

```bash
cd backend
pip install chromadb==1.5.9 sentence-transformers==3.3.1 --break-system-packages
```

Añadir a `backend/requirements.txt`:
```
chromadb==1.5.9
sentence-transformers==3.3.1
```

**Nota**: `sentence-transformers` instala PyTorch CPU. Total de dependencias nuevas: ~1.5GB. Es normal.

### Paso 2 — Crear `backend/app/memory/memory_manager.py`

```python
"""
MemoryManager — Sistema de memoria semántica de Aithera.
ChromaDB persiste en: %APPDATA%/Aithera/chroma/

Tres colecciones:
- 'conversations': historial de chat indexado semánticamente
- 'user_context': preferencias, decisiones, hechos del usuario
- 'documents': documentos indexados para búsqueda
"""
import os
from typing import List, Optional, Dict
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = os.path.join(os.environ.get('APPDATA') or '.', 'Aithera', 'chroma')
os.makedirs(CHROMA_PATH, exist_ok=True)


class MemoryManager:
    def __init__(self):
        self._client = chromadb.PersistentClient(path=CHROMA_PATH)
        self._ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self._conversations = self._client.get_or_create_collection("conversations", embedding_function=self._ef)
        self._user_context = self._client.get_or_create_collection("user_context", embedding_function=self._ef)
        self._documents = self._client.get_or_create_collection("documents", embedding_function=self._ef)

    def store_conversation(self, role: str, content: str, metadata: Optional[Dict] = None) -> str:
        doc_id = f"conv_{datetime.utcnow().timestamp()}"
        meta = {"role": role, "timestamp": datetime.utcnow().isoformat(), **(metadata or {})}
        self._conversations.add(documents=[content], ids=[doc_id], metadatas=[meta])
        return doc_id

    def search_conversations(self, query: str, n_results: int = 5) -> List[Dict]:
        count = self._conversations.count()
        if count == 0:
            return []
        results = self._conversations.query(query_texts=[query], n_results=min(n_results, count))
        return [
            {"content": doc, "role": meta.get("role"), "timestamp": meta.get("timestamp"), "distance": dist}
            for doc, meta, dist in zip(results['documents'][0], results['metadatas'][0], results['distances'][0])
        ]

    def store_user_context(self, key: str, content: str, category: str = "preference") -> str:
        doc_id = f"ctx_{key}"
        meta = {"key": key, "category": category, "updated_at": datetime.utcnow().isoformat()}
        try:
            self._user_context.update(documents=[content], ids=[doc_id], metadatas=[meta])
        except Exception:
            self._user_context.add(documents=[content], ids=[doc_id], metadatas=[meta])
        return doc_id

    def search_user_context(self, query: str, n_results: int = 3) -> List[Dict]:
        count = self._user_context.count()
        if count == 0:
            return []
        results = self._user_context.query(query_texts=[query], n_results=min(n_results, count))
        return [
            {"content": doc, "key": meta.get("key"), "category": meta.get("category")}
            for doc, meta in zip(results['documents'][0], results['metadatas'][0])
        ]

    def index_document(self, doc_id: str, content: str, title: str, path: Optional[str] = None) -> str:
        meta = {"title": title, "indexed_at": datetime.utcnow().isoformat()}
        if path:
            meta["path"] = path
        try:
            self._documents.update(documents=[content], ids=[doc_id], metadatas=[meta])
        except Exception:
            self._documents.add(documents=[content], ids=[doc_id], metadatas=[meta])
        return doc_id

    def search_documents(self, query: str, n_results: int = 5) -> List[Dict]:
        count = self._documents.count()
        if count == 0:
            return []
        results = self._documents.query(query_texts=[query], n_results=min(n_results, count))
        return [
            {"content": doc[:500], "title": meta.get("title"), "path": meta.get("path")}
            for doc, meta in zip(results['documents'][0], results['metadatas'][0])
        ]

    def build_context_for_chat(self, user_message: str) -> str:
        """Construye el bloque de contexto para inyectar en el system prompt del chat."""
        ctx_items = self.search_user_context(user_message, n_results=3)
        conv_items = self.search_conversations(user_message, n_results=2)
        parts = []
        if ctx_items:
            parts.append("Contexto del usuario:")
            for item in ctx_items:
                parts.append(f"- {item['content']}")
        if conv_items:
            parts.append("\nConversaciones relevantes anteriores:")
            for item in conv_items:
                parts.append(f"- [{item['role']}]: {item['content'][:200]}")
        return "\n".join(parts) if parts else ""

    def get_stats(self) -> Dict:
        return {
            "conversations": self._conversations.count(),
            "user_context": self._user_context.count(),
            "documents": self._documents.count(),
        }


# Singleton global — se inicializa al importar (descarga modelo si es la primera vez)
memory_manager = MemoryManager()
```

### Paso 3 — Log informativo en startup

`backend/app/main.py` — en el lifespan:
```python
from app.memory.memory_manager import memory_manager
log_info("startup", f"Memory system listo — {memory_manager.get_stats()}")
```

### ✅ Checkpoint Sesión 1 — verificar antes de parar

- [ ] `pip install chromadb sentence-transformers` completado (puede tardar varios minutos)
- [ ] El backend arranca sin errores (la primera vez descarga el modelo de embeddings)
- [ ] El directorio `%APPDATA%/Aithera/chroma/` existe después del arranque
- [ ] `memory_manager.store_conversation("user", "test")` no lanza excepciones
- [ ] `memory_manager.search_conversations("test")` devuelve la entrada guardada

### 🛑 Para aquí

Commit: `feat: MemoryManager + ChromaDB inicializado`. La Sesión 2 conecta la memoria al chat.

---

## SESIÓN 2: Integración en chat + endpoints + UI

**Tiempo estimado**: 2-3 horas
**Empieza con**: MemoryManager funcionando

### Paso 1 — Integrar en el chat

Modificar `backend/app/api/endpoints/chat.py`:

```python
from app.memory.memory_manager import memory_manager

@router.post("/stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    message = request.message

    # 1. Construir contexto desde la memoria
    context_block = memory_manager.build_context_for_chat(message)

    # 2. System prompt base de Aithera
    base_system = "Eres Aithera, un sistema operativo personal de IA. Conoces los proyectos, tareas, calendario y preferencias del usuario. Responde siempre en el idioma del usuario."
    system_prompt = f"{base_system}\n\n{context_block}" if context_block else base_system

    # 3. Almacenar mensaje del usuario
    memory_manager.store_conversation("user", message)

    # 4. Streaming con acumulación (patrón useRef existente en el backend)
    accumulated = []

    async def generate():
        async for chunk in ai_manager.chat_stream(message, system_prompt):
            accumulated.append(chunk)
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
        # 5. Almacenar respuesta completa
        full_response = "".join(accumulated)
        if full_response:
            memory_manager.store_conversation("assistant", full_response)

    return StreamingResponse(generate(), media_type="text/event-stream")
```

### Paso 2 — Crear `backend/app/api/endpoints/memory.py`

```
GET /api/memory/stats
    Response: { "conversations": 142, "user_context": 15, "documents": 8 }

POST /api/memory/context
    Body: { "key": "meeting_preference", "content": "Prefiero reuniones por la tarde", "category": "preference" }
    Response: { "id": "ctx_meeting_preference", "stored": true }

GET /api/memory/context/search?q=reuniones
    Response: [{ "content": "...", "key": "...", "category": "..." }]

POST /api/memory/documents/index
    Body: { "title": "Informe Q1", "content": "...", "path": "C:/..." }
    Response: { "id": "...", "indexed": true }

DELETE /api/memory/conversations
    Response: { "cleared": true, "count_before": 142 }
```

Registrar en `backend/app/main.py`:
```python
from app.api.endpoints import memory as memory_router
app.include_router(memory_router.router, prefix="/api")
```

### Paso 3 — Sección Memoria en Settings

`frontend/src/pages/Settings.tsx` — añadir sección "Memoria":
- Estadísticas: "X conversaciones, Y preferencias, Z documentos indexados"
- Botón "Borrar historial de conversaciones" (con diálogo de confirmación)
- Formulario añadir preferencia: campo key + campo contenido + botón guardar
- Lista de preferencias guardadas

### Bump de versión

- `backend/app/main.py`: `version="0.6.0"`
- `backend/app/core/config.py`: `VERSION = "0.6.0"`
- `frontend/package.json`: `"version": "0.6.0"`

### ✅ Checkpoint Sesión 2 — verificar antes de parar

- [ ] Al enviar un mensaje en el chat, la conversación se almacena en ChromaDB
- [ ] Al enviar un segundo mensaje relacionado, el contexto del primero aparece en el system prompt (verificar en logs del backend)
- [ ] `GET /api/memory/stats` devuelve estadísticas correctas
- [ ] `POST /api/memory/context` guarda una preferencia y es recuperable con `/search`
- [ ] La preferencia aparece en el contexto del chat cuando es relevante
- [ ] El botón "Borrar historial" en Settings limpia las conversaciones de ChromaDB
- [ ] `GET /` devuelve `"version": "0.6.0"`

### 🛑 Para aquí

Aithera V0.6.0 completada. Commit: `feat: V0.6.0 — Memory System (ChromaDB) + contexto en chat`.

**Siguiente fase**: `Fase_4_Email_Calendar_V06.md`

---

## ARCHIVOS CREADOS/MODIFICADOS EN ESTA FASE

**Sesión 1**: `backend/app/memory/__init__.py`, `backend/app/memory/memory_manager.py`, `backend/requirements.txt`, `backend/app/main.py` (import + log startup)

**Sesión 2**: `backend/app/api/endpoints/chat.py` (integración memoria), `backend/app/api/endpoints/memory.py` (nuevo), `backend/app/main.py` (registrar router memory, bump v0.6.0), `frontend/src/pages/Settings.tsx` (sección Memoria), `frontend/package.json`
