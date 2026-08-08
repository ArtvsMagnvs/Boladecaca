# app/mcp/client.py — conexión con servidores MCP externos (V1.2 C1, doc 27 §C1)
#
# LA RESTRICCIÓN QUE DICTA EL DISEÑO: los transports del SDK MCP
# (`stdio_client`, `sse_client`, `streamable_http_client`) son async context
# managers de anyio, y un cancel-scope de anyio DEBE entrar y salir en la MISMA
# task — abrir la conexión en una task y usarla desde otra revienta con
# "Attempted to exit cancel scope in a different task". Por eso cada servidor
# tiene UN worker-task que posee la pila entera (transport + ClientSession) y
# atiende llamadas por una cola. Las misiones concurrentes comparten la sesión
# del servidor (correcto: es UN proceso servidor) pero cada llamada es
# independiente — no hay estado por-misión que mezclar aquí.
#
# LECCIONES HEREDADAS (no reinventadas):
#   - S9 (browser): lanzamiento con double-checked locking — dos misiones que
#     llegan a la vez no lanzan dos procesos del mismo servidor.
#   - S9b (browser): un worker MUERTO se detecta y se relanza UNA vez en el
#     siguiente uso; si el relanzamiento también falla, el error sube honesto —
#     jamás un bucle de relanzamientos.
#   - Sesión A (preflight): el estado de la última conexión queda registrado
#     (`last_error`) para que el preflight del proxy responda en 1 ms sin
#     lanzar procesos.
#
# WINDOWS + npx: CreateProcess no ejecuta .cmd/.bat directamente de forma
# fiable; los servidores MCP más comunes se lanzan con `npx`/`npm` (que en
# Windows son .cmd). `_resolve_command` los envuelve en `cmd /c` — sin esto,
# "Conectar" fallaría en la máquina real del usuario con la mayoría de
# servidores del ecosistema.
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
from typing import Any, Optional

from app.core.config import settings

from . import store

logger = logging.getLogger(__name__)

# Registro de conexiones vivas: {server_name: MCPConnection}.
_connections: dict[str, "MCPConnection"] = {}
# Lock de LANZAMIENTO (patrón S9): protege la creación de la conexión, no cada
# llamada. Se recrea perezosamente porque pytest-anyio usa un loop por test
# (misma nota de entorno que test_audit_s9_browser_lock).
_launch_lock: Optional[asyncio.Lock] = None


def _lock() -> asyncio.Lock:
    global _launch_lock
    if _launch_lock is None:
        _launch_lock = asyncio.Lock()
    return _launch_lock


def _resolve_command(command: str, args: list[str]) -> tuple[str, list[str]]:
    """En Windows, un comando que resuelve a .cmd/.bat (npx, npm) se envuelve
    en `cmd /c`. En el resto de casos, tal cual."""
    if sys.platform != "win32":
        return command, args
    resolved = shutil.which(command) or command
    if resolved.lower().endswith((".cmd", ".bat")):
        return "cmd", ["/c", resolved, *args]
    return resolved, list(args)


class MCPConnection:
    """La conexión con UN servidor MCP. Un worker-task posee la pila async
    completa; el resto del backend le habla por la cola."""

    def __init__(self, cfg: store.MCPServerConfig):
        self.cfg = cfg
        self.tools: list[dict] = []          # [{name, description, input_schema}]
        self.last_error: Optional[str] = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._ready = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    # -- estado ---------------------------------------------------------
    @property
    def alive(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def connected(self) -> bool:
        return self.alive and self._ready.is_set()

    # -- ciclo de vida --------------------------------------------------
    async def ensure_ready(self, timeout: Optional[float] = None) -> None:
        """Lanza el worker si hace falta y espera a que la sesión esté
        inicializada (initialize + list_tools). Lanza RuntimeError con el
        motivo real si la conexión no se logra en el plazo."""
        timeout = timeout or settings.MCP_CONNECT_TIMEOUT_S
        if self.connected:
            return
        async with _lock():
            if not self.alive:                      # double-check dentro del lock
                self._ready = asyncio.Event()
                self.last_error = None
                self._task = asyncio.create_task(
                    self._run(), name=f"mcp-{self.cfg.name}")
        # Se espera a lo PRIMERO que ocurra: listo, o el worker MUERTO. Sin la
        # segunda pata, un servidor que revienta al arrancar (comando roto,
        # paquete inexistente) se comía el timeout ENTERO antes de reportar —
        # verificado en vivo: 30s para un proceso que salió en <1s.
        task = self._task
        waiter = asyncio.ensure_future(self._ready.wait())
        try:
            done, _ = await asyncio.wait({waiter, task}, timeout=timeout,
                                         return_when=asyncio.FIRST_COMPLETED)
        finally:
            waiter.cancel()
        if self._ready.is_set():
            return
        if task in done:
            # El worker murió durante el arranque — last_error trae la causa.
            raise RuntimeError(self.last_error or
                               f"el servidor MCP '{self.cfg.name}' no pudo arrancar")
        self.last_error = (f"el servidor MCP '{self.cfg.name}' no respondió "
                           f"en {timeout:.0f}s al conectar")
        await self.shutdown()
        raise RuntimeError(self.last_error)

    async def shutdown(self) -> None:
        task = self._task
        self._task = None
        self._ready = asyncio.Event()
        if task is not None and not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(task, timeout=5)
            except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                pass

    # -- llamadas -------------------------------------------------------
    async def call(self, tool_name: str, arguments: dict,
                   timeout: Optional[float] = None) -> dict:
        """Ejecuta una tool del servidor. Devuelve {"is_error", "text",
        "structured"}. Un worker muerto se relanza UNA vez (S9b); un timeout
        de llamada mata el worker (podría estar colgado a mitad de request —
        reutilizarlo dejaría la cola envenenada) y el error sube honesto."""
        timeout = timeout or settings.MCP_CALL_TIMEOUT_S
        if not self.connected:
            await self.ensure_ready()               # relanzamiento único; si falla, sube
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        await self._queue.put((fut, tool_name, arguments))
        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            self.last_error = (f"'{tool_name}' del servidor MCP '{self.cfg.name}' "
                               f"superó {timeout:.0f}s")
            await self.shutdown()
            raise RuntimeError(self.last_error)

    # -- worker ---------------------------------------------------------
    async def _run(self) -> None:
        try:
            transport_cm = self._make_transport()
            async with transport_cm as streams:
                read, write = streams[0], streams[1]
                from mcp import ClientSession
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listado = await session.list_tools()
                    self.tools = [_tool_to_dict(t) for t in (listado.tools or [])]
                    try:
                        store.cache_tools(self.cfg.name, self.tools)
                    except Exception:
                        pass                        # la caché es best-effort
                    self.last_error = None
                    self._ready.set()
                    await self._serve(session)
        except asyncio.CancelledError:
            raise
        except BaseException as e:                  # anyio agrupa en ExceptionGroup
            self.last_error = f"{type(e).__name__}: {_flatten_exc(e)}"[:300]
            logger.warning(f"[mcp] servidor '{self.cfg.name}' caído: {self.last_error}")
        finally:
            self._ready = asyncio.Event()           # nunca "conectado" con worker muerto

    async def _serve(self, session) -> None:
        while True:
            fut, tool_name, arguments = await self._queue.get()
            if fut.done():                          # el caller ya desistió (timeout)
                continue
            try:
                result = await session.call_tool(tool_name, arguments or {})
                if not fut.done():
                    fut.set_result(_result_to_dict(result))
            except Exception as e:
                if not fut.done():
                    fut.set_exception(RuntimeError(
                        f"fallo llamando a '{tool_name}' en '{self.cfg.name}': "
                        f"{type(e).__name__}: {e}"))

    def _make_transport(self):
        cfg = self.cfg
        srv_secrets = store.get_secrets(cfg.name)
        if cfg.transport == "stdio":
            from mcp import StdioServerParameters
            from mcp.client.stdio import get_default_environment, stdio_client
            command, args = _resolve_command(cfg.command, cfg.args)
            env = get_default_environment()
            env.update(srv_secrets.get("env") or {})
            return stdio_client(StdioServerParameters(
                command=command, args=args, env=env))
        headers = srv_secrets.get("headers") or None
        if cfg.transport == "sse":
            from mcp.client.sse import sse_client
            return sse_client(cfg.url, headers=headers)
        # "http" (streamable HTTP, el transport moderno para servidores
        # remotos — SSE quedó deprecado en el estándar). Los headers viajan
        # por un cliente httpx propio del SDK.
        from mcp.client.streamable_http import (create_mcp_http_client,
                                                streamable_http_client)
        http_client = create_mcp_http_client(headers=headers) if headers else None
        return streamable_http_client(cfg.url, http_client=http_client)


# ---------------------------------------------------------------------------
# Helpers de conversión — el resto de Aithera nunca ve tipos del SDK
# ---------------------------------------------------------------------------
def _tool_to_dict(tool) -> dict:
    schema = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None) or {}
    if hasattr(schema, "model_dump"):
        schema = schema.model_dump(mode="json")
    return {
        "name": getattr(tool, "name", ""),
        "description": getattr(tool, "description", "") or "",
        "input_schema": schema if isinstance(schema, dict) else {},
    }


def _result_to_dict(result) -> dict:
    """CallToolResult → dict plano. El texto se concatena de los bloques de
    contenido; lo estructurado (si el servidor lo da) viaja aparte."""
    partes = []
    for bloque in (getattr(result, "content", None) or []):
        texto = getattr(bloque, "text", None)
        if texto:
            partes.append(str(texto))
    structured = getattr(result, "structured_content", None)
    if hasattr(structured, "model_dump"):
        structured = structured.model_dump(mode="json")
    return {
        "is_error": bool(getattr(result, "is_error", False)),
        "text": "\n".join(partes),
        "structured": structured if isinstance(structured, (dict, list)) else None,
    }


def _flatten_exc(e: BaseException) -> str:
    """anyio envuelve los fallos del transport en ExceptionGroup; para el
    usuario, la causa hoja es la que informa."""
    if isinstance(e, BaseExceptionGroup):
        hojas = e.exceptions
        if hojas:
            return _flatten_exc(hojas[0])
    return str(e)


# ---------------------------------------------------------------------------
# Registro de conexiones
# ---------------------------------------------------------------------------
def get_connection(name: str) -> Optional[MCPConnection]:
    """La conexión para un servidor configurado (se crea perezosa, NO se
    conecta aquí — conectar es cosa de ensure_ready/call)."""
    conn = _connections.get(name)
    if conn is not None:
        return conn
    cfg = store.get_server(name)
    if cfg is None:
        return None
    conn = MCPConnection(cfg)
    _connections[name] = conn
    return conn


def drop_connection(name: str) -> None:
    """Retira la conexión del registro (al borrar/deshabilitar un servidor).
    El shutdown real lo hace el caller async."""
    _connections.pop(name, None)


async def shutdown_all() -> None:
    for name in list(_connections):
        conn = _connections.pop(name)
        try:
            await conn.shutdown()
        except Exception:
            pass
