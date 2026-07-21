# scripts/mission_report.py — timeline legible de una misión (doc 31, 2026-07-21)
#
# Uso (backend corriendo o no — lee la BD directamente):
#   python scripts/mission_report.py <mission_id>
#   python scripts/mission_report.py --aggregate 24    # reporte agregado (horas)
#   python scripts/mission_report.py --recent          # últimas 10 misiones con telemetría
#
# La herramienta del ciclo revisión→test→mejora: qué modelo hizo cada paso,
# cuánto tardó, qué tools fallaron.
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _fmt_ms(ms) -> str:
    if ms is None:
        return "—"
    return f"{ms / 1000:.1f}s" if ms >= 1000 else f"{ms}ms"


def print_timeline(mission_id: str) -> None:
    import app.telemetry as telemetry

    data = telemetry.mission_timeline(mission_id)
    if not data["events"]:
        print(f"Sin telemetría para {mission_id}")
        return
    print(f"\n═══ Misión {mission_id} — {data['summary']['event_count']} eventos, "
          f"total {_fmt_ms(data['summary']['total_ms'])} ═══")
    for e in data["events"]:
        ok = "✓" if e["ok"] else ("✗" if e["ok"] is False else " ")
        who = f" [{e['provider']}:{e['model']}]" if e["provider"] else ""
        dur = f" ({_fmt_ms(e['duration_ms'])})" if e["duration_ms"] is not None else ""
        det = f" — {e['detail']}" if e["detail"] else ""
        print(f"  {ok} {e['stage']:<12} {e['name'] or '':<28}{who}{dur}{det}")
    s = data["summary"]
    if s["llm_by_model"]:
        print("  ── LLM por modelo:")
        for k, v in sorted(s["llm_by_model"].items(), key=lambda x: -x[1]["ms"]):
            print(f"     {k}: {v['calls']} llamadas, {_fmt_ms(v['ms'])} total"
                  + (f", {v['fails']} fallos" if v["fails"] else ""))
    if s["tools"]:
        print("  ── Tools:")
        for k, v in sorted(s["tools"].items(), key=lambda x: -x[1]["calls"]):
            print(f"     {k}: {v['calls']}x, {_fmt_ms(v['ms'])} total"
                  + (f", {v['fails']} fallos" if v["fails"] else ""))


def print_aggregate(hours: int) -> None:
    import app.telemetry as telemetry

    r = telemetry.aggregate_report(hours)
    print(f"\n═══ Reporte agregado — últimas {hours}h ═══")
    m = r["missions"]
    print(f"Misiones: {m['total']} ({m['ok']} ok / {m['failed']} failed)"
          + (f", media {_fmt_ms(m.get('avg_ms'))}" if m.get("avg_ms") else ""))
    print("\nLLM por capacidad|modelo (medio/máximo):")
    for k, v in sorted(r["llm"].items(), key=lambda x: -x[1]["ms"]):
        print(f"  {k}: {v['calls']}x — avg {_fmt_ms(v['avg_ms'])}, max {_fmt_ms(v['max_ms'])}"
              + (f", {v['fails']} fallos" if v["fails"] else ""))
    print("\nTools:")
    for k, v in sorted(r["tools"].items(), key=lambda x: -x[1]["calls"]):
        rate = 100 * (1 - v["fails"] / v["calls"]) if v["calls"] else 0
        print(f"  {k}: {v['calls']}x — avg {_fmt_ms(v['avg_ms'])}, éxito {rate:.0f}%")
    if r["recent_errors"]:
        print("\nÚltimos errores:")
        for e in r["recent_errors"][:10]:
            print(f"  [{e['ts']}] {e['stage']} {e['name'] or ''} (misión {e['mission_id']}) {e['detail'] or ''}")


def print_recent() -> None:
    from app.db.database import SessionLocal
    from app.telemetry.models import MissionEvent

    db = SessionLocal()
    try:
        rows = (db.query(MissionEvent.mission_id)
                .filter(MissionEvent.mission_id.isnot(None))
                .order_by(MissionEvent.id.desc()).limit(400).all())
    finally:
        db.close()
    seen: list[str] = []
    for (mid,) in rows:
        if mid not in seen:
            seen.append(mid)
        if len(seen) >= 10:
            break
    print("Últimas misiones con telemetría:")
    for mid in seen:
        print(f"  {mid}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
    elif args[0] == "--aggregate":
        print_aggregate(int(args[1]) if len(args) > 1 else 24)
    elif args[0] == "--recent":
        print_recent()
    else:
        print_timeline(args[0])
