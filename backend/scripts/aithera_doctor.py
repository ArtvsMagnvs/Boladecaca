# scripts/aithera_doctor.py — el comando único de diagnóstico (Sesión C, doc 40)
#
# Uso (backend corriendo o no — lee la BD directamente, READ-ONLY absoluto):
#   python scripts/aithera_doctor.py [--hours 24]
#
# En Windows, si la consola es cp1252, fija PYTHONIOENCODING=utf-8 primero
# (lección de scripts/diagnose_new5.py, campaña 02) — algunos textos llevan
# tildes/símbolos que cp1252 no sabe imprimir:
#   set PYTHONIOENCODING=utf-8 && python scripts/aithera_doctor.py
#
# Qué responde: "¿qué falló y por qué?" con el backend apagado. Antes había
# piezas sueltas (mission_report.py, check_schema_drift en el log de arranque)
# pero nada que las juntara en un solo vistazo (doc 34, hallazgo 3 de la
# Sesión C). Patrón calcado de mission_report.py: sys.path insert + imports de
# app + consulta directa a la BD.
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def collect(hours: int = 24) -> dict:
    """Toda la lógica vive aquí — read-only absoluto, ni un UPDATE. `main()`
    solo imprime lo que esto devuelve, para que sea testeable sin capturar
    stdout."""
    return {
        "hours": hours,
        "missions": _collect_missions(),
        "telemetry": _collect_telemetry(),
        "config_health": _collect_config_health(),
        "schema": _collect_schema(),
        "approvals_pending": _collect_approvals_pending(),
    }


# ---------------------------------------------------------------------------
# 1 — Últimas misiones
# ---------------------------------------------------------------------------
def _collect_missions() -> list[dict]:
    from app.db.database import OrchestratorTrace, SessionLocal
    from app.automation.models import Approval

    db = SessionLocal()
    try:
        rows = (db.query(OrchestratorTrace)
                .order_by(OrchestratorTrace.created_at.desc())
                .limit(10).all())
        # Gates pendientes por mission_id, para marcar las "waiting" que de
        # verdad están esperando al usuario (no solo en un estado transitorio).
        pendientes_mission_ids: set[str] = set()
        try:
            for a in db.query(Approval).filter(Approval.status == "pending").all():
                mid = (a.action_payload or {}).get("mission_id") if a.action_payload else None
                if mid:
                    pendientes_mission_ids.add(mid)
        except Exception:
            pass

        out = []
        for r in rows:
            outcome = (r.outcome or "")[:160]
            esperando = bool(r.state == "waiting" and r.mission_id in pendientes_mission_ids)
            out.append({
                "id": r.id,
                "mission_id": r.mission_id,
                "state": r.state,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "outcome_preview": outcome,
                "waiting_with_gate": esperando,
            })
        return out
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 2 — Telemetría por misión (S3, doc 34) + eventos problemáticos del bucle
# ---------------------------------------------------------------------------
_PROBLEM_EVENTS = {"stalled", "preflight_not_ready", "repeated_failure",
                   "repeated_denial", "grant_denied", "permission_denied"}


def _collect_telemetry() -> dict:
    import app.telemetry as telemetry

    misiones = _collect_missions()
    por_mision: dict[str, dict] = {}
    fallos_tool: dict[str, dict] = {}

    for m in misiones:
        clave = m["mission_id"] or m["id"]
        if not clave:
            continue
        data = telemetry.mission_timeline(clave)
        if not data["events"]:
            continue
        s = data["summary"]
        problemas: dict[str, int] = {}
        for e in data["events"]:
            if e["stage"] == "toolloop" and e["name"] in _PROBLEM_EVENTS:
                problemas[e["name"]] = problemas.get(e["name"], 0) + 1
            if e["stage"] == "tool_call" and e["ok"] is False:
                agg = fallos_tool.setdefault(e["name"] or "?", {"count": 0, "last_error": None})
                agg["count"] += 1
                if e.get("detail"):
                    agg["last_error"] = e["detail"]
        por_mision[clave] = {
            "llm_calls": s.get("llm_calls"),
            "path": s.get("path"),
            "within_budget": s.get("within_budget"),
            "slowest_llm_ms": s.get("slowest_llm_ms"),
            "loop_problems": problemas,
        }

    top_fallos = sorted(fallos_tool.items(), key=lambda kv: -kv[1]["count"])[:5]
    return {"por_mision": por_mision, "top_tool_failures": dict(top_fallos)}


# ---------------------------------------------------------------------------
# 3 — Salud de configuración (nunca las keys, solo sí/no)
# ---------------------------------------------------------------------------
def _collect_config_health() -> dict:
    from app.db.database import AIProviderConfig, SessionLocal

    out: dict = {}
    db = SessionLocal()
    try:
        # Mismo criterio que ai_manager.py: una fila en ai_provider_configs YA
        # significa "configurado" (incluye a los NO_KEY_PROVIDERS, que no
        # llevan api_key pero sí tienen fila).
        proveedores = []
        for p in db.query(AIProviderConfig).all():
            proveedores.append({
                "provider": p.provider,
                "is_configured": True,
                "is_active": bool(p.is_active),
            })
        out["ai_providers"] = proveedores
    except Exception as e:
        out["ai_providers"] = []
        out["ai_providers_error"] = f"{type(e).__name__}: {e}"
    finally:
        db.close()

    try:
        from app.tools.search_tool import _configured_providers
        claves = _configured_providers()
        out["search"] = {k: bool(v) for k, v in claves.items()}
    except Exception as e:
        out["search"] = {}
        out["search_error"] = f"{type(e).__name__}: {e}"

    out["telegram_token_present"] = _config_value("telegram_bot_token") is not None

    try:
        from app.integrations.google_auth import is_connected as _google_connected
        out["google_credentials_present"] = bool(_google_connected())
    except Exception:
        out["google_credentials_present"] = False

    return out


def _config_value(key: str):
    """Lee la tabla Config (key-value) sin asumir su forma exacta — best-effort,
    nunca lanza. Devuelve None si no hay valor o si la lectura falla."""
    try:
        from app.db.database import Config, SessionLocal

        db = SessionLocal()
        try:
            row = db.query(Config).filter(Config.key == key).first()
            valor = getattr(row, "value", None) if row else None
            return valor if valor else None
        finally:
            db.close()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 4 — Desfase de esquema (ya existe, aquí solo se relanza)
# ---------------------------------------------------------------------------
def _collect_schema() -> dict:
    try:
        from app.db.database import check_schema_drift
        return check_schema_drift()
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# 5 — Aprobaciones pendientes (un gate olvidado hace días)
# ---------------------------------------------------------------------------
def _collect_approvals_pending() -> list[dict]:
    from app.automation.models import Approval
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        rows = (db.query(Approval)
                .filter(Approval.status == "pending")
                .order_by(Approval.requested_at.asc()).all())
        now = datetime.utcnow()
        out = []
        for a in rows:
            edad_h = None
            if a.requested_at:
                edad_h = round((now - a.requested_at).total_seconds() / 3600, 1)
            out.append({
                "id": a.id,
                "kind": a.kind,
                "action_type": a.action_type,
                "mission_id": (a.action_payload or {}).get("mission_id") if a.action_payload else None,
                "age_hours": edad_h,
            })
        return out
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Impresión
# ---------------------------------------------------------------------------
def _print(data: dict) -> None:
    print(f"\n═══ Aithera Doctor — últimas {data['hours']}h ═══\n")

    print("── Misiones recientes ──")
    if not data["missions"]:
        print("  (sin misiones registradas)")
    for m in data["missions"]:
        marca = "⚠ ESPERANDO — con gate pendiente" if m["waiting_with_gate"] else m["state"]
        print(f"  [{marca}] {m['mission_id'] or m['id']} — {m['created_at']}")
        if m["outcome_preview"]:
            print(f"      {m['outcome_preview']}")

    print("\n── Telemetría ──")
    tel = data["telemetry"]
    if not tel["por_mision"]:
        print("  (sin telemetría en el rango)")
    for mid, s in tel["por_mision"].items():
        presupuesto = "OK" if s["within_budget"] else "EXCEDIDO"
        print(f"  {mid}: {s['llm_calls']} llamadas LLM, camino={s['path']}, "
              f"presupuesto {presupuesto}, más lenta {s['slowest_llm_ms']}ms")
        if s["loop_problems"]:
            print(f"      problemas de bucle: {s['loop_problems']}")
    if tel["top_tool_failures"]:
        print("  ── Tools que más fallan:")
        for nombre, info in tel["top_tool_failures"].items():
            print(f"     {nombre}: {info['count']}x — último error: {info['last_error']}")

    print("\n── Salud de configuración ──")
    ch = data["config_health"]
    for p in ch.get("ai_providers", []):
        activo = " (ACTIVO)" if p["is_active"] else ""
        print(f"  IA {p['provider']}: {'configurado' if p['is_configured'] else 'sin configurar'}{activo}")
    for prov, ok in ch.get("search", {}).items():
        print(f"  búsqueda {prov}: {'configurada' if ok else 'sin configurar'}")
    print(f"  Telegram: {'configurado' if ch.get('telegram_token_present') else 'sin configurar'}")
    print(f"  Google: {'conectado' if ch.get('google_credentials_present') else 'sin conectar'}")

    print("\n── Esquema (ORM vs BD real) ──")
    desfase = data["schema"]
    if not desfase or "_error" in desfase:
        print("  sin desfase detectado" if not desfase else f"  no verificable: {desfase['_error']}")
    else:
        for tabla, cols in desfase.items():
            print(f"  ⚠ {tabla}: faltan columnas {cols} — corre `alembic upgrade head`")

    print("\n── Aprobaciones pendientes ──")
    if not data["approvals_pending"]:
        print("  (ninguna)")
    for a in data["approvals_pending"]:
        print(f"  [{a['age_hours']}h] {a['kind']} ({a['action_type']}) — misión {a['mission_id']}")
    print()


def main() -> None:
    hours = 24
    args = sys.argv[1:]
    if "--hours" in args:
        i = args.index("--hours")
        if i + 1 < len(args):
            hours = int(args[i + 1])
    _print(collect(hours))


if __name__ == "__main__":
    main()
