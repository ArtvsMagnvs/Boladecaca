# app/mcp/directory.py — el registro OFICIAL de servidores MCP (V1.2 C1b, doc 42 §2)
#
# El segundo nivel del directorio: cuando lo que el usuario busca no está en el
# catálogo curado del frontend, se busca en el registro oficial de la
# comunidad (`registry.modelcontextprotocol.io`, REST público sin auth) y se
# traduce a una config conectable.
#
# POR QUÉ EL PROXY VIVE EN EL BACKEND y no se llama desde el navegador: (a) el
# CORS del registro no es asunto nuestro, (b) la caché se comparte entre
# pestañas y reinicios de la UI, y (c) el mapeo entrada→`MCPServerConfig` es
# lógica que quiero PROBADA con fixtures reales, no repartida en un componente.
#
# EL MAPEO ES DETERMINISTA — código, nunca un LLM. La forma de una entrada del
# registro (verificada en vivo contra respuestas reales, doc 42 §1) ya trae
# todo lo que hace falta:
#   packages[] con registryType npm/pypi + runtimeHint + transport stdio
#       → un servidor stdio (`npx -y <paquete>`)
#   remotes[] con type streamable-http|sse + url + headers
#       → un servidor http/sse (el transporte `http` que C1 añadió al alza es
#         justo lo que hace conectable a la mayoría de entradas remotas)
#   environmentVariables[] / headers[] con isSecret/isRequired/description
#       → los campos del formulario de conexión, CON sus textos de ayuda
#
# HONESTIDAD: una entrada que no trae ni paquete conocido ni remoto soportado
# se devuelve marcada `connectable=False` con el motivo y el enlace al repo.
# Nunca se ADIVINA un comando: ejecutar lo que uno se inventa es justo lo que
# no se hace con código externo.
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.logging_config import get_system_logger
from app.core.sanitize import clean_external

logger = get_system_logger("mcp.directory")

REGISTRY_URL = "https://registry.modelcontextprotocol.io/v0/servers"
_TIMEOUT_S = 8.0
_CACHE_TTL_S = 900.0            # 15 min: el registro cambia despacio
_cache: dict[str, tuple[float, list]] = {}

# Runtimes que sabemos lanzar. `npx`/`uvx`/`bunx` descargan y ejecutan el
# paquete; el resto (docker, binarios sueltos…) NO se adivina.
_RUNTIME_BY_REGISTRY = {"npm": "npx", "pypi": "uvx"}
_KNOWN_RUNTIMES = {"npx", "uvx", "bunx"}
_REMOTE_TRANSPORT = {"streamable-http": "http", "http": "http", "sse": "sse"}


@dataclass
class DirectorySecret:
    """Un dato que el servidor necesita y el usuario tiene que aportar."""
    key: str                     # GITHUB_TOKEN / Authorization
    kind: str                    # "env" | "header"
    description: str = ""
    required: bool = False
    is_secret: bool = True


@dataclass
class DirectoryEntry:
    name: str                    # reverse-DNS del registro: io.github.foo/bar
    title: str
    description: str
    version: str = ""
    repository_url: str = ""
    # Config conectable (vacía si connectable=False)
    transport: str = ""
    command: str = ""
    args: list[str] = field(default_factory=list)
    url: str = ""
    secrets: list[DirectorySecret] = field(default_factory=list)
    connectable: bool = True
    reason: str = ""             # por qué NO es conectable, si no lo es
    suggested_slug: str = ""     # nombre corto propuesto para Aithera


def _slug_from(name: str) -> str:
    """`io.github.pulsemcp/remote-filesystem` → `remote-filesystem`. El nombre
    del registro es reverse-DNS y no vale como id de tool (el charset de
    `store.validate_config` es [a-z0-9_-])."""
    corto = (name or "").split("/")[-1].strip().lower()
    limpio = "".join(c if (c.isalnum() or c in "-_") else "-" for c in corto).strip("-")
    while "--" in limpio:
        limpio = limpio.replace("--", "-")
    return limpio[:32] or "servidor"


def _secrets_from_env(variables: list) -> list[DirectorySecret]:
    out = []
    for v in variables or []:
        if not isinstance(v, dict) or not v.get("name"):
            continue
        out.append(DirectorySecret(
            key=str(v["name"]), kind="env",
            description=str(v.get("description", "") or "")[:200],
            required=bool(v.get("isRequired")),
            # Sin `isSecret` explícito se trata como secreto igualmente: es más
            # seguro tapar un valor inocuo que enseñar uno que no debía verse.
            is_secret=bool(v.get("isSecret", True)),
        ))
    return out


def _secrets_from_headers(headers: list) -> list[DirectorySecret]:
    out = []
    for h in headers or []:
        if not isinstance(h, dict) or not h.get("name"):
            continue
        out.append(DirectorySecret(
            key=str(h["name"]), kind="header",
            description=str(h.get("description", "") or "")[:200],
            required=bool(h.get("isRequired")),
            is_secret=bool(h.get("isSecret", True)),
        ))
    return out


def _arg_values(items: list) -> list[str]:
    """Argumentos POSICIONALES declarados por el paquete (p.ej. `-y` de npx).
    Los `named` se omiten a propósito: casi siempre llevan valores que el
    usuario tendría que rellenar, y adivinarlos sería inventar."""
    out = []
    for a in items or []:
        if isinstance(a, dict) and a.get("type", "positional") == "positional":
            valor = a.get("value") or a.get("default")
            if valor:
                out.append(str(valor))
    return out


def map_entry(server: dict) -> DirectoryEntry:
    """Entrada del registro → algo conectable (o un "no puedo, y por qué").
    Función PURA: es lo que los tests ejercitan con respuestas reales."""
    server = clean_external(server or {})       # texto externo, S9c
    name = str(server.get("name", ""))
    entry = DirectoryEntry(
        name=name,
        title=str(server.get("title") or _slug_from(name)),
        description=str(server.get("description", "") or "")[:400],
        version=str(server.get("version", "") or ""),
        repository_url=str((server.get("repository") or {}).get("url", "") or ""),
        suggested_slug=_slug_from(name),
    )

    # 1) Paquete local (stdio) — el caso mayoritario del ecosistema.
    for pkg in (server.get("packages") or []):
        if not isinstance(pkg, dict):
            continue
        transporte = (pkg.get("transport") or {}).get("type", "stdio")
        if transporte != "stdio":
            continue
        runtime = (pkg.get("runtimeHint")
                   or _RUNTIME_BY_REGISTRY.get(str(pkg.get("registryType", "")).lower(), ""))
        identifier = str(pkg.get("identifier", "") or "")
        if runtime not in _KNOWN_RUNTIMES or not identifier:
            continue
        entry.transport = "stdio"
        entry.command = runtime
        entry.args = (_arg_values(pkg.get("runtimeArguments"))
                      + [identifier]
                      + _arg_values(pkg.get("packageArguments")))
        entry.secrets = _secrets_from_env(pkg.get("environmentVariables"))
        return entry

    # 2) Servidor remoto.
    for remote in (server.get("remotes") or []):
        if not isinstance(remote, dict):
            continue
        transporte = _REMOTE_TRANSPORT.get(str(remote.get("type", "")).lower())
        url = str(remote.get("url", "") or "")
        if not transporte or not url.lower().startswith(("http://", "https://")):
            continue
        entry.transport = transporte
        entry.url = url
        entry.secrets = _secrets_from_headers(remote.get("headers"))
        return entry

    entry.connectable = False
    entry.reason = ("este servidor no publica ni un paquete que Aithera sepa lanzar "
                    "(npx/uvx) ni una dirección web: mira su repositorio para ver "
                    "cómo se instala")
    return entry


async def search(query: str, limit: int = 20) -> list[DirectoryEntry]:
    """Busca en el registro oficial. Fail-soft: sin red, con el registro caído
    o con una respuesta rara, devuelve lista vacía — el directorio curado del
    frontend sigue funcionando igual."""
    q = (query or "").strip()
    if not q:
        return []
    clave = f"{q.lower()}|{limit}"
    hit = _cache.get(clave)
    now = time.monotonic()
    if hit and (now - hit[0]) < _CACHE_TTL_S:
        return hit[1]

    try:
        import httpx

        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            r = await client.get(REGISTRY_URL,
                                 params={"search": q, "limit": max(1, min(limit, 50))})
            r.raise_for_status()
            data = r.json()
    except Exception as e:      # noqa: BLE001 — buscar nunca puede romper Ajustes
        logger.info(f"[mcp-dir] el registro no respondió ({type(e).__name__}: {e})")
        return []

    salida: list[DirectoryEntry] = []
    vistos: set[str] = set()
    for item in (data.get("servers") or []):
        srv = item.get("server") if isinstance(item, dict) else None
        if not isinstance(srv, dict) or not srv.get("name"):
            continue
        if srv["name"] in vistos:       # el registro lista versiones repetidas
            continue
        vistos.add(srv["name"])
        try:
            salida.append(map_entry(srv))
        except Exception:               # una entrada rara no tumba la búsqueda
            continue
    _cache[clave] = (now, salida)
    return salida


def entry_to_dict(e: DirectoryEntry) -> dict[str, Any]:
    return {
        "name": e.name, "title": e.title, "description": e.description,
        "version": e.version, "repository_url": e.repository_url,
        "suggested_slug": e.suggested_slug,
        "transport": e.transport, "command": e.command, "args": e.args, "url": e.url,
        "connectable": e.connectable, "reason": e.reason,
        "secrets": [{"key": s.key, "kind": s.kind, "description": s.description,
                     "required": s.required, "is_secret": s.is_secret}
                    for s in e.secrets],
    }


def clear_cache() -> None:
    _cache.clear()
