# tests/test_action_intent.py — las ACCIONES sobre Aithera nunca degradan a
# charla, y Aithera nunca finge haberlas hecho (2026-07-25).
#
# EL FALLO REAL (log del usuario, 17:35:20):
#     classify LLM: 5781ms modelo='llama3'
#     [intents] sin JSON parseable, fallback conversational
# "crea una milestone MVP y un agente Investigador" → el clasificador local no
# produjo JSON → fail-safe conversational → chat SIN herramientas → el modelo
# respondió como si lo hubiera hecho. Y al preguntarle, volvió a mentir tirando
# del historial.
#
# Estos tests blindan el arreglo GLOBAL (no un parche para milestones):
#   1. Detector determinista de acción, DERIVADO del catálogo real de la tool
#      (test de cobertura: una acción nueva sin mapear rompe el test).
#   2. Los 3 caminos de fallo del clasificador conservan la intención de acción.
#   3. Una clasificación floja ("conversational" para una orden) se corrige.
#   4. La charla NO se convierte en acción (no se pierde versatilidad).
#   5. El bucle recibe el contexto real (ids de proyecto + historial) para
#      resolver "en este proyecto".
#   6. El prompt del chat PROHÍBE fingir ejecución e inventar datos.
import json

import pytest

from app.db.database import Base, ChatMessage, Project, SessionLocal, engine
from app.tie import action_intent as ai
from app.tie.contracts import Intent, IntentType


@pytest.fixture(autouse=True)
def _clean():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(Project).delete()
        db.query(ChatMessage).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(Project).delete()
        db.query(ChatMessage).delete()
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 1) El detector cubre TODO el catálogo de aithera_tool (anti-parche)
# ---------------------------------------------------------------------------
def test_el_detector_cubre_todas_las_acciones_del_catalogo():
    """Si mañana se añade una acción a `aithera_tool` y nadie la mapea en
    `_NOUN_TO_ACTIONS`, este test falla. Es lo que impide que el detector se
    quede obsoleto en silencio (y se convierta en un parche)."""
    import app.tools  # noqa: F401
    from app.tools import tool_manager

    acciones = set()
    for t in tool_manager.list_tools(include_internal=True):
        if t["tool_id"] == "aithera":
            acciones = {a["id"] for a in t.get("actions", [])}
    assert acciones, "no se encontró la tool 'aithera' en el catálogo"
    sin_cubrir = ai.assert_covers_catalog(acciones)
    assert not sin_cubrir, (
        f"acciones de aithera_tool sin sustantivo de dominio que las active: {sin_cubrir}. "
        f"Añádelas a _DOMAIN_NOUNS/_NOUN_TO_ACTIONS en action_intent.py"
    )


@pytest.mark.parametrize("msg", [
    "Crea un nuevo proyecto llamado Cordyceps",
    "ahora crea en este proyecto una milestone llamada MVP",
    "crea un agente que se llame Investigador con skills de web",
    "ponle skills de backend al agente Investigador",
    "asignale las tools de git al agente",
    "crea una tarea en el proyecto Aithera",
    "cierra la tarea de la milestone",
    "crea una regla de email para reuniones",
    "crea un recordatorio diario a las 8",
    "activa la regla de briefing",
    "borra el agente Investigador",
    "archiva el proyecto viejo",
    "abre el proyecto Waterquest",
    "cambia el idioma a inglés",
    "pon minimax como modelo principal del chat",
    "create a milestone called MVP",
    "change the language to english",
])
def test_detecta_ordenes_de_accion(msg):
    it = ai.action_intent(msg)
    assert it is not None, f"{msg!r} debe detectarse como acción"
    assert it.type == IntentType.EXECUTE
    assert it.requires_tools == ["aithera"]
    assert it.is_direct_action, "debe ir al camino de acción (bucle con herramientas)"


@pytest.mark.parametrize("msg", [
    "hola buenos días", "cómo estás", "gracias", "cuéntame un chiste",
    "dime qué proyectos tengo",      # listado → quick_answers, no acción
    "qué tareas tengo en niide",
    "qué agentes tengo",
    "resume mis emails importantes",
    "qué tal el clima mañana",
])
def test_la_charla_y_los_listados_no_son_accion(msg):
    """No se pierde versatilidad: charla y listados siguen su camino."""
    assert ai.action_intent(msg) is None


def test_verificar_si_algo_se_hizo_va_a_las_herramientas():
    """«¿has creado la milestone?» DEBE ir a herramientas para comprobarlo de
    verdad — en el fallo real esa pregunta se respondió con una mentira sacada
    del historial del chat."""
    assert ai.action_intent("has creado la milestone y el agente? no lo veo") is not None


# ---------------------------------------------------------------------------
# 2+3) classify: los 3 caminos de fallo y la corrección de tipo
# ---------------------------------------------------------------------------
ORDEN = "crea una milestone llamada MVP y un agente Investigador"


def _fake_router(monkeypatch, response=None, error=False, raises=False):
    from app.tie import router

    async def _complete(prompt, system_prompt=None, capability="chat", **kw):
        if raises:
            raise RuntimeError("proveedor caído")
        return {"response": response or "", "model": "llama3", "error": error}
    monkeypatch.setattr(router, "complete", _complete)


@pytest.mark.anyio
async def test_sin_json_parseable_la_orden_sigue_siendo_accion(monkeypatch):
    """EL FALLO EXACTO DEL LOG."""
    from app.tie import intents

    _fake_router(monkeypatch, response="lo siento, no sé responder en JSON")
    it = await intents.classify(ORDEN)
    assert it.type == IntentType.EXECUTE, "degradó a charla: el fallo real"
    assert "aithera" in it.requires_tools
    assert it.is_direct_action


@pytest.mark.anyio
async def test_error_del_proveedor_la_orden_sigue_siendo_accion(monkeypatch):
    from app.tie import intents

    _fake_router(monkeypatch, response="", error=True)
    it = await intents.classify(ORDEN)
    assert it.type == IntentType.EXECUTE
    assert "aithera" in it.requires_tools


@pytest.mark.anyio
async def test_excepcion_del_clasificador_la_orden_sigue_siendo_accion(monkeypatch):
    from app.tie import intents

    _fake_router(monkeypatch, raises=True)
    it = await intents.classify(ORDEN)
    assert it.type == IntentType.EXECUTE
    assert "aithera" in it.requires_tools


@pytest.mark.anyio
async def test_clasificacion_floja_se_corrige(monkeypatch):
    """El LLM dice 'conversational' para una ORDEN → se sube a EXECUTE."""
    from app.tie import intents

    _fake_router(monkeypatch, response=json.dumps({
        "type": "conversational", "goal": "charlar", "confidence": 0.9,
        "requires_tools": [], "requires_planning": False,
    }))
    it = await intents.classify(ORDEN)
    assert it.type == IntentType.EXECUTE
    assert "aithera" in it.requires_tools


@pytest.mark.anyio
async def test_tool_olvidada_se_anade_sin_pisar_las_demas(monkeypatch):
    from app.tie import intents

    _fake_router(monkeypatch, response=json.dumps({
        "type": "execute", "goal": "crear milestone", "confidence": 0.95,
        "requires_tools": ["filesystem"], "requires_planning": False,
    }))
    it = await intents.classify(ORDEN)
    assert "aithera" in it.requires_tools
    assert "filesystem" in it.requires_tools, "no se pisan las tools que el LLM sí detectó"


@pytest.mark.anyio
async def test_la_charla_no_se_fuerza_a_accion(monkeypatch):
    """Contra-prueba: el guard no rompe la charla (versatilidad intacta)."""
    from app.tie import intents

    _fake_router(monkeypatch, response=json.dumps({
        "type": "conversational", "goal": "saludar", "confidence": 0.9,
        "requires_tools": [], "requires_planning": False,
    }))
    it = await intents.classify("cuéntame algo interesante sobre el espacio")
    assert it.type == IntentType.CONVERSATIONAL
    assert "aithera" not in (it.requires_tools or [])


# ---------------------------------------------------------------------------
# 5) el bucle recibe contexto real (ids + historial) → resuelve "este proyecto"
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_el_bucle_recibe_ids_reales_y_el_historial(monkeypatch):
    from app.tie import pipeline as pl
    from app.tie.missions import new_mission
    from app.tie.runtime import AgentResult

    db = SessionLocal()
    try:
        db.add(Project(name="Cordyceps", status="active", progress=0.0))
        db.add(ChatMessage(role="user", content="Crea un proyecto llamado Cordyceps",
                           session_id="s1"))
        db.add(ChatMessage(role="assistant", content="Proyecto Cordyceps creado",
                           session_id="s1"))
        db.commit()
    finally:
        db.close()

    capt = {}

    class _FakeRT:
        async def execute_task(self, task, memory, tools, approval_gate):
            capt["context"] = task.context
            capt["tools"] = task.tools
            return AgentResult(task_id=task.id, success=True, output="hecho")

    monkeypatch.setattr(pl, "get_runtime", lambda name=None: _FakeRT())

    it = Intent(type=IntentType.EXECUTE, goal="crear milestone", confidence=1.0,
                requires_tools=["aithera"],
                raw_text="en este proyecto crea una milestone MVP")
    mission = new_mission(goal="x", source="user", channel="web")
    await pl._direct_action_path("en este proyecto crea una milestone MVP", it,
                                 mission, "tr-1", session_id="s1")

    assert "Cordyceps" in capt["context"], "el bucle debe ver el proyecto real con su id"
    assert "id 1" in capt["context"] or "[id" in capt["context"]
    assert "Últimos turnos" in capt["context"], (
        "el bucle debe ver el historial para resolver «este proyecto»"
    )
    assert "aithera" in capt["tools"]


# ---------------------------------------------------------------------------
# 6) el prompt del chat prohíbe fingir e inventar
# ---------------------------------------------------------------------------
def test_el_prompt_prohibe_fingir_ejecucion_e_inventar():
    from app.services.chat_service import DEFAULT_SYSTEM_PROMPT as P

    assert "NUNCA FINJAS HABER ACTUADO" in P
    assert "he creado" in P            # ejemplos explícitos de lo prohibido
    assert "NO INVENTES DATOS" in P
