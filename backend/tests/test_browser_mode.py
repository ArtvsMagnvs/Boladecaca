# tests/test_browser_mode.py — modo de navegador: dedicado vs habitual
# (2026-07-23, petición del usuario)
#
# Lo que protege:
#   1. El endpoint persiste y por defecto es "aithera" (el modo SEGURO).
#   2. Un modo desconocido se rechaza (400), nunca se guarda basura.
#   3. `browser_tool._browser_mode()` lee lo persistido; sin BD legible
#      degrada a "aithera" (nunca revienta el arranque del navegador).
#   4. En modo "user", un fallo al abrir el Chrome real NUNCA sustituye en
#      silencio por el perfil dedicado (mismo criterio que
#      ExplicitModelUnfit/ExplicitModelUnavailable del MEL) — se avisa claro.
from __future__ import annotations

import pytest

from app.tools import browser_tool


@pytest.fixture(autouse=False)
def _clean_browser_mode():
    from app.db.database import SessionLocal
    from app.db.models import Config

    def _clean():
        db = SessionLocal()
        try:
            db.query(Config).filter(Config.key == "browser_mode").delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()
    _clean()
    yield
    _clean()


# ---------------------------------------------------------------------------
# 1-2. Endpoint
# ---------------------------------------------------------------------------
def test_modo_por_defecto_es_aithera(client, _clean_browser_mode):
    r = client.get("/api/search/browser-mode")
    assert r.status_code == 200
    assert r.json()["mode"] == "aithera"


def test_configurar_modo_user_se_persiste(client, _clean_browser_mode):
    r = client.post("/api/search/browser-mode", json={"mode": "user"})
    assert r.status_code == 200
    assert r.json()["mode"] == "user"

    r2 = client.get("/api/search/browser-mode")
    assert r2.json()["mode"] == "user"


def test_modo_desconocido_se_rechaza(client, _clean_browser_mode):
    r = client.post("/api/search/browser-mode", json={"mode": "incognito"})
    assert r.status_code == 400
    # no se guardó nada
    assert client.get("/api/search/browser-mode").json()["mode"] == "aithera"


# ---------------------------------------------------------------------------
# 3. Lectura desde browser_tool
# ---------------------------------------------------------------------------
def test_browser_mode_lee_lo_persistido(client, _clean_browser_mode):
    client.post("/api/search/browser-mode", json={"mode": "user"})
    assert browser_tool._browser_mode() == "user"

    client.post("/api/search/browser-mode", json={"mode": "aithera"})
    assert browser_tool._browser_mode() == "aithera"


def test_browser_mode_sin_bd_degrada_a_aithera(monkeypatch, _clean_browser_mode):
    def _revienta():
        raise RuntimeError("BD caida")
    monkeypatch.setattr("app.db.database.SessionLocal", _revienta)
    assert browser_tool._browser_mode() == "aithera"


# ---------------------------------------------------------------------------
# 4. `_ensure_browser` en modo "user": nunca sustituye en silencio
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_modo_user_sin_perfil_localizado_error_claro(monkeypatch):
    monkeypatch.setattr(browser_tool, "_browser_mode", lambda: "user")
    monkeypatch.setattr(browser_tool, "_user_chrome_profile_dir", lambda: None)
    monkeypatch.setattr(browser_tool, "_playwright", None)
    monkeypatch.setattr(browser_tool, "_browser", None)
    monkeypatch.setattr(browser_tool, "_persistent_context", None)

    class _FakePlaywright:
        async def start(self):
            return self
        chromium = None

    async def _fake_start():
        return _FakePlaywright()

    import sys
    import types
    fake_pw_module = types.ModuleType("playwright.async_api")
    fake_pw_module.async_playwright = lambda: types.SimpleNamespace(start=_fake_start)
    monkeypatch.setitem(sys.modules, "playwright.async_api", fake_pw_module)

    with pytest.raises(RuntimeError, match="No se encontró tu perfil de Chrome"):
        await browser_tool._ensure_browser()
    # Nunca cayó al perfil dedicado en silencio.
    assert browser_tool._persistent_context is None


@pytest.mark.anyio
async def test_modo_user_fallo_al_lanzar_no_sustituye_en_silencio(monkeypatch, tmp_path):
    """El caso real más probable: el usuario ya tiene Chrome abierto con ese
    perfil. El error debe ser CLARO y NO debe caer al perfil dedicado — el
    usuario eligió su Chrome a propósito."""
    monkeypatch.setattr(browser_tool, "_browser_mode", lambda: "user")
    monkeypatch.setattr(browser_tool, "_user_chrome_profile_dir", lambda: str(tmp_path))
    monkeypatch.setattr(browser_tool, "_playwright", None)
    monkeypatch.setattr(browser_tool, "_browser", None)
    monkeypatch.setattr(browser_tool, "_persistent_context", None)

    class _FakeChromium:
        async def launch_persistent_context(self, *a, **kw):
            raise RuntimeError("profile already in use")

    class _FakePlaywright:
        chromium = _FakeChromium()

    async def _fake_start():
        return _FakePlaywright()

    import sys
    import types
    fake_pw_module = types.ModuleType("playwright.async_api")
    fake_pw_module.async_playwright = lambda: types.SimpleNamespace(start=_fake_start)
    monkeypatch.setitem(sys.modules, "playwright.async_api", fake_pw_module)

    with pytest.raises(RuntimeError, match="ya lo tengas abierto"):
        await browser_tool._ensure_browser()
    assert browser_tool._persistent_context is None
    assert browser_tool._browser is None   # NO cayó al modo antiguo/dedicado
