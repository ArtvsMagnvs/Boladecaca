# Chat API Endpoints
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.ai_manager import ai_manager
from app.db.database import get_db, SessionLocal
from app.db.models import ChatMessage
from app.db.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Chat"])


DEFAULT_SYSTEM_PROMPT = """Eres Aithera, un asistente de IA personal avanzado.

Puedes ayudar con:
- Gestión de proyectos y tareas
- Programación y desarrollo de software
- Análisis y resolución de problemas
- Investigación y aprendizaje
- Planificación y estrategia

Siempre sé helpful, claro y conciso en tus respuestas."""


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Send a chat message and get a complete (non-streaming) response."""
    # Get AI response
    result = await ai_manager.chat(
        message=request.message,
        system_prompt=DEFAULT_SYSTEM_PROMPT
    )

    # Save user message
    user_msg = ChatMessage(
        role="user",
        content=request.message,
        model_used=result.get("model")
    )
    db.add(user_msg)

    # Save assistant response
    assistant_msg = ChatMessage(
        role="assistant",
        content=result.get("response", ""),
        model_used=result.get("model"),
        tokens_used=result.get("tokens")
    )
    db.add(assistant_msg)

    db.commit()

    return ChatResponse(
        response=result.get("response", "No response"),
        model_used=result.get("model"),
        tokens_used=result.get("tokens")
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Send a chat message and stream the AI response as Server-Sent Events (SSE).

    Each event is a line of the form "data: <chunk>\\n\\n". The client should
    concatenate the chunks as they arrive to render the response incrementally.
    A final "event: done" marks the end of the stream.

    Note: this endpoint manages its own DB session (instead of Depends(get_db))
    because FastAPI tears down `yield`-based dependencies as soon as the route
    function returns - which happens immediately for a StreamingResponse, before
    the body has actually finished streaming. Using Depends(get_db) here would
    close the session while chunks are still being sent.
    """

    async def event_generator():
        full_response = ""
        model_used = ai_manager.current_provider_name
        try:
            async for chunk in ai_manager.chat_stream(request.message, DEFAULT_SYSTEM_PROMPT):
                full_response += chunk
                safe_chunk = chunk.replace("\r", "").replace("\n", "\\n")
                yield f"data: {safe_chunk}\n\n"
        finally:
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
    """Get chat history."""
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
    """Clear all chat history."""
    db.query(ChatMessage).delete()
    db.commit()
    return {"message": "Chat history cleared"}
