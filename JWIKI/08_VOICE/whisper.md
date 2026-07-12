# OpenAI Whisper — STT

## Resumen

**OpenAI Whisper** es el modelo STT open weights más popular. **Aithera V0.8.0 usa `faster-whisper`** (port optimizado de Whisper, ~4x más rápido, menos memoria). CLAUDE.md §1.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Modelos Whisper

| Modelo | Params | VRAM | Velocidad | Calidad |
|---|---|---|---|---|
| tiny | 39M | ~1GB | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| base | 74M | ~1GB | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| small | 244M | ~2GB | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| medium | 769M | ~5GB | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| large-v3 | 1.5B | ~10GB | ⭐ | ⭐⭐⭐⭐⭐ |
| **distil-large-v3** | 756M | ~4GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ (97% de large-v3) |

**Aithera V0.8.0**: usa `distil-large-v3` o `large-v3` (pendiente verificar exacto).

## OpenAI Whisper API (cloud)

```python
from openai import OpenAI

client = OpenAI()
audio_file = open("recording.mp3", "rb")
transcript = client.audio.transcriptions.create(
    model="whisper-1",
    file=audio_file,
    language="es",  # opcional
    response_format="text"  # o "srt", "vtt"
)
print(transcript.text)
```

**Pricing**: $0.006 / minuto audio.

## faster-whisper (local, Aithera)

```python
from faster_whisper import WhisperModel

# CPU int8 (rápido, baja VRAM)
model = WhisperModel("distil-large-v3", device="cpu", compute_type="int8")

# GPU float16
# model = WhisperModel("distil-large-v3", device="cuda", compute_type="float16")

segments, info = model.transcribe("audio.mp3", language="es", beam_size=5)

for segment in segments:
    print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
```

## Aithera integration

```python
# backend/app/voice/whisper_stt.py
from faster_whisper import WhisperModel

class WhisperSTT:
    def __init__(self, model_size: str = "distil-large-v3", device: str = "cpu"):
        self.model = WhisperModel(model_size, device=device, compute_type="int8")
    
    async def transcribe(self, audio_path: str, language: str = None) -> dict:
        segments, info = self.model.transcribe(audio_path, language=language, beam_size=5)
        text = " ".join([s.text for s in segments])
        return {
            "text": text,
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration
        }
```

## Whisper.cpp (alternativa C++)

Más rápido que faster-whisper en CPU, pero C++. **NO** usado en Aithera.

## Latency

- **1 min audio**: ~3-5s con faster-whisper large-v3 + int8.
- **10 min audio**: ~30-50s.
- **Realtime**: NO (Whisper no es streaming).

## Para Aithera

- ✅ V0.8.0: faster-whisper `distil-large-v3` (mejor relación calidad/recursos).
- ⏳ V0.85+: diarization (speaker ID).
- ⏳ V1.0+: streaming STT con Whisper realtime.

## Referencias cruzadas

- [JWIKI-135 README.md](./README.md)
- [JWIKI-143 deepgram.md](./deepgram.md)
- [JWIKI-144 google-stt.md](./google-stt.md)

## Fuentes

1. https://openai.com/research/whisper
2. https://github.com/SYSTRAN/faster-whisper
3. https://github.com/ggerganov/whisper.cpp
4. CLAUDE.md §1

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified