# Voice Synthesis API Endpoints - Supports both ElevenLabs and eSpeak NG
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Union
import base64
import io

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
        except Exception as e:
            print(f"ElevenLabs failed, trying eSpeak: {e}")
    
    # Fallback to eSpeak NG
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
        except Exception as e:
            print(f"ElevenLabs failed: {e}")
    
    # Fallback to eSpeak NG
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
