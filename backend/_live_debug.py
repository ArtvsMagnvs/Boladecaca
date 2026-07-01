"""Verificacion directa: que tiene sender_emails en BD?"""
import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(".env")
from app.db.database import SessionLocal
from app.db.models import EmailAutoReplyRule
import json

db = SessionLocal()
try:
    rules = db.query(EmailAutoReplyRule).filter(EmailAutoReplyRule.enabled == True).all()
    print(f"Total enabled rules: {len(rules)}")
    for r in rules:
        print(f"\nRule id={r.id} name={r.name!r}")
        print(f"  r.sender_emails raw = {r.sender_emails!r}")
        print(f"  r.sender_emails type = {type(r.sender_emails).__name__}")
        # Simular exactamente lo que hace process_inbox
        result = json.loads(r.sender_emails or "[]")
        print(f"  json.loads(r.sender_emails or '[]') = {result!r}")
finally:
    db.close()