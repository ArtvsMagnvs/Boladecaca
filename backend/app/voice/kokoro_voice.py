"""
Kokoro TTS — proveedor de voz LOCAL EN PROCESO (V0.83), sin Docker.

Usa la librería `kokoro` (KPipeline) directamente dentro del backend y DEVUELVE
bytes WAV al frontend (Aithera es web/Electron: el audio lo reproduce el
navegador, no el backend). Modelo ~330 MB: se descarga de HuggingFace la primera
vez (requiere internet una vez) y se cachea; después funciona offline. GPU si hay
CUDA, si no CPU. Referencia probada: Mark-XL `core/tts.py`.

Instalar: `pip install kokoro`  (torch ya viene por sentence-transformers).
Nota ES: algunas palabras en español pueden requerir `espeak-ng` en el sistema
como fallback de g2p (igual que en Mark-XL).
"""
from __future__ import annotations

import io
import threading
import wave
from typing import List, Optional

# Prefijo del voice_id de Kokoro v1.0 -> lang_code de KPipeline.
#   a=US English  b=UK English  e=Spanish  f=French  h=Hindi
#   i=Italian     j=Japanese    p=BR Portuguese      z=Mandarin
_KOKORO_LANG = {
    "a": "a", "b": "b", "e": "e", "f": "f",
    "h": "h", "i": "i", "j": "j", "p": "p", "z": "z",
}

# Lista curada (Kokoro no expone endpoint de voces en proceso). Español primero.
KOKORO_VOICES: List[dict] = [
    {"id": "ef_dora",    "name": "Dora (Español ♀)",   "lang": "es"},
    {"id": "em_alex",    "name": "Alex (Español ♂)",   "lang": "es"},
    {"id": "em_santa",   "name": "Santa (Español ♂)",  "lang": "es"},
    {"id": "af_heart",   "name": "Heart (EN-US ♀)",    "lang": "en"},
    {"id": "af_bella",   "name": "Bella (EN-US ♀)",    "lang": "en"},
    {"id": "am_adam",    "name": "Adam (EN-US ♂)",     "lang": "en"},
    {"id": "am_michael", "name": "Michael (EN-US ♂)",  "lang": "en"},
    {"id": "bf_emma",    "name": "Emma (EN-UK ♀)",     "lang": "en"},
    {"id": "bm_george",  "name": "George (EN-UK ♂)",   "lang": "en"},
]

_SAMPLE_RATE = 24000  # Kokoro genera 24 kHz mono


class KokoroVoice:
    """TTS de Kokoro en proceso. Cachea una KPipeline por idioma."""

    def __init__(self) -> None:
        self._pipelines: dict = {}
        self._lock = threading.Lock()      # KPipeline no es thread-safe
        self._device: Optional[str] = None
        self.last_error: Optional[str] = None

    def is_available(self) -> bool:
        try:
            import kokoro  # noqa: F401
            return True
        except Exception:
            return False

    def _lang_of(self, voice: str) -> str:
        return _KOKORO_LANG.get((voice or "e")[:1].lower(), "a")

    def _get_pipeline(self, lang: str):
        if lang in self._pipelines:
            return self._pipelines[lang]
        from kokoro import KPipeline
        if self._device is None:
            try:
                import torch
                self._device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                self._device = "cpu"
        try:
            pipe = KPipeline(lang_code=lang, device=self._device)
        except TypeError:
            pipe = KPipeline(lang_code=lang)  # builds antiguos sin `device`
        self._pipelines[lang] = pipe
        return pipe

    def synthesize_wav(
        self, text: str, voice: str = "ef_dora", speed: float = 1.0
    ) -> Optional[bytes]:
        """Genera audio y lo devuelve como WAV (bytes). None + last_error si falla.
        BLOQUEANTE (CPU/GPU): el endpoint lo llama vía asyncio.to_thread."""
        try:
            import numpy as np
        except Exception as e:  # pragma: no cover
            self.last_error = f"Kokoro necesita numpy: {e}"
            return None
        try:
            with self._lock:
                pipe = self._get_pipeline(self._lang_of(voice))
                chunks: List = []
                for out in pipe(text, voice=voice, speed=speed):
                    audio = getattr(out, "audio", None)
                    if audio is None:
                        try:
                            audio = out[2]
                        except Exception:
                            audio = None
                    if audio is None:
                        continue
                    if hasattr(audio, "detach"):  # tensor torch
                        audio = audio.detach().cpu().float().numpy()
                    arr = np.asarray(audio, dtype=np.float32).flatten()
                    if arr.size:
                        chunks.append(arr)
            if not chunks:
                self.last_error = "Kokoro no generó audio."
                return None
            full = np.concatenate(chunks)
            pcm16 = (np.clip(full, -1.0, 1.0) * 32767.0).astype("<i2")
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(_SAMPLE_RATE)
                w.writeframes(pcm16.tobytes())
            self.last_error = None
            return buf.getvalue()
        except Exception as e:
            self.last_error = f"Kokoro falló: {type(e).__name__}: {e}"
            return None


kokoro_client = KokoroVoice()
