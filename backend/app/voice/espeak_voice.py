"""
eSpeak NG Text-to-Speech Module for Aithera.
Uses eSpeak NG for offline, free professional voices.
"""
import os
import subprocess
import tempfile
import asyncio
from typing import Optional, List, Dict, Any

# eSpeak NG configuration
ESPEAK_VOICES = {
    # Spanish voices
    "es_female": {
        "lang": "es",
        "voice": "es",
        "name": "María (Español)",
        "gender": "female"
    },
    "es_male": {
        "lang": "es",
        "voice": "es-la",
        "name": "Carlos (Español)",
        "gender": "male"
    },
    
    # English voices
    "en_female": {
        "lang": "en",
        "voice": "en",
        "name": "Emma (English)",
        "gender": "female"
    },
    "en_male": {
        "lang": "en-gb",
        "voice": "en-gb",
        "name": "James (English UK)",
        "gender": "male"
    },
    "en_us_female": {
        "lang": "en-us",
        "voice": "en-us",
        "name": "Rachel (English US)",
        "gender": "female"
    },
    "en_us_male": {
        "lang": "en-us",
        "voice": "en-us-semi",
        "name": "David (English US)",
        "gender": "male"
    },
    
    # Japanese voices
    "ja_female": {
        "lang": "ja",
        "voice": "ja",
        "name": "Sakura (日本語)",
        "gender": "female"
    },
    "ja_male": {
        "lang": "ja",
        "voice": "ja",
        "name": "Kenji (日本語)",
        "gender": "male"
    },
    
    # French voices
    "fr_female": {
        "lang": "fr",
        "voice": "fr",
        "name": "Béatrice (Français)",
        "gender": "female"
    },
    "fr_male": {
        "lang": "fr",
        "voice": "fr-be",
        "name": "Henri (Français)",
        "gender": "male"
    },
    
    # German voices
    "de_female": {
        "lang": "de",
        "voice": "de",
        "name": "Klara (Deutsch)",
        "gender": "female"
    },
    "de_male": {
        "lang": "de",
        "voice": "de",
        "name": "Hans (Deutsch)",
        "gender": "male"
    },
    
    # Italian voices
    "it_female": {
        "lang": "it",
        "voice": "it",
        "name": "Elsa (Italiano)",
        "gender": "female"
    },
    "it_male": {
        "lang": "it",
        "voice": "it",
        "name": "Luca (Italiano)",
        "gender": "male"
    },
    
    # Portuguese voices
    "pt_female": {
        "lang": "pt",
        "voice": "pt",
        "name": "Amelia (Português)",
        "gender": "female"
    },
    "pt_male": {
        "lang": "pt",
        "voice": "pt",
        "name": "Antonio (Português)",
        "gender": "male"
    },
    
    # Chinese voices
    "zh_female": {
        "lang": "zh",
        "voice": "zh",
        "name": "Lin (中文)",
        "gender": "female"
    },
    "zh_male": {
        "lang": "zh",
        "voice": "zh",
        "name": "Wei (中文)",
        "gender": "male"
    },
}


class eSpeakVoice:
    """eSpeak NG TTS client for offline professional voices."""
    
    def __init__(self):
        self.espeak_path = self._find_espeak()
    
    def _find_espeak(self) -> Optional[str]:
        """Find eSpeak NG executable."""
        # Check common locations
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        paths_to_check = [
            os.path.join(base_dir, "voces", "espeak-ng", "espeak-ng.exe"),
            os.path.join(base_dir, "voces", "espeak-ng", "espeak.exe"),
            r"C:\Program Files\eSpeak NG\espeak-ng.exe",
            r"C:\Program Files (x86)\eSpeak NG\espeak-ng.exe",
        ]
        
        for path in paths_to_check:
            if os.path.exists(path):
                return path
        
        # Try to find in PATH
        try:
            result = subprocess.run(["where", "espeak-ng"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        return None
    
    def is_available(self) -> bool:
        """Check if eSpeak NG is installed."""
        return self.espeak_path is not None
    
    def synthesize(self, text: str, voice_key: str = "es_female", 
                 speed: int = 175, pitch: int = 50) -> Optional[bytes]:
        """
        Synthesize speech using eSpeak NG.
        
        Args:
            text: Text to synthesize
            voice_key: Key from ESPEAK_VOICES dict
            speed: Speech speed (words per minute, default 175)
            pitch: Voice pitch (0-100, default 50)
        
        Returns:
            WAV audio data as bytes, or None if failed
        """
        if not self.is_available():
            return None
        
        voice = ESPEAK_VOICES.get(voice_key, ESPEAK_VOICES["es_female"])
        
        try:
            # Create temp file for output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                output_path = tmp.name
            
            # Build command
            cmd = [
                self.espeak_path,
                "-w", output_path,
                "-v", voice["voice"],
                "-s", str(speed),
                "-p", str(pitch),
                text
            ]
            
            # Run synthesis
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode != 0:
                print(f"eSpeak error: {result.stderr}")
                return None
            
            # Read output
            with open(output_path, "rb") as f:
                audio_data = f.read()
            
            # Cleanup
            try:
                os.unlink(output_path)
            except:
                pass
            
            return audio_data
            
        except subprocess.TimeoutExpired:
            print("eSpeak synthesis timeout")
            return None
        except Exception as e:
            print(f"eSpeak synthesis error: {e}")
            return None
    
    def synthesize_to_mp3(self, text: str, voice_key: str = "es_female",
                        speed: int = 175, pitch: int = 50) -> Optional[bytes]:
        """
        Synthesize speech and convert to MP3 using eSpeak NG.
        """
        if not self.is_available():
            return None
        
        voice = ESPEAK_VOICES.get(voice_key, ESPEAK_VOICES["es_female"])
        
        try:
            # First synthesize to WAV
            wav_data = self.synthesize(text, voice_key, speed, pitch)
            if not wav_data:
                return None
            
            # For now, return WAV data (MP3 requires additional library)
            # Can be converted with: ffmpeg -i input.wav -codec:a libmp3lame output.mp3
            return wav_data
            
        except Exception as e:
            print(f"eSpeak MP3 conversion error: {e}")
            return None
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available eSpeak voices."""
        voices = []
        for key, voice in ESPEAK_VOICES.items():
            voices.append({
                "id": key,
                "name": voice["name"],
                "lang": voice["lang"],
                "gender": voice["gender"],
                "type": "espeak_ng",
                "offline": True
            })
        return voices
    
    def get_voice_info(self, voice_key: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific voice."""
        voice = ESPEAK_VOICES.get(voice_key)
        if voice:
            return {
                "id": voice_key,
                "name": voice["name"],
                "lang": voice["lang"],
                "gender": voice["gender"],
                "type": "espeak_ng"
            }
        return None


# Global instance
espeak_client = eSpeakVoice()


def synthesize_offline(text: str, voice_key: str = "es_female") -> Optional[bytes]:
    """Convenience function to synthesize speech offline."""
    return espeak_client.synthesize(text, voice_key)


def get_espeak_voices() -> List[Dict[str, Any]]:
    """Get all available eSpeak voices."""
    return espeak_client.get_available_voices()


def is_espeak_available() -> bool:
    """Check if eSpeak NG is installed."""
    return espeak_client.is_available()
