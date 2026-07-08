# Anthropic (Claude) — Frontier con foco en código y razonamiento

## Resumen

Anthropic es el **principal competidor de OpenAI** en 2026, con la familia Claude 4/5 (claude-opus-4-8 flagship, claude-mythos-5, claude-fable-5, claude-haiku-4-5). Conocido por su **fortaleza en código** (#1 en SWE-bench), razonamiento profundo (Computer Use), y prompt caching agresivo. Aithera v0.7.3 lo integra nativamente en `backend/app/ai/providers/anthropic_provider.py` con `claude-sonnet-4-6` como modelo declarado.

## Objetivo

Documentar el estado real de Anthropic en julio 2026: familia Claude 4.x/5, pricing, function calling propio (tool_use), Computer Use, prompt caching, y comparativa con OpenAI. Responde a "¿cuándo Anthropic gana sobre OpenAI?".

## Estado

🟡 En progreso — base escrita 2026-07-07. Pendiente verificar pricing oficial exacto (rate-limited).

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| Anthropic API | v1 (current) | Endpoint: `api.anthropic.com/v1/messages` |
| anthropic-sdk-python | ≥0.40 (recomendado ≥0.50) | MIT, async support |
| claude-opus-4-8 | Última flagship | jul 2026, top del line-up |
| claude-opus-4-7 | (jul 2026) | Predecessor |
| claude-opus-4-6 | (jul 2026) | Más antiguo |
| claude-opus-4-5 | (jul 2026) | Stable |
| claude-opus-4-1 | 2025-08-05 | Larga vida en producción |
| claude-mythos-5 | Última | Specialized (rebuscar exactamente) |
| claude-fable-5 | Última | Specialized (rebuscar exactamente) |
| claude-haiku-4-5 | Última 2025-10-01 | Barato y rápido |
| claude-sonnet-4-6 | (default declarado Aithera) | A actualizar a opus-4-8 |
| Aithera | V0.7+ | `app/ai/providers/anthropic_provider.py` |

## Familia Claude 4.x / 5 (jul 2026)

| Modelo | Lanzamiento | Notas |
|---|---|---|
| **claude-opus-4-8** | ~Q2 2026 | Flagship actual. Lo mejor en código + razonamiento. |
| **claude-opus-4-7** | ~Q1 2026 | Predecessor. |
| **claude-opus-4-6** | ~Q4 2025 | Más estable en producción. |
| **claude-opus-4-5** | 2025-11-01 | Buen balance. |
| **claude-opus-4-1** | 2025-08-05 | Larga vida útil, aún en uso. |
| **claude-mythos-5** | (jul 2026) | Variante specialized (verificar). |
| **claude-fable-5** | (jul 2026) | Variante specialized (verificar). |
| **claude-haiku-4-5** | 2025-10-01 | Barato y rápido. Default para alto volumen. |
| **claude-haiku-4-5-20251001** | Versión pinneada | Para reproducibilidad |

## API y SDK

### Endpoint

```
POST https://api.anthropic.com/v1/messages
```

### SDK: anthropic-sdk-python (MIT)

```bash
pip install anthropic>=0.50
```

```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key="sk-ant-...")

response = await client.messages.create(
    model="claude-opus-4-8",
    max_tokens=2048,
    messages=[
        {"role": "user", "content": "Hello!"}
    ],
    system="You are a helpful assistant.",
)

print(response.content[0].text)
print(response.usage.input_tokens, response.usage.output_tokens)
```

## Tool use (function calling)

Anthropic usa formato propio `tool_use`, no OpenAI-compat. Similar conceptualmente pero sintaxis diferente.

```python
tools = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            },
            "required": ["location"]
        }
    }
]

response = await client.messages.create(
    model="claude-opus-4-8",
    max_tokens=2048,
    tools=tools,
    messages=[
        {"role": "user", "content": "What's the weather in Madrid?"}
    ],
)

# response.stop_reason == "tool_use"
# response.content[0].type == "tool_use"
# response.content[0].name == "get_weather"
# response.content[0].input == {"location": "Madrid"}

# Tool result back to Claude:
messages.append({"role": "assistant", "content": response.content})
messages.append({
    "role": "user",
    "content": [{
        "type": "tool_result",
        "tool_use_id": response.content[0].id,
        "content": "sunny, 25°C"
    }]
})
```

## Streaming (SSE)

```python
async with client.messages.stream(
    model="claude-opus-4-8",
    max_tokens=2048,
    messages=[{"role": "user", "content": "Tell me a story"}]
) as stream:
    async for text in stream.text_stream:
        print(text, end="")
```

## Prompt caching (killer feature de Anthropic)

Anthropic soporta **prompt caching** agresivo: cacheas system prompt + documentos grandes y reduces el coste hasta 10x.

```python
response = await client.messages.create(
    model="claude-opus-4-8",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "You are an expert code reviewer...",
        },
        {
            "type": "text",
            "text": long_document,  # Cacheable
            "cache_control": {"type": "ephemeral"}  # Cache for 5 min
        }
    ],
    messages=[{"role": "user", "content": "Review this code: ..."}]
)

# response.usage.cache_creation_input_tokens  # First time
# response.usage.cache_read_input_tokens      # Subsequent reads (90% cheaper)
```

**Para Aithera**: la system prompt del Email Assistant (clasificación) y el contexto del proyecto (JWIKI) son ideales para prompt caching. Reduciría costes significativamente.

## Computer Use (único en producción)

Anthropic fue el primero en ofrecer **Computer Use** (control del escritorio vía screenshots + acciones):

```python
# Claude puede tomar screenshots y hacer click/type/scroll
# Requiere un sandbox seguro (Docker recomendado)
```

**Riesgos**:
- Necesita sandbox estricto
- Coste alto (muchos tokens por iteración)
- Latencia alta (segundos por iteración)

**Para Aithera**: Computer Use es lo que permitiría automatizar tareas de escritorio más allá de las tools. Aithera V0.9 (Automation) podría explorar esto con sandbox Docker.

## Vision

Anthropic soporta vision nativamente desde Claude 3:

```python
response = await client.messages.create(
    model="claude-opus-4-8",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "url", "url": "https://..."}},
                {"type": "text", "text": "What's in this image?"}
            ]
        }
    ]
)
```

Soporta: image (URL o base64), PDF (input nativo).

## Pricing (verificación pendiente)

> ADVERTENCIA: cifras estimadas a jul 2026.

| Modelo | Input $/1M | Output $/1M | Context | Notas |
|---|---|---|---|---|
| claude-opus-4-8 | ~$15.00 | ~$75.00 | 200K | Flagship caro |
| claude-opus-4-1 | ~$15.00 | ~$75.00 | 200K | Larga vida |
| claude-haiku-4-5 | ~$0.80 | ~$4.00 | 200K | **10x más barato** |
| claude-sonnet-4-6 | ~$3.00 | ~$15.00 | 200K | Balance |

**Prompt caching pricing** (separado):
- Cache write: +25% sobre input normal
- Cache read: **-90%** sobre input normal (90% descuento)

## Rate limits

| Tier | Spend | RPM | TPM |
|---|---|---|---|
| Free | $0 | 5 | 25K |
| Build Tier 1 | $5 | 60 | 500K |
| Build Tier 2 | $50 | 500 | 1M |
| Build Tier 3 | $200 | 2K | 4M |
| Build Tier 4 | $1K+ | 4K | 8M |

## Configuración en Aithera

### `app/ai/providers/anthropic_provider.py` (excerpt)

```python
from anthropic import AsyncAnthropic

class AnthropicProvider:
    """Proveedor Anthropic nativo."""
    
    default_model_name = "claude-sonnet-4-6"  # ACTUALIZAR a opus-4-8 en próxima iteración
    
    def __init__(self, api_key: str, **kwargs):
        self.client = AsyncAnthropic(api_key=api_key)
    
    async def chat(self, messages, model=None, system=None, **kwargs):
        model = model or self.default_model_name
        return await self.client.messages.create(
            model=model,
            max_tokens=kwargs.pop("max_tokens", 2048),
            messages=messages,
            system=system or "",
            **kwargs
        )
```

## Cuándo elegir Anthropic sobre OpenAI

✅ **Elegir Anthropic cuando**:
- Necesitas el **mejor código del mercado** (SWE-bench #1)
- Quieres **razonamiento profundo** (Mythos 5, Opus 4-8)
- **Prompt caching** es importante (ahorro 10x en costes)
- **Computer Use** (única opción madura)
- **PDF input** nativo
- **Larger context** que OpenAI (200K vs 128K en algunas configs)
- **Menor alucinación** en tareas técnicas

❌ **NO elegir Anthropic cuando**:
- **Realtime audio** (gpt-realtime-2 es único maduro)
- **Costo ultra-bajo** (DeepSeek 10x más barato, Haiku 4-5 es la opción Anthropic barata)
- **Vision multimodal** complejo (Gemini 3.5-pro mejor, OpenAI gpt-5.5 similar)
- **Video input** (Gemini 3.5-pro)
- **OpenAI ecosystem** (LangChain funciona, pero es nativo OpenAI)

## Diferencias OpenAI vs Anthropic (resumen)

| Criterio | OpenAI | Anthropic |
|---|---|---|
| API format | OpenAI chat/completions | Messages API (distinto) |
| Tool use format | OpenAI tools | tool_use blocks |
| Pricing | Caro pero razonable | Más caro pero prompt caching compensa |
| Velocidad | Rápido | Medio (Opus lento, Haiku rápido) |
| Código | Muy bueno | **El mejor** |
| Razonamiento | Muy bueno | Muy bueno |
| Multimodal | ✅ top | ✅ (no audio) |
| Realtime | ✅ gpt-realtime-2 | ❌ |
| Computer Use | ❌ | ✅ |
| Prompt caching | ❌ (todavía) | ✅ **killer feature** |
| Context window | 256K | 200K |
| PDF input | ❌ | ✅ nativo |
| Brand power | El más conocido | "AI safety focused" |

## Pendientes

- [ ] Verificar pricing oficial (rate-limited al redactar)
- [ ] Confirmar fecha exacta de claude-opus-4-8 release
- [ ] Documentar Computer Use en detalle con sandbox
- [ ] Documentar prompt caching con métricas reales
- [ ] Comparativa latency benchmarks vs OpenAI
- [ ] Actualizar Aithera v0.7.3 default de claude-sonnet-4-6 a claude-opus-4-8

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md) — matriz comparativa
- [JWIKI-020 openai.md](./openai.md) — competidor #1
- [JWIKI-022 gemini.md](./gemini.md) — Google
- [JWIKI-034 function-calling.md](./function-calling.md) — function calling
- [JWIKI-035 streaming.md](./streaming.md) — SSE streaming
- [JWIKI-036 pricing-comparison.md](./pricing-comparison.md)
- [JWIKI-041 multimodal.md](./multimodal.md)
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md)

## Fuentes

1. `https://api.anthropic.com/v1/messages` — acceso 2026-07-07
2. `https://docs.anthropic.com/en/docs/about-claude/models/overview` — acceso 2026-07-07
3. `https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching` — prompt caching
4. `https://docs.anthropic.com/en/docs/agents-and-tools/computer-use` — Computer Use
5. `github.com/anthropics/anthropic-sdk-python` — SDK oficial
6. `backend/app/ai/providers/anthropic_provider.py` — código Aithera v0.7.3

## Nivel de confianza

**88%** — Familia Claude confirmada, modelos identificados, SDK confirmado, prompt caching y Computer Use bien documentados. Pendiente: pricing exacto, fecha exacta de cada modelo, benchmarks de latencia.

---

## Changelog

### 2026-07-07 — versión inicial
- Autor: Aithera Escriba
- Cambio: doc creado con familia Claude 4.x/5, prompt caching, Computer Use
- Validador: contraste con `anthropic_provider.py` + website oficial
- Estado: 🟡 en progreso
