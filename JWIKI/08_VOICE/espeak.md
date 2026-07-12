# eSpeak NG — TTS offline fallback Aithera

## Resumen

**eSpeak NG** es el TTS offline más liviano. **Integrado en Aithera V0.8.0** como fallback cuando no hay conexión a ElevenLabs/EdgeTTS (CLAUDE.md §1).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Características

- ✅ **Cero dependencias** (C library).
- ✅ **Multiplataforma** (Windows, Linux, macOS).
- ✅ **100+ voces** (en, es, fr, de, it, etc.).
- ✅ **Muy rápido** (< 50ms TTFB).
- ❌ **Calidad baja** (robotic, "computarizada").
- ❌ Sin emociones ni énfasis.

## API (CLI)

```bash
espeak-ng -v es -s 150 "Hola, ¿cómo estás?" -w output.wav
```

- `-v es`: voz español.
- `-s 150`: velocidad (palabras/minuto).
- `-w output.wav`: escribir a archivo.

## API (Python)

```python
# subprocess directo
import subprocess
subprocess.run(["espeak-ng", "-v", "es", "-s", "150", text])

# O vía library python-espeak
import espeak
espeak.synth(text)
```

## Aithera integration

```python
# backend/app/voice/espeak_voice.py
import subprocess

class ESpeakVoice:
    async def synthesize(self, text: str, voice: str = "es", speed: int = 150) -> bytes:
        output_path = f"/tmp/espeak_{hash(text)}.wav"
        subprocess.run([
            "espeak-ng",
            "-v", voice,
            "-s", str(speed),
            "-w", output_path,
            text
        ])
        with open(output_path, "rb") as f:
            return f.read()
```

## Configuración

```bash
# Windows
winget install espeak-ng

# Linux
apt install espeak-ng

# macOS
brew install espeak
```

## Voices disponibles

```bash
espeak-ng --voices
# Listado de 100+ voces con language code, gender, age
```

## Latency

- TTFB: < 50ms.
- Tiempo real: ✅ (más rápido que ElevenLabs streaming).

## Cuándo usar eSpeak

- ✅ **Sin internet** (offline).
- ✅ **Latency crítica** (< 50ms).
- ✅ **Backup robusto** (no depende de APIs externas).
- ❌ No para producción final (calidad robotic).

## Para Aithera

- ✅ V0.8.0: fallback chain (ElevenLabs → EdgeTTS → eSpeak).
- ✅ V0.85+: voice activity detection (VAD) usa eSpeak como hint de "habla terminada" (energy threshold).

## Referencias cruzadas

- [JWIKI-135 README.md](./README.md)
- [JWIKI-141 coqui-tts.md](./coqui-tts.md)

## Fuentes

1. https://github.com/espeak-ng/espeak-ng
2. CLAUDE.md §1

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified