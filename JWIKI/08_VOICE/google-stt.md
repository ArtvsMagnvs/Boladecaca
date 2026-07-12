# Google STT — STT cloud alternativa

## Resumen

**Google Cloud Speech-to-Text** es STT cloud enterprise con 125+ idiomas. **NO integrado en Aithera V0.8.0** (usa faster-whisper).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Características

- ✅ **125+ idiomas**.
- ✅ **Diarization** (speaker ID).
- ✅ **Word-level confidence**.
- ✅ **Auto punctuation**.
- ✅ **Domain models** (medical, legal, etc.).
- ❌ Cloud-only (no local).
- ❌ Caro para alto volumen.

## Modelos

| Modelo | Calidad | Pricing |
|---|---|---|
| `latest_long` | ⭐⭐⭐⭐⭐ | $0.006/15s |
| `phone_call` | ⭐⭐⭐⭐ | $0.006/15s |
| `command_and_search` | ⭐⭐⭐ | $0.006/15s |
| `medical_conversation` | ⭐⭐⭐⭐⭐ | $0.006/15s |

## API

```python
from google.cloud import speech

client = speech.SpeechClient()

with open("audio.wav", "rb") as f:
    content = f.read()

audio = speech.RecognitionAudio(content=content)
config = speech.RecognitionConfig(
    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz=16000,
    language_code="es-ES",
    enable_word_time_offsets=True,
    enable_word_confidence=True,
    enable_speaker_diarization=True,
    diarization_speaker_count=2
)

response = client.recognize(config=config, audio=audio)

for result in response.results:
    alternative = result.alternatives[0]
    print(f"Transcript: {alternative.transcript}")
    print(f"Confidence: {alternative.confidence}")
    for word_info in alternative.words_info:
        print(f"Word: {word_info.word}, Speaker: {word_info.speaker_tag}")
```

## Aithera integration (opcional)

```python
# backend/app/voice/google_stt.py
from google.cloud import speech

class GoogleSTT:
    def __init__(self, credentials_path: str):
        self.client = speech.SpeechClient.from_service_account_file(credentials_path)
    
    async def transcribe(self, audio_path: str, language: str = "es-ES") -> dict:
        with open(audio_path, "rb") as f:
            content = f.read()
        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=language,
            enable_word_time_offsets=True,
            enable_speaker_diarization=True
        )
        response = self.client.recognize(config=config, audio=audio)
        # ...
```

## Para Aithera

NO integrado. Razones:
- faster-whisper local es suficiente y gratis.
- Diarization no es core.
- Google requiere service account.

## Referencias cruzadas

- [JWIKI-135 README.md](./README.md)
- [JWIKI-142 whisper.md](./whisper.md)
- [JWIKI-143 deepgram.md](./deepgram.md)

## Fuentes

1. https://cloud.google.com/speech-to-text
2. https://cloud.google.com/speech-to-text/docs

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified