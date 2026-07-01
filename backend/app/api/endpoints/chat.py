# Chat API Endpoints
# V0.6 (Fase 3 Memory System): integracion de ChromaDB como memoria semantica.
# Cada mensaje del chat se almacena automaticamente y el contexto recuperado
# se inyecta en el system prompt de las siguientes interacciones.
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.ai_manager import ai_manager
from app.db.database import get_db, SessionLocal
from app.db.models import ChatMessage
from app.db.schemas import ChatRequest, ChatResponse
from app.memory.memory_manager import memory_manager

router = APIRouter(prefix="/chat", tags=["Chat"])


# FIX V0.6: prompt base actualizado para reflejar el proposito del sistema.
# El bloque de contexto semantico (preferencias del usuario + conversaciones
# relevantes) se concatena en runtime desde memory_manager.build_context_for_chat().
DEFAULT_SYSTEM_PROMPT = """Eres Aithera, un sistema operativo personal de IA.

Conoces los proyectos, tareas, calendario y preferencias del usuario.
Responde siempre en el idioma del usuario. Se conciso y util."""


def _build_system_prompt(user_message: str) -> str:
    """V0.6: enriquece el system prompt base con el contexto de la memoria.

    Si ChromaDB no esta disponible o no hay coincidencias, devuelve solo el
    prompt base (sin romper el chat).
    """
    base = DEFAULT_SYSTEM_PROMPT
    if not memory_manager.is_healthy() or not user_message:
        return base
    try:
        ctx = memory_manager.build_context_for_chat(user_message)
    except Exception as e:
        print(f"[chat] build_context_for_chat error: {e}")
        ctx = ""
    if ctx:
        return f"{base}\n\n{ctx}"
    return base


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Send a chat message and get a complete (non-streaming) response."""
    # V0.6: el system prompt se construye con el contexto de la memoria.
    system_prompt = _build_system_prompt(request.message)

    # V0.6: almacenamos el mensaje del usuario ANTES de la respuesta, para
    # que si la IA falla al responder, el mensaje siga indexado.
    memory_manager.store_conversation("user", request.message)

    result = await ai_manager.chat(
        message=request.message,
        system_prompt=system_prompt,
    )

    response_text = result.get("response", "")
    # V0.6: almacenamos la respuesta del asistente (si no esta vacia).
    if response_text:
        memory_manager.store_conversation("assistant", response_text)

    # Mantenemos el guardado tradicional en ChatMessage (historial de UI).
    user_msg = ChatMessage(
        role="user",
        content=request.message,
        model_used=result.get("model"),
    )
    db.add(user_msg)

    assistant_msg = ChatMessage(
        role="assistant",
        content=response_text,
        model_used=result.get("model"),
        tokens_used=result.get("tokens"),
    )
    db.add(assistant_msg)

    db.commit()

    return ChatResponse(
        response=response_text or "No response",
        model=result.get("model"),
        tokens=result.get("tokens"),
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Send a chat message and stream the AI response as Server-Sent Events.

    V0.6: igual que chat() pero en modo streaming. La gestion del DB session
    se hace en `finally` (mismo patron que en V0.2 para evitar que FastAPI
    cierre la sesion antes de que termine el stream).
    """
    system_prompt = _build_system_prompt(request.message)

    # Almacenamos el user message al principio para que quede indexado
    # aunque la IA falle o el cliente cancele el stream.
    memory_manager.store_conversation("user", request.message)

    async def event_generator():
        full_response = ""
        model_used = ai_manager.current_provider_name
        try:
            async for chunk in ai_manager.chat_stream(request.message, system_prompt):
                full_response += chunk
                safe_chunk = chunk.replace("\r", "").replace("\n", "\\n")
                yield f"data: {safe_chunk}\n\n"
        finally:
            # V0.6: almacenamos la respuesta del asistente.
            if full_response:
                memory_manager.store_conversation(
                    "assistant", full_response, metadata={"model": model_used or "unknown"}
                )
            db = SessionLocal()
            try:
                db.add(ChatMessage(role="user", content=request.message, model_used=model_used))
                db.add(ChatMessage(role="assistant", content=full_response, model_used=model_used))
                db.commit()
            finally:
                db.close()
            yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history")
async def get_chat_history(limit: int = 50, db: Session = Depends(get_db)):
    """Get chat history (UI)."""
    messages = db.query(ChatMessage).order_by(
        ChatMessage.created_at.desc()
    ).limit(limit).all()

    # Reverse to show oldest first
    messages = list(reversed(messages))

    return [
        {
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        }
        for msg in messages
    ]


@router.delete("/history")
async def clear_chat_history(db: Session = Depends(get_db)):
    """Clear all chat history (UI)."""
    db.query(ChatMessage).delete()
    db.commit()
    return {"message": "Chat history cleared"}