# app/api/endpoints/telegram.py
#
# V0.8 (PLAN_MAESTRO_2026): configuracion del canal Telegram desde Ajustes.
# Guarda el token (CIFRADO con DPAPI, ver app/core/secrets.py) y la whitelist
# de chat_id en la tabla Config. El adapter se registra/arranca en el lifespan
# de main.py leyendo estas claves y descifrando el token; cambiar la config
# aqui surte efecto al reiniciar el backend (el polling se monta al arrancar).
#
# El token NUNCA se devuelve por la API: el status solo dice si hay uno guardado
# y muestra una mascara. Para cambiarlo se envia uno nuevo; para conservarlo se
# omite (token vacio => se mantiene el que ya habia).

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core import secrets
from app.db.database import get_db
from app.db.models import Config

router = APIRouter(prefix="/telegram", tags=["Telegram"])

_KEY_TOKEN = "telegram_bot_token"
_KEY_CHATS = "telegram_chat_id"  # CSV de chat_id autorizados


def _get(db: Session, key: str) -> Optional[str]:
    row = db.query(Config).filter(Config.key == key).first()
    return row.value if row else None


def _set(db: Session, key: str, value: str) -> None:
    row = db.query(Config).filter(Config.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Config(key=key, value=value))


class TelegramConfig(BaseModel):
    # token opcional: si viene vacio/omitido se conserva el guardado (solo se
    # actualiza la whitelist). Asi la UI no necesita reescribir el secreto.
    token: Optional[str] = None
    chat_ids: List[str] = []


class TelegramStatus(BaseModel):
    configured: bool            # hay token guardado
    running: bool               # el adapter esta registrado y activo AHORA
    allowed_chat_ids: List[str]
    token_masked: str = ""      # '••••abcd' si hay token; nunca el token entero


def _status(db: Session) -> "TelegramStatus":
    stored = _get(db, _KEY_TOKEN)
    chats_raw = _get(db, _KEY_CHATS) or ""
    chats = [c.strip() for c in chats_raw.split(",") if c.strip()]

    masked = ""
    if stored:
        try:
            masked = secrets.mask(secrets.decrypt(stored))
        except Exception:
            masked = "••••"  # hay token pero no se pudo descifrar en este equipo

    running = False
    try:
        from app.gateway.gateway import gateway
        running = "telegram" in gateway.adapters()
    except Exception:
        running = False

    return TelegramStatus(
        configured=bool(stored),
        running=running,
        allowed_chat_ids=chats,
        token_masked=masked,
    )


@router.get("/status", response_model=TelegramStatus)
def telegram_status(db: Session = Depends(get_db)):
    """Estado del canal. `running` refleja el adapter vivo en el Gateway."""
    return _status(db)


@router.post("/configure", response_model=TelegramStatus)
def telegram_configure(cfg: TelegramConfig, db: Session = Depends(get_db)):
    """Guarda whitelist y, si se envia, el token (cifrado). Aplica al reiniciar."""
    token = (cfg.token or "").strip()
    if token:
        _set(db, _KEY_TOKEN, secrets.encrypt(token))  # cifrado en reposo
    _set(db, _KEY_CHATS, ",".join(c.strip() for c in cfg.chat_ids if c.strip()))
    db.commit()
    return _status(db)


@router.delete("/configure", response_model=TelegramStatus)
def telegram_deconfigure(db: Session = Depends(get_db)):
    """Borra la configuracion del canal (desactiva al reiniciar)."""
    for key in (_KEY_TOKEN, _KEY_CHATS):
        row = db.query(Config).filter(Config.key == key).first()
        if row:
            db.delete(row)
    db.commit()
    return _status(db)
