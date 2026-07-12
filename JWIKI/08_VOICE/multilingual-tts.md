# Multilingual TTS — Multi-idioma

## Resumen

**Multilingual TTS** es la capacidad de un TTS engine de hablar múltiples idiomas con la misma voz (o voces nativas). Aithera V0.8.0 soporta via ElevenLabs multilingual_v2 + EdgeTTS.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Engines multilingües

| Engine | Idiomas | Calidad cross-lang | Aithera |
|---|---|---|---|
| **ElevenLabs multilingual_v2** | 29 | ⭐⭐⭐⭐⭐ | ✅ primary |
| **OpenAI tts-1** | 50+ | ⭐⭐⭐ | ⏳ |
| **EdgeTTS** | 100+ | ⭐⭐⭐ | ✅ fallback |
| **Google Cloud TTS** | 50+ | ⭐⭐⭐⭐ | ⏳ |
| **ElevenLabs multilingual_v1** | 9 | ⭐⭐⭐⭐ | deprecated |
| **GPT-4o realtime TTS** | 50+ | ⭐⭐⭐⭐⭐ | ⏳ V1.0+ |

## ElevenLabs multilingual_v2

```python
from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key="...")

# Mismo voice "Rachel" habla español manteniendo acento
audio_es = client.generate(
    text="Hola, ¿cómo estás?",
    voice="Rachel",
    model="eleven_multilingual_v2",
    voice_settings={
        "stability": 0.5,
        "similarity_boost": 0.8
    }
)

# Mismo voice habla inglés
audio_en = client.generate(
    text="Hello, how are you?",
    voice="Rachel",
    model="eleven_multilingual_v2"
)
```

## EdgeTTS

```python
import edge_tts

# Voces nativas por idioma (mejor que cross-lang)
communicate = edge_tts.Communicate(
    "Hola, ¿cómo estás?",
    "es-ES-ElviraNeural"  # voz nativa española
)
await communicate.save("output.mp3")

# Inglés
communicate = edge_tts.Communicate(
    "Hello, how are you?",
    "en-US-JennyNeural"  # voz nativa inglesa
)
```

## Idiomas soportados (top 10)

| Idioma | ElevenLabs v2 | EdgeTTS | Google |
|---|---|---|---|
| English | ✅ native | ✅ 50+ voices | ✅ |
| Spanish | ✅ cross-lang | ✅ Elvira, etc. | ✅ |
| French | ✅ cross-lang | ✅ Denise, etc. | ✅ |
| German | ✅ cross-lang | ✅ Katja, etc. | ✅ |
| Italian | ✅ cross-lang | ✅ Elsa, etc. | ✅ |
| Portuguese | ✅ cross-lang | ✅ Francisca, etc. | ✅ |
| Chinese | ✅ cross-lang | ✅ Xiaoxiao, etc. | ✅ |
| Japanese | ✅ cross-lang | ✅ Nanami, etc. | ✅ |
| Korean | ✅ cross-lang | ✅ Sun-Hi, etc. | ✅ |
| Russian | ✅ cross-lang | ✅ Svetlana, etc. | ✅ |

## Strategy Aithera

```python
# Detectar idioma del user
detected_lang = detect_language(user_text)  # "es", "en", etc.

# Routing por idioma
if detected_lang in ["es", "en", "fr", "de", "it", "pt"]:
    # Idiomas principales: ElevenLabs multilingual_v2
    audio = elevenlabs.generate(text, voice="Rachel", model="multilingual_v2")
elif detected_lang in supported_languages:
    # Idiomas secundarios: EdgeTTS con voz nativa
    audio = edge_tts.generate(text, voice=native_voice)
else:
    # Idioma no soportado: fallback a inglés
    translated = await llm.translate(text, target="en")
    audio = elevenlabs.generate(translated, voice="Rachel")
```

## Aithera V0.85+

- ✅ **Auto-detect language** del user text.
- ✅ **Per-user voice preference**: cada user puede elegir su voz preferida.
- ✅ **Voice cloning** opcional (ElevenLabs o XTTS local).

## Referencias cruzadas

- [JWIKI-136 elevenlabs.md](./elevenlabs.md)
- [JWIKI-137 openai-tts.md](./openai-tts.md)
- [JWIKI-138 google-tts.md](./google-tts.md)

## Fuentes

1. https://elevenlabs.io/languages
2. https://github.com/rany2/edge-tts
3. https://cloud.google.com/text-to-speech/docs/voices

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified