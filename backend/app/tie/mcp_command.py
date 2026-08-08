# app/tie/mcp_command.py — el puente MCP↔TIE (V1.2 C1b, doc 42 §3 y §4)
#
# Dos mitades del mismo problema —"¿cuándo uso un servidor MCP conectado?"—,
# juntas porque comparten la misma fuente (la lista de servidores) y la misma
# disciplina (determinismo y coste cero cuando no aplica):
#
#   1. EXPLÍCITA — `parse()`: "/github dame mis PRs". El usuario nombra el
#      servicio y Aithera no tiene que adivinar.
#   2. POR CONTEXTO — `classifier_block()`: los servicios conectados entran en
#      el prompt del clasificador con sus pistas, para que "la ruta naval de
#      Barcelona a Mallorca" pueda elegir el MCP de navegación sin que nadie
#      escriba ningún comando.
#
# El atajo EXPLÍCITO es determinista, 0 LLM, y se resuelve ANTES del
# clasificador — mismo sitio y mismo criterio que `quick_answers` (PU4) y
# `quick_memory` (PU10).
#
# LA DISTINCIÓN QUE NO SE PUEDE PERDER: `/github` expresa **intención de
# herramienta**, jamás **autorización**. Fija qué servidor usar; el gate del
# ApprovalGate y el permiso `mcp.use` (C1/A3b) siguen exactamente igual — el
# usuario que escribe `/github borra el repo` sigue viendo la petición de
# permiso antes de que nada ocurra.
#
# COSTE EN EL CAMINO CALIENTE: cero. `parse()` sale en la primera línea si el
# mensaje no empieza por "/", que es el 99,9% de los mensajes; solo entonces
# se consulta la lista de servidores conectados.
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional

from app.core.logging_config import get_system_logger
from app.tie.contracts import Intent, IntentType

logger = get_system_logger("tie.mcp_command")

# Caché del bloque para el clasificador. A diferencia de `parse()` —que solo
# corre cuando el mensaje empieza por "/"—, esto se consulta en el camino
# CALIENTE de cada mensaje no trivial, así que no puede pagar un viaje a la BD
# cada vez. TTL corto: conectar un servidor debe notarse enseguida, sin
# reiniciar (mismo criterio y mismo patrón que `capabilities_map`).
_CACHE_TTL_S = 30.0
_cache: dict[str, tuple[float, str]] = {}

# Mismo charset que valida `app.mcp.store` para el nombre de un servidor: lo
# que se puede conectar es exactamente lo que se puede invocar.
_CMD_RE = re.compile(r"^/([a-z0-9][a-z0-9_-]{0,31})(?:\s+(.*))?$",
                     re.IGNORECASE | re.DOTALL)


@dataclass
class MCPCommand:
    """Resultado del parseo. Dos formas mutuamente excluyentes:
      - `reply` != None  → hay que responder ESO y terminar el turno (listado
        de acciones del servidor, o slug desconocido). 0 LLM.
      - `tool_id` != None → el turno SIGUE su camino normal con `rest` como
        mensaje y ese servidor fijado en el intent."""
    slug: str
    tool_id: Optional[str] = None
    rest: str = ""
    reply: Optional[str] = None


def _servers() -> list:
    """Servidores MCP conectados Y habilitados. Aislado para que un fallo de
    BD no rompa un turno: sin lista, no hay comando (se sigue como siempre)."""
    try:
        from app import mcp as mcp_service

        return [s for s in mcp_service.list_servers() if s.enabled]
    except Exception as e:      # noqa: BLE001 — nunca romper el chat por esto
        logger.info(f"[mcp-cmd] no se pudo leer la lista de servidores: {e!r}")
        return []


def parse(text: str) -> Optional[MCPCommand]:
    """`/<servidor> [resto]` → MCPCommand; None si no aplica (el caso normal).

    Devuelve None también cuando NO hay ningún servidor MCP conectado: sin
    servidores, "/loquesea" no es un comando de MCP y no tiene por qué
    secuestrar el mensaje (podría ser una ruta, un fragmento de código…)."""
    raw = (text or "").strip()
    if not raw.startswith("/"):
        return None                      # salida en la 1.ª línea: coste cero
    m = _CMD_RE.match(raw)
    if not m:
        return None
    slug = m.group(1).lower()
    rest = (m.group(2) or "").strip()

    servers = _servers()
    if not servers:
        return None
    by_name = {s.name: s for s in servers}

    if slug not in by_name:
        # Slug desconocido PERO hay servidores conectados: el usuario intentó
        # invocar uno. Se le dice cuáles tiene, en vez de mandar "/loquesea"
        # al modelo como si fuera parte de la pregunta.
        nombres = ", ".join(f"/{n}" for n in sorted(by_name))
        return MCPCommand(slug=slug, reply=(
            f"No tienes ningún servicio conectado que se llame «{slug}». "
            f"Los que tienes ahora mismo: {nombres}.\n"
            f"Puedes conectar más en Ajustes → Conexiones → Servidores MCP."
        ))

    if not rest:
        return MCPCommand(slug=slug, reply=_actions_reply(by_name[slug]))

    return MCPCommand(slug=slug, tool_id=_tool_id(slug), rest=rest)


def _tool_id(slug: str) -> str:
    """El id con el que el servidor vive en el ToolManager. Se pide a
    `permission_service` (donde vive el prefijo como vocabulario de
    seguridad, C1) en vez de recomponerlo aquí: un solo sitio."""
    from app.automation import permission_service

    return permission_service.MCP_TOOL_PREFIX + slug


def _actions_reply(cfg) -> str:
    """`/github` a secas → qué sabe hacer ese servidor. De la caché de tools
    que dejó C1 al descubrirlas, así que es instantáneo y sin LLM."""
    from app import mcp as mcp_service

    tools = mcp_service.cached_tools(cfg.name)
    cabecera = f"**{cfg.name}**" + (f" — {cfg.description}" if cfg.description else "")
    if not tools:
        return (f"{cabecera}\n\nTodavía no sé qué sabe hacer este servicio: pulsa "
                f"«Probar» en Ajustes → Conexiones → Servidores MCP para que se "
                f"conecte y descubra sus herramientas.")
    lineas = []
    for t in tools[:25]:
        desc = (t.get("description") or "").strip().split("\n")[0][:110]
        lineas.append(f"- {t.get('name')}" + (f": {desc}" if desc else ""))
    extra = f"\n(y {len(tools) - 25} más)" if len(tools) > 25 else ""
    return (f"{cabecera}\n\nEsto es lo que puede hacer:\n" + "\n".join(lineas) + extra +
            f"\n\nEscribe `/{cfg.name} ` seguido de lo que quieras y me pongo con ello.")


# ---------------------------------------------------------------------------
# Mitad 2 — POR CONTEXTO (doc 42 §4)
# ---------------------------------------------------------------------------
def connected() -> list[tuple[str, str, str]]:
    """`[(tool_id, nombre, descripción)]` de los servidores conectados y
    habilitados. La descripción es la que el usuario escribió al conectarlo
    (o la del catálogo, si lo conectó desde el directorio) — por eso ese campo
    se diseñó en C1 "para ti y para el modelo"."""
    return [(_tool_id(s.name), s.name, (s.description or "").strip())
            for s in _servers()]


def classifier_block() -> str:
    """El bloque que se AÑADE al prompt del clasificador (`intents.py`).

    EL GAP QUE CIERRA (hallazgo de PU8, confirmado al auditar C1): la lista de
    `requires_tools` del clasificador es un TECHO — lo que no está en ella no
    puede llegar al camino de acción directa. Esa lista es estática y solo
    tiene las tools nativas, así que un servidor MCP conectado era invisible
    para el clasificador por muy bien descrito que estuviera: "dame la ruta
    naval a Mallorca" acabaría en `search`/`browser` en vez de en el servicio
    del usuario. Aquí se inyectan los conectados, con su descripción como
    pista.

    Cadena vacía si no hay ninguno: el prompt queda EXACTAMENTE como estaba
    (no-regresión para quien no use MCP, que es el caso por defecto)."""
    now = time.monotonic()
    hit = _cache.get("classifier")
    if hit and (now - hit[0]) < _CACHE_TTL_S:
        return hit[1]

    try:
        servicios = connected()
    except Exception:           # noqa: BLE001 — el clasificador nunca cae por esto
        servicios = []
    if not servicios:
        texto = ""
    else:
        lineas = [f'    "{tid}": {desc or nombre}'
                  + (f' (el usuario también puede pedirlo como "/{nombre}")' if not desc else "")
                  for tid, nombre, desc in servicios]
        texto = (
            "\n\nSERVICIOS EXTERNOS CONECTADOS POR EL USUARIO (MCP). Estos ids "
            "TAMBIÉN son valores válidos de \"requires_tools\", y tienen "
            "PREFERENCIA sobre una herramienta genérica cuando el mensaje cae "
            "claramente en su dominio (p.ej. si hay un servicio de repositorios "
            "conectado, una pregunta sobre commits o pull requests va a ese "
            "servicio, no a \"browser\" ni a \"search\"):\n" + "\n".join(lineas) +
            "\nSi el mensaje NO encaja con ninguno, ignóralos por completo."
        )
    _cache["classifier"] = (now, texto)
    return texto


def invalidate_cache() -> None:
    """Se llama al conectar/desconectar un servidor (endpoints de `/api/mcp`).

    Vacía las DOS cachés que dependen de la lista de servidores: la de aquí
    (30 s) y la del mapa de capacidades (`capabilities_map`, 1 HORA — sin
    esto, conectar GitHub y preguntar "¿qué sabes hacer?" seguiría sin
    mencionarlo durante una hora)."""
    _cache.pop("classifier", None)
    try:
        from app.tie import capabilities_map

        capabilities_map.invalidate()
    except Exception:           # noqa: BLE001 — invalidar nunca puede romper nada
        pass


def pin(intent: Intent, tool_id: str) -> Intent:
    """Fija el servidor en el intent que salga del clasificador.

    DOS COSAS, y las dos hacen falta:
      1. `requires_tools` gana el tool_id (si el clasificador ya lo puso, no
         se duplica).
      2. Si el intent quedó en un tipo de CAMINO CORTO (conversational/query
         simple), se sube a EXECUTE — el camino corto NO TIENE herramientas,
         así que dejarlo ahí sería aceptar el comando y no usar el servicio
         (mismo razonamiento y mismo remedio que `action_intent`, NEW-7).
    Nunca lanza: un fallo aquí devolvería el intent tal cual, y el turno
    seguiría como un mensaje normal."""
    try:
        tools = list(intent.requires_tools or [])
        if tool_id not in tools:
            tools.append(tool_id)
        intent.requires_tools = tools
        if intent.is_short_path:
            logger.info(f"[mcp-cmd] intent {intent.type.value!r} → EXECUTE: el camino "
                        f"corto no tiene herramientas y se pidió {tool_id!r}")
            intent.type = IntentType.EXECUTE
    except Exception as e:      # noqa: BLE001
        logger.info(f"[mcp-cmd] no se pudo fijar {tool_id!r} en el intent: {e!r}")
    return intent
