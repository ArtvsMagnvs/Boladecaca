"""Cleanup rapido: borrar regla legacy #5 y listar estado."""
import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(".env")
from app.db.database import SessionLocal
from app.db.models import EmailAutoReplyRule, MeetingProposal, EmailActivityLog

LOG = open("_cleanup_log.txt", "w", encoding="utf-8")
def log(msg):
    LOG.write(msg + "\n")
    LOG.flush()

log("=" * 70)
log(" CLEANUP: borrar regla legacy #5 que bloquea a la regla #8")
log("=" * 70)

db = SessionLocal()
try:
    r5 = db.query(EmailAutoReplyRule).filter(EmailAutoReplyRule.id == 5).first()
    if r5:
        log(f"Encontrada regla id=5: name={r5.name!r}")
        log(f"  sender_emails={r5.sender_emails}")
        log(f"  matching={r5.matching} pattern={r5.pattern!r}")
        log(f"  action={r5.action}")
        log(f"  detect_meeting={r5.detect_meeting_with_ia}")
        log(f"  reply_template={r5.reply_template!r}")
        db.delete(r5)
        db.commit()
        log(f"  ELIMINADA regla id=5")
    else:
        log("No existe regla id=5 (ya borrada?)")

    log("")
    log("Reglas restantes enabled:")
    for r in db.query(EmailAutoReplyRule).filter(EmailAutoReplyRule.enabled == True).all():
        log(f"  id={r.id} name={r.name!r} action={r.action} detect_meeting={r.detect_meeting_with_ia}")
        log(f"    sender_emails={r.sender_emails}")

    log("")
    log("Tambien limpio propuestas y activity log antiguas (para forzar reprocesamiento):")
    np = db.query(MeetingProposal).delete()
    na = db.query(EmailActivityLog).delete()
    db.commit()
    log(f"  Eliminadas {np} propuestas y {na} activity logs")
finally:
    db.close()

LOG.close()