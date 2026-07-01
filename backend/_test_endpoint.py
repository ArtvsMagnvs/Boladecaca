"""Test final: que tiene realmente process-inbox vs /rules"""
import sys
import json
import asyncio

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(".env")

# Simulo el endpoint EXACTAMENTE
from app.db.database import SessionLocal as _SessionLocal
from app.db.models import EmailAutoReplyRule
import json as json_module

db = _SessionLocal()
try:
    rules = db.query(EmailAutoReplyRule).filter(
        EmailAutoReplyRule.enabled == True  # noqa: E712
    ).all()
    rules_data = []
    for r in rules:
        try:
            emails = json_module.loads(r.sender_emails or "[]")
        except Exception as e:
            print(f"EXCEPTION: {e}", flush=True)
            emails = []
        try:
            domains = json_module.loads(r.sender_domains or "[]")
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

    print("rules_data:", json.dumps(rules_data, indent=2, ensure_ascii=False))
finally:
    db.close()