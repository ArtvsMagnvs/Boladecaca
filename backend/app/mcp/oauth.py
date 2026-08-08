# app/mcp/oauth.py — «Autorizar» en la web del propio servicio (V1.2 C1c)
#
# LO QUE RESUELVE (petición del usuario, 2026-08-08): conectar un servidor MCP
# remoto SIN buscar tokens. El usuario pulsa Conectar, se le abre la página del
# propio servicio (GitHub, Notion, Linear…), pulsa «Authorize», y vuelve. Es el
# mismo modelo del OAuth de Google que Aithera ya usa: **las credenciales las
# teclea el usuario en la web del proveedor, Aithera NUNCA las ve.**
#
# NO SE REIMPLEMENTA EL PROTOCOLO. El SDK oficial ya trae el baile completo
# (`OAuthClientProvider`): descubrimiento del recurso protegido (RFC 9728) →
# metadatos del servidor de autorización (RFC 8414) → **registro dinámico de
# cliente** (RFC 7591, por eso no hace falta dar de alta una app en cada
# servicio) → PKCE → intercambio del código → refresco. Aquí solo se aportan
# las TRES piezas que el SDK deja abiertas a propósito, porque dependen de
# dónde corre el cliente:
#   1. DÓNDE SE GUARDAN los tokens  → `_TokenStore`, cifrado con DPAPI en la
#      tabla Config (mismo helper que el resto de secretos de Aithera).
#   2. CÓMO SE ABRE el navegador    → el SDK asume una CLI que abre una
#      ventana; aquí el backend no puede abrir nada en la máquina del usuario
#      de forma fiable, así que se CAPTURA la URL y la abre el frontend.
#   3. CÓMO VUELVE el código        → el SDK asume un servidor local efímero;
#      aquí ya hay uno (el propio backend), así que el `redirect_uri` es un
#      endpoint de la API y el código llega por ahí.
#
# EL PUENTE ENTRE 2 Y 3 es un futuro por flujo: `redirect_handler` guarda la
# URL y devuelve; `callback_handler` espera a que el endpoint del callback
# resuelva el futuro. Con plazo: un flujo que el usuario abandona no puede
# dejar una tarea esperando para siempre.
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import parse_qs, urlparse

from app.core import secrets as secrets_helper
from app.core.config import settings
from app.core.logging_config import get_system_logger

logger = get_system_logger("mcp.oauth")

_KEY_OAUTH = "mcp.oauth."          # + nombre del servidor (cifrado entero)

# Plazo para que el usuario complete la autorización en su navegador. Generoso
# a propósito (puede tener que iniciar sesión, elegir organización, leer los
# permisos), pero finito: si abandona, la tarea de conexión no se queda
# colgada indefinidamente.
AUTHORIZE_TIMEOUT_S = 300.0


# ---------------------------------------------------------------------------
# 1. Dónde se guardan los tokens — cifrados, como cualquier otro secreto
# ---------------------------------------------------------------------------
def _config_get(key: str) -> Optional[str]:
    from app.db.database import SessionLocal
    from app.db.models import Config

    db = SessionLocal()
    try:
        row = db.query(Config).filter(Config.key == key).first()
        return row.value if row else None
    finally:
        db.close()


def _config_set(key: str, value: str) -> None:
    from app.db.database import SessionLocal
    from app.db.models import Config

    db = SessionLocal()
    try:
        row = db.query(Config).filter(Config.key == key).first()
        if row:
            row.value = value
        else:
            db.add(Config(key=key, value=value))
        db.commit()
    finally:
        db.close()


def _load(name: str) -> dict:
    raw = _config_get(_KEY_OAUTH + name)
    if not raw:
        return {}
    try:
        return json.loads(secrets_helper.decrypt(raw)) or {}
    except Exception:
        return {}


def _save(name: str, data: dict) -> None:
    _config_set(_KEY_OAUTH + name,
                secrets_helper.encrypt(json.dumps(data, ensure_ascii=False)))


def forget(name: str) -> None:
    """Olvida la autorización de un servidor (al borrarlo o al reconectarlo
    desde cero). El token deja de existir para Aithera; revocarlo del lado del
    servicio es cosa del usuario en la web del propio servicio."""
    from app.db.database import SessionLocal
    from app.db.models import Config

    db = SessionLocal()
    try:
        row = db.query(Config).filter(Config.key == _KEY_OAUTH + name).first()
        if row:
            db.delete(row)
            db.commit()
    finally:
        db.close()


def is_authorized(name: str) -> bool:
    return bool(_load(name).get("tokens"))


class _TokenStore:
    """`TokenStorage` del SDK sobre la Config cifrada. Guarda además el
    `client_info` del registro dinámico: sin él, cada reconexión daría de alta
    un cliente nuevo en el servicio del usuario."""

    def __init__(self, name: str):
        self.name = name

    async def get_tokens(self):
        from mcp.shared.auth import OAuthToken

        data = _load(self.name).get("tokens")
        return OAuthToken.model_validate(data) if data else None

    async def set_tokens(self, tokens) -> None:
        data = _load(self.name)
        data["tokens"] = tokens.model_dump(mode="json")
        data["updated_at"] = int(time.time())
        _save(self.name, data)

    async def get_client_info(self):
        from mcp.shared.auth import OAuthClientInformationFull

        data = _load(self.name).get("client")
        return OAuthClientInformationFull.model_validate(data) if data else None

    async def set_client_info(self, client_info) -> None:
        data = _load(self.name)
        data["client"] = client_info.model_dump(mode="json")
        _save(self.name, data)


# ---------------------------------------------------------------------------
# 2 y 3. El puente navegador ↔ callback
# ---------------------------------------------------------------------------
@dataclass
class PendingFlow:
    """Un flujo de autorización en curso.

    El resultado viaja por un `asyncio.Event` + dos huecos, NO por un
    `Future`: un Future se ata a un event loop en cuanto se construye, y este
    objeto se crea antes de saber en qué loop se esperará (el arranque del
    flujo y la espera del callback son dos peticiones HTTP distintas)."""
    name: str
    authorize_url: Optional[str] = None
    state: Optional[str] = None
    code: Optional[str] = None
    error: Optional[str] = None
    done: asyncio.Event = field(default_factory=asyncio.Event)
    started_at: float = field(default_factory=time.monotonic)


_PENDING: dict[str, PendingFlow] = {}      # por nombre de servidor
_BY_STATE: dict[str, PendingFlow] = {}     # por `state` del OAuth


def _cleanup(flow: PendingFlow) -> None:
    _PENDING.pop(flow.name, None)
    if flow.state:
        _BY_STATE.pop(flow.state, None)


def pending_url(name: str) -> Optional[str]:
    """La URL de autorización de un flujo en curso, si ya se conoce. El
    endpoint de arranque la espera unos instantes y se la da al frontend."""
    flow = _PENDING.get(name)
    return flow.authorize_url if flow else None


def resolve_callback(code: str, state: str) -> bool:
    """Lo llama el endpoint del callback. True si había un flujo esperando.

    Un `state` que no espera a nadie se RECHAZA: sin esto, un callback ajeno
    podría inyectar un código en un flujo que no le corresponde."""
    flow = _BY_STATE.get(state)
    if flow is None or flow.done.is_set():
        return False
    flow.code = code
    flow.done.set()
    return True


def cancel(name: str, reason: str = "cancelado") -> None:
    flow = _PENDING.get(name)
    if flow is None:
        return
    if not flow.done.is_set():
        flow.error = reason
        flow.done.set()
    _cleanup(flow)


def redirect_uri() -> str:
    return settings.MCP_OAUTH_REDIRECT_URI


def build_provider(name: str, server_url: str):
    """El `OAuthClientProvider` del SDK, cableado a esta app. Devuelve None si
    la librería no está (el backend arranca igual, patrón telegram)."""
    try:
        from mcp.client.auth import OAuthClientProvider
        from mcp.shared.auth import AuthorizationCodeResult, OAuthClientMetadata
    except Exception as e:      # noqa: BLE001
        logger.info(f"[mcp-oauth] SDK sin soporte OAuth ({e!r})")
        return None

    flow = PendingFlow(name=name)
    _PENDING[name] = flow

    async def _redirect_handler(url: str) -> None:
        # El SDK esperaría abrir un navegador aquí. En su lugar se GUARDA la
        # URL: quien tiene un navegador delante es el frontend, no el backend.
        flow.authorize_url = url
        try:
            estado = (parse_qs(urlparse(url).query).get("state") or [None])[0]
        except Exception:
            estado = None
        if estado:
            flow.state = estado
            _BY_STATE[estado] = flow
        logger.info(f"[mcp-oauth] '{name}': esperando autorización del usuario")

    async def _callback_handler() -> "AuthorizationCodeResult":
        try:
            await asyncio.wait_for(flow.done.wait(), timeout=AUTHORIZE_TIMEOUT_S)
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"nadie completó la autorización de '{name}' en "
                f"{AUTHORIZE_TIMEOUT_S:.0f}s")
        finally:
            _cleanup(flow)
        if flow.error or not flow.code:
            raise RuntimeError(flow.error or "no llegó ningún código de autorización")
        return AuthorizationCodeResult(code=flow.code, state=flow.state)

    metadata = OAuthClientMetadata(
        client_name="Aithera",
        redirect_uris=[redirect_uri()],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="none",   # cliente público + PKCE
    )
    return OAuthClientProvider(
        server_url=server_url,
        client_metadata=metadata,
        storage=_TokenStore(name),
        redirect_handler=_redirect_handler,
        callback_handler=_callback_handler,
    )
