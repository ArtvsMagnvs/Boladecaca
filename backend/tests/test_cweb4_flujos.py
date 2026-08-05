# tests/test_cweb4_flujos.py — C·WEB-4 (doc 32): los cinco casos de uso reales
# sobre el bucle agentic.
#
# Sin red, sin navegador y sin modelo. Un ÚNICO fake en la frontera del LLM
# (`mel.complete`); el bucle, la `BrowserTool`, los playbooks y las fronteras de
# seguridad son código REAL.
#
# Lo que estos tests fijan, por encima de "el flujo funciona", es DÓNDE PARA cada
# uno. Un flujo que llega más lejos de lo que debía —pagar, confirmar la cita,
# instalar el ejecutable, publicar en el foro— es el fallo caro; el barato es
# quedarse corto. Por eso la mitad de las pruebas comprueban que NO se pulsó.
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from app.tie import webflows, webloop
from app.tools.browser_tool import BrowserTool


# ---------------------------------------------------------------------------
# Dobles (mismo estilo que test_cweb3_webloop; se mantienen en cada archivo para
# que ninguno dependa del otro, pero deben moverse a la vez si el contrato de
# Page cambia — el fallo LOG-1 del proyecto es justo un doble que se queda atrás)
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
    def __init__(self, marks=None, url="https://sitio.example/", title="Sitio"):
        self.mouse = _FakeMouse()
        self.keyboard = _FakeKeyboard()
        self.viewport_size = {"width": 1280, "height": 720}
        self.url = url
        self._title = title
        self._marks = marks or []
        self.gotos: List[str] = []

    def set_marks(self, marks): self._marks = marks

    async def title(self): return self._title

    async def evaluate(self, js, *a, **kw):
        if not js.strip().startswith("(opciones)"):
            return None
        opciones = (a[0] if a else {}) or {}
        marks = self._marks[: int(opciones.get("max", 60))]
        return {"marks": marks, "truncated": len(self._marks) > len(marks),
                "scroll": {"y": 0, "can_down": True, "can_up": False}}

    async def screenshot(self, type="png"): return b"PNG"

    async def goto(self, url, **kw):
        self.gotos.append(url)
        self.url = url
        return None

    def is_closed(self): return False


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


class _FakeResult:
    def __init__(self, text="", ok=True, error=None):
        self.text, self.ok, self.error = text, ok, error


def _fake_mel(monkeypatch, decisiones: List[str], captura: Optional[list] = None):
    import app.mel as mel

    pendientes = list(decisiones)

    async def _complete(req):
        if captura is not None:
            captura.append(req)
        if pendientes:
            return _FakeResult(pendientes.pop(0))
        return _FakeResult('{"action": "done", "answer": "sin mas pasos"}')

    monkeypatch.setattr(mel, "complete", _complete)


class _ToolManagerFake:
    def __init__(self):
        self.tool = BrowserTool()
        self.llamadas: List[tuple] = []

    async def execute(self, tool_id, action, params, **kw):
        self.llamadas.append((tool_id, action, dict(params)))
        return await self.tool.execute(action, params)


class _GateApruebaTodo:
    """El gate más permisivo posible. Se usa a propósito en los tests de parada
    dura: si la frontera dependiera del gate, con esto se cruzaría."""

    def __init__(self): self.abiertos: List[dict] = []

    async def request_approval(self, **kw):
        self.abiertos.append(kw)
        return "g"

    def get(self, gid):
        class _A:
            status = "approved"
            resolution_note = ""
        return _A()


# ---------------------------------------------------------------------------
# 1 · Detección del flujo (pura)
# ---------------------------------------------------------------------------
def test_cada_encargo_activa_su_flujo():
    casos = {
        "añádeme leche y pan al carrito del Carrefour": "compra",
        "pídeme cita previa en Hacienda para el jueves": "cita",
        "descárgame el instalador de Blender": "descarga",
        "dime dónde consigo la api key de Groq": "api_key",
        "busca en el foro qué opinan del coche": "foro",
    }
    for goal, esperado in casos.items():
        assert webflows.detect(goal) == esperado, goal


def test_un_objetivo_normal_no_activa_ningun_flujo():
    """Un falso positivo pondría fronteras que no tocan (parar en «Confirmar»
    una tarea que sí debía enviarse). Ante la duda, ninguno."""
    for goal in ["mira el tiempo que va a hacer mañana",
                 "abre la página de la wikipedia sobre el Cid",
                 "resume esta noticia",
                 "busca el precio del iPhone",   # buscar precio NO es comprar
                 ""]:
        assert webflows.detect(goal) is None, goal


def test_la_frontera_de_seguridad_gana_al_modo_lectura():
    """«en el foro el enlace de descarga» activa `descarga`, no `foro`: perder
    el aviso de fuente es peor que perder el modo solo-lectura."""
    assert webflows.detect("busca en el foro el enlace de descarga del juego") == "descarga"


def test_el_flujo_se_puede_forzar_a_mano():
    assert webflows.get("foro").name == "foro"
    assert webflows.get("no_existe") is None
    assert webflows.get(None) is None


# ---------------------------------------------------------------------------
# 2 · Las fronteras, elemento a elemento (puras)
# ---------------------------------------------------------------------------
def test_la_frontera_de_cada_flujo():
    casos = [
        ("compra", ["Pagar", "Tramitar pedido", "Finalizar compra", "Place order",
                    "Proceder al pago", "Comprar ahora"]),
        ("cita", ["Confirmar", "Confirmar cita", "Reservar ahora", "Firmar"]),
        ("descarga", ["Instalar", "Instalar ahora", "Ejecutar", "Install"]),
        ("api_key", ["Iniciar sesión", "Log in", "Crear cuenta", "Create new secret key",
                     "Generar clave"]),
        ("foro", ["Responder", "Publicar", "Votar", "Suscribirse"]),
    ]
    for pb, etiquetas in casos:
        for e in etiquetas:
            assert webflows.is_hard_stop(pb, e), f"{pb}: {e}"


def test_lo_que_hay_que_poder_pulsar_no_es_frontera():
    """Si el flujo parase con todo, no serviría para nada. En concreto «Seguir
    comprando» contiene «compra» como SUBCADENA: por eso la detección del flujo
    va por palabras completas y las fronteras no incluyen «compra» a secas."""
    for pb, etiqueta in [
        ("compra", "Añadir al carrito"), ("compra", "Seguir comprando"),
        ("compra", "Ver cesta"), ("compra", "Buscar"),
        ("cita", "Siguiente"), ("cita", "Elegir hora"),
        ("descarga", "Descargar"), ("descarga", "Ver versiones"),
        ("api_key", "Documentación"), ("api_key", "Precios"),
        ("foro", "Siguiente página"), ("foro", "Ver hilo"),
    ]:
        assert not webflows.is_hard_stop(pb, etiqueta), f"{pb}: {etiqueta}"


def test_sin_flujo_no_hay_frontera_de_flujo():
    """Sin playbook el bucle se comporta EXACTAMENTE como en C·WEB-3."""
    assert not webflows.is_hard_stop(None, "Pagar")
    assert not webflows.is_hard_stop("", "Instalar")


def test_un_termino_corto_dentro_de_otra_palabra_no_cuenta():
    """REGRESIÓN de un fallo real de C·WEB-3 encontrado al escribir estos tests:
    «pin» es subcadena de «o-PIN-iones», así que buscar «opiniones» en un foro se
    rechazaba con «no relleno contraseñas». Con palabra completa deja de pasar —
    y las formas en las que una web etiqueta de verdad ese campo siguen
    casando."""
    assert not webloop.is_forbidden_field("opiniones")
    assert not webloop.is_forbidden_field("Escribe tu opinión")
    for si in ["CVV", "CVV:", "cvv-input", "Introduce el PIN", "DNI / NIE"]:
        assert webloop.is_forbidden_field(si), si


def test_la_caja_de_busqueda_se_distingue_de_los_demas_campos():
    for si in ["Buscar", "Buscar en el foro", "Search", "q", "Filtrar"]:
        assert webflows.is_search_field(si), si
    for no in ["Comentario", "Tu respuesta", "Nombre", "Título del hilo", ""]:
        assert not webflows.is_search_field(no), no


# ---------------------------------------------------------------------------
# 3 · Credenciales que nunca deben acabar en un log (puro)
# ---------------------------------------------------------------------------
def test_tapa_lo_que_parece_una_credencial():
    for secreto in [
        "sk-abc123DEF456ghi789",
        "sk-ant-api03-ZZZaaa111bbb222",
        "AIzaSyD9fakeKEY1234567890abcdef",
        "ghp_1234567890abcdefGHIJKL",
        "eyJhbGciOi.eyJzdWIiOjEyMw.aBcDeF12",
        "Bearer abcDEF1234567890xyz",
        "Xk9" + "aB3" * 14,                       # 45 chars, alta entropía
    ]:
        fuera = webflows.redact_secrets(f"la clave es {secreto} y ya está")
        assert secreto not in fuera, secreto
        assert webflows.OCULTO in fuera


def test_no_tapa_lo_que_no_es_una_credencial():
    """Conservador a propósito: tapar de más rompe respuestas útiles (un SHA de
    git o el id de un producto son cosas legítimas que reportar)."""
    intactos = [
        "el commit es a94a8fe5ccb19ba61c4c0873d391e987982fbbd3",   # SHA-1, 40 hex
        "https://tienda.example/producto/1234567890",
        "el hilo https://foro.example/showthread.php?t=9384756",
        "he añadido 3 productos al carrito",
    ]
    for texto in intactos:
        assert webflows.redact_secrets(texto) == texto, texto


# ---------------------------------------------------------------------------
# 4 · Fuentes de descarga (puro)
# ---------------------------------------------------------------------------
def test_avisa_de_una_fuente_dudosa_sin_bloquearla():
    aviso = webflows.download_source_warning("https://gamesrepack.example/crack/juego.exe")
    assert aviso and "crack" in aviso.lower()
    assert "EJECUTABLE" in aviso
    assert "no lo abro" in aviso.lower()          # informa, no bloquea


def test_una_descarga_normal_no_lleva_aviso():
    assert webflows.download_source_warning("https://blender.org/download/blender.zip") == ""
    assert webflows.download_source_warning("") == ""


def test_un_ejecutable_siempre_se_senala():
    for url in ["https://oficial.example/setup.exe", "https://x.example/app.msi",
                "https://x.example/a.apk?token=1"]:
        assert "EJECUTABLE" in webflows.download_source_warning(url), url


# ---------------------------------------------------------------------------
# 5 · COMPRA — hasta el carrito, ni un paso más
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_compra_llena_el_carrito_y_para_antes_de_pagar(monkeypatch, page_fake):
    """El caso central del encargo. Con un gate que aprueba TODO: si la frontera
    dependiera del gate, aquí se habría pagado."""
    page_fake.set_marks([_mark(0, "Buscar productos", tag="input"),
                         _mark(1, "Añadir al carrito"),
                         _mark(2, "Tramitar pedido")])
    _fake_mel(monkeypatch, [
        '{"action": "type", "index": 0, "text": "leche", "enter": true}',
        '{"action": "click", "index": 1, "why": "al carrito"}',
        '{"action": "click", "index": 2, "why": "terminar"}',
    ])
    gate = _GateApruebaTodo()
    r = await webloop.run("añade leche al carrito del super",
                          tool_manager=_ToolManagerFake(), approval_gate=gate)

    assert r.playbook == "compra"
    assert r.ok                                   # llegar a la frontera NO es fallar
    # El clic del carrito sí; el de tramitar el pedido NO (el de índice 0 es el
    # foco que `type_index` da al campo antes de teclear).
    assert page_fake.mouse.clicks == [(100, 200), (110, 200)]
    assert gate.abiertos == []                    # no se pregunta: no hay nada que conceder
    assert "Tramitar pedido" in r.answer
    assert "el pago lo haces tú" in r.answer.lower()
    assert "Añadir al carrito" in r.answer        # cuenta lo que SÍ hizo


@pytest.mark.anyio
async def test_compra_lleva_su_guia_en_el_prompt(monkeypatch, page_fake):
    page_fake.set_marks([_mark(0, "Buscar", tag="input")])
    prompts: list = []
    _fake_mel(monkeypatch, ['{"action": "done", "answer": "ok"}'], captura=prompts)
    await webloop.run("añádelo al carrito", tool_manager=_ToolManagerFake())
    assert "HASTA EL CARRITO" in prompts[0].system_prompt
    # y sin perder las reglas generales del bucle
    assert "Los índices son los de ESTA vuelta" in prompts[0].system_prompt


@pytest.mark.anyio
async def test_dentro_de_un_flujo_el_gate_generico_sigue_vivo(monkeypatch, page_fake):
    """Las dos capas conviven: la PARADA es solo para la frontera del flujo
    (pagar). Un elemento sensible que no es esa frontera —suscribirse a un
    boletín en mitad de una compra— sigue preguntando, como en C·WEB-3."""
    page_fake.set_marks([_mark(0, "Suscribirme al boletín")])
    _fake_mel(monkeypatch, [
        '{"action": "click", "index": 0}',
        '{"action": "done", "answer": "hecho"}',
    ])
    gate = _GateApruebaTodo()
    r = await webloop.run("añade pan al carrito", tool_manager=_ToolManagerFake(),
                          approval_gate=gate)
    assert r.playbook == "compra"
    assert len(gate.abiertos) == 1                # preguntó
    assert page_fake.mouse.clicks == [(100, 200)]  # y al conceder, pulsó


# ---------------------------------------------------------------------------
# 6 · CITA — hasta el resumen, sin confirmar
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_cita_rellena_el_formulario_y_para_antes_de_confirmar(monkeypatch, page_fake):
    page_fake.set_marks([_mark(0, "Nombre", tag="input"),
                         _mark(1, "Siguiente"),
                         _mark(2, "Confirmar cita")])
    _fake_mel(monkeypatch, [
        '{"action": "type", "index": 0, "text": "Alejandro"}',
        '{"action": "click", "index": 1}',
        '{"action": "click", "index": 2}',
    ])
    r = await webloop.run("pídeme cita previa en el dentista",
                          tool_manager=_ToolManagerFake(),
                          approval_gate=_GateApruebaTodo())
    assert r.playbook == "cita" and r.ok
    assert page_fake.keyboard.typed == ["Alejandro"]
    assert (100, 200) in page_fake.mouse.clicks    # foco del campo
    assert (120, 200) not in page_fake.mouse.clicks  # NO se confirmó
    assert any("no hay cita" in n.lower() for n in r.notes)


@pytest.mark.anyio
async def test_cita_no_inventa_un_dni(monkeypatch, page_fake):
    """La regla general de C·WEB-3 sigue mandando dentro de un flujo."""
    page_fake.set_marks([_mark(0, "DNI", tag="input")])
    _fake_mel(monkeypatch, ['{"action": "type", "index": 0, "text": "12345678Z"}'])
    r = await webloop.run("pide cita en Hacienda", tool_manager=_ToolManagerFake(),
                          max_steps=2)
    assert page_fake.keyboard.typed == []
    assert any("introduce el usuario" in l for l in r.limitations)


# ---------------------------------------------------------------------------
# 7 · DESCARGA — localiza el enlace, no instala
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_descarga_entrega_el_enlace_a_download_tool(monkeypatch, page_fake):
    page_fake.set_marks([_mark(0, "Blender 4.2")])
    _fake_mel(monkeypatch, [
        '{"action": "click", "index": 0}',
        '{"action": "done", "answer": "El enlace directo es '
        'https://blender.org/release/blender-4.2.zip (320 MB)"}',
    ])
    r = await webloop.run("descárgame Blender", tool_manager=_ToolManagerFake())

    assert r.playbook == "descarga" and r.ok
    assert r.handoff == {
        "tool": "download", "action": "download_url",
        "params": {"url": "https://blender.org/release/blender-4.2.zip"},
        "note": ("bájala con download.download_url; NUNCA la ejecutes ni la "
                 "instales tú"),
    }


@pytest.mark.anyio
async def test_descarga_no_pulsa_instalar(monkeypatch, page_fake):
    page_fake.set_marks([_mark(0, "Instalar ahora")])
    _fake_mel(monkeypatch, ['{"action": "click", "index": 0}'])
    r = await webloop.run("descarga el programa", tool_manager=_ToolManagerFake(),
                          approval_gate=_GateApruebaTodo())
    assert page_fake.mouse.clicks == []
    assert "Instalar ahora" in r.answer


@pytest.mark.anyio
async def test_descarga_de_fuente_dudosa_lo_dice(monkeypatch, page_fake):
    page_fake.set_marks([_mark(0, "Descargar")])
    _fake_mel(monkeypatch, [
        '{"action": "done", "answer": "Aquí lo tienes: '
        'https://gamesunlocked.example/repack/juego-setup.exe"}',
    ])
    r = await webloop.run("descarga el juego", tool_manager=_ToolManagerFake())
    assert r.notes and any("cuidado con esta fuente" in n.lower() for n in r.notes)
    assert any("EJECUTABLE" in n for n in r.notes)


# ---------------------------------------------------------------------------
# 8 · API KEY — enseña dónde, no la crea
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_api_key_no_inicia_sesion_por_ti(monkeypatch, page_fake):
    page_fake.set_marks([_mark(0, "Documentación"), _mark(1, "Iniciar sesión")])
    _fake_mel(monkeypatch, [
        '{"action": "click", "index": 0}',
        '{"action": "click", "index": 1}',
    ])
    r = await webloop.run("dónde saco la api key de Groq",
                          tool_manager=_ToolManagerFake(),
                          approval_gate=_GateApruebaTodo())
    assert r.playbook == "api_key" and r.ok
    assert page_fake.mouse.clicks == [(100, 200)]      # solo la documentación
    assert "Iniciar sesión" in r.answer
    assert "no manejo tus credenciales" in r.answer.lower()


@pytest.mark.anyio
async def test_api_key_nunca_repite_el_valor_de_una_clave(monkeypatch, page_fake):
    """El riesgo real: si el usuario ya tenía la sesión abierta, la clave estaba
    en pantalla y el modelo la repite sin malicia, quedaría escrita en la traza
    de la misión, en la telemetría y en la memoria."""
    page_fake.set_marks([_mark(0, "Ver")])
    _fake_mel(monkeypatch, [
        '{"action": "done", "answer": "Tu clave es sk-proj-AbC123dEf456GhI789jKl"}',
    ])
    r = await webloop.run("busca mi api key", tool_manager=_ToolManagerFake())
    assert "sk-proj-AbC123dEf456GhI789jKl" not in r.answer
    assert webflows.OCULTO in r.answer
    assert any("credencial" in n for n in r.notes)


# ---------------------------------------------------------------------------
# 9 · FORO — lee y sintetiza, sin dejar rastro
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_foro_busca_pero_no_escribe_en_ningun_otro_campo(monkeypatch, page_fake):
    page_fake.set_marks([_mark(0, "Buscar en el foro", tag="input"),
                         _mark(1, "Tu respuesta", tag="textarea")])
    _fake_mel(monkeypatch, [
        '{"action": "type", "index": 0, "text": "opiniones", "enter": true}',
        '{"action": "type", "index": 1, "text": "yo opino que..."}',
        '{"action": "done", "answer": "resumen del hilo"}',
    ])
    r = await webloop.run("busca en el foro qué opinan",
                          tool_manager=_ToolManagerFake())
    assert r.playbook == "foro"
    assert page_fake.keyboard.typed == ["opiniones"]     # solo la búsqueda
    assert any("solo de lectura" in l for l in r.limitations)


@pytest.mark.anyio
async def test_foro_no_publica_ni_vota(monkeypatch, page_fake):
    page_fake.set_marks([_mark(0, "Responder")])
    _fake_mel(monkeypatch, ['{"action": "click", "index": 0}'])
    r = await webloop.run("investiga el hilo del foro",
                          tool_manager=_ToolManagerFake(),
                          approval_gate=_GateApruebaTodo())
    assert page_fake.mouse.clicks == []
    assert "no publico nada" in r.answer.lower()


@pytest.mark.anyio
async def test_foro_avisa_de_lo_que_es_un_foro(monkeypatch, page_fake):
    page_fake.set_marks([_mark(0, "Hilo")])
    _fake_mel(monkeypatch, ['{"action": "done", "answer": "tres personas dicen X"}'])
    r = await webloop.run("mira en reddit qué dicen", tool_manager=_ToolManagerFake())
    assert any("no una fuente" in n for n in r.notes)


@pytest.mark.anyio
async def test_el_research_tiene_mas_vueltas_que_una_compra(monkeypatch, page_fake):
    """Entrar en hilos y paginar necesita más pasos que añadir algo al carrito.
    Lo declara el playbook; un `max_steps` explícito sigue mandando."""
    assert webflows.get("foro").suggested_steps > webloop.MAX_STEPS

    page_fake.set_marks([_mark(0, "A")])
    _fake_mel(monkeypatch, ['{"action": "click", "index": 99}'] * 50)
    r = await webloop.run("busca en el foro", tool_manager=_ToolManagerFake(),
                          max_steps=2)
    assert r.steps <= 2                                  # el explícito gana


# ---------------------------------------------------------------------------
# 10 · No-regresión: sin flujo, el bucle es exactamente el de C·WEB-3
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_sin_flujo_un_paso_sensible_sigue_abriendo_gate(monkeypatch, page_fake):
    """Lo importante de C·WEB-4 es no haber sustituido el gate por una parada en
    los casos que NO son uno de los cinco flujos: ahí «Enviar» debe seguir
    preguntando y, si se concede, ejecutarse."""
    page_fake.set_marks([_mark(0, "Enviar")])
    _fake_mel(monkeypatch, [
        '{"action": "click", "index": 0}',
        '{"action": "done", "answer": "enviado"}',
    ])
    gate = _GateApruebaTodo()
    r = await webloop.run("rellena el contacto y envíalo",
                          tool_manager=_ToolManagerFake(), approval_gate=gate)
    assert r.playbook is None
    assert len(gate.abiertos) == 1 and gate.abiertos[0]["kind"] == "web.sensitive_click"
    assert page_fake.mouse.clicks == [(100, 200)]        # concedido → se pulsa
    assert r.notes == []


# ---------------------------------------------------------------------------
# 11 · La tool `browse` expone el flujo, las notas y el siguiente paso
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_browse_pasa_el_flujo_y_devuelve_notas_y_siguiente_paso(monkeypatch, page_fake):
    page_fake.set_marks([_mark(0, "Descargar")])
    _fake_mel(monkeypatch, [
        '{"action": "done", "answer": "está en https://x.example/app.zip"}',
    ])
    from app.tools import browser_tool

    monkeypatch.setattr(browser_tool, "tool_manager", _ToolManagerFake(), raising=False)
    r = await BrowserTool().execute("browse", {"goal": "descarga la app"})
    assert r["success"], r
    assert r["result"]["playbook"] == "descarga"
    assert r["result"]["next_step"]["tool"] == "download"


def test_browse_documenta_los_cinco_flujos():
    acciones = {a["id"]: a for a in BrowserTool().list_actions()}
    desc = acciones["browse"]["description"]
    for nombre in ("compra", "cita", "descarga", "api_key", "foro"):
        assert nombre in desc, nombre
    assert "playbook" in acciones["browse"]["params"]
