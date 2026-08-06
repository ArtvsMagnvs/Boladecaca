# tests/test_product_learner.py — CONTRATOS DE PRODUCTO de la fase V1.1 (Learner)
#
# [doc 27 §3, regla de la primera sesión] Estos 4 contratos se escriben en L1 y
# son LA DEFINICIÓN EJECUTABLE del cierre de fase: V1.1 no se cierra hasta que
# los 4 estén en verde SIN marcas.
#
# Estado al escribirse (L1):
#   1. misión repetida 3+ → skill DRAFT ........ EN ROJO (xfail estricto: lo
#      implementan L2/L3; cuando pase, el xfail REVIENTA la suite y obliga a
#      quitar la marca en la misma sesión que lo implemente — el flip es un
#      acto deliberado, no una casualidad)
#   2. nada se aplica sin evidencia/aprobación .. VERDE (la escalera de L1)
#   3. undo restaura el estado anterior ......... VERDE (snapshots de L1)
#   4. el Learner jamás escribe fuera ........... VERDE (frontera estática +
#      diff de BD en un apply real)
#
# Patrón S4: un solo fake como mucho (la frontera del LLM — aquí ninguno hace
# falta), BD real de test, servicios reales.
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
        id=str(uuid.uuid4()), name="skill de contrato", version="1.0.0",
        description="skill para contratos de producto",
        definition={"steps": ["a"]}, input_schema={}, output_schema={},
        runtime_agnostic=True, created_by="local_learning_loop",
        created_at=datetime.utcnow(), status=SkillStatus.DRAFT,
    )
    base.update(kw)
    return LocalSkill(**base)


# ===========================================================================
# CONTRATO 1 — "una misión repetida 3+ veces produce una skill DRAFT"
# ===========================================================================
async def test_contrato_1_mision_repetida_3_veces_produce_skill_draft(monkeypatch):
    """El usuario pide lo mismo tres veces en contextos distintos → el Learner
    lo nota y una skill candidata aparece en su cuarentena, sin que nadie se lo
    pida.

    [L3, 2026-08-06] EN VERDE. El xfail estricto de L1 hizo su trabajo: al
    implementarse `analyze_repeated_missions` dejó de lanzar y la suite obligó
    a venir aquí a retirar la marca — el flip es un acto deliberado, como se
    escribió.

    Se siembran tres MISIONES reales (el mismo encargo redactado de tres formas
    distintas, como lo diría una persona) y se deja que el análisis las
    agrupe. Único doble: el accesor de lectura del TIE, para no depender de que
    haya trazas de otra sesión en la BD de test."""
    from app.learner import analyze_repeated_missions

    misiones = [
        {"trace_id": "t1", "mission_id": "m1", "state": "done", "nodes": 2,
         "goal": "prepárame el resumen semanal del proyecto Aithera",
         "tools": ["document", "filesystem"], "project_id": None},
        {"trace_id": "t2", "mission_id": "m2", "state": "done", "nodes": 2,
         "goal": "quiero el resumen semanal para el proyecto Aithera, por favor",
         "tools": ["document", "filesystem"], "project_id": None},
        {"trace_id": "t3", "mission_id": "m3", "state": "done", "nodes": 2,
         "goal": "hazme el resumen semanal del proyecto Aithera",
         "tools": ["document", "filesystem"], "project_id": None},
    ]
    monkeypatch.setattr("app.learner.analysis._misiones_recientes",
                        lambda days: misiones)

    ids = await analyze_repeated_missions(days=30)
    assert ids, "el análisis debe crear al menos una propuesta skill_new"
    prop = await proposal_service.get(ids[0])
    assert prop["kind"] == "skill_new"
    assert prop["state"] in ("candidate", "proposed")   # jamás nace validada
    assert len(prop["evidence"]) == 3, "una evidencia por contexto distinto"


# ===========================================================================
# CONTRATO 2 — "ninguna propuesta del Learner se aplica sin evidencia o aprobación"
# ===========================================================================
async def test_contrato_2_nada_se_aplica_sin_evidencia_ni_aprobacion():
    """Las tres puertas, cerradas: (a) una skill no se valida sin 3 ejecuciones
    OK reales o el usuario; (b) una propuesta de riesgo alto no se valida ni
    con 50 evidencias automáticas; (c) apply() sin pasar por validated lanza."""
    # (a) skill
    sk = _skill()
    await skill_library.create(sk)
    with pytest.raises(ValueError):
        await skill_library.validate(sk.id, actor="learner")

    # (b) riesgo alto: solo HITL
    pid = await proposal_service.create(kind="rule", title="regla sugerida",
                                        risk="high", state="proposed")
    for i in range(50):
        p = await proposal_service.add_evidence(
            pid, {"kind": "execution_ok", "context_key": f"m{i}", "payload": {}})
    assert p["state"] == "proposed", "riesgo alto se autovalidó: violación del HITL"

    # (c) la cuarentena no tiene puerta de atrás
    with pytest.raises(ValueError):
        await proposal_service.apply(pid)


async def test_contrato_2b_la_evidencia_del_propio_llm_no_cuenta():
    """Anti-contaminación (doc 15 §3.3): el bucle de retroalimentación que
    refuerza sus propios errores está cerrado EN LA PUERTA."""
    pid = await proposal_service.create(kind="preference", title="x", risk="low")
    with pytest.raises(ValueError):
        await proposal_service.add_evidence(
            pid, {"kind": "llm_self_report", "context_key": "m1", "payload": {}})


# ===========================================================================
# CONTRATO 3 — "undo restaura el estado anterior"
# ===========================================================================
async def test_contrato_3_undo_de_skill_restaura_el_estado_exacto():
    sk = _skill(description="original", quality_score=0.4)
    await skill_library.create(sk)
    antes = await skill_library.get(sk.id)

    await skill_library.improve(sk.id, {"description": "cambiada",
                                        "quality_score": 0.9})
    tras = await skill_library.undo_last(sk.id)

    assert tras.description == antes.description == "original"
    assert tras.quality_score == pytest.approx(0.4)
    # y el undo es HISTORIA, no una goma de borrar:
    eventos = [e["event"] for e in await skill_library.history(sk.id)]
    assert eventos[0] == "reverted" and "improved" in eventos


async def test_contrato_3b_undo_de_una_propuesta_consolidada():
    """Consolidar skill_new crea la skill; deshacerlo la retira (deprecate —
    nunca borra) y la propuesta queda `reverted` con su rastro."""
    pid = await proposal_service.create(
        kind="skill_new", title="skill nueva", risk="medium", state="proposed",
        payload={"name": "Skill reversible", "description": "d",
                 "definition": {}})
    await proposal_service.approve(pid)
    aplicada = await proposal_service.apply(pid)
    skill_id = aplicada["applied_snapshot"]["skill_id"]
    assert (await skill_library.get(skill_id)).status is SkillStatus.DRAFT

    deshecha = await proposal_service.undo(pid)
    assert deshecha["state"] == "reverted"
    sk = await skill_library.get(skill_id)
    assert sk is not None                                # nunca se borra
    assert sk.status is SkillStatus.DEPRECATED           # pero está retirada


# ===========================================================================
# CONTRATO 4 — "el Learner jamás escribe fuera de sus tablas/colecciones"
# ===========================================================================
_TABLAS_DEL_LEARNER = {"skills", "skill_events", "learner_proposals",
                       "model_stats", "tool_stats"}

# Módulos que el Learner tiene PROHIBIDO importar (doc 15 §10: 'no importa
# gateway/ai directo; escribe únicamente por APIs MOS/Skill'). Lo que NO está
# aquí y es deliberado: `app.memory` (API pública del MOS), `app.mel`
# (capability ANALYZE es la vía pública correcta al LLM, L2), `app.telemetry`
# (solo lectura de lo que el sistema ya mide) y `app.services.decision_service`
# (la Decision API es una de las dos APIs por las que el Learner SÍ escribe).
_IMPORTS_PROHIBIDOS = (
    "app.gateway", "app.ai", "app.tools", "app.agents", "app.workspace",
    "app.orchestrator", "app.automation", "app.voice",
    "app.integrations", "app.db.models",
)

# [L2] `app.tie` es un caso aparte y merece su propia regla, más precisa que un
# veto en bloque. Las trazas del TIE son la FUENTE DE APRENDIZAJE nº 1 (doc 15
# §2), así que prohibirlas entero habría dejado al Learner sin su materia prima.
# Lo que la regla constitucional protege no es "no mirar al TIE": es que el
# Learner NUNCA planifique ni ejecute. Así que se permite el barrel y SOLO estos
# dos símbolos de lectura pura — cualquier otro (handle, submit_mission,
# executor, pipeline...) significaría que el Learner ha empezado a actuar.
_TIE_LECTURA_PERMITIDA = {"tracer", "extract_json"}


def test_contrato_4_frontera_estatica_de_imports():
    """El Learner no puede escribir donde no puede LLEGAR: ninguno de sus
    archivos importa módulos de ejecución/negocio ajenos. Es la mitad
    estructural de la regla constitucional (doc 15)."""
    from pathlib import Path

    learner_dir = Path(__file__).resolve().parent.parent / "app" / "learner"
    ofensas = []
    for f in sorted(learner_dir.glob("*.py")):
        texto = f.read_text(encoding="utf-8")
        for linea in texto.splitlines():
            limpio = linea.strip()
            if not (limpio.startswith("import ") or limpio.startswith("from ")):
                continue
            for prohibido in _IMPORTS_PROHIBIDOS:
                if f"{prohibido}." in limpio or limpio.endswith(prohibido) \
                   or f"{prohibido} " in limpio:
                    ofensas.append(f"{f.name}: {limpio}")
    assert not ofensas, f"el Learner importa módulos prohibidos: {ofensas}"


def test_contrato_4a_del_tie_solo_se_lee():
    """El Learner mira las trazas del TIE (su fuente nº 1) pero jamás toca nada
    que planifique o ejecute. Si mañana alguien importa `submit_mission` aquí
    'para reintentar una misión fallida', el Learner habría dejado de ser un
    observador — y este test lo dice antes de que llegue a producción."""
    import re
    from pathlib import Path

    learner_dir = Path(__file__).resolve().parent.parent / "app" / "learner"
    ofensas = []
    for f in sorted(learner_dir.glob("*.py")):
        for linea in f.read_text(encoding="utf-8").splitlines():
            limpio = linea.split("#", 1)[0].strip()   # sin el comentario de la línea
            if not (limpio.startswith("import ") or limpio.startswith("from ")):
                continue
            # Los internos del TIE están vetados sin excepción (doc 16).
            if re.search(r"\b(from|import)\s+app\.tie\.", limpio):
                ofensas.append(f"{f.name}: interno del TIE → {limpio}")
                continue
            m = re.match(r"from\s+app\.tie\s+import\s+(.+)$", limpio)
            if m:
                simbolos = {s.strip().split(" as ")[0].strip()
                            for s in m.group(1).split(",")}
                extra = simbolos - _TIE_LECTURA_PERMITIDA
                if extra:
                    ofensas.append(f"{f.name}: {sorted(extra)} no es lectura pura")
    assert not ofensas, (
        "el Learner usa el TIE para algo más que leer:\n" + "\n".join(ofensas))


async def test_contrato_4b_un_apply_real_solo_toca_tablas_del_learner():
    """La mitad DINÁMICA: se consolida una propuesta real y se comparan los
    conteos de TODAS las tablas antes/después — solo las del Learner cambian.
    (mem_skill es colección ChromaDB, no tabla: su espejo es best-effort y
    está fuera de este diff por construcción.)"""
    from app.db.database import SessionLocal
    from sqlalchemy import text

    def _conteos() -> dict:
        with SessionLocal() as s:
            out = {}
            for nombre in Base.metadata.tables:
                try:
                    out[nombre] = s.execute(
                        text(f'SELECT COUNT(*) FROM "{nombre}"')).scalar()
                except Exception:
                    out[nombre] = None       # tabla aún no creada: igual a ambos lados
            return out

    antes = _conteos()
    pid = await proposal_service.create(
        kind="skill_new", title="skill frontera", risk="medium", state="proposed",
        payload={"name": "Skill frontera", "description": "d", "definition": {}})
    await proposal_service.approve(pid)
    await proposal_service.apply(pid)
    despues = _conteos()

    cambiadas = {t for t in antes
                 if antes[t] is not None and antes[t] != despues.get(t)}
    fuera = cambiadas - _TABLAS_DEL_LEARNER
    assert not fuera, f"el Learner escribió fuera de sus tablas: {sorted(fuera)}"
    assert "skills" in cambiadas             # y dentro SÍ escribió de verdad
