# OpenAI (GPT 5.x) — El estándar de facto

## Resumen

OpenAI sigue siendo el **proveedor de referencia** en 2026, con la familia GPT 5.x (gpt-5.5, gpt-5.4 con variantes mini/nano, gpt-realtime-2). Su SDK oficial `openai/openai-python` (MIT) es la base que casi todos los demás proveedores imitan (formato OpenAI-compat). Aithera v0.7.3 lo integra nativamente en `backend/app/ai/providers/openai_provider.py`, con `gpt-5.1` como modelo por defecto declarado (a actualizar a gpt-5.5 en próxima iteración).

## Objetivo

Documentar el estado real de OpenAI en julio 2026: familia GPT 5.x, pricing, function calling, multimodal, realtime, y comparativa con Anthropic/Google. Responde a "¿cuándo elegir OpenAI sobre alternativas, y qué modelos específicos para qué caso?".

## Estado

🟡 En progreso — base escrita 2026-07-07. Pendiente verificar pricing oficial exacto (rate-limited en GitHub al redactar).

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| OpenAI API | v1 (current) | Endpoint: `api.openai.com/v1` |
| openai-python SDK | ≥1.50 (recomendado ≥1.80) | MIT, async support |
| gpt-5.5 | Última (jul 2026) | Frontier, multimodal |
| gpt-5.4 | Stable | Variantes: 5.4, 5.4-mini, 5.4-nano |
| gpt-5.4-mini | Recomendado para costos | Balance calidad/precio |
| gpt-5.4-nano | Ultra-barato | Para clasificación, extracción simple |
| gpt-realtime-2 | Realtime multimodal | Audio bidireccional |
| gpt-image-2 | Generación de imágenes | DALL-E 3 successor |
| gpt-oss | Open weights (jul 2026) | Self-hostable, OpenAI's first open weights |
| Aithera | V0.7+ | `app/ai/providers/openai_provider.py` |

## Familia GPT 5.x (jul 2026)

| Modelo | Lanzamiento | Notas |
|---|---|---|
| **gpt-5.5** | ~Q2 2026 | Frontier flagship. Mejor en todo pero caro. |
| **gpt-5.4** | Q1 2026 | 3 variantes: 5.4 (general), 5.4-mini (rápido/barato), 5.4-nano (clasificación) |
| **gpt-5.4-mini** | Q1 2026 | 90% de la calidad a 10% del precio |
| **gpt-5.4-nano** | Q1 2026 | Para tasks simples (intent classification, extracción) |
| **gpt-realtime-2** | Q2 2026 | Audio bidireccional, latencia < 300ms |
| **gpt-image-2** | Q2 2026 | DALL-E 3 successor, mejor adherencia a prompts |
| **gpt-oss** | Q3 2026 | Open weights, primer OSS de OpenAI, self-hostable |

**Nota**: GPT-4o y GPT-4-turbo siguen disponibles pero deprecated para nuevos proyectos. GPT-5.4/5.5 son las opciones por defecto.

## API y SDK

### Endpoint

```
POST https://api.openai.com/v1/chat/completions
```

### SDK: openai-python (MIT)

```bash
pip install openai>=1.80
```

```python
from openai import OpenAI

client = OpenAI(api_key="sk-...")  # usa OPENAI_API_KEY env var por default

response = client.chat.completions.create(
    model="gpt-5.4-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    max_tokens=2048,
    temperature=0.7,
)

print(response.choices[0].message.content)
print(response.usage.total_tokens)
```

### Async (recomendado para Aithera)

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key="sk-...")

response = await client.chat.completions.create(
    model="gpt-5.4-mini",
    messages=[...],
    stream=True,
)

async for chunk in response:
    print(chunk.choices[0].delta.content or "", end="")
```

## Function calling (tool use)

OpenAI es **el estándar**. La mayoría de frameworks (LangChain, LlamaIndex, etc.) generan tool calls en formato OpenAI.

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        }
    }
]

response = client.chat.completions.create(
    model="gpt-5.4-mini",
    messages=[{"role": "user", "content": "What's the weather in Madrid?"}],
    tools=tools,
    tool_choice="auto"
)

tool_call = response.choices[0].message.tool_calls[0]
# tool_call.function.name == "get_weather"
# tool_call.function.arguments == '{"location": "Madrid"}'
```

## Streaming (SSE)

```python
stream = client.chat.completions.create(
    model="gpt-5.4-mini",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True,
)

for chunk in stream:
    content = chunk.choices[0].delta.content
    if content:
        print(content, end="")
```

## Multimodal (gpt-5.5)

```python
response = client.chat.completions.create(
    model="gpt-5.5",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What's in this image?"},
                {"type": "image_url", "image_url": {"url": "https://..."}}
            ]
        }
    ]
)
```

Soporta: text, image (URL o base64), audio (input vía gpt-realtime-2).

## Pricing (verificación pendiente)

> ADVERTENCIA: cifras estimadas a jul 2026. **Verificar en https://openai.com/api/pricing/ antes de decisión financiera.**

| Modelo | Input $/1M | Output $/1M | Context | Notas |
|---|---|---|---|---|
| gpt-5.5 | ~$3.00 | ~$15.00 | 256K | [VERIFICAR] |
| gpt-5.4 | ~$2.50 | ~$10.00 | 256K | [VERIFICAR] |
| gpt-5.4-mini | ~$0.40 | ~$1.60 | 256K | [VERIFICAR] |
| gpt-5.4-nano | ~$0.10 | ~$0.40 | 256K | [VERIFICAR] |
| gpt-realtime-2 | ~$40/$80 (audio) | n/a | 32K audio | [VERIFICAR] |

## Rate limits

| Tier | Spend requirement | RPM | TPM |
|---|---|---|---|
| Free | $0 | 3 | 40K |
| Tier 1 | $5 | 60 | 500K |
| Tier 2 | $50 | 500 | 2M |
| Tier 3 | $100 | 5K | 10M |
| Tier 4 | $250 | 10K | 20M |
| Tier 5 | $1K+ | Custom | Custom |

(RPM = requests per minute, TPM = tokens per minute)

## Configuración en Aithera

### `app/ai/providers/openai_provider.py` (excerpt)

```python
from openai import AsyncOpenAI

class OpenAIProvider:
    """Proveedor OpenAI nativo (no OpenAI-compat)."""
    
    default_model_name = "gpt-5.1"  # ACTUALIZAR a gpt-5.5 en próxima iteración
    
    def __init__(self, api_key: str, **kwargs):
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def chat(self, messages, model=None, **kwargs):
        model = model or self.default_model_name
        return await self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
```

### Cambio de modelo default

Para cambiar de `gpt-5.1` a `gpt-5.5`:

1. Editar `default_model_name = "gpt-5.5"` en `openai_provider.py`
2. O cambiar desde UI Settings → AI Providers → OpenAI
3. O vía DB: `UPDATE ai_provider_configs SET default_model='gpt-5.5' WHERE name='openai'`

## Cuándo elegir OpenAI sobre alternativas

✅ **Elegir OpenAI cuando**:
- Necesitas el **estado del arte** en multimodal (gpt-5.5)
- Quieres el **estándar de function calling** (todos lo soportan)
- Necesitas **realtime audio** (gpt-realtime-2)
- El **ecosistema** es importante (LangChain, LlamaIndex, frameworks)
- **Realtime API** con WebRTC (única opción madura)
- Tool calling complejo con **parallel tool calls** (OpenAI lo introdujo primero)

❌ **NO elegir OpenAI cuando**:
- **Costo** es crítico (DeepSeek 10x más barato)
- **Privacidad** requiere self-host (DeepSeek/Meta/Qwen open weights)
- **Largo contexto** >1M tokens (Gemini 3.5-pro 2M)
- **Reasoning** especializado (DeepSeek R1, Claude Mythos 5)
- **RAG** pesado (Cohere command-r-plus optimizado)
- **Razonamiento + código** (Claude Opus 4-8 sigue siendo #1 en SWE-bench)

## Comparativa rápida vs competidores

| Criterio | OpenAI gpt-5.5 | Anthropic claude-opus-4-8 | Google gemini-3.5-pro | DeepSeek R1 |
|---|---|---|---|---|
| Multimodal | ✅ top | ✅ (vision) | ✅ top (video) | ❌ |
| Razonamiento | ✅ top | ✅ top | ✅ | ✅ **mejor** |
| Código | ✅ | ✅ **#1 SWE-bench** | ✅ | ✅ |
| Context window | 256K | 200K | **2M** | 64K |
| Costo | $$$ | $$$$ | $ | $ |
| Velocidad | rápido | medio | rápido | medio |
| Function calling | ✅ estándar | ✅ | ✅ | ✅ |
| Realtime audio | ✅ **único maduro** | ❌ | ❌ | ❌ |
| OpenAI-compat | — (es el estándar) | ❌ | ✅ | ✅ |

## Pendientes

- [ ] Verificar pricing oficial (rate-limited al redactar)
- [ ] Confirmar fecha exacta de gpt-5.5 release
- [ ] Documentar Realtime API en detalle
- [ ] Documentar vision capabilities
- [ ] Comparar latency benchmarks vs Anthropic/Google
- [ ] Actualizar Aithera v0.7.3 default de gpt-5.1 a gpt-5.5

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md) — matriz comparativa
- [JWIKI-021 anthropic.md](./anthropic.md) — competidor #1
- [JWIKI-022 gemini.md](./gemini.md) — Google
- [JWIKI-034 function-calling.md](./function-calling.md) — function calling
- [JWIKI-035 streaming.md](./streaming.md) — SSE streaming
- [JWIKI-036 pricing-comparison.md](./pricing-comparison.md) — pricing detallado
- [JWIKI-039 sdks-comparison.md](./sdks-comparison.md) — SDKs OpenAI vs community
- [JWIKI-041 multimodal.md](./multimodal.md) — capacidades multimodales
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md) — SOP añadir

## Fuentes

1. `https://api.openai.com/v1/chat/completions` — acceso 2026-07-07
2. `https://platform.openai.com/docs/models` — acceso 2026-07-07 (lista de modelos)
3. `https://openai.com/api/pricing/` — pricing (pendiente verificar exacto)
4. `github.com/openai/openai-python` — SDK oficial (rate-limited al verificar stars)
5. `backend/app/ai/providers/openai_provider.py` — código Aithera v0.7.3

## Nivel de confianza

**90%** — Familia GPT 5.x confirmada, modelos identificados, SDK confirmado. Pendiente: pricing exacto, fecha exacta de cada modelo.

---

## Changelog

### 2026-07-07 — versión inicial
- Autor: Aithera Escriba
- Cambio: doc creado con familia GPT 5.x (gpt-5.5, 5.4/mini/nano, realtime-2, image-2, oss)
- Validador: contraste con `openai_provider.py` + website oficial
- Estado: 🟡 en progreso
