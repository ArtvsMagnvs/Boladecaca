# Voice Synthesis API Endpoints - Supports both ElevenLabs, eSpeak NG, and
# faster-whisper STT (V0.83, Paso 4).
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
from app.voice.espeak_voice import (
    espeak_client,
    synthesize_offline,
    get_espeak_voices,
    is_espeak_available,
    ESPEAK_VOICES
)
from app.voice.whisper_stt import transcribe, get_status as stt_status

router = APIRouter(prefix="/voice", tags=["Voice"])


class SynthesizeRequest(BaseModel):
    text: str
    voice_id: Optional[str] = "XB0fDUnXU5powGXd8GSW"  # Default: Spanish female
    use_stream: Optional[bool] = True


@router.get("/voices")
def list_voices() -> JSONResponse:
    """
    Get list of all available professional voices.
    Includes both ElevenLabs (if configured) and eSpeak NG (always available).
    """
    voices = []

    # Add ElevenLabs voices if configured
    if elevenlabs_client.api_key:
        voices.extend(elevenlabs_client.get_professional_voices())

    # Add eSpeak NG voices (always available as fallback)
    voices.extend(get_espeak_voices())

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

    FIX V0.3 (Fase 1 Estabilizacion Hub V03 - P2): devuelve la estructura
    PLANA { configured, voices_count, message } en lugar de la version
    anidada previa { elevenlabs: {...}, espeak: {...} }. Esto alinea el
    contrato HTTP con lo que el cliente TypeScript (api.ts) ya consume
    desde V0.2 para la barra de estado inferior del Hub.

    Mantenemos la informacion completa de ambos proveedores (ElevenLabs
    + eSpeak) en claves adicionales para no perder capacidad de
    diagnostico, pero la lectura principal del estado es la clave
    plana de mas arriba.
    """
    elevenlabs_status = bool(elevenlabs_client.api_key)
    espeak_status = is_espeak_available()

    # Estado principal plano (contrato publico)
    if elevenlabs_status:
        configured = True
        voices_count = len(PROFESSIONAL_VOICES)
        source = "elevenlabs"
        message = "ElevenLabs configurado"
    elif espeak_status:
        configured = True
        voices_count = len(ESPEAK_VOICES)
        source = "espeak"
        message = "eSpeak NG disponible (fallback offline)"
    else:
        configured = False
        voices_count = 0
        source = "none"
        message = "Sin motor de voz configurado"

    return JSONResponse(content={
        # Contrato principal (estructura plana) - V0.3
        "configured": configured,
        "voices_count": voices_count,
        "message": message,
        "source": source,
        # Detalle adicional de ambos proveedores (no rompe compatibilidad
        # con clientes que ya lean las claves anidadas)
        "elevenlabs": {
            "configured": elevenlabs_status,
            "voices_count": len(PROFESSIONAL_VOICES),
            "message": "ElevenLabs ready" if elevenlabs_status else "Set ELEVENLABS_API_KEY for AI voices"
        },
        "espeak": {
            "available": espeak_status,
            "voices_count": len(ESPEAK_VOICES),
            "message": "eSpeak NG ready" if espeak_status else "Install eSpeak NG for offline voices"
        },
        "fallback": "espeak" if espeak_status else "none",
        "recommended": "elevenlabs" if elevenlabs_status else ("espeak" if espeak_status else "none")
    })


@router.post("/synthesize")
async def synthesize(request: SynthesizeRequest) -> Response:
    """
    Synthesize speech from text.
    
    Priority:
    1. ElevenLabs (if API key configured)
    2. eSpeak NG (offline fallback)
    
    Returns MP3/WAV audio data.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    # Try ElevenLabs first
    if elevenlabs_client.api_key:
        try:
            audio_data = await elevenlabs_synthesize(
                text=request.text,
                voice_id=request.voice_id,
                use_stream=request.use_stream
            )
            if audio_data:
                return Response(
                    content=audio_data,
                    media_type="audio/mpeg",
                    headers={"Content-Disposition": 'inline; filename="speech.mp3"'}
                )
            # elevenlabs_synthesize devolvio None (fallo silencioso en el
            # cliente). V0.83 (fix): no seguimos al fallback sin avisar
            # porque el usuario queda colgado sin saber que ElevenLabs fallo.
            # Levantamos 502 con detalle del problema y el codigo HTTP.
            raise HTTPException(
                status_code=502,
                detail="ElevenLabs devolvio audio vacio. Revisa la API key, el voice_id, o si tu cuenta tiene cuota.",
            )
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

    # Si llegamos aqui, ElevenLabs no estaba configurado. Fallback a eSpeak.
    if is_espeak_available():
        # Map ElevenLabs voice IDs to eSpeak voice keys
        espeak_voice_map = {
            "XB0fDUnXU5powGXd8GSW": "es_female",  # Spanish
            "VRgBjM5LWMVLQdJBADuO": "es_male",
            "EXAVITQu4vr4xnSDxMaL": "en_female",  # English
            "21m00Tcm4TlvDq8ikWAM": "en_us_female",
            "TxGEqnHWrfWFTfGW9Uj1": "en_male",
            "CYw3kZ02XxukaQ43fj0C": "en_us_male",
            "M0XMcJl3aMSh0bL3V0tX": "ja_female",  # Japanese
            "Xb7hH8MSDhxAmzVbBvjN": "ja_male",
            "GMwe3DBXQwAEkbqiQDhK": "fr_male",  # French
            "TxhqxN7eKXvBdrCDK0Kz": "zh_female",  # Chinese
        }
        
        espeak_key = espeak_voice_map.get(request.voice_id, "es_female")
        audio_data = synthesize_offline(request.text, espeak_key)
        
        if audio_data:
            return Response(
                content=audio_data,
                media_type="audio/wav",
                headers={"Content-Disposition": 'inline; filename="speech.wav"'}
            )
    
    # No synthesis available
    raise HTTPException(
        status_code=503,
        detail="No voice synthesis available. Install eSpeak NG or configure ElevenLabs."
    )


@router.post("/synthesize/base64")
async def synthesize_base64(request: SynthesizeRequest) -> JSONResponse:
    """Synthesize speech and return as base64-encoded audio."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    # Try ElevenLabs first
    if elevenlabs_client.api_key:
        try:
            audio_data = await elevenlabs_synthesize(
                text=request.text,
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
            raise HTTPException(
                status_code=502,
                detail="ElevenLabs devolvio audio vacio.",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"ElevenLabs fallo: {type(e).__name__}: {e}",
            )

    # Fallback a eSpeak NG
    if is_espeak_available():
        espeak_voice_map = {
            "XB0fDUnXU5powGXd8GSW": "es_female",
            "21m00Tcm4TlvDq8ikWAM": "en_us_female",
            "M0XMcJl3aMSh0bL3V0tX": "ja_female",
        }
        espeak_key = espeak_voice_map.get(request.voice_id, "es_female")
        audio_data = synthesize_offline(request.text, espeak_key)
        
        if audio_data:
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            return JSONResponse(content={
                "audio": f"data:audio/wav;base64,{audio_b64}",
                "voice_id": request.voice_id,
                "format": "wav",
                "source": "espeak_ng"
            })
    
    raise HTTPException(
        status_code=503,
        detail="No voice synthesis available"
    )


@router.get("/espeak/install")
def espeak_install_guide() -> JSONResponse:
    """Get installation guide for eSpeak NG."""
    return JSONResponse(content={
        "name": "eSpeak NG",
        "description": "Software libre de síntesis de voz",
        "download_url": "https://github.com/espeak-ng/espeak-ng/releases",
        "installer": "espeak-ng-x64.msi",
        "portable": "espeak-ng-x64.zip",
        "languages": [
            "Spanish (es)", "English (en)", "French (fr)",
            "German (de)", "Italian (it)", "Portuguese (pt)",
            "Japanese (ja)", "Chinese (zh)", "Russian (ru)",
            "And 100+ more languages"
        ],
        "instructions": [
            "1. Download eSpeak NG from GitHub",
            "2. Install or extract to a folder",
            "3. Add the folder to PATH, or",
            "4. Place in 'voces/espeak-ng' subfolder of Aithera backend"
        ]
    })


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
        # las siguientes son <2s para clips de 5s.
        try:
            result = transcribe(tmp_path, language=language)
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
