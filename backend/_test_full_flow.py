"""Test completo del flujo."""
import sys
import json
import asyncio
import io

# Force UTF-8 (para evitar encoding issues en consolas Windows)
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Log a archivo (evita problemas de buffering en PowerShell)
LOG = open("_test_full_log.txt", "w", encoding="utf-8")
def log(msg):
    LOG.write(msg + "\n")
    LOG.flush()

log("=" * 70)
log(" TEST COMPLETO DEL FLUJO: matching + IA + calendar + contrapropuesta")
log("=" * 70)

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(".env")

from app.db.database import SessionLocal
from app.db.models import EmailAutoReplyRule, CalendarAvailability, MeetingProposal
from app.tools.email_tool import (
    detect_meeting_proposal,
    extract_meeting_datetime,
    _extract_email_address,
    _extract_domain,
    generate_meeting_reschedule_reply,
)
from datetime import datetime, timedelta

# Limpiar propuestas
log("\n[Cleanup] Limpiando propuestas antiguas (pueden bloquear reprocesamiento)...")
db = SessionLocal()
try:
    deleted = db.query(MeetingProposal).delete()
    db.commit()
    log(f"  Eliminadas {deleted} propuestas")
finally:
    db.close()

# Test 1: detect_meeting_proposal
log("\n" + "=" * 70)
log(" TEST 1: detect_meeting_proposal")
log("=" * 70)

async def test_detect():
    casos = [
        ("Reunion", "Quedamos el 1 de julio a las 11h?"),
        ("Reunion", "Hola, quiero proponerte quedar el 1 de julio a las 11h. Quedamos?"),
        ("Propuesta reunion", "Quedamos el 1 de julio a las 11h?"),
        ("RE:Reunion", "ey, podriamos quedar el 1 de julio a las 11h?"),
    ]
    for subject, body in casos:
        result = await detect_meeting_proposal(subject=subject, body=body)
        log(f"  subj={subject!r}, body={body[:50]!r}")
        log(f"    is_meeting={result['is_meeting_proposal']}, dt={result.get('datetime_iso')}, method={result.get('method')}")
        log(f"    reason={result.get('reason', '')[:100]}")

asyncio.run(test_detect())


# Test 2: Calendar busy check
log("\n" + "=" * 70)
log(" TEST 2: Calendar busy check para 1 julio 11h")
log("=" * 70)

proposed_dt = datetime(2026, 7, 1, 11, 0, 0)
day_blocks = []
db = SessionLocal()
try:
    day_blocks = db.query(CalendarAvailability).filter(
        CalendarAvailability.date == datetime.combine(proposed_dt.date(), datetime.min.time())
    ).all()
    is_busy = any(
        b.status in {"unavailable", "busy"} and b.hour_start <= proposed_dt.hour < b.hour_end
        for b in day_blocks
    )
    log(f"  Bloques en {proposed_dt.date()}: {len(day_blocks)}")
    for b in day_blocks:
        log(f"    {b.hour_start}-{b.hour_end} {b.status} {b.label!r}")
    log(f"  is_busy para {proposed_dt}: {is_busy}")
finally:
    db.close()


# Test 3: find_free_slots
log("\n" + "=" * 70)
log(" TEST 3: find_free_slots para 1 julio y siguientes")
log("=" * 70)

async def test_slots():
    from app.tools.calendar_tool import CalendarTool
    ct = CalendarTool()
    for offset in range(7):
        date_iso = (proposed_dt.date() + timedelta(days=offset)).isoformat()
        r = await ct.execute("find_free_slots", {"date": date_iso, "duration_minutes": 60})
        slots = (r.get("result") or {}).get("slots", [])
        log(f"  {date_iso}: {len(slots)} huecos libres")
        if slots:
            for s in slots[:3]:
                log(f"    {s.get('start')} - {s.get('end')}")
            if offset == 0 or True:
                return slots[0].get("start")
    return None

new_iso = asyncio.run(test_slots())
log(f"\n  Primer hueco libre: {new_iso}")


# Test 4: generar contrapropuesta
log("\n" + "=" * 70)
log(" TEST 4: generate_meeting_reschedule_reply")
log("=" * 70)

async def test_reply():
    if not new_iso:
        log("  No hay huecos, saltando test")
        return
    body = await generate_meeting_reschedule_reply(
        sender="losmagnoviajes@gmail.com",
        subject="Reunion",
        original_body="Hola, quiero proponerte quedar el 1 de julio a las 11h. Quedamos?",
        original_proposed_iso="2026-07-01T11:00:00",
        new_proposed_iso=new_iso,
    )
    log(f"  Reply body ({len(body)} chars):")
    log(f"  ---START---")
    log(body)
    log(f"  ---END---")

asyncio.run(test_reply())


# Test 5: SIMULACION COMPLETA del flujo end-to-end
log("\n" + "=" * 70)
log(" TEST 5: SIMULACION COMPLETA del flujo end-to-end")
log("=" * 70)

async def test_full_simulation():
    """Simula lo que haria process_inbox para un email del usuario."""
    sender_email = "losmagnoviajes@gmail.com"
    subject = "Reunion"
    body = "Hola, quiero proponerte quedar el 1 de julio a las 11h. Quedamos?"

    # 1. Matching
    db = SessionLocal()
    try:
        rules = db.query(EmailAutoReplyRule).filter(
            EmailAutoReplyRule.enabled == True
        ).order_by(EmailAutoReplyRule.created_at.asc()).all()

        # Prioridad
        matched_rule = None
        for r in rules:
            emails = json.loads(r.sender_emails or "[]")
            domains = json.loads(r.sender_domains or "[]")
            if emails and sender_email in emails:
                matched_rule = r
                break
        if not matched_rule:
            for r in rules:
                domains = json.loads(r.sender_domains or "[]")
                if domains and "gmail.com" in domains:
                    matched_rule = r
                    break

        log(f"  1. MATCHING: regla seleccionada = id={matched_rule.id} name={matched_rule.name!r}")
        log(f"     action={matched_rule.action} detect_meeting={matched_rule.detect_meeting_with_ia}")
    finally:
        db.close()

    if not matched_rule:
        log("  NINGUNA REGLA MATCHEA - fin")
        return

    # 2. Deteccion de reunion con IA
    if matched_rule.detect_meeting_with_ia:
        detection = await detect_meeting_proposal(subject=subject, body=body)
        is_meeting = detection["is_meeting_proposal"]
        meeting_dt = detection.get("datetime_iso")
        log(f"  2. IA DETECTION: is_meeting={is_meeting} dt={meeting_dt} method={detection.get('method')}")
        log(f"     reason={detection.get('reason', '')[:100]}")

        if not is_meeting:
            log("  No es reunion, fin")
            return

        # 3. Calendar check
        from datetime import datetime as _dt
        proposed_dt = _dt.fromisoformat(meeting_dt.replace("Z", ""))
        db = SessionLocal()
        try:
            blocks = db.query(CalendarAvailability).filter(
                CalendarAvailability.date == _dt.combine(proposed_dt.date(), _dt.min.time())
            ).all()
            is_busy = any(
                b.status in {"unavailable", "busy"} and b.hour_start <= proposed_dt.hour < b.hour_end
                for b in blocks
            )
        finally:
            db.close()
        log(f"  3. CALENDAR: is_busy={is_busy}")

        # 4. find_free_slots
        if is_busy:
            from app.tools.calendar_tool import CalendarTool
            ct = CalendarTool()
            new_iso_local = None
            for offset in range(7):
                alt_date = (proposed_dt + timedelta(days=offset)).date().isoformat()
                r = await ct.execute("find_free_slots", {"date": alt_date, "duration_minutes": 60})
                slots = (r.get("result") or {}).get("slots", [])
                if slots:
                    new_iso_local = slots[0].get("start")
                    break
            log(f"  4. FIND_FREE_SLOTS: nueva fecha={new_iso_local}")

            if new_iso_local:
                # 5. generate reschedule reply
                reschedule_body = await generate_meeting_reschedule_reply(
                    sender=sender_email,
                    subject=subject,
                    original_body=body,
                    original_proposed_iso=meeting_dt,
                    new_proposed_iso=new_iso_local,
                )
                log(f"  5. AI REPLY ({len(reschedule_body)} chars):")
                log(f"     {reschedule_body[:300]}...")
                log("")
                log(f"  ✅ SIMULACION COMPLETA OK - Sistema responderia correctamente")
            else:
                log(f"  ❌ No hay huecos libres en 7 dias")
        else:
            log(f"  Calendario libre -> se aceptaria la reunion")

asyncio.run(test_full_simulation())

LOG.close()