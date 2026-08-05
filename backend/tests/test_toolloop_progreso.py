# tests/test_toolloop_progreso.py — [Sesión A, 2026-08-04] EL PRESUPUESTO DEL
# BUCLE PASA DE FIJO A BASADO EN PROGRESO.
#
# El fallo real que cierra (caso Cordyceps, 2026-08-03): "lee el GDD, investiga
# en la web y escribe el plan" necesitaba ~30 pasos LEGÍTIMOS y el muro fijo de
# 12 vueltas (TIE_TOOL_MAX_ITERS_WRITE) la cortaba a medias — mientras que una
# misión ATASCADA (search sin API key fallando idéntico) quemaba esas mismas 12
# vueltas sin producir nada. El número fijo castigaba el trabajo y toleraba el
# atasco: exactamente al revés de lo que debe.
#
# El contrato nuevo (criterio Claude Code — "¿sigo progresando?", no "¿cuántos
# pasos llevo?"):
#   1. Techo DURO alto (TIE_TOOL_HARD_CEILING=60): solo corta bucles desbocados.
#   2. Corte EFECTIVO por atasco (TIE_TOOL_STALL_LIMIT=4): N vueltas consecutivas
#      sin una sola tool ejecutada con éxito → se corta con la causa real.
#   3. Si hubo trabajo real previo, UNA última vuelta para cerrar con honestidad
#      (contar lo conseguido y lo que no) antes de rendirse.
#   4. PREFLIGHT: una tool inoperativa por configuración (search sin API key) se
#      detecta ANTES del bucle — fallo honesto en el segundo 1, 0 llamadas LLM.
#
# Se mockea SOLO la frontera del LLM (patrón test_tie_toolloop) + un ToolManager
# fake mínimo donde hace falta guionizar éxitos/fallos.
from __future__ import annotations

import json

import pytest

from app.core.config import settings
from app.tie import toolloop


# ---------------------------------------------------------------------------
# Dobles mínimos
# ---------------------------------------------------------------------------
def _fake_mel(monkeypatch, responses: list[str]):
    """Encola respuestas del modelo; cada llamada consume una. Devuelve la lista
    de prompts vistos (para asertar QUÉ leyó el modelo y CUÁNTAS llamadas hubo)."""
    import app.mel as mel
    from app.mel import ExecutionResult, ServedBy, Usage

    seen: list[str] = []
    queue = list(responses)

    async def _complete(req):
        seen.append(req.prompt)
        text = queue.pop(0) if queue else '{"answer": "sin más que decir"}'
        return ExecutionResult(text=text, ok=True,
                               served_by=ServedBy("fake", "fake-model"), usage=Usage(tokens=1))

    monkeypatch.setattr(mel, "complete", _complete)
    return seen


class _FakeTool:
    """Una tool registrada, opcionalmente con preflight."""
    def __init__(self, preflight_result=None, preflight_raises=False):
        self._pf = preflight_result
        self._raises = preflight_raises
        if preflight_result is None and not preflight_raises:
            # sin el atributo siquiera — el caso "tool normal sin preflight"
            return
        def preflight():
            if self._raises:
                raise RuntimeError("chequeo roto")
            return self._pf
        self.preflight = preflight


class _FakeTM:
    """ToolManager guionizable: `outcomes` es la cola de resultados de execute()
    (dicts con success/error). El contrato es el mismo que usa el bucle real."""
    def __init__(self, tools: dict[str, _FakeTool], outcomes: list[dict] | None = None):
        self._tools = tools
        self.outcomes = list(outcomes or [])
        self.executed: list[tuple] = []

    def tie_catalog(self, include_internal: bool = True):
        return [
            {"tool_id": tid, "actions": [
                {"id": "run", "description": "acción de prueba",
                 "params": {"x": "string"}, "requires_confirmation": False},
            ]}
            for tid in self._tools
        ]

    def get_tool(self, tool_id):
        return self._tools.get(tool_id)

    async def execute(self, tool_id, action, params, allowed_tools=None, timeout=None):
        self.executed.append((tool_id, action))
        if self.outcomes:
            return self.outcomes.pop(0)
        return {"success": True, "result": {"ok": 1}, "error": None}


def _tool_json(tid="t1", x="a"):
    return json.dumps({"tool": {"tool_id": tid, "action": "run", "params": {"x": x}}})


# ---------------------------------------------------------------------------
# 1 — El muro viejo ya no existe: el trabajo legítimo pasa de 12 vueltas
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_una_tarea_grande_con_progreso_pasa_del_muro_viejo(monkeypatch):
    """15 tools ejecutadas con éxito + la respuesta = 16 iteraciones. Con el
    muro viejo (12) esto moría a medias; ahora termina bien. ES el caso
    Cordyceps en miniatura."""
    n = 15
    seen = _fake_mel(monkeypatch, [_tool_json(x=str(i)) for i in range(n)]
                     + ['{"answer": "trabajo completo con datos reales"}'])
    tm = _FakeTM({"t1": _FakeTool()})

    res = await toolloop.run(
        instruction="tarea grande", context="", allowed_tools=["t1"],
        tool_manager=tm, max_iters=settings.TIE_TOOL_HARD_CEILING,
    )

    assert res.ok, res.error
    assert res.iterations == n + 1 > 12          # superó el muro viejo
    assert len(tm.executed) == n                 # todas se ejecutaron de verdad
    assert len(seen) == n + 1


# ---------------------------------------------------------------------------
# 2 — El atasco corta MUCHO antes que el techo
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_atasco_sin_fundamento_corta_al_limite_no_al_techo(monkeypatch):
    """Un modelo que nunca produce JSON válido: antes quemaba max_iters llamadas
    LLM; ahora se corta a las TIE_TOOL_STALL_LIMIT vueltas estériles con la
    causa real en el error."""
    monkeypatch.setattr(settings, "TIE_TOOL_STALL_LIMIT", 4)
    seen = _fake_mel(monkeypatch, ["esto no es json"] * 40)
    tm = _FakeTM({"t1": _FakeTool()})

    res = await toolloop.run(
        instruction="haz algo", context="", allowed_tools=["t1"],
        tool_manager=tm, max_iters=40,
    )

    assert not res.ok
    assert "falta de progreso" in (res.error or "")
    assert len(seen) == 4                        # ni una llamada LLM más
    assert res.iterations == 4
    assert not tm.executed                       # nada llegó a ejecutarse


@pytest.mark.anyio
async def test_fallos_distintos_consecutivos_tambien_cortan(monkeypatch):
    """S9c corta el fallo IDÉNTICO repetido; este detector corta el atasco
    GENERAL — fallos distintos cada vez (que S9c no agrupa) también son vueltas
    estériles y también se cortan."""
    monkeypatch.setattr(settings, "TIE_TOOL_STALL_LIMIT", 4)
    _fake_mel(monkeypatch, [_tool_json(x=str(i)) for i in range(40)])
    # 4 fallos con errores DISTINTOS (firmas S9c distintas → S9c no corta)
    tm = _FakeTM({"t1": _FakeTool()}, outcomes=[
        {"success": False, "result": None, "error": f"error distinto {i}"} for i in range(40)
    ])

    res = await toolloop.run(
        instruction="haz algo", context="", allowed_tools=["t1"],
        tool_manager=tm, max_iters=40,
    )

    assert not res.ok
    assert "falta de progreso" in (res.error or "")
    assert res.iterations == 4


# ---------------------------------------------------------------------------
# 3 — Con trabajo real previo: UNA última vuelta para cerrar con honestidad
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_atasco_con_trabajo_previo_pide_cierre_honesto(monkeypatch):
    """1 éxito + 4 fallos distintos → atasco. Pero como HUBO trabajo real, el
    bucle no tira lo conseguido: pide al modelo cerrar contando lo que sí hay,
    y ese answer (fundamentado en el éxito real) se acepta."""
    monkeypatch.setattr(settings, "TIE_TOOL_STALL_LIMIT", 4)
    seen = _fake_mel(monkeypatch, [_tool_json(x=str(i)) for i in range(5)]
                     + ['{"answer": "conseguí la parte A; la parte B no se pudo por los fallos"}'])
    tm = _FakeTM({"t1": _FakeTool()}, outcomes=[
        {"success": True, "result": {"dato": "real"}, "error": None},
        {"success": False, "result": None, "error": "fallo uno"},
        {"success": False, "result": None, "error": "fallo dos"},
        {"success": False, "result": None, "error": "fallo tres"},
        {"success": False, "result": None, "error": "fallo cuatro"},
    ])

    res = await toolloop.run(
        instruction="haz algo", context="", allowed_tools=["t1"],
        tool_manager=tm, max_iters=40,
    )

    assert res.ok, res.error                     # entrega honesta, no fallo mudo
    assert "parte A" in res.answer
    assert "ATASCO CONFIRMADO" in seen[-1]       # el cierre se pidió de verdad


@pytest.mark.anyio
async def test_el_exito_resetea_el_contador_de_atasco(monkeypatch):
    """Fallos intercalados con éxitos NUNCA disparan el atasco: la racha se
    resetea con cada tool que funciona. 8 pares fallo+éxito = 16 vueltas + la
    respuesta, y el bucle sigue vivo hasta el final."""
    monkeypatch.setattr(settings, "TIE_TOOL_STALL_LIMIT", 4)
    pares = 8
    _fake_mel(monkeypatch, [_tool_json(x=str(i)) for i in range(pares * 2)]
              + ['{"answer": "terminado"}'])
    outcomes = []
    for i in range(pares):
        outcomes.append({"success": False, "result": None, "error": f"fallo {i}"})
        outcomes.append({"success": True, "result": {"i": i}, "error": None})
    tm = _FakeTM({"t1": _FakeTool()}, outcomes=outcomes)

    res = await toolloop.run(
        instruction="haz algo", context="", allowed_tools=["t1"],
        tool_manager=tm, max_iters=40,
    )

    assert res.ok, res.error
    assert res.iterations == pares * 2 + 1


# ---------------------------------------------------------------------------
# 4 — PREFLIGHT: la tool inoperativa se detecta ANTES de quemar nada
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_preflight_unica_tool_inoperativa_falla_en_el_acto(monkeypatch):
    """El caso real: search sin API key como única tool del paso. Antes: 12
    llamadas LLM para descubrirlo. Ahora: fallo honesto con el motivo, CERO
    llamadas LLM."""
    seen = _fake_mel(monkeypatch, ["no debería llamarse"])
    tm = _FakeTM({"search": _FakeTool(preflight_result="sin API key configurada")})

    res = await toolloop.run(
        instruction="busca en la web", context="", allowed_tools=["search"],
        tool_manager=tm, max_iters=40,
    )

    assert not res.ok
    assert "no están operativas" in (res.error or "")
    assert "sin API key" in (res.error or "")
    assert len(seen) == 0                        # NI UNA llamada al LLM
    assert "search" in res.limitations


@pytest.mark.anyio
async def test_preflight_con_otra_tool_sana_el_bucle_sigue_avisado(monkeypatch):
    """Una tool inoperativa + una sana: el bucle arranca con la sana, el modelo
    ve el AVISO PREVIO en cabecera (para no intentar rutas imposibles) y la
    limitación queda declarada para el responder."""
    seen = _fake_mel(monkeypatch, [_tool_json(tid="fs"), '{"answer": "hecho con fs"}'])
    tm = _FakeTM({
        "search": _FakeTool(preflight_result="sin API key configurada"),
        "fs": _FakeTool(),
    })

    res = await toolloop.run(
        instruction="haz algo", context="", allowed_tools=["search", "fs"],
        tool_manager=tm, max_iters=10,
    )

    assert res.ok, res.error
    assert "AVISO PREVIO" in seen[0]             # el modelo lo supo desde la vuelta 1
    assert "search" in seen[0] and "sin API key" in seen[0]
    assert "search" in res.limitations           # y el responder podrá avisar
    assert 'tool_id="search"' not in seen[0]     # excluida del catálogo ofrecido


@pytest.mark.anyio
async def test_preflight_roto_jamas_bloquea(monkeypatch):
    """Un preflight que LANZA se ignora: la tool sigue disponible. Un chequeo
    roto no puede quitar capacidades."""
    _fake_mel(monkeypatch, [_tool_json(tid="t1"), '{"answer": "ok"}'])
    tm = _FakeTM({"t1": _FakeTool(preflight_raises=True)})

    res = await toolloop.run(
        instruction="haz algo", context="", allowed_tools=["t1"],
        tool_manager=tm, max_iters=10,
    )

    assert res.ok, res.error
    assert tm.executed                           # se ejecutó con normalidad


# ---------------------------------------------------------------------------
# 5 — El preflight REAL de SearchTool (sin BD: se mockea la consulta de keys)
# ---------------------------------------------------------------------------
def test_search_preflight_sin_keys_avisa_con_keys_calla(monkeypatch):
    import app.tools.search_tool as st

    tool = st.SearchTool()

    monkeypatch.setattr(st, "_configured_providers",
                        lambda: {"brave": None, "serpapi": None})
    motivo = tool.preflight()
    assert motivo and "API key" in motivo and "Ajustes" in motivo

    monkeypatch.setattr(st, "_configured_providers",
                        lambda: {"brave": None, "serpapi": "sk-real"})
    assert tool.preflight() is None

    # Y si la consulta revienta (BD no disponible), None: jamás bloquear.
    def _boom():
        raise RuntimeError("sin BD")
    monkeypatch.setattr(st, "_configured_providers", _boom)
    assert tool.preflight() is None
