# tests/test_lc2_consolidacion.py — EL APRENDIZAJE DE VERDAD (V1.1 LC2, doc 41)
#
# LC1 puso el juez: ahora consta si una misión SIRVIÓ. LC2 es lo que se hace con
# eso, y lo que estos tests defienden es el reparto de doc 41 §1:
#
#   lo mecánico EXTRAE y PROTEGE · la IA ENTIENDE y PROPONE · el usuario DECIDE
#
# Las tres mitades que se prueban aquí:
#   1. La escalera solo sube con evidencia JUZGADA (y lo del criterio viejo se
#      conserva pero no empuja).
#   2. La consolidación aprende de las DOS caras — de lo que funcionó sale un
#      procedimiento; de lo que falló, el porqué y, si se puede, el arreglo.
#   3. El grounding: los pasos de una skill salen de lo que de verdad se hizo,
#      no de lo que el modelo imagina que se hizo.
#
# UN SOLO DOBLE, la frontera del LLM (`app.mel.complete`) — patrón S4, doc 27
# §3. La cuarentena, la escalera, la biblioteca y la BD son las reales.
from __future__ import annotations

import json
import uuid
from datetime import datetime

import pytest

from app.db.database import Base, Config, SessionLocal, engine
from app.learner import ladder
from app.learner.consolidation import check_steps_grounded, consolidate
from app.learner.models import LearnerProposal, MissionVerdict, Skill, SkillEvent
from app.learner.proposals import proposal_service

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _mundo_limpio():
    # Importar los modelos ANTES de `create_all`: es lo que los registra en
    # `Base`. Sin esto, `mission_events` no existe y cualquier lectura de
    # telemetría revienta con "no such table" (lo cazó el último test de este
    # archivo, que ejercita `_learn` de verdad).
    import app.mel.models      # noqa: F401
    import app.telemetry.models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    def _borra():
        with SessionLocal() as s:
            for modelo in (SkillEvent, Skill, LearnerProposal, MissionVerdict):
                s.query(modelo).delete()
            s.query(Config).filter(Config.key.like("learner.%")).delete()
            s.commit()

    _borra()
    yield
    _borra()


def _responde(monkeypatch, payload, registro: list | None = None):
    class _Res:
        ok = True

        def __init__(self, texto):
            self.text = texto
            self.served_by = None

    texto = payload if isinstance(payload, str) else json.dumps(payload)

    async def _r(req, *a, **k):
        if registro is not None:
            registro.append(req)
        return _Res(texto)

    monkeypatch.setattr("app.mel.complete", _r)


def _veredicto(*, goal: str, verdict: str = "served", tools=("document",),
               lesson: dict | None = None, origin: str = "user",
               mission_id: str | None = None) -> str:
    """Un veredicto REAL en la tabla real — la entrada de la consolidación."""
    mid = mission_id or uuid.uuid4().hex
    with SessionLocal() as s:
        s.add(MissionVerdict(
            id=uuid.uuid4().hex, mission_id=mid, trace_id=None, origin=origin,
            verdict=verdict, confidence=0.9,
            reasons="motivo de prueba", evidence=["outcome_text"],
            signals={"goal": goal, "project_id": None,
                     "nodes": [{"id": "n1", "tools_used": list(tools)}],
                     "execution": {"problems": []}},
            lesson=lesson, judge_model="ollama:deepseek-r1:8b", judge_bias=False,
            created_at=datetime.utcnow()))
        s.commit()
    return mid


# ===========================================================================
# 1 · LA ESCALERA: solo sube lo JUZGADO
# ===========================================================================
class TestLaEscaleraDistingueTerminarDeServir:
    def test_lo_juzgado_util_empuja_y_lo_viejo_no(self):
        """El cambio de criterio, en la función pura. `execution_ok` era "la
        máquina terminó" — y con eso se propuso como procedimiento algo que
        fallaba (doc 41 §0)."""
        juzgadas = [{"kind": "judged_success", "context_key": f"m{i}"} for i in range(3)]
        viejas = [{"kind": "execution_ok", "context_key": f"v{i}"} for i in range(9)]

        assert ladder.can_be_candidate(juzgadas)[0] is True
        ok, motivo = ladder.can_be_candidate(viejas)
        assert ok is False
        assert "sin juzgar" in motivo, "el motivo tiene que explicar POR QUÉ no sube"

    def test_lo_viejo_se_conserva_para_poder_mirarlo(self):
        """No se borra: es historia auditable, y el panel puede decir cuántas
        misiones están esperando veredicto en vez de callarse."""
        viejas = [{"kind": "legacy_unjudged", "context_key": f"v{i}"} for i in range(4)]
        assert ladder.is_valid_evidence(viejas[0]) is True
        assert ladder.counts_for_promotion(viejas[0]) is False
        assert ladder.unjudged_in(viejas) == 4

    def test_un_fracaso_juzgado_es_evidencia_EN_CONTRA(self):
        """La otra mitad de "se aprende igual del error": un veredicto `failed`
        no es neutral respecto a convertir el trabajo en procedimiento — es un
        argumento en contra, y frena la auto-validación de riesgo bajo."""
        mezcla = ([{"kind": "judged_success", "context_key": f"m{i}"} for i in range(5)]
                  + [{"kind": "judged_failure", "context_key": "malo"}])
        assert ladder.contradictions_in(mezcla) == 1
        ok, motivo = ladder.can_validate("low", mezcla)
        assert ok is False and "contradicción" in motivo

    def test_riesgo_medio_cuenta_veredictos_no_ejecuciones(self):
        ok, _ = ladder.can_validate(
            "medium", [{"kind": "judged_success", "context_key": f"m{i}"} for i in range(3)])
        assert ok is True
        ok2, motivo = ladder.can_validate(
            "medium", [{"kind": "execution_ok", "context_key": f"m{i}"} for i in range(9)])
        assert ok2 is False and "sin juzgar" in motivo


# ===========================================================================
# 2 · EL GROUNDING: los pasos no se inventan
# ===========================================================================
class TestLosPasosSalenDeLoQuePaso:
    def test_pasos_anclados_se_aceptan(self):
        ok, _ = check_steps_grounded(
            ["leer el documento", "escribir el resumen"],
            ["document", "filesystem"], {"document", "filesystem"})
        assert ok is True

    def test_una_herramienta_declarada_que_nadie_uso_desancla(self):
        ok, motivo = check_steps_grounded(
            ["buscar en internet"], ["search"], {"document"})
        assert ok is False and "search" in motivo

    def test_un_paso_que_nombra_una_herramienta_no_usada_desancla(self):
        """El caso sutil: declarar solo lo correcto y colar la invención en el
        texto del paso. Se compara contra el repertorio OBSERVADO, no contra el
        catálogo del ToolManager — el Learner no importa `app.tools`."""
        ok, motivo = check_steps_grounded(
            ["abrir el navegador y usar browser para mirar la web"],
            ["document"], {"document"}, vocabulario={"document", "browser"})
        assert ok is False and "browser" in motivo

    def test_sin_herramientas_observadas_no_hay_procedimiento(self):
        ok, motivo = check_steps_grounded(["hacer algo"], [], set())
        assert ok is False and "ninguna herramienta" in motivo


# ===========================================================================
# 3 · LA CONSOLIDACIÓN: aprende de los ACIERTOS
# ===========================================================================
class TestAprendeDeLoQueFunciono:
    async def test_tres_misiones_utiles_producen_una_candidata_con_pasos_reales(
            self, monkeypatch):
        ids = [_veredicto(goal="prepara el resumen semanal del proyecto",
                          tools=("document", "filesystem")) for _ in range(3)]
        _responde(monkeypatch, {"decisions": [{
            "action": "create_skill",
            "name": "Resumen semanal",
            "description": "prepara el resumen semanal de un proyecto",
            "steps": ["leer las notas del proyecto", "escribir el resumen"],
            "tools": ["document", "filesystem"],
            "mission_ids": ids,
            "why": "se ha hecho bien tres veces"}]})

        r = await consolidate()
        assert len(r["created"]) == 1
        p = await proposal_service.get(r["created"][0])
        assert p["kind"] == "skill_new"
        assert p["state"] == "candidate", "3 misiones útiles distintas → candidata"
        assert p["payload"]["definition"]["steps"], "los pasos anclados se conservan"
        assert p["payload"]["grounded"] is True
        assert {e["kind"] for e in p["evidence"]} == {"judged_success"}

    async def test_los_pasos_inventados_se_tiran_pero_la_señal_se_queda(
            self, monkeypatch):
        """Degradar, no descartar: "esto se repite" sigue siendo cierto aunque
        "y se hace así" resulte ser una fantasía del modelo."""
        ids = [_veredicto(goal="prepara el resumen semanal", tools=("document",))
               for _ in range(3)]
        _responde(monkeypatch, {"decisions": [{
            "action": "create_skill", "name": "Resumen semanal",
            "description": "d",
            "steps": ["buscar en internet los datos"],
            "tools": ["search", "browser"],          # ← nadie las usó
            "mission_ids": ids, "why": "-"}]})

        r = await consolidate()
        p = await proposal_service.get(r["created"][0])
        assert p["payload"]["definition"]["steps"] == []
        assert p["payload"]["grounded"] is False
        assert "search" in p["payload"]["grounding_note"]
        assert p["state"] == "candidate", "la observación sobrevive sin los pasos"

    async def test_dos_misiones_no_bastan_aunque_la_ia_insista(self, monkeypatch):
        """La regla "una racha no es un patrón" (doc 15 §3.3) es política del
        SISTEMA, no una opinión que el modelo pueda saltarse."""
        ids = [_veredicto(goal="haz el informe") for _ in range(2)]
        _responde(monkeypatch, {"decisions": [{
            "action": "create_skill", "name": "Informe", "description": "d",
            "steps": [], "tools": ["document"], "mission_ids": ids, "why": "-"}]})
        r = await consolidate()
        assert r["created"] == []


# ===========================================================================
# 4 · LA CONSOLIDACIÓN: aprende de los ERRORES
# ===========================================================================
class TestAprendeDeLoQueFallo:
    async def test_los_fallos_llegan_a_la_ia_con_su_leccion(self, monkeypatch):
        """Que un fallo entre en el material de aprendizaje no es un detalle:
        es la mitad del contrato. Si la entrada no los lleva, no hay forma de
        aprender de ellos por muy bueno que sea el modelo."""
        _veredicto(goal="pon la canción de melendi", verdict="failed",
                   tools=("browser",),
                   lesson={"type": "error_pattern",
                           "content": "el navegador no reproduce audio del sistema"})
        peticiones: list = []
        _responde(monkeypatch, {"decisions": []}, registro=peticiones)

        await consolidate()
        assert peticiones, "no se llegó a preguntar a la IA"
        enviado = peticiones[0].prompt
        assert "melendi" in enviado.lower()
        assert "error_pattern" in enviado
        assert "no reproduce audio" in enviado

    async def test_de_un_fallo_sale_una_propuesta_de_configuracion(self, monkeypatch):
        """Un fallo entendido produce algo accionable. Sin applier a propósito:
        configurar es del usuario (misma disciplina que el `config_fix`
        determinista de L2b)."""
        _veredicto(goal="busca en internet el precio", verdict="failed",
                   tools=("search",),
                   lesson={"type": "system_weakness",
                           "content": "no hay API key de búsqueda"})
        _responde(monkeypatch, {"decisions": [{
            "action": "config_fix",
            "title": "Falta una API key de búsqueda web",
            "detail": "Añádela en Ajustes → Búsqueda web",
            "why": "3 misiones no pudieron buscar"}]})

        r = await consolidate()
        assert len(r["config"]) == 1
        p = await proposal_service.get(r["config"][0])
        assert p["kind"] == "config_fix"
        assert "API key" in p["title"]

    async def test_una_candidata_desmentida_se_retira(self, monkeypatch):
        """Aprender del error incluye DESAPRENDER: si lo que sostenía una
        propuesta resulta que no funcionaba, la propuesta se va — con motivo."""
        pid = await proposal_service.create(
            kind="skill_new", risk="medium", state="observed",
            title="Procedimiento: poner una canción")
        _veredicto(goal="pon la canción", verdict="failed")
        _responde(monkeypatch, {"decisions": [{
            "action": "drop_candidate", "proposal_id": pid,
            "why": "las misiones que la sostenían fallaron"}]})

        r = await consolidate()
        assert r["dropped"] == 1
        p = await proposal_service.get(pid)
        assert p["state"] == "rejected"
        assert "fallaron" in (p["decision_note"] or "")


# ===========================================================================
# 5 · CALIBRACIÓN Y CORPUS
# ===========================================================================
class TestCalibracionYCorpus:
    async def test_los_rechazos_del_usuario_viajan_en_el_prompt(self, monkeypatch):
        """"El usuario ya dijo que no a esto, y por qué" es información. Sin
        ella, el Learner vuelve a proponer lo mismo cada semana."""
        pid = await proposal_service.create(kind="skill_new", risk="medium",
                                            state="proposed",
                                            title="Resumen de los lunes")
        await proposal_service.reject(pid, note="no me sirve así, lo quiero por proyecto")
        _veredicto(goal="haz el resumen")

        peticiones: list = []
        _responde(monkeypatch, {"decisions": []}, registro=peticiones)
        await consolidate()
        enviado = peticiones[0].prompt
        assert "Resumen de los lunes" in enviado
        assert "lo quiero por proyecto" in enviado

    async def test_el_corpus_de_pruebas_no_entra_en_el_aprendizaje(self, monkeypatch):
        """Ningún sistema serio aprende de su propio banco de pruebas."""
        for _ in range(3):
            _veredicto(goal="test-campanya: abre una web", origin="test")
        peticiones: list = []
        _responde(monkeypatch, {"decisions": []}, registro=peticiones)
        r = await consolidate()
        assert peticiones == [], "se preguntó a la IA sobre corpus de pruebas"
        assert r["created"] == []

    async def test_dos_propuestas_que_son_lo_mismo_se_fusionan(self, monkeypatch):
        a = await proposal_service.create(kind="skill_new", risk="medium",
                                          state="observed", title="Resumen semanal")
        b = await proposal_service.create(kind="skill_new", risk="medium",
                                          state="observed", title="Resumen de la semana")
        await proposal_service.add_evidence(
            a, {"kind": "judged_success", "context_key": "m1"})
        await proposal_service.add_evidence(
            a, {"kind": "judged_success", "context_key": "m2"})
        await proposal_service.add_evidence(
            b, {"kind": "judged_success", "context_key": "m3"})
        _veredicto(goal="haz el resumen semanal")

        _responde(monkeypatch, {"decisions": [{
            "action": "merge_candidates", "proposal_ids": [a, b],
            "why": "son el mismo trabajo"}]})
        r = await consolidate()
        assert r["merged"] == 1
        ganadora = await proposal_service.get(a)
        perdedora = await proposal_service.get(b)
        assert perdedora["state"] == "rejected"
        assert len(ganadora["evidence"]) == 3, "la evidencia se conserva al fusionar"
        assert ganadora["state"] == "candidate", "y con 3 contextos ya es candidata"


# ===========================================================================
# 6 · EL SANEADO DE LO YA APRENDIDO (§6)
# ===========================================================================
class TestSaneadoDelCorpusContaminado:
    async def test_la_evidencia_vieja_se_reetiqueta_sin_borrarse(self):
        from app.learner import mark_legacy_evidence

        pid = await proposal_service.create(kind="skill_new", risk="medium",
                                            state="observed", title="vieja")
        for i in range(3):
            await proposal_service.add_evidence(
                pid, {"kind": "execution_ok", "context_key": f"m{i}"})

        assert mark_legacy_evidence() == 1
        p = await proposal_service.get(pid)
        assert len(p["evidence"]) == 3, "no se borra nada"
        assert {e["kind"] for e in p["evidence"]} == {"legacy_unjudged"}
        assert ladder.distinct_contexts(p["evidence"]) == 0

    async def test_es_idempotente(self):
        from app.learner import mark_legacy_evidence

        pid = await proposal_service.create(kind="skill_new", risk="medium",
                                            state="observed", title="vieja")
        await proposal_service.add_evidence(
            pid, {"kind": "execution_ok", "context_key": "m1"})
        assert mark_legacy_evidence() == 1
        assert mark_legacy_evidence() == 0

    async def test_una_propuesta_del_corpus_de_pruebas_se_retira_con_motivo(self):
        from app.learner import purge_test_corpus

        pid = await proposal_service.create(kind="skill_new", risk="medium",
                                            state="observed", title="de una campaña")
        for i in range(2):
            mid = _veredicto(goal="test-campanya", origin="test")
            await proposal_service.add_evidence(
                pid, {"kind": "judged_success", "context_key": mid})

        retiradas = await purge_test_corpus()
        assert pid in retiradas
        p = await proposal_service.get(pid)
        assert p["state"] == "rejected"
        assert "prueba" in (p["decision_note"] or "")

    async def test_una_propuesta_con_una_mision_real_de_verdad_sobrevive(self):
        """Retirar de más también es un error: basta UNA misión real que la
        sostenga para que la propuesta siga viva."""
        from app.learner import purge_test_corpus

        pid = await proposal_service.create(kind="skill_new", risk="medium",
                                            state="observed", title="mixta")
        m_test = _veredicto(goal="test-campanya", origin="test")
        m_real = _veredicto(goal="trabajo de verdad", origin="user")
        for mid in (m_test, m_real):
            await proposal_service.add_evidence(
                pid, {"kind": "judged_success", "context_key": mid})

        assert pid not in await purge_test_corpus()
        assert (await proposal_service.get(pid))["state"] != "rejected"

    async def test_sin_veredicto_no_se_acusa_a_nadie(self):
        """Una propuesta cuyas misiones aún no se han juzgado se queda quieta,
        no se retira: fail-closed también en la dirección de no destruir."""
        from app.learner import purge_test_corpus

        pid = await proposal_service.create(kind="skill_new", risk="medium",
                                            state="observed", title="sin juzgar")
        await proposal_service.add_evidence(
            pid, {"kind": "judged_success", "context_key": "mision-sin-veredicto"})
        _veredicto(goal="otra cosa cualquiera")     # para que haya veredictos

        assert pid not in await purge_test_corpus()


# ===========================================================================
# 7 · LO QUE SE RETIRÓ
# ===========================================================================
class TestLoMecanicoYaNoDecide:
    async def test_el_analisis_por_repeticion_ya_no_crea_nada(self):
        """Contaba `state="done"` y decidía. Se conserva la firma (el barrel la
        exporta) pero no propone: quien decide es la consolidación."""
        from app.learner import analyze_repeated_missions

        assert await analyze_repeated_missions(days=30) == []

    async def test_una_mision_terminada_ya_no_abre_propuesta_por_si_sola(
            self, monkeypatch):
        """La regresión que abre doc 41: terminar no puede seguir bastando para
        acabar en la bandeja del usuario."""
        from app.learner.mission_learning import _learn

        monkeypatch.setattr("app.learner.mission_learning._reflect",
                            lambda snap: _corutina({"reflection": "salió bien",
                                                    "repeatable": True,
                                                    "skill_name": "Algo",
                                                    "skill_steps": ["paso"]}))
        monkeypatch.setattr(
            "app.tie.tracer.mission_snapshot",
            lambda mid: {"mission_id": mid, "goal": "haz algo", "state": "done",
                         "nodes": [{"id": "n1", "tool_calls": [
                             {"tool": "document", "action": "read", "ok": True}]}]})

        antes = len(await proposal_service.pending(kind="skill_new"))
        await _learn("m-nueva", ok=True)
        assert len(await proposal_service.pending(kind="skill_new")) == antes


async def _corutina(valor):
    return valor
