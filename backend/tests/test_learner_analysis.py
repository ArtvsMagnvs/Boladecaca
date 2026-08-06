# tests/test_learner_analysis.py — V1.1 L3: el LLL en batch + "aprende esto"
#
# Un solo doble donde hace falta (la frontera del LLM y el accesor de lectura
# del TIE, para no depender de trazas de otra sesión); todo lo demás real:
# la cuarentena, la escalera, la biblioteca de skills, la BD de test.
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from app.db.database import Base, SessionLocal, engine
from app.learner import ladder, proposal_service, skill_library
from app.learner.analysis import (
    _agrupa_por_trabajo,
    _puntua,
    _titular,
    analyze_cross_project,
    analyze_repeated_missions,
    error_findings,
    last_report,
    recompute_skill_quality,
    run_nightly_analysis,
    weekly_learning_report,
)
from app.learner.models import FailureStat, LearnerProposal, Skill, SkillEvent

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _limpio():
    Base.metadata.create_all(bind=engine)

    def _borra():
        with SessionLocal() as s:
            for modelo in (SkillEvent, Skill, LearnerProposal, FailureStat):
                s.query(modelo).delete()
            s.commit()
    _borra()
    yield
    _borra()


def _mision(mid, goal, tools=("document",), project_id=None):
    return {"trace_id": f"t-{mid}", "mission_id": mid, "state": "done", "nodes": 2,
            "goal": goal, "tools": list(tools), "project_id": project_id,
            "created_at": datetime.utcnow().isoformat()}


class _Ev:
    """Doble mínimo de SkillEvent para probar la puntuación sin BD."""

    def __init__(self, event, dias=0, context_key=""):
        self.event = event
        self.created_at = datetime.utcnow() - timedelta(days=dias)
        self.payload = {"context_key": context_key} if context_key else {}


# ===========================================================================
# 1 · Análisis 1 — tareas repetidas
# ===========================================================================
class TestRepetidas:
    def test_agrupa_lo_que_es_el_mismo_trabajo(self):
        grupos = _agrupa_por_trabajo([
            _mision("a", "prepárame el resumen semanal del proyecto Aithera"),
            _mision("b", "quiero el resumen semanal para el proyecto Aithera"),
            _mision("c", "búscame vuelos baratos a Roma", tools=("search",)),
        ])
        assert len(grupos) == 2
        assert len(grupos[0]) == 2, "lo más repetido, primero"

    def test_las_mismas_palabras_con_OTRAS_herramientas_no_son_el_mismo_trabajo(self):
        """El procedimiento es parte de la identidad del trabajo: leer un
        informe del disco y buscarlo en la web no es lo mismo aunque se pida
        igual."""
        grupos = _agrupa_por_trabajo([
            _mision("a", "resumen semanal del proyecto Aithera", tools=("document",)),
            _mision("b", "resumen semanal del proyecto Aithera", tools=("search",)),
        ])
        assert len(grupos) == 2

    async def test_por_debajo_del_umbral_no_propone_nada(self, monkeypatch):
        """Dos veces es casualidad. La escalera de L1 manda también aquí."""
        monkeypatch.setattr("app.learner.analysis._misiones_recientes", lambda d: [
            _mision("m1", "prepárame el informe mensual de gastos"),
            _mision("m2", "quiero el informe mensual de gastos"),
        ])
        assert await analyze_repeated_missions() == []

    async def test_tres_entregas_de_la_MISMA_mision_cuentan_como_una(self, monkeypatch):
        """La protección contra rachas: el contexto es la misión, no la
        repetición. Sin esto, un reintento triple parecería un patrón."""
        monkeypatch.setattr("app.learner.analysis._misiones_recientes", lambda d: [
            _mision("m1", "prepárame el informe mensual de gastos"),
            _mision("m1", "prepárame el informe mensual de gastos"),
            _mision("m1", "prepárame el informe mensual de gastos"),
        ])
        assert await analyze_repeated_missions() == []

    async def test_no_duplica_lo_que_L2_ya_propuso(self, monkeypatch):
        """El análisis en batch y la acumulación por misión miran los mismos
        datos. Si crearan propuestas por separado, el usuario vería la misma
        cosa dos veces en la bandeja."""
        pid = await proposal_service.create(
            kind="skill_new", risk="medium", state="observed",
            title="ya existente",
            payload={"description": "prepárame el resumen semanal del proyecto Aithera",
                     "tools": ["document"], "name": "resumen"})
        monkeypatch.setattr("app.learner.analysis._misiones_recientes", lambda d: [
            _mision(f"m{i}", "quiero el resumen semanal del proyecto Aithera")
            for i in range(3)])

        ids = await analyze_repeated_missions()
        assert ids == [pid], "refuerza la que había, no crea otra"
        con_kind = await proposal_service.pending(kind="skill_new")
        assert len(con_kind) == 1
        assert len(con_kind[0]["evidence"]) == 3

    async def test_la_candidata_no_se_inventa_los_pasos(self, monkeypatch):
        """Nace SIN pasos a propósito: unos pasos redactados por un LLM que
        nadie ha visto funcionar son justo la fábrica de skills-basura que doc
        15 §10 teme. Los escribe el usuario al aceptarla, o ML2 (V1.2)."""
        monkeypatch.setattr("app.learner.analysis._misiones_recientes", lambda d: [
            _mision(f"m{i}", "prepárame el informe mensual de gastos") for i in range(3)])
        ids = await analyze_repeated_missions()
        prop = await proposal_service.get(ids[0])
        assert prop["payload"]["definition"]["steps"] == []
        assert prop["payload"]["tools"] == ["document"]

    async def test_una_pasada_vacia_no_rompe_ni_propone(self, monkeypatch):
        monkeypatch.setattr("app.learner.analysis._misiones_recientes", lambda d: [])
        assert await analyze_repeated_missions() == []

    async def test_si_el_tie_falla_el_analisis_no_lanza(self, monkeypatch):
        def _explota(_d):
            raise RuntimeError("BD caída")
        monkeypatch.setattr("app.learner.analysis._misiones_recientes", _explota)
        assert await analyze_repeated_missions() == []


# ===========================================================================
# 2 · Análisis 3 — el mismo trabajo en varios proyectos
# ===========================================================================
class TestInterProyecto:
    async def _con_proyectos(self, proyectos: list):
        pid = await proposal_service.create(
            kind="skill_new", risk="medium", state="observed",
            title="informe", payload={"name": "informe", "description": "informe",
                                      "tools": []}, project_id=proyectos[0])
        for i, proy in enumerate(proyectos):
            await proposal_service.add_evidence(pid, {
                "kind": "execution_ok", "context_key": f"m{i}",
                "payload": {"goal": "informe", "project_id": proy}})
        return pid

    async def test_un_trabajo_visto_en_dos_proyectos_deja_de_ser_de_uno(self):
        pid = await self._con_proyectos([7, 9])
        assert await analyze_cross_project() == [pid]
        prop = await proposal_service.get(pid)
        assert prop["payload"]["cross_project"] is True
        assert prop["payload"]["projects"] == [7, 9]
        assert prop["project_id"] is None

    async def test_un_solo_proyecto_no_se_toca(self):
        pid = await self._con_proyectos([7, 7])
        assert await analyze_cross_project() == []
        assert (await proposal_service.get(pid))["project_id"] == 7

    async def test_sin_proyecto_el_analisis_calla(self):
        """Las misiones del chat general no traen proyecto. La respuesta
        honesta ahí es no decir nada, no inventarse un alcance."""
        await self._con_proyectos([None, None])
        assert await analyze_cross_project() == []

    async def test_no_se_reescribe_una_propuesta_ya_decidida(self):
        pid = await self._con_proyectos([7, 9])
        await proposal_service.reject(pid, note="no me interesa")
        with pytest.raises(ValueError):
            await proposal_service.update_payload(pid, {"x": 1})


# ===========================================================================
# 3 · Análisis 4 — calidad de las skills
# ===========================================================================
class TestCalidad:
    def test_sin_historial_no_hay_nota(self):
        assert _puntua([], datetime.utcnow()) == (0.0, 0.0)

    def test_lo_reciente_pesa_mas_que_lo_viejo(self):
        """Una skill que funcionó hace medio año y nada desde entonces no vale
        lo mismo que una que funciona hoy: el mundo cambia y una skill puede
        quedarse obsoleta sin fallar nunca.

        ESTE TEST ENCONTRÓ UN FALLO DE DISEÑO real: la primera versión ponderaba
        por recencia dentro de una PROPORCIÓN, y con un único evento el peso se
        cancela consigo mismo (ratio 1.0 a cualquier edad). El decaimiento
        estaba escrito y no hacía nada."""
        ahora = datetime.utcnow()
        reciente, _ = _puntua([_Ev("executed_ok", dias=0, context_key="a")], ahora)
        viejo, _ = _puntua([_Ev("executed_ok", dias=180, context_key="a")], ahora)
        assert reciente > viejo
        assert viejo < reciente / 2, "medio año sin usarse tiene que notarse"

    def test_el_error_rate_es_la_proporcion_real(self):
        _, err = _puntua([_Ev("executed_ok"), _Ev("executed_ok"),
                          _Ev("executed_fail"), _Ev("executed_fail")],
                         datetime.utcnow())
        assert err == 0.5

    def test_funcionar_en_sitios_distintos_puntua_mas(self):
        ahora = datetime.utcnow()
        variada, _ = _puntua([_Ev("executed_ok", context_key=f"c{i}") for i in range(5)], ahora)
        monotona, _ = _puntua([_Ev("executed_ok", context_key="c0") for _ in range(5)], ahora)
        assert variada > monotona

    async def test_recalcula_sobre_skills_reales(self):
        from app.memory import LocalSkill, SkillStatus

        sk = LocalSkill(id=str(uuid.uuid4()), name="s", version="1.0.0",
                        description="d", definition={}, input_schema={},
                        output_schema={}, runtime_agnostic=True,
                        created_by="learner", created_at=datetime.utcnow(),
                        status=SkillStatus.DRAFT)
        await skill_library.create(sk)
        await skill_library.record_execution(sk.id, True, context_key="c1")
        await skill_library.record_execution(sk.id, False, context_key="c2")

        assert await recompute_skill_quality() >= 1
        with SessionLocal() as s:
            fila = s.get(Skill, sk.id)
        assert 0.0 < fila.quality_score < 1.0
        assert fila.error_rate == 0.5


# ===========================================================================
# 4 · Análisis 2 y 5 — hallazgos e informe semanal
# ===========================================================================
class TestInforme:
    def _fallo(self, kind, blame, component, n=5):
        from app.learner.stats import record_failures
        record_failures("m-1", [{"kind": kind, "blame": blame, "component": component,
                                 "model_key": None, "tool": None, "event_key": None,
                                 "detail": "algo"}] * n)

    def test_los_hallazgos_excluyen_lo_ya_accionable(self):
        """Lo de configuración YA tiene su propuesta (L2b) y lo que no es un
        fallo no es un hallazgo. Repetirlo aquí sería ruido."""
        self._fallo("config_missing", "config", "tool:search")
        self._fallo("permission_denied", "none", "tie:toolloop")
        self._fallo("model_reasoning", "model", "model:x:y")
        hallazgos = error_findings()
        assert [h["kind"] for h in hallazgos] == ["model_reasoning"]

    async def test_el_informe_sale_aunque_el_modelo_no_conteste(self, monkeypatch):
        """La autopsia es la guinda; el informe es determinista. Si el modelo
        de calidad no está, se entrega igual lo que sí se sabe."""
        async def _no_hay(*a, **k):
            raise RuntimeError("sin proveedor")
        monkeypatch.setattr("app.mel.complete", _no_hay)
        self._fallo("model_reasoning", "model", "model:x:y")

        informe = await weekly_learning_report(force=True)
        assert informe["findings"] == []
        assert informe["headline"].startswith("Esta semana")
        assert "counts" in informe and "failures_by_blame" in informe

    async def test_sin_fallos_no_se_paga_una_llamada_de_calidad(self, monkeypatch):
        """Pagar el modelo bueno para que diga "todo bien" es reflection
        theater (doc 15 §10)."""
        llamadas = []

        async def _cuenta(*a, **k):
            llamadas.append(1)
            raise RuntimeError("no debería llamarse")
        monkeypatch.setattr("app.mel.complete", _cuenta)

        await weekly_learning_report(force=True)
        assert llamadas == []

    async def test_un_hallazgo_sin_evidencia_se_descarta(self, monkeypatch):
        """Un diagnóstico que no se puede comprobar no es un diagnóstico
        (misma disciplina que el grounding)."""
        class _Res:
            ok = True
            text = ('{"findings": [{"title": "con pruebas", "why": "x", '
                    '"evidence": ["m-1"]}, {"title": "sin pruebas", "why": "y"}]}')

        async def _responde(*a, **k):
            return _Res()
        monkeypatch.setattr("app.mel.complete", _responde)
        self._fallo("model_reasoning", "model", "model:x:y")

        informe = await weekly_learning_report(force=True)
        assert [h["title"] for h in informe["findings"]] == ["con pruebas"]

    async def test_el_informe_se_guarda_y_no_se_repite_a_diario(self, monkeypatch):
        async def _nada(*a, **k):
            raise RuntimeError("sin modelo")
        monkeypatch.setattr("app.mel.complete", _nada)

        primero = await weekly_learning_report(force=True)
        assert last_report()["generated_at"] == primero["generated_at"]
        # Sin `force`, dentro de la misma semana devuelve el guardado.
        segundo = await weekly_learning_report()
        assert segundo["generated_at"] == primero["generated_at"]

    def test_el_titular_es_determinista(self):
        assert "nada nuevo" in _titular({}, {})
        t = _titular({"skills_nuevas": 2, "propuestas_abiertas": 1},
                     {"external": 3, "config": 1})
        assert "2 procedimiento(s)" in t and "4 fallo(s)" in t


# ===========================================================================
# 5 · La pasada nocturna completa
# ===========================================================================
class TestPasadaNocturna:
    async def test_un_analisis_roto_no_cancela_los_demas(self, monkeypatch):
        """Son independientes: perder los cuatro porque uno falló sería tonto."""
        async def _explota():
            raise RuntimeError("boom")
        monkeypatch.setattr("app.learner.analysis.analyze_cross_project", _explota)
        monkeypatch.setattr("app.learner.analysis._misiones_recientes", lambda d: [
            _mision(f"m{i}", "prepárame el informe mensual de gastos") for i in range(3)])

        async def _sin_modelo(*a, **k):
            raise RuntimeError("sin proveedor")
        monkeypatch.setattr("app.mel.complete", _sin_modelo)

        resumen = await run_nightly_analysis()
        assert resumen["repeated"], "el análisis 1 sí corrió"
        assert resumen["cross_project"] == [], "el roto devuelve vacío, no rompe"
        assert "report" in resumen


# ===========================================================================
# 6 · "Aprende esto" — la vía del usuario
# ===========================================================================
class TestAprendeEsto:
    def _modelo(self, monkeypatch, payload: str):
        class _Res:
            ok = True
            text = payload

        async def _responde(*a, **k):
            return _Res()
        monkeypatch.setattr("app.mel.complete", _responde)

    async def test_unas_notas_se_convierten_en_borrador(self, monkeypatch):
        from app.memory import SkillStatus

        self._modelo(monkeypatch, '{"name": "Cerrar el mes", "description": "cierre '
                                  'contable", "steps": ["exportar", "cuadrar", "archivar"], '
                                  '"tags": ["contabilidad"], "confident": true}')
        res = await learn("Para cerrar el mes exporto los movimientos, los cuadro "
                          "con el banco y archivo el PDF en la carpeta del año.")
        assert res.ok and res.skill_id
        skill = await skill_library.get(res.skill_id)
        assert skill.status == SkillStatus.DRAFT, "NUNCA nace activa"
        assert skill.created_by == "user_taught", "la provenance dice quién enseñó"
        assert len(skill.definition["steps"]) == 3

    async def test_lo_que_ensena_el_usuario_pasa_por_la_MISMA_puerta(self, monkeypatch):
        """Que lo pida el usuario no lo hace verdad: pide el TEMA, no certifica
        el RESULTADO — y lo que se guarda lo redacta un modelo."""
        self._modelo(monkeypatch, '{"name": "x", "description": "d", '
                                  '"steps": ["a"], "confident": true}')
        res = await learn("unas notas suficientemente largas para pasar el mínimo")
        skill = await skill_library.get(res.skill_id)
        assert skill.status.value == "draft"
        assert ladder.skill_can_transition("draft", "local") is False, (
            "no hay atajo de borrador a activa ni siquiera para lo que enseña el usuario")

    async def test_si_el_modelo_no_lo_ve_claro_no_se_guarda_nada(self, monkeypatch):
        """El modelo dice `confident: false` PERO entrega unos pasos igualmente
        —que es lo que hace de verdad: rellenar el hueco—. Tiene que rechazarse
        por la bandera, no por casualidad.

        La primera versión de este test mandaba `steps: []` junto al
        `confident: false`, así que lo rechazaba el OTRO guard y la
        comprobación de la bandera no se ejercitaba: la mutación que la
        desactivaba pasaba con los 33 tests en verde."""
        self._modelo(monkeypatch, '{"name": "Algo", "description": "d", '
                                  '"steps": ["paso inventado", "otro"], '
                                  '"confident": false}')
        res = await learn("algo vago pero con longitud suficiente para intentarlo")
        assert not res.ok and res.skill_id is None
        assert await skill_library.list() == [], (
            "nada a medias entra en la cuarentena, aunque traiga pasos")

    async def test_sin_pasos_concretos_tampoco(self, monkeypatch):
        self._modelo(monkeypatch, '{"name": "x", "steps": [], "confident": true}')
        res = await learn("unas notas suficientemente largas para pasar el mínimo")
        assert not res.ok

    async def test_dos_palabras_no_son_un_procedimiento(self):
        res = await learn("haz eso")
        assert not res.ok and "detalle" in res.message

    async def test_si_el_modelo_se_cae_responde_y_no_lanza(self, monkeypatch):
        async def _explota(*a, **k):
            raise RuntimeError("sin proveedor")
        monkeypatch.setattr("app.mel.complete", _explota)
        res = await learn("unas notas suficientemente largas para pasar el mínimo")
        assert not res.ok and res.message

    async def test_dentro_de_un_proyecto_nace_acotada(self, monkeypatch):
        self._modelo(monkeypatch, '{"name": "x", "description": "d", '
                                  '"steps": ["a"], "confident": true}')
        res = await learn("unas notas suficientemente largas para pasar el mínimo",
                          project_id=42)
        skill = await skill_library.get(res.skill_id)
        assert skill.projects == [42]

    async def test_la_accion_de_la_tool_esta_cableada(self, monkeypatch):
        """El cableado REAL: `aithera.learn_skill` ejecutándose de verdad. Lo
        contrario sería probar una función que nadie llama (la lección S9b)."""
        from app.tools.aithera_tool import AitheraTool

        self._modelo(monkeypatch, '{"name": "Cerrar el mes", "description": "d", '
                                  '"steps": ["a", "b"], "confident": true}')
        out = await AitheraTool().execute("learn_skill", {
            "notes": "para cerrar el mes exporto, cuadro y archivo el resultado",
            "source": "conversación"})
        assert out["success"] and out["result"]["skill_id"]
        skill = await skill_library.get(out["result"]["skill_id"])
        assert skill.definition["source"] == "conversación"

    async def test_learn_skill_hereda_el_proyecto_de_la_mision(self):
        """Igual que `create_agent`: el `project_id` lo pone el bucle desde la
        autoridad, no el modelo — esperar a que se acuerde sería confiar la
        frontera a su memoria."""
        from app.tie.toolloop import _AITHERA_PROJECT_SCOPED_CREATE

        assert "learn_skill" in _AITHERA_PROJECT_SCOPED_CREATE


async def learn(notas: str, **kw):
    from app.learner import learn_this

    return await learn_this(notas, **kw)
