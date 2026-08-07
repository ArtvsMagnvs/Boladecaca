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

    async def test_el_analisis_1_ya_no_decide_nada(self, monkeypatch):
        """[V1.1 LC2, doc 41 §7] Contaba misiones con `state="done"` y, a las
        tres parecidas, dejaba una propuesta en la bandeja. Ese es el camino por
        el que ocho intentos FALLIDOS del mismo encargo acabaron propuestos como
        procedimiento (doc 41 §0).

        Se conserva la firma —el barrel la exporta— pero no crea nada: quién
        merece ser skill lo decide `consolidation.consolidate()` con los
        veredictos del juez delante. La agrupación por parecido sobrevive
        degradada a pre-agrupador, y su test sigue arriba (`_agrupa_por_trabajo`)
        porque agrupar es lo que hace bien."""
        monkeypatch.setattr("app.learner.analysis._misiones_recientes", lambda d: [
            _mision(f"m{i}", "prepárame el resumen semanal del proyecto Aithera")
            for i in range(5)])

        assert await analyze_repeated_missions() == []
        assert await proposal_service.pending(kind="skill_new") == [], (
            "contar repeticiones ya no llena la bandeja del usuario")


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
        # [LC2] Sin modelo no hay consolidación (aprender exige a la IA), pero
        # el resto de la pasada tiene que seguir su curso — que es lo que este
        # test defiende: los pasos son independientes.
        assert resumen["consolidation"] == {"created": [], "improved": [],
                                            "merged": 0, "dropped": 0,
                                            "config": [], "findings": []}
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
