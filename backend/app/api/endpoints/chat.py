# Chat API Endpoints
# V0.6 (Fase 3 Memory System): integracion de ChromaDB como memoria semantica.
# Cada mensaje del chat se almacena automaticamente y el contexto recuperado
# se inyecta en el system prompt de las siguientes interacciones.
# V0.85 (MOS M4): el pipeline (system prompt + memoria + IA + strip_reasoning)
# vive ahora en app/services/chat_service.py — lo comparte con el Gateway
# (doc 12 A4: antes duplicaban esta logica casi entera).
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.ai_manager import ai_manager
from app.core.config import settings
from app.db.database import get_db, SessionLocal
from app.db.models import ChatMessage
from app.db.schemas import ChatRequest, ChatResponse
from app.memory.memory_manager import memory_manager
# B21 (2026-07-02): separar la cadena de pensamiento de los modelos
# razonadores (MiniMax <think>) de la respuesta que ve el usuario.
from app.ai.reasoning_filter import StreamingReasoningFilter
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a chat message and get a complete (non-streaming) response.

    [V0.85 M4] Delega en chat_service.answer() — mismo pipeline que usa el
    Gateway (Telegram, etc.), con memoria del MOS y atribucion de fuente.
    """
    result = await chat_service.answer(request.message, channel="web")
    return ChatResponse(
        response=result.text or "No response",
        model=result.model,
        tokens=result.tokens,
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Send a chat message and stream the AI response as Server-Sent Events.

    V0.6: igual que chat() pero en modo streaming. La gestion del DB session
    se hace en `finally` (mismo patron que en V0.2 para evitar que FastAPI
    cierre la sesion antes de que termine el stream).

    [V0.85 M4] El system prompt usa chat_service.build_system_prompt(): misma
    memoria del MOS con atribucion de fuente que el chat no-streaming. No se
    delega en chat_service.answer() completo porque el streaming necesita ir
    emitiendo chunks mientras la IA genera, algo que answer() (no streaming)
    no puede hacer — pero comparte la MISMA construccion de contexto.
    """
    system_prompt = await chat_service.build_system_prompt(request.message)

    # Almacenamos el user message al principio para que quede indexado
    # aunque la IA falle o el cliente cancele el stream.
    memory_manager.store_conversation("user", request.message, metadata={"channel": "web"})

    async def event_generator():
        full_response = ""
        model_used = ai_manager.current_provider_name
        # B21: filtro incremental — el bloque <think> inicial se retiene y
        # NO se emite; el historial y la memoria guardan la respuesta limpia.
        reasoning_filter = StreamingReasoningFilter()
        try:
            if settings.TIE_ENABLED:
                # [V1.0 T4b] El chat de Electron pasa por el TIE: entiende antes de
                # responder. El camino corto (~80%) streamea tokens igual que
                # siempre — el TIE ya aplica el filtro B21 dentro del runtime, así
                # que aquí NO se vuelve a filtrar. El complejo emite estados
                # ("analizando", "planificando") y luego la respuesta.
                import app.tie as tie

                async for kind, payload in tie.handle_stream(request.message, channel="web"):
                    if not payload:
                        continue
                    safe = str(payload).replace("\r", "").replace("\n", "\\n")
                    if kind == "text":
                        full_response += str(payload)
                        yield f"data: {safe}\n\n"
                    else:
                        # "status" | "mission": eventos SSE tipados. El cliente los
                        # distingue por el `event:` (api.streamChat) y NUNCA los
                        # mete en el texto de la respuesta.
                        yield f"event: {kind}\ndata: {safe}\n\n"
            else:
                async for chunk in ai_manager.chat_stream(request.message, system_prompt):
                    visible = reasoning_filter.feed(chunk)
                    if not visible:
                        continue
                    full_response += visible
                    safe_chunk = visible.replace("\r", "").replace("\n", "\\n")
                    yield f"data: {safe_chunk}\n\n"
                tail = reasoning_filter.flush()
                if tail:
                    full_response += tail
                    safe_tail = tail.replace("\r", "").replace("\n", "\\n")
                    yield f"data: {safe_tail}\n\n"
        finally:
            # V0.6: almacenamos la respuesta del asistente.
            if full_response:
                memory_manager.store_conversation(
                    "assistant", full_response,
                    metadata={"model": model_used or "unknown", "channel": "web"},
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