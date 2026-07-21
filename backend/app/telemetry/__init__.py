# backend/app/telemetry/__init__.py — API PÚBLICA de la telemetría de misiones
#
# [doc 16] Disciplina modular: el resto de la app importa SOLO desde
# `app.telemetry`. Observabilidad punta a punta del entorno de Misiones
# (Orchestrator/TIE/MEL/tools) — diseño y ciclo de mejora en doc 31.
from __future__ import annotations

from app.telemetry.recorder import (
    aggregate_report,
    current_mission,
    mission_timeline,
    purge_old,
    record,
    set_mission,
)

__all__ = [
    "record", "set_mission", "current_mission",
    "mission_timeline", "aggregate_report", "purge_old",
]
