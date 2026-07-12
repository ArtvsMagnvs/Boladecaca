# tests/test_memory_ingestion.py — Ingesta proactiva (V0.85 M2, doc 07 §6)
#
# No hay credenciales Google reales en el entorno de test: se fake-ea
# EmailTool.execute (list_inbox_preview) y google_auth.is_connected, tal como
# lo haria el Gmail real — así se verifica el pipeline completo (triaje cruzado,
# dedup_key, MemoryJobRun, evento memory.ingested) sin tocar la red.
# El calendario SI se prueba con datos reales de la BD local (CalendarEvent).
import pytest

from app.memory import ingestion
from app.memory.router import memory_router
from app.memory.memory_manager import memory_manager

pytestmark = pytest.mark.skipif(
    not memory_router.healthy, reason="ChromaDB no disponible en el entorno de test"
)


class _FakeEmailTool:
    """Reemplaza EmailTool: list_inbox_preview devuelve items fijos."""

    def __init__(self, items):
        self._items = items

    async def execute(self, action, params):
        assert action == "list_inbox_preview"
        return {"success": True, "result": {"count": len(self._items), "items": self._items}}


def _fake_items():
    return [
        {"id": "ing_test_1", "subject": "Factura de luz", "from": "luz@empresa.com",
         "date": "Mon, 1 Jan 2026", "snippet": "Tu factura de enero ya esta disponible", "unread": True},
        {"id": "ing_test_2", "subject": "Reunion de equipo", "from": "jefe@empresa.com",
         "date": "Mon, 1 Jan 2026", "snippet": "Quedamos manana a las 10", "unread": False},
    ]


@pytest.fixture(autouse=True)
def _cleanup_ingestion_items():
    yield
    import asyncio
    from app.memory import MemoryType

    async def _clean():
        await memory_router.forget(MemoryType.PERSONAL, {"source": "email"})
        await memory_router.forget(MemoryType.PERSONAL, {"source": "calendar"})

    asyncio.run(_clean())


@pytest.mark.anyio
async def test_ingest_email_indexa_y_cruza_triaje(monkeypatch):
    from app.db.database import SessionLocal
    from app.db.models import EmailTriage

    items = _fake_items()
    monkeypatch.setattr(ingestion.google_auth, "is_connected", lambda: True)
    monkeypatch.setattr(ingestion, "_email_tool", lambda: _FakeEmailTool(items))

    # ing_test_2 ya esta triado -> debe cruzarse (category != None) y emitir email.triaged
    db = SessionLocal()
    try:
        db.add(EmailTriage(email_id="ing_test_2", sender="jefe@empresa.com",
                            subject="Reunion de equipo", category="reunion", method="heuristic"))
        db.commit()
    finally:
        db.close()

    from app.core.events import Event, subscribe, unsubscribe
    triaged_events: list[Event] = []
    ingested_events: list[Event] = []

    async def on_triaged(ev):
        triaged_events.append(ev)

    async def on_ingested(ev):
        ingested_events.append(ev)

    subscribe("email.triaged", on_triaged)
    subscribe("memory.ingested", on_ingested)
    try:
        result = await ingestion.ingest_email()
        assert result["status"] == "ok"
        assert result["items_new"] == 2

        import asyncio
        await asyncio.sleep(0.05)  # los handlers corren en create_task

        assert len(ingested_events) == 1
        assert ingested_events[0].payload["items_new"] == 2
        assert len(triaged_events) == 1
        assert triaged_events[0].payload == {"email_id": "ing_test_2", "category": "reunion"}
    finally:
        unsubscribe("email.triaged", on_triaged)
        unsubscribe("memory.ingested", on_ingested)

    got1 = await memory_router.retrieve("mem_personal:ing_test_1")
    assert got1 is not None and "Factura de luz" in got1.content
    assert got1.metadata.get("category") is None  # no triado -> None (doc 07 §6)

    got2 = await memory_router.retrieve("mem_personal:ing_test_2")
    assert got2 is not None and got2.metadata.get("category") == "reunion"

    run = ingestion.last_run(ingestion.JOB_EMAIL)
    assert run is not None and run.status == "ok" and run.items_processed == 2


@pytest.mark.anyio
async def test_segunda_pasada_no_duplica(monkeypatch):
    items = _fake_items()
    monkeypatch.setattr(ingestion.google_auth, "is_connected", lambda: True)
    monkeypatch.setattr(ingestion, "_email_tool", lambda: _FakeEmailTool(items))

    col = memory_manager.get_or_create_collection("mem_personal")
    before = col.count()

    await ingestion.ingest_email()
    after_first = col.count()
    assert after_first - before == 2

    await ingestion.ingest_email()
    after_second = col.count()
    assert after_second == after_first, "la 2a pasada no debe anadir items nuevos (dedup_key)"


@pytest.mark.anyio
async def test_ingest_email_google_no_conectado_es_ok_sin_ruido(monkeypatch):
    monkeypatch.setattr(ingestion.google_auth, "is_connected", lambda: False)
    result = await ingestion.ingest_email()
    assert result == {"job": ingestion.JOB_EMAIL, "status": "ok", "items_new": 0, "reason": "google_not_connected"}


@pytest.mark.anyio
async def test_ingest_calendar_indexa_eventos_locales():
    from datetime import datetime, timedelta
    from app.db.database import SessionLocal
    from app.db.models import CalendarEvent

    db = SessionLocal()
    try:
        ev = CalendarEvent(
            title="Reunion Aithera M2",
            description="Cierre del sprint de ingesta",
            start_date=datetime.utcnow() + timedelta(days=1),
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)
        event_id = ev.id
    finally:
        db.close()

    try:
        result = await ingestion.ingest_calendar()
        assert result["status"] == "ok"
        assert result["items_new"] >= 1

        got = await memory_router.retrieve(f"mem_personal:cal:local:{event_id}")
        assert got is not None
        assert "Reunion Aithera M2" in got.content
        assert got.metadata.get("kind") == "agenda_item"
    finally:
        db = SessionLocal()
        try:
            db.query(CalendarEvent).filter(CalendarEvent.id == event_id).delete()
            db.commit()
        finally:
            db.close()


def test_endpoint_ingest_status(client):
    r = client.get("/api/memory/ingest/status")
    assert r.status_code == 200
    data = r.json()
    assert ingestion.JOB_EMAIL in data["jobs"]
    assert ingestion.JOB_CALENDAR in data["jobs"]
    assert "interval_min" in data["jobs"][ingestion.JOB_EMAIL]


def test_endpoint_ingest_run_calendar(client):
    r = client.post("/api/memory/ingest/run", params={"job": "calendar"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["job"] == ingestion.JOB_CALENDAR
