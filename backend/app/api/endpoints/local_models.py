# app/api/endpoints/local_models.py — modelos locales especializados (V1.0)
#
# El catálogo por categorías (Runtime/General/Coding/Reasoning/Vision), la
# instalación de 1 clic con progreso real, y el interruptor que decide qué
# modelos participan en el enrutado del MEL.
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ai import local_installer
from app.ai.local_catalog import CATEGORIES, LOCAL_CATALOG
from app.db.database import SessionLocal
from app.db.models import LocalModel

router = APIRouter(prefix="/local-models", tags=["local-models"])


@router.get("/hardware")
async def hardware_recommendation():
    """[2026-07-21] Escanea el PC (CPU/RAM/GPU) y recomienda AUTOMÁTICAMENTE el
    modelo de Ollama óptimo (+ uno inferior seguro y uno superior solo si el
    equipo lo aguanta) y el nivel de partículas del AVCS. Lo usa la config
    inicial (auto) y Ajustes. Fail-soft: nunca rompe, degrada a lo que sabe."""
    import asyncio

    from app.core import hardware

    # scan/nvidia-smi son bloqueantes → a un hilo, para no atascar el loop.
    return await asyncio.to_thread(hardware.full_recommendation)


@router.get("/catalog")
async def get_catalog():
    """Catálogo completo + qué está instalado de verdad (cruzado con Ollama) +
    progreso de las descargas en curso. Una sola llamada para pintar la
    pantalla entera."""
    installed = await local_installer.installed_tags()
    jobs = local_installer.all_jobs()

    db = SessionLocal()
    try:
        enabled_map = {r.model_tag: r.enabled for r in db.query(LocalModel).all()}
    except Exception:
        enabled_map = {}
    finally:
        db.close()

    runtime_ok = bool(installed) or await local_installer.runtime_alive()

    families = []
    for family, fam in LOCAL_CATALOG.items():
        models = []
        for m in fam.get("models", []):
            tag = m["tag"]
            models.append({
                **m,
                "installed": tag in installed,
                "enabled": enabled_map.get(tag, False),
                "job": jobs.get(tag),
            })
        families.append({
            "family": family,
            "label": fam["label"],
            "category": fam["category"],
            "description": fam["description"],
            "is_runtime": fam.get("is_runtime", False),
            "install_url": fam.get("install_url"),
            "models": models,
        })

    return {
        "categories": [{"id": c, "label": l, "description": d} for c, l, d in CATEGORIES],
        "families": families,
        "runtime_ok": runtime_ok,
    }


@router.get("/runtime")
async def runtime_status():
    """[OB-2, doc 30 §1] ¿Está Ollama instalado y operativo? Chequeo LIGERO
    (no descarga el catálogo entero) para el onboarding: si no está, la UI
    ofrece el enlace de descarga y un botón de reintento. `install_url` sale
    del catálogo (la familia runtime), no hardcodeado aquí."""
    ok = await local_installer.runtime_alive()
    install_url = None
    for fam in LOCAL_CATALOG.values():
        if fam.get("is_runtime"):
            install_url = fam.get("install_url")
            break
    return {"ok": ok, "install_url": install_url}


class TagBody(BaseModel):
    tag: str


@router.post("/install")
async def install_model(body: TagBody):
    """Lanza la descarga en segundo plano (idempotente). Devuelve el progreso
    inicial; la UI hace polling a /install/status.

    `async def` NO es decorativo: la descarga se lanza con `asyncio.create_task`,
    que exige un event loop corriendo. Con `def`, FastAPI ejecuta esto en el
    threadpool (sin loop) y la tarea nunca arrancaba — ese era exactamente el
    bug de la barra clavada en 0%."""
    return await local_installer.start(body.tag)


@router.get("/install/status")
def install_status(tag: str):
    st = local_installer.status(tag)
    if st is None:
        raise HTTPException(status_code=404, detail=f"sin instalación registrada para {tag}")
    return st


@router.post("/install/cancel")
async def install_cancel(body: TagBody):
    if not await local_installer.cancel(body.tag):
        raise HTTPException(status_code=400, detail="no hay una descarga en curso para ese modelo")
    return {"cancelled": True}


class EnableBody(BaseModel):
    tag: str
    enabled: bool


@router.post("/enable")
async def set_enabled(body: EnableBody):
    """Activa/desactiva un modelo YA instalado en el enrutado del MEL (sin
    borrar los GB del disco).

    FIX (2026-07-21, bug real del usuario con qwen3:14b): la fila de
    `local_models` solo la creaba el instalador de Aithera AL TERMINAR una
    descarga. Si el modelo llegó a Ollama por cualquier otra vía (pull manual,
    backend reiniciado a media descarga y Ollama reanudando solo, fallo del
    alta), la UI decía "instalado" (verdad del disco vía `ollama list`) pero
    este endpoint respondía 404 "modelo no instalado". El DISCO es la fuente
    de verdad: si Ollama lo tiene, se da de alta aquí mismo (self-heal) en vez
    de negar lo evidente. `async def` porque consulta a Ollama."""
    from datetime import datetime

    from app.ai.local_catalog import find_model

    db = SessionLocal()
    try:
        row = db.query(LocalModel).filter(LocalModel.model_tag == body.tag).first()
        if not row:
            installed = await local_installer.installed_tags()
            if body.tag not in installed:
                raise HTTPException(status_code=404, detail=f"modelo no instalado: {body.tag}")
            meta = find_model(body.tag) or {}
            row = LocalModel(
                family=meta.get("family") or "otros",
                model_tag=body.tag,
                label=meta.get("label") or body.tag,
                size_gb=meta.get("size_gb"),
                enabled=body.enabled,
                installed_at=datetime.utcnow(),
            )
            db.add(row)
        row.enabled = body.enabled
        db.commit()
        return {"tag": body.tag, "enabled": body.enabled}
    finally:
        db.close()


@router.delete("/{tag:path}")
async def delete_model(tag: str):
    """Elimina el modelo de Ollama (libera disco) y lo da de baja del enrutado."""
    import httpx
    from app.core.config import settings

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.request("DELETE", f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/delete",
                                     json={"model": tag})
        if r.status_code not in (200, 404):
            raise HTTPException(status_code=502, detail=f"Ollama devolvió {r.status_code}: {r.text[:200]}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"no se pudo borrar en Ollama: {e}")

    db = SessionLocal()
    try:
        db.query(LocalModel).filter(LocalModel.model_tag == tag).delete()
        db.commit()
    finally:
        db.close()
    return {"tag": tag, "deleted": True}
