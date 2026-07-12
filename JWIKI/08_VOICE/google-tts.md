# Google Cloud TTS — Alternativa cloud

## Resumen

**Google Cloud TTS** (WaveNet + Neural2 + Studio voices) es alternativa enterprise. **NO integrado en Aithera V0.8.0** (ElevenLabs + EdgeTTS son los TTS).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Modelos

| Voice type | Calidad | Latency | Pricing |
|---|---|---|---|
| **Standard** | ⭐⭐⭐ | baja | $4/1M chars (free tier 4M/mes) |
| **WaveNet** | ⭐⭐⭐⭐ | media | $16/1M chars |
| **Neural2** | ⭐⭐⭐⭐⭐ | media | $16/1M chars |
| **Studio** | ⭐⭐⭐⭐⭐ | alta (cached) | $160/1M chars |
| **Journey** | ⭐⭐⭐⭐⭐ | media | $30/1M chars (preview) |

## Voces (380+)

Google tiene la mayor librería:
- 50+ idiomas.
- Voces regionales (en-US-Wavenet-A, es-ES-Neural2-A, etc.).
- Custom Voice (V0.85+): subir samples para clonar.

## API

```python
from google.cloud import texttospeech

client = texttospeech.TextToSpeechClient()

response = client.synthesize_speech(
    input=texttospeech.SynthesisInput(text="Hola"),
    voice=texttospeech.VoiceSelectionParams(
        language_code="es-ES",
        name="es-ES-Neural2-A"
    ),
    audio_config=texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
)

# response.audio_content = bytes MP3
```

## SSML support

Google TTS soporta **SSML** (Speech Synthesis Markup Language) para control fino:

```xml
<speak>
    <prosody rate="slow" pitch="+2st">Hola, ¿cómo estás?</prosody>
    <break time="500ms"/>
    <emphasis level="strong">Importante</emphasis>
</speak>
```

## Aithera integration (opcional)

```python
# backend/app/voice/google_voice.py
from google.cloud import texttospeech

class GoogleVoice:
    def __init__(self, credentials_path: str):
        self.client = texttospeech.TextToSpeechClient.from_service_account_file(credentials_path)
    
    async def synthesize(self, text: str, voice_name: str = "es-ES-Neural2-A") -> bytes:
        response = self.client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=text),
            voice=texttospeech.VoiceSelectionParams(
                language_code="es-ES",
                name=voice_name
            ),
            audio_config=texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
        )
        return response.audio_content
```

## Para Aithera

NO integrado. Razones:
- ElevenLabs tiene mejor calidad.
- EdgeTTS es gratis (oficial Microsoft).
- Google requiere service account JSON (más fricción).

## Referencias cruzadas

- [JWIKI-135 README.md](./README.md)
- [JWIKI-149 multilingual-tts.md](./multilingual-tts.md)

## Fuentes

1. https://cloud.google.com/text-to-speech
2. https://cloud.google.com/text-to-speech/docs

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified