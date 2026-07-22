# app/telemetry/recorder.py — registro punta a punta de misiones (2026-07-21)
#
# Filosofía (la misma del tracer del TIE): BEST-EFFORT TOTAL. La telemetría
# JAMÁS rompe ni frena el pipeline — un fallo aquí se loguea y se sigue. El
# contexto de misión viaja por `contextvars` (sobrevive a los await del mismo
# task), así los hooks del MEL/toolloop no necesitan que nadie les pase el
# mission_id por parámetro.
#
# ¿Por qué BD y no el bus de eventos? El bus (app/core/events.py) es in-process
# y sin persistencia: si el backend se reinicia o el handler falla, el dato se
# pierde — y esta información es justo la que necesitamos DESPUÉS de que algo
# fallara. La BD es la fuente de verdad; un espejo al bus puede añadirse luego
# para vistas en vivo (doc 31).
from __future__ import annotations

import asyncio
from contextvars import ContextVar
from datetime import datetime, timedelta
from typing import Any, Optional

from app.core.logging_config import get_system_logger

logger = get_system_logger("telemetry")

# (mission_id, trace_id) del task actual. Default: llamada suelta (chat corto).
_mission_ctx: ContextVar[tuple[Optional[str], Optional[str]]] = ContextVar(
    "aithera_mission_ctx", default=(None, None)
)

_table_ready = False


def set_mission(mission_id: Optional[str], trace_id: Optional[str] = None):
    """Fija el contexto de misión del task actual (lo llama el TIE al arrancar
    handle/executor). Devuelve el token por si el caller quiere restaurar."""
    return _mission_ctx.set((mission_id, trace_id))


def current_mission() -> tuple[Optional[str], Optional[str]]:
    return _mission_ctx.get()


def _ensure_table() -> None:
    """Self-heal para el camino dev (SQLite creada por create_all antes de que
    este módulo existiera). En Postgres real la crea la migración 26.ª."""
    global _table_ready
    if _table_ready:
        return
    try:
        from app.db.database import Base, engine
        from app.telemetry.models import MissionEvent

        Base.metadata.create_all(bind=engine, tables=[MissionEvent.__table__])
        _table_ready = True
    except Exception as e:
        logger.error(f"[telemetry] ensure_table falló (no crítico): {type(e).__name__}: {e}")


def _write(payload: dict) -> None:
    try:
        _ensure_table()
        from app.db.database import SessionLocal
        from app.telemetry.models import MissionEvent

        db = SessionLocal()
        try:
            db.add(MissionEvent(**payload))
            db.commit()
        finally:
            db.close()
    except Exception as e:  # best-effort SIEMPRE
        logger.error(f"[telemetry] registro falló (no crítico): {type(e).__name__}: {e}")


def record(stage: str, *, name: Optional[str] = None, provider: Optional[str] = None,
           model: Optional[str] = None, duration_ms: Optional[int] = None,
           ok: Optional[bool] = None, detail: Optional[dict] = None,
           mission_id: Optional[str] = None, trace_id: Optional[str] = None) -> None:
    """Registra UN evento. mission/trace explícitos ganan; si no, el contexto.
    Nunca lanza. Fuera del hot path: con loop corriendo escribe en un hilo."""
    try:
        ctx_mission, ctx_trace = _mission_ctx.get()
        payload = {
            "mission_id": mission_id or ctx_mission,
            "trace_id": trace_id or ctx_trace,
            "ts": datetime.utcnow(),
            "stage": stage,
            "name": name,
            "provider": provider,
            "model": model,
            "duration_ms": duration_ms,
            "ok": ok,
            "detail": detail,
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(asyncio.to_thread(_write, payload))
        except RuntimeError:
            _write(payload)   # sin loop (script/test síncrono): escribe directo
    except Exception as e:
        logger.error(f"[telemetry] record falló (no crítico): {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Consultas (la parte que consumen los reportes y el mission_lab)
# ---------------------------------------------------------------------------
def mission_timeline(mission_id: str) -> dict:
    """Timeline ordenado de UNA misión + resumen calculado (duraciones por
    etapa, LLM por modelo, tools ok/fallo).

    [2026-07-22, fix mismatch doc 31] Acepta indistintamente un mission_id
    (Mission.id) o un trace_id: cada fila guarda los dos, pero quien llama
    (mission_report.py, un cliente externo) solo tiene el id que le llegó por
    SSE, y esa convención no era uniforme entre el camino corto del TIE
    (emitía trace_id) y el Orquestador (emitía mission_id) — ver
    app/tie/pipeline.py y app/orchestrator/__init__.py. Consultar por
    cualquiera de los dos hace el lookup robusto sin depender de que esa
    inconsistencia esté 100% corregida en todos los callers."""
    from sqlalchemy import or_

    from app.db.database import SessionLocal
    from app.telemetry.models import MissionEvent

    db = SessionLocal()
    try:
        rows = (db.query(MissionEvent)
                .filter(or_(MissionEvent.mission_id == mission_id,
                           MissionEvent.trace_id == mission_id))
                .order_by(MissionEvent.id).all())
    finally:
        db.close()

    events = [{
        "ts": r.ts.isoformat() if r.ts else None, "stage": r.stage, "name": r.name,
        "provider": r.provider, "model": r.model, "duration_ms": r.duration_ms,
        "ok": r.ok, "detail": r.detail,
    } for r in rows]

    llm: dict[str, dict[str, Any]] = {}
    tools: dict[str, dict[str, Any]] = {}
    total_ms = 0
    for r in rows:
        if r.stage == "llm_call":
            key = f"{r.provider}:{r.model}" if r.provider else "?"
            agg = llm.setdefault(key, {"calls": 0, "ms": 0, "fails": 0})
            agg["calls"] += 1
            agg["ms"] += r.duration_ms or 0
            if r.ok is False:
                agg["fails"] += 1
        elif r.stage == "tool_call":
            agg = tools.setdefault(r.name or "?", {"calls": 0, "ms": 0, "fails": 0})
            agg["calls"] += 1
            agg["ms"] += r.duration_ms or 0
            if r.ok is False:
                agg["fails"] += 1
        elif r.stage == "mission_end":
            total_ms = r.duration_ms or total_ms
    if not total_ms and len(rows) >= 2 and rows[0].ts and rows[-1].ts:
        total_ms = int((rows[-1].ts - rows[0].ts).total_seconds() * 1000)

    return {
        "mission_id": mission_id,
        "events": events,
        "summary": {"total_ms": total_ms, "llm_by_model": llm, "tools": tools,
                    "event_count": len(events)},
    }


def aggregate_report(hours: int = 24) -> dict:
    """Reporte agregado del período: qué modelo ejecuta cada capacidad y a qué
    velocidad, qué tools fallan, misiones ok/failed, y los últimos errores.
    La base del ciclo de mejora (doc 31)."""
    from app.db.database import SessionLocal
    from app.telemetry.models import MissionEvent

    since = datetime.utcnow() - timedelta(hours=hours)
    db = SessionLocal()
    try:
        rows = (db.query(MissionEvent)
                .filter(MissionEvent.ts >= since)
                .order_by(MissionEvent.id).all())
    finally:
        db.close()

    llm: dict[str, dict[str, Any]] = {}      # "capability|provider:model" -> stats
    tools: dict[str, dict[str, Any]] = {}
    missions = {"total": 0, "ok": 0, "failed": 0, "ms": 0}
    errors: list[dict] = []
    for r in rows:
        if r.stage == "llm_call":
            key = f"{r.name or '?'} | {r.provider}:{r.model}"
            agg = llm.setdefault(key, {"calls": 0, "ms": 0, "max_ms": 0, "fails": 0})
            agg["calls"] += 1
            agg["ms"] += r.duration_ms or 0
            agg["max_ms"] = max(agg["max_ms"], r.duration_ms or 0)
            if r.ok is False:
                agg["fails"] += 1
        elif r.stage == "tool_call":
            agg = tools.setdefault(r.name or "?", {"calls": 0, "ms": 0, "fails": 0})
            agg["calls"] += 1
            agg["ms"] += r.duration_ms or 0
            if r.ok is False:
                agg["fails"] += 1
        elif r.stage == "mission_end":
            missions["total"] += 1
            missions["ms"] += r.duration_ms or 0
            if r.ok:
                missions["ok"] += 1
            else:
                missions["failed"] += 1
        if (r.ok is False or r.stage == "error") and len(errors) < 25:
            errors.append({"ts": r.ts.isoformat() if r.ts else None, "stage": r.stage,
                           "name": r.name, "mission_id": r.mission_id,
                           "detail": r.detail})

    for agg in list(llm.values()) + list(tools.values()):
        agg["avg_ms"] = int(agg["ms"] / agg["calls"]) if agg["calls"] else 0
    if missions["total"]:
        missions["avg_ms"] = int(missions["ms"] / missions["total"])

    return {"hours": hours, "llm": llm, "tools": tools, "missions": missions,
            "recent_errors": errors}


def purge_old(retention_days: int = 30) -> int:
    """Borra eventos más viejos que la retención. Mismo espíritu que
    tracer.purge_old — nunca toca datos recientes."""
    if retention_days <= 0:
        return 0
    from app.db.database import SessionLocal
    from app.telemetry.models import MissionEvent

    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    db = SessionLocal()
    try:
        n = db.query(MissionEvent).filter(MissionEvent.ts < cutoff).delete()
        db.commit()
        return n
    except Exception as e:
        db.rollback()
        logger.error(f"[telemetry] purge falló: {type(e).__name__}: {e}")
        return 0
    finally:
        db.close()
