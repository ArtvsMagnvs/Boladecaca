"""
Aithera — local STT (speech-to-text) via faster-whisper.

WHY THIS MODULE
- V0.83 (Paso 4) introduces a micro button in the UI. The captured audio
  is posted to /api/voice/transcribe, which delegates here.
- faster-whisper (CTranslate2 backend) is 4x faster than openai/whisper
  on CPU, MIT licensed, bundles PyAV (no system ffmpeg needed).
- We force language="es" because the user uses Aithera primarily in
  Spanish. Letting Whisper auto-detect from short clips (~3s) often
  misfires to Portuguese or Italian (skill aithera-voice-stt pitfall #4).

WHAT THIS MODULE DOES
- Exposes get_model() which returns a process-wide singleton WhisperModel.
  The first call downloads + loads the model (5-10s, ~150MB for "base").
  Subsequent calls are <100ms.
- Exposes transcribe(audio_path, language) which runs the model on an
  audio file (webm/opus/wav/mp3 — anything PyAV decodes) and returns
  a dict with the joined text, language, segments, and audio duration.

SCOPE
- CPU by default. GPU requires `pip install nvidia-cublas-cu12 ...` and
  LD_LIBRARY_PATH tweaks (out of scope here, see faster-whisper README).
- compute_type="int8" is 2x faster than float32 on CPU with negligible
  accuracy loss. Skill pitfall #9 says always use vad_filter=True to
  avoid garbage tokens at the start/end (silence transcribed as text).
"""
from __future__ import annotations

import os
from typing import Any

# Default model = "small" (466 MB, ~3-4% WER espanol, mucho mas preciso que
# "base"). En CPU int8 va ~1-1.5x realtime, de sobra para clips cortos. Cambia
# con WHISPER_MODEL: "base" (142MB, mas rapido/menos preciso) o "medium"
# (1.5GB, aun mas preciso pero lento en CPU).
_DEFAULT_MODEL = os.getenv("WHISPER_MODEL", "small")
_DEFAULT_LANG = os.getenv("WHISPER_LANGUAGE", "es")
# Device por defecto CPU. Antes se usaba "auto", que en equipos con GPU NVIDIA
# intenta CUDA y falla si faltan las libs (cublas64_12.dll / cudnn) — que es lo
# normal si el usuario no ha montado el toolkit CUDA. En CPU con int8 el modelo
# "base" va ~3x realtime, de sobra para clips cortos. Quien tenga CUDA montado
# puede poner WHISPER_DEVICE=cuda en el .env.
_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")

_model: Any = None
_model_size: str = _DEFAULT_MODEL
_load_error: str | None = None
# Distingue los dos modos de fallo, que necesitan acciones DISTINTAS:
#   _lib_missing=True  -> falta `pip install faster-whisper`
#   _lib_missing=False -> la lib esta, pero el modelo no cargo (descarga
#                         incompleta / sin internet la primera vez).
_lib_missing: bool = False


def _load_model() -> Any:
    """Lazy-load del modelo. Se llama solo la primera vez."""
    global _model, _load_error, _lib_missing
    # 1) ¿esta la libreria? Import lazy: si no esta, el resto del backend
    #    (TTS, email...) sigue y /transcribe devuelve 503 claro.
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        _lib_missing = True
        _load_error = f"faster-whisper no instalado: {e}"
        return None
    # 2) La lib esta; intentamos cargar/descargar el modelo. Aqui es donde
    #    cae el caso tipico: descarga interrumpida por falta de red deja el
    #    snapshot a medias (falta model.bin) y WhisperModel() revienta.
    # compute_type="int8" es el sweet spot para CPU (skill aithera-voice-stt).
    try:
        _model = WhisperModel(_model_size, device=_DEVICE, compute_type="int8")
        _lib_missing = False
        return _model
    except Exception as e:
        # Si se pidio GPU (cuda) y falla por falta de libs CUDA, reintentamos
        # en CPU en vez de dejar el STT muerto. Solo relanzamos si ya era CPU.
        if _DEVICE != "cpu":
            try:
                _model = WhisperModel(_model_size, device="cpu", compute_type="int8")
                _lib_missing = False
                return _model
            except Exception as e2:
                _lib_missing = False
                _load_error = f"{e2}"
                return None
        _lib_missing = False
        _load_error = str(e)
        return None


def get_model() -> Any:
    """Devuelve el singleton del modelo. Lo carga en la primera llamada."""
    if _model is None:
        return _load_model()
    return _model


def is_available() -> bool:
    """Dice si faster-whisper esta instalado y el modelo se ha podido cargar."""
    if _model is not None:
        return True
    # Intento cargar (silencioso). Si falla, devuelvo False.
    return get_model() is not None


def get_status() -> dict:
    """Estado del STT para el endpoint /api/voice/status."""
    if _model is not None:
        return {
            "available": True,
            "model": _model_size,
            "language": _DEFAULT_LANG,
            "load_error": None,
        }
    # Probe: si no esta cargado, intenta. Asi /status da una respuesta
    # realista sin obligar al usuario a transcribir primero.
    loaded = get_model()
    return {
        "available": loaded is not None,
        "model": _model_size,
        "language": _DEFAULT_LANG,
        "load_error": _load_error,
        # reason ayuda a la UI a mostrar el mensaje correcto:
        #   "lib_missing"  -> pedir pip install
        #   "model_failed" -> pedir borrar cache + reintentar con internet
        #   None           -> disponible
        "reason": (
            None if loaded is not None
            else ("lib_missing" if _lib_missing else "model_failed")
        ),
    }


def transcribe(
    audio_path: str,
    language: str | None = None,
    beam_size: int = 5,
    vad_filter: bool = True,
) -> dict:
    """
    Transcribe an audio file with the loaded model.

    Args:
        audio_path: ruta a un archivo de audio. faster-whisper usa PyAV
            internamente, asi que acepta webm/opus (lo que produce
            MediaRecorder en Electron), wav, mp3, m4a, etc. SIN conversion.
        language: forzar idioma. "es" es lo normal. None = autodetect
            (recomendado NO usar; skill pitfall #4).
        beam_size: 5 por defecto. Sube a 10 si quieres +accuracy a costa
            de ~2x latencia.
        vad_filter: True por defecto. Filtra silencios al inicio/fin
            para evitar tokens basura (skill pitfall #9).

    Returns dict con:
        text: transcripcion completa (segmentos unidos con espacio)
        language: idioma detectado o el forzado
        language_probability: 0..1
        duration: duracion del audio en segundos (info de Whisper)
        segments: lista de {start, end, text}
    """
    model = get_model()
    if model is None:
        if _lib_missing:
            raise RuntimeError(
                "faster-whisper no esta instalado. Instala con "
                "`pip install faster-whisper==1.2.1`."
            )
        # La lib esta pero el modelo no cargo: casi siempre es una descarga
        # incompleta del modelo "base" de HuggingFace (falta model.bin)
        # porque la primera vez no habia internet o el DNS fallo.
        raise RuntimeError(
            "El modelo de STT no se pudo cargar (probable descarga incompleta "
            "o sin conexion la primera vez). Con internet, borra la cache "
            "'~/.cache/huggingface/hub/models--Systran--faster-whisper-base' "
            f"y reintenta. Detalle: {_load_error}"
        )

    lang = language or _DEFAULT_LANG
    segments_iter, info = model.transcribe(
        audio_path,
        language=lang,
        beam_size=beam_size,
        vad_filter=vad_filter,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    # IMPORTANTE: segments es un generador. Materializamos ahora porque
    # el audio_path se borra despues de que la funcion retorna.
    # Si no, la lectura posterior daria objetos vacios.
    segs = list(segments_iter)
    return {
        "text": " ".join(s.text.strip() for s in segs).strip(),
        "language": info.language,
        "language_probability": round(info.language_probability, 4),
        "duration": round(info.duration, 3),
        "segments": [
            {
                "start": round(s.start, 3),
                "end": round(s.end, 3),
                "text": s.text.strip(),
            }
            for s in segs
        ],
    }
