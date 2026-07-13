# app/workspace/models.py — Modelos del WPMS (V0.87, doc 18 §3.4)
#
# Milestone es la pieza que hace esto "Aithera" y no "Trello": el EJE DE VERSION.
# Aithera avanza por versiones (V0.85 -> V0.87 -> V0.9); el milestone lo modela
# literalmente. El TIE planifica "hacia el milestone activo", el briefing reporta
# "estas al 60% de V0.9", el Learner mide "V0.85 tardo 6 sesiones vs 4 estimadas".
#
# La extension de Project/Task vive en app/db/database.py (esas clases ya existian
# alli — evolucion, no reescritura, doc 18 §3.1). Aqui solo nace la entidad nueva.
# Base viene de app.db.database (todos los modelos comparten metadata).
#
# progress NO es columna: se calcula (doc 18 §3.4, §8) en workspace/progress.py.
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.database import Base


class Milestone(Base):
    """Un objetivo de version dentro de un proyecto. status: planned|active|done|
    archived. Una tarea puede vivir sin milestone (backlog suelto) — la jerarquia
    guia, no obliga (leccion de Linear, doc 18 §4)."""

    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True)
    # Integer plano + indice (no ForeignKey) por simetria con Task.milestone_id:
    # referencia cross-modulo, integridad a nivel app. Ver database.py.
    project_id = Column(Integer, index=True)  # -> projects.id
    name = Column(String(120))                 # "V0.85 — MOS Skeleton"
    version = Column(String(40))               # "0.8.5" — Aithera trabaja por versiones
    description = Column(Text)                  # el objetivo de la version
    status = Column(String(20), default="planned", index=True)  # planned|active|done|archived
    target_date = Column(DateTime)
    order_index = Column(Integer, default=0)   # orden en el roadmap del proyecto ('order' reservado)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)            # se rellena al pasar a 'done'
    updated_at = Column(DateTime, default=datetime.utcnow)
