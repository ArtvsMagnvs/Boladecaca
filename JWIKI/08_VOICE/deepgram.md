# Deepgram — STT cloud

## Resumen

**Deepgram** es STT cloud enterprise con **streaming** y **diarization** (speaker ID). **NO integrado en Aithera V0.8.0** (usa faster-whisper local).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Características

- ✅ **Streaming**: TTFB < 300ms.
- ✅ **Diarization**: identifica speakers (Speaker 1, Speaker 2, ...).
- ✅ **36+ idiomas**.
- ✅ **Nova-3 model**: alta accuracy.
- ✅ **API simple**.

## Modelos

| Modelo | Accuracy | Latency | Diarization | Pricing |
|---|---|---|---|---|
| Nova-3 | ⭐⭐⭐⭐⭐ | < 300ms | ✅ | $0.0043/min |
| Nova-2 | ⭐⭐⭐⭐ | < 300ms | ✅ | $0.0043/min |
| Whisper Cloud | ⭐⭐⭐⭐ | medio | ❌ | $0.006/min |

## API

```python
from deepgram import Deepgram

dg = Deepgram("YOUR_API_KEY")

# File transcription
with open("audio.mp3", "rb") as f:
    source = {"buffer": f.read(), "mimetype": "audio/mp3"}
    response = await dg.transcription.prerecorded(
        source,
        {"punctuate": True, "language": "es", "diarize": True}
    )
    print(response["results"]["channels"][0]["alternatives"][0]["transcript"])

# Streaming (WebSocket)
dg_connection = await dg.transcription.live({"language": "es", "diarize": True})
async def on_message(result):
    print(result["channel"]["alternatives"][0]["transcript"])
dg_connection.on("Results", on_message)
```

## Aithera integration (opcional)

```python
# backend/app/voice/deepgram_stt.py
from deepgram import Deepgram

class DeepgramSTT:
    def __init__(self, api_key: str):
        self.dg = Deepgram(api_key)
    
    async def transcribe(self, audio_path: str, language: str = "es") -> dict:
        with open(audio_path, "rb") as f:
            source = {"buffer": f.read(), "mimetype": "audio/mp3"}
        response = await self.dg.transcription.prerecorded(
            source, {"language": language, "diarize": True}
        )
        words = response["results"]["channels"][0]["alternatives"][0]["words"]
        return {
            "text": " ".join([w["word"] for w in words]),
            "language": language,
            "speakers": self._extract_speakers(words)
        }
```

## Streaming STT

Deepgram es **streaming-first**:

```python
dg_connection = await dg.transcription.live({"language": "es", "interim_results": True})

async def send_audio():
    with open("stream.wav", "rb") as f:
        while chunk := f.read(4096):
            await dg_connection.send(chunk)

async def on_result(result):
    if result["is_final"]:
        print("Final:", result["channel"]["alternatives"][0]["transcript"])
    else:
        print("Interim:", result["channel"]["alternatives"][0]["transcript"])

dg_connection.on("Results", on_result)
await send_audio()
```

## Pricing

| Plan | $/mes | Minutos |
|---|---|---|
| Pay-as-you-go | $0 | según uso |
| Growth | $0 | 1.2K minutos gratis |
| Enterprise | custom | custom |

## Cuándo elegir Deepgram

- ✅ **Streaming real-time** (VAD + STT en uno).
- ✅ **Diarization** (multi-speaker).
- ✅ **Production-grade** (SLA 99.9%).
- ❌ Si quieres local (usar faster-whisper).

## Para Aithera

NO integrado. Razones:
- faster-whisper local es suficiente para single-user.
- Diarization es nice-to-have, no core.
- Costo ($0.0043/min) aceptable pero innecesario.

## Referencias cruzadas

- [JWIKI-135 README.md](./README.md)
- [JWIKI-142 whisper.md](./whisper.md)

## Fuentes

1. https://deepgram.com/
2. https://developers.deepgram.com/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified