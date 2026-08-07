# tests/test_lc3_ui.py — LA CARA (V1.1 LC3, doc 41 §8)
#
# Lo que este archivo defiende, en una frase: una "mejora de skill" no llega al
# usuario sin haberse comparado de verdad con la versión actual, y un veredicto
# re-juzgado no borra el anterior — queda enlazado, visible y cuenta para la
# calibración del juez.
#
# Tres piezas nuevas de LC3, en el mismo orden que el archivo:
#   1. `comparison.py` — la prueba de mejora efectiva (texto contra texto,
#      dominio-agnóstica: la MISMA técnica sirve para una skill de frontend que
#      para una de marketing porque compara SALIDAS, no ejecuta nada).
#   2. `_mejorar_skill` — la consolidación NO propone una mejora que la
#      comparación desmiente, y es honesta cuando no pudo comprobarla.
#   3. Re-juzgar (`judge_mission(force=True)`) — enlaza el veredicto anterior
#      (`superseded_by`), nunca lo borra, y la calibración lo cuenta.
#   4. La cara: los endpoints exponen lo necesario para que el usuario decida
#      con la comparación delante, no a ciegas.
#
# UN SOLO DOBLE, la frontera del LLM (`app.mel.complete`) — patrón S4/LC1/LC2.
from __future__ import annotations

import json
import uuid
from datetime import datetime

import pytest

from app.core import corpus
from app.db.database import Base, ChatMessage, OrchestratorTrace, SessionLocal, engine
from app.learner import comparison, judge, proposal_service, skill_library
from app.learner.consolidation import consolidate
from app.learner.models import LearnerProposal, MissionVerdict, Skill, SkillEvent
from app.telemetry.models import MissionEvent
from app.tie import tracer
from app.tie.contracts import Intent, IntentType, Mission, NodeState, TaskGraph, TaskNode

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _mundo_limpio():
    Base.metadata.create_all(bind=engine)

    def _borra():
        with SessionLocal() as s:
            for modelo in (SkillEvent, Skill, LearnerProposal, MissionVerdict,
                           MissionEvent, OrchestratorTrace, ChatMessage):
                s.query(modelo).delete()
            s.commit()

    _borra()
    corpus.reset_cache()
    yield
    _borra()
    corpus.reset_cache()


# ---------------------------------------------------------------------------
# Los dos dobles: una respuesta fija, o una SECUENCIA (varias llamadas
# encadenadas — consolidación → comparación → juez de la comparación).
# ---------------------------------------------------------------------------
def _responde(monkeypatch, payload, modelo: str = "ollama:deepseek-r1:8b",
              registro: list | None = None):
    class _Servido:
        def __init__(self, key):
            self.provider, self.model = key.split(":", 1)

    class _Res:
        ok = True

        def __init__(self, texto, key):
            self.text = texto
            self.served_by = _Servido(key)

    texto = payload if isinstance(payload, str) else json.dumps(payload)

    async def _r(req, *a, **k):
        if registro is not None:
            registro.append(req)
        return _Res(texto, modelo)

    monkeypatch.setattr("app.mel.complete", _r)


def _secuencia(monkeypatch, respuestas: list, registro: list | None = None):
    """Una respuesta DISTINTA por llamada, consumida en orden. Cada elemento es
    un dict/str (payload con modelo por defecto), una tupla (payload, "prov:mod")
    para fijar quién sirvió, o None para simular un fallo (`ok=False`)."""
    class _Servido:
        def __init__(self, key):
            self.provider, self.model = key.split(":", 1)

    class _Res:
        def __init__(self, texto, key, ok=True):
            self.ok = ok
            self.text = texto
            self.served_by = _Servido(key) if key else None

    cola = list(respuestas)

    async def _r(req, *a, **k):
        if registro is not None:
            registro.append(req)
        if not cola:
            raise RuntimeError("se agotó la secuencia de respuestas simuladas del MEL")
        item = cola.pop(0)
        payload, key = item if isinstance(item, tuple) else (item, "ollama:deepseek-r1:8b")
        if payload is None:
            return _Res("", key, ok=False)
        texto = payload if isinstance(payload, str) else json.dumps(payload)
        return _Res(texto, key)

    monkeypatch.setattr("app.mel.complete", _r)


def _veredicto(*, goal: str, verdict: str = "served", tools=("document",),
              origin: str = "user", mission_id: str | None = None) -> str:
    mid = mission_id or uuid.uuid4().hex
    with SessionLocal() as s:
        s.add(MissionVerdict(
            id=uuid.uuid4().hex, mission_id=mid, trace_id=None, origin=origin,
            verdict=verdict, confidence=0.9, reasons="motivo de prueba",
            evidence=["outcome_text"],
            signals={"goal": goal, "project_id": None,
                    "nodes": [{"id": "n1", "tools_used": list(tools)}],
                    "execution": {"problems": []}},
            lesson=None, judge_model="ollama:deepseek-r1:8b", judge_bias=False,
            created_at=datetime.utcnow()))
        s.commit()
    return mid


def _mision(goal: str, *, outcome: str = "hecho") -> Mission:
    """Una misión real, escrita por la maquinaria real del TIE — la que
    `judge_mission`/`signals.collect` necesitan para poder juzgar algo."""
    m = Mission(id=uuid.uuid4().hex, goal=goal, channel="hub",
               session_id=None, source="user")
    trace_id = tracer.record_start(m)
    tracer.record_intent(trace_id, Intent(
        type=IntentType.EXECUTE, goal=goal, confidence=0.9,
        requires_tools=["browser"], requires_planning=True, raw_text=goal))
    nodo = TaskNode(id="n1", goal=goal, tools=["browser"])
    nodo.state = NodeState.DONE
    nodo.tool_calls = [{"tool": "browser", "action": "play_media", "ok": True}]
    tracer.record_plan(trace_id, TaskGraph(id=uuid.uuid4().hex, mission_id=m.id,
                                           nodes={"n1": nodo}))
    m.state = "done"
    tracer.record_end(trace_id, outcome=outcome, state=m.state)
    m.trace_id = trace_id
    return m


async def _crear_skill(nombre: str = "Resumen semanal",
                       descripcion: str = "Prepara el resumen semanal de un proyecto.") -> str:
    from app.memory import LocalSkill, SkillStatus

    skill = LocalSkill(id=str(uuid.uuid4()), name=nombre, version="1.0.0",
                       description=descripcion, definition={}, input_schema={},
                       output_schema={}, runtime_agnostic=True,
                       created_by="local_learning_loop", created_at=datetime.utcnow(),
                       status=SkillStatus.DRAFT)
    await skill_library.create(skill, actor="learner")
    return skill.id


# ===========================================================================
# 1 · LA PRUEBA DE MEJORA EFECTIVA (comparison.py)
# ===========================================================================
class TestLaPruebaDeMejoraEfectiva:
    async def test_sin_tareas_de_ejemplo_no_se_puede_comparar(self):
        """Sin material real que comparar, no hay veredicto — ni a favor ni en
        contra. Cero llamadas al MEL: no hay nada que preguntar."""
        r = await comparison.compare_skill_change(
            skill_name="X", current_description="d", proposed_change="c",
            sample_tasks=[])
        assert r is None

    async def test_mejora_confirmada_por_el_juez(self, monkeypatch):
        peticiones: list = []
        _secuencia(monkeypatch, [
            ("hago X sin comprobar el resultado", "ollama:llama3"),
            ("hago X y valido el resultado antes de terminar", "ollama:llama3"),
            {"improved": True, "confidence": 0.85,
             "verdict": "la version nueva valida el resultado, mas fiable",
             "per_task": [{"better": "after", "why": "valida el resultado"}]},
        ], registro=peticiones)

        r = await comparison.compare_skill_change(
            skill_name="Hacer X", current_description="Haz X.",
            proposed_change="Valida el resultado antes de terminar.",
            sample_tasks=["haz X para el proyecto Cordyceps"])

        assert r is not None
        assert r["improved"] is True
        assert r["confidence"] == pytest.approx(0.85)
        assert len(r["per_task"]) == 1
        assert r["per_task"][0]["better"] == "after"
        assert r["candidate_models"] == ["ollama:llama3"]
        # las DOS versiones se compararon contra la MISMA tarea real
        peticion_juez = peticiones[-1]
        assert "haz X para el proyecto Cordyceps" in peticion_juez.prompt

    async def test_sin_mejora_real_el_juez_dice_que_no(self, monkeypatch):
        _secuencia(monkeypatch, [
            "antes", "despues, casi igual",
            {"improved": False, "confidence": 0.6,
             "verdict": "no hay diferencia real entre las dos versiones",
             "per_task": [{"better": "tie", "why": "igual de completo"}]},
        ])
        r = await comparison.compare_skill_change(
            skill_name="X", current_description="d", proposed_change="c",
            sample_tasks=["una tarea"])
        assert r is not None
        assert r["improved"] is False

    async def test_el_juez_excluye_a_los_modelos_candidatos(self, monkeypatch):
        """Anti-sesgo: quien genera las respuestas candidatas no es quien
        decide cuál es mejor (mismo principio que el juez de misiones)."""
        peticiones: list = []
        _secuencia(monkeypatch, [
            ("antes", "ollama:llama3"),
            ("despues", "anthropic:claude-opus-5"),
            {"improved": True, "confidence": 0.7, "verdict": "-",
             "per_task": [{"better": "after", "why": "-"}]},
        ], registro=peticiones)
        await comparison.compare_skill_change(
            skill_name="X", current_description="d", proposed_change="c",
            sample_tasks=["una tarea"])
        peticion_juez = peticiones[-1]
        assert set(peticion_juez.exclude) == {"ollama:llama3", "anthropic:claude-opus-5"}

    async def test_si_el_juez_no_responde_no_hay_veredicto(self, monkeypatch):
        """Ni "mejora" ni "no mejora": sin poder comprobarlo, sin veredicto —
        lo mecánico solo puede quitar confianza, nunca inventarla."""
        _secuencia(monkeypatch, ["antes", "despues", None])
        r = await comparison.compare_skill_change(
            skill_name="X", current_description="d", proposed_change="c",
            sample_tasks=["una tarea"])
        assert r is None

    async def test_si_ningun_candidato_se_genera_no_hay_veredicto(self, monkeypatch):
        _secuencia(monkeypatch, [None, None])
        r = await comparison.compare_skill_change(
            skill_name="X", current_description="d", proposed_change="c",
            sample_tasks=["una tarea"])
        assert r is None


# ===========================================================================
# 2 · LA CONSOLIDACIÓN NO PROPONE SIN PRUEBA DE MEJORA (integración)
# ===========================================================================
class TestMejorarSkillIntegracion:
    async def test_mejora_verificada_efectiva_se_crea_verificada(self, monkeypatch):
        sid = await _crear_skill()
        mid = _veredicto(goal="prepara el resumen semanal", tools=("document",))
        _secuencia(monkeypatch, [
            {"decisions": [{"action": "improve_skill", "skill_id": sid,
                            "change": "incluye siempre los bloqueos del proyecto",
                            "mission_ids": [mid], "why": "se olvida a veces"}]},
            "resumen sin la seccion de bloqueos",
            "resumen con la seccion de bloqueos del proyecto",
            {"improved": True, "confidence": 0.8, "verdict": "mas completo",
             "per_task": [{"better": "after", "why": "incluye bloqueos"}]},
        ])
        r = await consolidate()
        assert len(r["improved"]) == 1
        p = await proposal_service.get(r["improved"][0])
        assert p["kind"] == "skill_improve"
        assert p["payload"]["verified"] is True
        assert p["payload"]["comparison"]["improved"] is True
        assert p["payload"]["current_description"] == \
            "Prepara el resumen semanal de un proyecto."

    async def test_sin_mejora_real_no_se_propone_nada(self, monkeypatch):
        """"Incumbente que gana = sin propuesta" — el criterio de SE1, aplicado
        aquí en su forma segura de texto-contra-texto."""
        sid = await _crear_skill()
        mid = _veredicto(goal="prepara el resumen semanal", tools=("document",))
        _secuencia(monkeypatch, [
            {"decisions": [{"action": "improve_skill", "skill_id": sid,
                            "change": "cambia el tono", "mission_ids": [mid],
                            "why": "-"}]},
            "antes", "despues",
            {"improved": False, "confidence": 0.5, "verdict": "no hay diferencia",
             "per_task": [{"better": "tie", "why": "-"}]},
        ])
        r = await consolidate()
        assert r["improved"] == []

    async def test_sin_tareas_de_ejemplo_se_marca_sin_verificar_pero_se_propone(
            self, monkeypatch):
        """No proponer nada porque el banco de pruebas estaba ocupado sería
        peor que ser honesto sobre no haber podido comprobarlo — el usuario
        decide con esa información delante, nunca a ciegas."""
        sid = await _crear_skill()
        # una entrada real para que la consolidación llegue a preguntar, pero
        # con OTRO mission_id — el que la decisión cita no existe en por_mision.
        _veredicto(goal="algo sin relación", tools=("document",))
        _secuencia(monkeypatch, [
            {"decisions": [{"action": "improve_skill", "skill_id": sid,
                            "change": "cambia algo", "mission_ids": ["mision-fantasma"],
                            "why": "-"}]},
        ])
        r = await consolidate()
        assert len(r["improved"]) == 1
        p = await proposal_service.get(r["improved"][0])
        assert p["payload"]["verified"] is False
        assert p["payload"]["comparison"] is None

    async def test_una_skill_inexistente_no_produce_propuesta(self, monkeypatch):
        mid = _veredicto(goal="algo")
        _secuencia(monkeypatch, [
            {"decisions": [{"action": "improve_skill", "skill_id": "no-existe",
                            "change": "x", "mission_ids": [mid], "why": "-"}]},
        ])
        r = await consolidate()
        assert r["improved"] == []


# ===========================================================================
# 3 · RE-JUZGAR: NUNCA BORRA, ENLAZA — Y ALIMENTA LA CALIBRACIÓN
# ===========================================================================
class TestReJuzgarYCalibracion:
    async def test_rejudge_enlaza_el_anterior_sin_borrarlo(self, monkeypatch):
        m = _mision("actualiza el documento")
        _responde(monkeypatch, {"verdict": "unclear", "confidence": 0.4,
                                "reasons": "no estaba claro", "evidence": [],
                                "lesson": {"type": "none", "content": ""}})
        assert await judge.judge_mission(m.id)
        primero = judge.verdict_of(m.id)

        _responde(monkeypatch, {"verdict": "served", "confidence": 0.9,
                                "reasons": "en realidad si sirvio",
                                "evidence": ["outcome_text"],
                                "lesson": {"type": "none", "content": ""}})
        assert await judge.judge_mission(m.id, force=True)
        vigente = judge.verdict_of(m.id)
        assert vigente["verdict"] == "served"
        assert vigente["id"] != primero["id"]

        historia = judge.verdict_history(m.id)
        assert len(historia) == 2
        assert historia[0]["id"] == primero["id"]
        assert historia[0]["superseded_by"] == vigente["id"], (
            "el veredicto sustituido tiene que quedar enlazado al que lo sustituye")
        assert historia[1]["superseded_by"] is None

    async def test_sin_force_no_se_rejuzga(self, monkeypatch):
        m = _mision("algo")
        _responde(monkeypatch, {"verdict": "served", "confidence": 0.8,
                                "reasons": "-", "evidence": ["outcome_text"],
                                "lesson": {"type": "none", "content": ""}})
        assert await judge.judge_mission(m.id)
        assert await judge.judge_mission(m.id) is None, "juzgar es idempotente sin force"
        assert len(judge.verdict_history(m.id)) == 1

    async def test_calibracion_cuenta_rejuicios_que_cambian_de_veredicto(self, monkeypatch):
        m = _mision("algo")
        _responde(monkeypatch, {"verdict": "failed", "confidence": 0.3, "reasons": "-",
                                "evidence": [], "lesson": {"type": "none", "content": ""}})
        await judge.judge_mission(m.id)
        _responde(monkeypatch, {"verdict": "served", "confidence": 0.9, "reasons": "-",
                                "evidence": ["outcome_text"],
                                "lesson": {"type": "none", "content": ""}})
        await judge.judge_mission(m.id, force=True)

        cal = judge.calibration_summary()
        assert cal["rejudged"] == 1
        assert cal["rejudge_changed_verdict"] == 1
        assert cal["rejudge_confirmed"] == 0

    async def test_calibracion_cuenta_rejuicios_confirmados(self, monkeypatch):
        m = _mision("algo")
        _responde(monkeypatch, {"verdict": "served", "confidence": 0.8, "reasons": "-",
                                "evidence": ["outcome_text"],
                                "lesson": {"type": "none", "content": ""}})
        await judge.judge_mission(m.id)
        _responde(monkeypatch, {"verdict": "served", "confidence": 0.95, "reasons": "-",
                                "evidence": ["outcome_text"],
                                "lesson": {"type": "none", "content": ""}})
        await judge.judge_mission(m.id, force=True)

        cal = judge.calibration_summary()
        assert cal["rejudged"] == 1
        assert cal["rejudge_confirmed"] == 1
        assert cal["rejudge_changed_verdict"] == 0

    async def test_calibracion_cuenta_el_sesgo(self):
        with SessionLocal() as s:
            s.add(MissionVerdict(id=uuid.uuid4().hex, mission_id="m-sesgada",
                                 trace_id=None, origin="user", verdict="served",
                                 confidence=0.5, reasons="-", evidence=[],
                                 signals={}, lesson=None, judge_model="ollama:x",
                                 judge_bias=True, created_at=datetime.utcnow()))
            s.commit()
        cal = judge.calibration_summary()
        assert cal["biased_verdicts"] == 1
        assert cal["total_verdicts"] == 1
        assert cal["bias_rate"] == pytest.approx(1.0)

    def test_sin_veredictos_la_calibracion_no_rompe(self):
        cal = judge.calibration_summary()
        assert cal == {"total_verdicts": 0, "biased_verdicts": 0, "bias_rate": 0.0,
                       "rejudged": 0, "rejudge_changed_verdict": 0,
                       "rejudge_confirmed": 0}


# ===========================================================================
# 4 · EL APPLIER DE `skill_improve` — Aceptar cambia la skill, undo restaura
# ===========================================================================
class TestElApplierDeMejora:
    async def test_aceptar_una_mejora_cambia_la_descripcion(self, client):
        sid = await _crear_skill(descripcion="Version original.")
        pid = await proposal_service.create(
            kind="skill_improve", risk="medium", state="observed",
            title="Mejorar: Resumen semanal",
            payload={"skill_id": sid, "change": "Añade una sección de riesgos.",
                    "current_description": "Version original.",
                    "verified": True, "comparison": {"improved": True}},
            subject_id=sid)
        for i in range(3):
            await proposal_service.add_evidence(
                pid, {"kind": "judged_success", "context_key": f"m{i}"})

        r = client.post(f"/api/learner/proposals/{pid}/approve", json={"note": "si"})
        assert r.status_code == 200 and r.json()["state"] == "consolidated"

        skill = await skill_library.get(sid)
        assert "Añade una sección de riesgos." in skill.description
        assert "Version original." in skill.description

    async def test_deshacer_una_mejora_restaura_la_descripcion_previa(self, client):
        sid = await _crear_skill(descripcion="Version original.")
        pid = await proposal_service.create(
            kind="skill_improve", risk="medium", state="observed",
            title="Mejorar",
            payload={"skill_id": sid, "change": "cambio cualquiera",
                    "current_description": "Version original.",
                    "verified": False, "comparison": None},
            subject_id=sid)
        for i in range(3):
            await proposal_service.add_evidence(
                pid, {"kind": "judged_success", "context_key": f"m{i}"})
        client.post(f"/api/learner/proposals/{pid}/approve", json={})
        assert client.post(f"/api/learner/proposals/{pid}/undo").status_code == 200

        skill = await skill_library.get(sid)
        assert skill.description == "Version original."


# ===========================================================================
# 5 · LA CARA — lo que el usuario necesita para decidir, no a ciegas
# ===========================================================================
class TestLosEndpointsExponenLoNecesarioParaDecidir:
    async def test_una_skill_nueva_trae_su_descripcion_completa(self, client):
        """Sin esto no hay forma de decidir "Aceptar" salvo creerse el título:
        el usuario tiene que poder VER de qué va la skill antes de aprobarla."""
        pid = await proposal_service.create(
            kind="skill_new", risk="medium", state="candidate",
            title="Procedimiento: Resumen semanal",
            summary="Se ha hecho bien tres veces.",
            payload={"name": "Resumen semanal",
                    "description": "Lee las notas del proyecto y escribe un resumen.",
                    "definition": {"steps": ["leer notas", "escribir resumen"]},
                    "tools": ["document"], "grounded": True,
                    "grounding_note": "pasos anclados"})
        p = client.get("/api/learner/proposals").json()["proposals"][0]
        assert p["id"] == pid
        assert p["description"] == "Lee las notas del proyecto y escribe un resumen."
        assert p["grounded"] is True
        assert p["steps"] == ["leer notas", "escribir resumen"]

    async def test_una_mejora_de_skill_trae_la_comparacion_completa(self, client):
        """La mejora tiene que poder verse comparada con un clic: antes/después,
        veredicto por tarea, y si de verdad se pudo comprobar."""
        sid = await _crear_skill(descripcion="Descripción actual.")
        comparacion = {
            "improved": True, "confidence": 0.82,
            "verdict": "la version nueva es mas completa",
            "per_task": [{"task": "haz X", "better": "after", "why": "mas completo"}],
            "samples": [{"task": "haz X", "before": "texto antes",
                        "after": "texto despues"}],
            "candidate_models": ["ollama:llama3"],
        }
        pid = await proposal_service.create(
            kind="skill_improve", risk="medium", state="proposed",
            title="Mejorar: X", summary="motivo",
            payload={"skill_id": sid, "change": "el cambio propuesto",
                    "current_description": "Descripción actual.",
                    "verified": True, "comparison": comparacion},
            subject_id=sid)
        p = client.get("/api/learner/proposals").json()["proposals"][0]
        assert p["id"] == pid
        assert p["skill_id"] == sid
        assert p["change"] == "el cambio propuesto"
        assert p["current_description"] == "Descripción actual."
        assert p["verified"] is True
        assert p["comparison"]["improved"] is True
        assert p["comparison"]["samples"][0]["before"] == "texto antes"
        assert p["comparison"]["samples"][0]["after"] == "texto despues"

    async def test_una_mejora_sin_verificar_lo_dice_claramente(self, client):
        sid = await _crear_skill()
        pid = await proposal_service.create(
            kind="skill_improve", risk="medium", state="proposed",
            title="Mejorar: X",
            payload={"skill_id": sid, "change": "algo", "current_description": "d",
                    "verified": False, "comparison": None},
            subject_id=sid)
        p = client.get("/api/learner/proposals").json()["proposals"][0]
        assert p["id"] == pid
        assert p["verified"] is False
        assert p["comparison"] is None

    async def test_un_procedimiento_nuevo_no_lleva_campos_de_mejora(self, client):
        """Los campos de un `skill_improve` no se cuelan en un `skill_new`: el
        `verified`/`comparison` valen None cuando el kind no es de mejora."""
        await proposal_service.create(
            kind="skill_new", risk="medium", state="observed",
            title="Procedimiento: X",
            payload={"name": "X", "description": "d", "tools": []})
        p = client.get("/api/learner/proposals").json()["proposals"][0]
        assert p["verified"] is None
        assert p["comparison"] is None

    async def test_verdictos_en_bloque_para_pintar_mission_control(self, monkeypatch, client):
        m1 = _mision("primera")
        m2 = _mision("segunda")
        _responde(monkeypatch, {"verdict": "served", "confidence": 0.9,
                                "reasons": "bien", "evidence": ["outcome_text"],
                                "lesson": {"type": "none", "content": ""}})
        await judge.judge_mission(m1.id)

        data = client.get(f"/api/learner/verdicts?mission_ids={m1.id},{m2.id},sin-traza").json()
        veredictos = data["verdicts"]
        assert veredictos[m1.id]["verdict"] == "served"
        assert veredictos[m1.id]["verdict_label"] == "Sirvió"
        assert veredictos[m2.id] is None
        assert veredictos["sin-traza"] is None

    async def test_verdicto_de_una_mision_trae_las_razones_y_su_historia(
            self, monkeypatch, client):
        m = _mision("algo")
        _responde(monkeypatch, {"verdict": "partial", "confidence": 0.6,
                                "reasons": "solo parte de lo pedido",
                                "evidence": ["outcome_text"],
                                "lesson": {"type": "none", "content": ""}})
        await judge.judge_mission(m.id)

        data = client.get(f"/api/learner/verdicts/{m.id}").json()
        assert data["verdict"]["verdict"] == "partial"
        assert data["verdict"]["verdict_label"] == "Sirvió en parte"
        assert data["verdict"]["reasons"] == "solo parte de lo pedido"
        assert len(data["history"]) == 1

    async def test_mision_sin_juzgar_responde_vacio_sin_romper(self, client):
        data = client.get("/api/learner/verdicts/mision-cualquiera").json()
        assert data["verdict"] is None
        assert data["history"] == []

    async def test_rejuzgar_desde_el_endpoint_deja_rastro_recorrible(
            self, monkeypatch, client):
        m = _mision("algo")
        _responde(monkeypatch, {"verdict": "failed", "confidence": 0.3,
                                "reasons": "no funcionó", "evidence": [],
                                "lesson": {"type": "none", "content": ""}})
        await judge.judge_mission(m.id)

        _responde(monkeypatch, {"verdict": "served", "confidence": 0.9,
                                "reasons": "si funcionó, se me habia pasado",
                                "evidence": ["outcome_text"],
                                "lesson": {"type": "none", "content": ""}})
        r = client.post(f"/api/learner/verdicts/{m.id}/rejudge")
        assert r.status_code == 200
        assert r.json()["verdict"]["verdict"] == "served"

        data = client.get(f"/api/learner/verdicts/{m.id}").json()
        assert len(data["history"]) == 2
        assert data["history"][0]["verdict"] == "failed"
        assert data["history"][0]["superseded_by"] is not None
        assert data["history"][1]["verdict"] == "served"

    async def test_si_el_juez_no_responde_el_rejuicio_avisa_con_claridad(
            self, monkeypatch, client):
        m = _mision("algo")

        async def _falla(*a, **k):
            raise RuntimeError("sin proveedor disponible")
        monkeypatch.setattr("app.mel.complete", _falla)

        r = client.post(f"/api/learner/verdicts/{m.id}/rejudge")
        assert r.status_code == 409

    async def test_salud_trae_la_calibracion_del_juez(self, monkeypatch, client):
        m = _mision("algo")
        _responde(monkeypatch, {"verdict": "failed", "confidence": 0.3,
                                "reasons": "-", "evidence": [],
                                "lesson": {"type": "none", "content": ""}})
        await judge.judge_mission(m.id)
        _responde(monkeypatch, {"verdict": "served", "confidence": 0.9,
                                "reasons": "-", "evidence": ["outcome_text"],
                                "lesson": {"type": "none", "content": ""}})
        await judge.judge_mission(m.id, force=True)

        data = client.get("/api/learner/health").json()
        assert data["calibration"]["rejudged"] == 1
        assert data["calibration"]["rejudge_changed_verdict"] == 1

    async def test_salud_sin_datos_todavia_no_rompe(self, client):
        data = client.get("/api/learner/health").json()
        assert data["calibration"]["total_verdicts"] == 0
