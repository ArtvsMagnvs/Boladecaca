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


@router.get("/models")
def get_models():
    """[E2b] Los (proveedor, modelo) configurados — pueblan los selectores de la
    personalización de políticas. `key` = `provider:model` de las cadenas."""
    return mel.list_models()


# Personalización manual de políticas (petición del usuario, 2026-07-18).
# La política Offline no es editable (es "solo local" por definición).
_EDITABLE = {"economy", "quality", "custom"}


class SetPrimaryBody(BaseModel):
    capability: str
    model_key: str | None = None   # None = "Automático" para esa capacidad


@router.patch("/policies/{name}/primary")
def set_policy_primary(name: str, body: SetPrimaryBody):
    """[E2b] Fija el modelo primario de UNA capacidad en una política editable."""
    if name not in _EDITABLE:
        raise HTTPException(status_code=400, detail=f"Política no editable: {name}")
    if not mel.set_policy_primary(name, body.capability, body.model_key):
        raise HTTPException(status_code=400,
                            detail="No se pudo aplicar (política/capacidad/modelo desconocido).")
    return {"ok": True}


class SetSlotBody(BaseModel):
    capability: str
    position: int          # 0=primario · 1-2=respaldos · 3=último recurso (solo local)
    model_key: str


@router.patch("/policies/{name}/slot")
def set_policy_slot(name: str, body: SetSlotBody):
    """[2026-07-21] Edita una posición concreta de la cadena de una capacidad.
    La posición final solo admite modelos LOCALES (red de seguridad offline)."""
    if name not in _EDITABLE:
        raise HTTPException(status_code=400, detail=f"Política no editable: {name}")
    if not mel.set_policy_slot(name, body.capability, body.position, body.model_key):
        raise HTTPException(
            status_code=400,
            detail="No se pudo aplicar (posición/modelo inválido; recuerda: la 4ª posición solo admite modelos locales).",
        )
    return {"ok": True}


@router.get("/health-summary")
def get_health_summary():
    """[2026-07-21] ¿Trabajando SOLO en local por caída de la nube? — banner naranja."""
    return mel.health_summary()


@router.post("/policies/{name}/restore")
def restore_policy(name: str):
    """[E2b] Devuelve una política a sus valores por defecto (botón Restaurar)."""
    if name not in _EDITABLE:
        raise HTTPException(status_code=400, detail=f"Política no editable: {name}")
    if not mel.restore_policy(name):
        raise HTTPException(status_code=404, detail=f"Política desconocida: {name}")
    return {"ok": True}


# Overrides de modelo por proyecto (pin persistente, doc 19 §7b).
@router.get("/overrides")
def get_overrides():
    """[E2b] Todos los pines de modelo por proyecto activos (lista borrable)."""
    return mel.list_overrides()


@router.delete("/overrides/{override_id}")
def delete_override(override_id: int):
    """[E2b] Borra un pin de proyecto (botón borrar en Ajustes → Inteligencia)."""
    if not mel.clear_override(override_id):
        raise HTTPException(status_code=404, detail="Override no encontrado")
    return {"ok": True}
