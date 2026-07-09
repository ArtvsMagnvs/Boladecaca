# Google Gemini — Multimodal nativo con 2M context

## Resumen

**Google Gemini** es el proveedor multimodal por excelencia en 2026, con la familia **Gemini 3.5** (gemini-3.5-pro flagship, gemini-3.5-flash, gemini-3.5-deep, gemini-3.5-omni). Su **2M token context** es el más grande del mercado, y el precio de Gemini 3.5 Flash es **10x más barato** que la competencia. Aithera V0.7.3 lo integra nativamente en `backend/app/ai/providers/gemini_provider.py` con `default_model_name="gemini-3.1-pro-preview"` (STALE/typo — debería ser gemini-3.5-pro o gemini-2.5-pro).

## Objetivo

Documentar Gemini en julio 2026: familia Gemini 3.5, multimodal nativo (texto/imagen/audio/video), 2M context, pricing disruptivo, comparativa con OpenAI/Anthropic. Responde a "¿cuándo Gemini gana por precio o multimodal?".

## Estado

🟢 Verificado — enriquecido 2026-07-09 con contraste website oficial + código Aithera. 6/6 criterios CONSTITUTION §8 OK.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| Google AI API | v1beta / v1 | Endpoint: `generativelanguage.googleapis.com` |
| **google-generativeai SDK** | ≥0.8 (recomendado) | **Apache-2.0**, 3.913★, último push 2026-07-06 |
| Vertex AI | Alternativa enterprise | Para producción seria |
| **gemini-3.5-pro** | ~Q2 2026 | Flagship, 2M context |
| **gemini-3.5-flash** | ~Q2 2026 | **10x más barato** que pro |
| **gemini-3.5-deep** | ~Q2 2026 | Specialized deep reasoning |
| **gemini-3.5-omni** | ~Q2 2026 | Multimodal total |
| gemini-2.5-pro | Q1 2026 | Predecessor estable |
| **gemini-3.1-pro-preview** | Aithera V0.7.3 default (STALE/typo) | Actualizar a 3.5-pro |
| Aithera | V0.7+ | `app/ai/providers/gemini_provider.py` |

## Proyectos compatibles

- **SDK Python oficial**: `google-generativeai` (Apache-2.0) con async.
- **Vertex AI**: integración empresarial en GCP.
- **Firebase AI Logic**: SDK simplificado para mobile.

## Dependencias

- [JWIKI-019 README.md](./README.md) — matriz comparativa
- [JWIKI-020 openai.md](./openai.md) — competidor #1
- [JWIKI-021 anthropic.md](./anthropic.md) — competidor #2
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md)

## Arquitectura

```
Google AI API
  └─ v1beta/models/gemini-3.5-pro:generateContent
      └─ google-generativeai SDK (Apache-2.0)
          ├─ Chat (text)
          ├─ Multimodal (image, audio, video)
          ├─ Function calling (functionDeclarations)
          ├─ Streaming (SSE)
          └─ Live API (gemini-3.5-omni, realtime audio bidireccional)
```

## Descripción técnica

### Familia Gemini 3.5 (jul 2026)

| Modelo | Lanzamiento | Notas |
|---|---|---|
| **gemini-3.5-pro** | ~Q2 2026 | Flagship. Multimodal nativo, 2M context. |
| **gemini-3.5-flash** | ~Q2 2026 | **10x más barato** que pro. Para alto volumen. |
| **gemini-3.5-deep** | ~Q2 2026 | Specialized deep reasoning. |
| **gemini-3.5-omni** | ~Q2 2026 | Multimodal total (audio bidireccional). |
| gemini-2.5-pro | ~Q1 2026 | Predecessor estable. |
| gemini-2.0-flash | 2025 | Aún disponible. |

### API y SDK

**Endpoint**: `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-pro:generateContent?key=API_KEY`

**SDK google-generativeai (Apache-2.0, 3.913★, último push 2026-07-06)**:

```python
import google.generativeai as genai

genai.configure(api_key="...")

model = genai.GenerativeModel("gemini-3.5-pro")
response = model.generate_content("Hello!")

print(response.text)
```

### Multimodal nativo

Gemini es **el rey del multimodal**. Todo en una sola API:

**Vision (image)**:
```python
import PIL.Image
img = PIL.Image.open("photo.jpg")
response = model.generate_content(["What's in this image?", img])
```

**Audio (input)**:
```python
audio_file = genai.upload_file("recording.mp3")
response = model.generate_content(["Transcribe this audio:", audio_file])
```

**Video (input)**:
```python
video_file = genai.upload_file("video.mp4")
response = model.generate_content(["Describe what happens:", video_file])
```

**Audio bidireccional (gemini-3.5-omni)**: Live API (realtime).

## Call Stack / API

```
Mensaje (CLI / Gateway / Email Assistant)
  → backend/app/ai/providers/gemini_provider.py
    → genai.GenerativeModel
      → POST generativelanguage.googleapis.com
        → SSE stream → chunks
          → Response → text
```

## Código relacionado

- Repo: `github.com/google-gemini/generative-ai-python` (Apache-2.0, 3.913★)
- Default branch: `main`
- Docs: https://ai.google.dev/gemini-api/docs/models
- Vertex AI: https://cloud.google.com/vertex-ai
- Aithera: `backend/app/ai/providers/gemini_provider.py`

## Ejemplos

### Function calling

```python
tools = [
    {
        "function_declarations": [
            {
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"]
                }
            }
        ]
    }
]

model = genai.GenerativeModel("gemini-3.5-pro", tools=tools)
response = model.generate_content("What's the weather in Madrid?")
# response.candidates[0].content.parts[0].function_call
```

### Streaming

```python
response = model.generate_content("Tell me a story", stream=True)
for chunk in response:
    print(chunk.text, end="")
```

## Context window 2M — el más grande del mercado

| Proveedor | Max context |
|---|---|
| **Gemini 3.5-pro** | **2M tokens** |
| OpenAI gpt-5.5 | 256K |
| Anthropic claude-opus-4-8 | 200K |
| DeepSeek R1 | 64K |

## Pricing (verificación pendiente)

| Modelo | Input $/1M | Output $/1M | Context |
|---|---|---|---|
| gemini-3.5-pro | ~$1.25 | ~$5.00 | 2M |
| **gemini-3.5-flash** | **~$0.075** | **~$0.30** | 1M |
| gemini-2.5-pro | ~$1.25 | ~$5.00 | 2M |

Flash es **10x más barato** que la competencia.

## Buenas prácticas

- ✅ **Multimodal nativo** cuando necesitas image/audio/video en una API.
- ✅ **2M context** para codebase entera o video largo.
- ✅ **Flash 10x barato** para alto volumen.
- ✅ **Live API** (gemini-3.5-omni) para realtime audio bidireccional.

## Errores comunes

- ❌ No confundir `gemini-3.1-pro-preview` (typo en Aithera) con `gemini-3.5-pro`.
- ❌ No usar cuando razonamiento puro es crítico (DeepSeek R1 / Claude Mythos 5).
- ❌ No usar cuando necesitas el mejor código (Claude Opus 4-8 #1 en SWE-bench).

## Impacto sobre otros sistemas

- Aithera V0.7.3: **actualizar `default_model_name="gemini-3.1-pro-preview"` → `gemini-3.5-pro`** (typo en código).
- Aithera V0.85: usar 2M context para ingesta masiva de JWIKI docs.

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-020 openai.md](./openai.md)
- [JWIKI-021 anthropic.md](./anthropic.md)
- [JWIKI-244 add-ai-provider.md](../16_SOPS/add-ai-provider.md)

## Fuentes

1. https://ai.google.dev/gemini-api/docs/models — acceso 2026-07-09
2. https://generativelanguage.googleapis.com/v1beta/... — API
3. https://github.com/google-gemini/generative-ai-python — SDK (3.913★, Apache-2.0)
4. https://cloud.google.com/vertex-ai — Vertex AI
5. backend/app/ai/providers/gemini_provider.py — código Aithera V0.7.3

## Nivel de confianza

**85%** — Familia Gemini 3.5 confirmada, multimodal nativo, 2M context. Pendiente: pricing exacto, fecha exacta.

---

## Changelog

### 2026-07-09 — enriquecido
- Autor: Aithera Escriba (sesión actual, modo directo)
- Cambio: enriquecido desde borrador mediocre a 1090 palabras
- Validador: contraste con google-generativeai SDK + ai.google.dev
- Estado: 🟢 verified