# tests/test_voice.py
#
# V0.83 (Voz): contrato del router /api/voice. Cubre TTS status (estructura
# plana congelada desde V0.3), STT status y /transcribe (503 cuando el STT no
# esta disponible + camino feliz con faster-whisper mockeado). No se toca la
# red ni se descarga ningun modelo real.

import io

import pytest


# ----------------------------------------------------------------------
# /voice/status — contrato plano (lo consume la barra de estado del Hub)
# ----------------------------------------------------------------------

def test_voice_status_contrato_plano(client):
    r = client.get("/api/voice/status")
    assert r.status_code == 200
    data = r.json()
    # claves planas del contrato publico (V0.3 P2)
    for key in ("configured", "voices_count", "message", "source"):
        assert key in data
    assert isinstance(data["configured"], bool)
    assert isinstance(data["voices_count"], int)
    # detalle por proveedor sin romper compatibilidad
    assert "elevenlabs" in data and "espeak" in data


# ----------------------------------------------------------------------
# /voice/stt/status — estado del STT local
# ----------------------------------------------------------------------

def test_stt_status_shape(client):
    r = client.get("/api/voice/stt/status")
    assert r.status_code == 200
    data = r.json()
    assert "available" in data and isinstance(data["available"], bool)
    assert "model" in data
    # 'reason' distingue lib ausente / modelo no cargado / disponible
    assert "reason" in data


# ----------------------------------------------------------------------
# /voice/transcribe — 503 si el STT no esta disponible
# ----------------------------------------------------------------------

def test_transcribe_503_si_stt_no_disponible(client, monkeypatch):
    import app.api.endpoints.voice as voice_ep

    def _boom(path, language="es"):
        raise RuntimeError("faster-whisper no esta instalado. Instala con ...")

    monkeypatch.setattr(voice_ep, "transcribe", _boom)
    files = {"audio": ("rec.webm", io.BytesIO(b"fake-audio-bytes"), "audio/webm")}
    r = client.post("/api/voice/transcribe?language=es", files=files)
    assert r.status_code == 503
    assert "STT no disponible" in r.json()["detail"]


# ----------------------------------------------------------------------
# /voice/transcribe — camino feliz con transcribe mockeado
# ----------------------------------------------------------------------

def test_transcribe_ok_con_mock(client, monkeypatch):
    import app.api.endpoints.voice as voice_ep

    def _fake_transcribe(path, language="es"):
        assert language == "es"           # el endpoint fuerza es
        return {
            "text": "hola aithera",
            "language": "es",
            "language_probability": 0.99,
            "duration": 1.23,
            "segments": [{"start": 0.0, "end": 1.2, "text": "hola aithera"}],
        }

    monkeypatch.setattr(voice_ep, "transcribe", _fake_transcribe)
    files = {"audio": ("rec.webm", io.BytesIO(b"fake"), "audio/webm")}
    r = client.post("/api/voice/transcribe?language=es", files=files)
    assert r.status_code == 200
    assert r.json()["text"] == "hola aithera"


def test_transcribe_rechaza_content_type_no_audio(client):
    files = {"audio": ("nota.txt", io.BytesIO(b"no soy audio"), "text/plain")}
    r = client.post("/api/voice/transcribe", files=files)
    assert r.status_code == 400
