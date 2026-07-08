"""
ElevenLabs Text-to-Speech Module for Aithera.
Provides high-quality voice synthesis with professional voices.
"""
import os
import base64
import json
import httpx
from typing import Optional, List, Dict, Any

# ElevenLabs API configuration
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"

# Professional voices from ElevenLabs (predefined for common languages)
PROFESSIONAL_VOICES = {
    # Spanish voices
    "es_female_1": {
        "id": "XB0fDUnXU5powGXd8GSW",  # Maria (Spanish)
        "name": "María (Español)",
        "lang": "es",
        "gender": "female",
        "description": "Profesional, cálida"
    },
    "es_female_2": {
        "id": "VRgBjM5LWMVLQdJBADuO",  # Sara (Spanish)
        "name": "Sara (Español MX)",
        "lang": "es",
        "gender": "female",
        "description": "Amigable, moderna"
    },
    "es_male_1": {
        "id": "pFZInIHuG2YLLnwAkyrJ",  # Alejandro (Spanish)
        "name": "Alejandro (Español)",
        "lang": "es",
        "gender": "male",
        "description": "Profesional, serio"
    },
    
    # English voices
    "en_female_1": {
        "id": "EXAVITQu4vr4xnSDxMaL",  # Bella
        "name": "Bella (English)",
        "lang": "en",
        "gender": "female",
        "description": "Joven, expresiva"
    },
    "en_female_2": {
        "id": "21m00Tcm4TlvDq8ikWAM",  # Rachel
        "name": "Rachel (English)",
        "lang": "en",
        "gender": "female",
        "description": "Clara, profesional"
    },
    "en_male_1": {
        "id": "TxGEqnHWrfWFTfGW9Uj1",  # Arnold
        "name": "Arnold (English)",
        "lang": "en",
        "gender": "male",
        "description": "Fuerte, profundo"
    },
    "en_male_2": {
        "id": "CYw3kZ02XxukaQ43fj0C",  # Josh
        "name": "Josh (English)",
        "lang": "en",
        "gender": "male",
        "description": "Casual, amigable"
    },
    
    # Japanese voices
    "ja_female_1": {
        "id": "M0XMcJl3aMSh0bL3V0tX",  # Airi
        "name": "Airi (日本語)",
        "lang": "ja",
        "gender": "female",
        "description": "Femenina, joven"
    },
    "ja_male_1": {
        "id": "Xb7hH8MSDhxAmzVbBvjN",  # Kenji
        "name": "Kenji (日本語)",
        "lang": "ja",
        "gender": "male",
        "description": "Masculino, formal"
    },
    
    # French voices
    "fr_female_1": {
        "id": "GMwe3DBXQwAEkbqiQDhK",  # Antoine
        "name": "Antoine (Français)",
        "lang": "fr",
        "gender": "male",
        "description": "Masculino, elegante"
    },
    
    # Chinese voices
    "zh_female_1": {
        "id": "TxhqxN7eKXvBdrCDK0Kz",  # Fei
        "name": "Fei (中文)",
        "lang": "zh",
        "gender": "female",
        "description": "Femenina, moderna"
    },
}


def resolve_elevenlabs_key() -> str:
    """Devuelve la API key de ElevenLabs con prioridad:
    1) Config en BD (`elevenlabs_api_key`, CIFRADA con DPAPI/secrets), que es
       lo que el usuario mete desde Ajustes.
    2) variable de entorno ELEVENLABS_API_KEY (compatibilidad).
    Se consulta en cada acceso (SQLite local, coste despreciable) para que un
    cambio desde Ajustes surta efecto sin reiniciar el backend."""
    try:
        from app.db.database import SessionLocal
        from app.db.models import Config
        from app.core import secrets

        db = SessionLocal()
        try:
            row = db.query(Config).filter(Config.key == "elevenlabs_api_key").first()
        finally:
            db.close()
        if row and row.value:
            return secrets.decrypt(row.value)
    except Exception:
        pass
    return os.environ.get("ELEVENLABS_API_KEY", "")


def _format_el_error(status: int, body: str) -> str:
    """Traduce la respuesta de error de ElevenLabs a un mensaje util.
    ElevenLabs suele devolver {'detail': {'status': ..., 'message': ...}}.
    402 con 'detected_unusual_activity' = plan gratuito bloqueado por uso via
    API/VPN (NO es cuota). 401 = key invalida. 429 = rate limit."""
    try:
        data = json.loads(body)
        d = data.get("detail")
        if isinstance(d, dict):
            st = d.get("status", "")
            msg = d.get("message", "")
            return f"ElevenLabs HTTP {status} · {st}: {msg}"[:400]
        return f"ElevenLabs HTTP {status}: {str(d or body)}"[:400]
    except Exception:
        return f"ElevenLabs HTTP {status}: {body}"[:400]


class ElevenLabsVoice:
    """ElevenLabs TTS client with professional voices."""

    def __init__(self, api_key: Optional[str] = None):
        # Si se pasa una key explicita (tests), se respeta; si no, se resuelve
        # dinamicamente desde Config/env via la property `api_key`.
        self._explicit_key = api_key
        self.base_url = ELEVENLABS_BASE_URL
        self.client = httpx.AsyncClient(timeout=30.0)
        # Ultimo error real de la API (para que el endpoint lo muestre en vez
        # de un generico "audio vacio"). None si la ultima llamada fue OK.
        self.last_error: Optional[str] = None

    @property
    def api_key(self) -> str:
        return self._explicit_key or resolve_elevenlabs_key()
    
    async def synthesize(
        self,
        text: str,
        voice_id: str = "XB0fDUnXU5powGXd8GSW",
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True
    ) -> Optional[bytes]:
        """
        Synthesize speech from text using ElevenLabs.
        
        Returns audio data as bytes, or None if failed.
        """
        if not self.api_key:
            return None
        
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }
        
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
                "use_speaker_boost": use_speaker_boost
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/text-to-speech/{voice_id}",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                self.last_error = None
                return response.content
            self.last_error = _format_el_error(response.status_code, response.text)
            print(self.last_error)
            return None

        except Exception as e:
            self.last_error = f"ElevenLabs error de red: {e}"
            print(self.last_error)
            return None
    
    async def synthesize_stream(
        self,
        text: str,
        voice_id: str = "XB0fDUnXU5powGXd8GSW"
    ) -> Optional[bytes]:
        """Synthesize using streaming endpoint for lower latency."""
        if not self.api_key:
            return None
        
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }
        
        payload = {
            "text": text,
            "model_id": "eleven_flash_v2_5",  # Lowest latency model
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/text-to-speech/{voice_id}/stream",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                self.last_error = None
                return response.content
            self.last_error = _format_el_error(response.status_code, response.text)
            print(self.last_error)
            return None

        except Exception as e:
            print(f"ElevenLabs streaming error: {e}")
            return None
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of voices available in the account."""
        if not self.api_key:
            return list(PROFESSIONAL_VOICES.values())
        
        headers = {"xi-api-key": self.api_key}
        
        try:
            response = await self.client.get(
                f"{self.base_url}/voices",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("voices", [])
            else:
                return list(PROFESSIONAL_VOICES.values())
                
        except Exception as e:
            print(f"Error getting voices: {e}")
            return list(PROFESSIONAL_VOICES.values())
    
    async def close(self):
        await self.client.aclose()
    
    def get_professional_voices(self) -> List[Dict[str, Any]]:
        """Return the list of predefined professional voices."""
        return list(PROFESSIONAL_VOICES.values())
    
    def get_voice_by_id(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get voice info by ID."""
        for voice in PROFESSIONAL_VOICES.values():
            if voice["id"] == voice_id:
                return voice
        return None


# Global instance
voice_client = ElevenLabsVoice()


async def synthesize_speech(
    text: str,
    voice_id: str = "XB0fDUnXU5powGXd8GSW",
    use_stream: bool = True
) -> Optional[bytes]:
    """Convenience function to synthesize speech."""
    if use_stream:
        return await voice_client.synthesize_stream(text, voice_id)
    else:
        return await voice_client.synthesize(text, voice_id)


async def get_all_voices() -> List[Dict[str, Any]]:
    """Get all available voices (account + predefined)."""
    return voice_client.get_professional_voices()
