# app/ai/local_installer.py — instalación de modelos locales con 1 clic (V1.0)
#
# Descarga vía el CLI de Ollama en un proceso INVISIBLE (`ollama pull <tag>`),
# parseando su barra de progreso para reflejar el % real en la UI.
#
# Por qué el CLI y no la API HTTP (petición del usuario, 2026-07-18): es la vía
# más directa —la misma que usaría el usuario en su terminal—, hereda tal cual el
# manejo de reintentos/reanudación del cliente oficial, y sobre todo **cancelar
# es matar el proceso**, que es fiable de verdad; con la API había que confiar en
# que el servidor atendiera una señal cooperativa.
#
# BUG CORREGIDO (2026-07-18): la versión anterior lanzaba la descarga con
# `asyncio.create_task()` desde un endpoint SÍNCRONO (`def`, que FastAPI ejecuta
# en el threadpool, sin event loop). Eso lanzaba `RuntimeError: no running event
# loop` DESPUÉS de haber creado la entrada del job — de ahí los dos síntomas que
# reportó el usuario: la barra aparecía clavada en 0% (el job existía pero nadie
# lo ejecutaba) y "Cancelar" no hacía nada (no había proceso que matar). Es el
# mismo patrón `def` vs `async def` que ya mordió en WPMS W4. Ahora los endpoints
# son `async def` y la descarga corre en un subproceso real.
from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any, Optional

from app.core.logging_config import get_system_logger
from app.ai.local_catalog import find_model

logger = get_system_logger("ai.local_installer")

# {tag: {status, percent, downloaded, total, step, error, _proc}}
_JOBS: dict[str, dict[str, Any]] = {}

# La barra de Ollama emite códigos ANSI y se refresca con \r. Se limpian para
# quedarse con el texto plano de la última línea de progreso.
_ANSI = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]|\x1B\][^\x07]*\x07|\x1B[<-?]")
# "pulling a3de86cd:  42% ▕███  ▏ 2.2 GB/5.2 GB  12 MB/s  4m2s"
_PCT = re.compile(r"(\d{1,3})\s*%")
_SIZES = re.compile(r"([\d.]+\s*[KMGT]?B)\s*/\s*([\d.]+\s*[KMGT]?B)")
_STEP = re.compile(r"(pulling manifest|verifying|writing manifest|success|pulling\s+\S+)")


def _ollama_cli() -> Optional[str]:
    import shutil
    return shutil.which("ollama")


def status(tag: str) -> Optional[dict]:
    """Progreso de una instalación (o None si nunca se lanzó para ese tag)."""
    job = _JOBS.get(tag)
    if not job:
        return None
    return {k: v for k, v in job.items() if not k.startswith("_")}


def all_jobs() -> dict[str, dict]:
    return {tag: status(tag) for tag in _JOBS}


async def start(tag: str) -> dict:
    """Lanza `ollama pull <tag>` en segundo plano. Idempotente: si ya está
    descargando, devuelve el estado actual sin duplicar el proceso."""
    job = _JOBS.get(tag)
    if job and job.get("status") == "downloading":
        return status(tag)

    cli = _ollama_cli()
    if not cli:
        _JOBS[tag] = {"tag": tag, "status": "failed", "percent": 0.0,
                      "downloaded": None, "total": None, "step": None,
                      "error": "El comando `ollama` no está instalado o no está en el PATH."}
        return status(tag)

    _JOBS[tag] = {"tag": tag, "status": "downloading", "percent": 0.0,
                  "downloaded": None, "total": None, "step": "iniciando…", "error": None}
    # Se lanza aquí (endpoint async -> hay event loop) y se deja corriendo: una
    # descarga de 5-21 GB no cabe en el ciclo de vida de una petición HTTP.
    asyncio.create_task(_pull(tag, cli))
    return status(tag)


async def cancel(tag: str) -> bool:
    """Cancela matando el proceso. Ollama conserva lo ya descargado en su caché,
    así que reintentar más tarde REANUDA en vez de empezar de cero."""
    job = _JOBS.get(tag)
    if not job or job.get("status") != "downloading":
        return False
    proc = job.get("_proc")
    if proc is not None and proc.returncode is None:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
    job["status"] = "cancelled"
    job["step"] = "cancelado"
    return True


async def _pull(tag: str, cli: str) -> None:
    job = _JOBS[tag]
    try:
        proc = await asyncio.create_subprocess_exec(
            cli, "pull", tag,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,   # la barra sale por stderr
        )
        job["_proc"] = proc

        buf = ""
        while True:
            chunk = await proc.stdout.read(2048)
            if not chunk:
                break
            buf += chunk.decode("utf-8", errors="replace")
            # La barra se refresca con \r; nos quedamos con el último tramo.
            parts = re.split(r"[\r\n]", buf)
            buf = parts[-1] if len(parts) > 1 else buf
            for raw in parts[:-1] or [buf]:
                _apply_progress(job, raw)
            if len(buf) > 4096:      # nunca crecer sin límite
                buf = buf[-1024:]

        await proc.wait()
        if job["status"] == "cancelled":
            return
        if proc.returncode == 0:
            job["percent"] = 100.0
            job["status"] = "done"
            job["step"] = "instalado"
            _register_installed(tag)
            logger.info(f"[local_installer] modelo instalado: {tag}")
        else:
            job["status"] = "failed"
            job["error"] = job.get("_last_line") or f"`ollama pull` terminó con código {proc.returncode}"
    except asyncio.CancelledError:
        job["status"] = "cancelled"
    except Exception as e:
        job["status"] = "failed"
        job["error"] = f"{type(e).__name__}: {e}"
        logger.error(f"[local_installer] fallo instalando {tag}: {e}")
    finally:
        job.pop("_proc", None)


def _apply_progress(job: dict, raw: str) -> None:
    """Traduce una línea de la barra de Ollama a estado consultable."""
    line = _ANSI.sub("", raw).strip()
    if not line:
        return
    job["_last_line"] = line[:300]

    step = _STEP.search(line)
    if step:
        job["step"] = step.group(1)

    sizes = _SIZES.search(line)
    if sizes:
        job["downloaded"], job["total"] = sizes.group(1).strip(), sizes.group(2).strip()

    pct = _PCT.search(line)
    if pct:
        value = int(pct.group(1))
        if 0 <= value <= 100:
            # La barra puede reiniciarse por capa; nos quedamos con el máximo
            # visto para que el porcentaje no retroceda en pantalla.
            job["percent"] = float(max(value, int(job.get("percent") or 0)))


def _register_installed(tag: str) -> None:
    """Alta en `local_models` → a partir de aquí el MEL lo ve como candidato."""
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
    """Modelos realmente presentes (fuente de verdad del disco), vía `ollama list`."""
    cli = _ollama_cli()
    if not cli:
        return set()
    try:
        proc = await asyncio.create_subprocess_exec(
            cli, "list", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        tags: set[str] = set()
        for line in out.decode("utf-8", errors="replace").splitlines()[1:]:  # salta cabecera
            name = line.split()[0] if line.split() else ""
            if name:
                tags.add(name)
                # `ollama list` muestra "modelo:latest"; el catálogo puede pedir
                # "modelo" a secas — se registran ambas formas.
                if name.endswith(":latest"):
                    tags.add(name[: -len(":latest")])
        return tags
    except Exception:
        return set()


async def runtime_alive() -> bool:
    """¿Está Ollama operativo? Se pregunta al propio CLI (misma vía que todo lo
    demás), no por HTTP."""
    cli = _ollama_cli()
    if not cli:
        return False
    try:
        proc = await asyncio.create_subprocess_exec(
            cli, "list", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=10)
        return proc.returncode == 0
    except Exception:
        return False
