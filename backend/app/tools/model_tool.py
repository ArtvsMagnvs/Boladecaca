# backend/app/tools/model_tool.py
#
# V1.0/1.1 (Tools): gestion de modelos locales de Ollama. Habla con la API
# REST de Ollama directamente (misma base_url que usa OllamaProvider,
# Settings.OLLAMA_BASE_URL) -- no reutiliza el AIManager porque estas
# acciones (pull/delete/listar instalados) son gestion de catalogo, no
# generacion de texto.
#
# Acciones:
#   list_models    -> GET /api/tags (modelos instalados localmente)
#   load_model     -> "calienta" un modelo en memoria (prompt vacio, sin generar)
#   pull_model     -> POST /api/pull (descarga desde la libreria de Ollama)
#   delete_model   -> DELETE /api/delete
#   gpu_ram_status -> psutil (RAM) + nvidia-smi si hay GPU NVIDIA (fail-soft)
#
# Descarga directa desde HuggingFace (repos .safetensors/.gguf arbitrarios,
# fuera del catalogo de Ollama): NO implementada aqui a proposito -- exige la
# dependencia nueva `huggingface_hub` + decidir el flujo de importacion a
# Ollama (Modelfile) o a un runtime GGUF aparte. Queda documentada como
# siguiente paso, no construida a medias.

from typing import Dict, Any, List, Optional

import httpx

from .base import BaseTool

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


def _base_url() -> str:
    from app.core.config import settings
    return settings.OLLAMA_BASE_URL.rstrip("/")


class ModelTool(BaseTool):
    tool_id = "model"
    name = "Model Tool"
    description = (
        "Gestiona los modelos de IA locales (Ollama): listar, cargar en memoria, "
        "descargar/eliminar del catalogo local, y consultar el estado de GPU/RAM."
    )
    requires_confirmation = False  # depende de la accion

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            handler = {
                "list_models": self._list_models,
                "load_model": self._load_model,
                "pull_model": self._pull_model,
                "delete_model": self._delete_model,
                "gpu_ram_status": self._gpu_ram_status,
            }.get(action)
            if not handler:
                return {
                    "success": False, "result": None,
                    "error": f"Accion desconocida: {action}. Disponibles: list_models, load_model, pull_model, delete_model, gpu_ram_status",
                }
            return await handler(params)
        except httpx.ConnectError:
            return {"success": False, "result": None, "error": f"no se pudo conectar a Ollama en {_base_url()} (¿esta arrancado?)"}
        except Exception as e:
            return {"success": False, "result": None, "error": f"{type(e).__name__}: {e}"}

    def list_actions(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "list_models",
                "description": "Lista los modelos de Ollama instalados localmente.",
                "requires_confirmation": False,
                "params": {},
            },
            {
                "id": "load_model",
                "description": "Carga un modelo en memoria (sin generar texto) para que la siguiente peticion sea rapida.",
                "requires_confirmation": False,
                "params": {"model": "string (ej. 'llama3')"},
            },
            {
                "id": "pull_model",
                "description": "Descarga un modelo desde la libreria de Ollama. Puede tardar varios minutos segun el tamano.",
                "requires_confirmation": True,
                "params": {"model": "string (ej. 'llama3:8b')"},
            },
            {
                "id": "delete_model",
                "description": "Elimina un modelo instalado localmente (libera disco).",
                "requires_confirmation": True,
                "params": {"model": "string"},
            },
            {
                "id": "gpu_ram_status",
                "description": "Estado de RAM del sistema y de GPU NVIDIA si hay una disponible.",
                "requires_confirmation": False,
                "params": {},
            },
        ]

    # ------------------------------------------------------------------

    async def _list_models(self, params: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{_base_url()}/api/tags")
            r.raise_for_status()
            data = r.json()
        models = [
            {"name": m.get("name"), "size_gb": round((m.get("size") or 0) / (1024 ** 3), 2),
             "modified_at": m.get("modified_at")}
            for m in data.get("models", [])
        ]
        return {"success": True, "result": {"models": models, "count": len(models)}, "error": None}

    async def _load_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        model = (params.get("model") or "").strip()
        if not model:
            return {"success": False, "result": None, "error": "falta parametro: model"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(f"{_base_url()}/api/generate", json={
                "model": model, "prompt": "", "stream": False,
            })
        if r.status_code != 200:
            return {"success": False, "result": None, "error": f"Ollama devolvio {r.status_code}: {r.text[:300]}"}
        return {"success": True, "result": {"model": model, "loaded": True}, "error": None}

    async def _pull_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        model = (params.get("model") or "").strip()
        if not model:
            return {"success": False, "result": None, "error": "falta parametro: model"}
        # stream=False -> Ollama bloquea hasta terminar y devuelve un unico JSON
        # (mas simple para el contrato success/result/error del ToolManager; el
        # timeout duro del manager, hasta 300s, sigue aplicando -- un modelo muy
        # grande puede necesitar mas tiempo del que el ToolManager permite).
        async with httpx.AsyncClient(timeout=290.0) as client:
            r = await client.post(f"{_base_url()}/api/pull", json={"model": model, "stream": False})
        if r.status_code != 200:
            return {"success": False, "result": None, "error": f"Ollama devolvio {r.status_code}: {r.text[:300]}"}
        data = r.json()
        status = data.get("status", "")
        if "error" in data:
            return {"success": False, "result": None, "error": data["error"]}
        return {"success": True, "result": {"model": model, "status": status}, "error": None}

    async def _delete_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        model = (params.get("model") or "").strip()
        if not model:
            return {"success": False, "result": None, "error": "falta parametro: model"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.request("DELETE", f"{_base_url()}/api/delete", json={"model": model})
        if r.status_code == 404:
            return {"success": False, "result": None, "error": f"modelo no encontrado: {model}"}
        if r.status_code != 200:
            return {"success": False, "result": None, "error": f"Ollama devolvio {r.status_code}: {r.text[:300]}"}
        return {"success": True, "result": {"model": model, "deleted": True}, "error": None}

    async def _gpu_ram_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        import asyncio

        ram: Optional[dict] = None
        if psutil is not None:
            def _ram():
                vm = psutil.virtual_memory()
                return {
                    "total_mb": round(vm.total / (1024 * 1024)),
                    "used_mb": round(vm.used / (1024 * 1024)),
                    "percent_used": vm.percent,
                }
            ram = await asyncio.to_thread(_ram)

        gpu = None
        gpu_error = None
        try:
            proc = await asyncio.create_subprocess_exec(
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,utilization.gpu",
                "--format=csv,noheader,nounits",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            if proc.returncode == 0 and stdout:
                gpus = []
                for line in stdout.decode("utf-8", errors="replace").strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) == 4:
                        gpus.append({
                            "name": parts[0], "memory_total_mb": int(parts[1]),
                            "memory_used_mb": int(parts[2]), "utilization_percent": int(parts[3]),
                        })
                gpu = gpus
        except FileNotFoundError:
            gpu_error = "nvidia-smi no encontrado (sin GPU NVIDIA o drivers no instalados)"
        except Exception as e:
            gpu_error = f"{type(e).__name__}: {e}"

        return {
            "success": True,
            "result": {"ram": ram, "gpu": gpu, "gpu_error": gpu_error},
            "error": None,
        }
