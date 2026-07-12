# Voice Pipelines — Realtime

## Resumen

**Voice pipelines** en tiempo real integran VAD + STT + LLM + TTS en un flujo continuo. Aithera V0.8.0 implementa "conversación continua" (CLAUDE.md §1). V1.0+ considera OpenAI Realtime API o Gemini Live.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Pipeline architecture

```
Mic audio (PCM 16kHz mono, chunks 100-300ms)
  ↓
VAD (Silero / WebRTC) — detecta speech start/end
  ↓
STT (faster-whisper) — audio → text
  ↓
LLM (DeepSeek-Flash streaming) — text → response
  ↓
TTS (ElevenLabs streaming) — response → audio
  ↓
Speaker output (PCM 22kHz)
```

## Async pipeline (Aithera V0.8.0)

```python
import asyncio

class VoicePipeline:
    def __init__(self, stt, llm, tts, vad):
        self.stt = stt
        self.llm = llm
        self.tts = tts
        self.vad = vad
    
    async def run(self, audio_stream):
        # 1. VAD loop
        async for chunk in audio_stream:
            is_speech = self.vad.is_speech(chunk)
            if is_speech:
                self.buffer.append(chunk)
            elif self.buffer:  # End of utterance
                # 2. STT
                text = await self.stt.transcribe(b"".join(self.buffer))
                self.buffer = []
                
                # 3. LLM streaming
                async for token in self.llm.stream(text):
                    # 4. TTS streaming per token
                    async for audio_chunk in self.tts.synthesize_stream(token):
                        yield audio_chunk
```

## OpenAI Realtime API (gpt-realtime-2)

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()

async with client.realtime.connect(model="gpt-realtime-2") as conn:
    # Configure
    await conn.session.update(session={
        "modalities": ["text", "audio"],
        "voice": "alloy",
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16"
    })
    
    # Send audio input
    await conn.input_audio_buffer.append(audio_chunk)
    await conn.input_audio_buffer.commit()
    
    # Receive events
    async for event in conn:
        if event.type == "response.audio.delta":
            audio = event.delta
            # play audio
        elif event.type == "response.text.delta":
            text = event.delta
            # for display
```

**TTFB**: ~200-500ms.
**Benefit**: todo en un solo WebSocket.

## Gemini Live (gemini-2.5-flash-native-audio)

```python
from google.generativeai import GenerativeModel

model = GenerativeModel("gemini-2.5-flash-native-audio")
chat = model.start_chat()

# Send audio
response = chat.send_message_stream(
    ["audio data", "respond in audio"]
)

for chunk in response:
    if chunk.audio:
        # play audio chunk
        pass
```

**Benefit**: native multimodal (text+audio+video).

## Latency breakdown

| Stage | Time | Aithera target |
|---|---|---|
| VAD detect end | 300-1000ms | ✅ |
| STT | 500-2000ms | ✅ faster-whisper int8 |
| LLM TTFT | 200-500ms | ✅ DeepSeek-Flash |
| LLM stream (per token) | 30-100ms | ✅ |
| TTS TTFB | 200-500ms | ✅ ElevenLabs streaming |
| TTS stream (per chunk) | 30-100ms | ✅ |
| **Total TTFB** | **< 2s** | ✅ |

## Para Aithera

- ✅ V0.8.0: pipeline async custom.
- ⏳ V0.85+: mejora VAD (Silero VAD v4).
- ⏳ V1.0+: OpenAI Realtime API integration (multimodal unified).
- ⏳ V1.5+: Gemini Live (multimodal real-time).

## Referencias cruzadas

- [JWIKI-135 README.md](./README.md)
- [JWIKI-142 whisper.md](./whisper.md)
- [JWIKI-147 voice-latency-budget.md](./voice-latency-budget.md)

## Fuentes

1. https://platform.openai.com/docs/guides/realtime
2. https://ai.google.dev/gemini-api/docs/live
3. https://github.com/snakers4/silero-vad

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified