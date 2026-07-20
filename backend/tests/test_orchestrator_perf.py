# tests/test_orchestrator_perf.py — presupuestos del Orquestador (R7, doc 23 §3·R7)
#
# Hasta R7, la regla de no-regresión de doc 23 §0 —"para un mensaje de un solo
# objetivo el Orquestador no añade NI UNA llamada al LLM ni un milisegundo"— era
# una PROMESA escrita en un documento. Aquí se mide.
#
# Es la promesa más importante del bloque en términos de producto: el ~80% de los
# mensajes son de un solo encargo, así que una regresión aquí la nota el usuario
# en CADA conversación, no en el caso raro.
#
# Todo con dobles deterministas y sin red, para que corra en CI: lo que se mide
# es el coste del ORQUESTADOR, no la latencia de un LLM real.
from __future__ import annotations

import asyncio
import time

import pytest

from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine
from app.orchestrator import models as orch_models

# Presupuestos (doc 23 §3·R7). Holgados a propósito respecto a lo medido: un
# test de rendimiento que salta por ruido del CI se acaba silenciando, y un
# test silenciado no protege nada.
OVERHEAD_1_OBJETIVO_MS = 50      # lo que el Orquestador puede añadir al camino de siempre
# Criterio de concurrencia: N misiones de duración D deben costar MENOS que 2·D,
# no ~N·D. No se exige la concurrencia perfecta (1·D) a propósito: el conductor
# persiste el run entero en cada transición (lo que lo hace auditable y
# reanudable), y eso son ~50 ms fijos por run medidos con 3 objetivos. Exigir
# 1·D convertiría este test en un detector de ruido de disco.
CONCURRENCIA_FACTOR = 2.0


def _borrar_residuos():
    s = SessionLocal()
    try:
        s.query(OrchestratorTrace).delete()
        s.query(orch_models.OrchestrationRunRow).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


@pytest.fixture(autouse=True)
def _clean():
    # Al entrar Y al salir: estos tests cuentan filas, así que un residuo ajeno
    # los hace fallar solo cuando corre la suite entera.
    Base.metadata.create_all(bind=db_engine)
    _borrar_residuos()
    yield
    _borrar_residuos()


class _Env:
    def __init__(self, text):
        self.text, self.channel, self.user_ref = text, "electron", "u1"


# ===========================================================================
# 1 — LA REGLA DE NO-REGRESIÓN, MEDIDA
# ===========================================================================
@pytest.mark.anyio
async def test_un_objetivo_no_paga_ni_una_llamada_extra_al_LLM(monkeypatch):
    """La mitad barata de la promesa: con un solo encargo, el Orquestador
    reutiliza el intent que el TIE iba a calcular igualmente. Cero llamadas
    nuevas — ni al decomposer ni al consolidador."""
    import app.orchestrator as orchestrator
    import app.tie as tie

    llamadas = {"classify": 0, "otras": 0}

    async def _classify(text, channel=None):
        llamadas["classify"] += 1
        from app.tie.contracts import Intent, IntentType
        return Intent(type=IntentType.CONVERSATIONAL, goal=text, confidence=0.9, objectives=[])

    async def _handle(envelope):
        return "respuesta del TIE"

    monkeypatch.setattr(tie, "classify", _classify)
    monkeypatch.setattr(tie, "handle", _handle)

    import app.mel as mel

    async def _no_deberia_llamarse(req):
        llamadas["otras"] += 1
        from app.mel import ExecutionResult
        return ExecutionResult(text="{}", ok=True)
    monkeypatch.setattr(mel, "complete", _no_deberia_llamarse)

    out = await orchestrator.handle(_Env("¿qué tal estás?"))

    assert out == "respuesta del TIE"
    assert llamadas["classify"] == 1, "el intent debe calcularse UNA vez y reutilizarse"
    assert llamadas["otras"] == 0, (
        "el Orquestador llamó al LLM por su cuenta en un mensaje de un solo encargo"
    )


@pytest.mark.anyio
async def test_overhead_del_orquestador_bajo_50ms(monkeypatch):
    """La otra mitad: el tiempo. Se compara `tie.handle` a pelo contra el mismo
    camino pasando por `orchestrator.handle`. La diferencia es TODO lo que el
    Orquestador añade — con el LLM neutralizado, es puro coste de la capa."""
    import app.orchestrator as orchestrator
    import app.tie as tie

    async def _classify(text, channel=None):
        from app.tie.contracts import Intent, IntentType
        return Intent(type=IntentType.CONVERSATIONAL, goal=text, confidence=0.9, objectives=[])

    async def _handle(envelope):
        return "ok"

    monkeypatch.setattr(tie, "classify", _classify)
    monkeypatch.setattr(tie, "handle", _handle)

    env = _Env("hola")
    REPS = 40

    # Calentamiento: el primer paso importa módulos de forma diferida y mediría
    # el coste del import, no el de la capa.
    for _ in range(5):
        await tie.handle(env)
        await orchestrator.handle(env)

    t0 = time.perf_counter()
    for _ in range(REPS):
        await tie.handle(env)
    solo_tie = (time.perf_counter() - t0) / REPS

    t0 = time.perf_counter()
    for _ in range(REPS):
        await orchestrator.handle(env)
    con_orquestador = (time.perf_counter() - t0) / REPS

    overhead_ms = (con_orquestador - solo_tie) * 1000
    assert overhead_ms < OVERHEAD_1_OBJETIVO_MS, (
        f"el Orquestador añade {overhead_ms:.1f} ms al camino de un solo objetivo "
        f"(presupuesto {OVERHEAD_1_OBJETIVO_MS} ms). Lo nota el ~80% de los mensajes."
    )


@pytest.mark.anyio
async def test_un_objetivo_no_escribe_un_run_en_la_BD(monkeypatch):
    """Coste que no se ve en el reloj pero se acumula en disco: un mensaje
    trivial no debe dejar una fila de orquestación."""
    import app.orchestrator as orchestrator
    import app.tie as tie

    async def _classify(text, channel=None):
        from app.tie.contracts import Intent, IntentType
        return Intent(type=IntentType.CONVERSATIONAL, goal=text, confidence=0.9, objectives=[])

    monkeypatch.setattr(tie, "classify", _classify)
    monkeypatch.setattr(tie, "handle", lambda env: _async("ok"))

    await orchestrator.handle(_Env("hola"))

    s = SessionLocal()
    try:
        assert s.query(orch_models.OrchestrationRunRow).count() == 0
    finally:
        s.close()


# ===========================================================================
# 2 — CONCURRENCIA REAL (no "se lanzan en paralelo" de boquilla)
# ===========================================================================
def _run_con_objetivos(n: int, prefijo: str = "o"):
    from app.orchestrator import Objective, OrchestrationRun
    return OrchestrationRun(
        id=OrchestrationRun.new_id(),
        user_message="mensaje de prueba",
        objectives=[Objective(id=f"{prefijo}{i}", goal=f"objetivo {i}") for i in range(n)],
        channel="test", source="user",
    )


def _mision_lenta(monkeypatch, duracion_s: float, *, registro: list | None = None):
    """Sustituye `tie.submit_mission` por una misión que tarda un tiempo FIJO.
    Con esto, medir concurrencia es aritmética: 4 misiones de 100 ms en serie
    son 400 ms; concurrentes con límite 3, ~200 ms."""
    import app.tie as tie
    from app.tie.contracts import Mission

    en_vuelo = {"ahora": 0, "pico": 0}

    async def _submit(goal, **kwargs):
        en_vuelo["ahora"] += 1
        en_vuelo["pico"] = max(en_vuelo["pico"], en_vuelo["ahora"])
        if registro is not None:
            registro.append(goal)
        try:
            await asyncio.sleep(duracion_s)
        finally:
            en_vuelo["ahora"] -= 1
        m = Mission(id=Mission.new_id(), goal=goal, source="user")
        m.state, m.outcome = "done", f"listo: {goal}"
        return m

    monkeypatch.setattr(tie, "submit_mission", _submit)
    return en_vuelo


@pytest.mark.anyio
async def test_los_objetivos_corren_de_verdad_en_paralelo(monkeypatch):
    """Lo que justifica el bloque entero: 3 encargos independientes no pueden
    costar 3 veces uno. Con ORCH_MAX_CONCURRENT=3 y misiones de 200 ms, el run
    entero debe rondar los 200 ms, no los 600."""
    from app.core.config import settings
    from app.orchestrator import conductor as conductor_mod

    monkeypatch.setattr(settings, "ORCH_MAX_CONCURRENT", 3)
    DURACION = 0.2
    _mision_lenta(monkeypatch, DURACION)

    run = _run_con_objetivos(3)
    t0 = time.perf_counter()
    await conductor_mod.run_objectives(run)
    transcurrido = time.perf_counter() - t0

    en_serie = DURACION * 3
    assert transcurrido < DURACION * CONCURRENCIA_FACTOR, (
        f"3 objetivos tardaron {transcurrido*1000:.0f} ms; en serie serían "
        f"{en_serie*1000:.0f} ms y con concurrencia perfecta {DURACION*1000:.0f} ms. "
        f"No se están ejecutando en paralelo."
    )
    assert all(o.state == "done" for o in run.objectives)


@pytest.mark.anyio
async def test_ORCH_MAX_CONCURRENT_se_respeta_de_verdad(monkeypatch):
    """El semáforo no es decorativo: lanzar 8 misiones a la vez contra un LLM
    con límite de tasa es la forma rápida de que el proveedor corte. Se mide el
    PICO real de misiones simultáneas, no la configuración."""
    from app.core.config import settings
    from app.orchestrator import conductor as conductor_mod

    LIMITE = 2
    monkeypatch.setattr(settings, "ORCH_MAX_CONCURRENT", LIMITE)
    en_vuelo = _mision_lenta(monkeypatch, 0.05)

    run = _run_con_objetivos(8)
    await conductor_mod.run_objectives(run)

    assert en_vuelo["pico"] <= LIMITE, (
        f"hubo {en_vuelo['pico']} misiones a la vez con ORCH_MAX_CONCURRENT={LIMITE}"
    )
    assert en_vuelo["pico"] > 1, "con 8 objetivos y límite 2, algo va mal si nunca hubo 2 a la vez"
    assert all(o.state == "done" for o in run.objectives), "el límite no puede perder objetivos"


@pytest.mark.anyio
async def test_las_dependencias_no_se_paralelizan(monkeypatch):
    """El contrapunto del test anterior: paralelizar está bien salvo cuando el
    usuario dijo "y cuando acabes, avísame". Un objetivo dependiente NUNCA
    puede solaparse con aquel del que depende."""
    from app.core.config import settings
    from app.orchestrator import Objective, OrchestrationRun, conductor as conductor_mod

    monkeypatch.setattr(settings, "ORCH_MAX_CONCURRENT", 5)
    orden: list[str] = []
    en_vuelo = _mision_lenta(monkeypatch, 0.05, registro=orden)

    run = OrchestrationRun(
        id=OrchestrationRun.new_id(), user_message="haz A y B, luego C",
        objectives=[
            Objective(id="a", goal="objetivo A"),
            Objective(id="b", goal="objetivo B"),
            Objective(id="c", goal="objetivo C final", depends_on=["a", "b"]),
        ],
        channel="test", source="user",
    )
    await conductor_mod.run_objectives(run)

    # `startswith` y no igualdad: el conductor anexa al goal el contexto de las
    # dependencias ("Contexto de pasos previos: ..."), que es justamente la
    # prueba de que esperó a que terminaran.
    assert orden[-1].startswith("objetivo C final"), f"el dependiente no fue el último: {orden}"
    assert "objetivo A" in orden[-1], "el dependiente no recibió el resultado del que dependía"
    assert en_vuelo["pico"] == 2, (
        f"pico de {en_vuelo['pico']}: A y B debían solaparse, y C ir sola después"
    )


@pytest.mark.anyio
async def test_un_objetivo_lento_no_bloquea_a_los_rapidos(monkeypatch):
    """El escenario real de doc 23 §0: "responde este email" no puede esperar a
    "crea 15 canales de YouTube". Se comprueba que los rápidos terminan mientras
    el lento sigue en vuelo."""
    import app.tie as tie
    from app.core.config import settings
    from app.orchestrator import conductor as conductor_mod
    from app.tie.contracts import Mission

    monkeypatch.setattr(settings, "ORCH_MAX_CONCURRENT", 5)
    terminados: list[str] = []

    async def _submit(goal, **kwargs):
        await asyncio.sleep(0.3 if "lento" in goal else 0.02)
        terminados.append(goal)
        m = Mission(id=Mission.new_id(), goal=goal, source="user")
        m.state, m.outcome = "done", "ok"
        return m

    monkeypatch.setattr(tie, "submit_mission", _submit)

    from app.orchestrator import Objective, OrchestrationRun
    run = OrchestrationRun(
        id=OrchestrationRun.new_id(), user_message="mezcla",
        objectives=[
            Objective(id="o1", goal="objetivo lento de verdad"),
            Objective(id="o2", goal="objetivo rapido A"),
            Objective(id="o3", goal="objetivo rapido B"),
        ],
        channel="test", source="user",
    )
    await conductor_mod.run_objectives(run)

    assert terminados[-1] == "objetivo lento de verdad", (
        f"los rápidos debían acabar antes que el lento: {terminados}"
    )


# ===========================================================================
# 3 — El coste de la capa en sí (sin LLM, sin misiones)
# ===========================================================================
@pytest.mark.anyio
async def test_persistir_un_run_es_barato(monkeypatch):
    """El conductor persiste el run entero en CADA transición de objetivo (es lo
    que lo hace auditable y reanudable). Con muchos objetivos eso podría
    convertirse en el cuello de botella, así que se mide."""
    from app.orchestrator import store

    run = _run_con_objetivos(20)
    t0 = time.perf_counter()
    for _ in range(20):
        store.save(run)
    por_guardado_ms = (time.perf_counter() - t0) / 20 * 1000

    assert por_guardado_ms < 50, (
        f"guardar un run de 20 objetivos cuesta {por_guardado_ms:.1f} ms; "
        f"se hace en cada transición"
    )


async def _async(v):
    return v
