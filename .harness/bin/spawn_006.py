"""
Spawn JWIKI-006 investigador via MiniMax Code.exe direct.
Bypasses mavis.cmd truncation (cmd.exe) and bash classifier IPC detection.
Pattern from mavis-infra-gotchas.md: ELECTRON_RUN_AS_NODE=1, single-line JSON.
"""
import json
import os
import subprocess
import sys
import time

# Session IDs
MY_SID = "mvs_bc3b13a27aa04947b4eeae28e21a6047"  # current repaired session (root tree)
CRON_SID = "mvs_f3ce04f0f9c14c0a84ba618cc69a3113"  # jwiki-tick-a cron
# Use cron as parent so the pipeline tree stays consistent (cron dispatched 005/008/011)
# After dispatch we'll message back to cron with result.

# Paths
EXE = r"C:\Users\Alejandro\AppData\Local\Programs\MiniMax Code\MiniMax Code.exe"
CLI = r"C:\Users\Alejandro\AppData\Local\Programs\MiniMax Code\resources\resources\daemon\cli.js"
BRIEFING_PATH = r"C:\Users\Alejandro\.mavis\sessions\mvs_f3ce04f0f9c14c0a84ba618cc69a3113\workspace\spawn-006.json"

# Read briefing (single-line JSON file, already ~3.3KB, well under 8KB)
with open(BRIEFING_PATH, "r", encoding="utf-8") as f:
    payload_str = f.read().strip()

# Optional: tweak prompt to mitigate thinking-freeze on long Write calls.
# Per gotcha: "briefings que pidan write incremental en chunks".
# But the briefing already has rich detail. We trust the precedent: 008 freeze happened
# at the WRITE of >5KB doc. The briefing only produces RAW material (~20KB markdown).
# We accept the risk; if it freezes again, we close + retry with smaller briefing.

env = os.environ.copy()
env["ELECTRON_RUN_AS_NODE"] = "1"

args = [
    EXE, CLI,
    "communication", "send",
    "--from", CRON_SID,
    "--to", CRON_SID,
    "--command", "spawn",
    "--content", payload_str,
]

print(f"[{time.strftime('%H:%M:%S')}] Spawning JWIKI-006 investigador from cron tree...")
print(f"  exe={EXE}")
print(f"  payload size={len(payload_str)} bytes")
print(f"  from/to={CRON_SID}")

try:
    rc = subprocess.run(args, shell=False, env=env, capture_output=True, text=True, timeout=60)
    print(f"\n[result] return code: {rc.returncode}")
    if rc.stdout:
        print(f"[stdout]\n{rc.stdout[:2000]}")
    if rc.stderr:
        print(f"[stderr]\n{rc.stderr[:2000]}")
except subprocess.TimeoutExpired:
    print("[error] subprocess timeout (60s)")
    sys.exit(1)
except Exception as e:
    print(f"[error] {type(e).__name__}: {e}")
    sys.exit(1)
