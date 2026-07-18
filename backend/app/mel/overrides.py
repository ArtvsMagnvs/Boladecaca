# app/mel/overrides.py — Override explícito del usuario a nivel PROYECTO (E2b)
#
# doc 19 §7b: si el usuario dice "a partir de ahora todo este proyecto con
# Claude", ese pin manda sobre la política del MEL para las misiones de ese
# proyecto — hasta que lo borre. El override de UNA tarea suelta NO vive aquí
# (ese es `model_override` de la petición, efímero); aquí solo los pines
# PERSISTENTES por proyecto.
#
# Precedencia (la aplica decision/executor, no este módulo):
#   model_override (tarea) > pin de proyecto (esto) > política.
#
# Referencia cruzada `project_id` como Integer plano indexado, SIN ForeignKey —
# mismo patrón que `Milestone.project_id`/`Agent.project_id` (doc 18): el MEL no
# importa el modelo Project, la integridad la lleva quien escribe el pin.
from __future__ import annotations

from typing import Optional

from app.core.logging_config import get_system_logger

logger = get_system_logger("mel.overrides")


def set_project_override(project_id: int, model_id: str,
                         capability: Optional[str] = None) -> bool:
    """Fija (o reemplaza) el modelo para un proyecto. `capability=None` = para
    TODAS las capacidades de ese proyecto (el caso normal: "todo el proyecto con
    X"). Idempotente por (project_id, capability): re-pinear reemplaza. Devuelve
    False si falla la escritura (best-effort, nunca lanza al caller)."""
    from app.db.database import SessionLocal
    from app.mel.models import MelOverride

    db = SessionLocal()
    try:
        row = (db.query(MelOverride)
                 .filter(MelOverride.project_id == project_id,
                         MelOverride.capability == capability)
                 .first())
        if row is None:
            row = MelOverride(project_id=project_id, capability=capability,
                              scope="project", source="user_explicit")
            db.add(row)
        row.model_id = model_id
        db.commit()
        return True
    except Exception as e:
        logger.error(f"[overrides] set_project_override falló: {type(e).__name__}: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def override_model_for(project_id: Optional[int], capability: str) -> Optional[str]:
    """El `model_id` pineado para (proyecto, capacidad), o None. Busca primero un
    pin específico de esa capacidad; si no hay, el pin global del proyecto
    (capability=None). None si no hay proyecto o no hay pin."""
    if not project_id:
        return None
    from app.db.database import SessionLocal
    from app.mel.models import MelOverride

    db = SessionLocal()
    try:
        specific = (db.query(MelOverride)
                      .filter(MelOverride.project_id == project_id,
                              MelOverride.capability == capability)
                      .first())
        if specific:
            return specific.model_id
        glob = (db.query(MelOverride)
                  .filter(MelOverride.project_id == project_id,
                          MelOverride.capability.is_(None))
                  .first())
        return glob.model_id if glob else None
    except Exception as e:
        logger.error(f"[overrides] override_model_for falló: {type(e).__name__}: {e}")
        return None
    finally:
        db.close()


def overrides_for(project_id: int) -> list[dict]:
    """Todos los pines de un proyecto (para la UI: lista borrable)."""
    from app.db.database import SessionLocal
    from app.mel.models import MelOverride

    db = SessionLocal()
    try:
        rows = (db.query(MelOverride)
                  .filter(MelOverride.project_id == project_id)
                  .order_by(MelOverride.id.desc()).all())
        return [_to_dict(r) for r in rows]
    except Exception:
        return []
    finally:
        db.close()


def list_all() -> list[dict]:
    """Todos los pines activos, para el panel global de Inteligencia (borrables)."""
    from app.db.database import SessionLocal
    from app.mel.models import MelOverride

    db = SessionLocal()
    try:
        rows = db.query(MelOverride).order_by(MelOverride.id.desc()).all()
        return [_to_dict(r) for r in rows]
    except Exception:
        return []
    finally:
        db.close()


def clear_override(override_id: int) -> bool:
    """Borra un pin por id (botón borrar). True si existía y se borró."""
    from app.db.database import SessionLocal
    from app.mel.models import MelOverride

    db = SessionLocal()
    try:
        row = db.query(MelOverride).filter(MelOverride.id == override_id).first()
        if row is None:
            return False
        db.delete(row)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"[overrides] clear_override falló: {type(e).__name__}: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def _to_dict(row) -> dict:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "capability": row.capability,
        "model_id": row.model_id,
        "scope": row.scope,
        "source": row.source,
    }
