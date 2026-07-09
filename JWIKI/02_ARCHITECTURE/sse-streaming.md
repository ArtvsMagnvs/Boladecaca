# SSE Streaming — Server-Sent Events en Aithera

## Resumen

**SSE (Server-Sent Events)** es el protocolo usado por Aithera V0.7.3 para streaming de chat. A diferencia de WebSocket, SSE es unidirectional (server → client) sobre HTTP. Más simple que WS para nuestro caso.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## SSE vs WebSocket

| Aspecto | SSE | WebSocket |
|---|---|---|
| **Dirección** | Server → Client | Bidirectional |
| **Protocolo** | HTTP | Upgrade a ws:// |
| **Reconexión** | Auto (eventos) | Manual |
| **Complejidad** | Baja | Alta |
| **Caso de uso** | Streaming de AI, notifications | Chat real-time, multiplayer |
| **Proxy/firewall** | ✅ friendly | ❌ a veces bloqueado |
| **Browser support** | ✅ EventSource nativo | ✅ WebSocket API |

## Aithera usa SSE para

- ✅ Chat streaming (`POST /api/chat/stream`).
- ✅ Voice synthesis streaming (`POST /api/voice/synthesize`).
- ✅ Email Assistant processing (futuro).

## FastAPI SSE

```python
from fastapi.responses import StreamingResponse

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        async for chunk in ai_provider.stream_chat(request.messages):
            yield f"data: {chunk.json()}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # nginx
        }
    )
```

## Formato SSE

```
data: {"id":"chatcmpl-1","object":"chat.completion.chunk","choices":[{"delta":{"content":"Hello"},"index":0}]}

data: {"id":"chatcmpl-1","object":"chat.completion.chunk","choices":[{"delta":{"content":" world"},"index":0}]}

data: {"id":"chatcmpl-1","object":"chat.completion.chunk","choices":[{"delta":{},"finish_reason":"stop"}],"usage":{...}}

data: [DONE]

```

## Cliente EventSource

```typescript
const eventSource = new EventSource("/api/chat/stream", {
    // con POST no es posible, EventSource es GET only
});

// Para POST streaming, usar fetch + ReadableStream
const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(request)
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value);
    // parse "data: {...}\n\n"
    // acumular con useRef
}
```

## B21 Reasoning Filter en SSE

Aithera V0.8 filtra `<think>...</think>` en stream:

```python
from app.ai.reasoning_filter import StreamingReasoningFilter

filter = StreamingReasoningFilter()

async def generate_filtered():
    async for chunk in provider.stream_chat(messages):
        cleaned = filter.feed(chunk.choices[0].delta.content or "")
        if cleaned:
            yield f"data: {cleaned}\n\n"
```

## Acumulación frontend con useRef

Patrón Aithera (CLAUDE.md §2):

```tsx
const accumulatedRef = useRef("");
const [, forceUpdate] = useReducer((x) => x + 1, 0);

async function streamChat(messages) {
    const response = await fetch("/api/chat/stream", {
        method: "POST",
        body: JSON.stringify({messages})
    });
    const reader = response.body.getReader();
    while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        const chunk = new TextDecoder().decode(value);
        accumulatedRef.current += chunk;  // acumula sin re-render
    }
    forceUpdate();  // trigger 1 re-render al final
}
```

## Manejo de errores

```python
async def generate_with_errors():
    try:
        async for chunk in provider.stream_chat(messages):
            yield f"data: {chunk.json()}\n\n"
    except asyncio.CancelledError:
        # cliente desconectó
        logger.info("Stream cancelled by client")
        raise
    except Exception as e:
        logger.exception("Stream error")
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
```

## Cancelación

```python
@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    # Generador async
    async def generate():
        ...
    
    return StreamingResponse(generate(), ...)
    # FastAPI automáticamente cancela el generador cuando el cliente desconecta
```

## Rate limiting en SSE

Para evitar abuse:
- API key auth.
- Max connections per user.
- Max tokens per minute.

## Referencias cruzadas

- [JWIKI-035 streaming.md](../05_AI_PROVIDERS/streaming.md)
- [JWIKI-049 async-patterns.md](./async-patterns.md)
- [JWIKI-099 useref-streaming.md](../04_FRONTEND/useref-streaming.md)

## Fuentes

1. https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
2. https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
3. https://html.spec.whatwg.org/multipage/server-sent-events.html

## Nivel de confianza

**95%** — SSE estándar, bien documentado.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified