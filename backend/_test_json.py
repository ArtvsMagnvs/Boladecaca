import json
raw = '["losmagnoviajes@gmail.com"]'
print(f"raw: {raw!r}")
print(f"type: {type(raw).__name__}")
try:
    parsed = json.loads(raw)
    print(f"parsed: {parsed!r}")
    print(f"type: {type(parsed).__name__}")
    print(f"is list: {isinstance(parsed, list)}")
    print(f"len: {len(parsed)}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

# Tambien test sin comillas
raw2 = '[losmagnoviajes@gmail.com]'
print(f"\nraw2: {raw2!r}")
try:
    parsed = json.loads(raw2)
    print(f"parsed: {parsed!r}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")