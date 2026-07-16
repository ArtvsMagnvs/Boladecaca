# tests/test_tie_graph.py — Graph Execution Engine: validación DAG (V1.0 T2, doc 21 §3·T2)
#
# Blinda las invariantes que se validan ANTES de ejecutar (doc 14 §3.4.1): DAG sin
# ciclos (Kahn), depends_on a ids existentes, tools ⊆ catálogo del ToolManager, y
# el ready_set que el executor (T3) consumirá.
import pytest

from app.tie import graph as g
from app.tie.contracts import NodeState, TaskNode


def _n(nid, goal="hacer algo", depends_on=None, tools=None, priority=0):
    return TaskNode(id=nid, goal=goal, depends_on=depends_on or [], tools=tools or [], priority=priority)


def test_dag_lineal_valido():
    graph = g.build("m1", [_n("n1"), _n("n2", depends_on=["n1"]), _n("n3", depends_on=["n2"])])
    ok, reason = g.validate(graph, tool_catalog=set())
    assert ok is True and reason == "ok"


def test_dag_con_ramas_valido():
    # n3 depende de n1 y n2 (dos ramas independientes que convergen)
    graph = g.build("m1", [_n("n1"), _n("n2"), _n("n3", depends_on=["n1", "n2"])])
    ok, _ = g.validate(graph, tool_catalog=set())
    assert ok is True


def test_ciclo_se_rechaza():
    graph = g.build("m1", [_n("a", depends_on=["b"]), _n("b", depends_on=["a"])])
    ok, reason = g.validate(graph, tool_catalog=set())
    assert ok is False and "ciclo" in reason.lower()


def test_ciclo_de_tres_se_rechaza():
    graph = g.build("m1", [
        _n("a", depends_on=["c"]), _n("b", depends_on=["a"]), _n("c", depends_on=["b"]),
    ])
    ok, reason = g.validate(graph, tool_catalog=set())
    assert ok is False and "ciclo" in reason.lower()


def test_autodependencia_se_rechaza():
    graph = g.build("m1", [_n("a", depends_on=["a"])])
    ok, reason = g.validate(graph, tool_catalog=set())
    assert ok is False and "sí mismo" in reason


def test_dependencia_a_id_inexistente_se_rechaza():
    graph = g.build("m1", [_n("n1", depends_on=["fantasma"])])
    ok, reason = g.validate(graph, tool_catalog=set())
    assert ok is False and "inexistente" in reason


def test_tool_fuera_del_catalogo_se_rechaza():
    graph = g.build("m1", [_n("n1", tools=["navegador_inventado"])])
    ok, reason = g.validate(graph, tool_catalog={"filesystem", "shell"})
    assert ok is False and "inexistente" in reason


def test_tool_en_catalogo_pasa():
    graph = g.build("m1", [_n("n1", tools=["filesystem"])])
    ok, _ = g.validate(graph, tool_catalog={"filesystem", "shell"})
    assert ok is True


def test_grafo_vacio_se_rechaza():
    graph = g.build("m1", [])
    ok, reason = g.validate(graph, tool_catalog=set())
    assert ok is False and "no tiene nodos" in reason


def test_nodo_sin_goal_se_rechaza():
    graph = g.build("m1", [_n("n1", goal="")])
    ok, reason = g.validate(graph, tool_catalog=set())
    assert ok is False and "goal" in reason


def test_ready_set_inicial_solo_nodos_sin_dependencias():
    graph = g.build("m1", [_n("n1"), _n("n2", depends_on=["n1"]), _n("n3")])
    ready = g.ready_set(graph)
    assert {n.id for n in ready} == {"n1", "n3"}  # n2 espera a n1


def test_ready_set_avanza_al_completar_dependencia():
    graph = g.build("m1", [_n("n1"), _n("n2", depends_on=["n1"])])
    graph.nodes["n1"].state = NodeState.DONE
    ready = g.ready_set(graph)
    assert {n.id for n in ready} == {"n2"}


def test_ready_set_orden_determinista_por_prioridad():
    graph = g.build("m1", [_n("z", priority=1), _n("a", priority=5), _n("m", priority=1)])
    ready = g.ready_set(graph)
    # prioridad desc, luego id asc → a(5), m(1), z(1)
    assert [n.id for n in ready] == ["a", "m", "z"]
