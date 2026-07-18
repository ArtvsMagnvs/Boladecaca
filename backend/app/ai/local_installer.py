# app/ai/local_installer.py — instalación de modelos locales con 1 clic (V1.0)
#
# Descarga automática vía `POST /api/pull` de Ollama con `stream=true`: Ollama
# emite líneas JSON con el progreso real (`total`/`completed`), que aquí se
# traducen a un porcentaje consultable desde la UI.
#
# Por qué en segundo plano y no una llamada bloqueante: un modelo son 5-21 GB;
# ninguna petición HTTP (ni el timeout duro del ToolManager, 300 s máx) aguanta
# eso. Mismo patrón que `DownloadTool`: `start()` devuelve al instante un id,
# y `status()`/`cancel()` consultan/paran después.
#
# Al terminar con éxito, el modelo se da de alta en la tabla `local_models` —
# ahí es cuando pasa a ser un candidato REAL para el MEL (registry lo ve y el
# Rule Engine puede elegirlo).
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Optional

import httpx

from app.core.logging_config import get_system_logger
from app.ai.local_catalog import find_model

logger = get_system_logger("ai.local_installer")

# {tag: {status, percent, downloaded_gb, total_gb, error, _cancel, _task}}
_JOBS: dict[str, dict[str, Any]] = {}


def _base_url() -> str:
    from app.core.config import settings
    return settings.OLLAMA_BASE_URL.rstrip("/")


def status(tag: str) -> Optional[dict]:
    """Progreso de una instalación (o None si nunca se lanzó para ese tag)."""
    job = _JOBS.get(tag)
    if not job:
        return None
    return {k: v for k, v in job.items() if not k.startswith("_")}


def all_jobs() -> dict[str, dict]:
    """Todas las instalaciones vivas/recientes — la UI las pinta de una vez."""
    return {tag: status(tag) for tag in _JOBS}


def start(tag: str) -> dict:
    """Lanza la descarga en segundo plano. Idempotente: si ya está en curso,
    devuelve el estado actual en vez de duplicar la descarga."""
    job = _JOBS.get(tag)
    if job and job.get("status") == "downloading":
        return status(tag)

    _JOBS[tag] = {
        "tag": tag, "status": "downloading", "percent": 0.0,
        "downloaded_gb": 0.0, "total_gb": None, "error": None, "_cancel": False,
    }
    _JOBS[tag]["_task"] = asyncio.create_task(_pull(tag))
    return status(tag)


def cancel(tag: str) -> bool:
    """Cancela una descarga en curso. Ollama deja el progreso parcial en su
    caché, así que reintentar más tarde REANUDA en vez de empezar de cero."""
    job = _JOBS.get(tag)
    if not job or job.get("status") != "downloading":
        return False
    job["_cancel"] = True
    task = job.get("_task")
    if task and not task.done():
        task.cancel()
    return True


async def _pull(tag: str) -> None:
    job = _JOBS[tag]
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{_base_url()}/api/pull",
                                     json={"model": tag, "stream": True}) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if job["_cancel"]:
                        job["status"] = "cancelled"
                        return
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Ollama informa el fallo en el propio cuerpo (HTTP sigue 200):
                    # p.ej. un tag que no existe en el registro.
                    if data.get("error"):
                        job["status"] = "failed"
                        job["error"] = str(data["error"])
                        return

                    total = data.get("total")
                    completed = data.get("completed")
                    if total:
                        job["total_gb"] = round(total / (1024 ** 3), 2)
                        if completed:
                            job["downloaded_gb"] = round(completed / (1024 ** 3), 2)
                            job["percent"] = round(completed / total * 100, 1)
                    job["step"] = data.get("status", "")

        job["percent"] = 100.0
        job["status"] = "done"
        _register_installed(tag)
        logger.info(f"[local_installer] modelo instalado: {tag}")
    except asyncio.CancelledError:
        job["status"] = "cancelled"
    except httpx.ConnectError:
        job["status"] = "failed"
        job["error"] = f"no se pudo conectar con Ollama en {_base_url()} (¿está arrancado?)"
    except Exception as e:
        job["status"] = "failed"
        job["error"] = f"{type(e).__name__}: {e}"
        logger.error(f"[local_installer] fallo instalando {tag}: {e}")


def _register_installed(tag: str) -> None:
    """Alta en `local_models` → a partir de aquí el MEL lo ve como candidato.
    Best-effort: si la BD falla, el modelo ya está descargado y se puede
    reintentar el alta; nunca se pierde la descarga por esto."""
    from app.db.database import SessionLocal
    from app.db.models import LocalModel

    meta = find_model(tag) or {}
    db = SessionLocal()
    try:
        row = db.query(LocalModel).filter(LocalModel.model_tag == tag).first()
        if row:
            row.enabled = True
            row.installed_at = datetime.utcnow()
        else:
            db.add(LocalModel(
                family=meta.get("family") or "otros",
                model_tag=tag,
                label=meta.get("label") or tag,
                size_gb=meta.get("size_gb"),
                enabled=True,
                installed_at=datetime.utcnow(),
            ))
        db.commit()
    except Exception as e:
        logger.error(f"[local_installer] alta en local_models falló: {type(e).__name__}: {e}")
        db.rollback()
    finally:
        db.close()


async def installed_tags() -> set[str]:
    """Modelos realmente presentes en Ollama (fuente de verdad del disco).
    Se cruza con el catálogo para que la UI sepa qué está instalado aunque el
    usuario lo bajara a mano con `ollama pull`."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(f"{_base_url()}/api/tags")
            r.raise_for_status()
            return {m.get("name", "") for m in r.json().get("models", [])}
    except Exception:
        return set()
