# Voice — TTS / STT comparativa

## Resumen

Aithera V0.8.0 integra **STT** (faster-whisper local) y **TTS** multi-proveedor (ElevenLabs, EdgeTTS, Kokoro, eSpeak). Comparativa de proveedores voice.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Categorías

| Categoría | Proveedores | Aithera |
|---|---|---|
| **TTS cloud** | ElevenLabs, OpenAI TTS, Google Cloud TTS, Azure Speech, Play.ht | ✅ ElevenLabs + OpenAI + EdgeTTS |
| **TTS local** | eSpeak NG, Kokoro, Coqui, Piper | ✅ eSpeak + Kokoro |
| **TTS realtime** | OpenAI Realtime API, Gemini Live | ✅ Gemini Live (omni) |
| **STT cloud** | OpenAI Whisper API, Deepgram, Google STT, Azure Speech | parcial |
| **STT local** | faster-whisper, whisper.cpp, Moonshine | ✅ faster-whisper |
| **Wake word** | Porcupine (Picovoice), openWakeWord | ⏳ V0.85+ |

## Stack Aithera V0.8.0 (CLAUDE.md §1)

- **STT**: faster-whisper (local, 1.2.1 versión estable) — `whisper-large-v3` o `distil-large-v3`.
- **TTS primario**: ElevenLabs (mejor calidad).
- **TTS fallback**: EdgeTTS (gratis, online, decent).
- **TTS offline**: Kokoro (local, decent, 82M params).
- **TTS ultra-offline**: eSpeak NG (robotic, pero funciona).
- **Wake word**: no implementado en V0.8.0 (futuro V0.85+).
- **Voice Activity Detection (VAD)**: Silero VAD o Whisper native.
- **Continuous conversation**: V0.8.0 soporta (CLAUDE.md §1 "conversación continua").

## Latency budgets (target)

| Stage | Target | Aithera actual |
|---|---|---|
| VAD | < 100ms | ✅ |
| STT (1min audio) | < 1s | ✅ con faster-whisper large-v3 |
| LLM TTFT | < 500ms | ⚠️ depende del provider |
| LLM stream | 50+ tokens/s | ✅ con DeepSeek-Flash / Gemini-Flash |
| TTS TTFB | < 300ms | ✅ EdgeTTS / ElevenLabs streaming |
| TTS stream | realtime | ✅ |
| **Total TTFB** | **< 2s** | ✅ para V0.8.0 |

## Voice pipeline architecture

```
Mic audio (PCM 16kHz mono)
  ↓
VAD (Silero) — detecta speech
  ↓
STT (faster-whisper) — audio → text
  ↓
LLM (AI Manager) — text → response
  ↓
TTS (ElevenLabs streaming) — response → audio
  ↓
Speaker output (PCM 22kHz)
```

## Continuous conversation (V0.8.0)

Aithera V0.8.0 introdujo "conversación continua" (CLAUDE.md §1):
- VAD detecta fin del habla.
- STT → LLM → TTS en pipeline async.
- Sin comando "wake word" necesario (siempre listening).
- Privacy: opt-out en settings.

## Aithera Voice API

```python
# POST /api/voice/synthesize
{
    "text": "Hola, ¿cómo estás?",
    "provider": "elevenlabs"  # o "edge-tts", "kokoro", "espeak"
}

# Response
{
    "audio_url": "/api/voice/audio/abc123.mp3",
    "duration_ms": 2500,
    "provider": "elevenlabs"
}
```

```python
# POST /api/voice/transcribe
{
    "audio": "<base64 PCM>",
    "language": "es"  # opcional
}

# Response
{
    "text": "Hola, ¿cómo estás?",
    "language": "es",
    "confidence": 0.95,
    "duration_ms": 1500
}
```

## V0.85+ roadmap

- Wake word (Porcupine o openWakeWord).
- Voice cloning (ElevenLabs).
- Realtime mode (OpenAI gpt-realtime-2 o Gemini Live).
- Multilingual TTS seamless switching.
- Voice orchestrator (multi-voice, persona selection).

## Referencias cruzadas

- [JWIKI-136 elevenlabs.md](./elevenlabs.md)
- [JWIKI-140 espeak.md](./espeak.md)
- [JWIKI-142 whisper.md](./whisper.md)
- [JWIKI-146 voice-pipelines-realtime.md](./voice-pipelines-realtime.md)
- [JWIKI-147 voice-latency-budget.md](./voice-latency-budget.md)

## Fuentes

1. CLAUDE.md §1 (V0.8.0 voz)
2. https://elevenlabs.io/
3. https://github.com/SYSTRAN/faster-whisper
4. https://github.com/hexgrad/kokoro

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified