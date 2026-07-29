# tests/test_audit_s9_browser_lock.py — auditoría runtime, sesión S9 (doc 34)
#
# Reabre F-1 (S3, doc 24 §22): la campaña 01 reprodujo en vivo que dos
# misiones con `browser` lanzadas con <20s de diferencia AMBAS fallaban con
# `TargetClosedError` (T06-R-D5-browser-concurrente). Causa raíz localizada
# leyendo el código: `_ensure_browser()` no tenía ningún lock — dos
# corrutinas que llegaban con `_browser is None and _persistent_context is
# None` pasaban AMBAS el guard y lanzaban DOS `launch_persistent_context()`
# sobre el MISMO perfil; Chrome bloquea el segundo proceso y el pisoteo de
# los globals deja a las DOS con una referencia a un contexto muerto.
#
# SIN RED: dobles ligeros de `playwright.async_api` que CUENTAN lanzamientos
# y tardan un poco (para que la carrera sea observable con concurrencia
# real de asyncio), igual que test_audit_s3_browser.py hace con Page/Context.
from __future__ import annotations

import asyncio
import sys
import types

import pytest

from app.tools import browser_tool


# ---------------------------------------------------------------------------
# Doble de `playwright.async_api` — cuenta lanzamientos, tarda un poco
# ---------------------------------------------------------------------------
def _fake_playwright_module(launches: list, delay: float = 0.05):
    class _FakeContext:
        # [S9b] `pages` e `is_connected` los tiene SIEMPRE un contexto real de
        # Playwright, y desde S9b `_alive()` los consulta para saber si el
        # navegador sigue vivo. Sin ellos el doble parecía muerto y
        # `_ensure_browser` relanzaba en cada llamada (mismo patrón que el
        # `is_closed()` que hubo que añadir a `_FakePage` en S9: un doble de un
        # contrato que evoluciona tiene que evolucionar con él).
        pages: list = []

        def is_connected(self):
            return True

        async def new_page(self):
            return _FakePage()

        async def close(self):
            return None

    class _FakeBrowserObj:
        def is_connected(self):
            return True

        async def new_context(self):
            return _FakeContext()

    class _FakePage:
        def is_closed(self):
            return False

    class _FakeChromium:
        async def launch_persistent_context(self, *a, **kw):
            launches.append(1)
            await asyncio.sleep(delay)   # simula el tiempo real de lanzar Chrome
            return _FakeContext()

        async def launch(self, *a, **kw):
            launches.append(1)
            await asyncio.sleep(delay)
            return _FakeBrowserObj()

    class _FakePlaywrightInstance:
        chromium = _FakeChromium()

    class _FakeAsyncPlaywrightCtx:
        async def start(self):
            return _FakePlaywrightInstance()

    def async_playwright():
        return _FakeAsyncPlaywrightCtx()

    return types.SimpleNamespace(async_playwright=async_playwright)


@pytest.fixture(autouse=True)
def _reset_globals(monkeypatch):
    """El estado del módulo (`_playwright`/`_browser`/`_persistent_context`/
    `_sessions`) es GLOBAL de proceso — se resetea antes y después de cada
    test para que ninguno vea el navegador "ya lanzado" por el anterior.

    `_launch_lock` se RECREA en cada test (no solo se limpia): un
    `asyncio.Lock` se vincula al event loop en el que se usa por primera vez,
    y pytest-anyio crea un loop NUEVO por test — reusar el mismo objeto de
    lock entre tests revienta con "is bound to a different event loop". En
    producción esto no aplica (un único loop de por vida del proceso)."""
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
# 1 · `_ensure_browser()` bajo concurrencia: UN solo lanzamiento
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_ensure_browser_concurrente_lanza_una_sola_vez(monkeypatch, tmp_path):
    """LA REGRESIÓN DEL HALLAZGO: 5 corrutinas concurrentes llamando
    `_ensure_browser()` (el equivalente a 5 misiones arrancando casi a la vez)
    deben acabar en UN solo `launch_persistent_context()`, no cinco."""
    launches: list = []
    fake_mod = _fake_playwright_module(launches)
    monkeypatch.setitem(sys.modules, "playwright.async_api", fake_mod)
    monkeypatch.setattr(browser_tool, "_browser_mode", lambda: "aithera")
    monkeypatch.setattr(browser_tool.settings, "BROWSER_CHANNEL", "chromium")
    monkeypatch.setattr(browser_tool.settings, "BROWSER_PROFILE_DIR", str(tmp_path))

    await asyncio.gather(*[browser_tool._ensure_browser() for _ in range(5)])

    assert launches == [1], f"debía lanzar UNA sola vez, lanzó {len(launches)}"
    assert browser_tool._persistent_context is not None


@pytest.mark.anyio
async def test_ensure_browser_ya_lanzado_no_vuelve_a_lanzar(monkeypatch, tmp_path):
    """No-regresión: si el navegador YA está lanzado (el caso normal, el
    99% de las llamadas), una nueva llamada es un no-op instantáneo — el
    lock no debe añadir coste en el camino ya caliente."""
    launches: list = []
    fake_mod = _fake_playwright_module(launches)
    monkeypatch.setitem(sys.modules, "playwright.async_api", fake_mod)
    monkeypatch.setattr(browser_tool, "_browser_mode", lambda: "aithera")
    monkeypatch.setattr(browser_tool.settings, "BROWSER_CHANNEL", "chromium")
    monkeypatch.setattr(browser_tool.settings, "BROWSER_PROFILE_DIR", str(tmp_path))

    await browser_tool._ensure_browser()
    assert launches == [1]

    await browser_tool._ensure_browser()
    await browser_tool._ensure_browser()
    assert launches == [1], "una segunda/tercera llamada no debe relanzar nada"


# ---------------------------------------------------------------------------
# 2 · `_get_session()` bajo concurrencia con el MISMO sid: UN solo contexto
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_get_session_concurrente_no_duplica_contexto(monkeypatch):
    """La carrera "en pequeño": modo respaldo (sin perfil persistente), dos
    misiones con el MISMO `session_id` (o ambas cayendo en el default) no
    deben terminar con dos `BrowserContext` distintos — uno quedaría
    huérfano, nunca cerrado."""
    contexts_created: list = []

    class _FakeContext:
        pass

    class _FakeBrowserObj:
        async def new_context(self):
            await asyncio.sleep(0.05)
            ctx = _FakeContext()
            contexts_created.append(ctx)
            return ctx

    async def _noop_ensure():
        return None

    monkeypatch.setattr(browser_tool, "_ensure_browser", _noop_ensure)
    monkeypatch.setattr(browser_tool, "_browser", _FakeBrowserObj())
    monkeypatch.setattr(browser_tool, "_persistent_context", None)

    results = await asyncio.gather(
        *[browser_tool._get_session("mision-concurrente") for _ in range(5)]
    )

    assert len(contexts_created) == 1, f"debía crear UN contexto, creó {len(contexts_created)}"
    assert all(r is results[0] for r in results), "las 5 llamadas deben devolver la MISMA sesión"


@pytest.mark.anyio
async def test_get_session_sids_distintos_si_crean_contextos_propios(monkeypatch):
    """No-regresión: el lock protege la escritura, no serializa misiones
    DISTINTAS entre sí — cada `session_id` distinto sigue teniendo su propio
    contexto (F-1, S3)."""
    contexts_created: list = []

    class _FakeContext:
        def __init__(self, tag):
            self.tag = tag

    class _FakeBrowserObj:
        def __init__(self):
            self._n = 0

        async def new_context(self):
            self._n += 1
            ctx = _FakeContext(self._n)
            contexts_created.append(ctx)
            return ctx

    async def _noop_ensure():
        return None

    monkeypatch.setattr(browser_tool, "_ensure_browser", _noop_ensure)
    monkeypatch.setattr(browser_tool, "_browser", _FakeBrowserObj())
    monkeypatch.setattr(browser_tool, "_persistent_context", None)

    sess_a, sess_b = await asyncio.gather(
        browser_tool._get_session("mision-a"), browser_tool._get_session("mision-b")
    )
    assert sess_a is not sess_b
    assert len(contexts_created) == 2


# ---------------------------------------------------------------------------
# 3 · `_get_page()` — una pestaña muerta se recrea, no revienta la misión
# ---------------------------------------------------------------------------
class _FakePageState:
    def __init__(self, closed: bool):
        self._closed = closed

    def is_closed(self):
        return self._closed


class _FakeCtxForPages:
    def __init__(self):
        self.created: list = []

    async def new_page(self):
        p = _FakePageState(closed=False)
        self.created.append(p)
        return p


@pytest.mark.anyio
async def test_get_page_pestana_muerta_se_recrea(monkeypatch):
    ctx = _FakeCtxForPages()
    sess = browser_tool._Session(ctx, owns_context=False)
    dead_page = _FakePageState(closed=True)
    sess.pages["vieja"] = dead_page
    sess.current_tab = "vieja"

    async def _fake_get_session(session_id):
        return sess

    monkeypatch.setattr(browser_tool, "_get_session", _fake_get_session)

    tid, page = await browser_tool._get_page(None, "mision-x")

    assert tid != "vieja", "no debe devolver el id de la pestaña muerta"
    assert page is not dead_page, "no debe devolver el HANDLE muerto"
    assert "vieja" not in sess.pages, "la pestaña muerta se descarta"
    assert sess.current_tab == tid


@pytest.mark.anyio
async def test_get_page_pestana_viva_se_reutiliza_sin_regresion(monkeypatch):
    """No-regresión: una pestaña VIVA sigue reutilizándose tal cual — S9 solo
    cambia el caso de una pestaña muerta."""
    ctx = _FakeCtxForPages()
    sess = browser_tool._Session(ctx, owns_context=False)
    alive_page = _FakePageState(closed=False)
    sess.pages["viva"] = alive_page
    sess.current_tab = "viva"

    async def _fake_get_session(session_id):
        return sess

    monkeypatch.setattr(browser_tool, "_get_session", _fake_get_session)

    tid, page = await browser_tool._get_page(None, "mision-x")

    assert tid == "viva"
    assert page is alive_page
    assert ctx.created == [], "una pestaña viva no debe crear ninguna nueva"


@pytest.mark.anyio
async def test_get_page_is_closed_que_lanza_se_trata_como_muerta(monkeypatch):
    """Defensa adicional: si `is_closed()` lanza (referencia realmente
    inválida), se trata igual que una pestaña muerta — nunca se propaga la
    excepción de Playwright hacia la misión."""
    class _PageQueRompe:
        def is_closed(self):
            raise RuntimeError("Target closed")

    ctx = _FakeCtxForPages()
    sess = browser_tool._Session(ctx, owns_context=False)
    sess.pages["rota"] = _PageQueRompe()
    sess.current_tab = "rota"

    async def _fake_get_session(session_id):
        return sess

    monkeypatch.setattr(browser_tool, "_get_session", _fake_get_session)

    tid, page = await browser_tool._get_page(None, "mision-x")

    assert tid != "rota"
    assert "rota" not in sess.pages
