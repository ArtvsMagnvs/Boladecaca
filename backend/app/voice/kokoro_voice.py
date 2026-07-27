"""
Kokoro TTS — voz LOCAL de máxima calidad, EN PROCESO, **sin Docker** (A·VOZ-5, doc 32).

Motor sobre `kokoro-onnx` (ONNX Runtime, SIN PyTorch). Sustituye al stub anterior
que usaba el paquete `kokoro` de PyTorch (arrastraba `misaki→spacy→thinc→blis`,
que NO compila en Python 3.13 y pinaba numpy==1.26.4, chocando con el numpy 2.x
del resto del stack — ver requirements.txt). `kokoro-onnx` en cambio:

  - Requiere numpy>=2.0.2 y onnxruntime>=1.20.1 → ALINEADO con el backend
    (chromadb ya trae onnxruntime; el stack ya corre numpy 2.x). Cero conflicto.
  - G2P (grafema→fonema) vía `phonemizer-fork` (Python puro) + `espeakng-loader`,
    que EMPAQUETA la librería espeak-ng como wheel de pip (incluye win_amd64).
    El usuario NO instala espeak-ng aparte: la fricción de Windows ("espeak not
    installed" / "phontab not found") la resuelve `kokoro-onnx` internamente
    (su tokenizer llama a `EspeakWrapper.set_data_path`/`set_library` con las
    rutas de `espeakng_loader`). Verificado en vivo (frase ES con nombres
    propios → IPA correcta).

El modelo ONNX (~80 MB cuantizado int8) y el banco de voces (~28 MB) se descargan
una vez a `%APPDATA%/Aithera/kokoro/` (ver el instalador en `endpoints/voice.py`),
NO se cargan en el arranque del backend (carga perezosa la primera vez que se
sintetiza). GPU si hay CUDA (onnxruntime-gpu opcional), si no CPU.

Devuelve bytes WAV al frontend (Aithera es web/Electron: el audio lo reproduce el
navegador, no el backend). Degradación graciosa: si la lib no está, si el modelo
no está descargado, o si la carga falla → `is_available()` False / `synthesize_wav`
devuelve None con `last_error`, y el endpoint cae a EdgeTTS (nunca voz muda).
"""
from __future__ import annotations

import io
import os
import threading
import wave
from pathlib import Path
from typing import List, Optional

# --------------------------------------------------------------------------
# Ubicación de los ficheros del modelo (mismo patrón que memory_manager/vault:
# %APPDATA%/Aithera/<subdir>, con override por variable de entorno para tests).
# --------------------------------------------------------------------------
KOKORO_DIR = Path(
    os.environ.get("AITHERA_KOKORO_DIR")
    or os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Aithera", "kokoro")
)

# Nombres de fichero. Por defecto la variante CUANTIZADA int8 (~80 MB, doc 32);
# si un usuario coloca el modelo completo `kokoro-v1.0.onnx`, también se acepta.
MODEL_FILENAME = "kokoro-v1.0.int8.onnx"
MODEL_FILENAME_FULL = "kokoro-v1.0.onnx"
VOICES_FILENAME = "voices-v1.0.bin"

# URLs de descarga (GitHub releases del proyecto kokoro-onnx). Las consume el
# instalador de `endpoints/voice.py`. El modelo cuantizado por defecto; el
# completo queda documentado por si se quiere máxima calidad a cambio de tamaño.
_RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
MODEL_URL = f"{_RELEASE}/{MODEL_FILENAME}"
MODEL_URL_FULL = f"{_RELEASE}/{MODEL_FILENAME_FULL}"
VOICES_URL = f"{_RELEASE}/{VOICES_FILENAME}"

# Prefijo del voice_id de Kokoro v1.0 -> código de idioma que espera kokoro-onnx
# (lo pasa a espeak). a=US b=UK e=Spanish f=French h=Hindi i=Italian j=Japanese
# p=BR Portuguese z=Mandarin.
_KOKORO_LANG = {
    "a": "en-us", "b": "en-gb", "e": "es", "f": "fr-fr",
    "h": "hi", "i": "it", "j": "ja", "p": "pt-br", "z": "cmn",
}

# Lista curada (Kokoro no expone endpoint de voces útil en proceso más allá de
# `get_voices()`, que da solo ids). Español primero. Los ids son los reales del
# banco `voices-v1.0.bin`.
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
    {"id": "ff_siwis",   "name": "Siwis (Français ♀)", "lang": "fr"},
    {"id": "pf_dora",    "name": "Dora (Português ♀)", "lang": "pt"},
]

_SAMPLE_RATE = 24000  # Kokoro genera 24 kHz mono


def model_path() -> Optional[Path]:
    """Ruta del modelo ONNX en disco (cuantizado preferido, completo aceptado).
    None si ninguno está descargado todavía."""
    q = KOKORO_DIR / MODEL_FILENAME
    if q.exists():
        return q
    full = KOKORO_DIR / MODEL_FILENAME_FULL
    if full.exists():
        return full
    return None


def voices_path() -> Optional[Path]:
    p = KOKORO_DIR / VOICES_FILENAME
    return p if p.exists() else None


def library_installed() -> bool:
    """¿Está la librería `kokoro-onnx` instalada? (independiente del modelo)."""
    try:
        import kokoro_onnx  # noqa: F401
        return True
    except Exception:
        return False


def model_downloaded() -> bool:
    """¿Están los dos ficheros (modelo + voces) en disco?"""
    return model_path() is not None and voices_path() is not None


class KokoroVoice:
    """TTS de Kokoro en proceso vía kokoro-onnx. Carga perezosa y thread-safe."""

    def __init__(self) -> None:
        self._kokoro = None                 # instancia kokoro_onnx.Kokoro (perezosa)
        self._lock = threading.Lock()
        self.last_error: Optional[str] = None

    def is_available(self) -> bool:
        """Operativo = librería instalada Y modelo descargado. Solo entonces el
        endpoint debe ofrecer Kokoro; si no, EdgeTTS."""
        return library_installed() and model_downloaded()

    def _lang_of(self, voice: str) -> str:
        return _KOKORO_LANG.get((voice or "e")[:1].lower(), "en-us")

    def _get_kokoro(self):
        """Construye (y cachea) la instancia Kokoro. Carga el ONNX + el banco de
        voces — pesado, por eso perezoso y bajo lock. kokoro-onnx cablea el
        espeak empaquetado por sí solo (no hace falta pasar EspeakConfig)."""
        if self._kokoro is not None:
            return self._kokoro
        from kokoro_onnx import Kokoro

        mp = model_path()
        vp = voices_path()
        if mp is None or vp is None:
            raise FileNotFoundError(
                "El modelo de Kokoro no está descargado "
                f"(esperado en {KOKORO_DIR})."
            )
        self._kokoro = Kokoro(str(mp), str(vp))
        return self._kokoro

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
                kok = self._get_kokoro()
                samples, sr = kok.create(
                    text, voice=voice, speed=speed, lang=self._lang_of(voice)
                )
            arr = np.asarray(samples, dtype=np.float32).flatten()
            if arr.size == 0:
                self.last_error = "Kokoro no generó audio."
                return None
            pcm16 = (np.clip(arr, -1.0, 1.0) * 32767.0).astype("<i2")
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(int(sr or _SAMPLE_RATE))
                w.writeframes(pcm16.tobytes())
            self.last_error = None
            return buf.getvalue()
        except Exception as e:
            self.last_error = f"Kokoro falló: {type(e).__name__}: {e}"
            return None


kokoro_client = KokoroVoice()
