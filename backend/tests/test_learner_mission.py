# tests/test_learner_mission.py — V1.1 L2: Mission Learning.
#
# Un ÚNICO fake: la frontera del LLM (`mel.complete`). El agregador, la firma de
# trabajo, la cuarentena, la escalera y la BD son código REAL.
#
# Lo que estos tests fijan por encima de "funciona": que el Learner **no cueste
# más de lo que aporta** (0 LLM en la charla, 1 llamada por misión, plazo duro)
# y que **no fabrique skills** (una misión no crea una skill; tres misiones
# distintas crean un candidato que sigue teniendo que ganarse la validación).
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

import pytest

from app.db.database import Base, SessionLocal, engine
from app.learner import ladder, mission_learning, proposal_service, stats
from app.learner.models import (
    LearnerProposal,
    ModelStat,
    Skill,
    SkillEvent,
    ToolStat,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _limpio():
    Base.metadata.create_all(bind=engine)

    def _borra():
        with SessionLocal() as s:
            for modelo in (SkillEvent, Skill, LearnerProposal, ModelStat, ToolStat):
                s.query(modelo).delete()
            s.commit()
        mission_learning._procesadas.clear()
    _borra()
    yield
    _borra()


def _timeline(*, models=None, tools=None, path="planned", slowest=0, total=1000):
    return {"summary": {"llm_by_model": models or {}, "tools": tools or {},
                        "path": path, "slowest_llm_ms": slowest,
                        "total_ms": total}}


def _snapshot(goal="prepara el resumen semanal del proyecto Aithera",
              nodes=None, state="done", mission_id=None):
    return {
        "trace_id": str(uuid.uuid4()),
        "mission_id": mission_id or str(uuid.uuid4()),
        "state": state, "goal": goal, "intent_type": "task",
        "outcome": "hecho", "nodes": nodes if nodes is not None else [
            {"id": "n1", "goal": "leer tareas", "state": "done",
             "tools": ["workspace"], "error": None,
             "tool_calls": [{"tool": "aithera", "action": "list_tasks", "ok": True}]},
        ],
        "created_at": datetime.utcnow().isoformat(),
    }


class _Res:
    def __init__(self, text="", ok=True, error=None):
        self.text, self.ok, self.error = text, ok, error


def _fake_mel(monkeypatch, respuesta: str, *, contador=None, retraso=0.0):
    import app.mel as mel

    async def _complete(req):
        if contador is not None:
            contador.append(req)
        if retraso:
            await asyncio.sleep(retraso)
        return _Res(respuesta)

    monkeypatch.setattr(mel, "complete", _complete)


def _fake_datos(monkeypatch, timeline, snap):
    """Sustituye las DOS lecturas externas (telemetría y traza del TIE) por
    datos fijos. Se parchea el módulo de origen porque el Learner importa
    ambas de forma diferida dentro de la función."""
    import app.telemetry as telemetry
    from app.tie import tracer

    monkeypatch.setattr(telemetry, "mission_timeline", lambda mid: timeline)
    monkeypatch.setattr(tracer, "mission_snapshot", lambda mid: snap)


_RESPUESTA_REPETIBLE = (
    '{"reflection": "Se leyeron las tareas y se redactó el resumen sin '
    'incidencias.", "repeatable": true, "skill_name": "Resumen semanal de '
    'proyecto", "skill_steps": ["leer tareas abiertas", "redactar resumen"]}')
_RESPUESTA_NO_REPETIBLE = (
    '{"reflection": "Consulta puntual, resuelta.", "repeatable": false, '
    '"skill_name": "", "skill_steps": []}')


# ===========================================================================
# 1 · Firma de trabajo (pura)
# ===========================================================================
class TestFirma:
    def test_dos_redacciones_del_mismo_encargo_son_el_mismo_trabajo(self):
        """EL CASO QUE ROMPIÓ LA PRIMERA VERSIÓN (un hash sha1 de "las 6
        palabras más largas"): una cortesía larga desplazaba a una palabra de
        contenido y los hashes salían distintos. Comparar conjuntos no tiene
        ese problema."""
        assert mission_learning.same_work(
            "prepárame el resumen semanal del proyecto Aithera", ["aithera"],
            "por favor, quiero el resumen semanal para el proyecto Aithera", ["aithera"])

    def test_encargos_distintos_no_se_confunden(self):
        assert not mission_learning.same_work(
            "resumen semanal del proyecto", ["aithera"],
            "descarga el instalador de Blender", ["browser"])

    def test_las_mismas_palabras_con_otras_tools_es_otro_trabajo(self):
        """La herramienta ES parte del procedimiento: leer el informe del disco
        y buscarlo en la web no son la misma tarea aunque se pidan igual."""
        assert not mission_learning.same_work(
            "dame el informe fiscal", ["document"],
            "dame el informe fiscal", ["search"])

    def test_el_mismo_tema_pero_otra_tarea_no_cuela(self):
        """El umbral tiene que separar "resumen del proyecto X" de "borra el
        proyecto X" — comparten el sustantivo, no el trabajo."""
        assert not mission_learning.same_work(
            "prepara el resumen semanal del proyecto Aithera", ["aithera"],
            "archiva y borra las tareas viejas del proyecto Aithera", ["aithera"])

    def test_las_palabras_de_relleno_no_cuentan(self):
        """La cortesía frecuente se filtra. Las formas con pronombre enclítico
        («prepárame») NO se filtran a propósito —en español son infinitas— y no
        hace falta: al comparar por SIMILITUD y no por igualdad, una colada solo
        baja el índice, no cambia la conclusión."""
        assert mission_learning.content_words("por favor, dame el informe") == {"informe"}
        assert mission_learning.similarity(set(), {"a"}) == 0.0
        assert mission_learning.same_work(
            "prepárame el informe fiscal", ["document"],
            "el informe fiscal", ["document"])


# ===========================================================================
# 2 · Agregación determinista (0 LLM)
# ===========================================================================
class TestStats:
    def test_provider_y_modelo_se_parten_por_el_primer_dos_puntos(self):
        """Un modelo local lleva `:` en su propio nombre (`qwen2.5vl:7b`)."""
        assert stats.split_model_key("ollama:qwen2.5vl:7b") == ("ollama", "qwen2.5vl:7b")
        assert stats.split_model_key("minimax:M2.7") == ("minimax", "M2.7")

    def test_agrega_modelos_y_tools_de_un_timeline(self):
        stats.aggregate_from_timeline(
            _timeline(models={"ollama:llama3": {"calls": 3, "ms": 900, "fails": 1}},
                      tools={"filesystem": {"calls": 2, "ms": 40, "fails": 0}},
                      slowest=500),
            mission_ok=True)
        with SessionLocal() as s:
            m = s.query(ModelStat).one()
            t = s.query(ToolStat).one()
        assert (m.missions, m.missions_ok, m.calls, m.call_fails) == (1, 1, 3, 1)
        assert m.slowest_ms == 500
        assert (t.calls, t.fails, t.missions) == (2, 0, 1)

    def test_la_mision_fallida_cuenta_como_participacion_pero_no_como_exito(self):
        """LA SEÑAL QUE JUSTIFICA ESTA TABLA: el modelo respondió (3 llamadas,
        0 fallos técnicos) y la misión no sirvió. `mel_executions` vería un
        éxito perfecto; esto ve la verdad."""
        tl = _timeline(models={"minimax:M3": {"calls": 3, "ms": 600, "fails": 0}})
        stats.aggregate_from_timeline(tl, mission_ok=False)
        with SessionLocal() as s:
            m = s.query(ModelStat).one()
        assert m.missions == 1 and m.missions_ok == 0 and m.call_fails == 0

    def test_es_incremental_entre_misiones(self):
        tl = _timeline(models={"ollama:llama3": {"calls": 2, "ms": 100, "fails": 0}})
        stats.aggregate_from_timeline(tl, mission_ok=True)
        stats.aggregate_from_timeline(tl, mission_ok=False)
        with SessionLocal() as s:
            m = s.query(ModelStat).one()
        assert (m.missions, m.missions_ok, m.calls) == (2, 1, 4)

    def test_ranking_ordena_por_exito_de_mision_no_por_latencia(self):
        stats.aggregate_from_timeline(
            _timeline(models={"lento:bueno": {"calls": 1, "ms": 9000, "fails": 0}}),
            mission_ok=True)
        stats.aggregate_from_timeline(
            _timeline(models={"rapido:malo": {"calls": 1, "ms": 100, "fails": 0}}),
            mission_ok=False)
        top = stats.model_ranking()[0]
        assert top["model"] == "bueno" and top["mission_success_rate"] == 1.0

    def test_ranking_de_tools_pone_delante_lo_que_se_rompe(self):
        stats.aggregate_from_timeline(
            _timeline(tools={"browser": {"calls": 4, "ms": 100, "fails": 3},
                             "filesystem": {"calls": 4, "ms": 10, "fails": 0}}),
            mission_ok=True)
        r = stats.tool_ranking()
        assert r[0]["tool"] == "browser" and r[0]["error_rate"] == 0.75

    def test_un_modelo_sin_identificar_no_ensucia_las_medias(self):
        stats.aggregate_from_timeline(
            _timeline(models={"?": {"calls": 5, "ms": 100, "fails": 0}}),
            mission_ok=True)
        with SessionLocal() as s:
            assert s.query(ModelStat).count() == 0


# ===========================================================================
# 3 · El job — coste y disciplina
# ===========================================================================
class TestCoste:
    async def test_la_charla_no_paga_ni_una_llamada(self, monkeypatch):
        """Doc 15 §4: reflexionar sobre "¿qué hora es?" es reflection theater.
        Los contadores SÍ se guardan (son gratis)."""
        llamadas = []
        _fake_mel(monkeypatch, _RESPUESTA_REPETIBLE, contador=llamadas)
        _fake_datos(monkeypatch,
                    _timeline(models={"ollama:llama3": {"calls": 1, "ms": 300, "fails": 0}},
                              path="chat"),
                    _snapshot())

        pid = await mission_learning.learn_from_mission("m-chat", ok=True)
        assert pid is None
        assert llamadas == []                       # 0 LLM
        with SessionLocal() as s:
            assert s.query(ModelStat).count() == 1  # pero los contadores están

    async def test_una_mision_de_verdad_gasta_exactamente_una_llamada(self, monkeypatch):
        llamadas = []
        _fake_mel(monkeypatch, _RESPUESTA_REPETIBLE, contador=llamadas)
        _fake_datos(monkeypatch,
                    _timeline(models={"ollama:llama3": {"calls": 4, "ms": 800, "fails": 0}}),
                    _snapshot())
        await mission_learning.learn_from_mission("m-1", ok=True)
        assert len(llamadas) == 1

    async def test_la_reflexion_usa_analyze_y_politica_economica(self, monkeypatch):
        """Ollama-first: aprender no puede costar lo que trabajar."""
        import app.mel as mel

        llamadas = []
        _fake_mel(monkeypatch, _RESPUESTA_NO_REPETIBLE, contador=llamadas)
        _fake_datos(monkeypatch, _timeline(), _snapshot())
        await mission_learning.learn_from_mission("m-2", ok=True)
        req = llamadas[0]
        assert req.capability is mel.Capability.ANALYZE
        assert req.policy_override == "economy"

    async def test_un_modelo_lento_no_deja_la_mision_sin_contadores(self, monkeypatch):
        """El plazo duro: si la reflexión no llega, lo determinista ya está."""
        monkeypatch.setattr(mission_learning.settings,
                            "LEARNER_REFLECTION_BUDGET_S", 0.05, raising=False)
        _fake_mel(monkeypatch, _RESPUESTA_REPETIBLE, retraso=0.5)
        _fake_datos(monkeypatch,
                    _timeline(models={"ollama:llama3": {"calls": 1, "ms": 50, "fails": 0}}),
                    _snapshot())
        pid = await mission_learning.learn_from_mission("m-lento", ok=True)
        assert pid is None
        with SessionLocal() as s:
            assert s.query(ModelStat).count() == 1

    async def test_el_mismo_evento_dos_veces_no_duplica_contadores(self, monkeypatch):
        """El bus es best-effort: podría entregar dos veces."""
        _fake_mel(monkeypatch, _RESPUESTA_NO_REPETIBLE)
        _fake_datos(monkeypatch,
                    _timeline(models={"ollama:llama3": {"calls": 2, "ms": 100, "fails": 0}}),
                    _snapshot())
        await mission_learning.learn_from_mission("m-dup", ok=True)
        await mission_learning.learn_from_mission("m-dup", ok=True)
        with SessionLocal() as s:
            assert s.query(ModelStat).one().missions == 1

    async def test_un_modelo_que_devuelve_basura_no_rompe_nada(self, monkeypatch):
        _fake_mel(monkeypatch, "no soy JSON, soy prosa")
        _fake_datos(monkeypatch,
                    _timeline(models={"ollama:llama3": {"calls": 1, "ms": 10, "fails": 0}}),
                    _snapshot())
        assert await mission_learning.learn_from_mission("m-basura", ok=True) is None
        with SessionLocal() as s:
            assert s.query(ModelStat).count() == 1


# ===========================================================================
# 4 · Aprendizaje real: reflexión + candidatos por acumulación
# ===========================================================================
class TestAprendizaje:
    async def test_la_reflexion_se_guarda_enlazada_a_la_mision(self, monkeypatch):
        guardadas = []

        async def _store(**kw):
            guardadas.append(kw)
            return None

        import app.services.decision_service as ds
        monkeypatch.setattr(ds, "store_decision", _store)
        _fake_mel(monkeypatch, _RESPUESTA_NO_REPETIBLE)
        snap = _snapshot(mission_id="mis-42")
        _fake_datos(monkeypatch, _timeline(), snap)

        await mission_learning.learn_from_mission("mis-42", ok=True)
        assert len(guardadas) == 1
        assert guardadas[0]["mission_id"] == "mis-42"
        assert "sin incidencias" in guardadas[0]["body"] or guardadas[0]["body"]

    async def test_una_sola_mision_NO_crea_una_skill(self, monkeypatch):
        """La defensa contra la fábrica de skills-basura (doc 15 §10). Lo que
        nace es una OBSERVACIÓN en cuarentena, no una skill."""
        _fake_mel(monkeypatch, _RESPUESTA_REPETIBLE)
        _fake_datos(monkeypatch, _timeline(), _snapshot(mission_id="a"))

        pid = await mission_learning.learn_from_mission("a", ok=True)
        assert pid is not None
        prop = await proposal_service.get(pid)
        assert prop["state"] == "observed"
        with SessionLocal() as s:
            assert s.query(Skill).count() == 0       # ninguna skill creada

    async def test_tres_misiones_distintas_suben_la_observacion_a_candidata(self, monkeypatch):
        """EL comportamiento que da sentido a todo: la repetición se detecta
        por acumulación de evidencia, sin gastar un LLM extra ni una pasada de
        clustering — la escalera de L1 hace el trabajo."""
        _fake_mel(monkeypatch, _RESPUESTA_REPETIBLE)
        goal = "prepara el resumen semanal del proyecto Aithera"
        pid = None
        for i in range(3):
            _fake_datos(monkeypatch, _timeline(), _snapshot(goal=goal, mission_id=f"m{i}"))
            pid = await mission_learning.learn_from_mission(f"m{i}", ok=True)

        prop = await proposal_service.get(pid)
        assert prop["state"] == "candidate"
        assert len(prop["evidence"]) == ladder.MIN_REP
        with SessionLocal() as s:
            assert s.query(LearnerProposal).count() == 1   # UNA propuesta, no tres

    async def test_tres_veces_la_misma_mision_no_cuentan_como_tres(self, monkeypatch):
        """La protección contra rachas de L1, heredada: el `context_key` es el
        mission_id, así que repetir el mismo id no suma contextos."""
        _fake_mel(monkeypatch, _RESPUESTA_REPETIBLE)
        goal = "prepara el resumen semanal del proyecto Aithera"
        snap = _snapshot(goal=goal, mission_id="siempre-la-misma")
        pid = None
        for i in range(3):
            mission_learning._procesadas.clear()   # simula 3 entregas del bus
            _fake_datos(monkeypatch, _timeline(), snap)
            pid = await mission_learning.learn_from_mission("siempre-la-misma", ok=True)
        prop = await proposal_service.get(pid)
        assert prop["state"] == "observed"          # no sube: 1 solo contexto

    async def test_una_mision_fallida_no_propone_convertirse_en_procedimiento(self, monkeypatch):
        """De un fallo se aprende (la reflexión se guarda), pero enseñarlo como
        skill sería enseñar a fallar."""
        guardadas = []

        async def _store(**kw):
            guardadas.append(kw)
        import app.services.decision_service as ds
        monkeypatch.setattr(ds, "store_decision", _store)
        _fake_mel(monkeypatch, _RESPUESTA_REPETIBLE)
        _fake_datos(monkeypatch, _timeline(), _snapshot(state="failed"))

        pid = await mission_learning.learn_from_mission("m-fallida", ok=False)
        assert pid is None
        assert len(guardadas) == 1                  # pero SÍ se reflexionó

    async def test_sin_ninguna_tool_con_exito_no_hay_procedimiento(self, monkeypatch):
        """Mismo grounding que A-1: si no se ejecutó nada, no hay
        procedimiento que capturar — solo texto."""
        _fake_mel(monkeypatch, _RESPUESTA_REPETIBLE)
        nodos = [{"id": "n1", "goal": "pensar", "state": "done", "tools": [],
                  "tool_calls": [], "error": None}]
        _fake_datos(monkeypatch, _timeline(), _snapshot(nodes=nodos))
        assert await mission_learning.learn_from_mission("m-sin-tools", ok=True) is None

    async def test_el_candidato_lleva_los_pasos_y_las_tools_reales(self, monkeypatch):
        _fake_mel(monkeypatch, _RESPUESTA_REPETIBLE)
        _fake_datos(monkeypatch, _timeline(), _snapshot())
        pid = await mission_learning.learn_from_mission("m-pasos", ok=True)
        payload = (await proposal_service.get(pid))["payload"]
        assert payload["definition"]["steps"] == ["leer tareas abiertas", "redactar resumen"]
        assert payload["tools"] == ["aithera"]
        assert payload["created_by"] == "local_learning_loop"


# ===========================================================================
# 5 · Cableado real al bus
# ===========================================================================
class TestBus:
    async def test_el_evento_de_mision_dispara_el_aprendizaje(self, monkeypatch):
        """Con el bus REAL: se emite `mission.completed` y el Learner aprende.
        Es la prueba de que el cable existe — no de que la lógica funcione
        (eso son los tests de arriba)."""
        from app.core.events import emit, unsubscribe

        _fake_mel(monkeypatch, _RESPUESTA_NO_REPETIBLE)
        _fake_datos(monkeypatch,
                    _timeline(models={"ollama:llama3": {"calls": 1, "ms": 20, "fails": 0}}),
                    _snapshot(mission_id="bus-1"))
        mission_learning._registrado = False
        mission_learning.register_handlers()
        try:
            emit("mission.completed", source="tie",
                 payload={"mission_id": "bus-1", "ok": True, "nodes": 2})
            for _ in range(40):                     # el bus despacha con create_task
                await asyncio.sleep(0.01)
                with SessionLocal() as s:
                    if s.query(ModelStat).count():
                        break
            with SessionLocal() as s:
                assert s.query(ModelStat).count() == 1
        finally:
            unsubscribe("mission.completed", mission_learning._on_mission_settled)
            unsubscribe("mission.failed", mission_learning._on_mission_settled)
            mission_learning._registrado = False

    def test_registrar_dos_veces_no_duplica_suscripciones(self):
        from app.core import events

        mission_learning._registrado = False
        antes = len(events._subscribers.get("mission.completed", []))
        mission_learning.register_handlers()
        mission_learning.register_handlers()
        despues = len(events._subscribers.get("mission.completed", []))
        try:
            assert despues == antes + 1
        finally:
            events.unsubscribe("mission.completed", mission_learning._on_mission_settled)
            events.unsubscribe("mission.failed", mission_learning._on_mission_settled)
            mission_learning._registrado = False


# ===========================================================================
# 6 · El accesor de lectura del TIE (la frontera que L2 estrena)
# ===========================================================================
class TestSnapshot:
    def test_mission_snapshot_devuelve_lo_que_el_learner_necesita(self):
        """Contra el tracer REAL y una traza REAL: el Learner no conoce el
        esquema de `orchestrator_traces`, solo este contrato."""
        from app.tie import tracer
        from app.tie.contracts import Mission

        mission = Mission(id=str(uuid.uuid4()), goal="lee el informe y resúmelo")
        trace_id = tracer.record_start(mission, channel="test")
        try:
            snap = tracer.mission_snapshot(mission.id)
            assert snap is not None
            assert snap["mission_id"] == mission.id
            assert snap["trace_id"] == trace_id
            assert "nodes" in snap and isinstance(snap["nodes"], list)
        finally:
            tracer.delete_trace(trace_id)

    def test_una_mision_inexistente_no_revienta(self):
        from app.tie import tracer

        assert tracer.mission_snapshot("no-existe-jamas") is None
