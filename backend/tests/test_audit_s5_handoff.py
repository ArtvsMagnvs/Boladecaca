# tests/test_audit_s5_handoff.py — el resultado de una tool debe llegar entero
# al paso siguiente (S5 del doc 34, NEW-1)
#
# EL FALLO REAL QUE CIERRA (campaña 00, T13): el agente leyó el GDD con
# `read_docx` → **`"ok": true`** — y acto seguido respondió: *"el paso que debía
# redactar el resumen falló porque el contenido completo no llegó a cargarse en
# la sesión"*. La tool funcionó; el contenido no sobrevivió al paso siguiente.
#
# La causa raíz (rastreada en el código, doc 34): `executor._execute_node`
# construía el contexto del nodo SOLO con memoria del MOS. El resultado de los
# nodos de los que ESTE depende (`node.depends_on`) no llegaba por ningún
# camino. "El contenido no llegó a cargarse en la sesión" era LITERALMENTE
# cierto: no había tubería. El patrón "lee X y haz Y con ello" —el caso de uso
# central de un asistente— solo funcionaba si ambas cosas caían en el mismo
# nodo; en cuanto el planner las separaba, el segundo trabajaba a ciegas.
#
# Y la segunda mitad: la observación de una tool se recortaba a 4000 caracteres
# sobre el JSON YA SERIALIZADO, así que cuánto contenido real sobrevivía
# dependía del ruido de estructura de cada documento — de ahí el "a veces lee
# más, a veces menos, sin patrón visible".
from __future__ import annotations

import json

import pytest

from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine
from app.tie import (
    AgentResult, AgentRuntime, Mission, NodeState, RuntimeHealth, TaskGraph,
    TaskNode, executor, register_runtime, tracer,
)


@pytest.fixture(autouse=True)
def _clean():
    Base.metadata.create_all(bind=db_engine)
    yield
    s = SessionLocal()
    try:
        s.query(OrchestratorTrace).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


class _Espia(AgentRuntime):
    """Runtime que ANOTA el contexto que recibe cada nodo — es justo lo que el
    fallo hacía invisible— y devuelve un output configurable por nodo."""

    def __init__(self, outputs: dict[str, str]):
        self.outputs = outputs
        self.contextos: dict[str, str] = {}

    @property
    def capabilities(self):
        return {"chat"}

    async def execute_task(self, task, memory, tools, approval_gate):
        self.contextos[task.node_id] = task.context or ""
        return AgentResult(task_id=task.id, success=True,
                           output=self.outputs.get(task.node_id, "hecho"), tokens=1)

    async def stream_task(self, task, memory, tools, approval_gate):
        yield None

    async def health_check(self):
        return RuntimeHealth(available=True)


def _grafo(nodes) -> TaskGraph:
    return TaskGraph(id="g-s5", mission_id="m-s5", nodes={n.id: n for n in nodes})


# ===========================================================================
# 1) La tubería: el resultado del paso previo llega al siguiente
# ===========================================================================
@pytest.mark.anyio
async def test_el_contenido_del_paso_previo_llega_al_siguiente(monkeypatch):
    """LA REPRO EXACTA de T13: paso 1 lee el documento, paso 2 lo resume.
    Antes de S5, el paso 2 no veía ni un carácter del documento."""
    gdd = "El hongo Cordyceps infecta al huésped y altera su comportamiento. " * 30
    rt = _Espia({"n1": gdd, "n2": "resumen listo"})
    register_runtime("s5rt", rt)

    g = _grafo([
        TaskNode(id="n1", goal="leer el GDD", runtime="s5rt"),
        TaskNode(id="n2", goal="resumir el GDD", runtime="s5rt", depends_on=["n1"]),
    ])
    mission = Mission(id="m-s5", goal="lee el GDD y resúmelo")
    trace_id = tracer.record_start(mission)

    await executor.run(g, mission, trace_id=trace_id)

    ctx2 = rt.contextos["n2"]
    assert "Cordyceps infecta al huésped" in ctx2, "el contenido del paso 1 NO llegó al paso 2"
    assert "RESULTADO DEL PASO PREVIO «leer el GDD»" in ctx2   # y etiquetado, no suelto
    assert rt.contextos["n1"] == ""            # el primero no depende de nadie: sin cambios


@pytest.mark.anyio
async def test_varias_dependencias_llegan_todas_y_en_orden(monkeypatch):
    rt = _Espia({"n1": "DATO UNO", "n2": "DATO DOS", "n3": "final"})
    register_runtime("s5rt2", rt)

    g = _grafo([
        TaskNode(id="n1", goal="paso uno", runtime="s5rt2"),
        TaskNode(id="n2", goal="paso dos", runtime="s5rt2"),
        TaskNode(id="n3", goal="juntar", runtime="s5rt2", depends_on=["n1", "n2"]),
    ])
    mission = Mission(id="m-s5b", goal="junta lo de ambos")
    await executor.run(g, mission, trace_id=tracer.record_start(mission))

    ctx3 = rt.contextos["n3"]
    assert "DATO UNO" in ctx3 and "DATO DOS" in ctx3
    assert ctx3.index("DATO UNO") < ctx3.index("DATO DOS")   # orden de depends_on


@pytest.mark.anyio
async def test_handoff_largo_se_recorta_diciendo_cuanto_falta(monkeypatch):
    """Honestidad en el recorte: el paso siguiente tiene que SABER que le falta
    contenido, para poder pedirlo — no suponer que eso era todo el documento."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "TIE_NODE_HANDOFF_CHARS", 500)
    largo = "x" * 5000
    rt = _Espia({"n1": largo, "n2": "ok"})
    register_runtime("s5rt3", rt)

    g = _grafo([
        TaskNode(id="n1", goal="leer", runtime="s5rt3"),
        TaskNode(id="n2", goal="usar", runtime="s5rt3", depends_on=["n1"]),
    ])
    mission = Mission(id="m-s5c", goal="lee y usa")
    await executor.run(g, mission, trace_id=tracer.record_start(mission))

    ctx2 = rt.contextos["n2"]
    assert "[TRUNCADO: 500 de 5000 caracteres]" in ctx2
    assert len(ctx2) < 1200


@pytest.mark.anyio
async def test_un_paso_fallido_no_ensucia_el_contexto_del_siguiente(monkeypatch):
    """Solo se pasa lo que salió BIEN: el resultado de un paso fallido no es
    material de trabajo."""
    g = _grafo([
        TaskNode(id="n1", goal="paso que falla", runtime="s5rt4",
                 state=NodeState.FAILED, result={"output": "BASURA DE UN FALLO"}),
        TaskNode(id="n2", goal="paso libre", runtime="s5rt4"),
    ])
    n2 = g.nodes["n2"]
    n2.depends_on = ["n1"]

    assert executor._handoff_from_deps(n2, g) == ""


def test_dependencia_sin_resultado_no_rompe():
    g = _grafo([
        TaskNode(id="n1", goal="sin salida", state=NodeState.DONE, result=None),
        TaskNode(id="n2", goal="siguiente", depends_on=["n1"]),
    ])
    assert executor._handoff_from_deps(g.nodes["n2"], g) == ""


def test_nodo_sin_dependencias_no_cambia_nada():
    """No regresión: un nodo suelto ve exactamente el contexto de siempre."""
    g = _grafo([TaskNode(id="n1", goal="solo")])
    assert executor._handoff_from_deps(g.nodes["n1"], g) == ""


# ===========================================================================
# 2) La observación: contenido, no JSON descabezado
# ===========================================================================
def test_lectura_de_documento_entrega_texto_plano_no_json():
    """La otra mitad del fallo: el recorte actuaba sobre el JSON serializado,
    así que las comillas y las claves (`"paragraphs":`…) se comían parte del
    presupuesto de contenido."""
    from app.tie.toolloop import _observation

    payload = {
        "path": "/home/u/gdd.docx",
        "paragraphs": ["p1", "p2"],
        "tables": [],
        "text": "El Cordyceps altera el comportamiento del huésped.",
        "paragraph_count": 2,
    }
    obs = _observation("document", "read_docx", payload)

    assert "El Cordyceps altera el comportamiento del huésped." in obs
    assert '"paragraphs":' not in obs        # el ruido de estructura, fuera
    assert "gdd.docx" in obs                 # los metadatos útiles, en una línea


def test_lectura_de_documento_tiene_presupuesto_grande():
    """Un GDD no puede compartir tope con un `list_dir`."""
    from app.core.config import settings
    from app.tie.toolloop import _observation

    texto = "contenido real. " * 2000        # ~32k chars
    obs = _observation("document", "read_docx", {"text": texto})

    assert len(obs) > 20_000, "la lectura de documento se está recortando como un list_dir"
    assert len(obs) < settings.TIE_OBSERVATION_CHARS_CONTENT + 500


def test_accion_normal_conserva_el_tope_de_siempre():
    """No regresión: un `list_dir` gigante sigue acotado a 4000 — el tope
    general existe por un motivo y no se toca."""
    from app.tie.toolloop import _observation

    payload = {"entries": ["archivo_%d.txt" % i for i in range(5000)]}
    obs = _observation("filesystem", "list_dir", payload)

    assert len(obs) < 4500
    assert "truncado" in obs                 # y lo dice


def test_el_truncado_siempre_declara_cuanto_queda_fuera():
    from app.tie.toolloop import _observation

    obs = _observation("document", "read_pdf", {"text": "y" * 100_000})
    assert "caracteres en total" in obs


def test_lectura_sin_campo_texto_sigue_funcionando():
    """`read_xlsx` devuelve filas, no `text`: no puede reventar, y merece el
    presupuesto grande igualmente."""
    from app.tie.toolloop import _observation

    payload = {"sheets": [{"name": "Hoja1", "rows": [[1, 2], [3, 4]]}]}
    obs = _observation("document", "read_xlsx", payload)
    assert "Hoja1" in obs
    assert json.loads(obs)["sheets"][0]["rows"] == [[1, 2], [3, 4]]


@pytest.mark.anyio
async def test_el_bucle_usa_de_verdad_el_presupuesto_de_contenido(monkeypatch, tmp_path):
    """EL CABLEADO, no solo la función. Este test nació de una comprobación de
    mutación: al desactivar `_observation` en el punto de llamada del bucle, los
    tests de la función pura seguían pasando — la lógica podía ser correcta y
    estar desconectada. Aquí se ejecuta `toolloop.run` REAL y se mira el prompt
    que le llega al modelo en la 2.ª vuelta."""
    from pathlib import Path

    from app.tie import toolloop
    from app.tools.tool_manager import tool_manager

    # Archivo REAL dentro de HOME (FilesystemTool solo opera ahí), de un tamaño
    # que el tope viejo de 4000 habría descabezado.
    carpeta = Path.home() / "_aithera_s5_test"
    carpeta.mkdir(exist_ok=True)
    doc = carpeta / "gdd.txt"
    contenido = "El Cordyceps altera el comportamiento del huésped. " * 400   # ~20k
    doc.write_text(contenido, encoding="utf-8")

    try:
        import app.mel as mel
        from app.mel import ExecutionResult, ServedBy, Usage

        prompts: list[str] = []
        cola = [
            json.dumps({"tool": {"tool_id": "filesystem", "action": "read_file",
                                 "params": {"path": str(doc)}}}),
            '{"answer": "leído"}',
        ]

        async def _complete(req):
            prompts.append(req.prompt)
            return ExecutionResult(text=cola.pop(0) if cola else '{"answer": "ya"}', ok=True,
                                   served_by=ServedBy("fake", "fake"), usage=Usage(tokens=1))
        monkeypatch.setattr(mel, "complete", _complete)

        res = await toolloop.run(instruction=f"lee {doc}", context="",
                                 allowed_tools=["filesystem"], tool_manager=tool_manager,
                                 max_iters=3)
        assert res.ok, res.error

        segundo = prompts[1]      # el prompt de la 2.ª vuelta ya trae la lectura
        assert segundo.count("El Cordyceps altera el comportamiento del huésped.") > 100, (
            "el contenido leído llega descabezado al modelo: el presupuesto de "
            "contenido no está cableado en el bucle"
        )
    finally:
        doc.unlink(missing_ok=True)
        carpeta.rmdir()


# ===========================================================================
# 3) read_docx: honesto sobre lo que NO lee
# ===========================================================================
@pytest.mark.anyio
async def test_read_docx_extrae_cabeceras_y_avisa_de_lo_que_no_lee(tmp_path, monkeypatch):
    """Antes se omitían cabeceras/pies EN SILENCIO. En un GDD con portada, el
    título vive justo ahí: bastaba eso para un "solo leyó una parte" sin que
    interviniera ningún límite de tamaño."""
    docx = pytest.importorskip("docx")
    from app.tools import document_tool
    from app.tools.document_tool import DocumentTool

    ruta = tmp_path / "gdd.docx"
    doc = docx.Document()
    doc.sections[0].header.paragraphs[0].text = "DeadlyCypros — GDD MVP"
    doc.add_paragraph("El hongo altera al huésped.")
    doc.save(str(ruta))

    # El validador de paths sólo permite dentro de HOME: se apunta a tmp_path.
    monkeypatch.setattr(document_tool, "_is_path_allowed", lambda p: True)
    monkeypatch.setattr(document_tool, "_resolve_user_path", lambda s: __import__("pathlib").Path(s))

    r = await DocumentTool().execute("read_docx", {"path": str(ruta)})

    assert r["success"]
    res = r["result"]
    assert "DeadlyCypros — GDD MVP" in res["headers"]
    assert "DeadlyCypros — GDD MVP" in res["text"]      # y entra en el texto que ve el modelo
    assert "El hongo altera al huésped." in res["text"]
    assert "cuadros de texto" in res["note"]           # aviso honesto de lo que NO lee
