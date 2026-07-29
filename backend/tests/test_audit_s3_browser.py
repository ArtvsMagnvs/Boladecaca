# tests/test_audit_s3_browser.py — Regresiones de la Sesión 3 del plan de
# corrección post-auditoría v0.9.5 (doc 24 hallazgos A-3 y F-1; doc 25 S3).
#
# Contratos que protege:
#   A-3: un muro de consentimiento (cookies/GDPR) se cierra SOLO antes de
#        reportar éxito, y `open_url` devuelve dónde aterrizó de verdad
#        (page_state) para que el modelo no navegue a ciegas.
#   F-1: dos misiones concurrentes tienen sesiones de navegador SEPARADAS
#        (BrowserContext propio): no se pisan la pestaña activa ni las cookies.
#
# SIN RED: las páginas son HTML local servido por `page.set_content` sobre un
# doble de Playwright ligero — no hace falta Chromium instalado para validar la
# LÓGICA de dismissal, de sesiones y de page_state, que es lo que falló en
# producción. La integración real con Chromium se valida en vivo (doc 25 §S3).
from __future__ import annotations

import pytest

from app.tools import browser_tool


# ---------------------------------------------------------------------------
# Dobles ligeros de Playwright (Page / BrowserContext / Browser)
# ---------------------------------------------------------------------------
class _FakeLocator:
    def __init__(self, page, selector):
        self._page = page
        self._selector = selector

    @property
    def first(self):
        return self

    async def count(self):
        return 1 if self._selector in self._page.consent_selectors else 0

    async def click(self, timeout=None):
        if self._selector not in self._page.consent_selectors:
            raise RuntimeError("elemento no encontrado")
        self._page.consent_clicked.append(self._selector)
        self._page.consent_selectors = set()      # el muro desaparece
        self._page.body_text = self._page.real_text


class _FakePage:
    """Página con un muro de consentimiento opcional que tapa el contenido."""

    def __init__(self, consent_selectors=(), real_text="CONTENIDO REAL", title="Página"):
        self.consent_selectors = set(consent_selectors)
        self.consent_clicked = []
        self.real_text = real_text
        self.body_text = "Aceptar cookies para continuar" if consent_selectors else real_text
        self._title = title
        self.url = "about:blank"
        self.closed = False

    async def goto(self, url, wait_until=None, timeout=None):
        self.url = url
        class _R:
            status = 200
        return _R()

    def locator(self, selector):
        return _FakeLocator(self, selector)

    async def wait_for_load_state(self, state, timeout=None):
        return None

    async def title(self):
        return self._title

    async def inner_text(self, selector, timeout=None):
        return self.body_text

    async def close(self):
        self.closed = True

    def is_closed(self):
        # [S9, doc 34 §10] `_get_page` (browser_tool.py) ahora pregunta
        # `is_closed()` antes de reutilizar una pestaña — un doble de Page sin
        # este método parecía "siempre muerta" (Exception -> dead=True) y
        # `_get_page` recreaba una pestaña nueva en CADA llamada, rompiendo la
        # reutilización que estos tests de F-1 verifican. Mismo patrón LOG-1
        # de siempre: un doble de un contrato que evoluciona debe evolucionar
        # con él. Playwright real siempre tiene este método.
        return self.closed


class _FakeContext:
    def __init__(self, page_factory):
        self._page_factory = page_factory
        self.pages = []
        self.closed = False

    async def new_page(self):
        p = self._page_factory()
        self.pages.append(p)
        return p

    async def close(self):
        self.closed = True


class _FakeBrowser:
    def __init__(self, page_factory):
        self._page_factory = page_factory
        self.contexts = []

    async def new_context(self):
        c = _FakeContext(self._page_factory)
        self.contexts.append(c)
        return c


@pytest.fixture
def fake_browser(monkeypatch):
    """Instala un navegador falso (modo EFIMERO — un contexto por mision) y
    limpia el estado global entre tests. [2026-07-23] Fuerza
    `_persistent_context=None` para que los tests de aislamiento F-1 ejerciten
    el camino efimero (un `new_context` por mision), no el perfil persistente."""
    def _install(page_factory):
        browser = _FakeBrowser(page_factory)
        monkeypatch.setattr(browser_tool, "_browser", browser)
        monkeypatch.setattr(browser_tool, "_persistent_context", None)
        monkeypatch.setattr(browser_tool, "_learned_consent", {})

        async def _noop():
            return None
        monkeypatch.setattr(browser_tool, "_ensure_browser", _noop)
        browser_tool._sessions.clear()
        return browser

    yield _install
    browser_tool._sessions.clear()


# ---------------------------------------------------------------------------
# A-3 — Muros de consentimiento
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_a3_el_muro_de_cookies_se_cierra_solo(fake_browser):
    """EL fallo A: cargar el muro de cookies de Google contaba como éxito y el
    modelo clicaba a ciegas el contenido tapado. Ahora el muro se cierra ANTES
    de reportar, y el texto que ve el modelo es el contenido REAL."""
    fake_browser(lambda: _FakePage(consent_selectors={"#onetrust-accept-btn-handler"},
                                   real_text="Vídeo de Melendi - Caminando por la vida"))
    tool = browser_tool.BrowserTool()

    res = await tool.execute("open_url", {"url": "youtube.com"})

    assert res["success"]
    r = res["result"]
    assert r["consent_dismissed"] == "#onetrust-accept-btn-handler"
    assert "Melendi" in r["text_excerpt"], "el modelo ve el CONTENIDO, no el muro"
    assert "cookies" not in r["text_excerpt"].lower()


@pytest.mark.anyio
async def test_a3_sin_muro_no_hace_nada(fake_browser):
    """Coste ~0 y cero regresión en el caso normal (la mayoría de páginas)."""
    fake_browser(lambda: _FakePage(real_text="Contenido directo"))
    tool = browser_tool.BrowserTool()

    res = await tool.execute("open_url", {"url": "example.com"})

    assert res["success"]
    assert res["result"]["consent_dismissed"] is None
    assert "Contenido directo" in res["result"]["text_excerpt"]


@pytest.mark.anyio
async def test_a3_muro_que_no_se_puede_cerrar_no_rompe_la_navegacion(fake_browser):
    """Un muro desconocido no debe impedir seguir: la navegación reporta éxito
    y el modelo lo VE en el extracto, así que puede decidir otra vía."""
    fake_browser(lambda: _FakePage(consent_selectors={"#un-cmp-que-no-conocemos"},
                                   real_text="tapado"))
    tool = browser_tool.BrowserTool()

    res = await tool.execute("open_url", {"url": "example.com"})

    assert res["success"]
    assert res["result"]["consent_dismissed"] is None
    assert "cookies" in res["result"]["text_excerpt"].lower()


@pytest.mark.anyio
async def test_a3_open_url_devuelve_page_state_completo(fake_browser):
    """El modelo necesita saber DÓNDE aterrizó sin pagar otra llamada."""
    fake_browser(lambda: _FakePage(real_text="hola mundo", title="Mi título"))
    tool = browser_tool.BrowserTool()

    r = (await tool.execute("open_url", {"url": "example.com"}))["result"]

    for campo in ("tab_id", "url", "title", "text_excerpt", "consent_dismissed", "status"):
        assert campo in r, f"falta {campo} en page_state"
    assert r["title"] == "Mi título"
    assert r["url"].startswith("https://")


# ---------------------------------------------------------------------------
# F-1 — Aislamiento de sesión por misión
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_f1_dos_misiones_no_comparten_pestanas(fake_browser):
    """EL riesgo latente: con ORCH_MAX_CONCURRENT=3, dos misiones que usaran el
    navegador compartían `_pages` y `_current_tab` y se pisaban la pestaña."""
    browser = fake_browser(lambda: _FakePage(real_text="ok"))
    tool = browser_tool.BrowserTool()

    a = (await tool.execute("open_url", {"url": "a.com", "_session": "mision-A"}))["result"]
    b = (await tool.execute("open_url", {"url": "b.com", "_session": "mision-B"}))["result"]

    assert a["tab_id"] != b["tab_id"]
    assert len(browser.contexts) == 2, "cada misión tiene su BrowserContext"
    sa = browser_tool._sessions["mision-A"]
    sb = browser_tool._sessions["mision-B"]
    assert sa.current_tab != sb.current_tab
    assert set(sa.pages) & set(sb.pages) == set(), "ninguna pestaña compartida"


@pytest.mark.anyio
async def test_f1_la_misma_mision_reutiliza_su_pestana(fake_browser):
    """Dentro de una misión, navegar dos veces sigue en la MISMA pestaña
    (comportamiento de siempre, ahora acotado a su sesión)."""
    fake_browser(lambda: _FakePage(real_text="ok"))
    tool = browser_tool.BrowserTool()

    a1 = (await tool.execute("open_url", {"url": "a.com", "_session": "M"}))["result"]
    a2 = (await tool.execute("open_url", {"url": "b.com", "_session": "M"}))["result"]

    assert a1["tab_id"] == a2["tab_id"]
    assert len(browser_tool._sessions["M"].pages) == 1


@pytest.mark.anyio
async def test_f1_sin_session_usa_default_cero_regresion(fake_browser):
    """El chat directo (sin misión) se comporta exactamente como antes."""
    fake_browser(lambda: _FakePage(real_text="ok"))
    tool = browser_tool.BrowserTool()

    await tool.execute("open_url", {"url": "a.com"})
    await tool.execute("open_url", {"url": "b.com"})

    assert list(browser_tool._sessions) == [browser_tool._DEFAULT_SESSION]
    assert len(browser_tool._sessions["default"].pages) == 1


@pytest.mark.anyio
async def test_f1_cerrar_la_sesion_libera_el_contexto(fake_browser):
    """Al terminar una misión, su contexto se cierra: sin esto cada misión que
    abriera el navegador dejaría un contexto vivo hasta reiniciar el backend."""
    browser = fake_browser(lambda: _FakePage(real_text="ok"))
    tool = browser_tool.BrowserTool()

    await tool.execute("open_url", {"url": "a.com", "_session": "M1"})
    ctx = browser_tool._sessions["M1"].context

    assert await browser_tool.close_session("M1") is True
    assert "M1" not in browser_tool._sessions
    assert ctx.closed is True
    assert await browser_tool.close_session("M1") is False   # idempotente


@pytest.mark.anyio
async def test_f1_cerrar_pestana_solo_afecta_a_su_mision(fake_browser):
    """Cerrar una pestaña de la misión A no puede tocar las de la B."""
    fake_browser(lambda: _FakePage(real_text="ok"))
    tool = browser_tool.BrowserTool()

    await tool.execute("open_url", {"url": "a.com", "_session": "A"})
    await tool.execute("open_url", {"url": "b.com", "_session": "B"})
    tab_b = browser_tool._sessions["B"].current_tab

    await tool.execute("close_tab", {"_session": "A"})

    assert browser_tool._sessions["A"].pages == {}
    assert tab_b in browser_tool._sessions["B"].pages, "la misión B intacta"


# ---------------------------------------------------------------------------
# Integración con el TIE: la sesión la inyecta el bucle, no el modelo
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_f1_el_toolloop_inyecta_la_sesion_de_la_mision(monkeypatch):
    """El modelo no ve ni puede falsear `_session`: la pone el bucle desde el
    id de la misión (mismo criterio que el etiquetado de memoria en C-1b)."""
    import json
    import sys
    import types
    from dataclasses import dataclass
    from typing import Any, Optional

    from app.tie import toolloop

    mel = types.ModuleType("app.mel")

    class Capability:
        AGENTIC = "agentic"

    @dataclass
    class ExecutionRequest:
        capability: Any = None
        prompt: str = ""
        system_prompt: str = ""
        model_override: Optional[str] = None
        context_tags: Optional[dict] = None
        policy_override: Optional[str] = None
        fitness_exempt: bool = False

    @dataclass
    class _Res:
        text: str
        ok: bool = True
        error: Optional[str] = None

    cola = [
        json.dumps({"tool": {"tool_id": "browser", "action": "open_url",
                             "params": {"url": "example.com"}}}),
        '{"answer": "abierto"}',
    ]

    async def _complete(req):
        return _Res(text=cola.pop(0))

    mel.Capability, mel.ExecutionRequest, mel.complete = Capability, ExecutionRequest, _complete
    monkeypatch.setitem(sys.modules, "app.mel", mel)

    capturado = {}

    class _TM:
        def list_tools(self, include_internal=False):
            return [{"tool_id": "browser", "description": "nav", "actions": [
                {"id": "open_url", "description": "abre", "requires_confirmation": False}]}]

        def tie_catalog(self):
            # [P1, doc 34] toolloop.py ahora pide tool_manager.tie_catalog();
            # el doble debe implementar el mismo contrato que el ToolManager
            # real, o revienta con AttributeError (LOG-1: un doble de un
            # contrato que evoluciona debe evolucionar con él, o el test se
            # vuelve vacuo/roto en silencio).
            return self.list_tools(include_internal=True)

        def get_tool(self, tid):
            return object() if tid == "browser" else None

        async def execute(self, **kw):
            capturado.update(kw)
            return {"success": True, "result": {"url": "x"}, "error": None}

    res = await toolloop.run(
        instruction="abre example.com", context="", allowed_tools=["browser"],
        tool_manager=_TM(), max_iters=3, session_key="mision-123",
    )

    assert res.ok
    assert capturado["params"]["_session"] == "mision-123"
