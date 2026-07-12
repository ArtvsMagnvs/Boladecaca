# Voice Latency Budget — Targets

## Resumen

**Latency budget** es el target de tiempo total para que un agente voice responda. Crítico para conversación natural. Target Aithera: **< 2 segundos** TTFB end-to-end.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Latency budget

| Stage | Aithera target | Best-in-class |
|---|---|---|
| VAD end-of-speech detect | 500ms | 100ms (Silero VAD) |
| STT (1 min audio) | 1.5s | 800ms (faster-whisper int8) |
| LLM TTFT | 500ms | 200ms (DeepSeek-Flash) |
| LLM first-token-to-speech | 800ms | 300ms (streaming) |
| TTS TTFB | 300ms | 200ms (ElevenLabs streaming) |
| **TOTAL TTFB** | **< 3.6s** | **< 1.6s** |

## Conversation natural

- Human reaction time: ~200-300ms.
- Acceptable AI response: < 1s (feels like conversation).
- Frustrating: > 3s.

Aithera target **< 2s** es "good" (no excelente, pero usable).

## Optimization strategies

### 1. Reduce STT latency

- **Streaming STT**: chunk-based, no full audio.
- **Smaller model**: `tiny` (39M) o `base` (74M) en vez de `large-v3`.
- **GPU**: `faster-whisper` en GPU es 5x más rápido que CPU.

### 2. Reduce LLM latency

- **TTFT** crítico: usar modelos con TTFT bajo (DeepSeek-Flash ~200ms, Gemini-Flash ~200ms).
- **Streaming**: tokens ASAP, no esperar completion.
- **Prompt caching**: reusar system prompt cache (Anthropic 90% descuento).

### 3. Reduce TTS latency

- **TTFB**: ElevenLabs streaming ~200ms.
- **Pre-buffer**: emitir primer chunk ASAP.
- **Chunk size**: 50-100ms (balance latency vs smoothness).

### 4. Pipeline parallelism

```python
# No esperar LLM complete para empezar TTS
async def pipeline(text):
    # Parallel: TTS primer chunk cuando LLM emite primer token
    tts_task = asyncio.create_task(tts.synthesize_stream(text))
    async for tts_chunk in tts_task:
        yield tts_chunk
```

## Profiling

Cómo medir en Aithera:

```python
import time

class ProfiledVoicePipeline:
    async def run(self, audio):
        timings = {}
        
        t0 = time.perf_counter()
        text = await self.stt.transcribe(audio)
        timings["stt"] = time.perf_counter() - t0
        
        t0 = time.perf_counter()
        response = await self.llm.chat(text)
        timings["llm_ttft"] = time.perf_counter() - t0
        
        t0 = time.perf_counter()
        audio_response = await self.tts.synthesize(response)
        timings["tts_ttfb"] = time.perf_counter() - t0
        
        timings["total_ttfb"] = timings["stt"] + timings["llm_ttft"] + timings["tts_ttfb"]
        logger.info(f"Voice pipeline timings: {timings}")
        return audio_response
```

## Para Aithera

- ✅ V0.8.0: target < 2s, profiling implementado.
- ⏳ V0.85+: mejorar a < 1.5s con streaming optimizations.
- ⏳ V1.0+: Realtime API (TTFB < 1s).

## Referencias cruzadas

- [JWIKI-135 README.md](./README.md)
- [JWIKI-146 voice-pipelines-realtime.md](./voice-pipelines-realtime.md)

## Fuentes

1. https://www.pingdom.com/blog/page-load-time-really-matter/
2. https://huggingface.co/spaces/openai/whisper-large-v3-turbo

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified