# SOP — Añadir motor TTS/STT

## Cuándo
Integrar nuevo motor voice (e.g., Coqui TTS local).

## Pasos

1. **Crear voice class** en `backend/app/voice/`:
```python
class CoquiVoice:
    async def synthesize(self, text: str, language: str = "es") -> bytes:
        from TTS.api import TTS
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        # Generate audio
        ...
        return audio_bytes
```

2. **Añadir a `VoiceManager`**:
```python
self.engines["coqui"] = CoquiVoice()
```

3. **API**:
```python
@router.post("/api/voice/synthesize")
async def synthesize(text: str, engine: str = "coqui"):
    return await voice_manager.engines[engine].synthesize(text)
```

4. **Settings UI**: añadir option en dropdown.

## Referencias cruzadas

- [JWIKI-141 coqui-tts.md](../08_VOICE/coqui-tts.md)

---

*Estado: 🟢 verified*