# tests/test_voice_text_clean.py
#
# El TTS no debe leer ni describir emoticonos (ej. decir "carita sonriente"
# al llegar a un "😊"): se quedan solo en el texto del chat. Cubre el filtro
# `strip_emojis` en aislamiento y que el endpoint /voice/synthesize/base64
# lo aplica de verdad antes de mandar el texto a un proveedor.

import pytest

from app.voice.text_clean import strip_emojis


# ----------------------------------------------------------------------
# strip_emojis() en aislamiento
# ----------------------------------------------------------------------

def test_texto_sin_emoticonos_no_cambia():
    assert strip_emojis("Hola, ¿cómo estás?") == "Hola, ¿cómo estás?"


def test_quita_emoticono_simple():
    assert strip_emojis("¡Genial! 😊") == "¡Genial!"


def test_quita_emoticono_en_medio_y_colapsa_espacios():
    assert strip_emojis("Genial 😊 gracias") == "Genial gracias"


def test_quita_varios_emoticonos_distintos_bloques():
    # cara (1F600-64F), pictograma (1F300-5FF), dingbat (2700-27BF),
    # bandera (regional indicator 1F1E6-1FF)
    assert strip_emojis("Hecho ✅ 🎉 vamos 🇪🇸!") == "Hecho vamos !"


def test_quita_emoji_compuesto_con_zwj_y_variation_selector():
    # familia con ZWJ + variation selector -16
    texto = "Te quiero ❤️‍🔥 mucho"
    limpio = strip_emojis(texto)
    assert "❤" not in limpio and "‍" not in limpio and "️" not in limpio
    assert limpio == "Te quiero mucho"


def test_texto_solo_emoticonos_queda_vacio():
    assert strip_emojis("👍👍👍") == ""


def test_string_vacio_no_rompe():
    assert strip_emojis("") == ""


def test_no_toca_acentos_ni_puntuacion_normal():
    texto = "¿Vale? ¡Perfecto! Ñoño — texto normal, con comas, y punto."
    assert strip_emojis(texto) == texto


# ----------------------------------------------------------------------
# El filtro esta REALMENTE conectado en el endpoint (no solo en la funcion)
# ----------------------------------------------------------------------

def test_synthesize_base64_quita_emoji_antes_de_llamar_al_proveedor(client, monkeypatch):
    import app.api.endpoints.voice as voice_ep

    captured = {}

    async def _fake_edgetts(text, voice):
        captured["text"] = text
        return b"fake-mp3-bytes"

    monkeypatch.setattr(voice_ep.edgetts_client, "synthesize_mp3", _fake_edgetts)

    r = client.post(
        "/api/voice/synthesize/base64",
        json={"text": "Hola 😊 ¿qué tal?", "provider": "edgetts"},
    )
    assert r.status_code == 200
    assert captured["text"] == "Hola ¿qué tal?"
    assert "😊" not in captured["text"]


def test_synthesize_base64_texto_solo_emoji_devuelve_422(client):
    r = client.post(
        "/api/voice/synthesize/base64",
        json={"text": "🎉🎉🎉", "provider": "edgetts"},
    )
    assert r.status_code == 422
