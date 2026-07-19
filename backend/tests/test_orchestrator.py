# tests/test_orchestrator.py — la capa de misiones concurrentes (R2, doc 23 §0)
#
# Lo que se prueba aquí es lo que el TIE NO puede hacer solo:
#   - un mensaje con varios encargos se convierte en varias misiones,
#   - que corren A LA VEZ (medido, no supuesto),
#   - respetando dependencias,
#   - y donde una que falla o queda esperando aprobación NO congela a las demás.
#
# Más el test de NO-REGRESIÓN, que es el que protege al 80% de los mensajes:
# un solo objetivo no puede pagar ni una llamada extra al LLM.
from __future__ import annotations

import asyncio

import pytest

import app.orchestrator as orchestrator
from app.orchestrator import conductor, store
from app.orchestrator.contracts import Objective, OrchestrationRun


class _Envelope:
    def __init__(self, text: str, channel: str = "web"):
        self.text = text
        self.channel = channel


def _fake_classify(monkeypatch, objectives: list[str]):
    """Sustituye el clasificador del TIE y CUENTA las veces que se llama."""
    import app.tie as tie
    from app.tie.contracts import Intent, IntentType

    llamadas = {"n": 0}

    async def _classify(text, *, channel=None):
        llamadas["n"] += 1
        return Intent(type=IntentType.QUERY, goal=text, confidence=0.9, objectives=objectives)

    monkeypatch.setattr(tie, "classify", _classify)
    return llamadas


def _fake_tie_handle(monkeypatch, respuesta="respuesta del TIE"):
    import app.tie as tie
    llamadas = {"n": 0}

    async def _handle(envelope):
        llamadas["n"] += 1
        return respuesta

    monkeypatch.setattr(tie, "handle", _handle)
    return llamadas


def _fake_submit_mission(monkeypatch, *, delay: float = 0.0, state: str = "done",
                         outcome: str = "hecho", fail_on: str | None = None):
    """Sustituye `tie.submit_mission` por una misión falsa con duración
    controlada, para poder MEDIR la concurrencia sin depender de un LLM."""
    import app.tie as tie
    from app.tie.contracts import Mission

    lanzadas: list[str] = []

    async def _submit(goal, *, source="automation", channel=None, project_id=None,
                      run_id=None, parent_id=None):
        lanzadas.append(goal)
        if delay:
            await asyncio.sleep(delay)
        if fail_on and fail_on in goal:
            return Mission(id=Mission.new_id(), goal=goal, state="failed",
                           outcome="no pude", run_id=run_id, parent_id=parent_id)
        return Mission(id=Mission.new_id(), goal=goal, state=state,
                       outcome=f"{outcome}: {goal[:40]}", run_id=run_id, parent_id=parent_id)

    monkeypatch.setattr(tie, "submit_mission", _submit)
    return lanzadas


def _fake_decompose(monkeypatch, objetivos: list[Objective]):
    from app.orchestrator import decomposer

    async def _dec(message, *, objectives_hint, depth=0):
        return [Objective(**{**o.to_dict(), "depth": depth}) for o in objetivos]

    monkeypatch.setattr(decomposer, "decompose", _dec)


def _fake_consolidate(monkeypatch):
    from app.orchestrator import consolidator

    async def _cons(run):
        return " | ".join(f"{o.goal}={o.state}" for o in run.objectives)

    monkeypatch.setattr(consolidator, "consolidate", _cons)


@pytest.fixture(autouse=True)
def _limpia_runs():
    """Borra los runs que cree cada test (van al Postgres/SQLite real).

    El `create_all` de entrada es el patrón ya usado en `test_mel_decision.py`:
    `init_db()` corre al importar `app.db.database`, antes de que los modelos de
    los módulos (orchestrator/mel/...) estén registrados, así que sus tablas no
    existen en la BD de tests. En producción las crea la migración."""
    from app.db.database import Base, engine as db_engine
    Base.metadata.create_all(bind=db_engine)

    creados: list[str] = []
    original = store.save

    def _spy(run, **kwargs):
        if run.id not in creados:
            creados.append(run.id)
        return original(run, **kwargs)

    store.save = _spy
    yield
    store.save = original

    from app.db.database import SessionLocal
    from app.orchestrator.models import OrchestrationRunRow
    db = SessionLocal()
    try:
        for rid in creados:
            row = db.get(OrchestrationRunRow, rid)
            if row:
                db.delete(row)
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# LA REGLA DE NO-REGRESIÓN (doc 23 §0)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_un_solo_objetivo_delega_en_el_tie_sin_llamadas_extra(monkeypatch):
    """El 80% de los mensajes. Debe costar EXACTAMENTE lo mismo que antes."""
    clasificaciones = _fake_classify(monkeypatch, objectives=[])   # 0 objetivos = uno solo
    handles = _fake_tie_handle(monkeypatch, "respuesta corta")

    # Si el orquestador llamara al decomposer o al consolidador, estos petarían.
    from app.orchestrator import consolidator, decomposer

    async def _boom(*a, **kw):
        raise AssertionError("el camino de 1 objetivo NO debe descomponer ni consolidar")

    monkeypatch.setattr(decomposer, "decompose", _boom)
    monkeypatch.setattr(consolidator, "consolidate", _boom)

    out = await orchestrator.handle(_Envelope("¿qué hora es?"))

    assert out == "respuesta corta"
    assert handles["n"] == 1
    assert clasificaciones["n"] == 1   # la MISMA que el TIE ya hacía, ni una más


@pytest.mark.anyio
async def test_si_la_capa_falla_delega_en_el_tie(monkeypatch):
    """Degradación: un fallo del orquestador nunca deja al usuario sin respuesta."""
    import app.tie as tie

    async def _classify_roto(text, *, channel=None):
        raise RuntimeError("clasificador caído")

    monkeypatch.setattr(tie, "classify", _classify_roto)
    handles = _fake_tie_handle(monkeypatch, "fallback del TIE")

    out = await orchestrator.handle(_Envelope("lo que sea"))
    assert out == "fallback del TIE" and handles["n"] == 1


# ---------------------------------------------------------------------------
# Concurrencia real
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_tres_objetivos_corren_a_la_vez(monkeypatch):
    """Los 3 objetivos de un mensaje se ejecutan SOLAPADOS, no en fila.

    Se mide contando cuántas misiones hay en vuelo a la vez, no con reloj de
    pared: bajo la carga de la suite completa un umbral de tiempo es un flake
    garantizado, mientras que el solapamiento es un hecho binario."""
    _fake_classify(monkeypatch, objectives=["a", "b", "c"])
    _fake_decompose(monkeypatch, [
        Objective(id="o1", goal="objetivo A"),
        Objective(id="o2", goal="objetivo B"),
        Objective(id="o3", goal="objetivo C"),
    ])
    _fake_consolidate(monkeypatch)

    import app.tie as tie
    from app.tie.contracts import Mission

    en_vuelo = {"ahora": 0, "max": 0}
    lanzadas: list[str] = []

    async def _submit(goal, **kwargs):
        lanzadas.append(goal)
        en_vuelo["ahora"] += 1
        en_vuelo["max"] = max(en_vuelo["max"], en_vuelo["ahora"])
        await asyncio.sleep(0.05)     # cede el control: si fuera secuencial,
        en_vuelo["ahora"] -= 1        # el máximo en vuelo nunca pasaría de 1
        return Mission(id=Mission.new_id(), goal=goal, state="done", outcome="ok")

    monkeypatch.setattr(tie, "submit_mission", _submit)

    out = await orchestrator.handle(_Envelope("haz A, B y C"))

    assert len(lanzadas) == 3
    assert en_vuelo["max"] >= 2, "las misiones se ejecutaron en fila, no en paralelo"
    assert out.count("=done") == 3


@pytest.mark.anyio
async def test_el_semaforo_limita_la_concurrencia(monkeypatch):
    """ORCH_MAX_CONCURRENT protege al MEL y a los modelos locales."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "ORCH_MAX_CONCURRENT", 2)

    en_vuelo = {"ahora": 0, "max": 0}
    import app.tie as tie
    from app.tie.contracts import Mission

    async def _submit(goal, **kwargs):
        en_vuelo["ahora"] += 1
        en_vuelo["max"] = max(en_vuelo["max"], en_vuelo["ahora"])
        await asyncio.sleep(0.15)
        en_vuelo["ahora"] -= 1
        return Mission(id=Mission.new_id(), goal=goal, state="done", outcome="ok")

    monkeypatch.setattr(tie, "submit_mission", _submit)

    run = OrchestrationRun(id=OrchestrationRun.new_id(), user_message="x", objectives=[
        Objective(id=f"o{i}", goal=f"tarea {i}") for i in range(1, 6)
    ])
    await conductor.run_objectives(run)

    assert en_vuelo["max"] <= 2, f"llegó a {en_vuelo['max']} misiones a la vez"


# ---------------------------------------------------------------------------
# Dependencias
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_un_objetivo_espera_a_sus_dependencias(monkeypatch):
    """El caso real: 'cuando termines todo, avisa a Héctor'."""
    orden: list[str] = []
    import app.tie as tie
    from app.tie.contracts import Mission

    async def _submit(goal, **kwargs):
        orden.append(goal)
        await asyncio.sleep(0.05)
        return Mission(id=Mission.new_id(), goal=goal, state="done", outcome=f"listo {goal}")

    monkeypatch.setattr(tie, "submit_mission", _submit)

    run = OrchestrationRun(id=OrchestrationRun.new_id(), user_message="x", objectives=[
        Objective(id="o1", goal="investigar"),
        Objective(id="o2", goal="redactar"),
        Objective(id="o3", goal="avisar al final", depends_on=["o1", "o2"]),
    ])
    await conductor.run_objectives(run)

    # El goal del último lleva añadido el contexto de sus dependencias (por eso
    # se compara con startswith, no con igualdad).
    assert orden[-1].startswith("avisar al final")
    assert orden[0] in ("investigar", "redactar")
    assert all(o.state == "done" for o in run.objectives)


@pytest.mark.anyio
async def test_el_contexto_de_las_dependencias_llega_al_objetivo(monkeypatch):
    """'Avisa de lo que hiciste' necesita saber QUÉ se hizo."""
    recibidos: list[str] = []
    import app.tie as tie
    from app.tie.contracts import Mission

    async def _submit(goal, **kwargs):
        recibidos.append(goal)
        return Mission(id=Mission.new_id(), goal=goal, state="done",
                       outcome="encontré 3 avances clave")

    monkeypatch.setattr(tie, "submit_mission", _submit)

    run = OrchestrationRun(id=OrchestrationRun.new_id(), user_message="x", objectives=[
        Objective(id="o1", goal="investigar IA"),
        Objective(id="o2", goal="resumirme lo investigado", depends_on=["o1"]),
    ])
    await conductor.run_objectives(run)

    assert any("encontré 3 avances clave" in g for g in recibidos)


# ---------------------------------------------------------------------------
# Aislamiento — lo que hoy es imposible
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_una_mision_que_falla_no_tumba_a_las_demas(monkeypatch):
    _fake_submit_mission(monkeypatch, fail_on="ROTO")

    run = OrchestrationRun(id=OrchestrationRun.new_id(), user_message="x", objectives=[
        Objective(id="o1", goal="tarea buena 1"),
        Objective(id="o2", goal="tarea ROTO"),
        Objective(id="o3", goal="tarea buena 2"),
    ])
    await conductor.run_objectives(run)

    estados = {o.id: o.state for o in run.objectives}
    assert estados == {"o1": "done", "o2": "failed", "o3": "done"}
    assert run.state == "done"      # algo útil salió


@pytest.mark.anyio
async def test_una_mision_esperando_aprobacion_no_bloquea_a_las_demas(monkeypatch):
    """El motivo principal del bloque: hoy un gate congela el mensaje entero."""
    import app.tie as tie
    from app.tie.contracts import Mission

    async def _submit(goal, **kwargs):
        if "sensible" in goal:
            return Mission(id=Mission.new_id(), goal=goal, state="waiting",
                           outcome="esperando tu aprobación")
        return Mission(id=Mission.new_id(), goal=goal, state="done", outcome="hecho")

    monkeypatch.setattr(tie, "submit_mission", _submit)

    run = OrchestrationRun(id=OrchestrationRun.new_id(), user_message="x", objectives=[
        Objective(id="o1", goal="enviar algo sensible"),
        Objective(id="o2", goal="tarea normal"),
    ])
    await conductor.run_objectives(run)

    assert run.by_id("o1").state == "waiting"
    assert run.by_id("o2").state == "done"     # NO se quedó bloqueada


@pytest.mark.anyio
async def test_los_dependientes_de_algo_fallido_se_marcan_saltados(monkeypatch):
    """Nunca se quedan en `pending` fingiendo que siguen vivos."""
    _fake_submit_mission(monkeypatch, fail_on="ROTO")

    run = OrchestrationRun(id=OrchestrationRun.new_id(), user_message="x", objectives=[
        Objective(id="o1", goal="paso ROTO"),
        Objective(id="o2", goal="depende del roto", depends_on=["o1"]),
    ])
    await conductor.run_objectives(run)

    assert run.by_id("o1").state == "failed"
    assert run.by_id("o2").state == "skipped"
    assert run.is_settled()


# ---------------------------------------------------------------------------
# Anidamiento
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_un_objetivo_amplio_se_descompone_en_submisiones(monkeypatch):
    """'Crea 15 canales' → sub-misiones, con parent_id."""
    from app.orchestrator import decomposer

    async def _dec(message, *, objectives_hint, depth=0):
        return [Objective(id="s1", goal="canal 1", depth=depth),
                Objective(id="s2", goal="canal 2", depth=depth)]

    monkeypatch.setattr(decomposer, "decompose", _dec)
    lanzadas = _fake_submit_mission(monkeypatch)

    run = OrchestrationRun(id=OrchestrationRun.new_id(), user_message="x", objectives=[
        Objective(id="o1", goal="crea varios canales", needs_decomposition=True),
    ])
    await conductor.run_objectives(run)

    assert len(lanzadas) == 2                      # se ejecutaron las 2 partes
    assert run.by_id("o1").state == "done"
    assert "canal 1" in (run.by_id("o1").outcome or "")


@pytest.mark.anyio
async def test_la_profundidad_maxima_corta_la_recursion(monkeypatch):
    """Sin este tope, un decomposer que siempre pide descomponer no pararía."""
    from app.core.config import settings
    from app.orchestrator import decomposer

    monkeypatch.setattr(settings, "ORCH_MAX_DEPTH", 1)

    async def _dec_infinito(message, *, objectives_hint, depth=0):
        return [Objective(id="s1", goal=f"parte A d{depth}", needs_decomposition=True, depth=depth),
                Objective(id="s2", goal=f"parte B d{depth}", needs_decomposition=True, depth=depth)]

    monkeypatch.setattr(decomposer, "decompose", _dec_infinito)
    lanzadas = _fake_submit_mission(monkeypatch)

    run = OrchestrationRun(id=OrchestrationRun.new_id(), user_message="x", objectives=[
        Objective(id="o1", goal="algo enorme", needs_decomposition=True, depth=0),
    ])
    await conductor.run_objectives(run)

    # depth 0 descompone en 2 (depth 1); esos ya tocan techo y se ejecutan.
    assert len(lanzadas) == 2
    assert run.by_id("o1").state == "done"


# ---------------------------------------------------------------------------
# Persistencia y cancelación
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_el_run_se_persiste_y_se_puede_leer(monkeypatch):
    _fake_submit_mission(monkeypatch)

    run = OrchestrationRun(id=OrchestrationRun.new_id(), user_message="mensaje real",
                           objectives=[Objective(id="o1", goal="tarea")])
    await conductor.run_objectives(run)

    leido = orchestrator.get_run(run.id)
    assert leido is not None
    assert leido["user_message"] == "mensaje real"
    assert leido["objectives"][0]["state"] == "done"


@pytest.mark.anyio
async def test_cancelar_un_run_detiene_los_objetivos_pendientes(monkeypatch):
    import app.tie as tie
    from app.tie.contracts import Mission

    run = OrchestrationRun(id=OrchestrationRun.new_id(), user_message="x", objectives=[
        Objective(id="o1", goal="primera"),
        Objective(id="o2", goal="segunda", depends_on=["o1"]),
    ])

    async def _submit(goal, **kwargs):
        if goal == "primera":
            store.mark_cancelled(run.id)      # el usuario cancela a mitad
        return Mission(id=Mission.new_id(), goal=goal, state="done", outcome="ok")

    monkeypatch.setattr(tie, "submit_mission", _submit)

    await conductor.run_objectives(run)
    assert run.state == "cancelled"
    assert run.by_id("o2").state == "cancelled"   # nunca llegó a lanzarse


# ---------------------------------------------------------------------------
# Contratos
# ---------------------------------------------------------------------------
def test_ready_respeta_dependencias_y_es_determinista():
    run = OrchestrationRun(id="r", user_message="x", objectives=[
        Objective(id="o1", goal="a", priority=0),
        Objective(id="o2", goal="b", priority=5),
        Objective(id="o3", goal="c", depends_on=["o1"]),
    ])
    assert [o.id for o in run.ready()] == ["o2", "o1"]   # prioridad desc, luego id
    run.by_id("o1").state = "done"
    assert "o3" in [o.id for o in run.ready()]


def test_run_serializa_y_deserializa():
    run = OrchestrationRun(id="r1", user_message="hola", objectives=[
        Objective(id="o1", goal="algo", depends_on=["o0"], outcome="listo"),
    ])
    copia = OrchestrationRun.from_dict(run.to_dict())
    assert copia.id == run.id
    assert copia.objectives[0].depends_on == ["o0"]
    assert copia.objectives[0].outcome == "listo"


def test_decomposer_rompe_ciclos():
    """Un ciclo dejaría los objetivos en `pending` para siempre."""
    from app.orchestrator.decomposer import _parse

    objetivos = _parse({"objectives": [
        {"id": "o1", "goal": "a", "depends_on": ["o2"]},
        {"id": "o2", "goal": "b", "depends_on": ["o1"]},
    ]}, depth=0)

    run = OrchestrationRun(id="r", user_message="x", objectives=objetivos)
    assert run.ready(), "el ciclo dejó el run sin objetivos lanzables"


def test_decomposer_descarta_dependencias_inexistentes():
    from app.orchestrator.decomposer import _parse

    objetivos = _parse({"objectives": [
        {"id": "o1", "goal": "a", "depends_on": ["no_existe"]},
    ]}, depth=0)
    assert objetivos[0].depends_on == []
