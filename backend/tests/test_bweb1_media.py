# tests/test_bweb1_media.py — B·WEB-1 (doc 32): abrir medios/URL en el
# navegador REAL por defecto del usuario, sin pasar por Playwright.
#
# Ninguno de estos tests toca Playwright ni abre un navegador de verdad: se
# mockea SOLO la frontera del sistema (`_launch_default_browser`, que envuelve
# `webbrowser.open`) y la frontera de red (`browser_tool._search`, importado
# de `search_tool` -- se monkeypatchea en `browser_tool`, no en `search_tool`,
# porque `from .search_tool import _search` copia la referencia al importar).
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.tools import browser_tool
from app.tools.tool_manager import tool_manager


# ---------------------------------------------------------------------------
# _launch_default_browser (el propio wrapper de webbrowser.open)
# ---------------------------------------------------------------------------
def test_launch_default_browser_delega_en_webbrowser_open(monkeypatch):
    llamado = {}

    def _fake_open(url):
        llamado["url"] = url
        return True

    monkeypatch.setattr(browser_tool.webbrowser, "open", _fake_open)
    assert browser_tool._launch_default_browser("https://example.com") is True
    assert llamado["url"] == "https://example.com"


def test_launch_default_browser_propaga_false(monkeypatch):
    monkeypatch.setattr(browser_tool.webbrowser, "open", lambda url: False)
    assert browser_tool._launch_default_browser("https://example.com") is False


# ---------------------------------------------------------------------------
# open_in_default_browser
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_open_in_default_browser_sin_url_falla_claro():
    r = await tool_manager.execute("browser", "open_in_default_browser", {})
    assert not r["success"]
    assert "url" in r["error"]


@pytest.mark.anyio
async def test_open_in_default_browser_completa_esquema_y_abre(monkeypatch):
    llamadas = []

    def _fake_launch(url):
        llamadas.append(url)
        return True

    # `_launch_default_browser` es sincrona (envuelve `webbrowser.open`) y el
    # handler la despacha via `asyncio.to_thread` -- monkeypatchear la propia
    # funcion (no `asyncio.to_thread`) ejercita ese despacho real sin
    # depender de threads de verdad en CI.
    monkeypatch.setattr(browser_tool, "_launch_default_browser", _fake_launch)

    r = await tool_manager.execute(
        "browser", "open_in_default_browser", {"url": "youtube.com/watch?v=1"}
    )
    assert r["success"], r
    assert r["result"]["url"] == "https://youtube.com/watch?v=1"
    assert llamadas == ["https://youtube.com/watch?v=1"]


@pytest.mark.anyio
async def test_open_in_default_browser_respeta_https_ya_presente(monkeypatch):
    monkeypatch.setattr(
        browser_tool, "_launch_default_browser", lambda url: True
    )
    r = await tool_manager.execute(
        "browser", "open_in_default_browser", {"url": "http://example.com"}
    )
    assert r["success"]
    assert r["result"]["url"] == "http://example.com"   # no se le mete https:// encima


@pytest.mark.anyio
async def test_open_in_default_browser_lanzador_devuelve_false(monkeypatch):
    monkeypatch.setattr(browser_tool, "_launch_default_browser", lambda url: False)
    r = await tool_manager.execute(
        "browser", "open_in_default_browser", {"url": "https://example.com"}
    )
    assert not r["success"]
    assert "example.com" in r["error"]


@pytest.mark.anyio
async def test_open_in_default_browser_excepcion_del_lanzador_no_rompe(monkeypatch):
    def _boom(url):
        raise OSError("no hay navegador registrado")

    monkeypatch.setattr(browser_tool, "_launch_default_browser", _boom)
    r = await tool_manager.execute(
        "browser", "open_in_default_browser", {"url": "https://example.com"}
    )
    assert not r["success"]
    assert "OSError" in r["error"]


@pytest.mark.anyio
async def test_open_in_default_browser_nunca_toca_playwright(monkeypatch):
    """Confirma que esta accion es de verdad un atajo fuera de Playwright:
    ninguna sesion/pestana nueva se crea (a diferencia de open_url) -- se
    compara el estado ANTES/DESPUES en vez de asumir que empieza vacio, para
    no depender del orden de ejecucion con otros tests del archivo hermano."""
    monkeypatch.setattr(browser_tool, "_launch_default_browser", lambda url: True)
    antes = dict(browser_tool._sessions)
    r = await tool_manager.execute(
        "browser", "open_in_default_browser", {"url": "https://example.com"}
    )
    assert r["success"]
    assert browser_tool._sessions == antes   # ni una sesion/pestana nueva


# ---------------------------------------------------------------------------
# play_media
# ---------------------------------------------------------------------------
def _search_result(items):
    return {"success": True, "result": {"provider": "brave", "query": "q", "items": items}, "error": None}


@pytest.mark.anyio
async def test_play_media_sin_query_falla_claro():
    r = await tool_manager.execute("browser", "play_media", {})
    assert not r["success"]
    assert "query" in r["error"]


@pytest.mark.anyio
async def test_play_media_resuelve_via_search_y_abre_en_navegador_real(monkeypatch):
    fake_search = AsyncMock(return_value=_search_result([
        {"title": "Bohemian Rhapsody", "url": "https://youtube.com/watch?v=fJ9rUzIMcZQ"},
    ]))
    monkeypatch.setattr(browser_tool, "_search", fake_search)
    monkeypatch.setattr(browser_tool, "_launch_default_browser", lambda url: True)

    r = await tool_manager.execute("browser", "play_media", {"query": "bohemian rhapsody"})

    assert r["success"], r
    assert r["result"]["url"] == "https://youtube.com/watch?v=fJ9rUzIMcZQ"
    assert r["result"]["title"] == "Bohemian Rhapsody"
    assert r["result"]["query"] == "bohemian rhapsody"
    # vertical "videos" -- una cancion/video es lo que se busca por defecto
    fake_search.assert_awaited_once_with("videos", "bohemian rhapsody", 5)


@pytest.mark.anyio
async def test_play_media_nunca_llama_a_google_search(monkeypatch):
    """La regla explicita de B·WEB-1: jamas via browser.google_search."""
    fake_search = AsyncMock(return_value=_search_result([{"title": "x", "url": "https://x.com"}]))
    monkeypatch.setattr(browser_tool, "_search", fake_search)
    monkeypatch.setattr(browser_tool, "_launch_default_browser", lambda url: True)

    tool = browser_tool.BrowserTool()
    google_search_llamado = {"veces": 0}

    async def _boom(params):
        google_search_llamado["veces"] += 1
        return {"success": False, "result": None, "error": "no deberia llamarse"}

    tool._google_search = _boom  # type: ignore[method-assign]
    r = await tool.execute("play_media", {"query": "algo"})
    assert r["success"]
    assert google_search_llamado["veces"] == 0


@pytest.mark.anyio
async def test_play_media_la_busqueda_falla_propaga_el_motivo_real(monkeypatch):
    fake_search = AsyncMock(return_value={
        "success": False, "result": None,
        "error": "no hay ningun proveedor de busqueda configurado. Ve a Ajustes -> "
                 "Busqueda web y anade una API key (Brave o SerpAPI).",
    })
    monkeypatch.setattr(browser_tool, "_search", fake_search)

    r = await tool_manager.execute("browser", "play_media", {"query": "algo"})
    assert not r["success"]
    assert "proveedor de busqueda" in r["error"]


@pytest.mark.anyio
async def test_play_media_sin_resultados_es_honesto(monkeypatch):
    fake_search = AsyncMock(return_value=_search_result([]))
    monkeypatch.setattr(browser_tool, "_search", fake_search)

    r = await tool_manager.execute("browser", "play_media", {"query": "algo muy raro"})
    assert not r["success"]
    assert "algo muy raro" in r["error"]


@pytest.mark.anyio
async def test_play_media_salta_items_sin_url_hasta_encontrar_uno(monkeypatch):
    fake_search = AsyncMock(return_value=_search_result([
        {"title": "sin url", "url": None},
        {"title": "con url", "url": "https://youtube.com/watch?v=2"},
    ]))
    monkeypatch.setattr(browser_tool, "_search", fake_search)
    monkeypatch.setattr(browser_tool, "_launch_default_browser", lambda url: True)

    r = await tool_manager.execute("browser", "play_media", {"query": "algo"})
    assert r["success"]
    assert r["result"]["url"] == "https://youtube.com/watch?v=2"


@pytest.mark.anyio
async def test_play_media_el_navegador_falla_al_abrir_se_reporta(monkeypatch):
    fake_search = AsyncMock(return_value=_search_result([
        {"title": "x", "url": "https://youtube.com/watch?v=1"},
    ]))
    monkeypatch.setattr(browser_tool, "_search", fake_search)
    monkeypatch.setattr(browser_tool, "_launch_default_browser", lambda url: False)

    r = await tool_manager.execute("browser", "play_media", {"query": "algo"})
    assert not r["success"]
    assert "youtube.com" in r["error"]


# ---------------------------------------------------------------------------
# Catálogo y permisos — sin confirmación adicional, cae bajo browser.use
# ---------------------------------------------------------------------------
def test_list_actions_incluye_las_dos_nuevas_sin_confirmacion():
    acciones = {a["id"]: a for a in browser_tool.BrowserTool().list_actions()}
    assert "open_in_default_browser" in acciones
    assert "play_media" in acciones
    assert acciones["open_in_default_browser"]["requires_confirmation"] is False
    assert acciones["play_media"]["requires_confirmation"] is False


def test_execute_accion_desconocida_lista_las_dos_nuevas():
    import asyncio as _asyncio

    r = _asyncio.run(browser_tool.BrowserTool().execute("no-existe", {}))
    assert not r["success"]
    assert "open_in_default_browser" in r["error"]
    assert "play_media" in r["error"]


def test_tie_catalog_no_pide_aprobacion_para_las_acciones_nuevas():
    from app.tie.toolloop import build_catalog

    catalogo = build_catalog(["browser"], tool_manager)
    por_id = {e["action"]: e for e in catalogo if e["tool_id"] == "browser"}
    assert "open_in_default_browser" in por_id
    assert "play_media" in por_id
    assert por_id["open_in_default_browser"]["needs_approval"] is False
    assert por_id["play_media"]["needs_approval"] is False


def test_permiso_de_las_acciones_nuevas_es_browser_use():
    from app.automation.permissions import permission_for_tool_action

    assert permission_for_tool_action("browser", "open_in_default_browser") == "browser.use"
    assert permission_for_tool_action("browser", "play_media") == "browser.use"


def test_toolloop_prompt_prefiere_navegador_real_para_medios():
    from app.tie.toolloop import _SYSTEM_PROMPT

    assert "play_media" in _SYSTEM_PROMPT
    assert "open_in_default_browser" in _SYSTEM_PROMPT
