# tests/test_i18n_strings.py — catálogo backend de fallbacks deterministas (I18N-10)
#
# Verifica que `app.core.strings.t()` resuelve correctamente en los 4 idiomas
# soportados, con fallback seguro, y que las plantillas deterministas de
# `tie/responder.py` y `orchestrator/consolidator.py` (las que se ven cuando NO
# hay LLM de por medio) salen en el idioma de interfaz elegido — el mismo
# principio que I18N-9 aplicó al chat, extendido a los fallbacks de puro código.
import pytest

from app.core import strings
from app.db.database import SessionLocal
from app.db.models import Config
from app.tie import responder
from app.tie.contracts import Mission, NodeState, TaskGraph, TaskNode
from app.orchestrator import consolidator
from app.orchestrator.contracts import Objective, OrchestrationRun


def _set_lang(value):
    db = SessionLocal()
    try:
        db.query(Config).filter(Config.key == "app_language").delete()
        if value is not None:
            db.add(Config(key="app_language", value=value))
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _clean_lang():
    _set_lang(None)
    yield
    _set_lang(None)


# ---------------------------------------------------------------------------
# app.core.strings.t() — la unidad
# ---------------------------------------------------------------------------
def test_sin_idioma_usa_espanol_por_defecto():
    assert strings.t("responder.node_done_fallback") == "hecho"


@pytest.mark.parametrize("lang,expected", [
    ("es", "hecho"),
    ("en", "done"),
    ("fr", "fait"),
    ("pt", "feito"),
])
def test_resuelve_los_4_idiomas(lang, expected):
    _set_lang(lang)
    assert strings.t("responder.node_done_fallback") == expected


def test_interpolacion_de_variables():
    _set_lang("en")
    out = strings.t("responder.completed_header", n=3, goal="test")
    assert "3" in out and "test" in out


def test_clave_desconocida_devuelve_la_propia_clave_sin_lanzar():
    assert strings.t("no.existe.esta.clave") == "no.existe.esta.clave"


def test_interpolacion_fallida_no_lanza():
    # Falta la variable `n` a propósito: no debe reventar, debe devolver algo.
    out = strings.t("responder.completed_header", goal="x")
    assert isinstance(out, str)


def test_idioma_no_soportado_cae_a_espanol():
    _set_lang("de")
    assert strings.t("responder.node_done_fallback") == "hecho"


# ---------------------------------------------------------------------------
# tie/responder.py — plantillas deterministas (sin LLM)
# ---------------------------------------------------------------------------
def _mission():
    return Mission(id="m1", goal="hacer algo")


def _node(id_, state, goal="paso", error=None):
    return TaskNode(id=id_, goal=goal, state=state, error=error)


def test_template_success_en_ingles():
    _set_lang("en")
    mission = _mission()
    done = [_node("n1", NodeState.DONE, goal="step one")]
    failed = [_node("n2", NodeState.FAILED, goal="step two", error="boom")]
    text = responder._template_success(mission, done, failed, [], [])
    assert "I completed" in text
    assert "I couldn't complete" in text
    assert "step two" in text


def test_template_success_en_frances():
    _set_lang("fr")
    mission = _mission()
    done = [_node("n1", NodeState.DONE, goal="étape un")]
    text = responder._template_success(mission, done, [], [], [])
    assert "J'ai terminé" in text


def test_template_failure_sin_fallos_en_portugues():
    _set_lang("pt")
    mission = _mission()
    text = responder._template_failure(mission, [])
    assert "Não consegui avançar" in text


def test_template_failure_con_razones_en_ingles():
    _set_lang("en")
    mission = _mission()
    failed = [_node("n1", NodeState.FAILED, goal="do X", error="network error")]
    text = responder._template_failure(mission, failed)
    assert "It failed" in text
    assert "network error" in text


def test_plan_summary_marca_permiso_en_ingles():
    _set_lang("en")
    graph = TaskGraph(id="g1", mission_id="m1", nodes={
        "n1": TaskNode(id="n1", goal="send email", approval_required=True),
    })
    summary = responder.plan_summary(graph)
    assert "needs your approval" in summary


def test_node_done_fallback_traducido():
    _set_lang("pt")
    node = _node("n1", NodeState.DONE, goal="x")
    assert responder._node_output(node) == "feito"


# ---------------------------------------------------------------------------
# orchestrator/consolidator.py — plantilla multi-objetivo (sin LLM)
# ---------------------------------------------------------------------------
def _run(objectives):
    return OrchestrationRun(id="r1", user_message="haz varias cosas", objectives=objectives)


def test_plantilla_multiobjetivo_en_ingles():
    _set_lang("en")
    objs = [
        Objective(id="o1", goal="task one", state="done", outcome="did it"),
        Objective(id="o2", goal="task two", state="failed", error="oops"),
    ]
    text = consolidator._plantilla(_run(objs))
    assert "I completed:" in text
    assert "I couldn't complete:" in text
    assert "oops" in text


def test_plantilla_nada_completado_en_frances():
    _set_lang("fr")
    objs = [Objective(id="o1", goal="task", state="failed", error="x")]
    text = consolidator._plantilla(_run(objs))
    assert "Je n'ai pas pu terminer" in text


def test_plantilla_vacia_en_portugues():
    _set_lang("pt")
    text = consolidator._plantilla(_run([]))
    assert text == "Não consegui concluir nenhuma das tarefas."


def test_estados_agrupados_en_ingles():
    """[S2·S6] Antes esto probaba `_detalle()` — el texto que se le pasaba al
    LLM del consolidator, que ya no existe (esa reescritura se eliminó, doc 34).
    Los estados siguen distinguiéndose para el usuario, pero por las cabeceras
    de grupo de la plantilla, que es ahora la única salida."""
    _set_lang("en")
    objs = [
        Objective(id="o1", goal="a", state="waiting"),
        Objective(id="o2", goal="b", state="skipped"),
    ]
    text = consolidator._plantilla(_run(objs))
    assert "Waiting for your approval:" in text
    assert "I couldn't complete:" in text


@pytest.mark.anyio
async def test_consolidate_sin_objetivos_en_ingles():
    _set_lang("en")
    text = await consolidator.consolidate(_run([]))
    assert text == "I didn't identify any task in your message."


@pytest.mark.anyio
async def test_consolidate_un_solo_objetivo_usa_su_outcome():
    _set_lang("en")
    objs = [Objective(id="o1", goal="a", state="done", outcome="ya está hecho")]
    text = await consolidator.consolidate(_run(objs))
    assert text == "ya está hecho"
