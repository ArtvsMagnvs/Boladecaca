# app/core/notify.py — avisar al usuario por el canal que él prefiera (R5)
#
# EL FLUJO QUE PIDIÓ EL USUARIO (doc 23 R5): el Orquestador planifica, ejecuta y
# «cada vez que completa algo que se puede comprobar, para y avisa». Este módulo
# es la mitad de «avisa»: decidir POR DÓNDE y entregarlo.
#
# DÓNDE VIVE LA PREFERENCIA: en la tabla `Config` (`notify_channel`), mismo
# patrón que los permisos de A3b y el token de Telegram — sin migración nueva.
#
# QUÉ NO HACE: no inventa un canal. Reusa `gateway.notify()` (A1 Δ8), que ya
# sabe entregar a cualquier adapter registrado sin que quien avisa se entere de
# cuál es. Añadir un canal futuro (WhatsApp, email...) no toca este archivo.
#
# FAIL-SOFT SIEMPRE: si el canal falla, la misión NO se rompe ni se queda
# colgada. El aviso siempre está en la UI —la aprobación pendiente es visible en
# Aithera por sí sola—, así que el push es un extra, nunca el único camino.
from __future__ import annotations

from typing import Optional

from app.core.logging_config import get_system_logger

logger = get_system_logger("core.notify")

CONFIG_KEY = "notify_channel"

# "ui" = no se empuja nada; el usuario lo ve en Aithera (comportamiento por
# defecto, y el único seguro si no hay ningún canal configurado).
DEFAULT_CHANNEL = "ui"


def get_preferred_channel() -> str:
    """Canal elegido por el usuario. Ante cualquier problema, "ui": nunca se
    intenta empujar a un sitio del que no estamos seguros."""
    try:
        from app.db.database import Config, SessionLocal

        db = SessionLocal()
        try:
            row = db.query(Config).filter(Config.key == CONFIG_KEY).first()
            return (row.value or DEFAULT_CHANNEL).strip() if row else DEFAULT_CHANNEL
        finally:
            db.close()
    except Exception:
        return DEFAULT_CHANNEL


def set_preferred_channel(channel: str) -> str:
    """Guarda la preferencia. Devuelve el valor efectivamente guardado."""
    value = (channel or DEFAULT_CHANNEL).strip() or DEFAULT_CHANNEL
    from app.db.database import Config, SessionLocal

    db = SessionLocal()
    try:
        row = db.query(Config).filter(Config.key == CONFIG_KEY).first()
        if row is None:
            db.add(Config(key=CONFIG_KEY, value=value))
        else:
            row.value = value
        db.commit()
        return value
    finally:
        db.close()


def _telegram_target() -> Optional[str]:
    """Primer chat_id autorizado. Misma fuente que usa el AE en su acción de
    Telegram — no se duplica el criterio de "a quién se le escribe"."""
    try:
        from app.db.database import Config, SessionLocal

        db = SessionLocal()
        try:
            row = db.query(Config).filter(Config.key == "telegram_chat_id").first()
            ids = [c.strip() for c in ((row.value if row else "") or "").split(",") if c.strip()]
            return ids[0] if ids else None
        finally:
            db.close()
    except Exception:
        return None


async def notify_user(text: str, *, channel: Optional[str] = None) -> bool:
    """Empuja un aviso al usuario. Devuelve True si se ENTREGÓ de verdad.

    `False` no es un error: significa "no había por dónde empujarlo" (canal en
    "ui", sin chat_id, adapter caído...). Quien llama debe seguir su curso — el
    aviso vive igualmente en Aithera."""
    destino = (channel or get_preferred_channel()).strip().lower()
    if destino in ("", "ui", "none", "off"):
        return False

    try:
        from app.gateway.envelope import OutboundMessage
        from app.gateway.gateway import gateway

        target = _telegram_target() if destino == "telegram" else None
        if destino == "telegram" and not target:
            logger.info("[notify] Telegram elegido pero no hay chat_id autorizado; el aviso queda en la UI")
            return False

        return await gateway.notify(destino, target or "", OutboundMessage(text=text))
    except Exception as e:
        # Un canal roto NUNCA puede tumbar lo que estuviera haciendo quien avisa.
        logger.info(f"[notify] no se pudo avisar por {destino!r}: {type(e).__name__}: {e}")
        return False
