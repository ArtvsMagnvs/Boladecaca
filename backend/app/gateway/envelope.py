# app/gateway/envelope.py
#
# V0.8 (PLAN_MAESTRO_2026, patron OpenClaw): el MessageEnvelope es EL contrato
# entre los canales (Electron, Web, Telegram, ...) y la logica de negocio.
#
# Regla de oro (principio 3 del AOS): la logica de negocio NUNCA sabe de que
# canal vino un mensaje. Los adapters convierten su formato nativo a este
# envelope y de vuelta; todo lo demas es channel-agnostic. Anadir un canal
# nuevo = escribir un adapter, cero cambios en el resto del backend.

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Attachment(BaseModel):
    """Adjunto normalizado. Los adapters rellenan lo que su canal soporte."""
    kind: str = "file"              # file | image | audio | video
    name: str = ""
    # Exactamente UNA de estas dos formas de contenido:
    url: Optional[str] = None       # recurso remoto (p.ej. file_id resuelto de Telegram)
    content_b64: Optional[str] = None  # contenido inline pequeño
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageEnvelope(BaseModel):
    """Mensaje ENTRANTE normalizado, venga del canal que venga."""
    envelope_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    channel: str                     # "electron" | "web" | "telegram" | ...
    user_ref: str                    # identidad en ESE canal (chat_id, session...)
    text: str = ""
    attachments: List[Attachment] = Field(default_factory=list)
    reply_to: Optional[str] = None   # id nativo del mensaje al que responde
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OutboundMessage(BaseModel):
    """Respuesta SALIENTE normalizada. El adapter la convierte a su canal."""
    text: str = ""
    envelope_id: str = ""            # correlacion con el envelope de entrada
    attachments: List[Attachment] = Field(default_factory=list)
    error: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
