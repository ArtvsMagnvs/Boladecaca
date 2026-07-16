# tests/test_lifecycle.py — MemoryLifecycleManager (V0.9 A2a, doc 08 RFC-007)
#
# El lifecycle BORRA memoria del usuario: los tests blindan las salvaguardas.
#   - dedup: items casi idénticos (sim>0.97) → uno se fusiona (borra), conserva
#     el de metadata más rica.
#   - prune: SOLO borra items viejos cuyo día YA tiene resumen; respeta pinned,
#     category=urgente y kind=daily_summary; NUNCA toca mem_decision/mem_skill.
#   - presupuesto: si la BD supera el presupuesto, aprieta la ventana HOT.
#   - cada pasada escribe un MemoryJobRun.
#
# Requiere ChromaDB sano (conftest hace initialize_sync a nivel de módulo). Si no,
# se saltan (igual que test_memory_contracts).
from datetime import date, timedelta

import pytest

from app.memory.lifecycle import lifecycle_manager
from app.memory.interfaces import MemoryType
from app.memory.memory_manager import memory_manager
from app.memory.stores.local_store import _collection_name
from app.db.database import SessionLocal
from app.db.models import MemoryJobRun

pytestmark = pytest.mark.skipif(
    not memory_manager.is_healthy(), reason="ChromaDB no disponible en el entorno de test"
)

OLD = (date.today() - timedelta(days=90)).isoformat()   # fuera de la ventana HOT (30d)
RECENT = date.today().isoformat()                        # dentro de la ventana HOT


def _col(mt: MemoryType):
    return memory_manager.get_or_create_collection(_collection_name(mt))


def _wipe(mt: MemoryType):
    """Deja la colección vacía para un test determinista (los tests son
    independientes; ChromaDB es un dir temporal de sesión)."""
    col = _col(mt)
    if col is None:
        return
    ids = (col.get() or {}).get("ids") or []
    if ids:
        col.delete(ids=ids)


def _add(mt: MemoryType, item_id: str, content: str, meta: dict):
    _col(mt).add(ids=[item_id], documents=[content], metadatas=[meta])


def _count(mt: MemoryType) -> int:
    col = _col(mt)
    return col.count() if col is not None else 0


def _ids(mt: MemoryType) -> set:
    col = _col(mt)
    return set((col.get() or {}).get("ids") or [])


@pytest.fixture(autouse=True)
def _clean_collections():
    for mt in (MemoryType.PERSONAL, MemoryType.CONVERSATIONAL, MemoryType.PROJECT, MemoryType.DECISION):
        _wipe(mt)
    yield
    for mt in (MemoryType.PERSONAL, MemoryType.CONVERSATIONAL, MemoryType.PROJECT, MemoryType.DECISION):
        _wipe(mt)


# ---------------------------------------------------------------------------
# dedup
# ---------------------------------------------------------------------------
def test_dedup_fusiona_casi_identicos_conservando_el_mas_rico():
    # dos items de CONTENIDO IDÉNTICO (sim = 1.0 ≥ 0.97) → uno se fusiona.
    _add(MemoryType.PERSONAL, "mem_personal:dup_rico", "reunión con el equipo el lunes",
         {"date": RECENT, "source": "email", "sender": "jefe@x.com", "category": "trabajo"})
    _add(MemoryType.PERSONAL, "mem_personal:dup_pobre", "reunión con el equipo el lunes",
         {"date": RECENT})

    merged = lifecycle_manager._dedup_type(MemoryType.PERSONAL)

    assert merged == 1
    ids = _ids(MemoryType.PERSONAL)
    assert "mem_personal:dup_rico" in ids   # el de metadata más rica sobrevive
    assert "mem_personal:dup_pobre" not in ids


def test_dedup_no_borra_items_distintos():
    _add(MemoryType.PERSONAL, "mem_personal:a", "comprar leche y pan", {"date": RECENT})
    _add(MemoryType.PERSONAL, "mem_personal:b", "informe trimestral de ventas Q3", {"date": RECENT})

    merged = lifecycle_manager._dedup_type(MemoryType.PERSONAL)

    assert merged == 0
    assert _count(MemoryType.PERSONAL) == 2


# ---------------------------------------------------------------------------
# prune + salvaguardas
# ---------------------------------------------------------------------------
def test_prune_borra_viejos_con_resumen_pero_respeta_pinned_y_resumen():
    # el día OLD tiene resumen → sus items crudos se pueden podar con seguridad
    _add(MemoryType.PERSONAL, "mem_personal:day:%s" % OLD, "resumen del día",
         {"date": OLD, "kind": "daily_summary"})
    # item crudo viejo normal → SE PODA
    _add(MemoryType.PERSONAL, "mem_personal:viejo_normal", "email cualquiera de hace meses",
         {"date": OLD, "source": "email"})
    # item crudo viejo PINNED → NO se poda
    _add(MemoryType.PERSONAL, "mem_personal:viejo_pinned", "algo importante fijado",
         {"date": OLD, "source": "email", "pinned": "true"})
    # item crudo viejo URGENTE → NO se poda
    _add(MemoryType.PERSONAL, "mem_personal:viejo_urgente", "email urgente",
         {"date": OLD, "source": "email", "category": "urgente"})
    # item reciente (dentro de HOT) → NO se poda aunque su día no tenga resumen
    _add(MemoryType.PERSONAL, "mem_personal:reciente", "email de hoy",
         {"date": RECENT, "source": "email"})

    pruned = lifecycle_manager._prune_all(hot_days=30)

    ids = _ids(MemoryType.PERSONAL)
    assert "mem_personal:viejo_normal" not in ids          # podado
    assert "mem_personal:viejo_pinned" in ids              # protegido (pinned)
    assert "mem_personal:viejo_urgente" in ids             # protegido (urgente)
    assert "mem_personal:day:%s" % OLD in ids              # el resumen NUNCA se poda
    assert "mem_personal:reciente" in ids                  # dentro de la ventana HOT
    assert pruned == 1


def test_prune_no_borra_viejos_sin_resumen():
    # día OLD SIN resumen → el item crudo NO se poda (sin resumen que preserve el
    # significado: la salvaguarda clave contra pérdida de datos).
    _add(MemoryType.PERSONAL, "mem_personal:huerfano", "email viejo sin resumen de su día",
         {"date": OLD, "source": "email"})

    pruned = lifecycle_manager._prune_all(hot_days=30)

    assert pruned == 0
    assert "mem_personal:huerfano" in _ids(MemoryType.PERSONAL)


# ---------------------------------------------------------------------------
# mem_decision / mem_skill NUNCA se compactan
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_mem_decision_nunca_se_toca():
    # dos decisiones idénticas + viejas: ni dedup ni prune deben tocarlas.
    _add(MemoryType.DECISION, "mem_decision:d1", "decidimos usar Postgres",
         {"date": OLD, "source": "decision"})
    _add(MemoryType.DECISION, "mem_decision:d2", "decidimos usar Postgres",
         {"date": OLD, "source": "decision"})

    result = await lifecycle_manager.run()

    assert result["status"] == "ok"
    assert _count(MemoryType.DECISION) == 2  # intactas: NEVER_COMPACT


# ---------------------------------------------------------------------------
# presupuesto
# ---------------------------------------------------------------------------
def test_presupuesto_aprieta_la_ventana(monkeypatch):
    # con la BD por debajo del presupuesto → ventana base (30d)
    monkeypatch.setattr(lifecycle_manager, "_chroma_size_mb", lambda: 100.0)
    assert lifecycle_manager._effective_hot_days(512) == 30

    # por encima del presupuesto → ventana apretada
    monkeypatch.setattr(lifecycle_manager, "_chroma_size_mb", lambda: 1000.0)
    assert lifecycle_manager._effective_hot_days(512) == 14   # over ≈1.95 → 14
    monkeypatch.setattr(lifecycle_manager, "_chroma_size_mb", lambda: 2000.0)
    assert lifecycle_manager._effective_hot_days(512) == 7    # over ≈3.9 → 7


# ---------------------------------------------------------------------------
# trazabilidad
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_escribe_memory_job_run():
    result = await lifecycle_manager.run()
    assert result["status"] == "ok"

    run = lifecycle_manager.last_run()
    assert run is not None
    assert run.job_name == "memory_lifecycle"
    assert run.status == "ok"
    assert run.finished_at is not None


@pytest.mark.anyio
async def test_run_emite_memory_compacted_cuando_hay_cambios(monkeypatch):
    import app.memory.lifecycle as lc_mod

    eventos = []
    monkeypatch.setattr(lc_mod, "emit", lambda name, source, payload: eventos.append((name, payload)))

    # prepara un dedup real (2 idénticos) para que la pasada tenga cambios
    _add(MemoryType.PERSONAL, "mem_personal:e1", "texto repetido idéntico", {"date": RECENT})
    _add(MemoryType.PERSONAL, "mem_personal:e2", "texto repetido idéntico", {"date": RECENT})

    await lifecycle_manager.run()

    names = [n for n, _ in eventos]
    assert "memory.compacted" in names
