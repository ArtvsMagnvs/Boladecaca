"""Test minimal - solo ASCII."""
LOG = open("_test_log.txt", "w", encoding="utf-8")
def log(msg):
    LOG.write(msg + "\n")
    LOG.flush()

log("STEP 1: start")
import sys
log("STEP 2: sys imported")
sys.path.insert(0, ".")
log("STEP 3: path added")
from dotenv import load_dotenv
log("STEP 4: dotenv imported")
load_dotenv(".env")
log("STEP 5: dotenv loaded")
from app.db.database import SessionLocal
log("STEP 6: SessionLocal imported")
from app.db.models import MeetingProposal
log("STEP 7: MeetingProposal imported")
db = SessionLocal()
log("STEP 8: SessionLocal instance")
count = db.query(MeetingProposal).count()
log(f"STEP 9: count={count}")
db.close()
log("STEP 10: done")
LOG.close()