# app/api/endpoints/telemetry.py — observabilidad de Misiones (2026-07-21, doc 31)
#
# Dos vistas: el timeline completo de UNA misión (qué modelo/tool hizo cada
# paso y cuánto tardó) y el reporte agregado del período (qué modelo ejecuta
# cada capacidad y a qué velocidad, qué tools fallan, misiones ok/failed).
# Los consumen la UI futura, el mission_lab y cualquier sesión de mejora.
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

import app.telemetry as telemetry

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("/missions/{mission_id}")
def get_mission_timeline(mission_id: str):
    data = telemetry.mission_timeline(mission_id)
    if not data["events"]:
        raise HTTPException(status_code=404, detail=f"sin telemetría para {mission_id}")
    return data


@router.get("/report")
def get_report(hours: int = Query(default=24, ge=1, le=24 * 30)):
    return telemetry.aggregate_report(hours)
