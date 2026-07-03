# tests/test_email_ai_reply.py
#
# Sprint 4b (PLAN_MAESTRO_2026): respuestas generadas por IA por regla
# (ai_prompt) + eleccion directa de autonomia al crear la regla.

import pytest

from app.services import email_service as svc


# ----------------------------------------------------------------------
# Eleccion directa de autonomia al crear
# ----------------------------------------------------------------------

def test_crear_regla_auto_directa(client):
    r = client.post("/api/email/auto-reply/rules", json={
        "name": "Escuela ninos",
        "sender_emails": ["escuela@colegio.edu"],
        "action": "auto_send",
        "autonomy": "auto",  # eleccion directa (remitente poco frecuente)
        "reply_template": "Recibido, gracias",
    })
    assert r.status_code == 201, r.text
    rules = client.get("/api/email/auto-reply/rules").json()["rules"]
    mine = [x for x in rules if x["name"] == "Escuela ninos"][0]
    assert mine["autonomy"] == "auto"


def test_autonomy_invalida_al_crear(client):
    r = client.post("/api/email/auto-reply/rules", json={
        "name": "Mala",
        "sender_emails": ["a@b.com"],
        "autonomy": "turbo",
        "reply_template": "x",
    })
    assert r.status_code == 400


# ----------------------------------------------------------------------
# ai_prompt: validaciones de creacion
# ----------------------------------------------------------------------

def test_crear_regla_solo_ai_prompt_sin_plantilla(client):
    """Con ai_prompt la plantilla es opcional aunque no detecte reuniones."""
    r = client.post("/api/email/auto-reply/rules", json={
        "name": "Viajes",
        "sender_emails": ["losmagnoviajes@gmail.com"],
        "action": "auto_send",
        "autonomy": "auto",
        "detect_meeting_with_ia": True,
        "ai_prompt": "Responde cordialmente con la propuesta para una reunion otro dia",
    })
    assert r.status_code == 201, r.text
    rules = client.get("/api/email/auto-reply/rules").json()["rules"]
    mine = [x for x in rules if x["name"] == "Viajes"][0]
    assert mine["ai_prompt"].startswith("Responde cordialmente")
    assert mine["reply_template"] == ""


def test_crear_regla_sin_nada_400(client):
    """Sin plantilla, sin ai_prompt y sin deteccion de reuniones -> 400."""
    r = client.post("/api/email/auto-reply/rules", json={
        "name": "Vacia",
        "sender_emails": ["x@y.com"],
        "detect_meeting_with_ia": False,
    })
    assert r.status_code == 400


def test_update_ai_prompt(client):
    client.post("/api/email/auto-reply/rules", json={
        "name": "Editable",
        "sender_emails": ["e@f.com"],
        "reply_template": "hola",
    })
    rules = client.get("/api/email/auto-reply/rules").json()["rules"]
    rid = [x for x in rules if x["name"] == "Editable"][0]["id"]
    r = client.patch(f"/api/email/auto-reply/rules/{rid}",
                     json={"ai_prompt": "Responde con humor"})
    assert r.status_code == 200
    rules = client.get("/api/email/auto-reply/rules").json()["rules"]
    assert [x for x in rules if x["id"] == rid][0]["ai_prompt"] == "Responde con humor"


# ----------------------------------------------------------------------
# generate_ai_reply (LLM mockeado)
# ----------------------------------------------------------------------

@pytest.mark.anyio
async def test_generate_ai_reply_ok(monkeypatch):
    class FakeAI:
        async def chat(self, message, system_prompt=None):
            assert "Responde cordialmente" in message
            assert "losmagnoviajes" in message
            return {"response": "Hola! Esta semana lo tengo complicado, te propongo vernos el jueves.", "error": False}
    import app.ai.ai_manager as aim
    monkeypatch.setattr(aim, "ai_manager", FakeAI())
    out = await svc.generate_ai_reply(
        "Responde cordialmente proponiendo otro dia",
        "Los Magno Viajes <losmagnoviajes@gmail.com>", "Reunion", "Podemos vernos manana?",
    )
    assert out and "jueves" in out


@pytest.mark.anyio
async def test_generate_ai_reply_fail_soft(monkeypatch):
    class FakeAI:
        async def chat(self, message, system_prompt=None):
            return {"response": "", "error": True}
    import app.ai.ai_manager as aim
    monkeypatch.setattr(aim, "ai_manager", FakeAI())
    assert await svc.generate_ai_reply("da igual", "a@b.com", "s", "b") is None


# ----------------------------------------------------------------------
# /auto-reply/send end-to-end con IA
# ----------------------------------------------------------------------

class FakeSendTool:
    def __init__(self):
        self.sent = []

    async def execute(self, action, params):
        assert action == "send_email"
        self.sent.append(params)
        return {"success": True, "result": {"sent": True, "id": "m9"}}


def test_auto_reply_send_con_ia(client, monkeypatch):
    client.post("/api/email/auto-reply/rules", json={
        "name": "Viajes send",
        "sender_emails": ["losmagnoviajes@gmail.com"],
        "action": "auto_send",
        "autonomy": "auto",
        "ai_prompt": "Responde cordialmente proponiendo otro dia",
    })
    from app.api.endpoints import email_auto_reply as ear
    tool = FakeSendTool()
    monkeypatch.setattr(ear, "_email_tool", lambda: tool)
    monkeypatch.setattr(ear.google_auth, "is_connected", lambda: True)

    async def fake_ai(prompt, sender, subject, body="", extra_context=""):
        return "Hola! Encantado, pero esta semana ando liado. Te va bien el jueves?"
    monkeypatch.setattr(svc, "generate_ai_reply", fake_ai)

    r = client.post("/api/email/auto-reply/send", json={
        "sender": "Los Magno Viajes <losmagnoviajes@gmail.com>",
        "subject": "Reunion",
        "body": "Podemos vernos manana a las 10?",
    })
    assert r.status_code == 200, r.text
    assert r.json()["sent"] is True
    assert tool.sent[0]["to"] == "losmagnoviajes@gmail.com"
    assert "jueves" in tool.sent[0]["body"]  # respuesta IA, no plantilla


def test_auto_reply_send_ia_cae_sin_fallback(client, monkeypatch):
    """IA sin respuesta y regla sin plantilla -> no se envia nada (fail-soft)."""
    client.post("/api/email/auto-reply/rules", json={
        "name": "Sin fallback",
        "sender_emails": ["solo-ia@x.com"],
        "action": "auto_send",
        "autonomy": "auto",
        "ai_prompt": "Responde bien",
    })
    from app.api.endpoints import email_auto_reply as ear
    tool = FakeSendTool()
    monkeypatch.setattr(ear, "_email_tool", lambda: tool)
    monkeypatch.setattr(ear.google_auth, "is_connected", lambda: True)

    async def fake_ai(*a, **k):
        return None
    monkeypatch.setattr(svc, "generate_ai_reply", fake_ai)

    r = client.post("/api/email/auto-reply/send", json={
        "sender": "solo-ia@x.com", "subject": "hola", "body": "",
    })
    assert r.status_code == 200
    assert r.json()["sent"] is False
    assert tool.sent == []  # nada salio


# ----------------------------------------------------------------------
# 2026-07-02: responder desde el dashboard (respond_to_email + endpoint)
# ----------------------------------------------------------------------

class FakeRespondTool:
    """Mock de EmailTool para respond_to_email: get_email + draft/send."""

    def __init__(self, email_data):
        self._email = email_data
        self.executed = []

    async def execute(self, action, params):
        self.executed.append((action, params))
        if action == "get_email":
            return {"success": True, "result": self._email}
        return {"success": True, "result": {"ok": True, "id": "x1"}}


@pytest.fixture()
def respond_setup(client, monkeypatch):
    """Regla con ai_prompt + email no-reunion + tool mockeado."""
    client.post("/api/email/auto-reply/rules", json={
        "name": "Viajes respond",
        "sender_emails": ["losmagnoviajes@gmail.com"],
        "action": "alert_only",  # la regla solo avisaba...
        "autonomy": "propose",
        "ai_prompt": "Responde cordialmente",
    })
    tool = FakeRespondTool({
        "from": "Los Magno Viajes <losmagnoviajes@gmail.com>",
        "subject": "Consulta",
        "body": "Hola, que tal todo?",
    })
    monkeypatch.setattr(svc, "_email_tool", lambda: tool)

    async def fake_ai(prompt, sender, subject, body="", extra_context=""):
        return "Todo genial, gracias! Un abrazo."
    monkeypatch.setattr(svc, "generate_ai_reply", fake_ai)

    # no-reunion: heuristica del detector devolvera not-meeting sin LLM?
    # Forzamos determinismo mockeando el detector en email_tool.
    import app.tools.email_tool as et
    import dataclasses

    @dataclasses.dataclass(frozen=True)
    class _Det:
        is_meeting_request: bool = False
        datetime_iso: str = ""
        reason: str = "mock"

    async def fake_detect(subject, body):
        return _Det()
    monkeypatch.setattr(et, "detect_meeting_proposal", fake_detect)
    return tool


@pytest.mark.anyio
async def test_respond_to_email_draft(respond_setup):
    """Aunque la regla sea alert_only/propose, la orden manual ejecuta:
    el click del usuario es el consentimiento."""
    r = await svc.respond_to_email("mail-x", "draft")
    assert r["ok"] is True, r
    assert r["action"] == "borrador_creado"
    tool = respond_setup
    actions = [a for a, _ in tool.executed]
    assert "create_draft" in actions and "send_email" not in actions


@pytest.mark.anyio
async def test_respond_to_email_send(respond_setup):
    r = await svc.respond_to_email("mail-x", "send")
    assert r["ok"] is True
    assert r["action"] == "respuesta_enviada"
    tool = respond_setup
    sent = [p for a, p in tool.executed if a == "send_email"]
    assert sent and sent[0]["to"] == "losmagnoviajes@gmail.com"
    assert "abrazo" in sent[0]["body"]


def test_respond_endpoint_desde_alerta(client, respond_setup, monkeypatch, db_session):
    from app.db.models import EmailActivityLog
    from app.api.endpoints import email_activity as ea
    monkeypatch.setattr(ea.google_auth, "is_connected", lambda: True)

    entry = EmailActivityLog(
        email_id="mail-x", sender="Los Magno Viajes <losmagnoviajes@gmail.com>",
        subject="Consulta", snippet="Hola", action_type="alert", read=False,
    )
    db_session.add(entry); db_session.commit()

    r = client.post(f"/api/email/activity/{entry.id}/respond?mode=send")
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True

    # la alerta queda marcada como leida y se registro la accion
    acts = client.get("/api/email/activity").json()["items"]
    original = [a for a in acts if a["id"] == entry.id][0]
    assert original["read"] is True
    assert any(a["action_type"] == "sent" and a["details"].get("manual_action") for a in acts)


def test_respond_endpoint_validaciones(client, monkeypatch):
    from app.api.endpoints import email_activity as ea
    monkeypatch.setattr(ea.google_auth, "is_connected", lambda: True)
    assert client.post("/api/email/activity/999999/respond?mode=send").status_code == 404
    assert client.post("/api/email/activity/1/respond?mode=yolo").status_code == 422


# ----------------------------------------------------------------------
# 2026-07-02 (bugs reportados): <think> en el email + respuesta a uno mismo
# ----------------------------------------------------------------------

def test_strip_reasoning_quita_think():
    from app.tools.email_tool import strip_reasoning
    raw = "<think> The user wants me to draft... Let me draft this: </think> Hola Alejandro, gracias por tu propuesta."
    assert strip_reasoning(raw) == "Hola Alejandro, gracias por tu propuesta."


def test_strip_reasoning_variantes():
    from app.tools.email_tool import strip_reasoning
    assert strip_reasoning("<thinking>bla</thinking>Respuesta") == "Respuesta"
    assert strip_reasoning("sin think") == "sin think"
    # bloque sin cerrar: no hay respuesta utilizable -> vacio (fallback)
    assert strip_reasoning("<think>pensando sin parar...") == ""
    # cierre huerfano al principio
    assert strip_reasoning("razonamiento previo</think>Hola!") == "Hola!"
    # multiples bloques
    assert strip_reasoning("<think>a</think>Hola<think>b</think>") == "Hola"


@pytest.mark.anyio
async def test_generate_ai_reply_sin_think(monkeypatch):
    class FakeAI:
        async def chat(self, message, system_prompt=None):
            return {"response": "<think>drafting...</think>Nos vemos el jueves!", "error": False}
    import app.ai.ai_manager as aim
    monkeypatch.setattr(aim, "ai_manager", FakeAI())
    out = await svc.generate_ai_reply("responde", "a@b.com", "s", "b")
    assert out == "Nos vemos el jueves!"
    assert "<think>" not in out


@pytest.mark.anyio
async def test_respond_nunca_a_uno_mismo(monkeypatch, client):
    """El email fetched dice From = MI PROPIA cuenta -> se descarta y se usa
    el sender guardado en la entrada del dashboard."""
    client.post("/api/email/auto-reply/rules", json={
        "name": "Guard", "sender_emails": ["losmagnoviajes@gmail.com"],
        "action": "auto_send", "autonomy": "auto", "ai_prompt": "Responde bien",
    })
    tool = FakeRespondTool({
        "from": "Alexandros Olmo <alexandros.olmo.magno@gmail.com>",  # yo mismo!
        "reply_to": "",
        "subject": "Reunion",
        "body_text": "Podemos vernos?",
    })
    monkeypatch.setattr(svc, "_email_tool", lambda: tool)
    monkeypatch.setattr(svc.google_auth, "get_connected_email",
                        lambda: "alexandros.olmo.magno@gmail.com")

    async def fake_ai(prompt, sender, subject, body="", extra_context=""):
        return "Claro, hablemos."
    monkeypatch.setattr(svc, "generate_ai_reply", fake_ai)
    import app.tools.email_tool as et
    import dataclasses

    @dataclasses.dataclass(frozen=True)
    class _Det:
        is_meeting_request: bool = False
        datetime_iso: str = ""
        reason: str = "mock"
    async def fake_detect(subject, body):
        return _Det()
    monkeypatch.setattr(et, "detect_meeting_proposal", fake_detect)

    r = await svc.respond_to_email(
        "mail-y", "send",
        fallback_sender="Los Magno Viajes <losmagnoviajes@gmail.com>",
    )
    assert r["ok"] is True, r
    assert r["sent_to"] == "losmagnoviajes@gmail.com"  # NUNCA mi propia cuenta
    sent = [p for a2, p in tool.executed if a2 == "send_email"]
    assert sent[0]["to"] == "losmagnoviajes@gmail.com"


@pytest.mark.anyio
async def test_respond_todos_candidatos_propios_error(monkeypatch):
    tool = FakeRespondTool({
        "from": "alexandros.olmo.magno@gmail.com",
        "reply_to": "", "subject": "x", "body_text": "y",
    })
    monkeypatch.setattr(svc, "_email_tool", lambda: tool)
    monkeypatch.setattr(svc.google_auth, "get_connected_email",
                        lambda: "alexandros.olmo.magno@gmail.com")
    r = await svc.respond_to_email("mail-z", "send",
                                   fallback_sender="alexandros.olmo.magno@gmail.com")
    assert r["ok"] is False
    assert "propia cuenta" in r["detail"]


@pytest.mark.anyio
async def test_respond_prefiere_reply_to(monkeypatch, client):
    client.post("/api/email/auto-reply/rules", json={
        "name": "ReplyTo", "sender_emails": ["losmagnoviajes@gmail.com"],
        "action": "auto_send", "autonomy": "auto", "ai_prompt": "Responde",
    })
    tool = FakeRespondTool({
        "from": "Los Magno Viajes <losmagnoviajes@gmail.com>",
        "reply_to": "agenda@losmagno.com",
        "subject": "Reunion", "body_text": "hola",
    })
    monkeypatch.setattr(svc, "_email_tool", lambda: tool)
    monkeypatch.setattr(svc.google_auth, "get_connected_email", lambda: "yo@gmail.com")

    async def fake_ai(*a, **k):
        return "Vale!"
    monkeypatch.setattr(svc, "generate_ai_reply", fake_ai)
    import app.tools.email_tool as et
    import dataclasses

    @dataclasses.dataclass(frozen=True)
    class _Det:
        is_meeting_request: bool = False
        datetime_iso: str = ""
        reason: str = "mock"
    async def fake_detect(subject, body):
        return _Det()
    monkeypatch.setattr(et, "detect_meeting_proposal", fake_detect)

    r = await svc.respond_to_email("mail-rt", "send")
    assert r["ok"] is True and r["sent_to"] == "agenda@losmagno.com"
