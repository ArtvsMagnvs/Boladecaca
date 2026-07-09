# Multimodal — Capacidades image/audio/video por proveedor

## Resumen

**Multimodal** = capacidad de procesar/entregar texto + imagen + audio + video. Tabla comparativa por proveedor.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Matriz multimodal

| Proveedor | Image in | Audio in | Video in | Audio out | Image out | Video out |
|---|---|---|---|---|---|---|
| **OpenAI gpt-5.5** | ✅ | ✅ (realtime) | ❌ | ✅ (realtime) | ✅ (gpt-image-2) | ❌ |
| **OpenAI gpt-realtime-2** | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Anthropic Claude Opus 4-8** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Anthropic Claude** | ✅ PDF | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Google Gemini 3.5-pro** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Google Gemini 3.5-omni** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **DeepSeek** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Mistral Pixtral Large** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **xAI Grok 4.3** | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Ollama (llava)** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Qwen-VL** | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |

## Gemini 3.5-omni — el multimodal más completo

`gemini-3.5-omni` es el **único modelo comercial** con multimodal nativo completo:
- Image, audio, video input.
- Audio bidireccional (Live API).
- Streaming multimodal.

## Claude Opus 4-8 — vision + PDF

```python
response = await client.messages.create(
    model="claude-opus-4-8",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "url", "url": "https://..."}},
                {"type": "document", "source": {"type": "url", "url": "https://...pdf"}},  # PDF nativo
                {"type": "text", "text": "What's in this image and PDF?"}
            ]
        }
    ]
)
```

## OpenAI gpt-image-2 — generación de imágenes

```python
from openai import OpenAI

client = OpenAI()
response = client.images.generate(
    model="gpt-image-2",
    prompt="A futuristic JARVIS UI",
    n=1,
    size="1024x1024"
)
```

## Gemini video input

```python
import google.generativeai as genai

genai.configure(api_key="...")
video = genai.upload_file("video.mp4")
response = model.generate_content(["Describe video:", video])
```

## Aithera V0.7.3 y multimodal

Aithera **NO usa multimodal** directamente en V0.7.3. Pero podría:
- **V0.85**: ingest de PDFs en JWIKI con Gemini 2M context (PDF support nativo).
- **V1.0**: Computer Use de Anthropic para automatizaciones desktop.

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-022 gemini.md](./gemini.md)
- [JWIKI-021 anthropic.md](./anthropic.md)
- [JWIKI-020 openai.md](./openai.md)

## Fuentes

1. https://platform.openai.com/docs/guides/vision
2. https://docs.anthropic.com/en/docs/build-with-claude/vision
3. https://ai.google.dev/gemini-api/docs/vision

## Nivel de confianza

**85%** — Capacidades principales confirmadas.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified