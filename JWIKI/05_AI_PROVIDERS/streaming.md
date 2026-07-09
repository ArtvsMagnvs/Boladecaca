# SSE Streaming — Estado por proveedor

## Resumen

**SSE (Server-Sent Events)** es el patrón estándar para streaming de LLMs. El servidor envía chunks `data: {...}` que el cliente concatena. Todos los proveedores principales lo soportan.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Matriz SSE

| Proveedor | SSE estándar | Chunks granularity | Cancelación | Tool calls en stream |
|---|---|---|---|---|
| **OpenAI** | ✅ | Fina (envía antes) | ✅ cierra conexión | ✅ desde gpt-4-turbo |
| **Anthropic** | ✅ | Conservadora | ✅ | ✅ desde Claude 3 |
| **Google Gemini** | ✅ | Fina | ✅ | ✅ |
| **DeepSeek** | ✅ OpenAI-compat | Fina | ✅ | ✅ |
| **Mistral** | ✅ OpenAI-compat | Fina | ✅ | ✅ |
| **Qwen** | ✅ OpenAI-compat | Fina | ✅ | ✅ |
| **Cohere** | ✅ formato propio | Fina | ✅ | ❌ |
| **xAI Grok** | ✅ OpenAI-compat | Fina | ✅ | ✅ |
| **Perplexity** | ✅ | Fina | ✅ | ❌ |
| **MiniMax** | ✅ OpenAI-compat | Media | ✅ | ❌ |
| **Ollama** | ✅ OpenAI-compat | Fina | ✅ | ✅ |
| **LM Studio** | ✅ OpenAI-compat | Fina | ✅ | ✅ |

## Formato OpenAI SSE

```
data: {"id":"chatcmpl-1","object":"chat.completion.chunk","choices":[{"delta":{"content":"Hello"},"index":0}]}

data: {"id":"chatcmpl-1","object":"chat.completion.chunk","choices":[{"delta":{"content":" world"},"index":0}]}

data: [DONE]
```

## Cliente SSE (Python)

```python
import httpx

async def stream_chat(messages):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "gpt-5.5", "messages": messages, "stream": True}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk = line[6:]
                    if chunk == "[DONE]":
                        break
                    # parse delta.content
```

## Cliente SSE (OpenAI SDK)

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()
stream = await client.chat.completions.create(
    model="gpt-5.5",
    messages=messages,
    stream=True
)

async for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

## B21 — Filtro de razonamiento en SSE

Aithera V0.8 `app/ai/reasoning_filter.py` filtra `<think>...</think>` de modelos razonadores (MiniMax M2.7, DeepSeek R1) en stream:

```python
from app.ai.reasoning_filter import StreamingReasoningFilter

filter = StreamingReasoningFilter()

async for chunk in stream:
    cleaned = filter.feed(chunk.choices[0].delta.content or "")
    if cleaned:
        # yield al cliente solo lo no-razonamiento
```

## Patrón `useRef` para acumular chunks

Frontend Aithera usa `useRef` para acumular chunks sin re-render:

```tsx
const accumulatedRef = useRef("");

async function* streamChat(messages) {
    const response = await fetch("/api/chat/stream", {...});
    const reader = response.body.getReader();
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = new TextDecoder().decode(value);
        accumulatedRef.current += chunk;  // acumula sin re-render
    }
}
```

## Cancelación

Cliente puede cerrar conexión para cancelar:

```javascript
const controller = new AbortController();
const response = await fetch("/api/chat/stream", {
    signal: controller.signal
});

// Para cancelar:
controller.abort();
```

El servidor detecta cierre de conexión y para la generación.

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-099 useref-streaming.md](../04_FRONTEND/useref-streaming.md) — patrón useRef frontend

## Fuentes

1. https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events — MDN SSE
2. https://platform.openai.com/docs/api-reference/streaming — OpenAI streaming
3. https://docs.anthropic.com/en/api/streaming — Anthropic streaming

## Nivel de confianza

**90%** — Patrón estándar bien documentado.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified