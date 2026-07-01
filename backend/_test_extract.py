"""Debug: por qué el matching dice 'no hay regla que matchee'?"""
import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(".env")
from app.tools.email_tool import _extract_email_address, _extract_domain

# El sender real del email
sender_raw = "Alejandro Olmo cuevas <losmagnoviajes@gmail.com>"
print(f"Sender raw: {sender_raw!r}")
print(f"Email extraido: {_extract_email_address(sender_raw)!r}")
print(f"Domain extraido: {_extract_domain(sender_raw)!r}")

# Test con la regla
rule_emails = ["losmagnoviajes@gmail.com"]
extracted = _extract_email_address(sender_raw)
print(f"\nRule emails: {rule_emails}")
print(f"Match check: {extracted in rule_emails}")
print(f"Match equals: {extracted == rule_emails[0]}")
print(f"Match lower: {extracted.lower() == rule_emails[0].lower()}")