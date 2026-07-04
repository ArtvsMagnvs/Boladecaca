# app/api/endpoints/telegram.py
#
# V0.8 (PLAN_MAESTRO_2026): configuracion del canal Telegram. Guarda el token
# y la whitelist de chat_id en la tabla Config (key-value) para no editar la
# BD a mano. El adapter se registra/arranca en el lifespan de main.py leyendo
# estas mismas claves; cambiar la config aqui surte efecto al reiniciar el
# backend (el polling se monta en el arranque, principio: sin sobreingenieria).

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

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
    token: str
    chat_ids: List[str] = []  # chat_id autorizados


class TelegramStatus(BaseModel):
    configured: bool          # hay token guardado
    running: bool             # el adapter esta registrado y activo AHORA
    allowed_chat_ids: List[str]


@router.get("/status", response_model=TelegramStatus)
def telegram_status(db: Session = Depends(get_db)):
    """Estado del canal. `running` refleja el adapter vivo en el Gateway."""
    token = _get(db, _KEY_TOKEN)
    chats_raw = _get(db, _KEY_CHATS) or ""
    chats = [c.strip() for c in chats_raw.split(",") if c.strip()]

    running = False
    try:
        from app.gateway.gateway import gateway
        running = "telegram" in gateway.adapters()
    except Exception:
        running = False

    return TelegramStatus(
        configured=bool(token),
        running=running,
        allowed_chat_ids=chats,
    )


@router.post("/configure", response_model=TelegramStatus)
def telegram_configure(cfg: TelegramConfig, db: Session = Depends(get_db)):
    """Guarda token + whitelist. Aplica al reiniciar el backend."""
    _set(db, _KEY_TOKEN, cfg.token.strip())
    _set(db, _KEY_CHATS, ",".join(c.strip() for c in cfg.chat_ids if c.strip()))
    db.commit()
    return telegram_status(db)


@router.delete("/configure", response_model=TelegramStatus)
def telegram_deconfigure(db: Session = Depends(get_db)):
    """Borra la configuracion del canal (desactiva al reiniciar)."""
    for key in (_KEY_TOKEN, _KEY_CHATS):
        row = db.query(Config).filter(Config.key == key).first()
        if row:
            db.delete(row)
    db.commit()
    return telegram_status(db)
