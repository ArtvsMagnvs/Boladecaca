# tests/test_workspace_model.py — WPMS W1: modelo + progreso + endpoints (doc 18)
#
# Cubre: (1) la funcion pura de progreso; (2) el CONTRATO de las rutas viejas
# /api/projects y /api/tasks (identicas tras absorberlas en workspace.py); (3)
# los campos nuevos de Project/Task; (4) Milestone CRUD; (5) progreso automatico
# por evento; (6) versionado al completar un milestone.
from datetime import datetime

import pytest

from app.workspace import compute_progress, is_done, DONE_STATUSES


# ======================================================================
# Limpieza local (conftest no limpia projects/tasks/milestones)
# ======================================================================
@pytest.fixture(autouse=True)
def _clean_workspace_tables():
    # Asegura que la tabla milestones existe (la crea el lifespan del `client`,
    # pero los tests puros de progreso corren sin arrancarlo). Idempotente.
    from app.db.database import Base, engine
    Base.metadata.create_all(bind=engine)
    yield
    from app.db.database import SessionLocal
    from app.db.models import Project, Task
    from app.workspace import Milestone
    db = SessionLocal()
    try:
        for model in (Task, Milestone, Project):
            try:
                db.query(model).delete()
            except Exception:
                db.rollback()
        db.commit()
    finally:
        db.close()


# ======================================================================
# Parte 1 — progreso puro (sin BD, doc 18 §8)
# ======================================================================
def test_compute_progress_vacio_es_cero():
    """Un milestone sin tareas esta al 0%, NO al 100% (doc 18 §8)."""
    r = compute_progress([])
    assert r == {"done": 0, "total": 0, "ratio": 0.0}


def test_compute_progress_conteo_simple():
    r = compute_progress(["pending", "completed", "done", "in_progress"])
    assert r["done"] == 2 and r["total"] == 4
    assert r["ratio"] == 0.5


def test_is_done_reconoce_done_y_completed():
    # Coincide con el filtro real del telegram_adapter (done + completed).
    assert is_done("done") and is_done("completed")
    assert is_done("COMPLETED")  # case-insensitive
    assert not is_done("pending") and not is_done("in_progress")
    assert not is_done(None)
    assert {"done", "completed"} == set(DONE_STATUSES)


# ======================================================================
# Parte 2 — CONTRATO de las rutas viejas (retrocompatibilidad)
# ======================================================================
def test_contrato_projects_viejo_intacto(client):
    """Crear un proyecto con SOLO los campos de siempre sigue funcionando."""
    r = client.post("/api/projects/", json={"name": "Legacy Proj", "status": "active"})
    assert r.status_code == 201, r.text
    body = r.json()
    # shape antiguo presente
    for k in ("id", "name", "status", "progress", "priority", "created_at"):
        assert k in body
    assert body["name"] == "Legacy Proj"

    lst = client.get("/api/projects/")
    assert lst.status_code == 200
    assert any(p["id"] == body["id"] for p in lst.json())


def test_contrato_tasks_viejo_intacto(client):
    """Crear una tarea con SOLO los campos de siempre sigue funcionando."""
    r = client.post("/api/tasks/", json={"title": "Legacy Task", "status": "pending"})
    assert r.status_code == 201, r.text
    body = r.json()
    for k in ("id", "title", "status", "priority", "created_at"):
        assert k in body
    assert body["title"] == "Legacy Task"


# ======================================================================
# Parte 3 — campos nuevos de Project/Task
# ======================================================================
def test_project_acepta_campos_nuevos(client):
    r = client.post("/api/projects/", json={
        "name": "Aithera",
        "repo_path": "C:/repo/aithera",
        "current_version": "0.8.5",
        "target_version": "0.8.7",
        "tags": ["ai", "desktop"],
        "docs": [{"label": "roadmap", "kind": "md", "url_or_path": "ROADMAP.md"}],
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["repo_path"] == "C:/repo/aithera"
    assert body["current_version"] == "0.8.5"
    assert body["tags"] == ["ai", "desktop"]
    assert body["docs"][0]["label"] == "roadmap"


def test_task_acepta_campos_nuevos(client):
    proj = client.post("/api/projects/", json={"name": "P"}).json()
    r = client.post("/api/tasks/", json={
        "title": "Implementar W1",
        "project_id": proj["id"],
        "checklist": [{"text": "migracion", "done": False}],
        "depends_on": [1, 2],
        "estimate": "1 sesion",
        "links": {"commit": "abc123"},
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["checklist"][0]["text"] == "migracion"
    assert body["depends_on"] == [1, 2]
    assert body["estimate"] == "1 sesion"
    assert body["links"]["commit"] == "abc123"
    assert body["closed_at"] is None  # nace pendiente


# ======================================================================
# Parte 4 — Milestone CRUD + progreso adjunto
# ======================================================================
def test_milestone_crud(client):
    proj = client.post("/api/projects/", json={"name": "P"}).json()
    r = client.post("/api/milestones/", json={
        "project_id": proj["id"], "name": "V0.9 — AE", "version": "0.9", "status": "active",
    })
    assert r.status_code == 201, r.text
    m = r.json()
    assert m["name"] == "V0.9 — AE" and m["version"] == "0.9"
    assert m["progress"] == {"done": 0, "total": 0, "ratio": 0.0}  # sin tareas

    # list filtrado por proyecto
    lst = client.get(f"/api/milestones/?project_id={proj['id']}")
    assert lst.status_code == 200 and len(lst.json()) == 1

    # update
    up = client.put(f"/api/milestones/{m['id']}", json={"description": "Automation Engine"})
    assert up.status_code == 200 and up.json()["description"] == "Automation Engine"

    # delete
    dl = client.delete(f"/api/milestones/{m['id']}")
    assert dl.status_code == 200
    assert client.get(f"/api/milestones/{m['id']}").status_code == 404


# ======================================================================
# Parte 5 — progreso automatico por evento (doc 18 §8)
# ======================================================================
def test_progreso_automatico_por_conteo(client):
    proj = client.post("/api/projects/", json={"name": "P"}).json()
    ms = client.post("/api/milestones/", json={"project_id": proj["id"], "name": "M1"}).json()

    ids = []
    for i in range(4):
        t = client.post("/api/tasks/", json={
            "title": f"T{i}", "project_id": proj["id"], "milestone_id": ms["id"],
        }).json()
        ids.append(t["id"])

    # 0/4 -> progreso 0.0
    assert client.get(f"/api/projects/{proj['id']}").json()["progress"] == 0.0

    # cerrar 2 tareas
    for tid in ids[:2]:
        client.put(f"/api/tasks/{tid}", json={"status": "completed"})

    # el proyecto se recalculo solo: 2/4 = 0.5
    assert client.get(f"/api/projects/{proj['id']}").json()["progress"] == 0.5
    # el progreso del milestone tambien
    mp = client.get(f"/api/milestones/{ms['id']}").json()["progress"]
    assert mp == {"done": 2, "total": 4, "ratio": 0.5}

    # /workspace/progress refleja el desglose
    wp = client.get(f"/api/workspace/progress?project_id={proj['id']}").json()
    assert wp["overall"]["ratio"] == 0.5
    assert wp["milestones"][0]["ratio"] == 0.5


def test_closed_at_se_sella_y_se_limpia(client):
    proj = client.post("/api/projects/", json={"name": "P"}).json()
    t = client.post("/api/tasks/", json={"title": "T", "project_id": proj["id"]}).json()
    assert t["closed_at"] is None

    closed = client.put(f"/api/tasks/{t['id']}", json={"status": "done"}).json()
    assert closed["closed_at"] is not None  # sellado al cerrar

    reopened = client.put(f"/api/tasks/{t['id']}", json={"status": "pending"}).json()
    assert reopened["closed_at"] is None  # limpiado al reabrir


# ======================================================================
# Parte 6 — versionado al completar un milestone (doc 18 §6)
# ======================================================================
def test_completar_milestone_propaga_version_y_activa_siguiente(client):
    proj = client.post("/api/projects/", json={"name": "Aithera", "current_version": "0.8.5"}).json()
    m1 = client.post("/api/milestones/", json={
        "project_id": proj["id"], "name": "V0.87", "version": "0.8.7",
        "status": "active", "order_index": 0,
    }).json()
    m2 = client.post("/api/milestones/", json={
        "project_id": proj["id"], "name": "V0.9", "version": "0.9",
        "status": "planned", "order_index": 1,
    }).json()

    done = client.post(f"/api/milestones/{m1['id']}/complete").json()
    assert done["status"] == "done" and done["completed_at"] is not None

    # el proyecto adopta la version completada y apunta a la siguiente
    p = client.get(f"/api/projects/{proj['id']}").json()
    assert p["current_version"] == "0.8.7"
    assert p["target_version"] == "0.9"

    # el siguiente milestone pasa a activo
    assert client.get(f"/api/milestones/{m2['id']}").json()["status"] == "active"


def test_borrar_milestone_deja_tareas_en_backlog(client):
    proj = client.post("/api/projects/", json={"name": "P"}).json()
    ms = client.post("/api/milestones/", json={"project_id": proj["id"], "name": "M"}).json()
    t = client.post("/api/tasks/", json={
        "title": "T", "project_id": proj["id"], "milestone_id": ms["id"],
    }).json()
    assert t["milestone_id"] == ms["id"]

    client.delete(f"/api/milestones/{ms['id']}")

    # la tarea sobrevive, sin milestone (backlog) — doc 18 §4
    back = client.get(f"/api/tasks/{t['id']}").json()
    assert back["milestone_id"] is None


# ======================================================================
# Parte 7 — integracion MOS/eventos (W4, doc 18 §5, §10)
# ======================================================================
import asyncio  # noqa: E402


def test_completar_milestone_distila_a_mem_project(client):
    from app.memory import MemoryType, memory_router

    proj = client.post("/api/projects/", json={"name": "P W4"}).json()
    m = client.post("/api/milestones/", json={
        "project_id": proj["id"], "name": "M1", "version": "1.0", "description": "primer hito",
    }).json()

    r = client.post(f"/api/milestones/{m['id']}/complete")
    assert r.status_code == 200

    item = asyncio.run(memory_router.retrieve(f"{MemoryType.PROJECT.value}:milestone:{m['id']}"))
    assert item is not None
    assert "M1" in item.content
    assert item.metadata.get("kind") == "milestone_completed"


def test_tarea_cerrada_con_decision_crea_decision(client):
    from app.db.database import SessionLocal
    from app.db.models import Decision

    proj = client.post("/api/projects/", json={"name": "P Decision"}).json()
    t = client.post("/api/tasks/", json={"title": "Elegir DB", "project_id": proj["id"]}).json()

    r = client.put(f"/api/tasks/{t['id']}", json={
        "status": "completed",
        "links": {"decision": "Usamos Postgres en vez de SQLite en produccion"},
    })
    assert r.status_code == 200

    db = SessionLocal()
    try:
        found = db.query(Decision).filter(Decision.title == "Elegir DB").first()
    finally:
        db.close()
    assert found is not None
    assert "Postgres" in found.body
    assert found.project == "P Decision"


def test_tarea_cerrada_sin_decision_no_crea_decision(client):
    from app.db.database import SessionLocal
    from app.db.models import Decision

    proj = client.post("/api/projects/", json={"name": "P Sin Decision"}).json()
    t = client.post("/api/tasks/", json={"title": "Tarea simple", "project_id": proj["id"]}).json()
    client.put(f"/api/tasks/{t['id']}", json={"status": "completed"})

    db = SessionLocal()
    try:
        found = db.query(Decision).filter(Decision.title == "Tarea simple").first()
    finally:
        db.close()
    assert found is None


def test_eventos_task_created_status_changed_closed(client, monkeypatch):
    emitted = []
    monkeypatch.setattr(
        "app.workspace.service.emit",
        lambda name, source, payload=None: emitted.append((name, payload)),
    )

    proj = client.post("/api/projects/", json={"name": "P Events"}).json()
    t = client.post("/api/tasks/", json={"title": "T Events", "project_id": proj["id"]}).json()
    client.put(f"/api/tasks/{t['id']}", json={"status": "in_progress"})
    client.put(f"/api/tasks/{t['id']}", json={"status": "completed"})

    names = [n for n, _ in emitted]
    assert "task.created" in names
    assert "task.status_changed" in names
    assert "task.closed" in names
    assert "project.progress_changed" in names

    status_changes = [p for n, p in emitted if n == "task.status_changed"]
    assert {"task_id": t["id"], "project_id": proj["id"], "from": "pending", "to": "in_progress"} in status_changes


def test_archivar_proyecto_distila_resumen_y_es_idempotente(client):
    from app.memory import MemoryType, memory_router

    proj = client.post("/api/projects/", json={"name": "P Archive", "current_version": "1.0"}).json()

    r1 = client.post(f"/api/projects/{proj['id']}/archive")
    assert r1.status_code == 200
    first_archived_at = r1.json()["archived_at"]
    assert first_archived_at is not None

    # segunda llamada es idempotente: no reescribe archived_at
    r2 = client.post(f"/api/projects/{proj['id']}/archive")
    assert r2.json()["archived_at"] == first_archived_at

    item = asyncio.run(memory_router.retrieve(f"{MemoryType.PROJECT.value}:project_archived:{proj['id']}"))
    assert item is not None
    assert "archivado" in item.content


def test_briefing_snapshot_incluye_milestone_activo_y_deadlines(client):
    from datetime import datetime, timedelta

    from app.db.database import SessionLocal
    from app.workspace import workspace_service

    proj = client.post("/api/projects/", json={"name": "P Briefing"}).json()
    m = client.post("/api/milestones/", json={
        "project_id": proj["id"], "name": "Activo", "status": "active",
    }).json()
    due = (datetime.utcnow() + timedelta(days=2)).isoformat()
    client.post("/api/tasks/", json={
        "title": "Deadline cercano", "project_id": proj["id"], "due_date": due, "priority": "high",
    })

    db = SessionLocal()
    try:
        snap = workspace_service.briefing_snapshot(db)
    finally:
        db.close()

    assert any(x["milestone_id"] == m["id"] for x in snap["active_milestones"])
    assert any(x["title"] == "Deadline cercano" for x in snap["upcoming_deadlines"])
    assert any(x["title"] == "Deadline cercano" for x in snap["high_priority_open"])
