# tests/test_learner_lsl.py — V1.1 L1: LSL completa + escalera de confianza.
#
# Capa 1-2 de la pirámide (doc 27 §3): unit de las reglas puras (ladder) +
# integración de SkillLibrary/ProposalService contra la BD REAL de test (SQLite
# vía create_all — mismo entorno que el resto de la suite). El espejo ChromaDB
# es best-effort y aquí ni se exige ni se mockea: si no está, la LSL funciona
# igual (ese ES el contrato del espejo).
#
# Los 4 contratos de PRODUCTO viven aparte en test_product_learner.py.
from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from app.db.database import Base, engine
from app.learner import ladder, proposal_service, skill_library
from app.learner.models import LearnerProposal, Skill, SkillEvent
from app.memory import LocalSkill, SkillStatus

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _tablas_limpias():
    """Tablas creadas y VACÍAS al entrar Y al salir (lección del bug de A4:
    `mission_events`/ids reciclados de otros archivos de test se colaban)."""
    Base.metadata.create_all(bind=engine)
    from app.db.database import SessionLocal

    def _limpia():
        with SessionLocal() as s:
            s.query(SkillEvent).delete()
            s.query(Skill).delete()
            s.query(LearnerProposal).delete()
            s.commit()
    _limpia()
    yield
    _limpia()


def _skill(**kw) -> LocalSkill:
    base = dict(
        id=str(uuid.uuid4()), name="Resumen semanal de proyecto",
        version="1.0.0", description="Genera el resumen semanal de un proyecto",
        definition={"steps": ["leer tareas", "redactar resumen"]},
        input_schema={"type": "object"}, output_schema={"type": "object"},
        runtime_agnostic=True, created_by="local_learning_loop",
        created_at=datetime.utcnow(), status=SkillStatus.DRAFT,
    )
    base.update(kw)
    return LocalSkill(**base)


def _ev(kind="judged_success", ctx=None):
    """[V1.1 LC2] El default pasa de `execution_ok` a `judged_success`.

    No es un ajuste cosmético del test: es el cambio de criterio de doc 41.
    `execution_ok` significaba "la máquina terminó sin colgarse" y con eso el
    Learner llegó a proponer como procedimiento ocho intentos fallidos;
    `judged_success` es el veredicto de un juez independiente sobre si la
    misión SIRVIÓ. Lo que estos tests comprueban (rachas, umbrales, rutas de
    riesgo) no cambia — cambia qué cuenta como evidencia."""
    return {"kind": kind, "context_key": ctx or str(uuid.uuid4()), "payload": {}}


# ===========================================================================
# 1 · La escalera (pura)
# ===========================================================================
class TestEscalera:
    def test_evidencia_sin_senal_externa_se_rechaza(self):
        """Anti-contaminación (doc 15 §3.3): 'el LLM dijo que salió bien' NO es
        evidencia — solo cuentan señales verificables desde fuera del modelo."""
        assert not ladder.is_valid_evidence({"kind": "llm_self_report", "context_key": "m1"})
        assert not ladder.is_valid_evidence({"kind": "judged_success"})       # sin contexto
        # [LC2] Y lo del criterio viejo se admite (es historia) pero no empuja:
        assert ladder.is_valid_evidence(_ev(kind="execution_ok"))
        assert not ladder.counts_for_promotion(_ev(kind="execution_ok"))
        assert not ladder.is_valid_evidence("no soy un dict")
        assert ladder.is_valid_evidence(_ev())

    def test_una_racha_en_el_mismo_contexto_cuenta_como_uno(self):
        """Tres éxitos en la MISMA misión = 1 contexto (doc 15 §3.3: 'una racha
        de suerte no es evidencia')."""
        evs = [_ev(ctx="mision-1"), _ev(ctx="mision-1"), _ev(ctx="mision-1")]
        assert ladder.distinct_contexts(evs) == 1
        ok, _ = ladder.can_be_candidate(evs)
        assert not ok
        evs += [_ev(ctx="mision-2"), _ev(ctx="mision-3")]
        ok, _ = ladder.can_be_candidate(evs)
        assert ok

    def test_riesgo_alto_solo_valida_el_usuario(self):
        """Doc 15 §3.2: ninguna cantidad de evidencia automática sustituye al
        HITL en riesgo alto."""
        muchas = [_ev(ctx=f"m{i}") for i in range(50)]
        ok, motivo = ladder.can_validate("high", muchas)
        assert not ok and "usuario" in motivo
        ok, _ = ladder.can_validate("high", muchas + [_ev("user_approval")])
        assert ok

    def test_riesgo_medio_3_ok_o_aprobacion(self):
        dos = [_ev(ctx="a"), _ev(ctx="b")]
        assert not ladder.can_validate("medium", dos)[0]
        assert ladder.can_validate("medium", dos + [_ev(ctx="c")])[0]
        assert ladder.can_validate("medium", [_ev("user_approval")])[0]

    def test_riesgo_bajo_una_contradiccion_para_la_auto_ruta(self):
        """Doc 15 §7.2: ante un conflicto se pregunta, no se asume."""
        cinco = [_ev(ctx=f"c{i}") for i in range(5)]
        assert ladder.can_validate("low", cinco)[0]
        ok, motivo = ladder.can_validate("low", cinco + [_ev("contradiction")])
        assert not ok and "contradicci" in motivo

    def test_riesgo_desconocido_es_fail_closed(self):
        assert not ladder.can_validate("yolo", [_ev("user_approval")])[0]

    def test_transiciones_ilegales_de_la_escalera(self):
        assert ladder.can_transition("observed", "candidate")
        assert not ladder.can_transition("observed", "validated")   # sin ascensor
        assert not ladder.can_transition("observed", "consolidated")
        assert not ladder.can_transition("rejected", "proposed")    # terminal
        assert ladder.can_transition("consolidated", "reverted")
        assert not ladder.can_transition("proposed", "reverted")    # nada que deshacer

    def test_ciclo_de_vida_de_skill_sin_atajos(self):
        assert ladder.skill_can_transition("draft", "validated")
        assert not ladder.skill_can_transition("draft", "local")    # DRAFT no salta a LOCAL
        assert ladder.skill_can_transition("validated", "local")
        assert not ladder.skill_can_transition("deprecated", "local")  # no resucita


# ===========================================================================
# 2 · SkillLibrary — SQL como fuente de verdad
# ===========================================================================
class TestSkillLibrary:
    async def test_create_get_roundtrip_completo(self):
        sk = _skill(tags=["email", "resumen"], derived_from=["padre-1"])
        await skill_library.create(sk)
        leida = await skill_library.get(sk.id)
        assert leida is not None
        assert leida.name == sk.name
        assert leida.definition == sk.definition
        assert leida.derived_from == ["padre-1"]        # el linaje sobrevive
        assert leida.status is SkillStatus.DRAFT

    async def test_create_es_idempotente_por_id(self):
        sk = _skill()
        await skill_library.create(sk)
        await skill_library.create(sk)                   # segunda vez: no duplica
        assert len(await skill_library.list()) == 1

    async def test_validar_sin_evidencia_se_rechaza_con_motivo(self):
        """EL corazón de la cuarentena de skills: DRAFT no sube a VALIDATED
        porque alguien lo pida — hacen falta 3 ejecuciones OK o el usuario."""
        sk = _skill()
        await skill_library.create(sk)
        with pytest.raises(ValueError, match="sin base para validar"):
            await skill_library.validate(sk.id, actor="learner")

    async def test_validar_con_3_ejecuciones_ok_reales(self):
        sk = _skill()
        await skill_library.create(sk)
        for i in range(3):
            await skill_library.record_execution(sk.id, True, context_key=f"m{i}")
        v = await skill_library.validate(sk.id, actor="learner")
        assert v.status is SkillStatus.VALIDATED

    async def test_el_usuario_valida_a_mano_sin_esperar_evidencia(self):
        sk = _skill()
        await skill_library.create(sk)
        v = await skill_library.validate(sk.id, actor="user")
        assert v.status is SkillStatus.VALIDATED

    async def test_record_execution_alimenta_las_metricas(self):
        sk = _skill()
        await skill_library.create(sk)
        await skill_library.record_execution(sk.id, True, context_key="a")
        await skill_library.record_execution(sk.id, False, context_key="b")
        s = await skill_library.get(sk.id)
        assert s.use_count == 2 and s.evidence_count == 1
        assert s.error_rate == pytest.approx(0.5)
        assert s.last_used is not None

    async def test_deprecate_nunca_borra_y_enlaza_el_reemplazo(self):
        vieja, nueva = _skill(name="v1"), _skill(name="v2")
        await skill_library.create(vieja)
        await skill_library.create(nueva)
        d = await skill_library.deprecate(vieja.id, superseded_by=nueva.id)
        assert d.status is SkillStatus.DEPRECATED
        assert d.superseded_by == nueva.id
        assert await skill_library.get(vieja.id) is not None    # sigue existiendo

    async def test_improve_no_puede_tocar_el_status(self):
        """La puerta de atrás que NO existe: cambiar el estado por improve()
        sería saltarse la cuarentena."""
        sk = _skill()
        await skill_library.create(sk)
        await skill_library.improve(sk.id, {"status": "local", "description": "mejor"})
        s = await skill_library.get(sk.id)
        assert s.status is SkillStatus.DRAFT             # intacto
        assert s.description == "mejor"                  # el contenido sí

    async def test_cada_mutacion_deja_su_evento_con_snapshot(self):
        sk = _skill()
        await skill_library.create(sk)
        await skill_library.improve(sk.id, {"description": "v2"})
        await skill_library.validate(sk.id, actor="user")
        h = await skill_library.history(sk.id)
        eventos = [e["event"] for e in h]
        assert eventos == ["validated", "improved", "created"]   # más reciente primero
        assert "prior" in h[0]["payload"] and "prior" in h[1]["payload"]

    async def test_snapshot_cubre_todas_las_columnas_mutables(self):
        """INVARIANTE (patrón test_migracion_columnas): si el modelo gana una
        columna y no entra en el snapshot, el undo restauraría a medias —
        este test lo caza en CI, no en producción."""
        from app.learner.library import _SNAPSHOT_FIELDS

        columnas = {c.name for c in Skill.__table__.columns}
        # Inmutables POR CONTRATO: la identidad (id), el nacimiento (created_at)
        # y la provenance (created_by) no cambian nunca — restaurarlas en un
        # undo no significa nada. Todo lo demás DEBE estar en el snapshot.
        inmutables = {"id", "created_at", "created_by"}
        assert columnas - inmutables == set(_SNAPSHOT_FIELDS), (
            "columnas del modelo fuera del snapshot de undo (o al revés)")

    async def test_search_degrada_a_sql_sin_chromadb(self):
        sk = _skill(name="Informe fiscal trimestral",
                    description="prepara el informe fiscal")
        await skill_library.create(sk)
        hits = await skill_library.search("fiscal", top_k=3)
        assert any(h.id == sk.id for h in hits)

    async def test_execute_sigue_cerrado_en_l1(self):
        with pytest.raises(NotImplementedError):
            await skill_library.execute("cualquiera", {})


# ===========================================================================
# 3 · ProposalService — la cuarentena general
# ===========================================================================
class TestCuarentena:
    async def test_no_se_nace_validado(self):
        with pytest.raises(ValueError, match="no puede nacer"):
            await proposal_service.create(kind="preference", title="x",
                                          state="validated")

    async def test_evidencia_basura_se_rechaza_en_la_puerta(self):
        pid = await proposal_service.create(kind="preference", title="x", risk="low")
        with pytest.raises(ValueError, match="señal EXTERNA"):
            await proposal_service.add_evidence(pid, {"kind": "llm_opinion",
                                                      "context_key": "m1"})

    async def test_observed_sube_a_candidate_con_min_rep_contextos(self):
        pid = await proposal_service.create(kind="preference", title="x", risk="low")
        for i in range(2):
            p = await proposal_service.add_evidence(pid, _ev(ctx=f"c{i}"))
            assert p["state"] == "observed"
        p = await proposal_service.add_evidence(pid, _ev(ctx="c2"))
        assert p["state"] == "candidate"

    async def test_riesgo_bajo_se_autovalida_con_5_y_sin_contradicciones(self):
        pid = await proposal_service.create(kind="preference", title="x",
                                            risk="low", state="proposed")
        for i in range(4):
            p = await proposal_service.add_evidence(pid, _ev("user_feedback", ctx=f"d{i}"))
            assert p["state"] == "proposed"
        p = await proposal_service.add_evidence(pid, _ev("user_feedback", ctx="d4"))
        assert p["state"] == "validated" and p["decided_by"] == "auto"

    async def test_una_contradiccion_detiene_la_autovalidacion(self):
        pid = await proposal_service.create(kind="preference", title="x",
                                            risk="low", state="proposed")
        await proposal_service.add_evidence(pid, _ev("contradiction", ctx="z"))
        for i in range(6):
            p = await proposal_service.add_evidence(pid, _ev("user_feedback", ctx=f"e{i}"))
        assert p["state"] == "proposed"                  # se queda esperando al usuario

    async def test_riesgo_alto_jamas_se_autovalida(self):
        pid = await proposal_service.create(kind="rule", title="regla sugerida",
                                            risk="high", state="proposed")
        for i in range(10):
            p = await proposal_service.add_evidence(pid, _ev(ctx=f"h{i}"))
        assert p["state"] == "proposed"
        p = await proposal_service.approve(pid, note="vale")
        assert p["state"] == "validated" and p["decided_by"] == "user"

    async def test_el_rechazo_se_registra_y_es_terminal(self):
        pid = await proposal_service.create(kind="rule", title="x",
                                            risk="high", state="proposed")
        p = await proposal_service.reject(pid, note="no me interesa")
        assert p["state"] == "rejected"
        assert p["decision_note"] == "no me interesa"    # el Learner aprende del no
        with pytest.raises(ValueError):
            await proposal_service.approve(pid)          # no resucita

    async def test_apply_solo_desde_validated(self):
        pid = await proposal_service.create(kind="skill_new", title="x",
                                            risk="medium", state="proposed")
        with pytest.raises(ValueError, match="puerta de atrás"):
            await proposal_service.apply(pid)

    async def test_apply_de_skill_new_crea_la_skill_en_draft(self):
        """El applier real de L1: consolidar una propuesta skill_new crea la
        skill — que nace en SU propia cuarentena (DRAFT), nunca validada."""
        pid = await proposal_service.create(
            kind="skill_new", title="skill de resúmenes", risk="medium",
            state="proposed",
            payload={"name": "Resumen de reuniones",
                     "description": "resume actas", "definition": {"steps": []}})
        p = await proposal_service.approve(pid)
        p = await proposal_service.apply(pid)
        assert p["state"] == "consolidated"
        skill_id = p["applied_snapshot"]["skill_id"]
        sk = await skill_library.get(skill_id)
        assert sk is not None and sk.status is SkillStatus.DRAFT

    async def test_registrar_dos_appliers_del_mismo_kind_revienta(self):
        from app.learner import register_applier

        async def _a(payload):
            return None
        with pytest.raises(ValueError, match="ya registrado"):
            register_applier("skill_new", _a)


# ===========================================================================
# 3b · La migración declara TODO lo que el ORM declara
# ===========================================================================
class TestMigracion:
    def test_la_migracion_cubre_todas_las_columnas_del_orm(self):
        """LA LECCIÓN DE LAS 4 VECES (W1, W2c, A1, 2026-08-02): el desfase
        ORM↔migración rompió la app en Postgres real cuatro veces porque SQLite
        (create_all) lo enmascara. Mismo invariante que test_migracion_columnas:
        cada columna de cada modelo del Learner aparece POR NOMBRE en la
        migración a8b9c0d1e2f3."""
        from pathlib import Path

        from app.learner.models import LearnerProposal, Skill, SkillEvent

        mig = (Path(__file__).resolve().parent.parent / "alembic" / "versions"
               / "a8b9c0d1e2f3_v11_learner_lsl.py").read_text(encoding="utf-8")
        for modelo in (Skill, SkillEvent, LearnerProposal):
            for col in modelo.__table__.columns:
                assert f'"{col.name}"' in mig, (
                    f"{modelo.__tablename__}.{col.name} está en el ORM pero NO "
                    f"en la migración — el desfase que rompió la app 4 veces")

    def test_la_cadena_de_revisiones_no_tiene_ramas(self):
        """Un solo head: la migración nueva encadena tras f7a8b9c0d1e2."""
        from pathlib import Path

        mig = (Path(__file__).resolve().parent.parent / "alembic" / "versions"
               / "a8b9c0d1e2f3_v11_learner_lsl.py").read_text(encoding="utf-8")
        assert 'down_revision: Union[str, None] = "f7a8b9c0d1e2"' in mig


# ===========================================================================
# 4 · Backfill mecánico (mem_skill → SQL)
# ===========================================================================
class TestBackfill:
    async def test_backfill_inserta_lo_que_falta_y_respeta_lo_que_esta(self, monkeypatch):
        """Con un doble del stub (ChromaDB no corre en CI): 2 skills legacy,
        1 ya migrada → solo entra la que falta, y la existente NO se pisa."""
        import app.learner.backfill as bf

        ya = _skill(name="ya migrada", description="version SQL")
        await skill_library.create(ya)
        legacy_version = _skill(id=ya.id, name="ya migrada",
                                description="version VIEJA de chroma")
        nueva = _skill(name="solo en chroma")

        class _FakeStub:
            async def list(self, status=None, tags=None):
                return [legacy_version, nueva]

        import app.memory as mem
        monkeypatch.setattr(mem, "skill_store", _FakeStub())

        n = await bf.backfill_from_mem_skill()
        assert n == 1
        migrada = await skill_library.get(nueva.id)
        assert migrada is not None and migrada.name == "solo en chroma"
        intacta = await skill_library.get(ya.id)
        assert intacta.description == "version SQL"      # SQL manda

    async def test_backfill_es_idempotente(self, monkeypatch):
        import app.learner.backfill as bf

        sk = _skill()

        class _FakeStub:
            async def list(self, status=None, tags=None):
                return [sk]

        import app.memory as mem
        monkeypatch.setattr(mem, "skill_store", _FakeStub())
        assert await bf.backfill_from_mem_skill() == 1
        assert await bf.backfill_from_mem_skill() == 0   # segunda pasada: nada

    async def test_sin_chromadb_no_es_un_error(self, monkeypatch):
        import app.learner.backfill as bf

        class _Roto:
            async def list(self, status=None, tags=None):
                raise RuntimeError("chroma caido")

        import app.memory as mem
        monkeypatch.setattr(mem, "skill_store", _Roto())
        assert await bf.backfill_from_mem_skill() == 0   # degrada, no revienta
