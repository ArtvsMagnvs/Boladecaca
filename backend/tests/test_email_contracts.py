# tests/test_email_contracts.py
#
# Sprint 1 (PLAN_MAESTRO_2026, B2): TESTS DE CONTRATO del API de email.
#
# Proposito: congelar la superficie publica de /api/email ANTES del split
# del god-endpoint (Sprint 2). Si esta suite pasa antes y despues del
# refactor, el frontend (EmailAssistant.tsx) no nota el cambio.
#
# Dos niveles:
#   1. Contrato de rutas — cada (metodo, path) publico debe existir.
#   2. Contrato de shape — endpoints clave devuelven la forma esperada,
#      con Gmail/EmailTool mockeado (sin red, sin OAuth real).

import pytest

from app.main import app


# ----------------------------------------------------------------------
# 1. Contrato de rutas: la superficie publica completa de /api/email.
#    NO editar a la ligera: cambiar esto = romper el frontend.
# ----------------------------------------------------------------------

EMAIL_API_CONTRACT = [
    # Auth / status
    ("GET",    "/api/email/status"),
    ("POST",   "/api/email/auth/credentials"),
    ("DELETE", "/api/email/auth/credentials"),
    ("POST",   "/api/email/auth/start"),
    ("DELETE", "/api/email/auth"),
    # Inbox / lectura
    ("GET",    "/api/email/inbox"),
    ("GET",    "/api/email/inbox/preview"),
    ("GET",    "/api/email/email/{email_id}"),
    ("GET",    "/api/email/search/query"),
    ("GET",    "/api/email/summary"),
    # Composicion
    ("POST",   "/api/email/draft"),
    ("POST",   "/api/email/send"),
    # Auto-reply
    ("GET",    "/api/email/auto-reply/rules"),
    ("POST",   "/api/email/auto-reply/rules"),
    ("PATCH",  "/api/email/auto-reply/rules/{rule_id}"),
    ("DELETE", "/api/email/auto-reply/rules/{rule_id}"),
    ("POST",   "/api/email/auto-reply/test"),
    # V0.7.3 (Sprint 4, B6): feedback de autonomia gradual
    ("POST",   "/api/email/auto-reply/rules/{rule_id}/feedback"),
    ("POST",   "/api/email/auto-reply/send"),
    # Procesamiento
    ("POST",   "/api/email/process-inbox"),
    # V0.7.3 (Sprint 3): triaje del inbox
    ("POST",   "/api/email/triage/run"),
    ("POST",   "/api/email/process-test"),
    ("POST",   "/api/email/process-meetings"),
    ("POST",   "/api/email/check-confirmations"),
    # Activity log
    ("GET",    "/api/email/activity"),
    ("GET",    "/api/email/activity/stats"),
    # V0.7.3 (Sprint 4, B7): digest diario
    ("GET",    "/api/email/digest"),
    ("POST",   "/api/email/activity/{entry_id}/read"),
    ("POST",   "/api/email/activity/mark-all-read"),
    ("DELETE", "/api/email/activity/{entry_id}"),
    ("DELETE", "/api/email/activity"),
    # Meeting proposals
    ("GET",    "/api/email/proposals"),
    ("DELETE", "/api/email/proposals/{proposal_id}"),
]


def _mounted_routes():
    """Superficie publica via OpenAPI (robusto ante versiones de FastAPI:
    en versiones nuevas app.routes contiene _IncludedRouter lazy, pero el
    schema OpenAPI siempre materializa todas las rutas)."""
    routes = set()
    schema = app.openapi()
    for path, methods in schema.get("paths", {}).items():
        for method in methods:
            routes.add((method.upper(), path))
    return routes


@pytest.mark.parametrize("method,path", EMAIL_API_CONTRACT)
def test_ruta_existe(method, path):
    assert (method, path) in _mounted_routes(), (
        f"CONTRATO ROTO: {method} {path} ya no existe. "
        "Si es intencional, actualizar EmailAssistant.tsx y este contrato."
    )


def test_sin_rutas_email_no_contempladas():
    """Aviso si aparece una ruta /api/email nueva sin registrar en el contrato."""
    email_routes = {
        (m, p) for (m, p) in _mounted_routes()
        if p.startswith("/api/email") and m not in ("HEAD", "OPTIONS")
    }
    extra = email_routes - set(EMAIL_API_CONTRACT)
    assert not extra, (
        f"Rutas de email fuera del contrato (anadirlas): {sorted(extra)}"
    )


# ----------------------------------------------------------------------
# 2. Contrato de shape — con EmailTool/google_auth mockeados.
# ----------------------------------------------------------------------

class FakeEmailTool:
    """Mock de EmailTool: execute() devuelve respuestas predefinidas."""

    def __init__(self, responses=None):
        self._responses = responses or {}
        self.calls = []

    async def execute(self, action, params):
        self.calls.append((action, params))
        if action in self._responses:
            return self._responses[action]
        return {"success": True, "result": {"ok": True, "action": action}}


def test_status_shape(client):
    """GET /status responde siempre (conectado o no) con las 5 claves."""
    r = client.get("/api/email/status")
    assert r.status_code == 200
    data = r.json()
    for key in ("connected", "email", "has_credentials", "libs_available", "credentials_source"):
        assert key in data, f"clave ausente en /status: {key}"
    assert isinstance(data["connected"], bool)
    assert data["credentials_source"] in ("env", "db", "none")


def test_inbox_con_gmail_mockeado(client, monkeypatch):
    from app.api.endpoints import email_inbox as ea

    fake = FakeEmailTool({
        "list_inbox": {
            "success": True,
            "result": {"emails": [{"id": "abc123"}], "count": 1},
        }
    })
    monkeypatch.setattr(ea, "_email_tool", lambda: fake)
    r = client.get("/api/email/inbox?max_results=5")
    assert r.status_code == 200
    assert r.json()["count"] == 1
    assert fake.calls[0][0] == "list_inbox"
    assert fake.calls[0][1]["max_results"] == 5


def test_inbox_error_gmail_devuelve_400(client, monkeypatch):
    from app.api.endpoints import email_inbox as ea

    fake = FakeEmailTool({
        "list_inbox": {"success": False, "error": "Google no conectado"}
    })
    monkeypatch.setattr(ea, "_email_tool", lambda: fake)
    r = client.get("/api/email/inbox")
    assert r.status_code == 400
    assert "Google" in r.json()["detail"]


def test_send_sin_confirmacion_rechazado(client, monkeypatch):
    """CONTRATO DE SEGURIDAD (principio 5): enviar sin confirmed=true -> 400
    y el EmailTool NUNCA llega a ejecutarse."""
    from app.api.endpoints import email_compose as ea

    fake = FakeEmailTool()
    monkeypatch.setattr(ea, "_email_tool", lambda: fake)
    r = client.post("/api/email/send", json={
        "to": "test@example.com", "subject": "hola", "body": "test",
    })
    assert r.status_code == 400
    assert fake.calls == [], "send_email se ejecuto sin confirmacion explicita!"


def test_send_con_confirmacion(client, monkeypatch):
    from app.api.endpoints import email_compose as ea

    fake = FakeEmailTool({
        "send_email": {"success": True, "result": {"sent": True, "id": "m1"}}
    })
    monkeypatch.setattr(ea, "_email_tool", lambda: fake)
    r = client.post("/api/email/send", json={
        "to": "test@example.com", "subject": "hola", "body": "test", "confirmed": True,
    })
    assert r.status_code == 200
    assert r.json()["sent"] is True


def test_auth_credentials_vacias_400(client):
    r = client.post("/api/email/auth/credentials", json={
        "client_id": "  ", "client_secret": "",
    })
    assert r.status_code == 400


def test_auto_reply_send_sin_match(client):
    """Sin reglas en BD: sent=False con 200 (no es error)."""
    r = client.post("/api/email/auto-reply/send", json={
        "sender": "nadie@example.com", "subject": "sin regla", "body": "",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["sent"] is False
    assert "reason" in data


# --- Endpoints con BD real (temporal), sin Gmail ---

def test_activity_vacia(client):
    r = client.get("/api/email/activity")
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["count"] == 0


def test_activity_stats_shape(client):
    r = client.get("/api/email/activity/stats")
    assert r.status_code == 200
    stats = r.json()
    for key in ("sent", "draft", "alert", "meeting_proposal",
                "meeting_confirmed", "auto_replied", "error", "skipped"):
        assert key in stats
        assert set(stats[key].keys()) == {"total", "unread"}


def test_activity_ciclo_completo(client, db_session):
    """Crear entrada -> listar -> marcar leida -> borrar."""
    from app.db.models import EmailActivityLog
    entry = EmailActivityLog(
        email_id="e1", sender="Test", sender_email="t@x.com",
        subject="asunto", snippet="...", action_type="alert", read=False,
    )
    db_session.add(entry)
    db_session.commit()
    entry_id = entry.id

    r = client.get("/api/email/activity?only_unread=true")
    assert r.status_code == 200
    assert r.json()["count"] == 1

    assert client.post(f"/api/email/activity/{entry_id}/read").status_code == 204
    r = client.get("/api/email/activity?only_unread=true")
    assert r.json()["count"] == 0

    assert client.delete(f"/api/email/activity/{entry_id}").status_code == 204
    assert client.get("/api/email/activity").json()["count"] == 0


def test_activity_read_inexistente_404(client):
    assert client.post("/api/email/activity/999999/read").status_code == 404


def test_proposals_vacias(client):
    r = client.get("/api/email/proposals")
    assert r.status_code == 200
    data = r.json()
    assert data["proposals"] == []
    assert data["count"] == 0


def test_proposal_delete_inexistente_404(client):
    assert client.delete("/api/email/proposals/999999").status_code == 404


# --- Regresion Sprint 2: bug latente json/log_activity ---

def test_log_activity_persiste_details(client):
    """V0.7 tenia `import json as _json` pero log_activity usaba `json.dumps`
    -> NameError silenciado -> el activity log NUNCA persistia. Arreglado en
    el split (Sprint 2). Este test evita la regresion end-to-end."""
    from app.services.email_service import log_activity

    entry_id = log_activity(
        action_type="alert",
        sender="Regresion <bug@aithera.local>",
        subject="log_activity funciona",
        details={"motivo": "test regresion sprint 2", "n": 42},
    )
    assert entry_id is not None, "log_activity devolvio None: no persistio"

    r = client.get("/api/email/activity")
    assert r.status_code == 200
    items = [i for i in r.json()["items"] if i["id"] == entry_id]
    assert len(items) == 1
    assert items[0]["details"] == {"motivo": "test regresion sprint 2", "n": 42}
    assert items[0]["sender_email"] == "bug@aithera.local"
