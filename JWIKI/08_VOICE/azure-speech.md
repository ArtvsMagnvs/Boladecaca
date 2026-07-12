# Azure Speech — Alternativa enterprise

## Resumen

**Azure Speech** (Microsoft) es alternativa enterprise con TTS + STT + translation. **NO integrado en Aithera V0.8.0**.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Servicios

| Servicio | Función | Pricing |
|---|---|---|
| **Speech to Text** | STT cloud | $1/hora audio |
| **Text to Speech** | TTS cloud (Neural voices) | $16/1M chars |
| **Speech Translation** | STT + translation | $2.5/hora audio |
| **Speaker Recognition** | Voice biometrics | $5/1000 trans |
| **Custom Neural Voice** | Voice cloning (preview) | enterprise |

## Voces Neural (400+)

- 100+ idiomas.
- Multilingual v2 voices (es-ES-ElviraNeural, en-US-JennyNeural, etc.).
- Custom Voice (preview): entrenar con samples propios.

## API

```python
import azure.cognitiveservices.speech as speechsdk

speech_config = speechsdk.SpeechConfig(
    subscription="...",
    region="eastus"
)
speech_config.speech_synthesis_voice_name = "es-ES-ElviraNeural"

synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
result = synthesizer.speak_text_async("Hola, ¿cómo estás?").get()

# result.audio_data = bytes
```

## SSML support (más completo que Google)

```xml
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-ES">
    <voice name="es-ES-ElviraNeural">
        <prosody rate="+10%" pitch="+5%">
            Hola, ¿cómo estás?
        </prosody>
    </voice>
</speak>
```

## Aithera integration (opcional)

```python
# backend/app/voice/azure_voice.py
import azure.cognitiveservices.speech as speechsdk

class AzureVoice:
    def __init__(self, subscription_key: str, region: str):
        self.config = speechsdk.SpeechConfig(
            subscription=subscription_key,
            region=region
        )
    
    async def synthesize(self, text: str, voice: str = "es-ES-ElviraNeural") -> bytes:
        self.config.speech_synthesis_voice_name = voice
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.config)
        result = synthesizer.speak_text_async(text).get()
        return result.audio_data
```

## Continuous Language Identification

Azure detecta automáticamente el idioma del audio:

```python
auto_config = speechsdk.AutoDetectSourceLanguageConfig(languages=["es-ES", "en-US", "fr-FR"])
```

## Para Aithera

NO integrado. Razones:
- Microsoft ecosystem (vs Aithera que es más open).
- Requiere Azure subscription.
- EdgeTTS es alternativa gratuita con voces similares.

## Referencias cruzadas

- [JWIKI-135 README.md](./README.md)
- [JWIKI-144 google-stt.md](./google-stt.md)

## Fuentes

1. https://azure.microsoft.com/en-us/services/cognitive-services/speech-services/
2. https://learn.microsoft.com/en-us/azure/ai-services/speech/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified