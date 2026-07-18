# backend/app/tools/download_tool.py
#
# V1.0/1.1 (Tools): descargas de archivos por URL, separadas del futuro
# Browser Tool (esto es HTTP directo, sin navegador). El destino reusa la MISMA
# validacion de paths que FilesystemTool (solo dentro de HOME).
#
# Modelo de ejecucion: download_url INICIA la descarga como tarea de fondo y
# devuelve al instante un download_id -- una descarga grande superaria el
# timeout duro del ToolManager (max 300s) si se hiciera de forma bloqueante.
# get_download_status/cancel_download consultan/paran esa tarea despues.
#
# Acciones:
#   download_url      -> inicia una descarga (no bloquea)
#   get_download_status -> progreso/estado de una descarga
#   cancel_download    -> cancela una descarga en curso
#
# Seguridad: solo http(s), destino dentro de HOME, limite de tamano por
# defecto (protege contra llenar el disco con una URL maliciosa/enorme).

import asyncio
import uuid
from typing import Dict, Any, List, Optional

import httpx

from .base import BaseTool
from .filesystem_tool import _resolve_user_path, _is_path_allowed

DEFAULT_MAX_BYTES = 2 * 1024 * 1024 * 1024  # 2GB

# Estado de descargas activas/recientes, en memoria del proceso backend.
# {download_id: {"url","path","status","downloaded_bytes","total_bytes","error","_cancel","_task"}}
_DOWNLOADS: Dict[str, Dict[str, Any]] = {}


class DownloadTool(BaseTool):
    tool_id = "download"
    name = "Download Tool"
    description = (
        "Descarga archivos por URL (http/https) a una ruta dentro de HOME, "
        "en segundo plano. Permite consultar el progreso y cancelar."
    )
    requires_confirmation = False  # depende de la accion

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            handler = {
                "download_url": self._download_url,
                "get_download_status": self._get_status,
                "cancel_download": self._cancel,
            }.get(action)
            if not handler:
                return {
                    "success": False, "result": None,
                    "error": f"Accion desconocida: {action}. Disponibles: download_url, get_download_status, cancel_download",
                }
            return await handler(params)
        except Exception as e:
            return {"success": False, "result": None, "error": f"{type(e).__name__}: {e}"}

    def list_actions(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "download_url",
                "description": "Inicia la descarga de una URL a un archivo local. No bloquea.",
                "requires_confirmation": True,
                "params": {
                    "url": "string (http:// o https://)",
                    "path": "string (destino, dentro de HOME)",
                    "max_bytes": f"int opcional (default {DEFAULT_MAX_BYTES // (1024*1024)}MB)",
                },
            },
            {
                "id": "get_download_status",
                "description": "Progreso/estado de una descarga (downloading|done|failed|cancelled).",
                "requires_confirmation": False,
                "params": {"download_id": "string"},
            },
            {
                "id": "cancel_download",
                "description": "Cancela una descarga en curso.",
                "requires_confirmation": False,
                "params": {"download_id": "string"},
            },
        ]

    # ------------------------------------------------------------------

    async def _download_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = (params.get("url") or "").strip()
        path_str = params.get("path", "")
        if not url or not path_str:
            return {"success": False, "result": None, "error": "faltan parametros: url y path"}
        if not (url.startswith("http://") or url.startswith("https://")):
            return {"success": False, "result": None, "error": "solo se permiten URLs http:// o https://"}

        path = _resolve_user_path(path_str)
        if not _is_path_allowed(path):
            return {"success": False, "result": None, "error": f"destino fuera de zonas permitidas: {path}"}

        max_bytes = int(params.get("max_bytes") or DEFAULT_MAX_BYTES)

        download_id = uuid.uuid4().hex[:12]
        state: Dict[str, Any] = {
            "url": url, "path": str(path), "status": "downloading",
            "downloaded_bytes": 0, "total_bytes": None, "error": None, "_cancel": False,
        }
        _DOWNLOADS[download_id] = state
        state["_task"] = asyncio.create_task(self._do_download(download_id, url, path, max_bytes))

        return {"success": True, "result": {"download_id": download_id, "status": "started"}, "error": None}

    async def _do_download(self, download_id: str, url: str, path, max_bytes: int) -> None:
        state = _DOWNLOADS[download_id]
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
                async with client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    cl = resp.headers.get("content-length")
                    state["total_bytes"] = int(cl) if cl else None

                    def _open():
                        return open(path, "wb")
                    f = await asyncio.to_thread(_open)
                    try:
                        async for chunk in resp.aiter_bytes(chunk_size=65536):
                            if state["_cancel"]:
                                state["status"] = "cancelled"
                                return
                            if state["downloaded_bytes"] + len(chunk) > max_bytes:
                                state["status"] = "failed"
                                state["error"] = f"supera el limite de {max_bytes // (1024*1024)}MB"
                                return
                            await asyncio.to_thread(f.write, chunk)
                            state["downloaded_bytes"] += len(chunk)
                    finally:
                        await asyncio.to_thread(f.close)
            state["status"] = "done"
        except asyncio.CancelledError:
            state["status"] = "cancelled"
        except Exception as e:
            state["status"] = "failed"
            state["error"] = f"{type(e).__name__}: {e}"

    async def _get_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        download_id = params.get("download_id", "")
        state = _DOWNLOADS.get(download_id)
        if not state:
            return {"success": False, "result": None, "error": f"descarga no encontrada: {download_id}"}
        return {
            "success": True,
            "result": {k: v for k, v in state.items() if not k.startswith("_")},
            "error": None,
        }

    async def _cancel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        download_id = params.get("download_id", "")
        state = _DOWNLOADS.get(download_id)
        if not state:
            return {"success": False, "result": None, "error": f"descarga no encontrada: {download_id}"}
        state["_cancel"] = True
        task: Optional[asyncio.Task] = state.get("_task")
        if task and not task.done():
            task.cancel()
        return {"success": True, "result": {"download_id": download_id, "cancelling": True}, "error": None}
