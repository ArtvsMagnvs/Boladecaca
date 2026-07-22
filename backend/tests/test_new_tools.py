# tests/test_new_tools.py — Process/Secrets/Memory/Model/Download tools
#
# Las 5 tools nuevas que capacitan al Orchestrator (petición directa del
# usuario, 2026-07-18). Registro real en ToolManager + logica real de cada
# tool; se mockean SOLO las fronteras externas no deterministas en CI
# (subprocess de programas reales, Ollama/httpx de red) -- psutil y la BD
# real (Config/MOS) se ejercitan tal cual, igual que el resto de la suite.
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tools.tool_manager import tool_manager


def test_las_5_tools_nuevas_registradas():
    ids = {t["tool_id"] for t in tool_manager.list_tools()}
    assert {"process", "secrets", "memory", "model", "download"} <= ids


def test_search_tool_registrada():
    ids = {t["tool_id"] for t in tool_manager.list_tools()}
    assert "search" in ids


# ---------------------------------------------------------------------------
# Process Tool
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_process_list_cpu_ram_reales():
    r = await tool_manager.execute("process", "list_processes", {"limit": 3})
    assert r["success"] and r["result"]["count"] <= 3

    r = await tool_manager.execute("process", "cpu_status", {})
    assert r["success"] and "percent_total" in r["result"]

    r = await tool_manager.execute("process", "ram_status", {})
    assert r["success"] and r["result"]["total_mb"] > 0


@pytest.mark.anyio
async def test_process_open_program_fuera_de_whitelist_rechazado():
    r = await tool_manager.execute("process", "open_program", {"name": "cualquier_cosa"})
    assert not r["success"]
    assert "whitelist" in r["error"]


@pytest.mark.anyio
async def test_process_close_program_protege_el_propio_backend():
    import os
    r = await tool_manager.execute("process", "close_program", {"pid": os.getpid()})
    assert not r["success"]
    assert "propio proceso" in r["error"]


@pytest.mark.anyio
async def test_process_close_program_protege_procesos_del_sistema(monkeypatch):
    from app.tools import process_tool

    fake_proc = MagicMock()
    fake_proc.name.return_value = "svchost.exe"
    monkeypatch.setattr(process_tool.psutil, "Process", lambda pid: fake_proc)

    r = await tool_manager.execute("process", "close_program", {"pid": 999999})
    assert not r["success"]
    assert "protegido" in r["error"]
    fake_proc.terminate.assert_not_called()


# ---------------------------------------------------------------------------
# Secrets Tool
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_secrets_ciclo_completo_y_nunca_expone_en_list():
    await tool_manager.execute("secrets", "delete_secret", {"name": "_test_secret_ciclo"})  # limpieza previa

    r = await tool_manager.execute("secrets", "set_secret", {"name": "_test_secret_ciclo", "value": "valor-secreto-xyz"})
    assert r["success"]

    r = await tool_manager.execute("secrets", "get_secret", {"name": "_test_secret_ciclo"})
    assert r["success"] and r["result"]["value"] == "valor-secreto-xyz"

    r = await tool_manager.execute("secrets", "list_secrets", {})
    assert r["success"]
    entry = next((s for s in r["result"]["secrets"] if s["name"] == "_test_secret_ciclo"), None)
    assert entry is not None
    assert "valor-secreto-xyz" not in entry["value_preview"]

    r = await tool_manager.execute("secrets", "delete_secret", {"name": "_test_secret_ciclo"})
    assert r["success"]

    r = await tool_manager.execute("secrets", "get_secret", {"name": "_test_secret_ciclo"})
    assert not r["success"]


@pytest.mark.anyio
async def test_secrets_set_secret_esta_cifrado_en_bd():
    from app.db.database import SessionLocal
    from app.db.models import Config

    await tool_manager.execute("secrets", "set_secret", {"name": "_test_cifrado", "value": "texto-plano-original"})
    db = SessionLocal()
    try:
        row = db.query(Config).filter(Config.key == "secret:_test_cifrado").first()
        assert row is not None
        assert row.value != "texto-plano-original"  # NUNCA en texto plano en la BD
        assert row.value.startswith(("dpapi:", "plain:"))
    finally:
        db.close()
    await tool_manager.execute("secrets", "delete_secret", {"name": "_test_cifrado"})


# ---------------------------------------------------------------------------
# Memory Tool
# ---------------------------------------------------------------------------
pytestmark_memory = pytest.mark.skipif(
    __import__("app.memory", fromlist=["memory_router"]).memory_router.healthy is False,
    reason="ChromaDB no disponible en el entorno de test",
)


@pytest.mark.anyio
async def test_memory_ciclo_completo_save_search_update_delete():
    from app.memory import memory_router

    if not memory_router.healthy:
        pytest.skip("ChromaDB no disponible")

    r = await tool_manager.execute("memory", "save_memory", {
        "content": "test_new_tools: contenido original",
        "memory_type": "personal", "source": "_test_memtool_", "dedup_key": "_test_memtool_key",
    })
    assert r["success"]
    item_id = r["result"]["id"]
    assert item_id == "mem_personal:_test_memtool_key"

    r = await tool_manager.execute("memory", "search_memory", {
        "query": "test_new_tools contenido original", "memory_types": ["personal"], "top_k": 5,
    })
    assert r["success"]
    assert any(it["id"] == item_id for it in r["result"]["items"])

    r = await tool_manager.execute("memory", "update_memory", {"item_id": item_id, "content": "test_new_tools: contenido actualizado"})
    assert r["success"]

    r = await tool_manager.execute("memory", "delete_memory", {
        "memory_type": "personal", "filters": {"source": "_test_memtool_"},
    })
    assert r["success"] and r["result"]["deleted_count"] >= 1


@pytest.mark.anyio
async def test_memory_type_invalido_rechazado():
    r = await tool_manager.execute("memory", "save_memory", {
        "content": "x", "memory_type": "tipo_que_no_existe", "source": "test",
    })
    assert not r["success"]
    assert "memory_type invalido" in r["error"]


# ---------------------------------------------------------------------------
# Model Tool (Ollama mockeado -- no depende de tener Ollama arrancado en CI)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_model_list_models_mock():
    fake_response = MagicMock()
    fake_response.json.return_value = {"models": [{"name": "llama3:latest", "size": 4_000_000_000}]}
    fake_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=fake_response)):
        r = await tool_manager.execute("model", "list_models", {})
    assert r["success"]
    assert r["result"]["models"][0]["name"] == "llama3:latest"


@pytest.mark.anyio
async def test_model_ollama_no_disponible_error_claro():
    with patch("httpx.AsyncClient.get", side_effect=__import__("httpx").ConnectError("boom")):
        r = await tool_manager.execute("model", "list_models", {})
    assert not r["success"]
    assert "Ollama" in r["error"] or "conectar" in r["error"]


@pytest.mark.anyio
async def test_model_gpu_ram_status_real_ram():
    r = await tool_manager.execute("model", "gpu_ram_status", {})
    assert r["success"]
    assert r["result"]["ram"]["total_mb"] > 0


# ---------------------------------------------------------------------------
# Download Tool
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_download_url_no_http_rechazada(tmp_path):
    r = await tool_manager.execute("download", "download_url", {
        "url": "ftp://ejemplo.com/x", "path": str(tmp_path / "x.txt"),
    })
    assert not r["success"]
    assert "http" in r["error"]


@pytest.mark.anyio
async def test_download_status_de_id_inexistente():
    r = await tool_manager.execute("download", "get_download_status", {"download_id": "no-existe"})
    assert not r["success"]


@pytest.mark.anyio
async def test_download_url_fuera_de_home_rechazada():
    r = await tool_manager.execute("download", "download_url", {
        "url": "https://example.com/x", "path": "C:\\Windows\\Temp\\x.txt",
    })
    assert not r["success"]


# ---------------------------------------------------------------------------
# Search Tool (Brave/SerpAPI mockeados -- no gasta cuota real en tests)
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=False)
def _clean_search_config():
    from app.db.database import SessionLocal
    from app.db.models import Config

    def _clean():
        db = SessionLocal()
        try:
            db.query(Config).filter(Config.key.like("search_%")).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()
    _clean()
    yield
    _clean()


@pytest.mark.anyio
async def test_search_sin_proveedores_configurados_error_claro(_clean_search_config):
    r = await tool_manager.execute("search", "search_web", {"query": "aithera"})
    assert not r["success"]
    assert "Ajustes" in r["error"]


@pytest.mark.anyio
async def test_search_con_brave_configurado_usa_brave(_clean_search_config):
    from app.core import secrets
    from app.db.database import SessionLocal
    from app.db.models import Config

    db = SessionLocal()
    db.add(Config(key="search_brave_api_key", value=secrets.encrypt("fake-key")))
    db.commit()
    db.close()

    fake_resp = MagicMock()
    fake_resp.json.return_value = {"web": {"results": [{"title": "T", "url": "https://x.com", "description": "d"}]}}
    fake_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=fake_resp)):
        r = await tool_manager.execute("search", "search_web", {"query": "aithera"})
    assert r["success"]
    assert r["result"]["provider"] == "brave"
    assert r["result"]["items"][0]["title"] == "T"


@pytest.mark.anyio
async def test_search_con_ambos_configurados_usa_serpapi_primero(_clean_search_config):
    """[2026-07-22, orden del usuario] SerpAPI (free sin tarjeta, 250/mes) es
    el PRINCIPAL; Brave (free con tarjeta vinculada, 1000/mes) el respaldo."""
    from app.core import secrets
    from app.db.database import SessionLocal
    from app.db.models import Config

    db = SessionLocal()
    db.add(Config(key="search_brave_api_key", value=secrets.encrypt("fake-brave")))
    db.add(Config(key="search_serpapi_api_key", value=secrets.encrypt("fake-serp")))
    db.commit()
    db.close()

    serp_resp = MagicMock()
    serp_resp.json.return_value = {"organic_results": [{"title": "Serp", "link": "https://y.com", "snippet": "s"}]}
    serp_resp.raise_for_status = MagicMock()

    # Ambos responderían bien: debe elegir SerpAPI sin siquiera tocar Brave.
    urls: list[str] = []

    async def _get(self, url, **kwargs):
        urls.append(url)
        return serp_resp

    with patch("httpx.AsyncClient.get", new=_get):
        r = await tool_manager.execute("search", "search_web", {"query": "aithera"})
    assert r["success"]
    assert r["result"]["provider"] == "serpapi"
    assert all("serpapi" in u for u in urls), f"tocó otro proveedor sin necesidad: {urls}"


@pytest.mark.anyio
async def test_search_falla_serpapi_cae_a_brave(_clean_search_config):
    import httpx as httpx_module
    from app.core import secrets
    from app.db.database import SessionLocal
    from app.db.models import Config

    db = SessionLocal()
    db.add(Config(key="search_brave_api_key", value=secrets.encrypt("fake-brave")))
    db.add(Config(key="search_serpapi_api_key", value=secrets.encrypt("fake-serp")))
    db.commit()
    db.close()

    brave_resp = MagicMock()
    brave_resp.json.return_value = {"web": {"results": [{"title": "Brv", "url": "https://x.com", "description": "d"}]}}
    brave_resp.raise_for_status = MagicMock()

    async def _get(self, url, **kwargs):
        if "serpapi" in url:
            raise httpx_module.ConnectError("serpapi caido")
        return brave_resp

    with patch("httpx.AsyncClient.get", new=_get):
        r = await tool_manager.execute("search", "search_web", {"query": "aithera"})
    assert r["success"]
    assert r["result"]["provider"] == "brave"
    assert r["result"]["items"][0]["title"] == "Brv"


@pytest.mark.anyio
async def test_search_config_endpoints_nunca_exponen_la_key_en_claro(_clean_search_config):
    from app.db.database import SessionLocal
    from app.api.endpoints.search_config import search_configure, ConfigureBody

    db = SessionLocal()
    status = search_configure(ConfigureBody(provider="brave", api_key="super-secreta-123"), db)
    db.close()
    assert status.brave.configured is True
    assert "super-secreta-123" not in status.brave.key_masked


# ---------------------------------------------------------------------------
# Browser Tool (Chromium real via Playwright, contra example.com -- pagina
# estable y publica pensada exactamente para esto, sin credenciales)
# ---------------------------------------------------------------------------
def _playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


pytestmark_browser = pytest.mark.skipif(not _playwright_available(), reason="Playwright no instalado")


@pytest.fixture
async def _close_browser_after():
    yield
    from app.tools import browser_tool
    if browser_tool._browser:
        await browser_tool._browser.close()
        browser_tool._browser = None
    if browser_tool._playwright:
        await browser_tool._playwright.stop()
        browser_tool._playwright = None
    # [S3, F-1] El estado global `_pages`/`_current_tab` se sustituyo por
    # sesiones por mision (`_sessions`): limpiarlas equivale a lo de antes.
    browser_tool._sessions.clear()


@pytest.mark.anyio
@pytest.mark.skipif(not _playwright_available(), reason="Playwright no instalado")
async def test_browser_open_url_get_text_get_html_real(_close_browser_after):
    r = await tool_manager.execute("browser", "open_url", {"url": "https://example.com"})
    assert r["success"] and r["result"]["title"] == "Example Domain"
    tab = r["result"]["tab_id"]

    r2 = await tool_manager.execute("browser", "get_text", {"tab_id": tab})
    assert r2["success"] and "Example Domain" in r2["result"]["text"]

    r3 = await tool_manager.execute("browser", "get_html", {"tab_id": tab})
    assert r3["success"] and "<h1>" in r3["result"]["html"]

    r4 = await tool_manager.execute("browser", "screenshot", {"tab_id": tab})
    assert r4["success"] and len(r4["result"]["image_base64"]) > 100


@pytest.mark.anyio
@pytest.mark.skipif(not _playwright_available(), reason="Playwright no instalado")
async def test_browser_wait_for_element_encuentra_y_falla_limpio(_close_browser_after):
    r = await tool_manager.execute("browser", "open_url", {"url": "https://example.com"})
    tab = r["result"]["tab_id"]

    ok = await tool_manager.execute("browser", "wait_for_element", {"tab_id": tab, "selector": "h1", "timeout_ms": 3000})
    assert ok["success"]

    fail = await tool_manager.execute("browser", "wait_for_element", {"tab_id": tab, "selector": ".no-existe", "timeout_ms": 800})
    assert not fail["success"]


@pytest.mark.anyio
@pytest.mark.skipif(not _playwright_available(), reason="Playwright no instalado")
async def test_browser_new_tab_y_close_tab_reales(_close_browser_after):
    r1 = await tool_manager.execute("browser", "open_url", {"url": "https://example.com"})
    tab1 = r1["result"]["tab_id"]

    r2 = await tool_manager.execute("browser", "new_tab", {"url": "https://example.org"})
    assert r2["success"]
    tab2 = r2["result"]["tab_id"]
    assert tab2 != tab1

    r3 = await tool_manager.execute("browser", "close_tab", {"tab_id": tab2})
    assert r3["success"]

    r4 = await tool_manager.execute("browser", "close_tab", {"tab_id": "no-existe"})
    assert not r4["success"]


@pytest.mark.anyio
@pytest.mark.skipif(not _playwright_available(), reason="Playwright no instalado")
async def test_browser_upload_file_fuera_de_home_rechazado(_close_browser_after):
    r = await tool_manager.execute("browser", "upload_file", {
        "selector": "input[type=file]", "path": "C:\\Windows\\win.ini",
    })
    assert not r["success"]


# ---------------------------------------------------------------------------
# Desktop Tool
#
# Verificado EN VIVO por separado (ver informe): screenshot/ocr/find_text_on_
# screen y click/type/move_mouse funcionan de verdad (confirmado via el titulo
# de una ventana de Notepad real y via el propio texto reconocido por OCR).
# hotkey() en si mismo (el mecanismo de envio de teclas) se probo correcto con
# Ctrl+Z (undo funciono perfectamente) y se reprodujo un comportamiento
# anomalo con Ctrl+A/Ctrl+C EN ESTA MAQUINA CONCRETA con 3 mecanismos de
# inyeccion independientes (pyautogui, la libreria `keyboard`, y SendInput con
# scancodes fisicos) -- descarta un bug de esta tool; algo en el sistema del
# usuario intercepta esas combinaciones especificas. Los tests de aqui abajo
# cubren la LOGICA propia de la tool (validacion, clamping, failsafe) con
# pyautogui mockeado -- no dependen de hardware/hooks de ningun sistema.
# ---------------------------------------------------------------------------
def test_desktop_failsafe_permanece_activo():
    from app.tools import desktop_tool
    desktop_tool._ensure_pyautogui()  # import lazy -- forzarlo antes de leer el flag
    assert desktop_tool.pyautogui.FAILSAFE is True


@pytest.mark.anyio
async def test_desktop_screenshot_real():
    r = await tool_manager.execute("desktop", "screenshot", {})
    assert r["success"]
    assert r["result"]["width"] > 0 and r["result"]["height"] > 0
    assert len(r["result"]["image_base64"]) > 100


@pytest.mark.anyio
async def test_desktop_click_falta_coordenadas():
    r = await tool_manager.execute("desktop", "click", {"x": 10})
    assert not r["success"]
    assert "x, y" in r["error"]


@pytest.mark.anyio
async def test_desktop_type_falta_texto():
    r = await tool_manager.execute("desktop", "type", {})
    assert not r["success"]


@pytest.mark.anyio
async def test_desktop_hotkey_falta_keys():
    r = await tool_manager.execute("desktop", "hotkey", {})
    assert not r["success"]


@pytest.mark.anyio
async def test_desktop_click_acota_coordenadas_fuera_de_pantalla(monkeypatch):
    from app.tools import desktop_tool
    desktop_tool._ensure_pyautogui()

    calls = []
    monkeypatch.setattr(desktop_tool.pyautogui, "click", lambda x, y: calls.append((x, y)))
    w, h = desktop_tool.pyautogui.size()

    r = await tool_manager.execute("desktop", "click", {"x": w + 5000, "y": -100})
    assert r["success"]
    assert calls == [(w - 1, 0)]  # acotado dentro de los limites reales de pantalla


@pytest.mark.anyio
async def test_desktop_hotkey_delega_en_pyautogui(monkeypatch):
    from app.tools import desktop_tool
    desktop_tool._ensure_pyautogui()

    calls = []
    monkeypatch.setattr(desktop_tool.pyautogui, "hotkey", lambda *keys: calls.append(keys))

    r = await tool_manager.execute("desktop", "hotkey", {"keys": ["ctrl", "z"]})
    assert r["success"]
    assert calls == [("ctrl", "z")]
