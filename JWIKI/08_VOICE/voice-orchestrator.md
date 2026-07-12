# Voice Orchestrator — Patrón futuro

## Resumen

**Voice orchestrator** es un componente de Aithera V1.0+ que orquesta todos los engines de voice (TTS, STT, VAD, wake word, voice cloning) con state management y recovery. Inspirado en OpenAI Realtime API + Gemini Live.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Arquitectura propuesta (V1.0+)

```
User voice input (audio stream)
  ↓
Wake Word Detector (Porcupine)
  ↓
VAD (Silero VAD v4)
  ↓
Streaming STT (Deepgram o Whisper streaming)
  ↓
Intent Classifier (LLM, modelo rápido)
  ↓
[Si simple chat] → LLM directo
  ↓
[Si tool use] → Agent Loop (Orchestrator V1.0)
  ↓
Streaming TTS (ElevenLabs o Realtime API)
  ↓
Audio output al speaker
```

## State management

```python
class VoiceSession:
    conversation_id: str
    user_id: str
    voice_id: str  # ElevenLabs voice ID
    language: str
    started_at: datetime
    
    # VAD state
    is_speaking: bool
    silence_duration_ms: int
    
    # STT state
    partial_transcript: str
    final_transcript: str
    
    # LLM state
    messages: list[dict]
    
    # TTS state
    current_audio_chunk: bytes
    tts_queue: asyncio.Queue
```

## Recovery from failures

```python
class RobustVoiceOrchestrator:
    async def run(self, audio_stream):
        try:
            async for audio_response in self.pipeline(audio_stream):
                yield audio_response
        except STTError:
            # Fallback: pedir al user que repita
            yield await self.tts.synthesize("No te he oído, ¿puedes repetir?")
        except LLMError:
            # Fallback: respuesta genérica
            yield await self.tts.synthesize("Lo siento, ha habido un error. ¿Puedes reformular?")
        except TTSError:
            # Fallback: texto sin audio
            yield f"[TEXT_ONLY] {response_text}"
```

## Multi-voice (persona switching)

```python
class MultiVoiceOrchestrator:
    def __init__(self):
        self.voices = {
            "asistente": "Rachel",  # ElevenLabs voice
            "narrador": "Adam",
            "alerta": "Antoni"  # voice más grave para alertas
        }
    
    async def synthesize_with_persona(self, text, persona):
        voice = self.voices.get(persona, "Rachel")
        return await self.tts.synthesize(text, voice=voice)
```

## Interruption handling (barge-in)

Aithera V0.8.0 conversación continua: el user puede interrumpir al agent mientras habla.

```python
class InterruptibleOrchestrator:
    def __init__(self, tts, vad):
        self.tts = tts
        self.vad = vad
        self.is_speaking = False
    
    async def run_synthesis(self, text):
        self.is_speaking = True
        try:
            async for audio_chunk in self.tts.synthesize_stream(text):
                if await self.vad.detect_speech():  # user interrupted
                    await self.tts.stop()
                    break
                yield audio_chunk
        finally:
            self.is_speaking = False
```

## Routing por capabilities

```python
class CapabilityAwareOrchestrator:
    async def select_stt(self, audio):
        # Si user en settings prefiere local → faster-whisper
        if settings.prefer_local_stt:
            return await self.local_stt.transcribe(audio)
        # Sino → Deepgram (más accuracy)
        return await self.deepgram_stt.transcribe(audio)
    
    async def select_tts(self, text):
        # Si voice cloning habilitado → usar voz clonada
        if settings.cloned_voice_id:
            return await self.elevenlabs.synthesize(text, voice=settings.cloned_voice_id)
        # Sino → default voice
        return await self.elevenlabs.synthesize(text, voice="Rachel")
```

## Para Aithera

- ⏳ V1.0+: implementar VoiceOrchestrator con state management.
- ⏳ V1.5+: multi-voice, barge-in, capability routing.
- ⏳ V2.0+: emotional TTS (variaciones de tono según contexto).

## Referencias cruzadas

- [JWIKI-135 README.md](./README.md)
- [JWIKI-146 voice-pipelines-realtime.md](./voice-pipelines-realtime.md)
- [JWIKI-148 voice-cloning.md](./voice-cloning.md)
- [JWIKI-150 multi-agent-hierarchical.md](../06_AGENTS/multi-agent-hierarchical.md) — orchestrator pattern

## Fuentes

1. https://platform.openai.com/docs/guides/realtime
2. https://ai.google.dev/gemini-api/docs/live
3. Plan Maestro 2026 §11 (V1.0 Orchestrator)

## Nivel de confianza

**80%** — diseño conceptual, implementación futura.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified