# tests/test_cweb3_webloop.py — C·WEB-3 (doc 32): bucle agentic de navegación.
#
# Sin red, sin navegador y sin modelo: dobles de Page/Context al estilo de
# `test_audit_s3_browser.py`, y un ÚNICO fake en la frontera del LLM
# (`mel.complete`). El bucle, el `page_state`, la resolución por índice, la
# frontera de seguridad y el ApprovalGate son código REAL.
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from app.tie import webloop
from app.tools.browser_tool import BrowserTool, _serialize_marks


# ---------------------------------------------------------------------------
# Dobles
# ---------------------------------------------------------------------------
class _FakeKeyboard:
    def __init__(self):
        self.typed: List[str] = []
        self.pressed: List[str] = []

    async def type(self, text): self.typed.append(text)
    async def press(self, key): self.pressed.append(key)


class _FakeMouse:
    def __init__(self): self.clicks: List[tuple] = []
    async def click(self, x, y): self.clicks.append((x, y))


class _FakePage:
    """Página con una lista de elementos que puede CAMBIAR entre vueltas — que
    es justo lo que hace una página real y el motivo por el que los índices se
    revalidan en cada acción."""

    def __init__(self, marks=None, url="https://tienda.example/", title="Tienda",
                 evaluate_falla=False):
        self.mouse = _FakeMouse()
        self.keyboard = _FakeKeyboard()
        self.viewport_size = {"width": 1280, "height": 720}
        self.url = url
        self._title = title
        self._marks = marks if marks is not None else []
        self._evaluate_falla = evaluate_falla
        self.gotos: List[str] = []
        self.wheels: List[tuple] = []

    def set_marks(self, marks): self._marks = marks

    async def title(self): return self._title

    async def evaluate(self, js, *a, **kw):
        if not js.strip().startswith("(opciones)"):
            return None                      # limpieza de marcas
        if self._evaluate_falla:
            raise RuntimeError("CSP")
        opciones = (a[0] if a else {}) or {}
        marks = self._marks[: int(opciones.get("max", 60))]
        return {"marks": marks, "truncated": len(self._marks) > len(marks),
                "scroll": {"y": 0, "can_down": True, "can_up": False}}

    async def screenshot(self, type="png"): return b"\x89PNG\r\n\x1a\nFAKE"

    async def goto(self, url, **kw):
        self.gotos.append(url)
        self.url = url
        return None


def _mark(i, text, tag="button", **extra):
    m = {"index": i, "tag": tag, "type": None, "role": tag, "text": text,
         "editable": tag in ("input", "textarea"), "center": [100 + i * 10, 200]}
    m.update(extra)
    return m


@pytest.fixture
def page_fake(monkeypatch):
    from app.tools import browser_tool

    page = _FakePage()

    async def _get_page(tab_id=None, session_key=None):
        return "tab1", page

    async def _dismiss(p):
        return False

    monkeypatch.setattr(browser_tool, "_get_page", _get_page)
    monkeypatch.setattr(browser_tool, "_dismiss_consent", _dismiss)
    return page


# ---------------------------------------------------------------------------
# 1 · page_state (paso 2 del plan)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_page_state_devuelve_indices_url_y_titulo(page_fake):
    page_fake.set_marks([_mark(0, "Buscar", tag="input"), _mark(1, "Aceptar")])
    r = await BrowserTool().execute("page_state", {})
    assert r["success"], r
    res = r["result"]
    assert res["url"] == "https://tienda.example/"
    assert res["title"] == "Tienda"
    assert [e["index"] for e in res["elements"]] == [0, 1]
    assert res["scroll"]["can_down"] is True


@pytest.mark.anyio
async def test_page_state_sin_captura_por_defecto(page_fake):
    """La imagen es OPCIONAL a propósito: mandarla en cada vuelta multiplicaría
    el coste por diez y en la mayoría de los pasos la lista de texto basta."""
    page_fake.set_marks([_mark(0, "Ok")])
    r = await BrowserTool().execute("page_state", {})
    assert "image_base64" not in r["result"]
    r2 = await BrowserTool().execute("page_state", {"screenshot": True})
    assert r2["result"]["image_base64"]


@pytest.mark.anyio
async def test_page_state_avisa_si_la_lista_esta_recortada(page_fake):
    page_fake.set_marks([_mark(i, f"e{i}") for i in range(10)])
    r = await BrowserTool().execute("page_state", {"max": 3})
    assert r["result"]["truncated"] is True
    assert len(r["result"]["elements"]) == 3


@pytest.mark.anyio
async def test_page_state_falla_limpio_si_la_pagina_bloquea_la_inyeccion(monkeypatch):
    from app.tools import browser_tool

    page = _FakePage(evaluate_falla=True)

    async def _get_page(tab_id=None, session_key=None): return "t", page
    async def _dismiss(p): return False

    monkeypatch.setattr(browser_tool, "_get_page", _get_page)
    monkeypatch.setattr(browser_tool, "_dismiss_consent", _dismiss)
    r = await BrowserTool().execute("page_state", {})
    assert not r["success"] and "estado de la pagina" in r["error"]


def test_serialize_marks_usa_el_formato_de_browser_use():
    """`[i]<tag>texto</tag>` — el formato del spike, compacto y con el índice
    delante, que es lo que el modelo tiene que devolver."""
    texto = _serialize_marks([
        {"index": 0, "tag": "button", "role": "button", "text": "Añadir al carrito"},
        {"index": 1, "tag": "input", "type": "search", "role": "searchbox", "text": "Buscar"},
    ])
    assert '[0]<button>Añadir al carrito</button>' in texto
    assert '[1]<input type="search" role="searchbox">Buscar</input>' in texto


# ---------------------------------------------------------------------------
# 2 · click_index / type_index
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_click_index_clica_el_centro_real(page_fake):
    page_fake.set_marks([_mark(0, "A"), _mark(1, "B")])
    r = await BrowserTool().execute("click_index", {"index": 1})
    assert r["success"]
    assert page_fake.mouse.clicks == [(110, 200)]
    assert r["result"]["element"] == "B"


@pytest.mark.anyio
async def test_type_index_escribe_y_pulsa_intro(page_fake):
    page_fake.set_marks([_mark(0, "Buscar", tag="input")])
    r = await BrowserTool().execute("type_index", {"index": 0, "text": "zapatos", "enter": True})
    assert r["success"]
    assert page_fake.keyboard.typed == ["zapatos"]
    assert page_fake.keyboard.pressed == ["Enter"]


@pytest.mark.anyio
async def test_un_indice_que_ya_no_existe_no_clica_nada(page_fake):
    """LO IMPORTANTE: entre observar y actuar la página pudo cambiar. Un índice
    viejo NO se aproxima al más parecido: se rechaza."""
    page_fake.set_marks([_mark(0, "A")])
    r = await BrowserTool().execute("click_index", {"index": 7})
    assert not r["success"]
    assert "[7]" in r["error"]
    assert page_fake.mouse.clicks == []


@pytest.mark.anyio
async def test_click_index_revalida_contra_la_pagina_del_momento(page_fake):
    """La página cambia entre la observación y la acción: el elemento [0] ya no
    es el mismo, y el clic va al centro NUEVO, no al que se vio antes."""
    page_fake.set_marks([_mark(0, "Antiguo")])
    await BrowserTool().execute("page_state", {})
    page_fake.set_marks([{**_mark(0, "Nuevo"), "center": [999, 888]}])
    r = await BrowserTool().execute("click_index", {"index": 0})
    assert r["success"] and page_fake.mouse.clicks == [(999, 888)]
    assert r["result"]["element"] == "Nuevo"


# ---------------------------------------------------------------------------
# 3 · La frontera de seguridad (paso 4 del plan) — funciones puras
# ---------------------------------------------------------------------------
def test_detecta_los_pasos_que_comprometen_al_usuario():
    for t in ["Pagar ahora", "Comprar", "Finalizar pedido", "Confirmar reserva",
              "Place order", "Checkout", "Enviar formulario", "Acepto los términos",
              "Eliminar cuenta", "Suscribirme"]:
        assert webloop.is_sensitive_element(t), t


def test_no_marca_como_sensible_lo_que_no_lo_es():
    """Un gate de más cuesta una pregunta; uno de menos, una compra no querida —
    pero marcarlo TODO haría el bucle inservible."""
    for t in ["Buscar", "Siguiente página", "Ver detalles", "Añadir al carrito",
              "Filtrar por precio", "Cerrar", "Inicio", ""]:
        assert not webloop.is_sensitive_element(t), t


def test_detecta_los_campos_en_los_que_jamas_se_escribe():
    for t in ["Contraseña", "Password", "Número de tarjeta", "CVV", "IBAN",
              "Código de seguridad", "DNI", "PIN"]:
        assert webloop.is_forbidden_field(t), t


def test_los_campos_normales_si_se_pueden_rellenar():
    for t in ["Buscar", "Nombre", "Ciudad", "Comentario", "Email", ""]:
        assert not webloop.is_forbidden_field(t), t


# ---------------------------------------------------------------------------
# 4 · El bucle — con el LLM fake y el ToolManager real
# ---------------------------------------------------------------------------
class _FakeResult:
    def __init__(self, text="", ok=True, error=None):
        self.text, self.ok, self.error = text, ok, error


def _fake_mel(monkeypatch, decisiones: List[str], captura: Optional[list] = None):
    """El modelo devuelve las decisiones en orden. Cuando se agotan, 'done'."""
    import app.mel as mel

    pendientes = list(decisiones)

    async def _complete(req):
        if captura is not None:
            captura.append(req)
        if pendientes:
            return _FakeResult(pendientes.pop(0))
        return _FakeResult('{"action": "done", "answer": "sin más pasos"}')

    monkeypatch.setattr(mel, "complete", _complete)


class _ToolManagerFake:
    """Delega en la BrowserTool REAL (con la página falsa detrás) — así el bucle
    ejercita el camino de verdad sin necesitar la whitelist ni la BD."""

    def __init__(self):
        self.tool = BrowserTool()
        self.llamadas: List[tuple] = []

    async def execute(self, tool_id, action, params, **kw):
        self.llamadas.append((tool_id, action, dict(params)))
        return await self.tool.execute(action, params)


@pytest.mark.anyio
async def test_el_bucle_navega_por_indices_hasta_done(monkeypatch, page_fake):
    page_fake.set_marks([_mark(0, "Buscar", tag="input"), _mark(1, "Ver ofertas")])
    _fake_mel(monkeypatch, [
        '{"action": "type", "index": 0, "text": "zapatos", "enter": true, "why": "buscar"}',
        '{"action": "click", "index": 1, "why": "abrir ofertas"}',
        '{"action": "done", "answer": "He buscado zapatos y abierto las ofertas"}',
    ])
    tm = _ToolManagerFake()
    r = await webloop.run("busca zapatos", tool_manager=tm)

    assert r.ok, r
    assert r.steps == 3
    assert page_fake.keyboard.typed == ["zapatos"]
    # Dos clics: el primero es de `type_index` para dar FOCO al campo antes de
    # teclear (sin él, el texto se pierde); el segundo es el clic real del paso 2.
    assert page_fake.mouse.clicks == [(100, 200), (110, 200)]
    assert "zapatos" in r.answer
    # observó ANTES de cada decisión
    assert [a for t, a, p in tm.llamadas].count("page_state") == 3


@pytest.mark.anyio
async def test_el_objetivo_y_lo_ya_hecho_viajan_en_cada_vuelta(monkeypatch, page_fake):
    """Sin el objetivo en cada mensaje, el modelo lo pierde a las 15 vueltas;
    sin el historial, repite el mismo clic para siempre."""
    page_fake.set_marks([_mark(0, "Siguiente")])
    prompts: list = []
    _fake_mel(monkeypatch, [
        '{"action": "click", "index": 0}',
        '{"action": "done", "answer": "listo"}',
    ], captura=prompts)
    await webloop.run("llegar al final", tool_manager=_ToolManagerFake())

    assert "llegar al final" in prompts[0].prompt
    assert "PASO 1" in prompts[0].prompt
    assert "LO QUE YA HAS HECHO" in prompts[1].prompt
    assert "Siguiente" in prompts[1].prompt


@pytest.mark.anyio
async def test_un_paso_sensible_abre_gate_y_sin_permiso_no_se_pulsa(monkeypatch, page_fake):
    """[C·WEB-4] El objetivo era «compra algo», que desde entonces activa el
    flujo de compra — y ahí «Pagar ahora» es una PARADA, no un gate (con el
    perfil Autónomo un gate se auto-aprobaría y Aithera pagaría sola). Lo que
    este test fija es el gate GENÉRICO, así que su objetivo pasa a ser uno que
    no encaja en ningún flujo; el caso de la compra lo cubre
    `test_cweb4_flujos.py`."""
    page_fake.set_marks([_mark(0, "Pagar ahora")])
    _fake_mel(monkeypatch, ['{"action": "click", "index": 0, "why": "pagar"}'])

    abiertos = []

    class _Gate:
        async def request_approval(self, **kw):
            abiertos.append(kw)
            return "gate-1"

    class _GateRechaza(_Gate):
        def get(self, gid):
            class _A:
                status = "rejected"
                resolution_note = ""
            return _A()

    r = await webloop.run("sigue el proceso hasta el final",
                          tool_manager=_ToolManagerFake(),
                          approval_gate=_GateRechaza(), max_steps=2)
    assert abiertos and abiertos[0]["kind"] == "web.sensitive_click"
    assert "Pagar ahora" in abiertos[0]["title"]
    assert page_fake.mouse.clicks == []          # LO IMPORTANTE: no se pagó
    assert any("Pagar ahora" in l for l in r.limitations)


@pytest.mark.anyio
async def test_un_paso_sensible_aprobado_si_se_pulsa(monkeypatch, page_fake):
    """[C·WEB-4] Mismo motivo que el test de arriba: el objetivo pasa a ser uno
    sin flujo, para seguir probando el gate genérico y no la parada de un
    playbook."""
    page_fake.set_marks([_mark(0, "Confirmar pedido")])
    _fake_mel(monkeypatch, [
        '{"action": "click", "index": 0}',
        '{"action": "done", "answer": "pedido confirmado"}',
    ])

    class _GateAprueba:
        async def request_approval(self, **kw): return "g"
        def get(self, gid):
            class _A:
                status = "approved"
                resolution_note = ""
            return _A()

    r = await webloop.run("termina el trámite de la web",
                          tool_manager=_ToolManagerFake(),
                          approval_gate=_GateAprueba())
    assert r.ok and page_fake.mouse.clicks == [(100, 200)]


@pytest.mark.anyio
async def test_un_paso_normal_NO_abre_gate(monkeypatch, page_fake):
    """Si cada clic preguntara, navegar sería inútil. Solo lo que compromete."""
    page_fake.set_marks([_mark(0, "Ver más productos")])
    _fake_mel(monkeypatch, [
        '{"action": "click", "index": 0}',
        '{"action": "done", "answer": "ok"}',
    ])
    abiertos = []

    class _Gate:
        async def request_approval(self, **kw):
            abiertos.append(kw)
            return "g"

    r = await webloop.run("mira productos", tool_manager=_ToolManagerFake(),
                          approval_gate=_Gate())
    assert r.ok and abiertos == []
    assert page_fake.mouse.clicks == [(100, 200)]


@pytest.mark.anyio
async def test_jamas_escribe_en_un_campo_de_contrasena(monkeypatch, page_fake):
    """El límite DURO: ni con permiso, ni en modo Autónomo. El modo autónomo
    significa «no me preguntes», nunca «escribe mi contraseña»."""
    page_fake.set_marks([_mark(0, "Contraseña", tag="input")])
    _fake_mel(monkeypatch, ['{"action": "type", "index": 0, "text": "loquesea"}'])

    class _GateApruebaTodo:
        async def request_approval(self, **kw): return "g"
        def get(self, gid):
            class _A:
                status = "approved"
                resolution_note = ""
            return _A()

    r = await webloop.run("inicia sesión", tool_manager=_ToolManagerFake(),
                          approval_gate=_GateApruebaTodo(), max_steps=2)
    assert page_fake.keyboard.typed == []        # NADA tecleado
    assert any("introduce el usuario" in l for l in r.limitations)


@pytest.mark.anyio
async def test_el_bucle_corta_por_atasco_sin_agotar_los_pasos(monkeypatch, page_fake):
    """Insistir en un índice que no existe no aporta información nueva: se corta
    a las 4 vueltas estériles, no a los 25 pasos (misma regla que la Sesión A)."""
    page_fake.set_marks([_mark(0, "A")])
    _fake_mel(monkeypatch, ['{"action": "click", "index": 99}'] * 20)
    r = await webloop.run("algo", tool_manager=_ToolManagerFake(), max_steps=25)
    assert not r.ok
    assert r.steps <= webloop.MAX_STALLED
    assert "falta de progreso" in r.error


@pytest.mark.anyio
async def test_give_up_devuelve_el_motivo_real(monkeypatch, page_fake):
    page_fake.set_marks([_mark(0, "A")])
    _fake_mel(monkeypatch, [
        '{"action": "give_up", "reason": "la tienda pide iniciar sesión"}',
    ])
    r = await webloop.run("compra algo", tool_manager=_ToolManagerFake())
    assert not r.ok and "iniciar sesión" in r.answer


@pytest.mark.anyio
async def test_el_modelo_caido_no_rompe_el_bucle(monkeypatch, page_fake):
    import app.mel as mel

    page_fake.set_marks([_mark(0, "A")])

    async def _complete(req):
        return _FakeResult(ok=False, error="sin proveedores")

    monkeypatch.setattr(mel, "complete", _complete)
    r = await webloop.run("algo", tool_manager=_ToolManagerFake())
    assert not r.ok and "sin proveedores" in r.error


@pytest.mark.anyio
async def test_scroll_y_goto_funcionan(monkeypatch, page_fake):
    page_fake.set_marks([_mark(0, "A")])
    _fake_mel(monkeypatch, [
        '{"action": "scroll", "direction": "down"}',
        '{"action": "goto", "url": "https://otra.example/"}',
        '{"action": "done", "answer": "ok"}',
    ])
    tm = _ToolManagerFake()
    r = await webloop.run("navega", tool_manager=tm)
    assert r.ok
    assert any(a == "scroll" for _, a, _ in tm.llamadas)
    assert page_fake.gotos == ["https://otra.example/"]


# ---------------------------------------------------------------------------
# 5 · Parseo de la decisión (puro)
# ---------------------------------------------------------------------------
def test_parse_decision_acepta_las_seis_acciones():
    for accion in ("click", "type", "scroll", "goto", "done", "give_up"):
        d = webloop.parse_decision('{"action": "%s"}' % accion)
        assert d is not None and d["action"] == accion


def test_parse_decision_rechaza_lo_que_no_entiende():
    assert webloop.parse_decision("") is None
    assert webloop.parse_decision("pues no sé") is None
    assert webloop.parse_decision('{"action": "formatear_disco"}') is None
    assert webloop.parse_decision('{"foo": 1}') is None


def test_parse_decision_tolera_markdown():
    d = webloop.parse_decision('```json\n{"action": "click", "index": 3}\n```')
    assert d["action"] == "click" and d["index"] == 3


# ---------------------------------------------------------------------------
# 6 · Catálogo, permisos y frontera modular
# ---------------------------------------------------------------------------
def test_las_acciones_nuevas_estan_en_el_catalogo():
    acciones = {a["id"]: a for a in BrowserTool().list_actions()}
    for a in ("page_state", "click_index", "type_index", "browse"):
        assert a in acciones
    # observar es lectura; actuar compromete
    assert acciones["page_state"]["requires_confirmation"] is False
    assert acciones["click_index"]["requires_confirmation"] is True
    assert acciones["type_index"]["requires_confirmation"] is True
    assert acciones["browse"]["requires_confirmation"] is True


def test_permiso_de_las_acciones_nuevas_es_browser_use():
    from app.automation.permissions import permission_for_tool_action

    for a in ("page_state", "click_index", "type_index", "browse"):
        assert permission_for_tool_action("browser", a) == "browser.use"


def test_browse_se_expone_en_el_barrel_del_tie():
    import app.tie as tie

    assert hasattr(tie, "browse")
    assert tie.browse is webloop.run
