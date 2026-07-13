# tests/test_memory_contracts.py — contratos del MOS (V0.85, sprint M1)
#
# Los tests de contrato SON la definicion ejecutable de la interfaz (08 RFC-006):
# cualquier IMemoryStore futuro (Qdrant, distribuido) debe pasar esta suite. Aqui
# cubren la unica implementacion de V0.85 (LocalMemoryStore) + el shape congelado.
#
# Parte 1 (siempre): el shape congelado (enums append-only, metodos abstractos,
#   dataclasses, linaje de skills, barrel publico).
# Parte 2 (si ChromaDB disponible): roundtrip real store/search/retrieve/context/
#   forget + idempotencia por dedup_key + skills.
# Parte 3 (siempre, SQL): decision_service escribe la tabla `decisions` con mission_id.

import pytest

from app.memory import (
    IMemoryStore,
    ISkillStore,
    LocalSkill,
    MemoryItem,
    MemoryQuery,
    MemoryType,
    SkillStatus,
    memory_router,
    skill_store,
)

_HEALTHY = memory_router.healthy
requires_chroma = pytest.mark.skipif(
    not _HEALTHY, reason="ChromaDB no disponible en el entorno de test"
)


# ======================================================================
# Parte 1 — Shape congelado (sin ChromaDB)
# ======================================================================

def test_memory_type_valores_congelados():
    """Invariante APPEND-ONLY: los valores son nombres de COLECCION, no pueden
    renombrarse (romperia los datos indexados) ni reordenarse."""
    assert MemoryType.CONVERSATIONAL.value == "mem_conversational"
    assert MemoryType.PERSONAL.value == "mem_personal"
    assert MemoryType.PROJECT.value == "mem_project"
    assert MemoryType.SKILL.value == "mem_skill"
    assert MemoryType.DECISION.value == "mem_decision"
    # Reservados (coleccion creada lazy; NO en V0.85 pero el contrato ya existe)
    assert MemoryType.EPISODIC.value == "mem_episodic"
    assert MemoryType.ERROR.value == "mem_error"
    assert MemoryType.TOOL.value == "mem_tool"
    assert MemoryType.AUTOMATION.value == "mem_automation"
    assert MemoryType.KNOWLEDGE.value == "mem_knowledge"
    assert MemoryType.WORKING.value == "mem_working"


def test_imemorystore_metodos_congelados():
    """La superficie de IMemoryStore son EXACTAMENTE estos 6 metodos."""
    assert IMemoryStore.__abstractmethods__ == frozenset(
        {"store", "search", "retrieve", "summarize", "forget", "context"}
    )


def test_iskillstore_metodos_congelados():
    assert ISkillStore.__abstractmethods__ == frozenset(
        {"create", "get", "list", "search", "improve", "validate", "publish", "execute"}
    )


def test_memory_item_shape():
    from datetime import datetime

    it = MemoryItem(
        id="mem_personal:x",
        content="hola",
        memory_type=MemoryType.PERSONAL,
        source="user",
        created_at=datetime.utcnow(),
    )
    assert it.metadata == {} and it.score is None
    with pytest.raises(Exception):  # frozen -> inmutable
        it.content = "otro"  # type: ignore[misc]


def test_memory_query_defaults():
    q = MemoryQuery(query="algo")
    assert q.top_k == 5 and q.max_tokens == 1500 and q.memory_types is None


def test_localskill_incluye_linaje_delta():
    """[Δ doc 14 §4.1] LocalSkill tiene los campos de linaje del Skill Evolution."""
    from datetime import datetime

    s = LocalSkill(
        id="s1", name="n", version="1.0.0", description="d",
        definition={}, input_schema={}, output_schema={}, runtime_agnostic=True,
        created_by="user", created_at=datetime.utcnow(),
    )
    assert s.derived_from == [] and s.superseded_by is None
    assert s.status == SkillStatus.DRAFT
    # los campos de linaje son mutables (el LLL los actualiza en V1.1)
    s.derived_from = ["madre"]
    s.superseded_by = "reemplazo"
    assert s.derived_from == ["madre"] and s.superseded_by == "reemplazo"


# ======================================================================
# Parte 2 — Roundtrip real (requiere ChromaDB)
# ======================================================================

@requires_chroma
@pytest.mark.anyio
async def test_store_search_retrieve_context_forget():
    dedup = "contract_roundtrip_key"
    item_id = await memory_router.store(
        content="al usuario le gustan las reuniones por la manana",
        memory_type=MemoryType.PERSONAL,
        source="test_contract",
        metadata={"kind": "preference"},
        dedup_key=dedup,
    )
    assert item_id == f"{MemoryType.PERSONAL.value}:{dedup}"

    # search encuentra el item
    results = await memory_router.search(
        "cuando prefiere reuniones", memory_types=[MemoryType.PERSONAL], top_k=5
    )
    assert any(r.id == item_id for r in results)
    hit = next(r for r in results if r.id == item_id)
    assert hit.source == "test_contract" and hit.score is not None

    # retrieve por id exacto
    got = await memory_router.retrieve(item_id)
    assert got is not None and "manana" in got.content

    # context con atribucion de fuente
    ctx = await memory_router.context(
        "reuniones", max_tokens=500, memory_types=[MemoryType.PERSONAL]
    )
    assert "test_contract" in ctx

    # cleanup + forget devuelve el nº borrado
    n = await memory_router.forget(MemoryType.PERSONAL, {"source": "test_contract"})
    assert n >= 1
    assert await memory_router.retrieve(item_id) is None


@requires_chroma
@pytest.mark.anyio
async def test_summarize_filtra_por_rango_de_fechas():
    """Regresion [V0.85 M3]: summarize() usaba where $gte/$lte sobre un string
    de fecha, y esta version de ChromaDB (1.5.x) solo admite $gte/$lte sobre
    numeros -> lanzaba ValueError en cuanto alguien lo llamaba de verdad. Se
    arreglo con $in sobre los dias enumerados; este test lo cubre para que no
    vuelva a colarse sin test."""
    from datetime import date, timedelta

    today = date.today()
    await memory_router.store(
        "elemento de hoy", MemoryType.PERSONAL, "test_contract_summarize", dedup_key="sum_today",
    )
    text = await memory_router.summarize(MemoryType.PERSONAL, today, today)
    assert "elemento de hoy" in text or "1 elementos" in text

    # Rango que NO incluye hoy -> vacio, sin lanzar.
    empty = await memory_router.summarize(
        MemoryType.PERSONAL, today - timedelta(days=30), today - timedelta(days=29)
    )
    assert empty == ""

    await memory_router.forget(MemoryType.PERSONAL, {"source": "test_contract_summarize"})


@requires_chroma
@pytest.mark.anyio
async def test_dedup_key_es_idempotente():
    """Dos store con el mismo dedup_key = 1 item (actualiza, no duplica)."""
    dedup = "idem_key"
    id1 = await memory_router.store("version A", MemoryType.PERSONAL, "test_contract", dedup_key=dedup)
    id2 = await memory_router.store("version B", MemoryType.PERSONAL, "test_contract", dedup_key=dedup)
    assert id1 == id2

    got = await memory_router.retrieve(id1)
    assert got is not None and got.content == "version B"  # se actualizo
    await memory_router.forget(MemoryType.PERSONAL, {"source": "test_contract"})


@requires_chroma
@pytest.mark.anyio
async def test_skill_store_preserva_linaje():
    from datetime import datetime

    skill = LocalSkill(
        id="skill_contract_1", name="resumir_pr", version="1.0.0",
        description="resume un pull request tecnico",
        definition={"prompt": "resume"}, input_schema={}, output_schema={},
        runtime_agnostic=True, created_by="user", created_at=datetime.utcnow(),
        tags=["git", "review"], derived_from=["skill_madre"], superseded_by=None,
    )
    sid = await skill_store.create(skill)
    assert sid == "skill_contract_1"

    got = await skill_store.get("skill_contract_1")
    assert got is not None
    assert got.derived_from == ["skill_madre"]
    assert got.tags == ["git", "review"]
    assert got.definition == {"prompt": "resume"}

    listed = await skill_store.list()
    assert any(s.id == "skill_contract_1" for s in listed)

    # execute sigue sin runtime -> NotImplementedError (no ejecuta 'a medias')
    with pytest.raises(NotImplementedError):
        await skill_store.execute("skill_contract_1", {})

    await memory_router.forget(MemoryType.SKILL, {"skill_id": "skill_contract_1"})


# ======================================================================
# Parte 3 — decision_service (SQL siempre; espejo best-effort)
# ======================================================================

@pytest.mark.anyio
async def test_decision_service_escribe_tabla_con_mission_id():
    from app.services import decision_service
    from app.db.database import SessionLocal
    from app.db.models import Decision

    decision = await decision_service.store_decision(
        title="Elegir Opcion B para el MOS",
        body="Arquitectura definitiva, implementacion minima",
        reason="Contratos de 10 años; deuda ≈ 0",
        alternatives=["A: Express", "C: ACI Full"],
        project="aithera",
        impact="high",
        mission_id="mission-xyz",
    )
    assert decision.id and decision.status == "active"
    assert decision.mission_id == "mission-xyz"

    # la fila existe de verdad en SQL (fuente de verdad)
    session = SessionLocal()
    try:
        row = session.get(Decision, decision.id)
        assert row is not None
        assert row.impact == "high"
        assert row.mission_id == "mission-xyz"
        assert '"A: Express"' in (row.alternatives or "")  # JSON string
        session.delete(row)
        session.commit()
    finally:
        session.close()
