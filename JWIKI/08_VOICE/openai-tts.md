# OpenAI TTS — Alternativa cloud

## Resumen

**OpenAI TTS** ofrece TTS de alta calidad con `tts-1` y `tts-1-hd`. Disponible via API OpenAI standard. **NO es el primario en Aithera V0.8.0** (ElevenLabs lo es).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Modelos

| Modelo | Calidad | Latency | Precio |
|---|---|---|---|
| `tts-1` | ⭐⭐⭐⭐ | rápida | $15/1M chars |
| `tts-1-hd` | ⭐⭐⭐⭐⭐ | lenta | $30/1M chars |
| `gpt-4o-mini-tts` | ⭐⭐⭐⭐⭐ | media | $10/1M chars (input) + $20/1M (output) |

## Voces

6 voces pre-built:
- `alloy` (neutral)
- `echo` (male)
- `fable` (British male)
- `onyx` (deep male)
- `nova` (female)
- `shimmer` (female)

## API

```python
from openai import OpenAI

client = OpenAI()

# Síntesis básica
response = client.audio.speech.create(
    model="tts-1",
    voice="alloy",
    input="Hola, ¿cómo estás?"
)

# Streaming
response = client.audio.speech.create(
    model="tts-1",
    voice="alloy",
    input="...",
    stream=True
)

for chunk in response.iter_bytes():
    # play chunk
    pass

# Output formats: mp3, opus, aac, flac, wav, pcm
```

## Aithera integration (opcional)

Aithera V0.8.0 podría usar OpenAI TTS como fallback de ElevenLabs:

```python
# backend/app/voice/openai_voice.py
from openai import OpenAI

class OpenAIVoice:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    async def synthesize(self, text: str, voice: str = "alloy") -> bytes:
        response = self.client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        return response.content
```

## Realtime API (gpt-realtime-2)

OpenAI Realtime API combina STT + LLM + TTS en un solo WebSocket:

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()

async with client.realtime.connect(model="gpt-realtime-2") as conn:
    # Send audio chunks
    await conn.send_audio(audio_chunk)
    # Receive events
    async for event in conn:
        if event.type == "response.audio.delta":
            # play audio chunk
            pass
```

**TTFB**: ~200-500ms end-to-end.

## Pros y cons

| Pro | Con |
|---|---|
| ✅ Integrado con GPT-5.x | ❌ Menos natural que ElevenLabs |
| ✅ Streaming built-in | ❌ Sin voice cloning (julio 2026) |
| ✅ Pricing claro | ❌ Menos opciones de voice |
| ✅ Realtime API | |

## Cuándo elegir OpenAI TTS

- ✅ Si ya usas GPT-5.x para LLM (single vendor).
- ✅ Si necesitas Realtime API (voice + LLM + TTS unificado).
- ❌ Si quieres voice cloning (ElevenLabs).

## Para Aithera

V0.8.0: ElevenLabs primary, EdgeTTS fallback, OpenAI TTS no integrado aún.
V0.85+: considerar Realtime API.

## Referencias cruzadas

- [JWIKI-135 README.md](./README.md)
- [JWIKI-146 voice-pipelines-realtime.md](./voice-pipelines-realtime.md)
- [JWIKI-020 openai.md](../05_AI_PROVIDERS/openai.md)

## Fuentes

1. https://platform.openai.com/docs/guides/text-to-speech
2. https://platform.openai.com/docs/guides/realtime

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified