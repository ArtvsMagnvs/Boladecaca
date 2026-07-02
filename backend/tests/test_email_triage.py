# tests/test_email_triage.py
#
# Sprint 3 (PLAN_MAESTRO_2026, B5): tests del triaje de inbox en 2 etapas.
#   Etapa 1 heuristica (0 coste) -> Etapa 2 LLM solo si ambiguo -> fallback fyi.

import pytest

from app.services import email_service as svc


# ----------------------------------------------------------------------
# Etapa 1: heuristica
# ----------------------------------------------------------------------

@pytest.mark.parametrize("subject,sender,expected", [
    ("URGENT: action required", "admin@service.com", "urgente"),
    ("Data deletion warning", "noreply@google.com", "urgente"),  # keyword urgente gana
    ("Factura marzo 2026", "billing@empresa.com", "factura"),
    ("Your invoice is ready", "stripe@stripe.com", "factura"),
    ("Reunion el jueves?", "ana@cliente.com", "reunion"),
    ("Invitacion: llamada de seguimiento", "cal@empresa.com", "reunion"),
    ("Juan te ha mencionado en un comentario", "notification@facebook.com", "spam-social"),
    ("Tu resumen semanal", "digest@medium.com", "newsletter"),
])
def test_heuristica_clasifica(subject, sender, expected):
    assert svc.heuristic_triage(subject, sender) == expected


def test_heuristica_ambiguo_devuelve_none():
    """Un email personal sin keywords -> None (decide el LLM)."""
    assert svc.heuristic_triage("Sobre lo del otro dia", "maria@gmail.com", "te cuento") is None


# ----------------------------------------------------------------------
# Etapa 2: LLM (mockeado) + fallback
# ----------------------------------------------------------------------

@pytest.mark.anyio
async def test_triage_email_usa_heuristica_primero(monkeypatch):
    async def _no_llamar(*a, **k):
        raise AssertionError("el LLM no debe llamarse si la heuristica decide")
    monkeypatch.setattr(svc, "llm_triage", _no_llamar)
    cat, method = await svc.triage_email("e1", "Factura pendiente", "x@y.com")
    assert (cat, method) == ("factura", "heuristic")


@pytest.mark.anyio
async def test_triage_email_llm_para_ambiguos(monkeypatch):
    async def _llm(subject, sender, snippet=""):
        return "responder"
    monkeypatch.setattr(svc, "llm_triage", _llm)
    cat, method = await svc.triage_email("e2", "Sobre lo del otro dia", "maria@gmail.com")
    assert (cat, method) == ("responder", "llm")


@pytest.mark.anyio
async def test_triage_email_fallback_si_llm_cae(monkeypatch):
    async def _llm(subject, sender, snippet=""):
        return None
    monkeypatch.setattr(svc, "llm_triage", _llm)
    cat, method = await svc.triage_email("e3", "Sobre lo del otro dia", "maria@gmail.com")
    assert (cat, method) == ("fyi", "fallback")


@pytest.mark.anyio
async def test_llm_triage_valida_respuesta(monkeypatch):
    """Si el LLM responde basura, llm_triage devuelve None (no inventa)."""
    class FakeAI:
        async def chat(self, message, system_prompt=None):
            return {"response": "no tengo ni idea", "error": False}
    import app.ai.ai_manager as aim
    monkeypatch.setattr(aim, "ai_manager", FakeAI())
    assert await svc.llm_triage("asunto", "a@b.com") is None


# ----------------------------------------------------------------------
# Persistencia: save_triage / get_triage_map
# ----------------------------------------------------------------------

def test_save_y_map_roundtrip(client):
    svc.save_triage("mail-1", "a@b.com", "hola", "urgente", "heuristic")
    svc.save_triage("mail-2", "c@d.com", "que tal", "fyi", "fallback")
    m = svc.get_triage_map(["mail-1", "mail-2", "mail-3"])
    assert m == {"mail-1": "urgente", "mail-2": "fyi"}


def test_save_triage_es_upsert(client):
    svc.save_triage("mail-up", "a@b.com", "s", "fyi", "fallback")
    svc.save_triage("mail-up", "a@b.com", "s", "reunion", "llm")
    assert svc.get_triage_map(["mail-up"]) == {"mail-up": "reunion"}


# ----------------------------------------------------------------------
# Endpoint POST /api/email/triage/run + preview enriquecido
# ----------------------------------------------------------------------

class FakeTool:
    def __init__(self, items):
        self._items = items

    async def execute(self, action, params):
        assert action == "list_inbox_preview"
        return {"success": True, "result": {"count": len(self._items), "items": self._items}}


@pytest.fixture()
def inbox_mock(monkeypatch):
    from app.api.endpoints import email_inbox as ei
    items = [
        {"id": "t1", "subject": "Factura abril", "from": "billing@x.com", "snippet": "", "date": "", "unread": True},
        {"id": "t2", "subject": "Sobre lo del otro dia", "from": "maria@gmail.com", "snippet": "", "date": "", "unread": False},
    ]
    monkeypatch.setattr(ei, "_email_tool", lambda: FakeTool(items))
    monkeypatch.setattr(ei.google_auth, "is_connected", lambda: True)

    async def _llm(subject, sender, snippet=""):
        return "responder"
    monkeypatch.setattr(svc, "llm_triage", _llm)
    return items


def test_triage_run(client, inbox_mock):
    r = client.post("/api/email/triage/run?max_emails=10")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert data["classified_now"] == 2
    assert data["counts"]["factura"] == 1
    assert data["counts"]["responder"] == 1
    by_id = {i["id"]: i for i in data["items"]}
    assert by_id["t1"]["method"] == "heuristic"
    assert by_id["t2"]["method"] == "llm"

    # Segunda pasada sin force: todo cacheado
    r2 = client.post("/api/email/triage/run?max_emails=10")
    assert r2.json()["classified_now"] == 0
    assert {i["method"] for i in r2.json()["items"]} == {"cached"}


def test_preview_enriquecido_con_categoria(client, inbox_mock):
    client.post("/api/email/triage/run?max_emails=10")
    r = client.get("/api/email/inbox/preview?max_emails=10")
    assert r.status_code == 200
    items = r.json()["items"]
    cats = {i["id"]: i.get("category") for i in items}
    assert cats == {"t1": "factura", "t2": "responder"}


def test_triage_run_sin_google_503(client, monkeypatch):
    from app.api.endpoints import email_inbox as ei
    monkeypatch.setattr(ei.google_auth, "is_connected", lambda: False)
    assert client.post("/api/email/triage/run").status_code == 503
