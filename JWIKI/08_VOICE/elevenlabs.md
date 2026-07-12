# ElevenLabs — TTS cloud en uso en Aithera

## Resumen

**ElevenLabs** es el TTS primario de Aithera V0.8.0 (CLAUDE.md §1). Mejor calidad de voz sintética del mercado, voice cloning, 29+ idiomas.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Por qué ElevenLabs

- ✅ **Calidad top**: voces muy naturales (multilingual v2).
- ✅ **Voice cloning**: clonar tu propia voz con 1-3 min de audio.
- ✅ **API streaming**: TTFB < 300ms.
- ✅ **29+ idiomas**: multilingual.

## Pricing

| Plan | $/mes | Characters |
|---|---|---|
| Free | $0 | 10K |
| Starter | $5 | 30K |
| Creator | $22 | 100K |
| Pro | $99 | 500K |
| Scale | $330 | 2M |

## API

```python
from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key="...")

# Síntesis básica
audio = client.generate(
    text="Hola, ¿cómo estás?",
    voice="Rachel",
    model="eleven_multilingual_v2"
)

# Streaming (TTFB bajo)
audio_stream = client.generate(
    text="...",
    voice="Rachel",
    model="eleven_multilingual_v2",
    stream=True
)
for chunk in audio_stream:
    if chunk is not None:
        # play chunk
        pass

# Voice cloning
new_voice = client.clone(
    name="My Voice",
    files=["sample1.mp3", "sample2.mp3"]
)
```

## Aithera integration

```python
# backend/app/voice/elevenlabs_voice.py
from elevenlabs.client import ElevenLabs

class ElevenLabsVoice:
    def __init__(self, api_key: str):
        self.client = ElevenLabs(api_key=api_key)
        self.default_voice = "Rachel"
        self.default_model = "eleven_multilingual_v2"
    
    async def synthesize(self, text: str, voice: str = None) -> bytes:
        audio = self.client.generate(
            text=text,
            voice=voice or self.default_voice,
            model=self.default_model,
            stream=False
        )
        return audio  # bytes MP3
```

## Voces populares

- **Rachel**: female, English, calm.
- **Adam**: male, English, deep.
- **Antoni**: male, English, warm.
- **Josh**: male, English, young.
- **Bella**: female, English, friendly.

Para español: configurar voice + model multilingual v2.

## Voice cloning (V0.85+)

```python
# Subir samples de audio (3+ minutos)
voice = client.clone(
    name="Mi Voz Aithera",
    files=["sample1.wav", "sample2.wav", "sample3.wav"],
    description="Mi voz personal para Aithera"
)
# Usar en generate
audio = client.generate(text="...", voice=voice.voice_id)
```

## Latency

- TTFB: ~200-500ms con streaming.
- Real-time: ✅ adecuado para conversación.

## Para Aithera

- ✅ V0.8.0: ElevenLabs primary.
- ⏳ V0.85+: voice cloning para personalización.
- ⏳ V1.0+: realtime mode con OpenAI gpt-realtime-2 o Gemini Live.

## Pitfalls

- ❌ **No usar voice names sin verificar**: API puede cambiar.
- ❌ **No exceder rate limits**: 100 RPS en Scale.
- ❌ **No hardcodear API key**: usar config DPAPI (V0.8).

## Referencias cruzadas

- [JWIKI-135 README.md](./README.md)
- [JWIKI-148 voice-cloning.md](./voice-cloning.md)

## Fuentes

1. https://elevenlabs.io/
2. https://docs.elevenlabs.io/
3. CLAUDE.md §1

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified