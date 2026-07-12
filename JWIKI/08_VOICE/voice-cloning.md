# Voice Cloning — ElevenLabs y Coqui XTTS

## Resumen

**Voice cloning** permite replicar la voz de una persona con pocos minutos de audio. Aithera V0.85+ podría implementar para personalizar TTS.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Proveedores

| Provider | Min audio | Quality | Cost | Aithera |
|---|---|---|---|---|
| **ElevenLabs** | 1-3 min | ⭐⭐⭐⭐⭐ | $22+/mes | ⏳ V0.85+ |
| **Coqui XTTS v2** | 6 sec | ⭐⭐⭐⭐ | gratis (local) | ⏳ |
| **OpenAI Voice Engine** | 15+ min (preview) | ⭐⭐⭐⭐⭐ | enterprise | ❌ |
| **Play.ht** | 30 sec | ⭐⭐⭐⭐ | $30+/mes | ❌ |

## ElevenLabs voice cloning

```python
from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key="...")

# Subir samples
new_voice = client.clone(
    name="Mi Voz Aithera",
    files=["sample1.mp3", "sample2.mp3", "sample3.mp3"],  # 1-3 min total
    description="Voz personal del user de Aithera"
)

# Usar
audio = client.generate(
    text="Hola, esto es mi voz clonada.",
    voice=new_voice.voice_id
)
```

**Pros**: top quality, fast.
**Cons**: requiere samples de calidad, costo mensual.

## Coqui XTTS v2 (local, open source)

```python
from TTS.api import TTS

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)

# Voice cloning con 6+ sec
tts.tts_to_file(
    text="Hola, esto es mi voz clonada con XTTS.",
    file_path="output.wav",
    speaker_wav="mi_voz_sample.wav",  # 6+ sec sample
    language="es"
)
```

**Pros**: gratis, local, 6 sec minimum.
**Cons**: setup complejo, GPU recommended.

## Para Aithera

V0.85+ plan:
1. **Setup wizard** en Settings: "Clonar mi voz" → upload 1-3 min audio.
2. **TTS principal** cambia de "Rachel" (default ElevenLabs) a la voz clonada.
3. **Storage** del audio sample cifrado con DPAPI (CLAUDE.md §1).
4. **Opcional**: usar XTTS v2 local (gratis) o ElevenLabs (cloud).

## Privacy

- ⚠️ **Voice cloning es sensitive**: requiere consentimiento explícito.
- ⚠️ **No usar voz de terceros** sin permiso.
- ✅ Aithera: solo el user puede clonar SU propia voz.

## References

- [JWIKI-136 elevenlabs.md](./elevenlabs.md)
- [JWIKI-141 coqui-tts.md](./coqui-tts.md)

## Fuentes

1. https://elevenlabs.io/voice-cloning
2. https://docs.coqui.ai/

## Nivel de confianza

**85%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified