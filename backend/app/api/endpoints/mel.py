# app/api/endpoints/mel.py — endpoints del MEL (Model Execution Layer)
#
# V1.0 E1b: el informe auto-investigado por modelo conectado (doc 19 §5.4.3).
# V1.0 E2: políticas (listar + activar). El override explícito (E2b) y el
# decision trace llegan después según doc 22 §3.
from __future__ import annotations

import app.mel as mel
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/mel", tags=["MEL"])


@router.get("/capability-report")
def get_capability_report():
    """El informe de capacidades por modelo conectado, generado por el Catálogo
    Auto-Investigado (doc 19 §5.4) — un resumen legible, no solo uso interno."""
    return mel.capability_report()


@router.get("/policies")
def get_policies():
    """[E2] Las políticas compiladas (Economy/Quality/Offline) con su cadena
    capacidad→modelos y cuál está activa. Compila si aún no existen."""
    mel.ensure_ready()
    return mel.policies()


class SetActivePolicyBody(BaseModel):
    name: str


@router.post("/policies/active")
def set_active_policy(body: SetActivePolicyBody):
    """[E2] Cambia la política activa (Settings → Inteligencia, 1 clic)."""
    if not mel.set_active_policy(body.name):
        raise HTTPException(status_code=404, detail=f"Política desconocida: {body.name}")
    return {"active": body.name}
