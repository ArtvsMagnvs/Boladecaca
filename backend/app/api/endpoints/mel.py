# app/api/endpoints/mel.py — endpoints del MEL (Model Execution Layer)
#
# V1.0 E1b: el informe auto-investigado por modelo conectado (doc 19 §5.4.3).
# Más endpoints (políticas, override, decision trace) llegan en E2/E2b según
# doc 22 §3.
from __future__ import annotations

import app.mel as mel
from fastapi import APIRouter

router = APIRouter(prefix="/mel", tags=["MEL"])


@router.get("/capability-report")
def get_capability_report():
    """El informe de capacidades por modelo conectado, generado por el Catálogo
    Auto-Investigado (doc 19 §5.4) — un resumen legible, no solo uso interno."""
    return mel.capability_report()
