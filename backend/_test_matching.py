"""Test directo: simula process_inbox paso a paso con las reglas reales."""
import sys
import json

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(".env")

from app.db.database import SessionLocal
from app.db.models import EmailAutoReplyRule, CalendarAvailability
from app.tools.email_tool import (
    detect_meeting_proposal,
    extract_meeting_datetime,
    _extract_email_address,
    _extract_domain,
)
import asyncio
from datetime import datetime, date

print("=" * 70)
print(" TEST 1: Listar reglas que matchean losmagnoviajes@gmail.com")
print("=" * 70)

db = SessionLocal()
try:
    rules = db.query(EmailAutoReplyRule).filter(
        EmailAutoReplyRule.enabled == True
    ).order_by(EmailAutoReplyRule.created_at.asc()).all()

    sender_email = "losmagnoviajes@gmail.com"
    sender_domain = "gmail.com"
    sender_full = f"Aithera <{sender_email}>"

    matched = []
    for r in rules:
        emails = json.loads(r.sender_emails or "[]")
        domains = json.loads(r.sender_domains or "[]")
        rule_info = {
            "id": r.id, "name": r.name, "action": r.action,
            "detect_meeting_with_ia": r.detect_meeting_with_ia,
            "sender_emails": emails, "sender_domains": domains,
            "matching": r.matching, "pattern": r.pattern,
            "reply_template": (r.reply_template or "")[:60],
            "enabled": r.enabled,
        }
        # Email match
        if emails and sender_email in emails:
            rule_info["match_type"] = "sender_email"
            rule_info["priority"] = 1
            matched.append(rule_info)
            continue
        # Domain match
        if domains and sender_domain in domains:
            rule_info["match_type"] = "sender_domain"
            rule_info["priority"] = 2
            matched.append(rule_info)
            continue
        # Legacy
        if r.pattern and r.pattern != "*":
            if r.matching == "sender_contains" and r.pattern.lower() in sender_full.lower():
                rule_info["match_type"] = "sender_contains"
                rule_info["priority"] = 3
                matched.append(rule_info)

    print(f"Total reglas activas: {len(rules)}")
    print(f"Reglas que matchean losmagnoviajes@gmail.com: {len(matched)}")
    for r in matched:
        print(f"  id={r['id']} name={r['name']!r}")
        print(f"    match_type={r.get('match_type')} priority={r.get('priority')}")
        print(f"    action={r['action']!r} detect_meeting={r['detect_meeting_with_ia']}")
        print(f"    template={r['reply_template']!r}")

    # Ordenar por prioridad (FIX)
    matched.sort(key=lambda x: x.get("priority", 99))
    print()
    print(f"REGLA QUE SE USARIA (tras orden por prioridad):")
    if matched:
        winner = matched[0]
        print(f"  id={winner['id']} name={winner['name']!r}")
        print(f"  action={winner['action']!r} detect_meeting={winner['detect_meeting_with_ia']}")
    else:
        print("  NINGUNA - no hay match")

finally:
    db.close()


print()
print("=" * 70)
print(" TEST 2: Calendario ocupado?")
print("=" * 70)

today = date.today()
print(f"Hoy: {today}")

db = SessionLocal()
try:
    blocks = db.query(CalendarAvailability).limit(20).all()
    print(f"Total bloques en BD: {len(blocks)}")
    for b in blocks[:10]:
        print(f"  date={b.date} hour={b.hour_start}-{b.hour_end} status={b.status} label={b.label!r}")
finally:
    db.close()


print()
print("=" * 70)
print(" TEST 3: Detectar meeting en el email")
print("=" * 70)

async def test_detect():
    result = await detect_meeting_proposal(
        subject="Reunion",
        body="Hola, quiero proponerte quedar el 1 de julio a las 11h. Quedamos?",
    )
    print(f"Detect: {result}")

asyncio.run(test_detect())


print()
print("=" * 70)
print(" TEST 4: Simular bloqueo de calendario para 1 julio 11h")
print("=" * 70)

# El usuario YA tiene 1 julio 8-14 unavailable, asi que is_busy deberia ser True
proposed_dt = datetime(2026, 7, 1, 11, 0, 0)
day_date = datetime.combine(proposed_dt.date(), datetime.min.time())

db = SessionLocal()
try:
    blocks = db.query(CalendarAvailability).filter(
        CalendarAvailability.date == day_date
    ).all()
    print(f"Bloques para {proposed_dt.date()}: {len(blocks)}")
    is_busy = False
    for b in blocks:
        print(f"  {b.hour_start}-{b.hour_end} {b.status} {b.label!r}")
        if b.status in {"unavailable", "busy"} and b.hour_start <= proposed_dt.hour < b.hour_end:
            is_busy = True
            print(f"  >>> MATCH: {b.hour_start}<={proposed_dt.hour}<{b.hour_end} ✓ BUSY")
    print(f"is_busy para 1 julio 11h: {is_busy}")
finally:
    db.close()


print()
print("=" * 70)
print(" TEST 5: Verificar propuestas existentes que podrian BLOQUEAR")
print("=" * 70)

db = SessionLocal()
try:
    from app.db.models import MeetingProposal
    proposals = db.query(MeetingProposal).all()
    print(f"Total propuestas en BD: {len(proposals)}")
    for p in proposals:
        print(f"  id={p.id} sender={p.sender!r} subject={p.subject!r} status={p.status} date={p.original_proposed_datetime}")
finally:
    db.close()