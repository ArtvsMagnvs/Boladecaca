# app/api/endpoints/search_config.py
#
# V1.0/1.1 (Tools): configuracion de Search Tool desde Ajustes. Mismo patron
# que telegram.py -- las API keys se guardan CIFRADAS (DPAPI) en la tabla
# Config, nunca se devuelven en claro (solo un preview enmascarado).
#
# [2026-07-23, peticion del usuario] Modo de NAVEGADOR (no es una API key, va
# en el mismo router/seccion "Busqueda web" porque en la mente del usuario es
# "como Aithera se mueve por la web"): perfil DEDICADO de Aithera (persistente,
# recomendado) vs el Chrome HABITUAL del usuario (su sesion real, con
# advertencia de riesgo). Valor en claro en Config (no es secreto).

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core import secrets
from app.db.database import get_db
from app.db.models import Config

router = APIRouter(prefix="/search", tags=["Search"])

_KEY_BRAVE = "search_brave_api_key"
_KEY_SERPAPI = "search_serpapi_api_key"
_KEY_BROWSER_MODE = "browser_mode"   # "aithera" | "user"
_BROWSER_MODES = ("aithera", "user")


def _get(db: Session, key: str) -> Optional[str]:
    row = db.query(Config).filter(Config.key == key).first()
    return row.value if row else None


def _set(db: Session, key: str, value: str) -> None:
    row = db.query(Config).filter(Config.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Config(key=key, value=value))


def _delete(db: Session, key: str) -> None:
    row = db.query(Config).filter(Config.key == key).first()
    if row:
        db.delete(row)


class SearchProviderStatus(BaseModel):
    configured: bool
    key_masked: str = ""


class SearchStatus(BaseModel):
    brave: SearchProviderStatus
    serpapi: SearchProviderStatus


class ConfigureBody(BaseModel):
    provider: str  # "brave" | "serpapi"
    api_key: str


def _provider_status(db: Session, key: str) -> SearchProviderStatus:
    stored = _get(db, key)
    if not stored:
        return SearchProviderStatus(configured=False)
    try:
        masked = secrets.mask(secrets.decrypt(stored))
    except Exception:
        masked = "••••"
    return SearchProviderStatus(configured=True, key_masked=masked)


@router.get("/status", response_model=SearchStatus)
def search_status(db: Session = Depends(get_db)):
    return SearchStatus(
        brave=_provider_status(db, _KEY_BRAVE),
        serpapi=_provider_status(db, _KEY_SERPAPI),
    )


@router.post("/configure", response_model=SearchStatus)
def search_configure(body: ConfigureBody, db: Session = Depends(get_db)):
    key_map = {"brave": _KEY_BRAVE, "serpapi": _KEY_SERPAPI}
    config_key = key_map.get(body.provider)
    if not config_key:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"proveedor desconocido: {body.provider}")

    api_key = body.api_key.strip()
    if api_key:
        _set(db, config_key, secrets.encrypt(api_key))
        db.commit()
    return search_status(db)


@router.delete("/configure/{provider}", response_model=SearchStatus)
def search_deconfigure(provider: str, db: Session = Depends(get_db)):
    key_map = {"brave": _KEY_BRAVE, "serpapi": _KEY_SERPAPI}
    config_key = key_map.get(provider)
    if config_key:
        _delete(db, config_key)
        db.commit()
    return search_status(db)


# ---------------------------------------------------------------------------
# [2026-07-23] Modo de navegador — dedicado (Aithera) vs habitual (usuario)
# ---------------------------------------------------------------------------
class BrowserModeStatus(BaseModel):
    mode: str   # "aithera" | "user"


class BrowserModeBody(BaseModel):
    mode: str


@router.get("/browser-mode", response_model=BrowserModeStatus)
def get_browser_mode(db: Session = Depends(get_db)):
    stored = _get(db, _KEY_BROWSER_MODE)
    return BrowserModeStatus(mode=stored if stored in _BROWSER_MODES else "aithera")


@router.post("/browser-mode", response_model=BrowserModeStatus)
def set_browser_mode(body: BrowserModeBody, db: Session = Depends(get_db)):
    if body.mode not in _BROWSER_MODES:
        raise HTTPException(status_code=400, detail=f"modo desconocido: {body.mode}")
    _set(db, _KEY_BROWSER_MODE, body.mode)
    db.commit()
    # El cambio aplica a la PRÓXIMA sesión de navegador (una ya abierta sigue
    # con su perfil actual — cambiar de perfil a media misión sería más
    # confuso que útil). `browser_tool` lo lee al abrir cada sesión nueva.
    return BrowserModeStatus(mode=body.mode)
