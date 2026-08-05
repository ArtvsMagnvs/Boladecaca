# tests/test_entregables_honestos.py — [Sesión B, doc 40 §B] SI DIGO QUE HE
# ESCRITO UN ARCHIVO, EL ARCHIVO EXISTE.
#
# EL FALLO REAL QUE CIERRA (2026-08-04, reportado por el usuario): la respuesta
# final de una misión dijo «He escrito CORDYCEPS_PLAN_2026.md con el plan
# completo» y el archivo NO EXISTÍA. Ninguna capa anterior lo cazaba:
#   · S2·S6 (`_is_grounded`) solo comprueba que no se invente una espera de
#     aprobación.
#   · NEW-7 (`presents_unverifiable_evidence`) mira EVIDENCIA presentada
#     (listados, código, recuentos) — «he escrito X.md» no presenta ninguna.
#   · El grounding del camino corto no aplica: esta misión SÍ ejecutó
#     herramientas, solo que ninguna escribió ESE archivo.
#
# La cadena que se prueba aquí: el toolloop anota la ruta de cada escritura
# EXITOSA (§B1) → `grounding.claimed_written_files` detecta qué archivos AFIRMA
# la respuesta (§B2) → el responder cruza ambos y, si no cuadran, descarta la
# síntesis del LLM y sale la plantilla determinista (§B3).
#
# Un solo fake: la frontera del LLM. ToolManager, responder y grounding reales.
from __future__ import annotations

import json

import pytest

from app.core import grounding
from app.tie import responder, toolloop
from app.tie.contracts import Mission, NodeState, TaskGraph, TaskNode


# ===========================================================================
# 1 — El detector (función pura): positivos y, sobre todo, NEGATIVOS
# ===========================================================================
# El riesgo de esta sesión es pasarse: descartar una síntesis perfectamente
# válida porque el texto mencionó un archivo por otro motivo.

@pytest.mark.parametrize("texto,esperado", [
    # EL caso real del fallo
    ("He escrito CORDYCEPS_PLAN_2026.md con el plan completo.",
     ["cordyceps_plan_2026.md"]),
    ("He creado el archivo notas.txt en tu carpeta.", ["notas.txt"]),
    ("Ya queda guardado en informe.docx", ["informe.docx"]),
    ("Lo he guardado en C:/Proyectos/Cordyceps/plan.md", ["plan.md"]),
    ("He generado datos.xlsx con las tres hojas.", ["datos.xlsx"]),
    ("I created the file report.md with the summary.", ["report.md"]),
    ("Saved to resumen.txt", ["resumen.txt"]),
])
def test_detecta_entregables_afirmados(texto, esperado):
    assert grounding.claimed_written_files(texto) == esperado


@pytest.mark.parametrize("texto", [
    # FUTURO: anuncia, no afirma. Que lo cumpla o no es otro problema (S2·S6).
    "Voy a crear plan.md con todo lo que hemos hablado.",
    "Ahora escribiré el resumen en notas.md.",
    # PREGUNTA: ni afirma ni promete.
    "¿Quieres que lo guarde en notas.md o prefieres otro nombre?",
    # LECTURA: leer un archivo no lo crea.
    "He leído el GDD.docx y trata de un juego de terror.",
    "El archivo config.json contiene tres claves.",
    # MENCIÓN SUELTA sin verbo de creación.
    "El plan está estructurado en cinco fases.",
    "Tu proyecto usa main.py como punto de entrada.",
    # Sin ningún archivo: el caso mayoritario.
    "He creado el proyecto y le he añadido dos agentes.",
])
def test_no_marca_lo_que_no_es_una_afirmacion_de_entregable(texto):
    assert grounding.claimed_written_files(texto) == []


def test_el_codigo_de_ejemplo_no_cuenta_como_entregable():
    """Un bloque de código que ABRE un archivo es un ejemplo pedido por el
    usuario, no una afirmación de haberlo escrito."""
    texto = (
        "Aquí tienes el script que te sirve:\n"
        "```python\n"
        'with open("salida.md", "w") as f:\n'
        '    f.write("hola")  # he guardado salida.md\n'
        "```\n"
        "Ejecútalo cuando quieras."
    )
    assert grounding.claimed_written_files(texto) == []


def test_varios_entregables_sin_duplicados():
    texto = ("He creado plan.md y he guardado datos.csv. "
             "El plan.md incluye el cronograma.")
    assert grounding.claimed_written_files(texto) == ["plan.md", "datos.csv"]


# ===========================================================================
# 2 — El toolloop registra la ruta SOLO de escrituras exitosas
# ===========================================================================
def _fake_mel(monkeypatch, responses: list[str]):
    import app.mel as mel
    from app.mel import ExecutionResult, ServedBy, Usage

    queue = list(responses)

    async def _complete(req):
        text = queue.pop(0) if queue else '{"answer": "listo"}'
        return ExecutionResult(text=text, ok=True,
                               served_by=ServedBy("fake", "fake-model"), usage=Usage(tokens=1))

    monkeypatch.setattr(mel, "complete", _complete)


class _TM:
    """ToolManager mínimo: `outcomes` guioniza éxito/fallo de cada execute()."""
    def __init__(self, outcomes=None):
        self.outcomes = list(outcomes or [])

    def tie_catalog(self, include_internal: bool = True):
        return [
            {"tool_id": "filesystem", "actions": [
                {"id": "write_file", "description": "escribe", "params": {"path": "string"},
                 "requires_confirmation": False},
                {"id": "read_file", "description": "lee", "params": {"path": "string"},
                 "requires_confirmation": False},
            ]},
        ]

    def get_tool(self, tool_id):
        return object() if tool_id == "filesystem" else None

    async def execute(self, tool_id, action, params, allowed_tools=None, timeout=None):
        if self.outcomes:
            return self.outcomes.pop(0)
        return {"success": True, "result": {"written": True}, "error": None}


@pytest.mark.anyio
async def test_toolloop_anota_la_ruta_de_una_escritura_exitosa(monkeypatch):
    _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "filesystem", "action": "write_file",
                             "params": {"path": "C:/proyectos/x/PLAN.md", "content": "hola"}}}),
        '{"answer": "He escrito PLAN.md"}',
    ])
    res = await toolloop.run(instruction="escribe el plan", context="",
                             allowed_tools=["filesystem"], tool_manager=_TM(), max_iters=5)

    assert res.ok, res.error
    escritura = [c for c in res.tool_calls if c.get("action") == "write_file"][0]
    assert escritura["target"] == "C:/proyectos/x/PLAN.md"


@pytest.mark.anyio
async def test_una_lectura_no_anota_target_y_una_escritura_fallida_tampoco(monkeypatch):
    """Leer no crea nada; y una escritura que FALLÓ no debe dejar rastro de
    entregable — sería justo lo contrario de una prueba."""
    _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "filesystem", "action": "read_file",
                             "params": {"path": "C:/x/GDD.docx"}}}),
        json.dumps({"tool": {"tool_id": "filesystem", "action": "write_file",
                             "params": {"path": "C:/x/PLAN.md"}}}),
        '{"answer": "hecho"}',
    ])
    tm = _TM(outcomes=[
        {"success": True, "result": {"text": "contenido"}, "error": None},
        {"success": False, "result": None, "error": "disco lleno"},
    ])
    res = await toolloop.run(instruction="lee y escribe", context="",
                             allowed_tools=["filesystem"], tool_manager=tm, max_iters=5)

    assert all("target" not in c for c in res.tool_calls), res.tool_calls


# ===========================================================================
# 3 — El responder: la cadena completa
# ===========================================================================
def _graph(nodes):
    return TaskGraph(id="g1", mission_id="m1", nodes={n.id: n for n in nodes})


def _fake_llm(monkeypatch, texto):
    async def _complete(prompt, system_prompt=None, capability=None, **kw):
        return {"response": texto, "error": None}
    monkeypatch.setattr(responder.router, "complete", _complete)


@pytest.mark.anyio
async def test_afirmar_un_archivo_que_nadie_escribio_se_descarta(monkeypatch):
    """LA REGRESIÓN DEL FALLO. El nodo se completó (así que `_is_grounded` no
    ve nada raro) pero NINGUNA tool escribió el archivo: la síntesis del LLM
    se descarta y sale la plantilla, que solo cuenta lo que de verdad pasó."""
    _fake_llm(monkeypatch, "He escrito CORDYCEPS_PLAN_2026.md con el plan completo.")

    mission = Mission(id="m1", goal="escribe el plan de Cordyceps")
    nodo = TaskNode(id="n1", goal="preparar el plan", state=NodeState.DONE,
                    result={"output": "esquema del plan en 5 fases"},
                    tool_calls=[{"tool_id": "filesystem", "action": "read_file", "ok": True}])
    text = await responder.build(mission, _graph([nodo]))

    assert "CORDYCEPS_PLAN_2026.md" not in text
    assert "esquema del plan en 5 fases" in text      # la plantilla, con el hecho real


@pytest.mark.anyio
async def test_con_la_escritura_real_detras_el_texto_se_respeta(monkeypatch, tmp_path):
    """El contrario, igual de importante: si el archivo SÍ se escribió y sigue
    en disco, la síntesis del modelo pasa tal cual. Arreglar un caso no puede
    romper el otro."""
    destino = tmp_path / "PLAN.md"
    destino.write_text("el plan", encoding="utf-8")
    _fake_llm(monkeypatch, "He escrito PLAN.md con el plan completo.")

    mission = Mission(id="m1", goal="escribe el plan")
    nodo = TaskNode(id="n1", goal="escribir", state=NodeState.DONE,
                    result={"output": "escrito"},
                    tool_calls=[{"tool_id": "filesystem", "action": "write_file",
                                 "ok": True, "target": str(destino)}])
    text = await responder.build(mission, _graph([nodo]))

    assert text == "He escrito PLAN.md con el plan completo."


@pytest.mark.anyio
async def test_escrito_pero_ya_no_esta_en_disco_se_descarta(monkeypatch, tmp_path):
    """Contrato de producto nº 5: «si te pido un archivo, el archivo existe».
    Que se escribiera en su momento no basta si ya no está."""
    destino = tmp_path / "PLAN.md"      # NO se crea
    _fake_llm(monkeypatch, "He escrito PLAN.md con el plan completo.")

    mission = Mission(id="m1", goal="escribe el plan")
    nodo = TaskNode(id="n1", goal="escribir", state=NodeState.DONE,
                    result={"output": "escrito"},
                    tool_calls=[{"tool_id": "filesystem", "action": "write_file",
                                 "ok": True, "target": str(destino)}])
    text = await responder.build(mission, _graph([nodo]))

    assert "PLAN.md con el plan completo" not in text


@pytest.mark.anyio
async def test_ruta_relativa_no_se_verifica_en_disco(monkeypatch):
    """Una ruta relativa depende del cwd del proceso: comprobarla daría falsos
    positivos. Se acepta con el registro de escritura como única prueba."""
    _fake_llm(monkeypatch, "He guardado notas.md con el resumen.")

    mission = Mission(id="m1", goal="guarda notas")
    nodo = TaskNode(id="n1", goal="guardar", state=NodeState.DONE,
                    result={"output": "ok"},
                    tool_calls=[{"tool_id": "filesystem", "action": "write_file",
                                 "ok": True, "target": "salida/notas.md"}])
    text = await responder.build(mission, _graph([nodo]))

    assert text == "He guardado notas.md con el resumen."


@pytest.mark.anyio
async def test_no_regresion_sintesis_sin_archivos_pasa_identica(monkeypatch):
    """El caso mayoritario: una respuesta que no menciona ningún entregable no
    paga nada y sale byte a byte igual."""
    original = "He revisado tu bandeja y hay tres correos urgentes."
    _fake_llm(monkeypatch, original)

    mission = Mission(id="m1", goal="revisa el correo")
    nodo = TaskNode(id="n1", goal="revisar", state=NodeState.DONE,
                    result={"output": "3 urgentes"})
    assert await responder.build(mission, _graph([nodo])) == original


# ===========================================================================
# 4 — El motivo REAL del fallo llega a la respuesta final (§B4)
# ===========================================================================
# Los mensajes de la Sesión A están escritos para leerse tal cual. Aquí se
# fija que el responder no los sustituye por un genérico.

@pytest.mark.anyio
async def test_el_motivo_de_la_sesion_a_llega_entero_al_usuario(monkeypatch):
    """Sin ningún nodo DONE, `build` va a `_template_failure` — que debe
    incluir el error REAL del nodo, no un 'algo falló'."""
    _fake_llm(monkeypatch, "no debería usarse")

    mission = Mission(id="m1", goal="busca en la web y resume")
    nodo = TaskNode(
        id="n1", goal="buscar", state=NodeState.FAILED,
        error=("las herramientas de este paso no están operativas: search: la búsqueda "
               "web no está configurada: añade una API key de SerpAPI o Brave en "
               "Ajustes → Búsqueda web"),
    )
    text = await responder.build(mission, _graph([nodo]))

    assert "no está configurada" in text
    assert "Ajustes" in text


@pytest.mark.anyio
async def test_el_atasco_tambien_se_cuenta_con_su_causa(monkeypatch):
    _fake_llm(monkeypatch, "no debería usarse")

    mission = Mission(id="m1", goal="haz algo")
    nodo = TaskNode(id="n1", goal="intentarlo", state=NodeState.FAILED,
                    error="detenido por falta de progreso: 4 vueltas seguidas sin ninguna "
                          "herramienta ejecutada con éxito. Último obstáculo: browser.open_url "
                          "falló: TargetClosedError")
    text = await responder.build(mission, _graph([nodo]))

    assert "falta de progreso" in text
    assert "TargetClosedError" in text
