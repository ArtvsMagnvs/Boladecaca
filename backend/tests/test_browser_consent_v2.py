# tests/test_browser_consent_v2.py — arreglo DEFINITIVO del muro de cookies
# (2026-07-23, petición del usuario: "que aprenda de forma definitiva; que unas
# simples cookies no le frenen toda una misión en web").
#
# Lo que protege, SIN RED (dobles de Playwright):
#   1. Capa de TEXTO: un CMP casero SIN selector conocido pero con un botón
#      "Aceptar todo" se cierra igualmente (la cola larga que rompía misiones).
#   2. APRENDIZAJE PERSISTENTE: al cerrar un muro se guarda {dominio→estrategia};
#      la siguiente visita al mismo dominio usa lo aprendido PRIMERO (vía rápida)
#      y sobrevive a reiniciar el proceso (fichero en el perfil de Aithera).
#   3. Perfil PERSISTENTE: las misiones comparten contexto (sesión de Google),
#      y cerrar una misión NO cierra el contexto compartido, solo sus pestañas.
from __future__ import annotations

import re

import pytest

from app.tools import browser_tool


# ---------------------------------------------------------------------------
# Doble de Playwright con soporte de get_by_role (locators por texto/rol)
# ---------------------------------------------------------------------------
class _RoleLocator:
    def __init__(self, page, role, name_pattern):
        self._page, self._role, self._pat = page, role, name_pattern

    @property
    def first(self):
        return self

    def _match(self):
        for b in self._page.buttons:
            if b["role"] == self._role and self._pat.search(b["text"]):
                return b
        return None

    async def count(self):
        return 1 if self._match() else 0

    async def click(self, timeout=None):
        b = self._match()
        if not b:
            raise RuntimeError("no role match")
        self._page.clicked_text = b["text"]
        self._page.buttons = []                 # el muro desaparece
        self._page.body_text = self._page.real_text


class _CssLocator:
    def __init__(self, page, selector):
        self._page, self._sel = page, selector

    @property
    def first(self):
        return self

    async def count(self):
        return 1 if self._sel in self._page.css_selectors else 0

    async def click(self, timeout=None):
        if self._sel not in self._page.css_selectors:
            raise RuntimeError("no css match")
        self._page.clicked_css = self._sel
        self._page.css_selectors = set()
        self._page.body_text = self._page.real_text


class _Page:
    def __init__(self, *, url, css_selectors=(), buttons=(), real_text="CONTENIDO"):
        self.url = url
        self.css_selectors = set(css_selectors)
        # buttons: lista de {"role": "button"|"link", "text": str}
        self.buttons = list(buttons)
        self.real_text = real_text
        self.body_text = "Aceptar cookies para continuar" if (css_selectors or buttons) else real_text
        self.clicked_css = None
        self.clicked_text = None
        self.closed = False

    @property
    def frames(self):
        return [self]      # sin iframes reales; escanea la propia página

    def locator(self, selector):
        return _CssLocator(self, selector)

    def get_by_role(self, role, name=None):
        return _RoleLocator(self, role, name)

    async def wait_for_load_state(self, state, timeout=None):
        return None

    async def title(self):
        return "T"

    async def inner_text(self, selector, timeout=None):
        return self.body_text

    async def close(self):
        self.closed = True


@pytest.fixture
def _perfil_temporal(monkeypatch, tmp_path):
    """Aísla el aprendizaje en un perfil descartable (no toca el del usuario)."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "BROWSER_PROFILE_DIR", str(tmp_path / "prof"))
    browser_tool._learned_consent = None       # sin caché heredado
    yield
    browser_tool._learned_consent = None


# ---------------------------------------------------------------------------
# 1. Capa de TEXTO — CMP casero sin selector conocido
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_texto_cierra_cmp_casero_sin_selector(_perfil_temporal):
    """El caso que rompía misiones: un banner de cookies hecho a mano, sin
    ningún id de CMP conocido, pero con un botón 'Aceptar todo'."""
    page = _Page(url="https://tienda-random.example",
                 buttons=[{"role": "button", "text": "Aceptar todo"}],
                 real_text="Catálogo de productos")

    estrategia = await browser_tool._dismiss_consent(page)

    assert estrategia == "text=aceptar todo"
    assert page.clicked_text == "Aceptar todo"
    assert page.body_text == "Catálogo de productos"     # muro fuera


@pytest.mark.anyio
async def test_texto_ingles_y_frances(_perfil_temporal):
    for label, expect in [("Accept all", "text=accept all"),
                          ("Tout accepter", "text=tout accepter")]:
        page = _Page(url=f"https://x-{label}.example",
                     buttons=[{"role": "button", "text": label}])
        assert await browser_tool._dismiss_consent(page) == expect


@pytest.mark.anyio
async def test_no_toca_botones_que_no_son_aceptar(_perfil_temporal):
    """Prudencia: 'Rechazar'/'Configurar' NO se pulsan (mejor no tocar que
    romper el flujo o rechazar lo que el usuario querría aceptar)."""
    page = _Page(url="https://y.example",
                 buttons=[{"role": "button", "text": "Rechazar todo"},
                          {"role": "button", "text": "Configurar cookies"}])
    assert await browser_tool._dismiss_consent(page) is None


# ---------------------------------------------------------------------------
# 2. APRENDIZAJE PERSISTENTE por dominio
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_aprende_y_reusa_en_la_siguiente_visita(_perfil_temporal):
    dom = "https://aprendo.example/pagina"
    p1 = _Page(url=dom, buttons=[{"role": "button", "text": "Aceptar todo"}])
    await browser_tool._dismiss_consent(p1)

    # Se guardó {dominio: text=aceptar todo}
    learned = browser_tool._load_learned()
    assert learned.get("aprendo.example") == {"kind": "text", "value": "aceptar todo"}

    # Segunda visita: la vía aprendida cierra el muro de una (marca "learned:").
    p2 = _Page(url=dom, buttons=[{"role": "button", "text": "Aceptar todo"}])
    assert await browser_tool._dismiss_consent(p2) == "learned:aceptar todo"


@pytest.mark.anyio
async def test_lo_aprendido_sobrevive_a_reiniciar_el_proceso(_perfil_temporal):
    """Se persiste en un fichero del perfil: un backend nuevo (caché en None)
    lo relee del disco — 'de forma definitiva'."""
    dom = "https://persiste.example/x"
    p1 = _Page(url=dom, css_selectors={"#onetrust-accept-btn-handler"})
    await browser_tool._dismiss_consent(p1)

    browser_tool._learned_consent = None         # simula reinicio del proceso
    learned = browser_tool._load_learned()        # relee del fichero
    assert learned.get("persiste.example") == {"kind": "css",
                                               "value": "#onetrust-accept-btn-handler"}


@pytest.mark.anyio
async def test_css_conocido_se_aprende_y_reusa(_perfil_temporal):
    dom = "https://onetrust.example/z"
    p1 = _Page(url=dom, css_selectors={"#onetrust-accept-btn-handler"})
    assert await browser_tool._dismiss_consent(p1) == "#onetrust-accept-btn-handler"

    p2 = _Page(url=dom, css_selectors={"#onetrust-accept-btn-handler"})
    assert await browser_tool._dismiss_consent(p2) == "learned:#onetrust-accept-btn-handler"


@pytest.mark.anyio
async def test_sin_muro_no_aprende_ni_rompe(_perfil_temporal):
    page = _Page(url="https://limpia.example", real_text="Todo bien")
    assert await browser_tool._dismiss_consent(page) is None
    assert browser_tool._load_learned() == {}


# ---------------------------------------------------------------------------
# 3. Perfil PERSISTENTE: contexto compartido, cierre solo de pestañas
# ---------------------------------------------------------------------------
class _PersistentContext:
    def __init__(self):
        self.pages = []
        self.closed = False

    async def new_page(self):
        p = _Page(url="about:blank")
        self.pages.append(p)
        return p

    async def close(self):
        self.closed = True


@pytest.fixture
def _perfil_persistente(monkeypatch):
    ctx = _PersistentContext()
    monkeypatch.setattr(browser_tool, "_persistent_context", ctx)
    monkeypatch.setattr(browser_tool, "_browser", None)

    async def _noop():
        return None
    monkeypatch.setattr(browser_tool, "_ensure_browser", _noop)
    browser_tool._sessions.clear()
    yield ctx
    browser_tool._sessions.clear()


@pytest.mark.anyio
async def test_dos_misiones_comparten_el_contexto_persistente(_perfil_persistente):
    """Con perfil persistente, dos misiones comparten la MISMA sesión (las
    cookies/Google del usuario son el objetivo) pero tienen pestañas propias."""
    sa = await browser_tool._get_session("mision-A")
    sb = await browser_tool._get_session("mision-B")
    assert sa.context is sb.context is _perfil_persistente     # contexto compartido
    assert sa.owns_context is False


@pytest.mark.anyio
async def test_cerrar_mision_cierra_pestanas_no_el_contexto(_perfil_persistente):
    """Cerrar una misión no puede tirar la sesión de Google: cierra SOLO sus
    pestañas; el contexto persistente sigue vivo para las demás misiones."""
    tool = browser_tool.BrowserTool()
    await tool.execute("open_url", {"url": "example.com", "_session": "M1"})
    sess = browser_tool._sessions["M1"]
    page = next(iter(sess.pages.values()))

    assert await browser_tool.close_session("M1") is True
    assert "M1" not in browser_tool._sessions
    assert page.closed is True                       # su pestaña se cerró
    assert _perfil_persistente.closed is False       # el contexto NO
