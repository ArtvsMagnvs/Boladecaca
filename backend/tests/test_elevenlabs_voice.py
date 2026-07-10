# tests/test_elevenlabs_voice.py
#
# FIX (audit sistema de audio, 2026-07-10): synthesize_stream() es el camino
# POR DEFECTO de sintesis (SynthesizeRequest.use_stream=True), pero a
# diferencia de synthesize() no dejaba last_error al fallar por excepcion de
# red. El endpoint /voice/synthesize muestra last_error como el motivo del
# 502; sin este fix, un fallo de red en el camino por defecto mostraba un
# error generico o el de una llamada anterior no relacionada.

import pytest

from app.voice.elevenlabs_voice import ElevenLabsVoice


@pytest.mark.anyio
async def test_synthesize_stream_excepcion_de_red_deja_last_error(monkeypatch):
    client = ElevenLabsVoice(api_key="fake-key-for-test")

    async def _boom(*args, **kwargs):
        raise ConnectionError("DNS resolution failed")

    monkeypatch.setattr(client.client, "post", _boom)

    result = await client.synthesize_stream("hola", voice_id="XB0fDUnXU5powGXd8GSW")

    assert result is None
    assert client.last_error is not None
    assert "ConnectionError" in client.last_error or "DNS resolution failed" in client.last_error


@pytest.mark.anyio
async def test_synthesize_stream_exito_limpia_last_error_previo(monkeypatch):
    client = ElevenLabsVoice(api_key="fake-key-for-test")
    client.last_error = "error de una llamada anterior"

    class _FakeResponse:
        status_code = 200
        content = b"fake-mp3-bytes"

    async def _ok(*args, **kwargs):
        return _FakeResponse()

    monkeypatch.setattr(client.client, "post", _ok)

    result = await client.synthesize_stream("hola", voice_id="XB0fDUnXU5powGXd8GSW")

    assert result == b"fake-mp3-bytes"
    assert client.last_error is None
