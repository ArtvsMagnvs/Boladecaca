# Voice Synthesis API Endpoints - ElevenLabs, EdgeTTS, Kokoro, y
# faster-whisper STT (V0.83, Paso 4).
#
# [2026-07-23, A·VOZ-1] eSpeak NG RETIRADO (doc 32). EdgeTTS es la base
# garantizada (gratis, sin key, sin instalar nada) desde V3 (voice_defaults);
# eSpeak solo aportaba un fallback offline de peor calidad que ya no hace
# falta. Ver PLAN_MAESTRO_2026/32_VOZ_CONVERSACION_Y_NAVEGACION_WEB.md.
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Union
import base64
import io
import os
import tempfile
import httpx

from app.voice.elevenlabs_voice import (
    voice_client as elevenlabs_client,
    synthesize_speech as elevenlabs_synthesize,
    get_all_voices as get_elevenlabs_voices,
    PROFESSIONAL_VOICES
)
import asyncio
from app.voice.kokoro_voice import kokoro_client, KOKORO_VOICES
from app.voice.edge_tts_voice import edgetts_client, EDGE_VOICES
from app.voice.whisper_stt import transcribe, get_status as stt_status
from app.voice.text_clean import clean_for_speech

router = APIRouter(prefix="/voice", tags=["Voice"])


class SynthesizeRequest(BaseModel):
    text: str
    voice_id: Optional[str] = "XB0fDUnXU5powGXd8GSW"  # Default: Spanish female
    use_stream: Optional[bool] = True
    provider: Optional[str] = None


def _edge_voice_or_default(voice_id: Optional[str]) -> str:
    """`voice_id` por defecto de `SynthesizeRequest` es un ID de ElevenLabs
    ("XB0fDUnXU5powGXd8GSW") — pasarlo tal cual a EdgeTTS rompería la síntesis
    justo en el caso por defecto (sin ElevenLabs configurado, sin provider
    explícito). Solo se reusa `voice_id` si es un nombre de voz de Edge real."""
    if voice_id and any(v["id"] == voice_id for v in EDGE_VOICES):
        return voice_id
    return "es-ES-ElviraNeural"


@router.get("/voices")
def list_voices() -> JSONResponse:
    """Get list of all available professional voices (ElevenLabs, si está
    configurado)."""
    voices = []

    # Add ElevenLabs voices if configured
    if elevenlabs_client.api_key:
        voices.extend(elevenlabs_client.get_professional_voices())

    return JSONResponse(content=voices)


# V0.83 (Paso 3, sprint voz): lista las voces reales de la cuenta del usuario
# desde la API de ElevenLabs. Diferencia con /voices: este NO mezcla las
# predefinidas, solo devuelve lo que la cuenta tiene (premade + clonadas +
# professional + generated). El frontend las marca con badges por categoria.
@router.get("/voices/account")
async def list_account_voices() -> JSONResponse:
    """Lista las voces reales de la cuenta ElevenLabs del usuario."""
    if not elevenlabs_client.api_key:
        raise HTTPException(
            status_code=503,
            detail="ElevenLabs no configurado. Configura la API key en Ajustes.",
        )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{elevenlabs_client.base_url}/voices",
                headers={"xi-api-key": elevenlabs_client.api_key},
            )
        if r.status_code != 200:
            raise HTTPException(
                status_code=r.status_code,
                detail=f"ElevenLabs devolvio {r.status_code}: {r.text[:200]}",
            )
        return JSONResponse(content=r.json())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando ElevenLabs: {e}")


@router.get("/status")
def voice_status() -> JSONResponse:
    """
    Check voice synthesis status.

    FIX V0.3 (Fase 1 Estabilizacion Hub V03 - P2): estructura PLANA
    { configured, voices_count, message } — contrato que el cliente
    TypeScript (api.ts) consume desde V0.2 para la barra de estado del Hub.

    [2026-07-23, A·VOZ-1] eSpeak retirado: EdgeTTS es el fallback SIEMPRE
    disponible (gratis, sin key, sin instalar nada) — a diferencia de eSpeak,
    no depende de un binario que el usuario tuviera que instalar aparte, así
    que "configured" es efectivamente siempre True.
    """
    elevenlabs_status = bool(elevenlabs_client.api_key)

    if elevenlabs_status:
        configured = True
        voices_count = len(PROFESSIONAL_VOICES)
        source = "elevenlabs"
        message = "ElevenLabs configurado"
    else:
        configured = True
        voices_count = len(EDGE_VOICES)
        source = "edgetts"
        message = "EdgeTTS disponible (gratis, sin configuración)"

    return JSONResponse(content={
        # Contrato principal (estructura plana) - V0.3
        "configured": configured,
        "voices_count": voices_count,
        "message": message,
        "source": source,
        # Detalle adicional (no rompe compatibilidad con clientes que ya
        # lean la clave anidada "elevenlabs")
        "elevenlabs": {
            "configured": elevenlabs_status,
            "voices_count": len(PROFESSIONAL_VOICES),
            "message": "ElevenLabs ready" if elevenlabs_status else "Set ELEVENLABS_API_KEY for AI voices"
        },
        "fallback": "edgetts",
        "recommended": "elevenlabs" if elevenlabs_status else "edgetts",
    })


@router.post("/synthesize")
async def synthesize(request: SynthesizeRequest) -> Response:
    """
    Synthesize speech from text.

    Priority:
    1. ElevenLabs (if API key configured)
    2. EdgeTTS (free fallback, no key required)

    Returns MP3/WAV audio data.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    # El TTS no debe leer ni describir emoticonos (ej. decir "carita
    # sonriente" al llegar a un 😊). Se quitan SOLO para la voz; el texto que
    # ve el usuario en el chat no pasa por aqui y conserva los emoticonos.
    # [V1] Limpieza COMPLETA para voz: markdown + emojis + URLs. Antes solo
    # quitaba emojis, asi que la voz leia "asterisco asterisco" en las
    # negritas y pronunciaba guiones de lista y barras de tabla.
    text = clean_for_speech(request.text)
    if not text:
        raise HTTPException(
            status_code=422,
            detail="El texto solo contenia emoticonos; no hay nada que sintetizar en voz.",
        )

    # A·VOZ-5: Kokoro (TTS local EN PROCESO, sin Docker, devuelve WAV).
    # Bloqueante -> to_thread. DEGRADACIÓN GRACIOSA (doc 32): si Kokoro falla
    # (no instalado, modelo sin descargar, o fallo de carga), NO devolvemos 502
    # — caemos a EdgeTTS con log. Una voz de peor calidad es infinitamente mejor
    # que voz muda.
    if request.provider == "kokoro":
        audio_data = await asyncio.to_thread(
            kokoro_client.synthesize_wav, text, request.voice_id or "ef_dora"
        )
        if audio_data:
            return Response(
                content=audio_data,
                media_type="audio/wav",
                headers={"Content-Disposition": 'inline; filename="speech.wav"'},
            )
        print(f"[voz] Kokoro falló ({kokoro_client.last_error}); fallback a EdgeTTS.")
        audio_data = await edgetts_client.synthesize_mp3(
            text, _edge_voice_or_default(request.voice_id)
        )
        if audio_data:
            return Response(
                content=audio_data,
                media_type="audio/mpeg",
                headers={"Content-Disposition": 'inline; filename="speech.mp3"'},
            )
        raise HTTPException(
            status_code=502,
            detail=kokoro_client.last_error or "Kokoro no devolvio audio.",
        )

    # V0.83: EdgeTTS (Microsoft, gratis, sin key; devuelve MP3).
    if request.provider == "edgetts":
        audio_data = await edgetts_client.synthesize_mp3(
            text, request.voice_id or "es-ES-ElviraNeural"
        )
        if audio_data:
            return Response(
                content=audio_data,
                media_type="audio/mpeg",
                headers={"Content-Disposition": 'inline; filename="speech.mp3"'},
            )
        raise HTTPException(
            status_code=502,
            detail=edgetts_client.last_error or "EdgeTTS no devolvio audio.",
        )

    # Try ElevenLabs first (si está configurado).
    if elevenlabs_client.api_key:
        try:
            audio_data = await elevenlabs_synthesize(
                text=text,
                voice_id=request.voice_id,
                use_stream=request.use_stream
            )
            if audio_data:
                return Response(
                    content=audio_data,
                    media_type="audio/mpeg",
                    headers={"Content-Disposition": 'inline; filename="speech.mp3"'}
                )
            # elevenlabs_synthesize devolvio None: mostramos el MOTIVO REAL que
            # guardo el cliente (ej. "HTTP 402 · detected_unusual_activity:
            # ..."), no un generico. Asi el usuario sabe si es la key, cuota,
            # o el bloqueo del plan gratuito por uso via API/VPN.
            detail = elevenlabs_client.last_error or (
                "ElevenLabs devolvio audio vacio (sin detalle)."
            )
            raise HTTPException(status_code=502, detail=detail)
        except HTTPException:
            raise
        except Exception as e:
            # Si ElevenLabs falla con excepcion de red/auth, etc., devolvemos
            # 502 explicito (no 503 generico). Asi el frontend sabe que es
            # ElevenLabs y no "el backend no sabe sintetizar".
            raise HTTPException(
                status_code=502,
                detail=f"ElevenLabs fallo: {type(e).__name__}: {e}",
            )

    # Si llegamos aqui, ElevenLabs no estaba configurado (o se pidió otro
    # proveedor no manejado arriba). Fallback a EdgeTTS — gratis, sin key,
    # siempre disponible (A·VOZ-1: reemplaza al antiguo fallback eSpeak).
    audio_data = await edgetts_client.synthesize_mp3(
        text, _edge_voice_or_default(request.voice_id)
    )
    if audio_data:
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={"Content-Disposition": 'inline; filename="speech.mp3"'}
        )

    # No synthesis available
    raise HTTPException(
        status_code=503,
        detail=edgetts_client.last_error or "No voice synthesis available.",
    )


@router.post("/synthesize/base64")
async def synthesize_base64(request: SynthesizeRequest) -> JSONResponse:
    """Synthesize speech and return as base64-encoded audio."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    # El TTS no debe leer ni describir emoticonos (ver text_clean.py).
    # [V1] Limpieza COMPLETA para voz: markdown + emojis + URLs. Antes solo
    # quitaba emojis, asi que la voz leia "asterisco asterisco" en las
    # negritas y pronunciaba guiones de lista y barras de tabla.
    text = clean_for_speech(request.text)
    if not text:
        raise HTTPException(
            status_code=422,
            detail="El texto solo contenia emoticonos; no hay nada que sintetizar en voz.",
        )

    # A·VOZ-5: Kokoro (TTS local en proceso, WAV). Degradación graciosa a
    # EdgeTTS si falla (doc 32) — nunca voz muda.
    if request.provider == "kokoro":
        audio_data = await asyncio.to_thread(
            kokoro_client.synthesize_wav, text, request.voice_id or "ef_dora"
        )
        if audio_data:
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            return JSONResponse(content={
                "audio": f"data:audio/wav;base64,{audio_b64}",
                "voice_id": request.voice_id,
                "format": "wav",
                "source": "kokoro",
            })
        print(f"[voz] Kokoro falló ({kokoro_client.last_error}); fallback a EdgeTTS.")
        audio_data = await edgetts_client.synthesize_mp3(
            text, _edge_voice_or_default(request.voice_id)
        )
        if audio_data:
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            return JSONResponse(content={
                "audio": f"data:audio/mpeg;base64,{audio_b64}",
                "voice_id": request.voice_id,
                "format": "mp3",
                "source": "edgetts",
            })
        raise HTTPException(
            status_code=502,
            detail=kokoro_client.last_error or "Kokoro no devolvio audio.",
        )

    # V0.83: EdgeTTS (MP3).
    if request.provider == "edgetts":
        audio_data = await edgetts_client.synthesize_mp3(
            text, request.voice_id or "es-ES-ElviraNeural"
        )
        if audio_data:
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            return JSONResponse(content={
                "audio": f"data:audio/mpeg;base64,{audio_b64}",
                "voice_id": request.voice_id,
                "format": "mp3",
                "source": "edgetts",
            })
        raise HTTPException(
            status_code=502,
            detail=edgetts_client.last_error or "EdgeTTS no devolvio audio.",
        )

    # Try ElevenLabs first (si está configurado).
    if elevenlabs_client.api_key:
        try:
            audio_data = await elevenlabs_synthesize(
                text=text,
                voice_id=request.voice_id,
                use_stream=request.use_stream
            )
            if audio_data:
                audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                return JSONResponse(content={
                    "audio": f"data:audio/mpeg;base64,{audio_b64}",
                    "voice_id": request.voice_id,
                    "format": "mp3",
                    "source": "elevenlabs"
                })
            detail = elevenlabs_client.last_error or "ElevenLabs devolvio audio vacio."
            raise HTTPException(status_code=502, detail=detail)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"ElevenLabs fallo: {type(e).__name__}: {e}",
            )

    # Fallback a EdgeTTS (A·VOZ-1: reemplaza al antiguo fallback eSpeak).
    audio_data = await edgetts_client.synthesize_mp3(
        text, _edge_voice_or_default(request.voice_id)
    )
    if audio_data:
        audio_b64 = base64.b64encode(audio_data).decode("utf-8")
        return JSONResponse(content={
            "audio": f"data:audio/mpeg;base64,{audio_b64}",
            "voice_id": request.voice_id,
            "format": "mp3",
            "source": "edgetts",
        })

    raise HTTPException(
        status_code=503,
        detail=edgetts_client.last_error or "No voice synthesis available",
    )


# --------------------------------------------------------------------------
# V0.83 (Paso 4) — STT local con faster-whisper
# --------------------------------------------------------------------------
# Recibe un blob de audio del frontend (MediaRecorder produce audio/webm;
# codecs=opus) y devuelve la transcripcion. Sin internet, sin cloud, sin
# API key. El modelo "base" (~150 MB) se descarga la primera vez que se
# llama a /transcribe y se cachea en HF_HOME.
# --------------------------------------------------------------------------


@router.get("/stt/status")
def stt_status_endpoint() -> JSONResponse:
    """Dice si faster-whisper esta instalado y operativo."""
    return JSONResponse(content=stt_status())


@router.post("/transcribe")
async def transcribe_endpoint(
    audio: UploadFile = File(...),
    language: str = "es",
    fast: bool = False,
) -> JSONResponse:
    """
    Transcribe a short audio clip (typicamente 3-15s del micro del Hub).

    Accepts multipart/form-data con:
      - audio: blob (audio/webm, audio/ogg, audio/wav, audio/mpeg)
      - language: query param (default "es"). Forzado para evitar
        auto-detect en clips cortos (pitfall #4 skill aithera-voice-stt).

    Returns: { text, language, language_probability, duration, segments }
    """
    if not audio.filename:
        raise HTTPException(
            status_code=400,
            detail="Falta el archivo 'audio' (multipart/form-data).",
        )
    if audio.content_type and "audio" not in audio.content_type:
        raise HTTPException(
            status_code=400,
            detail=f"Content-Type esperado audio/*, recibido {audio.content_type}",
        )

    # faster-whisper necesita una ruta de archivo. Escribimos a temp y
    # borramos al final. NO convertimos a wav manualmente: faster-whisper
    # usa PyAV internamente y decodifica webm/opus directamente (skill
    # aithera-voice-stt, seccion "Important").
    suffix = os.path.splitext(audio.filename or "rec.webm")[1] or ".webm"
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="aithera_stt_")
    try:
        with os.fdopen(tmp_fd, "wb") as f:
            while True:
                chunk = await audio.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)

        # Transcribe. Esto lazy-loads el modelo la primera vez (5-10s);
        # las siguientes son <2s para clips de 5s. `fast` (O1): modo
        # conversación — modelo rápido + beam voraz, para fluidez en tiempo real.
        try:
            import time as _time
            _t0 = _time.perf_counter()
            result = transcribe(tmp_path, language=language, fast=fast)
            # [VZ5 profiling] Cuánto tardó el STT de verdad, en el log del
            # backend: la mitad servidor del perfil que el frontend imprime en
            # consola ([voz-perfil]). Juntos dicen qué etapa domina.
            _ms = int((_time.perf_counter() - _t0) * 1000)
            result["stt_ms"] = _ms
            print(f"[voz-perfil] STT {'fast' if fast else 'preciso'}: {_ms}ms "
                  f"para {result.get('duration', '?')}s de audio")
        except RuntimeError as e:
            # faster-whisper no instalado o modelo no cargable
            raise HTTPException(
                status_code=503,
                detail=f"STT no disponible: {e}",
            )
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error transcribiendo audio: {e}",
        )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ----------------------------------------------------------------------
# V0.83: configuracion de la API key de ElevenLabs desde Ajustes.
# La key se guarda CIFRADA (secrets.py, DPAPI) en la tabla Config bajo
# `elevenlabs_api_key`. El cliente TTS la lee dinamicamente (property
# api_key -> resolve_elevenlabs_key), asi que aplica sin reiniciar. NUNCA
# se devuelve la key entera: solo una mascara.
# ----------------------------------------------------------------------

_EL_KEY = "elevenlabs_api_key"


class ElevenLabsKeyIn(BaseModel):
    api_key: str


class ElevenLabsCfgStatus(BaseModel):
    configured: bool
    source: str          # "config" | "env" | "none"
    key_masked: str


def _el_status() -> dict:
    from app.core import secrets
    cfg_key = None
    try:
        from app.db.database import SessionLocal
        from app.db.models import Config
        db = SessionLocal()
        try:
            row = db.query(Config).filter(Config.key == _EL_KEY).first()
        finally:
            db.close()
        if row and row.value:
            cfg_key = secrets.decrypt(row.value)
    except Exception:
        cfg_key = None
    env_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if cfg_key:
        return {"configured": True, "source": "config", "key_masked": secrets.mask(cfg_key)}
    if env_key:
        return {"configured": True, "source": "env", "key_masked": secrets.mask(env_key)}
    return {"configured": False, "source": "none", "key_masked": ""}


@router.get("/elevenlabs/config", response_model=ElevenLabsCfgStatus)
def elevenlabs_get_config():
    """Estado de la API key de ElevenLabs (nunca devuelve la key entera)."""
    return _el_status()


@router.post("/elevenlabs/config", response_model=ElevenLabsCfgStatus)
def elevenlabs_set_config(payload: ElevenLabsKeyIn):
    """Guarda la API key CIFRADA en Config. Aplica sin reiniciar."""
    from app.core import secrets
    from app.db.database import SessionLocal
    from app.db.models import Config

    key = (payload.api_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="La API key no puede estar vacia.")
    db = SessionLocal()
    try:
        row = db.query(Config).filter(Config.key == _EL_KEY).first()
        enc = secrets.encrypt(key)
        if row:
            row.value = enc
        else:
            db.add(Config(key=_EL_KEY, value=enc))
        db.commit()
    finally:
        db.close()
    return _el_status()


@router.delete("/elevenlabs/config", response_model=ElevenLabsCfgStatus)
def elevenlabs_delete_config():
    """Borra la API key guardada en Config (vuelve a env si lo hubiera)."""
    from app.db.database import SessionLocal
    from app.db.models import Config

    db = SessionLocal()
    try:
        row = db.query(Config).filter(Config.key == _EL_KEY).first()
        if row:
            db.delete(row)
            db.commit()
    finally:
        db.close()
    return _el_status()


# ----------------------------------------------------------------------
# A·VOZ-5 (doc 32): Kokoro = voz LOCAL de máxima calidad, SIN Docker, vía
# `kokoro-onnx` (ONNX Runtime, sin PyTorch). Se añade junto a ElevenLabs/EdgeTTS.
# ----------------------------------------------------------------------

# La instalación tiene DOS fases con seguimiento real (a diferencia del stub
# anterior, que solo hacía `pip install kokoro` y dejaba el modelo "al primer
# uso" sin barra ni control): (1) pip install de la librería `kokoro-onnx` +
# `soundfile`, (2) descarga del modelo ONNX cuantizado (~80 MB) y el banco de
# voces (~28 MB) a %APPDATA%/Aithera/kokoro/. Un hilo captura la salida y el
# progreso; /kokoro/status informa de cada fase, del éxito o del ERROR REAL.
_KOKORO_INSTALL: dict = {
    "status": "idle",        # idle|installing|downloading|done|failed
    "detail": None,
    "progress": 0,           # 0-100 durante la descarga del modelo
}


def _download_with_progress(url: str, dest: "Path", label: str) -> None:
    """Descarga `url` a `dest` (atómico: baja a .part y renombra al final),
    actualizando `_KOKORO_INSTALL['progress']`. Lanza si falla."""
    import urllib.request

    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        with open(tmp, "wb") as f:
            while True:
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total:
                    _KOKORO_INSTALL["progress"] = int(done * 100 / total)
                _KOKORO_INSTALL["detail"] = f"Descargando {label}…"
    os.replace(tmp, dest)


def _kokoro_install_worker() -> None:
    import subprocess
    import sys
    from app.voice import kokoro_voice as kv

    try:
        # Fase 1: librería (idempotente — si ya está, pip no hace nada).
        if not kv.library_installed():
            _KOKORO_INSTALL.update(status="installing", detail="Instalando kokoro-onnx…")
            r = subprocess.run(
                [sys.executable, "-m", "pip", "install", "kokoro-onnx", "soundfile",
                 "--disable-pip-version-check"],
                capture_output=True, text=True, timeout=1800,
            )
            if r.returncode != 0:
                tail = (r.stderr or r.stdout or "").strip()[-400:]
                _KOKORO_INSTALL.update(
                    status="failed",
                    detail=tail or f"pip terminó con código {r.returncode}",
                )
                return

        # Fase 2: modelo + voces (~108 MB). Solo lo que falte.
        kv.KOKORO_DIR.mkdir(parents=True, exist_ok=True)
        _KOKORO_INSTALL.update(status="downloading", progress=0)
        if kv.model_path() is None:
            _download_with_progress(
                kv.MODEL_URL, kv.KOKORO_DIR / kv.MODEL_FILENAME, "modelo (~80 MB)"
            )
        if kv.voices_path() is None:
            _download_with_progress(
                kv.VOICES_URL, kv.KOKORO_DIR / kv.VOICES_FILENAME, "voces (~28 MB)"
            )
        _KOKORO_INSTALL.update(status="done", detail=None, progress=100)
    except Exception as e:
        _KOKORO_INSTALL.update(status="failed", detail=f"{type(e).__name__}: {e}")


@router.get("/kokoro/status")
def kokoro_status() -> JSONResponse:
    """Estado de Kokoro (voz local de alta calidad): librería + modelo
    descargado + instalación/descarga en curso lanzada desde la UI."""
    from app.voice import kokoro_voice as kv

    lib = kv.library_installed()
    model = kv.model_downloaded()
    available = lib and model
    inst = _KOKORO_INSTALL["status"]
    if available:
        msg = "Kokoro listo (voz local de máxima calidad, funciona sin conexión)."
    elif inst == "installing":
        msg = "Instalando la librería kokoro-onnx… (pip; unos minutos)"
    elif inst == "downloading":
        msg = f"Descargando el modelo de voz… ({_KOKORO_INSTALL.get('progress', 0)}%)"
    elif inst == "done":
        msg = ("Instalación terminada. Vuelve a seleccionar Kokoro; si no "
               "aparece, reinicia el backend.")
    elif inst == "failed":
        msg = f"La instalación falló: {_KOKORO_INSTALL['detail']}"
    elif lib and not model:
        msg = ("La librería está, falta el modelo de voz (~108 MB). "
               "Pulsa 'Instalar Kokoro' para descargarlo.")
    else:
        msg = ("Kokoro no está instalado. Pulsa 'Instalar Kokoro' — descarga "
               "~108 MB una vez (librería + modelo).")
    return JSONResponse(content={
        "available": available,
        "library_installed": lib,
        "model_downloaded": model,
        "install_status": inst,
        "progress": _KOKORO_INSTALL.get("progress", 0),
        "message": msg,
    })


@router.get("/kokoro/voices")
def kokoro_voices() -> JSONResponse:
    """Lista curada de voces de Kokoro (español primero)."""
    return JSONResponse(content={"voices": KOKORO_VOICES})


@router.post("/kokoro/install")
def kokoro_install() -> JSONResponse:
    """Lanza la instalación de Kokoro (pip `kokoro-onnx` + descarga del modelo),
    en un hilo con la salida/progreso capturados. Idempotente: si ya está listo
    o en curso, lo dice en vez de duplicar el proceso. Progreso en /status."""
    import threading

    if kokoro_client.is_available():
        return JSONResponse(content={"started": False, "message": "Kokoro ya está listo."})
    if _KOKORO_INSTALL["status"] in ("installing", "downloading"):
        return JSONResponse(content={"started": False, "message": "Ya hay una instalación en curso."})
    _KOKORO_INSTALL.update(status="installing", detail=None, progress=0)
    threading.Thread(target=_kokoro_install_worker, daemon=True).start()
    return JSONResponse(content={
        "started": True,
        "message": "Instalando Kokoro en segundo plano (librería + modelo, "
                   "~108 MB). El estado y el progreso se actualizan aquí.",
    })


@router.get("/edgetts/status")
def edgetts_status() -> JSONResponse:
    """¿Está edge-tts instalado? (voces de Microsoft, gratis, requiere internet)."""
    available = edgetts_client.is_available()
    return JSONResponse(content={
        "available": available,
        "message": (
            "EdgeTTS listo (gratis, requiere internet)." if available
            else "edge-tts no instalado: pip install edge-tts"
        ),
    })


@router.get("/edgetts/voices")
def edgetts_voices() -> JSONResponse:
    """Lista curada de voces EdgeTTS (español + inglés)."""
    return JSONResponse(content={"voices": EDGE_VOICES})


# ======================================================================
# V3 — VOZ POR DEFECTO GARANTIZADA (2026-07-20)
# ======================================================================
# EL BUG QUE CIERRA (reportado por el usuario): Aithera no respondía por voz
# hasta ir al Centro de Voz y elegir una manualmente. Una app de voz que arranca
# MUDA está rota: el usuario no sabe que tiene que ir a configurar nada.
#
# Ahora el arranque SIEMPRE resuelve una voz: la guardada por el usuario, o la
# mejor por defecto del idioma. EdgeTTS es el proveedor de defecto porque es el
# único gratis, sin API key y sin descargar modelos — el único que se puede
# garantizar en una instalación limpia.

_VOICE_KEY = "tts_selected_voice"
_PROVIDER_KEY = "tts_active_provider"
_LANG_KEY = "app_language"

# Mejor voz por defecto por idioma (EdgeTTS, neuronales, gratis). Cubre los 4
# idiomas de instalación (ES/EN/FR/PT).
_DEFAULT_VOICE_BY_LANG = {
    "es": "es-ES-ElviraNeural",
    "en": "en-US-AriaNeural",
    "fr": "fr-FR-DeniseNeural",
    "pt": "pt-BR-FranciscaNeural",
}
_FALLBACK_LANG = "es"


class VoiceDefaults(BaseModel):
    provider: str
    voice_id: str
    language: str
    was_assigned: bool     # True = no había ninguna elegida y se ha asignado ahora


def _cfg_get(key: str) -> Optional[str]:
    from app.db.database import SessionLocal
    from app.db.models import Config
    db = SessionLocal()
    try:
        row = db.query(Config).filter(Config.key == key).first()
        return row.value if row else None
    finally:
        db.close()


def _cfg_set(key: str, value: str) -> None:
    from app.db.database import SessionLocal
    from app.db.models import Config
    db = SessionLocal()
    try:
        row = db.query(Config).filter(Config.key == key).first()
        if row:
            row.value = value
        else:
            db.add(Config(key=key, value=value))
        db.commit()
    finally:
        db.close()


# Idioma que denota el ID de una voz de EdgeTTS ("pt-BR-…" → pt) o de Kokoro
# (prefijo: e=es a/b=en f=fr p=pt). Devuelve None si no se puede deducir (voces
# de ElevenLabs, que son opacas y además multilingües — a esas no se las toca).
_KOKORO_PREFIX_LANG = {"e": "es", "a": "en", "b": "en", "f": "fr", "p": "pt"}


def _voice_language(voice_id: str, provider: Optional[str]) -> Optional[str]:
    if not voice_id:
        return None
    if provider == "kokoro" or ("_" in voice_id and len(voice_id.split("_")[0]) <= 2):
        return _KOKORO_PREFIX_LANG.get(voice_id[:1].lower())
    # EdgeTTS: "es-ES-ElviraNeural" → "es"
    head = voice_id.split("-", 1)[0].lower()
    return head if head in ("es", "en", "fr", "pt") else None


@router.get("/defaults", response_model=VoiceDefaults)
def voice_defaults() -> VoiceDefaults:
    """La voz que Aithera debe usar AHORA. Si el usuario no ha elegido ninguna,
    asigna (y persiste) la mejor del idioma configurado — nunca devuelve vacío.

    [2026-07-24 FIX] La voz SIGUE al idioma. EL BUG (reportado): al cambiar el
    idioma de la app, la voz guardada NO se reevaluaba — una voz portuguesa
    heredada de antes se quedaba y leía el español con acento portugués. Ahora,
    si la voz guardada pertenece a OTRO idioma que el de la app (deducible en
    EdgeTTS/Kokoro), se reasigna a la voz por defecto del idioma actual. Las voces
    de ElevenLabs (opacas y multilingües) no se tocan.

    Lo llama el frontend al arrancar: así el chat habla desde el primer mensaje,
    sin pasar por el Centro de Voz."""
    lang = (_cfg_get(_LANG_KEY) or _FALLBACK_LANG).split("-")[0].lower()
    if lang not in _DEFAULT_VOICE_BY_LANG:
        lang = _FALLBACK_LANG

    voice = _cfg_get(_VOICE_KEY)
    provider = _cfg_get(_PROVIDER_KEY)
    assigned = False

    # ¿La voz guardada es de OTRO idioma? → reasignar a la del idioma actual.
    if voice:
        v_lang = _voice_language(voice, provider)
        if v_lang is not None and v_lang != lang:
            voice = _DEFAULT_VOICE_BY_LANG[lang]
            provider = "edgetts"
            _cfg_set(_VOICE_KEY, voice)
            _cfg_set(_PROVIDER_KEY, provider)
            assigned = True

    if not voice:
        voice = _DEFAULT_VOICE_BY_LANG[lang]
        provider = provider or "edgetts"
        _cfg_set(_VOICE_KEY, voice)
        _cfg_set(_PROVIDER_KEY, provider)
        assigned = True
    elif not provider:
        provider = "edgetts"
        _cfg_set(_PROVIDER_KEY, provider)
        assigned = True

    return VoiceDefaults(provider=provider or "edgetts", voice_id=voice,
                         language=lang, was_assigned=assigned)


# ======================================================================
# V2 — PERSONALIDADES (2026-07-20)
# ======================================================================
# Viven en `app/ai/personalities.py` (es tono de CHAT, no de voz); se exponen
# bajo /voice porque es donde el usuario las configura.

class PersonalitySelect(BaseModel):
    personality_id: str


class PersonalityCustomIn(BaseModel):
    description: str          # lo que escribe el usuario, en bruto
    activate: bool = True


@router.get("/personalities")
def list_personalities() -> JSONResponse:
    """Catálogo + personalidad activa + prompt personalizado (si lo hay)."""
    from app.ai import personalities
    return JSONResponse(content=personalities.catalog_payload())


@router.post("/personalities/select")
def select_personality(payload: PersonalitySelect) -> JSONResponse:
    from app.ai import personalities
    try:
        personalities.set_active(payload.personality_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse(content=personalities.catalog_payload())


@router.post("/personalities/custom")
async def create_custom_personality(payload: PersonalityCustomIn) -> JSONResponse:
    """Convierte la descripción EN BRUTO del usuario en un bloque de tono bien
    construido (lo mejora una IA potente) y lo guarda. Devuelve el prompt final
    para que el usuario lo vea y pueda ajustarlo."""
    from app.ai import personalities
    try:
        mejorado = await personalities.improve_prompt(payload.description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    personalities.save_custom(mejorado, activate=payload.activate)
    return JSONResponse(content={
        "prompt": mejorado,
        **personalities.catalog_payload(),
    })
