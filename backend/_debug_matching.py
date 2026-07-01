"""Debug: simulo EXACTAMENTE lo que hace process_inbox para el email real."""
import sys
import json
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(".env")

from app.db.database import SessionLocal
from app.db.models import EmailAutoReplyRule
from app.tools.email_tool import _extract_email_address, _extract_domain

# Email real del usuario (de la respuesta de la API)
sender = "Alejandro Olmo cuevas <losmagnoviajes@gmail.com>"
subject = "Reunion"

print("=== DEBUG MATCHING EN VIVO ===\n")

# 1) Extraer email y domain (como hace process_inbox)
sender_email = _extract_email_address(sender)
sender_domain = _extract_domain(sender)
print(f"sender_email extraido: {sender_email!r}")
print(f"sender_domain extraido: {sender_domain!r}")

# 2) Cargar rules de BD (como hace process_inbox)
db = SessionLocal()
try:
    rules = db.query(EmailAutoReplyRule).filter(
        EmailAutoReplyRule.enabled == True
    ).all()
    print(f"\nReglas enabled cargadas: {len(rules)}")

    rules_data = []
    for r in rules:
        try:
            emails = json.loads(r.sender_emails or "[]")
        except Exception:
            emails = []
        try:
            domains = json.loads(r.sender_domains or "[]")
        except Exception:
            domains = []
        rules_data.append({
            "id": r.id,
            "name": r.name,
            "sender_emails": emails,
            "sender_domains": domains,
            "matching": r.matching,
            "pattern": r.pattern,
            "reply_template": r.reply_template,
            "action": getattr(r, "action", "auto_send"),
            "detect_meeting_with_ia": getattr(r, "detect_meeting_with_ia", True),
        })
        print(f"  id={r.id} name={r.name!r} sender_emails={emails} sender_domains={domains}")
finally:
    db.close()

# 3) Simular el matching
print("\n=== SIMULANDO MATCHING ===")
matched_rule = None

# Primero: sender_emails exactos
for r in rules_data:
    print(f"\nEvaluando regla id={r['id']}:")
    print(f"  r['sender_emails'] = {r['sender_emails']!r}")
    print(f"  sender_email = {sender_email!r}")
    if r["sender_emails"]:
        print(f"  Truthy check: {bool(r['sender_emails'])}")
        contains = sender_email in r["sender_emails"]
        print(f"  {sender_email!r} in {r['sender_emails']!r} = {contains}")
        if contains:
            matched_rule = r
            print(f"  >>> MATCH ENCONTRADO")
            break

if matched_rule:
    print(f"\n>>> REGLA SELECCIONADA: id={matched_rule['id']} name={matched_rule['name']!r}")
else:
    print(f"\n>>> NINGUNA REGLA MATCHEA")