# tests/test_bweb2_vision.py — B·WEB-2 (doc 32): clic por visión como fallback.
#
# Sin pantalla, sin navegador, sin red y sin modelo real: el ÚNICO doble es la
# frontera del LLM (`mel.complete`). Todo lo demás es el código real —
# `vision_click` entero, el filtro de aptitud del MEL, los payloads de los 4
# formatos de proveedor, y el handler de `desktop.find_and_click` con un
# pyautogui falso (el sandbox no tiene display).
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from app.mel.catalog import supports_vision
from app.mel.contracts import Capability, ExecutionRequest, ModelRef
from app.mel.policies import is_capable
from app.tools import vision_click


# ---------------------------------------------------------------------------
# 1 · Fail-closed de la capacidad VISION (paso 1 del plan)
# ---------------------------------------------------------------------------
def test_supports_vision_reconoce_las_familias_multimodales():
    assert supports_vision("gemini", "gemini-3.5-flash")
    assert supports_vision("anthropic", "claude-opus-4-8")
    assert supports_vision("openai", "gpt-5.2")
    assert supports_vision("grok", "grok-4.5")


def test_supports_vision_reconoce_un_local_vl_por_su_nombre():
    """Un modelo recién descargado (`ollama pull llava`) funciona sin tocar
    código: lo delata su propio nombre."""
    assert supports_vision("ollama", "qwen2.5vl:7b")
    assert supports_vision("ollama", "llava:13b")
    assert supports_vision("ollama", "llama3.2-vision:11b")
    assert supports_vision("ollama", "moondream")


def test_supports_vision_es_fail_closed_con_los_ciegos():
    """Lo que NO está declarado, no ve. Un `True` de más produce coordenadas
    inventadas; un `False` de más solo deja una capacidad sin cubrir."""
    assert not supports_vision("ollama", "llama3")
    assert not supports_vision("ollama", "deepseek-r1:8b")
    assert not supports_vision("minimax", "MiniMax-M2.7-highspeed")
    assert not supports_vision("deepseek", "deepseek-v4-pro")
    assert not supports_vision("proveedor-que-no-existe", "modelo-raro")


def test_los_agentes_cli_nunca_ven_aunque_el_modelo_detras_sea_multimodal():
    """Claude/Codex por CLI hablan por línea de comandos: no hay por dónde
    pasarles un PNG, sin importar de qué es capaz el modelo detrás."""
    assert not supports_vision("claude_code", "opus")
    assert not supports_vision("codex", "gpt-5.6-terra")


def test_is_capable_excluye_de_vision_a_los_no_multimodales():
    """El punto ÚNICO de aptitud del MEL: de aquí salen gratis las tres capas
    (compilación de políticas, filtro retroactivo en ejecución, y la UI)."""
    ciego = ModelRef(provider="ollama", model="llama3", is_local=True)
    vidente = ModelRef(provider="gemini", model="gemini-3.5-flash")
    assert not is_capable(ciego, Capability.VISION)
    assert is_capable(vidente, Capability.VISION)
    # ...y no se pisa ninguna otra capacidad: el modelo ciego sigue sirviendo
    # para todo lo demás.
    assert is_capable(ciego, Capability.CHAT)
    assert is_capable(ciego, Capability.CLASSIFY)


def test_una_politica_no_compila_un_modelo_ciego_en_vision():
    from app.mel.policies import _compile_policy
    from app.mel.contracts import PolicyName

    disponibles = [
        ModelRef(provider="ollama", model="llama3", is_local=True),
        ModelRef(provider="gemini", model="gemini-3.5-flash"),
    ]
    compilada = _compile_policy(PolicyName.QUALITY, disponibles)
    assert compilada["vision"] == ["gemini:gemini-3.5-flash"]
    # sin ningún modelo con visión, la cadena queda VACÍA (no se rellena con
    # un ciego "por si acaso"): es exactamente el fail-closed pedido.
    solo_ciegos = _compile_policy(PolicyName.QUALITY,
                                  [ModelRef(provider="ollama", model="llama3", is_local=True)])
    assert solo_ciegos["vision"] == []


# ---------------------------------------------------------------------------
# 2 · Transporte de la imagen — los 4 formatos de proveedor
# ---------------------------------------------------------------------------
def test_normalize_images_acepta_base64_puro_y_data_uri():
    from app.ai.providers.base import normalize_images

    assert normalize_images(["iVBORw0KGgo="]) == ["iVBORw0KGgo="]
    assert normalize_images(["data:image/png;base64,iVBORw0KGgo="]) == ["iVBORw0KGgo="]
    assert normalize_images([]) == []
    assert normalize_images(None) == []
    assert normalize_images(["  ", None, 42, "ok"]) == ["ok"]


def test_payload_openai_compatible_con_imagen():
    from app.ai.providers.openai_compatible import OpenAICompatibleProvider

    class _P(OpenAICompatibleProvider):
        def get_default_model(self): return "m"
        @property
        def provider_name(self): return "test"

    p = _P(api_key="k", model="m", base_url="http://x")
    msgs = p._build_messages("¿dónde está el botón?", None, None, ["AAA"])
    contenido = msgs[-1]["content"]
    assert isinstance(contenido, list)
    assert contenido[0]["type"] == "image_url"
    assert contenido[0]["image_url"]["url"] == "data:image/png;base64,AAA"
    assert contenido[-1] == {"type": "text", "text": "¿dónde está el botón?"}


def test_payload_openai_compatible_sin_imagen_es_identico_al_de_siempre():
    from app.ai.providers.openai_compatible import OpenAICompatibleProvider

    class _P(OpenAICompatibleProvider):
        def get_default_model(self): return "m"
        @property
        def provider_name(self): return "test"

    p = _P(api_key="k", model="m", base_url="http://x")
    assert p._build_messages("hola", None, None) == [{"role": "user", "content": "hola"}]
    assert p._build_messages("hola", None, None, []) == [{"role": "user", "content": "hola"}]


def test_payload_anthropic_con_imagen():
    from app.ai.providers.anthropic_provider import AnthropicProvider

    p = AnthropicProvider(api_key="k")
    payload = p._build_payload("mira", None, stream=False, images=["AAA"])
    contenido = payload["messages"][-1]["content"]
    assert contenido[0]["type"] == "image"
    assert contenido[0]["source"] == {"type": "base64", "media_type": "image/png", "data": "AAA"}
    assert contenido[-1] == {"type": "text", "text": "mira"}
    # sin imagen: el string de siempre
    assert p._build_payload("mira", None, stream=False)["messages"][-1]["content"] == "mira"


def test_payload_gemini_con_imagen():
    from app.ai.providers.gemini_provider import GeminiProvider

    p = GeminiProvider(api_key="k")
    partes = p._build_payload("mira", None, None, ["AAA"])["contents"][-1]["parts"]
    assert partes[0]["inline_data"] == {"mime_type": "image/png", "data": "AAA"}
    assert partes[-1] == {"text": "mira"}
    sin = p._build_payload("mira", None, None)["contents"][-1]["parts"]
    assert sin == [{"text": "mira"}]


def test_payload_ollama_con_imagen_en_los_dos_endpoints():
    from app.ai.providers.ollama_provider import OllamaProvider

    p = OllamaProvider()
    url, payload, es_chat = p._endpoint_and_payload("mira", None, None, False, ["AAA"])
    assert url.endswith("/api/generate") and not es_chat
    assert payload["images"] == ["AAA"]

    url, payload, es_chat = p._endpoint_and_payload(
        "mira", None, [{"role": "user", "content": "antes"}], False, ["AAA"])
    assert url.endswith("/api/chat") and es_chat
    assert payload["messages"][-1]["images"] == ["AAA"]
    # sin imagen, ni rastro del campo
    _, sin, _ = p._endpoint_and_payload("mira", None, None, False)
    assert "images" not in sin


@pytest.mark.anyio
async def test_el_registry_lanza_si_el_proveedor_no_acepta_imagenes(monkeypatch):
    """LA regla de B·WEB-2: una imagen NO degrada en silencio. Un proveedor
    ciego que recibiera la petición sin la imagen respondería igualmente,
    inventándose lo que "ve" — por eso se lanza y el executor salta de
    candidato en vez de aceptar esa respuesta."""
    from app.mel import registry

    class _Ciego:
        model = "m"
        async def generate(self, prompt, system_prompt=None, messages=None):
            return {"response": "me lo invento", "model": "m"}

    monkeypatch.setattr(registry, "_instance_for", lambda ref: _Ciego())
    ref = ModelRef(provider="x", model="m")
    with pytest.raises(RuntimeError, match="no acepta imágenes"):
        await registry.execute(ref, "mira", images=["AAA"])


# ---------------------------------------------------------------------------
# 3 · Parseo de la respuesta del modelo (puro)
# ---------------------------------------------------------------------------
def test_parse_location_json_con_indice_y_con_coordenadas():
    assert vision_click.parse_location('{"index": 7}').index == 7
    u = vision_click.parse_location('{"x": 412, "y": 268}')
    assert (u.x, u.y) == (412, 268)


def test_parse_location_tolera_markdown_y_texto_alrededor():
    u = vision_click.parse_location('Claro:\n```json\n{"x": 10, "y": 20}\n```\nEso es.')
    assert (u.x, u.y) == (10, 20)


def test_parse_location_acepta_un_par_suelto_como_ultimo_recurso():
    """Los modelos pequeños responden así a menudo; rechazarlo por su formato
    sería perder una localización correcta."""
    u = vision_click.parse_location("El botón está en 412, 268")
    assert (u.x, u.y) == (412, 268)


def test_parse_location_devuelve_none_si_el_modelo_dice_que_no_lo_ve():
    assert vision_click.parse_location('{"not_found": true, "reason": "no aparece"}') is None


def test_parse_location_devuelve_none_ante_basura():
    """Ante la duda NO se hace clic: una respuesta ininteligible vale lo mismo
    que un 'no lo encuentro'."""
    assert vision_click.parse_location("") is None
    assert vision_click.parse_location("no tengo ni idea de qué me hablas") is None
    assert vision_click.parse_location('{"algo": "otra cosa"}') is None
    assert vision_click.parse_location('{"index": true}') is None   # bool no es índice


# ---------------------------------------------------------------------------
# 4 · Escala / multi-monitor (paso 5 del plan)
# ---------------------------------------------------------------------------
def test_to_screen_coords_sin_escalado_es_la_identidad():
    assert vision_click.to_screen_coords(
        400, 300, image_size=(1920, 1080), screen_size=(1920, 1080)) == (400, 300)


def test_to_screen_coords_corrige_el_escalado_de_windows():
    """Captura física 2560x1440, ratón lógico 1707x960 (escala 150%): sin esta
    conversión el clic caería 1,5 veces más abajo y a la derecha."""
    x, y = vision_click.to_screen_coords(
        2560, 1440, image_size=(2560, 1440), screen_size=(1707, 960))
    assert (x, y) == (1706, 959)      # acotado al último píxel real
    x, y = vision_click.to_screen_coords(
        1280, 720, image_size=(2560, 1440), screen_size=(1707, 960))
    assert (x, y) == (854, 480)       # el centro sigue siendo el centro


def test_to_screen_coords_nunca_devuelve_un_clic_fuera_de_pantalla():
    assert vision_click.to_screen_coords(
        9999, 9999, image_size=(1000, 1000), screen_size=(800, 600)) == (799, 599)
    assert vision_click.to_screen_coords(
        -50, -50, image_size=(1000, 1000), screen_size=(800, 600)) == (0, 0)


# ---------------------------------------------------------------------------
# 5 · El prompt
# ---------------------------------------------------------------------------
def test_el_prompt_lleva_las_dimensiones_y_prohibe_inventar():
    p = vision_click.build_prompt("el botón de guardar", width=1920, height=1080)
    assert "1920x1080" in p
    assert "el botón de guardar" in p
    assert "not_found" in p
    assert "NUNCA te inventes" in p


def test_el_prompt_con_marcas_pide_elegir_por_indice():
    marcas = [{"index": 0, "role": "button", "text": "Aceptar"},
              {"index": 1, "role": "a", "text": "Más información"}]
    p = vision_click.build_prompt("aceptar cookies", width=1280, height=720, marks=marcas)
    assert "[0] button: Aceptar" in p
    assert "[1] a: Más información" in p
    assert '{"index": <número>}' in p


# ---------------------------------------------------------------------------
# 6 · locate() — fail-closed en las tres formas de fallar
# ---------------------------------------------------------------------------
class _FakeResult:
    def __init__(self, text="", ok=True, error=None):
        self.text, self.ok, self.error = text, ok, error


def _fake_mel(monkeypatch, *, disponible=True, resultado=None, captura=None):
    """Sustituye SOLO la frontera del LLM. `captura` recoge el ExecutionRequest
    real para poder afirmar sobre él."""
    import app.mel as mel

    monkeypatch.setattr(mel, "vision_available", lambda: disponible)

    async def _complete(req):
        if captura is not None:
            captura.append(req)
        return resultado or _FakeResult('{"x": 100, "y": 200}')

    monkeypatch.setattr(mel, "complete", _complete)


@pytest.mark.anyio
async def test_locate_sin_modelo_de_vision_falla_claro_y_no_llama_a_nadie(monkeypatch):
    llamadas = []
    _fake_mel(monkeypatch, disponible=False, captura=llamadas)
    ubic, error = await vision_click.locate("un botón", "AAA", width=800, height=600)
    assert ubic is None
    assert "ningún modelo con visión" in error
    assert llamadas == []          # ni una llamada gastada


@pytest.mark.anyio
async def test_locate_pide_capacidad_vision_y_manda_la_imagen(monkeypatch):
    llamadas: List[ExecutionRequest] = []
    _fake_mel(monkeypatch, captura=llamadas)
    ubic, error = await vision_click.locate("un botón", "AAA", width=800, height=600)
    assert error is None and (ubic.x, ubic.y) == (100, 200)
    assert llamadas[0].capability is Capability.VISION
    assert llamadas[0].images == ("AAA",)


@pytest.mark.anyio
async def test_locate_con_el_mel_en_error_no_devuelve_coordenadas(monkeypatch):
    _fake_mel(monkeypatch, resultado=_FakeResult(ok=False, error="sin proveedores"))
    ubic, error = await vision_click.locate("un botón", "AAA", width=800, height=600)
    assert ubic is None and "sin proveedores" in error


@pytest.mark.anyio
async def test_locate_con_respuesta_ininteligible_no_hace_clic(monkeypatch):
    _fake_mel(monkeypatch, resultado=_FakeResult("pues no sé, mira tú"))
    ubic, error = await vision_click.locate("un botón", "AAA", width=800, height=600)
    assert ubic is None and "no ha localizado" in error


# ---------------------------------------------------------------------------
# 7 · desktop.find_and_click — el cableado real (pyautogui falso)
# ---------------------------------------------------------------------------
class _FakeImg:
    def __init__(self, w, h):
        self.width, self.height = w, h

    def save(self, buf, format="PNG"):
        buf.write(b"\x89PNG\r\n\x1a\nFAKE")


class _FakePyAutoGui:
    FailSafeException = RuntimeError

    def __init__(self, screen=(1920, 1080), shot=(1920, 1080)):
        self._screen, self._shot = screen, shot
        self.clicks: List[tuple] = []
        self.dobles: List[tuple] = []

    def size(self): return self._screen
    def screenshot(self): return _FakeImg(*self._shot)
    def click(self, x, y): self.clicks.append((x, y))
    def doubleClick(self, x, y): self.dobles.append((x, y))


@pytest.fixture
def desktop_fake(monkeypatch):
    from app.tools import desktop_tool

    fake = _FakePyAutoGui()
    monkeypatch.setattr(desktop_tool, "pyautogui", fake)
    monkeypatch.setattr(desktop_tool, "_ensure_pyautogui", lambda: None)
    return fake


@pytest.mark.anyio
async def test_desktop_find_and_click_clica_donde_dijo_el_modelo(monkeypatch, desktop_fake):
    from app.tools.desktop_tool import DesktopTool

    _fake_mel(monkeypatch, resultado=_FakeResult('{"x": 640, "y": 360}'))
    r = await DesktopTool().execute("find_and_click", {"description": "el botón de guardar"})
    assert r["success"], r
    assert desktop_fake.clicks == [(640, 360)]
    assert r["result"]["located_by"] == "vision"
    assert r["result"]["description"] == "el botón de guardar"


@pytest.mark.anyio
async def test_desktop_find_and_click_convierte_la_escala_antes_de_clicar(monkeypatch):
    """La captura sale a 2560x1440 y el ratón vive en 1280x720: el clic tiene
    que ir a la MITAD de lo que dijo el modelo, no a lo que dijo."""
    from app.tools import desktop_tool
    from app.tools.desktop_tool import DesktopTool

    fake = _FakePyAutoGui(screen=(1280, 720), shot=(2560, 1440))
    monkeypatch.setattr(desktop_tool, "pyautogui", fake)
    monkeypatch.setattr(desktop_tool, "_ensure_pyautogui", lambda: None)
    _fake_mel(monkeypatch, resultado=_FakeResult('{"x": 1000, "y": 800}'))

    r = await DesktopTool().execute("find_and_click", {"description": "un icono"})
    assert r["success"]
    assert fake.clicks == [(500, 400)]
    assert r["result"]["image_coords"] == [1000, 800]


@pytest.mark.anyio
async def test_desktop_find_and_click_sin_vision_no_clica_nada(monkeypatch, desktop_fake):
    from app.tools.desktop_tool import DesktopTool

    _fake_mel(monkeypatch, disponible=False)
    r = await DesktopTool().execute("find_and_click", {"description": "el botón"})
    assert not r["success"]
    assert "ningún modelo con visión" in r["error"]
    assert desktop_fake.clicks == []      # LO IMPORTANTE: no se hizo clic


@pytest.mark.anyio
async def test_desktop_find_and_click_si_el_modelo_no_lo_ve_no_clica(monkeypatch, desktop_fake):
    from app.tools.desktop_tool import DesktopTool

    _fake_mel(monkeypatch, resultado=_FakeResult('{"not_found": true}'))
    r = await DesktopTool().execute("find_and_click", {"description": "un unicornio"})
    assert not r["success"]
    assert desktop_fake.clicks == []


@pytest.mark.anyio
async def test_desktop_find_and_click_sin_descripcion_falla_claro(desktop_fake):
    from app.tools.desktop_tool import DesktopTool

    r = await DesktopTool().execute("find_and_click", {})
    assert not r["success"] and "description" in r["error"]


@pytest.mark.anyio
async def test_desktop_find_and_click_doble(monkeypatch, desktop_fake):
    from app.tools.desktop_tool import DesktopTool

    _fake_mel(monkeypatch, resultado=_FakeResult('{"x": 10, "y": 20}'))
    r = await DesktopTool().execute("find_and_click", {"description": "x", "double": True})
    assert r["success"]
    assert desktop_fake.dobles == [(10, 20)] and desktop_fake.clicks == []


# ---------------------------------------------------------------------------
# 8 · browser.find_and_click — set-of-mark con dobles de Playwright
# ---------------------------------------------------------------------------
class _FakeMouse:
    def __init__(self): self.clicks: List[tuple] = []
    async def click(self, x, y): self.clicks.append((x, y))


class _FakeBrowserPage:
    def __init__(self, marks=None, evaluate_falla=False):
        self.mouse = _FakeMouse()
        self.viewport_size = {"width": 1280, "height": 720}
        self._marks = marks if marks is not None else []
        self._evaluate_falla = evaluate_falla
        self.evaluaciones: List[str] = []

    async def evaluate(self, js, *a, **kw):
        self.evaluaciones.append(js)
        # El JS de limpieza es una línea; el de set-of-mark recibe opciones.
        # [C·WEB-3] `_SET_OF_MARK_JS` devuelve {marks, truncated, scroll}, no una
        # lista suelta — el doble sigue el contrato REAL (patrón LOG-1: un doble
        # de un contrato que evoluciona tiene que evolucionar con él).
        if not js.strip().startswith("(opciones)"):
            return None                      # limpieza de marcas
        if self._evaluate_falla:
            raise RuntimeError("CSP bloquea la inyección")
        return {"marks": self._marks, "truncated": False,
                "scroll": {"y": 0, "can_down": False, "can_up": False}}

    async def screenshot(self, type="png"):
        return b"\x89PNG\r\n\x1a\nFAKE"


def _browser_fake(monkeypatch, page):
    from app.tools import browser_tool

    async def _get_page(tab_id=None, session_key=None):
        return "tab1", page

    async def _dismiss(p):
        return False

    monkeypatch.setattr(browser_tool, "_get_page", _get_page)
    monkeypatch.setattr(browser_tool, "_dismiss_consent", _dismiss)


@pytest.mark.anyio
async def test_browser_find_and_click_elige_por_indice_y_clica_el_centro_real(monkeypatch):
    from app.tools.browser_tool import BrowserTool

    page = _FakeBrowserPage(marks=[
        {"index": 0, "role": "button", "text": "Rechazar", "center": [100, 200]},
        {"index": 1, "role": "button", "text": "Aceptar todo", "center": [400, 200]},
    ])
    _browser_fake(monkeypatch, page)
    llamadas: List[ExecutionRequest] = []
    _fake_mel(monkeypatch, resultado=_FakeResult('{"index": 1}'), captura=llamadas)

    r = await BrowserTool().execute("find_and_click", {"description": "aceptar cookies"})
    assert r["success"], r
    assert page.mouse.clicks == [(400, 200)]       # el centro REAL del elemento
    assert r["result"]["located_by"] == "set_of_mark"
    assert r["result"]["element"] == "Aceptar todo"
    # el prompt llevaba la lista de cajas
    assert "[1] button: Aceptar todo" in llamadas[0].prompt


@pytest.mark.anyio
async def test_browser_find_and_click_retira_las_marcas_antes_de_clicar(monkeypatch):
    """Si las cajas se quedan pintadas, el clic cae sobre el overlay y no sobre
    la página — el mismo tipo de fallo que el muro de cookies de A-3."""
    from app.tools.browser_tool import BrowserTool

    page = _FakeBrowserPage(marks=[{"index": 0, "role": "button", "text": "Ok",
                                    "center": [1, 2]}])
    _browser_fake(monkeypatch, page)
    _fake_mel(monkeypatch, resultado=_FakeResult('{"index": 0}'))

    await BrowserTool().execute("find_and_click", {"description": "ok"})
    assert any("__aithera_mark" in js and "SEL" not in js for js in page.evaluaciones)


@pytest.mark.anyio
async def test_browser_find_and_click_indice_inexistente_no_clica(monkeypatch):
    from app.tools.browser_tool import BrowserTool

    page = _FakeBrowserPage(marks=[{"index": 0, "role": "button", "text": "Ok",
                                    "center": [1, 2]}])
    _browser_fake(monkeypatch, page)
    _fake_mel(monkeypatch, resultado=_FakeResult('{"index": 42}'))

    r = await BrowserTool().execute("find_and_click", {"description": "algo"})
    assert not r["success"]
    assert "[42]" in r["error"]
    assert page.mouse.clicks == []


@pytest.mark.anyio
async def test_browser_find_and_click_cae_a_coordenadas_si_el_dom_no_se_puede_marcar(monkeypatch):
    """Una página con CSP estricta bloquea la inyección: el modo de último
    recurso (coordenadas puras) tiene que seguir funcionando."""
    from app.tools.browser_tool import BrowserTool

    page = _FakeBrowserPage(evaluate_falla=True)
    _browser_fake(monkeypatch, page)
    llamadas: List[ExecutionRequest] = []
    _fake_mel(monkeypatch, resultado=_FakeResult('{"x": 640, "y": 360}'), captura=llamadas)

    r = await BrowserTool().execute("find_and_click", {"description": "el botón de play"})
    assert r["success"]
    assert page.mouse.clicks == [(640, 360)]
    assert r["result"]["located_by"] == "vision_coords"
    assert "[0]" not in llamadas[0].prompt        # sin cajas que ofrecer


@pytest.mark.anyio
async def test_browser_find_and_click_sin_vision_no_clica(monkeypatch):
    from app.tools.browser_tool import BrowserTool

    page = _FakeBrowserPage(marks=[])
    _browser_fake(monkeypatch, page)
    _fake_mel(monkeypatch, disponible=False)

    r = await BrowserTool().execute("find_and_click", {"description": "algo"})
    assert not r["success"] and page.mouse.clicks == []


# ---------------------------------------------------------------------------
# 9 · Catálogo, permisos y enrutado (pasos 4 y 6)
# ---------------------------------------------------------------------------
def test_las_dos_acciones_piden_confirmacion():
    """Un clic es un clic: que lo decida un modelo de visión no lo hace menos
    real. Mismo gate que `desktop.click`/`browser.click`."""
    from app.tools.browser_tool import BrowserTool
    from app.tools.desktop_tool import DesktopTool

    for tool in (BrowserTool(), DesktopTool()):
        acciones = {a["id"]: a for a in tool.list_actions()}
        assert acciones["find_and_click"]["requires_confirmation"] is True


def test_permisos_de_find_and_click():
    from app.automation.permissions import permission_for_tool_action

    assert permission_for_tool_action("desktop", "find_and_click") == "computer.use"
    assert permission_for_tool_action("browser", "find_and_click") == "browser.use"


def test_el_prompt_del_toolloop_manda_usar_el_selector_primero():
    """La visión es el RESPALDO, no la primera opción: el DOM es más barato y
    más preciso cuando existe (paso 4 del plan)."""
    from app.tie.toolloop import _SYSTEM_PROMPT

    assert "find_and_click" in _SYSTEM_PROMPT
    assert "ÚLTIMO RECURSO" in _SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# 10 · La UI y la EJECUCIÓN comparten el criterio de aptitud
# ---------------------------------------------------------------------------
def test_list_models_marca_no_apto_para_vision_a_los_modelos_ciegos(monkeypatch):
    """EL FALLO QUE CIERRA: el selector de Ajustes → Inteligencia ofrecía
    modelos ciegos para la capacidad de visión y, al elegir uno, `set_primary`
    lo rechazaba por dentro — el usuario veía que su elección "no se guardaba"
    sin ninguna explicación. `unfit` es lo que la UI filtra, así que tiene que
    decir exactamente lo mismo que `is_capable`."""
    import app.mel as mel
    from app.mel import registry

    disponibles = [
        ModelRef(provider="ollama", model="llama3", is_local=True),
        ModelRef(provider="ollama", model="qwen2.5vl:7b", is_local=True),
        ModelRef(provider="gemini", model="gemini-3.5-flash"),
    ]
    monkeypatch.setattr(registry, "list_available", lambda: disponibles)

    por_key = {m["key"]: m for m in mel.list_models()}
    assert "vision" in por_key["ollama:llama3"]["unfit"]
    assert "vision" in por_key["ollama:llama3"]["unfit_catalog"]
    assert "vision" not in por_key["ollama:qwen2.5vl:7b"]["unfit"]
    assert "vision" not in por_key["gemini:gemini-3.5-flash"]["unfit"]


def test_unfit_y_is_capable_no_pueden_desalinearse(monkeypatch):
    """El invariante, no el caso concreto: para CADA modelo y CADA capacidad,
    lo que la UI filtra (`unfit`) tiene que coincidir con lo que la ejecución
    permite (`is_capable`). Si mañana se añade otra regla de aptitud en un solo
    sitio, este test la caza."""
    import app.mel as mel
    from app.mel import registry

    disponibles = [
        ModelRef(provider="ollama", model="llama3", is_local=True),
        ModelRef(provider="ollama", model="llava:13b", is_local=True),
        ModelRef(provider="gemini", model="gemini-3.5-flash"),
        ModelRef(provider="claude_code", model="opus"),
    ]
    monkeypatch.setattr(registry, "list_available", lambda: disponibles)

    por_key = {m["key"]: m for m in mel.list_models()}
    for ref in disponibles:
        no_aptas = set(por_key[ref.key]["unfit"])
        for cap in Capability:
            assert is_capable(ref, cap) == (cap.value not in no_aptas), (
                f"{ref.key} / {cap.value}: la UI y la ejecución no coinciden"
            )
