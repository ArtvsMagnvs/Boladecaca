# tests/test_audit_s9b_browser_muerto.py — S9b (doc 34): un navegador MUERTO
# se relanza en vez de envenenar el proceso entero.
#
# EL FALLO REAL (verificación en vivo del usuario, 2026-07-28, DESPUÉS de S9):
# tres misiones seguidas con navegador, todas con el mismo final —
#   "El navegador (BrowserContext) está cerrado en esta sesión, así que tanto
#    `browser.open_url` como `browser.new_tab` fallan con TargetClosedError"
# S9 arregló la CARRERA entre misiones concurrentes (dos lanzamientos a la vez),
# pero debajo quedaba algo peor, que ni siquiera necesita concurrencia:
# `_ensure_browser()` comprobaba `is not None`, NO si el navegador seguía vivo.
# En cuanto `_persistent_context` moría por una causa externa (el usuario cerró
# esa ventana de Chrome, el proceso se cayó), la global seguía apuntando al
# cadáver y el guard decía "ya está lanzado" PARA SIEMPRE: ninguna misión
# posterior podía navegar hasta reiniciar el backend.
#
# SIN RED: dobles de Playwright que simulan un contexto que muere.
from __future__ import annotations

import asyncio

import pytest

from app.tools import browser_tool


class _FakePage:
    def __init__(self):
        self.closed = False

    def is_closed(self):
        return self.closed


class _FakeContext:
    """Contexto que puede morir: tras `matar()`, `new_page()` lanza el mismo
    error que Playwright real y `is_connected()` devuelve False."""

    def __init__(self, tag: str = "ctx"):
        self.tag = tag
        self.vivo = True
        self.miente = False        # "vivo" para el chequeo, muerto al usarlo
        self.pages: list = []
        self.cerrado = False

    def matar(self, mintiendo: bool = False):
        """`mintiendo=True` reproduce EL caso que el chequeo previo no puede
        cubrir: el navegador contesta que sigue conectado (o Playwright aún no
        se ha enterado) pero la primera operación real revienta."""
        self.vivo = False
        self.miente = mintiendo

    def is_connected(self):
        return True if self.miente else self.vivo

    async def new_page(self):
        if not self.vivo:
            raise RuntimeError("TargetClosedError: Target page, context or "
                               "browser has been closed")
        p = _FakePage()
        self.pages.append(p)
        return p

    async def close(self):
        self.cerrado = True
        self.vivo = False


@pytest.fixture(autouse=True)
def _reset_globals():
    """Estado de módulo + `_launch_lock` recreado por test (un `asyncio.Lock`
    se vincula al primer event loop que lo usa y pytest-anyio crea uno nuevo
    por test). Mismo motivo documentado en `test_audit_s9_browser_lock.py`."""
    def _clear():
        browser_tool._playwright = None
        browser_tool._browser = None
        browser_tool._persistent_context = None
        browser_tool._sessions.clear()
        browser_tool._launch_lock = asyncio.Lock()

    _clear()
    yield
    _clear()


# ---------------------------------------------------------------------------
# 1 · `_looks_closed` y `_alive` — los dos detectores
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("exc", [
    RuntimeError("TargetClosedError: Target page, context or browser has been closed"),
    RuntimeError("Browser has been closed"),
    Exception("Connection closed while reading from the driver"),
])
def test_reconoce_un_error_de_navegador_cerrado(exc):
    assert browser_tool._looks_closed(exc) is True


@pytest.mark.parametrize("exc", [
    RuntimeError("net::ERR_NAME_NOT_RESOLVED"),
    TimeoutError("Timeout 30000ms exceeded"),
    ValueError("selector inválido"),
])
def test_no_confunde_otros_errores_con_navegador_cerrado(exc):
    """Importa tanto como lo anterior: si un timeout de red se tomara por
    'navegador muerto', se relanzaría Chrome (cerrando las pestañas del
    usuario) por un fallo que no tiene nada que ver."""
    assert browser_tool._looks_closed(exc) is False


def test_alive_detecta_vivo_y_muerto():
    ctx = _FakeContext()
    assert browser_tool._alive(ctx) is True
    ctx.matar()
    assert browser_tool._alive(ctx) is False
    assert browser_tool._alive(None) is False


def test_browser_ready_es_false_con_un_contexto_muerto():
    """EL GUARD QUE FALLABA: con un contexto no-None pero muerto, el viejo
    `is not None` decía "ya está lanzado" y no relanzaba nunca."""
    ctx = _FakeContext()
    browser_tool._persistent_context = ctx
    assert browser_tool._browser_ready() is True
    ctx.matar()
    assert browser_tool._browser_ready() is False


# ---------------------------------------------------------------------------
# 2 · el relanzamiento real
# ---------------------------------------------------------------------------
def _fake_launcher(monkeypatch, creados: list, tmp_path):
    """Sustituye el lanzamiento real por uno que cuenta y devuelve contextos
    nuevos, para poder afirmar cuántas veces se relanzó."""
    import sys
    import types

    class _FakeChromium:
        async def launch_persistent_context(self, *a, **kw):
            ctx = _FakeContext(tag=f"ctx{len(creados) + 1}")
            creados.append(ctx)
            return ctx

        async def launch(self, *a, **kw):
            ctx = _FakeContext(tag=f"br{len(creados) + 1}")
            creados.append(ctx)
            return ctx

    class _FakeInstance:
        chromium = _FakeChromium()

        async def stop(self):
            return None

    class _FakeCtxMgr:
        async def start(self):
            return _FakeInstance()

    mod = types.SimpleNamespace(async_playwright=lambda: _FakeCtxMgr())
    monkeypatch.setitem(sys.modules, "playwright.async_api", mod)
    monkeypatch.setattr(browser_tool, "_browser_mode", lambda: "aithera")
    monkeypatch.setattr(browser_tool.settings, "BROWSER_CHANNEL", "chromium")
    monkeypatch.setattr(browser_tool.settings, "BROWSER_PROFILE_DIR", str(tmp_path))


@pytest.mark.anyio
async def test_ensure_browser_relanza_si_el_contexto_murio(monkeypatch, tmp_path):
    """LA REGRESIÓN DEL FALLO: navegador lanzado -> muere por fuera -> la
    siguiente llamada debe relanzar, no dar por bueno el cadáver."""
    creados: list = []
    _fake_launcher(monkeypatch, creados, tmp_path)

    await browser_tool._ensure_browser()
    assert len(creados) == 1

    creados[0].matar()                      # el usuario cierra esa ventana

    await browser_tool._ensure_browser()
    assert len(creados) == 2, "debía relanzar tras la muerte del contexto"
    assert browser_tool._persistent_context is creados[1]
    assert browser_tool._browser_ready() is True


@pytest.mark.anyio
async def test_ensure_browser_vivo_no_relanza(monkeypatch, tmp_path):
    """No-regresión: mientras esté vivo, `_ensure_browser` sigue siendo un
    no-op barato — no puede ponerse a relanzar Chrome en cada llamada."""
    creados: list = []
    _fake_launcher(monkeypatch, creados, tmp_path)

    await browser_tool._ensure_browser()
    await browser_tool._ensure_browser()
    await browser_tool._ensure_browser()
    assert len(creados) == 1


@pytest.mark.anyio
async def test_las_sesiones_viejas_no_sobreviven_al_relanzamiento(monkeypatch, tmp_path):
    """Si una sesión de misión conservara su `context` viejo tras el
    relanzamiento, seguiría fallando igual: hay que recrearla contra el
    contexto NUEVO."""
    creados: list = []
    _fake_launcher(monkeypatch, creados, tmp_path)

    sess1 = await browser_tool._get_session("mision-1")
    assert sess1.context is creados[0]

    creados[0].matar()
    await browser_tool._ensure_browser()        # relanza

    sess2 = await browser_tool._get_session("mision-1")
    assert sess2 is not sess1
    assert sess2.context is creados[1], "la sesión debe apuntar al contexto vivo"


@pytest.mark.anyio
async def test_get_page_relanza_y_reintenta_una_vez(monkeypatch, tmp_path):
    """El caso que el chequeo previo NO puede cubrir: el navegador está vivo
    cuando se comprueba y muere justo antes de abrir la pestaña. `_get_page`
    debe relanzar y reintentar UNA vez, devolviendo una pestaña usable."""
    creados: list = []
    _fake_launcher(monkeypatch, creados, tmp_path)

    sess = await browser_tool._get_session("mision-x")
    assert sess.context is creados[0]
    # MIENTE: `is_connected()` sigue diciendo True, así que `_ensure_browser`
    # NO lo cazará — el fallo solo aparece al pedir la pestaña. Es el caso que
    # ningún chequeo previo puede cubrir, y el motivo de que exista el reintento.
    creados[0].matar(mintiendo=True)

    tid, page = await browser_tool._get_page(None, "mision-x")

    assert tid and page is not None
    assert len(creados) == 2, "debía relanzar exactamente una vez"
    assert page in creados[1].pages, "la pestaña debe salir del navegador NUEVO"


@pytest.mark.anyio
async def test_get_page_no_entra_en_bucle_si_el_relanzamiento_tambien_falla(
        monkeypatch, tmp_path):
    """Un solo reintento. Si el navegador nuevo también está muerto, el error
    SUBE y la misión falla honestamente — nunca un bucle infinito de
    relanzamientos."""
    creados: list = []
    _fake_launcher(monkeypatch, creados, tmp_path)
    await browser_tool._get_session("mision-y")
    creados[0].matar(mintiendo=True)

    # el contexto que salga del relanzamiento nace ya muerto
    orig = browser_tool._get_session

    async def _sesion_muerta(session_id):
        s = await orig(session_id)
        s.context.matar(mintiendo=True)
        return s

    monkeypatch.setattr(browser_tool, "_get_session", _sesion_muerta)

    with pytest.raises(Exception) as exc:
        await browser_tool._get_page(None, "mision-y")
    assert browser_tool._looks_closed(exc.value)
    assert len(creados) <= 3, "no puede relanzar en bucle"


@pytest.mark.anyio
async def test_un_error_ajeno_no_dispara_relanzamiento(monkeypatch, tmp_path):
    """Un fallo de red al abrir pestaña no es 'navegador muerto': debe subir
    tal cual, sin cerrar ni relanzar nada del usuario."""
    creados: list = []
    _fake_launcher(monkeypatch, creados, tmp_path)
    sess = await browser_tool._get_session("mision-z")

    async def _rompe():
        raise RuntimeError("net::ERR_NAME_NOT_RESOLVED")

    sess.context.new_page = _rompe

    with pytest.raises(RuntimeError, match="ERR_NAME_NOT_RESOLVED"):
        await browser_tool._get_page(None, "mision-z")
    assert len(creados) == 1, "no debía relanzar por un error de red"
