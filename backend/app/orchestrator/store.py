# app/orchestrator/store.py — persistencia del run (R2)
#
# Checkpoint por transición: el run se reescribe en la BD cada vez que un
# objetivo cambia de estado. Mismo criterio que el executor del TIE con su grafo
# (T3): todo el estado vive en disco, así que un reinicio del backend a mitad de
# una orquestación no pierde lo ya hecho.
#
# Best-effort a propósito: un fallo de escritura NUNCA debe tumbar una
# orquestación que por lo demás va bien. Se registra y se sigue.
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.core.logging_config import get_system_logger
from app.orchestrator.contracts import OrchestrationRun

logger = get_system_logger("orchestrator.store")


def save(run: OrchestrationRun, *, duration_ms: Optional[int] = None) -> None:
    """Crea o actualiza la fila del run (upsert). Se llama en cada transición."""
    from app.db.database import SessionLocal
    from app.orchestrator.models import OrchestrationRunRow

    db = SessionLocal()
    try:
        row = db.get(OrchestrationRunRow, run.id)
        if row is None:
            row = OrchestrationRunRow(id=run.id, created_at=datetime.utcnow())
            db.add(row)
        row.user_message = run.user_message
        row.objectives = [o.to_dict() for o in run.objectives]
        # La cancelación la pide el USUARIO y viaja por la BD (es la forma de
        # que llegue a un conductor que está a mitad de una ola). Un checkpoint
        # posterior NO puede devolverla a "running": el conductor todavía tiene
        # `run.state = "running"` en memoria y borraría la petición.
        if not (row.state == "cancelled" and run.state == "running"):
            row.state = run.state
        row.outcome = run.outcome
        row.channel = run.channel
        row.source = run.source
        row.updated_at = datetime.utcnow()
        if duration_ms is not None:
            row.duration_ms = duration_ms
        db.commit()
    except Exception as e:
        logger.error(f"[store] no se pudo guardar el run {run.id}: {type(e).__name__}: {e}")
        db.rollback()
    finally:
        db.close()


def load(run_id: str) -> Optional[OrchestrationRun]:
    from app.db.database import SessionLocal
    from app.orchestrator.models import OrchestrationRunRow

    db = SessionLocal()
    try:
        row = db.get(OrchestrationRunRow, run_id)
        if row is None:
            return None
        return OrchestrationRun.from_dict({
            "id": row.id, "user_message": row.user_message or "",
            "objectives": row.objectives or [], "state": row.state or "running",
            "outcome": row.outcome, "channel": row.channel, "source": row.source or "user",
        })
    except Exception as e:
        logger.error(f"[store] no se pudo cargar el run {run_id}: {type(e).__name__}: {e}")
        return None
    finally:
        db.close()


def recent(limit: int = 30) -> list[dict]:
    """Runs recientes para la UI. Los que siguen vivos, primero."""
    from app.db.database import SessionLocal
    from app.orchestrator.models import OrchestrationRunRow

    db = SessionLocal()
    try:
        rows = (db.query(OrchestrationRunRow)
                  .order_by(OrchestrationRunRow.created_at.desc())
                  .limit(max(1, min(limit, 200))).all())
        items = [{
            "id": r.id, "user_message": r.user_message, "state": r.state,
            "outcome": r.outcome, "channel": r.channel,
            "n_objectives": len(r.objectives or []),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "duration_ms": r.duration_ms,
        } for r in rows]
        vivos = [i for i in items if i["state"] == "running"]
        return vivos + [i for i in items if i["state"] != "running"]
    except Exception as e:
        logger.error(f"[store] no se pudieron listar los runs: {type(e).__name__}: {e}")
        return []
    finally:
        db.close()


def mark_cancelled(run_id: str) -> bool:
    """Marca el run como cancelado. El conductor lo consulta entre olas y deja de
    lanzar objetivos nuevos; las misiones ya en vuelo las corta el kill-switch
    del TIE."""
    from app.db.database import SessionLocal
    from app.orchestrator.models import OrchestrationRunRow

    db = SessionLocal()
    try:
        row = db.get(OrchestrationRunRow, run_id)
        if row is None or row.state != "running":
            return False
        row.state = "cancelled"
        row.updated_at = datetime.utcnow()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def is_cancelled(run_id: str) -> bool:
    from app.db.database import SessionLocal
    from app.orchestrator.models import OrchestrationRunRow

    db = SessionLocal()
    try:
        row = db.get(OrchestrationRunRow, run_id)
        return bool(row and row.state == "cancelled")
    except Exception:
        return False
    finally:
        db.close()
