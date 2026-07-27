# tests/test_kokoro_voice.py — Kokoro-onnx, voz local sin Docker (A·VOZ-5, doc 32)
#
# Cubre el MOTOR (kokoro_voice.py) y el router (/api/voice/kokoro/*) sin tocar la
# red ni descargar ningún modelo real: la librería kokoro-onnx se sustituye por
# un doble, y la descarga del modelo se mockea. Blinda: is_available depende de
# librería + modelo, síntesis produce WAV, la instalación es idempotente y con
# progreso, y —lo importante— el fallback a EdgeTTS cuando Kokoro falla (nunca
# voz muda, doc 32 §4).
import io
import wave

import pytest

from app.voice import kokoro_voice as kv


# ----------------------------------------------------------------------
# Fixtures: aislar KOKORO_DIR en un tmp para no tocar %APPDATA% real.
# ----------------------------------------------------------------------
@pytest.fixture
def kdir(tmp_path, monkeypatch):
    monkeypatch.setattr(kv, "KOKORO_DIR", tmp_path)
    # cada test arranca con el cliente sin instancia cacheada
    kv.kokoro_client._kokoro = None
    kv.kokoro_client.last_error = None
    return tmp_path


def _touch_model(kdir):
    (kdir / kv.MODEL_FILENAME).write_bytes(b"fake-onnx")
    (kdir / kv.VOICES_FILENAME).write_bytes(b"fake-voices")


# ----------------------------------------------------------------------
# Motor: disponibilidad (librería + modelo) y mapa de idiomas
# ----------------------------------------------------------------------
def test_no_disponible_sin_modelo_aunque_este_la_libreria(kdir, monkeypatch):
    monkeypatch.setattr(kv, "library_installed", lambda: True)
    assert kv.model_downloaded() is False
    assert kv.kokoro_client.is_available() is False


def test_no_disponible_sin_libreria_aunque_este_el_modelo(kdir, monkeypatch):
    _touch_model(kdir)
    monkeypatch.setattr(kv, "library_installed", lambda: False)
    assert kv.model_downloaded() is True
    assert kv.kokoro_client.is_available() is False


def test_disponible_con_libreria_y_modelo(kdir, monkeypatch):
    _touch_model(kdir)
    monkeypatch.setattr(kv, "library_installed", lambda: True)
    assert kv.kokoro_client.is_available() is True


def test_acepta_modelo_completo_si_no_esta_el_cuantizado(kdir):
    (kdir / kv.MODEL_FILENAME_FULL).write_bytes(b"fake-full-onnx")
    (kdir / kv.VOICES_FILENAME).write_bytes(b"fake-voices")
    assert kv.model_path() is not None
    assert kv.model_path().name == kv.MODEL_FILENAME_FULL


@pytest.mark.parametrize("voice,lang", [
    ("ef_dora", "es"), ("em_alex", "es"), ("af_heart", "en-us"),
    ("bf_emma", "en-gb"), ("ff_siwis", "fr-fr"), ("pf_dora", "pt-br"),
    ("", "es"),          # voz vacía -> prefijo "e" -> español (app es ES-primero)
    ("x_raro", "en-us"), # prefijo desconocido -> default en-us
])
def test_mapa_de_idioma_por_prefijo(voice, lang):
    assert kv.kokoro_client._lang_of(voice) == lang


# ----------------------------------------------------------------------
# Motor: síntesis produce WAV válido (con un doble de kokoro-onnx)
# ----------------------------------------------------------------------
class _FakeKokoro:
    def __init__(self, samples, sr=24000):
        self._samples = samples
        self._sr = sr
        self.seen = {}

    def create(self, text, voice="ef_dora", speed=1.0, lang="es"):
        import numpy as np
        self.seen = {"text": text, "voice": voice, "speed": speed, "lang": lang}
        return np.asarray(self._samples, dtype=np.float32), self._sr


def test_synthesize_wav_produce_wav_valido(kdir):
    np = pytest.importorskip("numpy")
    fake = _FakeKokoro(np.linspace(-0.5, 0.5, 2400))
    kv.kokoro_client._kokoro = fake  # inyecta el doble (evita cargar ONNX real)

    out = kv.kokoro_client.synthesize_wav("hola Alejandro", voice="ef_dora", speed=1.1)
    assert out is not None and out[:4] == b"RIFF"     # cabecera WAV
    # el WAV es reproducible y coherente (24 kHz, mono, 16-bit)
    with wave.open(io.BytesIO(out), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == 24000
        assert w.getnframes() == 2400
    # el idioma se derivó de la voz española, no del default
    assert fake.seen["lang"] == "es"
    assert fake.seen["speed"] == 1.1
    assert kv.kokoro_client.last_error is None


def test_synthesize_wav_none_si_no_hay_audio(kdir):
    np = pytest.importorskip("numpy")
    kv.kokoro_client._kokoro = _FakeKokoro(np.asarray([], dtype=np.float32))
    out = kv.kokoro_client.synthesize_wav("hola")
    assert out is None
    assert "no generó audio" in (kv.kokoro_client.last_error or "")


def test_synthesize_wav_captura_excepcion_del_modelo(kdir):
    class _Boom:
        def create(self, *a, **k):
            raise RuntimeError("onnx se rompió")

    kv.kokoro_client._kokoro = _Boom()
    out = kv.kokoro_client.synthesize_wav("hola")
    assert out is None
    assert "onnx se rompió" in (kv.kokoro_client.last_error or "")


# ----------------------------------------------------------------------
# Router: /kokoro/status refleja librería + modelo + progreso
# ----------------------------------------------------------------------
def test_kokoro_status_sin_nada(client, kdir, monkeypatch):
    monkeypatch.setattr(kv, "library_installed", lambda: False)
    r = client.get("/api/voice/kokoro/status")
    assert r.status_code == 200
    d = r.json()
    for key in ("available", "library_installed", "model_downloaded",
                "install_status", "progress", "message"):
        assert key in d
    assert d["available"] is False
    assert d["library_installed"] is False


def test_kokoro_status_libreria_sin_modelo(client, kdir, monkeypatch):
    monkeypatch.setattr(kv, "library_installed", lambda: True)
    r = client.get("/api/voice/kokoro/status")
    d = r.json()
    assert d["library_installed"] is True
    assert d["model_downloaded"] is False
    assert d["available"] is False
    assert "falta el modelo" in d["message"]


def test_kokoro_status_listo(client, kdir, monkeypatch):
    _touch_model(kdir)
    monkeypatch.setattr(kv, "library_installed", lambda: True)
    r = client.get("/api/voice/kokoro/status")
    d = r.json()
    assert d["available"] is True
    assert "listo" in d["message"].lower()


def test_kokoro_voices_contrato(client):
    r = client.get("/api/voice/kokoro/voices")
    assert r.status_code == 200
    voices = r.json()["voices"]
    assert any(v["lang"] == "es" for v in voices)   # español presente
    # español primero (criterio curado)
    assert voices[0]["lang"] == "es"


# ----------------------------------------------------------------------
# Router: /kokoro/install es idempotente
# ----------------------------------------------------------------------
def test_install_no_duplica_si_ya_esta_listo(client, kdir, monkeypatch):
    _touch_model(kdir)
    monkeypatch.setattr(kv, "library_installed", lambda: True)
    r = client.post("/api/voice/kokoro/install")
    d = r.json()
    assert d["started"] is False
    assert "listo" in d["message"].lower()


def test_install_no_duplica_si_ya_en_curso(client, kdir, monkeypatch):
    import app.api.endpoints.voice as voice_ep
    monkeypatch.setattr(kv, "library_installed", lambda: False)
    monkeypatch.setitem(voice_ep._KOKORO_INSTALL, "status", "downloading")
    try:
        r = client.post("/api/voice/kokoro/install")
        assert r.json()["started"] is False
    finally:
        voice_ep._KOKORO_INSTALL["status"] = "idle"


# ----------------------------------------------------------------------
# Router: el worker de instalación NO toca la red (pip + descarga mockeados)
# ----------------------------------------------------------------------
def test_install_worker_mockeado_llega_a_done(kdir, monkeypatch):
    import app.api.endpoints.voice as voice_ep

    # librería "ya instalada" -> se salta pip; solo prueba la fase de descarga
    monkeypatch.setattr(kv, "library_installed", lambda: True)

    def _fake_dl(url, dest, label):
        dest.write_bytes(b"downloaded")   # simula la descarga sin red

    monkeypatch.setattr(voice_ep, "_download_with_progress", _fake_dl)
    voice_ep._KOKORO_INSTALL.update(status="installing", detail=None, progress=0)
    try:
        voice_ep._kokoro_install_worker()
        assert voice_ep._KOKORO_INSTALL["status"] == "done"
        assert kv.model_downloaded() is True
    finally:
        voice_ep._KOKORO_INSTALL.update(status="idle", detail=None, progress=0)


# ----------------------------------------------------------------------
# Cadena/factoría: Kokoro que falla -> fallback a EdgeTTS (nunca voz muda)
# ----------------------------------------------------------------------
def test_synthesize_kokoro_falla_cae_a_edgetts(client, monkeypatch):
    import app.api.endpoints.voice as voice_ep

    # Kokoro devuelve None (fallo): no debe dar 502, debe caer a EdgeTTS.
    def _kokoro_falla(text, voice="ef_dora"):
        voice_ep.kokoro_client.last_error = "modelo no descargado"
        return None

    monkeypatch.setattr(voice_ep.kokoro_client, "synthesize_wav", _kokoro_falla)

    async def _edge_ok(text, voice):
        return b"fake-mp3-bytes"

    monkeypatch.setattr(voice_ep.edgetts_client, "synthesize_mp3", _edge_ok)

    r = client.post("/api/voice/synthesize", json={
        "text": "hola", "provider": "kokoro", "voice_id": "ef_dora",
    })
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/mpeg")   # MP3 de EdgeTTS


def test_synthesize_base64_kokoro_falla_cae_a_edgetts(client, monkeypatch):
    import app.api.endpoints.voice as voice_ep

    monkeypatch.setattr(voice_ep.kokoro_client, "synthesize_wav",
                        lambda text, voice="ef_dora": None)

    async def _edge_ok(text, voice):
        return b"fake-mp3-bytes"

    monkeypatch.setattr(voice_ep.edgetts_client, "synthesize_mp3", _edge_ok)

    r = client.post("/api/voice/synthesize/base64", json={
        "text": "hola", "provider": "kokoro",
    })
    assert r.status_code == 200
    d = r.json()
    assert d["source"] == "edgetts"     # el fallback se refleja en 'source'
    assert d["format"] == "mp3"
