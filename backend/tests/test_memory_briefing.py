# tests/test_memory_briefing.py — Resumen nocturno + Briefing (V0.85 M3)
#
# Cierre de fase (doc 07, criterio de cierre de V0.85): "¿qué me ha llegado
# importante hoy?" debe responder desde memoria local, con Gmail DESCONECTADO.
# test_criterio_de_cierre_briefing_sin_google lo verifica explicitamente.
from datetime import date, datetime, timedelta

import pytest

from app.memory import MemoryType, memory_router
from app.memory import summarizer

pytestmark = pytest.mark.skipif(
    not memory_router.healthy, reason="ChromaDB no disponible en el entorno de test"
)

TODAY = datetime.utcnow().date()


def _seed_triage(db, email_id, sender, subject, category):
    from app.db.models import EmailTriage

    db.add(EmailTriage(email_id=email_id, sender=sender, subject=subject, category=category))


@pytest.fixture()
def seeded_day(db_session):
    """Siembra EmailTriage (2 urgentes: 1 tocada, 1 pendiente; 1 responder) +
    un CalendarEvent hoy + un item de agenda ya ingestado + una conversacion."""
    from app.db.models import CalendarEvent, EmailActivityLog

    _seed_triage(db_session, "brief_1", "jefe@empresa.com", "Servidor caido", "urgente")
    _seed_triage(db_session, "brief_2", "jefe@empresa.com", "Factura pendiente", "urgente")
    _seed_triage(db_session, "brief_3", "cliente@empresa.com", "Podemos hablar?", "responder")
    db_session.add(EmailActivityLog(
        timestamp=datetime.utcnow(), email_id="brief_1", action_type="sent",
        sender="jefe@empresa.com", subject="Servidor caido", details="{}",
    ))
    ev = CalendarEvent(title="Reunion M3", description="Cierre de sprint", start_date=datetime.utcnow())
    db_session.add(ev)
    db_session.commit()
    db_session.refresh(ev)

    yield {"event_id": ev.id}


@pytest.fixture(autouse=True)
def _cleanup_chroma():
    """Autouse pero SIN depender de seeded_day: correr para todos los tests
    del fichero (no solo los que siembran datos), sin forzar esa siembra en
    los que no la necesitan. forget() de algo que no existe es un no-op."""
    yield
    import asyncio

    async def _clean():
        await memory_router.forget(MemoryType.PERSONAL, {"kind": "agenda_item"})
        await memory_router.forget(MemoryType.PERSONAL, {"kind": "daily_summary"})

    asyncio.run(_clean())


async def _ingest_agenda_item(event_id: int):
    await memory_router.store(
        content="Reunion M3\nCierre de sprint",
        memory_type=MemoryType.PERSONAL,
        source="calendar",
        metadata={"kind": "agenda_item", "event_id": f"local:{event_id}", "event_start": datetime.utcnow().isoformat()},
        dedup_key=f"cal:local:{event_id}",
    )


def test_build_deterministic_summary_vacio_y_con_datos():
    vacio = summarizer.build_deterministic_summary({
        "date": TODAY.isoformat(), "triage_counts": {}, "triaged_total": 0,
        "urgent_pending": {"count": 0, "items": []}, "agenda": [], "conversations_count": 0,
    })
    assert "Sin actividad relevante" in vacio

    con_datos = summarizer.build_deterministic_summary({
        "date": TODAY.isoformat(), "triage_counts": {"urgente": 2, "responder": 1}, "triaged_total": 3,
        "urgent_pending": {"count": 2, "items": [{"subject": "Servidor caido"}]},
        "agenda": [{"title": "Reunion"}], "conversations_count": 4,
    })
    assert "3 emails triados" in con_datos
    assert "2 urgentes pendientes" in con_datos
    assert "Servidor caido" in con_datos


@pytest.mark.anyio
async def test_gather_day_data_urgent_pending_excluye_tocados(seeded_day):
    data = summarizer.gather_day_data(TODAY)
    ids_pendientes = {it["email_id"] for it in data["urgent_pending"]["items"]}
    assert "brief_2" in ids_pendientes  # urgente sin accion -> pendiente
    assert "brief_1" not in ids_pendientes  # urgente CON accion -> ya no pendiente
    assert data["triage_counts"].get("urgente") == 2
    assert data["triage_counts"].get("responder") == 1


@pytest.mark.anyio
async def test_gather_day_data_top_senders(seeded_day):
    data = summarizer.gather_day_data(TODAY)
    top = {s["sender"]: s["count"] for s in data["top_senders"]}
    assert top.get("jefe@empresa.com") == 2


@pytest.mark.anyio
async def test_gather_day_data_agenda_lee_items_ingestados(seeded_day):
    await _ingest_agenda_item(seeded_day["event_id"])
    data = summarizer.gather_day_data(TODAY)
    titles = [a["title"] for a in data["agenda"]]
    assert "Reunion M3" in titles


@pytest.mark.anyio
async def test_run_summarizer_persiste_y_es_idempotente(monkeypatch, seeded_day):
    # Forzamos la plantilla determinista (sin depender de que haya un LLM
    # configurado en la maquina donde corre el test).
    monkeypatch.setattr(summarizer, "_try_llm_summary", _no_llm)

    result1 = await summarizer.run_summarizer(TODAY)
    assert result1["status"] == "ok"
    cached1 = await summarizer.get_cached_summary(TODAY)
    assert cached1 == result1["summary"]

    # Segunda pasada el mismo dia: sobreescribe (dedup_key=day:{date}), no duplica.
    result2 = await summarizer.run_summarizer(TODAY)
    cached2 = await summarizer.get_cached_summary(TODAY)
    assert cached2 == result2["summary"]

    run = summarizer.last_run()
    assert run is not None and run.status == "ok" and run.job_name == summarizer.JOB_SUMMARIZER


async def _no_llm(_data):
    return None


def test_endpoint_briefing_sin_cache_es_live_deterministic(client, seeded_day):
    r = client.get("/api/memory/briefing")
    assert r.status_code == 200
    data = r.json()
    assert data["summary_source"] == "live_deterministic"
    assert data["date"] == TODAY.isoformat()
    assert "urgent_pending" in data and "agenda" in data and "top_senders" in data


@pytest.mark.anyio
async def test_endpoint_briefing_usa_cache_tras_summarizer(monkeypatch, client, seeded_day):
    monkeypatch.setattr(summarizer, "_try_llm_summary", _no_llm)
    await summarizer.run_summarizer(TODAY)

    r = client.get("/api/memory/briefing")
    assert r.status_code == 200
    data = r.json()
    assert data["summary_source"] == "cached"


def test_endpoint_briefing_fecha_invalida(client):
    r = client.get("/api/memory/briefing", params={"date": "no-es-una-fecha"})
    assert r.status_code == 400


def test_endpoint_stats_extiende_con_mos(client):
    r = client.get("/api/memory/stats")
    assert r.status_code == 200
    data = r.json()
    assert "conversations" in data  # legacy intacto
    assert "mos_collections" in data
    for mt in (MemoryType.PERSONAL, MemoryType.PROJECT, MemoryType.SKILL, MemoryType.DECISION):
        assert mt.value in data["mos_collections"]
    assert isinstance(data["mos_days_covered"], int)


@pytest.mark.anyio
async def test_criterio_de_cierre_briefing_sin_google(monkeypatch, client, seeded_day):
    """EL criterio de cierre de fase V0.85 (doc 07): "que me ha llegado
    importante hoy" responde desde memoria local con Gmail DESCONECTADO —
    cero llamadas a Gmail/Google en todo el pipeline."""
    from app.integrations import google_auth

    monkeypatch.setattr(google_auth, "is_connected", lambda: False)
    monkeypatch.setattr(summarizer, "_try_llm_summary", _no_llm)

    await _ingest_agenda_item(seeded_day["event_id"])
    await summarizer.run_summarizer(TODAY)

    r = client.get("/api/memory/briefing")
    assert r.status_code == 200
    data = r.json()

    # Respuesta real y con contenido, no un stub vacio.
    assert data["summary"] and "Sin actividad relevante" not in data["summary"]
    assert data["urgent_pending"]["count"] >= 1
    assert any(a["title"] == "Reunion M3" for a in data["agenda"])
    assert data["summary_source"] == "cached"
