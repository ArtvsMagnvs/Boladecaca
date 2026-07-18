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

    runtime_ok = bool(installed) or await _ollama_alive()

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


async def _ollama_alive() -> bool:
    import httpx
    from app.core.config import settings
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


class TagBody(BaseModel):
    tag: str


@router.post("/install")
def install_model(body: TagBody):
    """Lanza la descarga en segundo plano (idempotente). Devuelve el progreso
    inicial; la UI hace polling a /install/status."""
    return local_installer.start(body.tag)


@router.get("/install/status")
def install_status(tag: str):
    st = local_installer.status(tag)
    if st is None:
        raise HTTPException(status_code=404, detail=f"sin instalación registrada para {tag}")
    return st


@router.post("/install/cancel")
def install_cancel(body: TagBody):
    if not local_installer.cancel(body.tag):
        raise HTTPException(status_code=400, detail="no hay una descarga en curso para ese modelo")
    return {"cancelled": True}


class EnableBody(BaseModel):
    tag: str
    enabled: bool


@router.post("/enable")
def set_enabled(body: EnableBody):
    """Activa/desactiva un modelo YA instalado en el enrutado del MEL (sin
    borrar los GB del disco)."""
    db = SessionLocal()
    try:
        row = db.query(LocalModel).filter(LocalModel.model_tag == body.tag).first()
        if not row:
            raise HTTPException(status_code=404, detail=f"modelo no instalado: {body.tag}")
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
