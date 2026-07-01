"""Reusable spawn helper for JWIKI cron ticks.

Bypasses mavis.cmd (CreateProcess can't directly exec .cmd/.bat) and calls the
underlying electron binary directly with ELECTRON_RUN_AS_NODE=1, replicating
the mavis CLI.

Usage:
    python spawn_agent.py --from <session_id> --to <session_id> \
        --payload-json <path-to-json-or-json-string>

Reads the JSON payload (agent + prompt) and dispatches `mavis communication
send --command spawn --content <json>` to the target session.

This file lives at ticks/spawn_agent.py. It is intentionally parameter-only so
each tick can inject its own payload via JSON file (no shell-escape headaches).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


EXE_PATH = Path(r"C:\Users\Alejandro\AppData\Local\Programs\MiniMax Code\MiniMax Code.exe")
CLI_PATH = Path(r"C:\Users\Alejandro\AppData\Local\Programs\MiniMax Code\resources\resources\daemon\cli.js")


def run_spawn(from_session: str, to_session: str, payload: dict) -> dict:
    # Build args list (no shell, no escape issues with quotes in payload)
    args = [
        str(EXE_PATH),
        str(CLI_PATH),
        "communication",
        "send",
        "--from", from_session,
        "--to", to_session,
        "--command", "spawn",
        "--content", json.dumps(payload, ensure_ascii=False),
    ]

    env = os.environ.copy()
    env["ELECTRON_RUN_AS_NODE"] = "1"

    print(f"[spawn_agent] launching: {EXE_PATH.name} cli.js communication send ...", file=sys.stderr)
    proc = subprocess.run(
        args,
        shell=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return {
        "rc": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="from_session", required=True, help="Sender session id")
    parser.add_argument("--to", dest="to_session", required=True, help="Target session id (self for spawn)")
    parser.add_argument(
        "--payload-json",
        dest="payload_json",
        required=True,
        help="Path to JSON file with {agent, prompt} OR '-' for stdin",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print payload without executing")
    args = parser.parse_args()

    if args.payload_json == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(args.payload_json).read_text(encoding="utf-8")
    payload = json.loads(raw)

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    result = run_spawn(args.from_session, args.to_session, payload)
    print("RC:", result["rc"])
    print("STDOUT:", result["stdout"])
    print("STDERR:", result["stderr"])
    return result["rc"]


if __name__ == "__main__":
    raise SystemExit(main())
