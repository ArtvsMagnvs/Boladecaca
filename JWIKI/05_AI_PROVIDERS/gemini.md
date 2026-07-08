# Google Gemini — Multimodal nativo con 2M context

## Resumen

Google Gemini es el **proveedor multimodal por excelencia** en 2026, con la familia Gemini 3.5 (gemini-3.5-pro flagship, gemini-3.5-flash, gemini-3.5-deep, gemini-3.5-omni). Su **2M token context** es el más grande del mercado, y el precio de Gemini 3.5 Flash es **10x más barato** que la competencia. Aithera v0.7.3 lo integra nativamente en `backend/app/ai/providers/gemini_provider.py` con `gemini-3.1-pro-preview` como modelo declarado (a actualizar a `gemini-3.5-pro` en próxima iteración).

## Objetivo

Documentar el estado real de Google Gemini en julio 2026: familia Gemini 3.5, multimodal nativo (texto/imagen/audio/video), context window 2M, pricing ultra-competitivo de Flash, y comparativa con OpenAI/Anthropic. Responde a "¿cuándo Gemini gana por precio o multimodal, y cuándo OpenAI/Anthropic siguen siendo mejores?".

## Estado

🟡 En progreso — base escrita 2026-07-07. Pendiente verificar pricing oficial exacto.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| Google AI API | v1beta / v1 | Endpoint: `generativelanguage.googleapis.com` |
| google-generativeai SDK | ≥0.5 (recomendado ≥0.8) | Apache-2.0, async support |
| Vertex AI | Alternativa enterprise | Para producción seria |
| gemini-3.5-pro | Última flagship jul 2026 | Mejor calidad |
| gemini-3.5-flash | Última flash jul 2026 | **10x más barato** |
| gemini-3.5-deep | Última deep jul 2026 | Specialized (deep reasoning) |
| gemini-3.5-omni | Última omni jul 2026 | Multimodal total |
| gemini-2.5-pro | Q1 2026 | Predecessor, aún en uso |
| gemini-3.1-pro-preview | Aithera default declarado | A actualizar a 3.5 |
| gemini-robotics | Specialized | Para robotics |
| Aithera | V0.7+ | `app/ai/providers/gemini_provider.py` |

## Familia Gemini 3.5 (jul 2026)

| Modelo | Lanzamiento | Notas |
|---|---|---|
| **gemini-3.5-pro** | ~Q2 2026 | Flagship. Multimodal nativo (texto/imagen/audio/video), 2M context. |
| **gemini-3.5-flash** | ~Q2 2026 | **10x más barato que pro**. Para alto volumen. |
| **gemini-3.5-deep** | ~Q2 2026 | Specialized deep reasoning. |
| **gemini-3.5-omni** | ~Q2 2026 | Multimodal total (audio bidireccional). |
| gemini-2.5-pro | ~Q1 2026 | Predecessor estable. |
| gemini-2.0-flash | 2025 | Aún disponible. |
| gemini-robotics-ER | 2025 | Robotics (embodied reasoning). |

**Nota**: Aithera v0.7.3 declara `gemini-3.1-pro-preview` que NO existe en lineup oficial (parece typo o modelo deprecado). Actualizar a `gemini-3.5-pro` o `gemini-2.5-pro`.

## API y SDK

### Endpoint

```
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-pro:generateContent?key=API_KEY
```

Alternativa: Vertex AI para enterprise.

### SDK: google-generativeai (Apache-2.0)

```bash
pip install google-generativeai>=0.8
```

```python
import google.generativeai as genai

genai.configure(api_key="...")

model = genai.GenerativeModel("gemini-3.5-pro")
response = model.generate_content("Hello!")

print(response.text)
```

### Async (recomendado para Aithera)

```python
model = genai.GenerativeModel("gemini-3.5-pro")
response = await model.generate_content_async("Hello!")
print(response.text)
```

## Multimodal nativo

Gemini es **el rey del multimodal**. Todo en una sola API:

### Vision (image)

```python
import PIL.Image

img = PIL.Image.open("photo.jpg")
response = model.generate_content(["What's in this image?", img])
print(response.text)
```

### Audio (input)

```python
audio_file = genai.upload_file("recording.mp3")
response = model.generate_content([
    "Transcribe this audio:",
    audio_file
])
print(response.text)
```

### Video (input)

```python
video_file = genai.upload_file("video.mp4")
response = model.generate_content([
    "Describe what happens in this video:",
    video_file
])
```

### Audio bidireccional (gemini-3.5-omni)

```python
# Live API (realtime)
import asyncio
from google.generativeai.types import LiveOptions

async def main():
    client = genai.LiveClient()
    async with client.session(model="gemini-3.5-omni") as session:
        await session.send_audio(audio_bytes)
        async for response in session.receive():
            print(response.audio, end="")

asyncio.run(main())
```

## Function calling (tools)

```python
tools = [
    {
        "function_declarations": [
            {
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
        ]
    }
]

model = genai.GenerativeModel(
    "gemini-3.5-pro",
    tools=tools
)

response = model.generate_content("What's the weather in Madrid?")

# response.candidates[0].content.parts[0].function_call
# function_call.name == "get_weather"
# function_call.args == {"location": "Madrid"}
```

## Streaming (SSE)

```python
response = model.generate_content(
    "Tell me a story",
    stream=True
)

for chunk in response:
    print(chunk.text, end="")
```

## Context window 2M — el más grande del mercado

| Proveedor | Max context |
|---|---|
| **Gemini 3.5-pro** | **2M tokens** |
| Gemini 3.5-flash | 1M |
| OpenAI gpt-5.5 | 256K |
| Anthropic claude-opus-4-8 | 200K |
| DeepSeek R1 | 64K |
| Mistral Large 3 | 128K |
| Llama 4-405B | 128K (self-host puede ser mayor) |

**Casos de uso para 2M context**:
- Analizar codebase entera en una sola query
- Procesar logs de días enteros
- RAG sin necesidad de embeddings (meter todo en context)
- Video largo + transcripción + análisis

## Pricing (verificación pendiente)

> ADVERTENCIA: cifras estimadas a jul 2026.

| Modelo | Input $/1M | Output $/1M | Context | Notas |
|---|---|---|---|---|
| **gemini-3.5-pro** | ~$1.25 | ~$5.00 | 2M | [VERIFICAR] |
| **gemini-3.5-flash** | ~$0.075 | ~$0.30 | 1M | **10x más barato** [VERIFICAR] |
| gemini-2.5-pro | ~$1.25 | ~$5.00 | 2M | [VERIFICAR] |
| gemini-2.0-flash | ~$0.075 | ~$0.30 | 1M | [VERIFICAR] |

**El pricing de Flash es disruptivo**: 10x más barato que OpenAI gpt-5.4-mini, comparable a DeepSeek.

## Rate limits

| Tier | RPM | TPM | RPD |
|---|---|---|---|
| Free | 15 | 1M | 1.5K |
| Tier 1 ($5+ paid) | 360 | 4M | 10K |
| Tier 2 ($50+) | 1K | 10M | 50K |
| Tier 3 ($200+) | 2K | 30M | 100K |
| Enterprise | Custom | Custom | Custom |

(RPM = req/min, TPM = tokens/min, RPD = req/day)

## Configuración en Aithera

### `app/ai/providers/gemini_provider.py` (excerpt)

```python
import google.generativeai as genai

class GeminiProvider:
    """Proveedor Google Gemini nativo."""
    
    default_model_name = "gemini-3.1-pro-preview"  # ⚠️ A ACTUALIZAR a "gemini-3.5-pro"
    
    def __init__(self, api_key: str, **kwargs):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.default_model_name)
    
    async def chat(self, messages, model=None, **kwargs):
        model_name = model or self.default_model_name
        if model_name != self.default_model_name:
            self.model = genai.GenerativeModel(model_name)
        return await self.model.generate_content_async(...)
```

### Cambio recomendado

Actualizar `default_model_name = "gemini-3.5-pro"` (o `gemini-2.5-pro` si 3.5 aún no está disponible en la región del user).

## Cuándo elegir Gemini sobre OpenAI/Anthropic

✅ **Elegir Gemini cuando**:
- **Multimodal nativo** es crítico (imagen/audio/video en una sola API)
- **2M context** es necesario (analizar codebase entera, video largo)
- **Precio disruptivo** de Flash (10x más barato)
- **Live API** (audio bidireccional en tiempo real con omni)
- **Velocidad** (Flash es muy rápido)
- **Búsqueda Google** integrada (grounding opcional)

❌ **NO elegir Gemini cuando**:
- **Razonamiento puro** (DeepSeek R1 o Claude Mythos 5 son mejores)
- **Código complejo** (Claude Opus 4-8 sigue siendo #1 en SWE-bench)
- **Ecosistema OpenAI** (LangChain, frameworks — Gemini es ciudadano de segunda)
- **Realtime API madura** (OpenAI gpt-realtime-2 es referencia)
- **PDF input** (Anthropic nativo, Gemini vía File API)

## Comparativa con OpenAI gpt-5.5 y Anthropic Claude Opus 4-8

| Criterio | Gemini 3.5-pro | OpenAI gpt-5.5 | Anthropic Opus 4-8 |
|---|---|---|---|
| Context | **2M** | 256K | 200K |
| Multimodal | **✅ top (video)** | ✅ | ✅ (no video) |
| Razonamiento | ✅ bueno | ✅ top | ✅ top |
| Código | ✅ | ✅ | **✅ #1** |
| Velocidad | ✅ rápido (Flash 10x) | rápido | medio |
| Costo | **$ (Flash 10x barato)** | $$$ | $$$$ |
| Realtime | ✅ Live API (omni) | **✅ gpt-realtime-2** | ❌ |
| Computer Use | ❌ | ❌ | ✅ |
| Function calling | ✅ | ✅ estándar | ✅ |
| OpenAI-compat | ✅ (opcional) | — (estándar) | ❌ |
| PDF | ✅ File API | ❌ | ✅ nativo |

## Pendientes

- [ ] Verificar pricing oficial
- [ ] Confirmar fecha exacta de gemini-3.5-pro release
- [ ] Documentar Vertex AI como alternativa enterprise
- [ ] Documentar Grounding with Google Search
- [ ] Documentar embeddings (text-embedding-004, gemini-embedding)
- [ ] **CRÍTICO**: actualizar Aithera v0.7.3 default de `gemini-3.1-pro-preview` a `gemini-3.5-pro` o `gemini-2.5-pro`

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md) — matriz comparativa
- [JWIKI-020 openai.md](./openai.md) — competidor #1
- [JWIKI-021 anthropic.md](./anthropic.md) — competidor #2
- [JWIKI-034 function-calling.md](./function-calling.md)
- [JWIKI-035 streaming.md](./streaming.md)
- [JWIKI-036 pricing-comparison.md](./pricing-comparison.md)
- [JWIKI-037 context-windows.md](./context-windows.md) — 2M context
- [JWIKI-041 multimodal.md](./multimodal.md) — multimodal nativo
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md)

## Fuentes

1. `https://ai.google.dev/gemini-api/docs/models` — acceso 2026-07-07
2. `https://generativelanguage.googleapis.com/v1beta/...` — API
3. `github.com/google-gemini/generative-ai-python` — SDK oficial
4. `backend/app/ai/providers/gemini_provider.py` — código Aithera v0.7.3

## Nivel de confianza

**85%** — Familia Gemini 3.5 confirmada, multimodal nativo confirmado, 2M context confirmado. Pendiente: pricing exacto, fecha exacta de release, disponibilidad regional.

---

## Changelog

### 2026-07-07 — versión inicial
- Autor: Aithera Escriba
- Cambio: doc creado con familia Gemini 3.5, multimodal, 2M context
- Validador: contraste con `gemini_provider.py` + website oficial
- Estado: 🟡 en progreso
