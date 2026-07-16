# app/tie/missions.py — Mission Manager (doc 14 §3.6, T1 mínimo)
#
# En V1.0 la misión es IMPLÍCITA: 1 query compleja = 1 misión = 1 grafo = 1
# traza. Aquí solo vive el helper de creación; la tabla `missions` propia +
# `submit_mission` público con multi-grafo + panel del Hub llegan en V1.2.
from __future__ import annotations

from typing import Optional

from app.tie.contracts import Mission


def new_mission(
    goal: str,
    *,
    source: str = "user",
    channel: Optional[str] = None,
    project_id: Optional[int] = None,
) -> Mission:
    """Crea una misión nueva (en V1.0 no se persiste en tabla propia — su rastro
    vive en `orchestrator_traces` vía el tracer). `source` gobierna los
    presupuestos futuros (automation < user, doc 14 §3.5) y de dónde vino, para
    que AE/WPMS deleguen sin acoplarse."""
    return Mission(
        id=Mission.new_id(),
        goal=goal,
        source=source,
        channel=channel,
        project_id=project_id,
    )
