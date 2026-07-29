# tests/test_audit_new4_rendicion.py — NEW-4 (doc 34 §12.4): un nodo puede
# quedar "Hecha" contradiciendo su propio texto.
#
# EL FALLO REAL (verificación en vivo, 2026-07-28): el paso 1 de una misión
# respondió literalmente "No puedo completar este objetivo: las herramientas
# disponibles en este paso NO incluyen ninguna de búsqueda web ni navegador" —
# y la UI lo mostró con el check verde de completado. Causa: `_validate_result`
# (T3 §3.4.7) pregunta "¿corrió alguna herramienta con éxito y hay salida con
# forma?", no "¿consiguió su objetivo?". El nodo hizo un `list_dir` correcto,
# así que su prosa de rendición se aceptó como resultado válido — honesto a
# nivel de texto, mentira a nivel de estado.
from __future__ import annotations

import pytest

from app.automation import Approval, approval_gate
from app.core.grounding import is_surrender
from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine
from app.tie import (
    AgentResult,
    AgentRuntime,
    Mission,
    NodeState,
    RuntimeHealth,
    TaskGraph,
    TaskNode,
    executor,
    new_mission,
    register_runtime,
    tracer,
)


@pytest.fixture(autouse=True)
def _tables_and_clean():
    Base.metadata.create_all(bind=db_engine)
    executor._CANCELLED.clear()
    executor._NODE_TASKS.clear()
    yield
    executor._CANCELLED.clear()
    executor._NODE_TASKS.clear()
    s = SessionLocal()
    try:
        s.query(OrchestratorTrace).delete()
        s.query(Approval).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


# ===========================================================================
# is_surrender — función pura
# ===========================================================================
_MENSAJE_REAL = (
    "No puedo completar este objetivo: las herramientas disponibles en este "
    "paso NO incluyen ninguna de búsqueda web ni navegador."
)


@pytest.mark.parametrize("texto", [
    _MENSAJE_REAL,
    "No puedo completar esta tarea con las herramientas que tengo asignadas.",
    "No puedo cumplir este objetivo, me falta acceso a internet.",
    "No conseguí completar la tarea solicitada.",
    "No ha sido posible completar el paso pedido.",
    "No dispongo de las herramientas necesarias para hacer esto.",
    "I cannot complete this objective with the tools available.",
    "Unable to complete this task in the current step.",
])
def test_detecta_rendicion_explicita(texto):
    assert is_surrender(texto) is True


@pytest.mark.parametrize("texto", [
    "",
    "   ",
    "He listado los archivos de la carpeta correctamente.",
    "Encontré 12 documentos en el proyecto y los he resumido abajo.",
    # Resultado PARCIAL honesto: cuenta lo que sí logró, la mención de lo que
    # falló va al final — no es una rendición, es un resultado parcial.
    ("He revisado los 8 archivos del proyecto y generado el índice pedido. "
     "Nota: no pude acceder al último commit porque git no estaba disponible, "
     "pero el resto del trabajo está completo y no puedo decir que haya fallado."),
    "El objetivo se ha cumplido: aquí tienes el resumen solicitado.",
])
def test_no_dispara_con_resultados_honestos_o_parciales(texto):
    assert is_surrender(texto) is False


def test_solo_mira_la_cabecera_no_el_cuerpo_entero():
    """Una rendición mencionada muy al final, tras un resultado sustancial, no
    debe contar — evita que un resumen largo que de pasada roza la frase
    dispare un falso positivo."""
    texto = ("X" * 300) + " no puedo completar este objetivo"
    assert is_surrender(texto) is False


# ===========================================================================
# Integración con el executor — el nodo se degrada a FAILED
# ===========================================================================
class _FakeRuntime(AgentRuntime):
    def __init__(self, output: str):
        self.output = output

    @property
    def capabilities(self):
        return {"chat", "tool_use_basic"}

    async def execute_task(self, task, memory, tools, approval_gate):
        # Mismo caso real: la tool SÍ corrió con éxito (de ahí `success=True`
        # con salida), pero el propio texto es una rendición.
        return AgentResult(task_id=task.id, success=True, output=self.output, tokens=3)

    async def stream_task(self, task, memory, tools, approval_gate):
        yield None

    async def health_check(self):
        return RuntimeHealth(available=True)


def _graph(mission_id: str, nodes: list[TaskNode]) -> TaskGraph:
    return TaskGraph(id="g1", mission_id=mission_id, nodes={n.id: n for n in nodes})


def _start(goal="misión de test"):
    m = new_mission(goal, source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    return m, trace_id


@pytest.mark.anyio
async def test_nodo_con_rendicion_explicita_queda_failed_no_done():
    """LA REGRESIÓN EXACTA: una tool corrió bien (success=True, hay salida),
    pero el texto es una rendición explícita — el nodo NO puede quedar DONE."""
    register_runtime("surrender", _FakeRuntime(_MENSAJE_REAL))
    m, trace_id = _start()
    g = _graph(m.id, [TaskNode(id="n1", goal="recolectar info", runtime="surrender")])
    tracer.record_plan(trace_id, g)

    await executor.run(g, m, trace_id=trace_id)

    assert g.nodes["n1"].state == NodeState.FAILED
    assert g.nodes["n1"].validation["ok"] is False
    assert g.nodes["n1"].validation["method"] == "grounding"
    assert "rindió" in g.nodes["n1"].validation["notes"]
    assert "rindió" in (g.nodes["n1"].error or "")


@pytest.mark.anyio
async def test_nodo_con_resultado_real_sigue_quedando_done():
    """No-regresión: la inmensa mayoría de nodos no dicen nada parecido a una
    rendición y deben seguir quedando DONE exactamente como antes."""
    register_runtime("normal", _FakeRuntime("He listado los archivos: a.py, b.py, c.py"))
    m, trace_id = _start()
    g = _graph(m.id, [TaskNode(id="n1", goal="listar", runtime="normal")])
    tracer.record_plan(trace_id, g)

    await executor.run(g, m, trace_id=trace_id)

    assert g.nodes["n1"].state == NodeState.DONE
    assert g.nodes["n1"].validation == {"ok": True, "method": "schema", "notes": ""}


@pytest.mark.anyio
async def test_nodo_con_resultado_parcial_honesto_sigue_done():
    """No-regresión clave: un nodo que cuenta lo que sí logró y menciona un
    fallo parcial de pasada NO es una rendición — sigue DONE."""
    texto = ("He revisado los 8 archivos del proyecto y generado el índice "
             "pedido. Nota: no pude acceder al último commit porque git no "
             "estaba disponible, pero el resto del trabajo está completo.")
    register_runtime("parcial", _FakeRuntime(texto))
    m, trace_id = _start()
    g = _graph(m.id, [TaskNode(id="n1", goal="revisar", runtime="parcial")])
    tracer.record_plan(trace_id, g)

    await executor.run(g, m, trace_id=trace_id)

    assert g.nodes["n1"].state == NodeState.DONE
