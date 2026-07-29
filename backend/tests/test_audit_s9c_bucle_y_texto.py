# tests/test_audit_s9c_bucle_y_texto.py — S9c (doc 34): dos secuelas de la
# verificación en vivo del 2026-07-28, ninguna del navegador en sí.
#
# (1) REPETICIÓN ESTÉRIL. Con el navegador roto, el bucle gastó sus 12 vueltas
#     pidiendo `browser.open_url` una y otra vez y recibiendo EXACTAMENTE el
#     mismo `TargetClosedError` — 12 llamadas al LLM y un minuto largo para una
#     conclusión que ya estaba clara en la segunda.
#
# (2) TEXTO EXTERNO SUCIO. La misma misión degradó bien a `search.search_videos`
#     y trajo resultados REALES, pero los enlaces salieron rotos:
#         [https://…iy35dCK0iaI](https://…iy35dCK0iaI￼Ritmos)
#     Ese `￼` es invisible: ni en el JSON ni en el log se ve, y el modelo lo
#     pega dentro del enlace. El usuario recibe una URL que no lleva a ninguna
#     parte.
from __future__ import annotations

import json

import pytest

from app.core.sanitize import clean_external, clean_url, strip_invisible
from app.tie import toolloop


# ===========================================================================
# (1) El bucle deja de insistir en lo que ya falló igual
# ===========================================================================
class _FakeToolManager:
    """ToolManager mínimo: una sola tool, que SIEMPRE falla igual (el caso
    real: el navegador muerto devolvía el mismo error en cada vuelta)."""

    def __init__(self, error: str = "TargetClosedError: browser has been closed"):
        self.error = error
        self.llamadas = 0

    def tie_catalog(self):
        return [{
            "tool_id": "browser",
            "requires_confirmation": False,
            "actions": [{"id": "open_url", "description": "Abre una URL",
                         "requires_confirmation": False, "params": {}}],
        }]

    def get_tool(self, tool_id):
        # `_denial_reason` lo consulta para explicar POR QUÉ se deniega. El
        # ToolManager real siempre lo tiene; un doble incompleto rompería por
        # su cuenta y no por la lógica bajo prueba (patrón LOG-1).
        return None

    async def execute(self, *, tool_id, action, params, allowed_tools, timeout):
        self.llamadas += 1
        return {"success": False, "error": self.error}


def _modelo_terco(monkeypatch, pedido: dict):
    """Un modelo que SIEMPRE pide lo mismo, pase lo que pase — exactamente el
    comportamiento observado en vivo."""
    llamadas = {"n": 0}

    async def _complete(req):
        llamadas["n"] += 1

        class _Res:
            text = json.dumps(pedido)
            ok = True
            served_by = None
        return _Res()

    import app.mel as _mel
    monkeypatch.setattr(_mel, "complete", _complete)
    return llamadas


@pytest.mark.anyio
async def test_el_mismo_fallo_repetido_no_agota_las_iteraciones(monkeypatch):
    """LA REGRESIÓN: 12 vueltas permitidas, pero el mismo error tres veces
    seguidas debe cortar mucho antes."""
    tm = _FakeToolManager()
    llamadas = _modelo_terco(monkeypatch, {
        "tool": {"tool_id": "browser", "action": "open_url",
                 "params": {"url": "https://wikipedia.org"}}})

    res = await toolloop.run(
        instruction="abre wikipedia", context="", allowed_tools=["browser"],
        tool_manager=tm, max_iters=12,
    )

    assert res.ok is False
    assert tm.llamadas == toolloop._MAX_REPEATED_FAILURES, \
        f"debía abandonar tras {toolloop._MAX_REPEATED_FAILURES} fallos idénticos, hizo {tm.llamadas}"
    assert res.iterations < 12, "no puede haber gastado las 12 vueltas"
    assert "falló" in (res.error or "").lower()
    assert "targetclosederror" in (res.error or "").lower(), \
        "el error real debe llegar al usuario, no un genérico"


@pytest.mark.anyio
async def test_un_fallo_transitorio_no_corta_el_bucle(monkeypatch):
    """No-regresión IMPORTANTE: reintentar UNA vez tras un fallo puntual es
    legítimo (una red que va y viene, un elemento que aún no cargó). Solo se
    abandona a la TERCERA repetición idéntica."""
    class _TMIntermitente(_FakeToolManager):
        async def execute(self, **kw):
            self.llamadas += 1
            if self.llamadas == 1:
                return {"success": False, "error": "timeout puntual"}
            return {"success": True, "result": {"text": "contenido real"}}

    tm = _TMIntermitente()
    respuestas = [
        {"tool": {"tool_id": "browser", "action": "open_url", "params": {"url": "u"}}},
        {"tool": {"tool_id": "browser", "action": "open_url", "params": {"url": "u"}}},
        {"answer": "He abierto la página y dice: contenido real"},
    ]
    idx = {"i": 0}

    async def _complete(req):
        i = min(idx["i"], len(respuestas) - 1)
        idx["i"] += 1

        class _Res:
            text = json.dumps(respuestas[i])
            ok = True
            served_by = None
        return _Res()

    import app.mel as _mel
    monkeypatch.setattr(_mel, "complete", _complete)

    res = await toolloop.run(
        instruction="abre la página", context="", allowed_tools=["browser"],
        tool_manager=tm, max_iters=12,
    )
    assert res.ok is True, "un reintento que acaba funcionando no debe cortarse"
    assert tm.llamadas == 2


@pytest.mark.anyio
async def test_pedir_la_misma_tool_inexistente_tampoco_quema_las_vueltas(monkeypatch):
    """La otra forma de girar en vacío: insistir en una tool que no existe o no
    está permitida. Mismo contador, mismo abandono."""
    tm = _FakeToolManager()
    _modelo_terco(monkeypatch, {
        "tool": {"tool_id": "inventada", "action": "hacer_magia", "params": {}}})

    res = await toolloop.run(
        instruction="haz magia", context="", allowed_tools=["browser"],
        tool_manager=tm, max_iters=12,
    )
    assert res.ok is False
    assert res.iterations <= toolloop._MAX_REPEATED_FAILURES
    assert tm.llamadas == 0, "una tool inexistente nunca llega a ejecutarse"


# ===========================================================================
# (2) El texto que viene de fuera entra limpio
# ===========================================================================
def test_quita_el_caracter_invisible_del_fallo_real():
    sucio = "https://www.youtube.com/watch?v=iy35dCK0iaI￼Ritmos soleados"
    assert "￼" in sucio
    assert "￼" not in strip_invisible(sucio)


@pytest.mark.parametrize("ch", ["￼", "�", "­", "​", "‌",
                                "⁠", "﻿", "\x00", "\x1f"])
def test_quita_los_invisibles_conocidos(ch):
    assert strip_invisible(f"antes{ch}despues") == "antesdespues"


@pytest.mark.parametrize("texto", [
    "Ritmos soleados de Sídney — con olas 🌊 y ambiente playero",
    "línea uno\nlínea dos\tcon tabulador",
    "日本語のテキスト",
    "acentuación, ñ, ü, çedilla",
])
def test_no_toca_el_texto_legitimo(texto):
    """El riesgo del saneo es pasarse: acentos, emojis, CJK y saltos de línea
    tienen que salir intactos."""
    assert strip_invisible(texto) == texto


def test_clean_url_corta_la_descripcion_pegada():
    """EL FALLO EXACTO: la descripción pegada a la URL acababa DENTRO del
    enlace markdown que escribe el modelo."""
    assert clean_url("https://youtu.be/abc￼Ritmos soleados") == "https://youtu.be/abc"
    assert clean_url("  https://ok.com/x  ") == "https://ok.com/x"


def test_clean_external_limpia_el_resultado_de_una_busqueda():
    """Lo que devuelve de verdad el search tool: lista de {title, url,
    description}. Una llamada y todo el árbol queda limpio."""
    crudo = [{
        "title": "Sydney, Australia - lofi hip hop￼",
        "url": "https://www.youtube.com/watch?v=iy35dCK0iaI￼Ritmos",
        "description": "Ritmos​ soleados de Sídney",
    }]
    limpio = clean_external(crudo)
    assert limpio[0]["url"] == "https://www.youtube.com/watch?v=iy35dCK0iaI"
    assert "￼" not in limpio[0]["title"]
    assert limpio[0]["description"] == "Ritmos soleados de Sídney"


@pytest.mark.anyio
async def test_el_search_tool_entrega_los_resultados_ya_limpios(monkeypatch):
    """La lógica de saneo puede ser correcta y estar DESCONECTADA. Este test
    ejercita `_search_brave` REAL contra una respuesta HTTP sucia (la forma
    exacta que devuelve Brave) y comprueba lo que sale por la frontera de la
    tool — no la función pura por su cuenta."""
    from app.tools import search_tool

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [{
                "title": "Sydney, Australia - lofi hip hop￼",
                "url": "https://www.youtube.com/watch?v=iy35dCK0iaI￼Ritmos",
                "description": "Ritmos​ soleados",
            }]}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **kw):
            return _Resp()

    monkeypatch.setattr(search_tool.httpx, "AsyncClient", lambda *a, **kw: _Client())

    out = await search_tool._search_brave("videos", "lofi australia", 5, "fake-key")

    assert out[0]["url"] == "https://www.youtube.com/watch?v=iy35dCK0iaI", \
        "la URL debe salir de la tool ya cortada, no depender de quien la use"
    assert "￼" not in out[0]["title"]
    assert out[0]["description"] == "Ritmos soleados"


def test_clean_external_respeta_tipos_no_texto():
    """No puede convertir números, booleanos ni None por el camino."""
    dato = {"n": 3, "ok": True, "nada": None, "lista": [1, "a￼b"], "url": "http://x.com"}
    out = clean_external(dato)
    assert out["n"] == 3 and out["ok"] is True and out["nada"] is None
    assert out["lista"] == [1, "ab"]
    assert out["url"] == "http://x.com"
