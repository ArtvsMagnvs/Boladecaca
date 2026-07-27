# backend/app/api/endpoints/onboarding.py — Asistente de bienvenida (OB-1, doc 30 §1)
#
# La primera vez que se abre Aithera, el frontend muestra un asistente que
# elige idioma → escanea hardware → recomienda modelo → resuelve voz. Este
# router es el PEGAMENTO de estado: dice si el onboarding ya se completó y lo
# sella al terminar. Todo el trabajo real (escaneo, instalación, voz) lo hacen
# endpoints que YA existen (`/local-models/hardware`, `/local-models/install`,
# `/voice/defaults`) — aquí solo se guarda el veredicto en la tabla `Config`,
# mismo patrón key-value que telegram/search/voz (sin migración nueva).
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.db.models import Config

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

# Claves en `Config` (reutiliza `app_language`, ya leída por /voice/defaults).
_DONE_KEY = "onboarding_completed"
_LANG_KEY = "app_language"
# Modelo que el usuario aceptó en OB-1 pero que descargará OB-2 (instalación
# guiada con progreso). OB-1 nunca descarga: solo deja la intención anotada.
_PENDING_MODEL_KEY = "onboarding_pending_model"


def _get(db: Session, key: str) -> Optional[str]:
    row = db.query(Config).filter(Config.key == key).first()
    return row.value if row else None


def _set(db: Session, key: str, value: str) -> None:
    row = db.query(Config).filter(Config.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Config(key=key, value=value))
    db.commit()


class OnboardingStatus(BaseModel):
    completed: bool
    language: Optional[str] = None
    pending_model: Optional[str] = None


class OnboardingComplete(BaseModel):
    language: str                       # "es" | "en" | "fr" | "pt"
    model_tag: Optional[str] = None     # modelo aceptado → lo descarga OB-2
    # El tier del AVCS lo persiste el frontend (store, localStorage) igual que
    # desde Ajustes; no hace falta duplicarlo aquí.


@router.get("/status", response_model=OnboardingStatus)
def onboarding_status(db: Session = Depends(get_db)) -> OnboardingStatus:
    """¿Ya se completó el onboarding? Lo llama el frontend al arrancar para
    decidir si muestra el asistente. Fuente de verdad en BD (sobrevive a
    reinstalar el frontend / limpiar localStorage)."""
    return OnboardingStatus(
        completed=(_get(db, _DONE_KEY) == "true"),
        language=_get(db, _LANG_KEY),
        pending_model=_get(db, _PENDING_MODEL_KEY),
    )


@router.post("/complete", response_model=OnboardingStatus)
def onboarding_complete(body: OnboardingComplete, db: Session = Depends(get_db)) -> OnboardingStatus:
    """Sella el onboarding: guarda idioma, el modelo pendiente (para OB-2) y
    marca el flag. Idempotente — volver a llamarlo solo actualiza los valores."""
    _set(db, _LANG_KEY, body.language)
    if body.model_tag:
        _set(db, _PENDING_MODEL_KEY, body.model_tag)
    _set(db, _DONE_KEY, "true")
    return OnboardingStatus(
        completed=True,
        language=body.language,
        pending_model=body.model_tag,
    )


@router.post("/reset", response_model=OnboardingStatus)
def onboarding_reset(db: Session = Depends(get_db)) -> OnboardingStatus:
    """Vuelve a mostrar el asistente en el próximo arranque (Ajustes → Sistema:
    "Repetir bienvenida"). No borra idioma ni preferencias ya aplicadas."""
    _set(db, _DONE_KEY, "false")
    return OnboardingStatus(completed=False, language=_get(db, _LANG_KEY))
