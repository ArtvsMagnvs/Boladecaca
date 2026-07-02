# tests/test_email_autonomy_digest.py
#
# Sprint 4 (PLAN_MAESTRO_2026): B6 autonomia gradual por regla (patron
# Inbox Zero: propose -> feedback -> auto) y B7 digest diario.

import pytest

from app.services.email_service import (
    effective_rule_action,
    rule_can_promote,
    PROMOTE_THRESHOLD,
    save_triage,
)


# ----------------------------------------------------------------------
# B6 — logica pura
# ----------------------------------------------------------------------

@pytest.mark.parametrize("action,autonomy,expected", [
    ("auto_send", "propose", "create_draft"),   # el gating clave
    ("auto_send", "auto", "auto_send"),
    ("create_draft", "propose", "create_draft"),
    ("create_draft", "auto", "create_draft"),
    ("alert_only", "propose", "alert_only"),
    ("alert_only", "auto", "alert_only"),
])
def test_effective_rule_action(action, autonomy, expected):
    assert effective_rule_action(action, autonomy) == expected


def test_can_promote_umbral():
    assert not rule_can_promote("propose", PROMOTE_THRESHOLD - 1, 0, 0)
    assert rule_can_promote("propose", PROMOTE_THRESHOLD, 0, 0)
    # editadas/rechazadas restan
    assert not rule_can_promote("propose", PROMOTE_THRESHOLD, 1, 0)
    assert rule_can_promote("propose", PROMOTE_THRESHOLD + 2, 1, 1)
    # una regla ya auto no se "promociona"
    assert not rule_can_promote("auto", 99, 0, 0)


# ----------------------------------------------------------------------
# B6 — API end-to-end (BD temporal, sin Gmail)
# ----------------------------------------------------------------------

def _create_rule(client, name="Regla test"):
    r = client.post("/api/email/auto-reply/rules", json={
        "name": name,
        "sender_emails": ["jefe@empresa.com"],
        "action": "auto_send",
        "reply_template": "Recibido, gracias {sender}",
    })
    assert r.status_code == 201, r.text
    rules = client.get("/api/email/auto-reply/rules").json()["rules"]
    return [x for x in rules if x["name"] == name][0]


def test_regla_nueva_nace_en_propose(client):
    rule = _create_rule(client)
    assert rule["autonomy"] == "propose"
    assert rule["can_promote"] is False
    assert rule["approved_count"] == 0


def test_feedback_y_promocion(client):
    rule = _create_rule(client, "Regla feedback")
    # 4 aprobadas: aun no
    for _ in range(PROMOTE_THRESHOLD - 1):
        r = client.post(f"/api/email/auto-reply/rules/{rule['id']}/feedback",
                        json={"result": "approved"})
        assert r.status_code == 200
        assert r.json()["can_promote"] is False
    # 5a aprobada: ya puede
    r = client.post(f"/api/email/auto-reply/rules/{rule['id']}/feedback",
                    json={"result": "approved"})
    assert r.json()["can_promote"] is True
    assert r.json()["approved_count"] == PROMOTE_THRESHOLD

    # promocion via PATCH (misma ruta publica de siempre)
    r = client.patch(f"/api/email/auto-reply/rules/{rule['id']}",
                     json={"autonomy": "auto"})
    assert r.status_code == 200
    rules = client.get("/api/email/auto-reply/rules").json()["rules"]
    mine = [x for x in rules if x["id"] == rule["id"]][0]
    assert mine["autonomy"] == "auto"
    assert mine["can_promote"] is False  # ya es auto


def test_feedback_validaciones(client):
    rule = _create_rule(client, "Regla valida")
    assert client.post(f"/api/email/auto-reply/rules/{rule['id']}/feedback",
                       json={"result": "meh"}).status_code == 400
    assert client.post("/api/email/auto-reply/rules/999999/feedback",
                       json={"result": "approved"}).status_code == 404


def test_patch_autonomy_invalida_400(client):
    rule = _create_rule(client, "Regla patch")
    r = client.patch(f"/api/email/auto-reply/rules/{rule['id']}",
                     json={"autonomy": "yolo"})
    assert r.status_code == 400


# ----------------------------------------------------------------------
# B7 — digest diario
# ----------------------------------------------------------------------

def test_digest_vacio_shape(client):
    r = client.get("/api/email/digest")
    assert r.status_code == 200
    d = r.json()
    for key in ("date", "triage_counts", "triaged_total", "urgent_pending",
                "drafts_awaiting", "meetings", "rules"):
        assert key in d
    assert d["triaged_total"] == 0
    assert d["meetings"] == {"today": 0, "pending": 0}


def test_digest_con_datos(client, db_session):
    from app.db.models import EmailActivityLog
    # triaje de hoy
    save_triage("dg1", "a@b.com", "s1", "urgente", "heuristic")
    save_triage("dg2", "c@d.com", "s2", "fyi", "fallback")
    # alerta y borrador sin leer
    db_session.add(EmailActivityLog(email_id="dg1", sender="A", subject="s1",
                                    action_type="alert", read=False))
    db_session.add(EmailActivityLog(email_id="dg3", sender="B", subject="s3",
                                    action_type="draft", read=False, rule_id=1))
    db_session.commit()
    # regla activa en propose
    _create_rule(client, "Regla digest")

    d = client.get("/api/email/digest").json()
    assert d["triage_counts"] == {"urgente": 1, "fyi": 1}
    assert d["triaged_total"] == 2
    assert d["urgent_pending"] == 1
    assert d["drafts_awaiting"] == 1
    assert d["rules"]["enabled"] >= 1
    assert d["rules"]["propose"] >= 1


def test_digest_fecha_invalida_400(client):
    assert client.get("/api/email/digest?date=ayer").status_code == 400


# ----------------------------------------------------------------------
# Regresion (2026-07-02, bug reportado): los eventos del calendario LOCAL
# de Aithera no contaban como "ocupado" en el chequeo de conflictos de
# reuniones (solo CalendarAvailability + Google Calendar).
# ----------------------------------------------------------------------

def test_evento_local_cuenta_como_ocupado(client, db_session):
    from datetime import datetime, timedelta
    from app.db.models import CalendarEvent
    from app.services.email_service import (
        local_events_for_date,
        detect_calendar_conflicts,
        _parse_iso,
    )

    dia = datetime(2026, 7, 10)
    # Evento local en el calendario de Aithera: 10:00-11:00
    db_session.add(CalendarEvent(
        title="Ocupado (marcado en Aithera)",
        start_date=dia.replace(hour=10),
        end_date=dia.replace(hour=11),
        all_day=False,
    ))
    db_session.commit()

    eventos = local_events_for_date(dia.date())
    assert len(eventos) == 1

    # Reunion propuesta a las 10:30 -> CONFLICTO (antes se daba por libre)
    assert detect_calendar_conflicts(
        dia.replace(hour=10, minute=30),
        dia.replace(hour=11, minute=30),
        [],           # sin bloques de disponibilidad
        eventos,      # SOLO el evento local
    ) is True

    # Reunion a las 15:00 -> libre
    assert detect_calendar_conflicts(
        dia.replace(hour=15),
        dia.replace(hour=16),
        [],
        eventos,
    ) is False


def test_evento_all_day_bloquea_todo_el_dia(client, db_session):
    from datetime import datetime
    from app.db.models import CalendarEvent
    from app.services.email_service import local_events_for_date, detect_calendar_conflicts

    dia = datetime(2026, 7, 11)
    db_session.add(CalendarEvent(
        title="Fuera todo el dia", start_date=dia, all_day=True,
    ))
    db_session.commit()
    eventos = local_events_for_date(dia.date())
    assert detect_calendar_conflicts(
        dia.replace(hour=9), dia.replace(hour=10), [], eventos,
    ) is True


def test_evento_local_sin_end_date_asume_1h(client, db_session):
    from datetime import datetime
    from app.db.models import CalendarEvent
    from app.services.email_service import local_events_for_date

    dia = datetime(2026, 7, 12)
    db_session.add(CalendarEvent(title="Sin fin", start_date=dia.replace(hour=9)))
    db_session.commit()
    ev = local_events_for_date(dia.date())[0]
    assert ev["end"].endswith("10:00:00")
