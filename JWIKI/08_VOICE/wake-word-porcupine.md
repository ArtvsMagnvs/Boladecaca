# Wake Word — Porcupine y openWakeWord

## Resumen

**Wake word** detection (e.g., "Hey Siri", "OK Google") permite a un agente activarse solo cuando el usuario lo invoca. Aithera V0.8.0 **NO tiene wake word** (conversación continua = siempre listening). V0.85+ podría añadir.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Opciones

| Engine | Costo | Privacidad | Latency | Aithera |
|---|---|---|---|---|
| **Porcupine** (Picovoice) | $0 (10 wake words/mes) | cloud (default) | < 100ms | ⏳ |
| **openWakeWord** | gratis | local | < 100ms | ⏳ |
| **Picovoice Cheetah** | enterprise | local | < 50ms | ❌ |
| **Snowboy** (deprecated) | - | local | - | ❌ |
| **Alexa Wake Word** | - | cloud | - | ❌ |

## Porcupine (Picovoice)

```python
import pvporcupine

porcupine = pvporcupine.create(
    keywords=["jarvis", "alexa"],
    access_key="..."
)

# Stream audio from mic
import pvrecorder
recorder = pvrecorder.PvRecorder(
    device_index=-1,
    frame_length=porcupine.frame_length
)
recorder.start()

while True:
    pcm = recorder.read()
    keyword_index = porcupine.process(pcm)
    if keyword_index >= 0:
        print(f"Wake word detected: {porcupine.keywords[keyword_index]}")
        # Trigger Aithera
```

**Custom wake word**: Picovoice permite entrenar tu propio wake word (con samples). Aithera podría tener "Hey Aithera" custom.

## openWakeWord

```python
from openwakeword.model import Model

model = Model(
    wakeword_models=["jarvis"],
    inference_framework="onnx"
)

# Stream audio
import pyaudio
pa = pyaudio.PyAudio()
stream = pa.open(rate=16000, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=1280)

while True:
    audio = stream.read(1280)
    prediction = model.predict(audio)
    if prediction["jarvis"] > 0.5:
        # Wake word detected
        break
```

**Pros**: gratis, local, open source.
**Cons**: requiere más compute que Porcupine.

## Latency budget

- VAD → STT → LLM → TTS pipeline: target < 2s TTFB.
- Wake word: < 100ms (local, no LLM).
- Total reaction time: < 2.1s (aceptable para conversational).

## Privacy concerns

- ⚠️ **Always listening**: privacy concern.
- ✅ **Aithera V0.8.0 actual**: opt-out en settings.
- ✅ **V0.85+ con wake word**: solo escucha después del wake word (más privacy).

## Para Aithera

- ❌ V0.8.0: NO wake word (conversación continua).
- ⏳ V0.85+: añadir wake word opcional ("Hey Aithera") con openWakeWord (gratis, local) o Porcupine (custom voice).

## Referencias cruzadas

- [JWIKI-135 README.md](./README.md)
- [JWIKI-146 voice-pipelines-realtime.md](./voice-pipelines-realtime.md)

## Fuentes

1. https://picovoice.ai/docs/porcupine/
2. https://github.com/dscripka/openWakeWord
3. https://github.com/Picovoice/porcupine

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified