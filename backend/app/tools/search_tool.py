# backend/app/tools/search_tool.py
#
# V1.0/1.1 (Tools): busqueda web real (no navegador -- eso es Browser Tool).
# Dos proveedores combinables (peticion del usuario, 2026-07-18): SerpAPI
# (resultados de Google reales; plan free SIN tarjeta, 250 consultas/mes) se
# prueba PRIMERO, y Brave Search API (su plan free exige vincular tarjeta,
# 1000 consultas/mes) queda como respaldo si SerpAPI falla o no esta
# configurado — orden decidido por el usuario (2026-07-22): la cuota de Brave
# es mayor pero esta atada a una tarjeta, mejor reservarla de red de
# seguridad. El usuario configura una o ambas API keys en Ajustes ->
# Busqueda web (endpoints en app/api/endpoints/search_config.py); las keys se
# leen cifradas de la tabla Config, igual que el token de Telegram.
#
# Acciones: search_web, search_news, search_images, search_videos.

from typing import Dict, Any, List, Optional

import httpx

from .base import BaseTool
from app.core import secrets as secrets_module

_KEY_BRAVE = "search_brave_api_key"
_KEY_SERPAPI = "search_serpapi_api_key"

# Ruta de cada vertical por proveedor (doc de la tool, 2026-07-18).
_BRAVE_PATHS = {
    "web": "/res/v1/web/search",
    "news": "/res/v1/news/search",
    "images": "/res/v1/images/search",
    "videos": "/res/v1/videos/search",
}
_SERPAPI_TBM = {"web": None, "news": "nws", "images": "isch", "videos": "vid"}


def _get_key(db, config_key: str) -> Optional[str]:
    from app.db.models import Config
    row = db.query(Config).filter(Config.key == config_key).first()
    if not row or not row.value:
        return None
    try:
        return secrets_module.decrypt(row.value)
    except Exception:
        return None


def _configured_providers() -> Dict[str, Optional[str]]:
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        return {"brave": _get_key(db, _KEY_BRAVE), "serpapi": _get_key(db, _KEY_SERPAPI)}
    finally:
        db.close()


async def _search_brave(vertical: str, query: str, count: int, api_key: str) -> List[Dict[str, Any]]:
    path = _BRAVE_PATHS[vertical]
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(
            f"https://api.search.brave.com{path}",
            params={"q": query, "count": count},
            headers={"Accept": "application/json", "X-Subscription-Token": api_key},
        )
        r.raise_for_status()
        data = r.json()

    # La forma de la respuesta varia por vertical -- normalizamos a
    # {title, url, description} para que el caller no tenga que saber de
    # que proveedor vino.
    key_by_vertical = {"web": "web", "news": "results", "images": "results", "videos": "results"}
    bucket = data.get(key_by_vertical.get(vertical, "web"), {})
    items = bucket.get("results", bucket) if isinstance(bucket, dict) else bucket
    out = []
    for it in (items or [])[:count]:
        out.append({
            "title": it.get("title"),
            "url": it.get("url") or it.get("source"),
            "description": it.get("description") or it.get("snippet") or "",
        })
    return out


async def _search_serpapi(vertical: str, query: str, count: int, api_key: str) -> List[Dict[str, Any]]:
    params = {"engine": "google", "q": query, "api_key": api_key, "num": count}
    tbm = _SERPAPI_TBM.get(vertical)
    if tbm:
        params["tbm"] = tbm

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get("https://serpapi.com/search", params=params)
        r.raise_for_status()
        data = r.json()

    if "error" in data:
        raise RuntimeError(data["error"])

    key_by_vertical = {
        "web": "organic_results", "news": "news_results",
        "images": "images_results", "videos": "video_results",
    }
    items = data.get(key_by_vertical.get(vertical, "organic_results"), [])
    out = []
    for it in (items or [])[:count]:
        out.append({
            "title": it.get("title"),
            "url": it.get("link") or it.get("original") or it.get("source"),
            "description": it.get("snippet") or "",
        })
    return out


async def _search(vertical: str, query: str, count: int) -> Dict[str, Any]:
    keys = _configured_providers()
    if not keys["brave"] and not keys["serpapi"]:
        return {
            "success": False, "result": None,
            "error": (
                "no hay ningun proveedor de busqueda configurado. Ve a Ajustes -> "
                "Busqueda web y anade una API key (Brave o SerpAPI)."
            ),
        }

    errors = []
    # SerpAPI primero (free sin tarjeta); Brave como respaldo (free con
    # tarjeta vinculada) — orden del usuario, 2026-07-22.
    if keys["serpapi"]:
        try:
            items = await _search_serpapi(vertical, query, count, keys["serpapi"])
            return {"success": True, "result": {"provider": "serpapi", "query": query, "items": items}, "error": None}
        except Exception as e:
            errors.append(f"serpapi: {type(e).__name__}: {e}")
    if keys["brave"]:
        try:
            items = await _search_brave(vertical, query, count, keys["brave"])
            return {"success": True, "result": {"provider": "brave", "query": query, "items": items}, "error": None}
        except Exception as e:
            errors.append(f"brave: {type(e).__name__}: {e}")

    return {"success": False, "result": None, "error": "todos los proveedores fallaron: " + " | ".join(errors)}


class SearchTool(BaseTool):
    tool_id = "search"
    name = "Search Tool"
    description = (
        "Busqueda web real (no navegador): web, noticias, imagenes, videos. "
        "Usa SerpAPI (Google) primero; si falla o no esta configurada, cae a "
        "Brave Search API. Requiere al menos una API key en Ajustes."
    )
    requires_confirmation = False

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            vertical_by_action = {
                "search_web": "web", "search_news": "news",
                "search_images": "images", "search_videos": "videos",
            }
            vertical = vertical_by_action.get(action)
            if not vertical:
                return {
                    "success": False, "result": None,
                    "error": f"Accion desconocida: {action}. Disponibles: {', '.join(vertical_by_action)}",
                }
            query = (params.get("query") or "").strip()
            if not query:
                return {"success": False, "result": None, "error": "falta parametro: query"}
            count = int(params.get("count", 8))
            count = max(1, min(count, 20))
            return await _search(vertical, query, count)
        except Exception as e:
            return {"success": False, "result": None, "error": f"{type(e).__name__}: {e}"}

    def list_actions(self) -> List[Dict[str, Any]]:
        common_params = {"query": "string", "count": "int opcional (default 8, max 20)"}
        return [
            {"id": "search_web", "description": "Busqueda web general.", "requires_confirmation": False, "params": common_params},
            {"id": "search_news", "description": "Busqueda de noticias.", "requires_confirmation": False, "params": common_params},
            {"id": "search_images", "description": "Busqueda de imagenes.", "requires_confirmation": False, "params": common_params},
            {"id": "search_videos", "description": "Busqueda de videos.", "requires_confirmation": False, "params": common_params},
        ]
