# Coqui TTS — Open source TTS

## Resumen

**Coqui TTS** (fork de Mozilla TTS) es la librería open source más madura para TTS de alta calidad. **NO integrado en Aithera V0.8.0** (ElevenLabs + EdgeTTS + Kokoro son los TTS).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Características

- ✅ **Open source** (Mozilla Public License 2.0).
- ✅ **Modelos preentrenados** (VITS, Tacotron, etc.).
- ✅ **Multi-speaker** (clonar con few samples).
- ✅ **20+ idiomas**.
- ✅ **Local** (sin cloud).
- ❌ **Setup complejo** (Python env, models download).
- ❌ **GPU recommended** para inferencia rápida.

## Modelos

- **VITS** (end-to-end, ⭐⭐⭐⭐⭐).
- **Tacotron 2** (classic, ⭐⭐⭐⭐).
- **Glow-TTS** (flow-based, ⭐⭐⭐⭐).
- **XTTS v2** (multilingual, ⭐⭐⭐⭐⭐, ⭐⭐⭐⭐ voice cloning).

## Setup

```bash
pip install TTS
# Descarga modelos automáticamente
```

## API

```python
from TTS.api import TTS

# Listar modelos disponibles
print(TTS.list_models())

# Cargar modelo
tts = TTS(model_name="tts_models/en/ljspeech/vits", progress_bar=False)

# Síntesis
tts.tts_to_file(text="Hello, world!", file_path="output.wav")
```

## Voice cloning con XTTS v2

```python
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)
tts.tts_to_file(
    text="Hola, esto es un test de voice cloning.",
    file_path="output_cloned.wav",
    speaker_wav="reference_voice.wav",  # 6+ seconds sample
    language="es"
)
```

## Aithera integration (opcional)

```python
# backend/app/voice/coqui_voice.py
from TTS.api import TTS

class CoquiVoice:
    def __init__(self, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2", gpu: bool = False):
        self.tts = TTS(model_name, gpu=gpu)
    
    async def synthesize(self, text: str, language: str = "es", speaker_wav: str = None) -> bytes:
        output_path = f"/tmp/coqui_{hash(text)}.wav"
        if speaker_wav:
            self.tts.tts_to_file(text=text, file_path=output_path, speaker_wav=speaker_wav, language=language)
        else:
            self.tts.tts_to_file(text=text, file_path=output_path)
        with open(output_path, "rb") as f:
            return f.read()
```

## Pros y cons

| Pro | Con |
|---|---|
| ✅ Open source | ❌ Setup complejo |
| ✅ Voice cloning | ❌ GPU recommended |
| ✅ Multi-speaker | ❌ Modelos grandes (1-2GB) |
| ✅ Local | ❌ Inferencia lenta en CPU |

## Para Aithera

NO integrado. Razones:
- Kokoro (82M params) ya cubre el caso local TTS.
- XTTS v2 sería ideal para voice cloning, pero Aithera prefiere ElevenLabs (V0.85+).

## Referencias cruzadas

- [JWIKI-135 README.md](./README.md)
- [JWIKI-140 espeak.md](./espeak.md)
- [JWIKI-148 voice-cloning.md](./voice-cloning.md)

## Fuentes

1. https://github.com/coqui-ai/TTS
2. https://docs.coqui.ai/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified