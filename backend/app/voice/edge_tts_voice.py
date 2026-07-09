"""
EdgeTTS — voces neuronales de Microsoft (V0.83). GRATIS, sin API key; solo
requiere internet. Devuelve MP3 (bytes) que reproduce el frontend. Buena calidad
y sin descargar modelos, así que es la opción más ligera para distribuir.
Referencia: Mark-XL `core/tts.py`.

Instalar: `pip install edge-tts`.
"""
from __future__ import annotations

from typing import List, Optional

# Lista curada de voces habituales (EdgeTTS tiene cientos; estas cubren ES/EN).
EDGE_VOICES: List[dict] = [
    {"id": "es-ES-ElviraNeural", "name": "Elvira (España ♀)", "lang": "es"},
    {"id": "es-ES-AlvaroNeural", "name": "Álvaro (España ♂)", "lang": "es"},
    {"id": "es-MX-DaliaNeural",  "name": "Dalia (México ♀)",  "lang": "es"},
    {"id": "es-MX-JorgeNeural",  "name": "Jorge (México ♂)",  "lang": "es"},
    {"id": "en-US-AriaNeural",   "name": "Aria (EN-US ♀)",    "lang": "en"},
    {"id": "en-US-GuyNeural",    "name": "Guy (EN-US ♂)",     "lang": "en"},
    {"id": "en-GB-SoniaNeural",  "name": "Sonia (EN-UK ♀)",   "lang": "en"},
]


class EdgeTTSVoice:
    def __init__(self) -> None:
        self.last_error: Optional[str] = None

    def is_available(self) -> bool:
        try:
            import edge_tts  # noqa: F401
            return True
        except Exception:
            return False

    async def synthesize_mp3(
        self, text: str, voice: str = "es-ES-ElviraNeural"
    ) -> Optional[bytes]:
        """Genera MP3 (bytes). None + last_error si falla."""
        try:
            import edge_tts
        except Exception as e:
            self.last_error = f"edge-tts no instalado: {e}. Ejecuta: pip install edge-tts"
            return None
        try:
            comm = edge_tts.Communicate(text, voice or "es-ES-ElviraNeural")
            buf = bytearray()
            async for chunk in comm.stream():
                if chunk.get("type") == "audio":
                    buf.extend(chunk["data"])
            if not buf:
                self.last_error = "EdgeTTS no devolvió audio."
                return None
            self.last_error = None
            return bytes(buf)
        except Exception as e:
            self.last_error = f"EdgeTTS falló (¿sin internet?): {type(e).__name__}: {e}"
            return None


edgetts_client = EdgeTTSVoice()
