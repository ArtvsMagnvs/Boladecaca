# tests/test_quick_answers.py — respuestas deterministas + acuse de misión
# (2026-07-24, el arreglo definitivo del "no tengo acceso a tus proyectos").
#
# Contratos que blinda:
#   1. "¿qué proyectos tengo?" (y variantes/idiomas) se responde de la BD, con
#      los proyectos REALES, 0 LLM — imposible alucinar.
#   2. Frases de ACCIÓN ("crea un proyecto...") NO disparan el listado.
#   3. El flujo REAL del chat (orquestador → texto) responde sin clasificador.
#   4. Una misión emite el ACUSE inmediato ("Entendido, me pongo con ello")
#      antes de ejecutar — el chat nunca se queda mudo.
import pytest

from app.db.database import Base, Config, Project, SessionLocal, engine
from app.tie import quick_answers
from app.tie.contracts import Intent, IntentType


@pytest.fixture(autouse=True)
def _seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(Project).delete()
        db.query(Config).delete()
        for n in ("OT Saas", "Waterquest", "Quicky Dungeons"):
            db.add(Project(name=n, status="active", progress=0.3))
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(Project).delete()
        db.query(Config).delete()
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 1) listados → respuesta determinista con los datos reales
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("msg", [
    "Dime qué proyectos tengo.",
    "¿Qué proyecto tengo?",
    "muestra mis proyectos",
    "lista mis proyectos",
    "Muestra mis proyectos actuales",
    "what projects do I have",
])
def test_listado_de_proyectos_responde_los_reales(msg):
    r = quick_answers.try_answer(msg)
    assert r is not None, f"{msg!r} debería responderse de la BD"
    for n in ("OT Saas", "Waterquest", "Quicky Dungeons"):
        assert n in r


def test_sin_proyectos_lo_dice_sin_inventar():
    db = SessionLocal()
    try:
        db.query(Project).delete()
        db.commit()
    finally:
        db.close()
    r = quick_answers.try_answer("¿qué proyectos tengo?")
    assert r is not None
    assert "OT Saas" not in r          # jamás inventa
    assert "ningún proyecto" in r


def test_respuesta_en_el_idioma_de_la_app():
    db = SessionLocal()
    try:
        db.add(Config(key="app_language", value="en"))
        db.commit()
    finally:
        db.close()
    r = quick_answers.try_answer("what projects do I have?")
    assert r is not None and r.startswith("You have")


# ---------------------------------------------------------------------------
# 2) acciones y otros temas NO disparan
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("msg", [
    "crea un proyecto llamado Foo",
    "abre el proyecto OT Saas",
    "borra el proyecto Waterquest",
    "en el proyecto X crea un agente con Minimax",
    "cuéntame qué tal el clima",
    "renombra mi proyecto",
    "archiva el proyecto viejo",
])
def test_acciones_no_disparan_el_listado(msg):
    assert quick_answers.try_answer(msg) is None


# ---------------------------------------------------------------------------
# 3) flujo REAL: orquestador → respuesta determinista, sin LLM ni misión
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_orquestador_responde_proyectos_sin_llm(monkeypatch):
    import app.orchestrator as orch
    import app.tie as tie

    async def _boom(text, channel=None):
        raise AssertionError("el listado de proyectos NO debe llamar al clasificador LLM")
    monkeypatch.setattr(tie, "classify", _boom)

    evs = [ev async for ev in orch.handle_stream("Dime qué proyectos tengo.")]
    texto = "".join(p for k, p in evs if k == "text")
    for n in ("OT Saas", "Waterquest", "Quicky Dungeons"):
        assert n in texto
    assert not any(k == "status" for k, _ in evs), "sin 'analizando' — es instantáneo"
    assert not any(k == "mission" for k, _ in evs), "sin misión — es un listado"


# ---------------------------------------------------------------------------
# 4) acuse inmediato al arrancar una misión (el chat nunca mudo)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_mision_emite_acuse_inmediato(monkeypatch):
    from app.tie import handle_stream
    from app.tie import pipeline as pl

    async def _classify(text, channel=None):
        return Intent(type=IntentType.EXECUTE, goal="investigar el mercado",
                      confidence=0.95, requires_planning=True, raw_text=text)
    monkeypatch.setattr(pl.intents, "classify", _classify)

    async def _complex(text, intent, mission, trace_id, context, **kw):
        mission.outcome = "informe listo"
    monkeypatch.setattr(pl, "_complex_path", _complex)

    async def _prefetch(t):
        return ""
    monkeypatch.setattr(pl, "_prefetch_context", _prefetch)

    evs = [ev async for ev in handle_stream("investiga el mercado y hazme un informe")]
    textos = [p for k, p in evs if k == "text"]
    assert textos, "la misión debe emitir texto"
    assert "Entendido" in textos[0], "el PRIMER texto debe ser el acuse inmediato"
    assert "investigar el mercado" in textos[0]
    assert "informe listo" in "".join(textos)
