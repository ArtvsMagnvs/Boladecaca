# Performance — Streaming

## Resumen

**Streaming** es crítico para UX de chat: user ve respuesta empezar a llegar inmediatamente, no espera 10s.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## SSE (Server-Sent Events)

```python
# backend/app/api/endpoints/chat.py
@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        async for chunk in ai_manager.stream_chat(request):
            yield f"data: {chunk}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

## Frontend consumption (CLAUDE.md §2 pattern)

```tsx
// useRef pattern OBLIGATORIO
const accumulatedRef = useRef("");
const [, forceUpdate] = useReducer((x) => x + 1, 0);

const reader = response.body.getReader();
while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    accumulatedRef.current += new TextDecoder().decode(value);
}
forceUpdate();
```

## Backend TTFT optimization

- ✅ **Streaming SSE** (no esperar response completa).
- ✅ **Prompt caching** (Anthropic, OpenAI).
- ✅ **Smaller model** para chat (Gemini-Flash, DeepSeek-Flash).
- ✅ **TTFT < 500ms** target.

## Latency budget

| Stage | Target |
|---|---|
| Network | < 50ms |
| Server queue | < 100ms |
| LLM TTFT | < 500ms |
| First byte to client | < 100ms |
| **Total TTFB** | **< 750ms** |

## Para Aithera

- ✅ V0.7.3: SSE streaming.
- ✅ CLAUDE.md §2 useRef pattern.

## Referencias cruzadas

- [JWIKI-050 sse-streaming.md](../02_ARCHITECTURE/sse-streaming.md)
- [JWIKI-099 useref-streaming.md](../04_FRONTEND/useref-streaming.md)
- CLAUDE.md §2

## Fuentes

1. https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events

## Nivel de confianza

**100%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified