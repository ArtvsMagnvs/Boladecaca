# app/mcp/store.py — configuración de servidores MCP (V1.2 C1, doc 27 §C1)
#
# QUÉ GUARDA Y DÓNDE: la lista de servidores MCP que el usuario ha conectado
# vive en la tabla `Config` existente (mismo patrón que telegram.py /
# briefing_config.py — es config de usuario, pocos registros, sin migración
# nueva). Tres familias de claves:
#
#   mcp.servers            → JSON [ {name, transport, command, args, url,
#                                    description, enabled}, ... ]
#   mcp.secret.<name>      → JSON {"env": {...}, "headers": {...}} CIFRADO
#                            ENTERO con DPAPI (app/core/secrets.py). Aquí van
#                            los tokens (GITHUB_TOKEN, Authorization...). La
#                            API NUNCA los devuelve — solo los NOMBRES de las
#                            claves, para que la UI muestre "configurado".
#   mcp.tools.<name>       → JSON [{name, description, input_schema}] — caché
#                            del último descubrimiento. Permite que el catálogo
#                            del TIE muestre las acciones tras un reinicio SIN
#                            esperar a reconectar (la conexión real es perezosa).
#
# VALIDACIÓN DEL NOMBRE: el nombre del servidor acaba siendo parte del tool_id
# (`mcp_<name>`) que viaja por el planner, el toolloop, los permisos y la
# telemetría — se restringe a slug ([a-z0-9_-], empieza por alfanumérico) para
# que nunca pueda romper un prompt, un JSON o un id de permiso.
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core import secrets as secrets_helper

_KEY_SERVERS = "mcp.servers"
_KEY_SECRET = "mcp.secret."   # + name
_KEY_TOOLS = "mcp.tools."     # + name

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
TRANSPORTS = ("stdio", "sse", "http")


@dataclass
class MCPServerConfig:
    name: str
    transport: str = "stdio"          # "stdio" | "sse" | "http"
    command: str = ""                 # stdio: ejecutable (npx, python, ...)
    args: list[str] = field(default_factory=list)
    url: str = ""                     # sse/http: URL del servidor
    description: str = ""             # para el usuario Y para el modelo (contexto)
    enabled: bool = True
    # [C1c] Cómo se autentica. "oauth" = el usuario autoriza en la web del
    # propio servicio (sin pegar tokens); "token" = credenciales pegadas a
    # mano; "none" = no necesita nada. Append-only y con default seguro: una
    # config guardada por C1 (sin este campo) sigue comportándose igual.
    auth: str = "none"

    def to_dict(self) -> dict:
        return {
            "name": self.name, "transport": self.transport,
            "command": self.command, "args": list(self.args),
            "url": self.url, "description": self.description,
            "enabled": self.enabled, "auth": self.auth,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MCPServerConfig":
        return cls(
            name=str(d.get("name", "")),
            transport=str(d.get("transport", "stdio")),
            command=str(d.get("command", "")),
            args=[str(a) for a in (d.get("args") or [])],
            url=str(d.get("url", "")),
            description=str(d.get("description", "")),
            enabled=bool(d.get("enabled", True)),
            auth=str(d.get("auth", "none")),
        )


def validate_config(cfg: MCPServerConfig) -> Optional[str]:
    """None si es válida; texto con el motivo si no. La validación vive aquí
    (no en el endpoint) para que CUALQUIER camino que guarde un servidor —
    API, seed futuro del directorio de C1b — pase por la misma puerta."""
    if not _NAME_RE.match(cfg.name or ""):
        return ("nombre inválido: usa minúsculas, números, '-' o '_' "
                "(máx. 32 caracteres, empieza por letra o número)")
    if cfg.transport not in TRANSPORTS:
        return f"transporte inválido: {cfg.transport!r} (usa stdio, sse o http)"
    if cfg.transport == "stdio" and not cfg.command.strip():
        return "un servidor stdio necesita un comando (p. ej. npx)"
    if cfg.transport in ("sse", "http"):
        if not cfg.url.strip().lower().startswith(("http://", "https://")):
            return "un servidor sse/http necesita una URL http(s) válida"
    return None


# ---------------------------------------------------------------------------
# Acceso a Config — mismo patrón _get/_set que telegram.py
# ---------------------------------------------------------------------------
def _config_get(db, key: str) -> Optional[str]:
    from app.db.models import Config
    row = db.query(Config).filter(Config.key == key).first()
    return row.value if row else None


def _config_set(db, key: str, value: str) -> None:
    from app.db.models import Config
    row = db.query(Config).filter(Config.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Config(key=key, value=value))


def _config_del(db, key: str) -> None:
    from app.db.models import Config
    row = db.query(Config).filter(Config.key == key).first()
    if row:
        db.delete(row)


def _session():
    from app.db.database import SessionLocal
    return SessionLocal()


# ---------------------------------------------------------------------------
# Servidores
# ---------------------------------------------------------------------------
def list_servers() -> list[MCPServerConfig]:
    db = _session()
    try:
        raw = _config_get(db, _KEY_SERVERS)
    finally:
        db.close()
    if not raw:
        return []
    try:
        return [MCPServerConfig.from_dict(d) for d in json.loads(raw) if isinstance(d, dict)]
    except Exception:
        # Config corrupta → lista vacía, nunca romper el arranque (mismo
        # criterio que briefing_config: los defaults ante datos ilegibles).
        return []


def get_server(name: str) -> Optional[MCPServerConfig]:
    for cfg in list_servers():
        if cfg.name == name:
            return cfg
    return None


def upsert_server(cfg: MCPServerConfig,
                  server_secrets: Optional[dict] = None) -> None:
    """Crea o actualiza un servidor. `server_secrets` = {"env": {...},
    "headers": {...}}; None u omitido = conservar los ya guardados (la UI no
    necesita reescribir el secreto para cambiar la descripción — mismo
    contrato que el token de Telegram)."""
    motivo = validate_config(cfg)
    if motivo:
        raise ValueError(motivo)
    db = _session()
    try:
        servers = []
        raw = _config_get(db, _KEY_SERVERS)
        if raw:
            try:
                servers = [d for d in json.loads(raw) if isinstance(d, dict)]
            except Exception:
                servers = []
        servers = [d for d in servers if d.get("name") != cfg.name]
        servers.append(cfg.to_dict())
        servers.sort(key=lambda d: d.get("name", ""))
        _config_set(db, _KEY_SERVERS, json.dumps(servers, ensure_ascii=False))
        if server_secrets is not None:
            limpio = {
                "env": {str(k): str(v) for k, v in (server_secrets.get("env") or {}).items()},
                "headers": {str(k): str(v) for k, v in (server_secrets.get("headers") or {}).items()},
            }
            _config_set(db, _KEY_SECRET + cfg.name,
                        secrets_helper.encrypt(json.dumps(limpio, ensure_ascii=False)))
        db.commit()
    finally:
        db.close()


def delete_server(name: str) -> bool:
    db = _session()
    try:
        raw = _config_get(db, _KEY_SERVERS)
        servers = []
        if raw:
            try:
                servers = [d for d in json.loads(raw) if isinstance(d, dict)]
            except Exception:
                servers = []
        nuevos = [d for d in servers if d.get("name") != name]
        if len(nuevos) == len(servers):
            db.close()
            return False
        _config_set(db, _KEY_SERVERS, json.dumps(nuevos, ensure_ascii=False))
        _config_del(db, _KEY_SECRET + name)
        _config_del(db, _KEY_TOOLS + name)
        # [C1c] La autorización OAuth se va con el servidor: dejar el token
        # de un servicio ya borrado sería guardar una llave de una puerta que
        # ya no existe.
        _config_del(db, "mcp.oauth." + name)
        db.commit()
        return True
    finally:
        db.close()


def set_enabled(name: str, enabled: bool) -> bool:
    cfg = get_server(name)
    if cfg is None:
        return False
    cfg.enabled = enabled
    upsert_server(cfg)  # secrets=None → se conservan
    return True


# ---------------------------------------------------------------------------
# Secretos — se descifran SOLO para lanzar la conexión, jamás salen por la API
# ---------------------------------------------------------------------------
def get_secrets(name: str) -> dict:
    """{"env": {...}, "headers": {...}} descifrado. Vacíos si no hay."""
    db = _session()
    try:
        raw = _config_get(db, _KEY_SECRET + name)
    finally:
        db.close()
    if not raw:
        return {"env": {}, "headers": {}}
    try:
        data = json.loads(secrets_helper.decrypt(raw))
        return {"env": dict(data.get("env") or {}), "headers": dict(data.get("headers") or {})}
    except Exception:
        return {"env": {}, "headers": {}}


def secret_key_names(name: str) -> dict:
    """Solo los NOMBRES de las claves guardadas (para que la UI muestre
    'GITHUB_TOKEN: configurado' sin ver nunca el valor)."""
    data = get_secrets(name)
    return {"env": sorted(data["env"].keys()), "headers": sorted(data["headers"].keys())}


# ---------------------------------------------------------------------------
# Caché de tools descubiertas
# ---------------------------------------------------------------------------
def cache_tools(name: str, tools: list[dict]) -> None:
    db = _session()
    try:
        _config_set(db, _KEY_TOOLS + name, json.dumps(tools, ensure_ascii=False))
        db.commit()
    finally:
        db.close()


def cached_tools(name: str) -> list[dict]:
    db = _session()
    try:
        raw = _config_get(db, _KEY_TOOLS + name)
    finally:
        db.close()
    if not raw:
        return []
    try:
        return [t for t in json.loads(raw) if isinstance(t, dict)]
    except Exception:
        return []
