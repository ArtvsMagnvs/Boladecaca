"""Simple test."""
print("HELLO")
import sys
sys.path.insert(0, ".")
print("sys path added")
from dotenv import load_dotenv
print("dotenv imported")
load_dotenv(".env")
print("dotenv loaded")

from app.db.database import SessionLocal
print("SessionLocal imported")
db = SessionLocal()
print("SessionLocal instance created")
db.close()
print("OK")