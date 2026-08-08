# tests/test_mcp_client.py — cliente MCP (V1.2 C1, doc 27 §C1)
#
# Tres capas de tests:
#   1. STORE: round-trip de configuración + secretos CIFRADOS en reposo (el
#      valor en la tabla Config jamás contiene el token en claro) + la API de
#      nombres-de-claves nunca devuelve valores.
#   2. PROXY (sin red): catálogo desde la caché, gate marcado en TODO,
#      sandbox de argumentos (obligatorios/no-declarados/tipos), preflight
#      barato, mapeo de permiso por prefijo — LA MISMA constante en
#      permissions.py y en el proxy (contrato anti-divergencia).
#   3. INTEGRACIÓN (servidor MCP REAL): tests/mcp_mini_server.py lanzado por
#      stdio con el venv — spawn + initialize + list_tools + call_tool de
#      verdad, sin mocks del SDK. Cubre además la sanitización de la
#      respuesta externa (S9c) y el fallo rápido de un servidor muerto.
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app import mcp as mcp_service
from app.automation import permission_service
from app.db.database import Base, SessionLocal, engine as db_engine
from app.db.models import Config
from app.tools.tool_manager import tool_manager

MINI_SERVER = str(Path(__file__).parent / "mcp_mini_server.py")


@pytest.fixture(autouse=True)
def _clean_mcp_config():
    """[LOG-1/S3] Config es una tabla GLOBAL — limpiar las claves mcp.* al
    ENTRAR y al SALIR, y retirar cualquier proxy mcp_* del ToolManager."""
    def _purge():
        s = SessionLocal()
        try:
            s.query(Config).filter(Config.key.like("mcp.%")).delete(
                synchronize_session=False)
            s.commit()
        except Exception:
            s.rollback()
        finally:
            s.close()
        for tid in [t for t in list(tool_manager._tools)
                    if t.startswith(permission_service.MCP_TOOL_PREFIX)]:
            tool_manager.unregister(tid)
        mcp_service.drop_connection("minitest")
        mcp_service.drop_connection("roto")

    Base.metadata.create_all(bind=db_engine)
    _purge()
    yield
    _purge()


def _cfg(name="minitest", **kw) -> mcp_service.MCPServerConfig:
    base = dict(name=name, transport="stdio", command=sys.executable,
                args=[MINI_SERVER], description="mini servidor de prueba",
                enabled=True)
    base.update(kw)
    return mcp_service.MCPServerConfig(**base)


# ===========================================================================
# 1. STORE
# ===========================================================================
class TestStore:
    def test_round_trip_upsert_list_get_delete(self):
        mcp_service.upsert_server(_cfg())
        assert [s.name for s in mcp_service.list_servers()] == ["minitest"]
        got = mcp_service.get_server("minitest")
        assert got.command == sys.executable and got.enabled
        assert mcp_service.delete_server("minitest")
        assert mcp_service.list_servers() == []
        assert not mcp_service.delete_server("minitest")  # ya no existe

    def test_validacion_rechaza_configs_invalidas(self):
        with pytest.raises(ValueError):
            mcp_service.upsert_server(_cfg(name="Nombre Con Espacios"))
        with pytest.raises(ValueError):
            mcp_service.upsert_server(_cfg(transport="carrier-pigeon"))
        with pytest.raises(ValueError):
            mcp_service.upsert_server(_cfg(command=""))          # stdio sin comando
        with pytest.raises(ValueError):
            mcp_service.upsert_server(_cfg(transport="sse", url="ni-una-url"))

    def test_secretos_cifrados_en_reposo_y_nunca_expuestos(self):
        mcp_service.upsert_server(
            _cfg(), {"env": {"GITHUB_TOKEN": "ghp_secretisimo123"}})
        # En la BD: NUNCA el token en claro.
        s = SessionLocal()
        try:
            row = s.query(Config).filter(Config.key == "mcp.secret.minitest").first()
        finally:
            s.close()
        assert row is not None
        assert "ghp_secretisimo123" not in (row.value or "")
        from app.core import secrets as sec
        assert sec.is_encrypted(row.value)
        # La API de nombres: claves sí, valores jamás.
        nombres = mcp_service.secret_key_names("minitest")
        assert nombres["env"] == ["GITHUB_TOKEN"]
        assert "ghp_secretisimo123" not in str(nombres)

    def test_upsert_sin_secrets_conserva_los_guardados(self):
        mcp_service.upsert_server(_cfg(), {"env": {"TOKEN": "abc"}})
        mcp_service.upsert_server(_cfg(description="editada"))   # secrets=None
        assert mcp_service.get_server("minitest").description == "editada"
        assert mcp_service.secret_key_names("minitest")["env"] == ["TOKEN"]

    def test_set_enabled_y_cache_de_tools(self):
        mcp_service.upsert_server(_cfg())
        assert mcp_service.set_enabled("minitest", False)
        assert mcp_service.get_server("minitest").enabled is False
        mcp_service.cached_tools("minitest") == []
        from app.mcp import store as _store
        _store.cache_tools("minitest", [{"name": "x", "description": "d",
                                         "input_schema": {}}])
        assert [t["name"] for t in mcp_service.cached_tools("minitest")] == ["x"]


# ===========================================================================
# 2. PROXY (sin red) — catálogo, gate, sandbox, preflight, permiso
# ===========================================================================
def _proxy_con_catalogo(schema=None) -> mcp_service.MCPToolProxy:
    """Proxy sobre un servidor configurado con tools EN CACHÉ (sin conectar)."""
    mcp_service.upsert_server(_cfg())
    from app.mcp import store as _store
    _store.cache_tools("minitest", [{
        "name": "buscar",
        "description": "busca algo",
        "input_schema": schema if schema is not None else {
            "type": "object",
            "properties": {"q": {"type": "string", "description": "consulta"},
                           "limite": {"type": "integer"}},
            "required": ["q"],
        },
    }])
    return mcp_service.MCPToolProxy("minitest")


class TestProxy:
    def test_gate_marcado_en_tool_y_en_cada_accion(self):
        proxy = _proxy_con_catalogo()
        assert proxy.requires_confirmation is True
        acciones = proxy.list_actions()
        assert acciones and all(a["requires_confirmation"] is True for a in acciones)
        # Y el catálogo del toolloop lo lee como sensible (needs_approval).
        from app.tie import toolloop
        tool_manager.register(proxy)
        catalogo = toolloop.build_catalog([proxy.tool_id], tool_manager)
        assert catalogo and all(e["needs_approval"] for e in catalogo)

    def test_sandbox_obligatorio_faltante(self):
        proxy = _proxy_con_catalogo()
        assert proxy.validate_params("buscar", {}) is False           # falta q
        assert proxy.validate_params("buscar", {"q": "hola"}) is True

    def test_sandbox_argumento_no_declarado_se_rechaza(self):
        proxy = _proxy_con_catalogo()
        assert proxy.validate_params("buscar", {"q": "x", "colado": 1}) is False

    def test_sandbox_additional_properties_true_lo_permite(self):
        proxy = _proxy_con_catalogo({
            "type": "object", "properties": {"q": {"type": "string"}},
            "required": ["q"], "additionalProperties": True,
        })
        assert proxy.validate_params("buscar", {"q": "x", "extra": "ok"}) is True

    def test_sandbox_tipos_primitivos(self):
        proxy = _proxy_con_catalogo()
        assert proxy.validate_params("buscar", {"q": 42}) is False        # str esperado
        assert proxy.validate_params("buscar", {"q": "x", "limite": "5"}) is False
        assert proxy.validate_params("buscar", {"q": "x", "limite": True}) is False  # bool≠int
        assert proxy.validate_params("buscar", {"q": "x", "limite": 5}) is True

    def test_sandbox_accion_desconocida_con_catalogo_se_rechaza(self):
        proxy = _proxy_con_catalogo()
        assert proxy.validate_params("accion_inventada", {}) is False

    def test_preflight_barato(self):
        proxy = _proxy_con_catalogo()
        assert proxy.preflight() is None                     # nunca intentado → que pruebe
        mcp_service.set_enabled("minitest", False)
        assert "desactivado" in proxy.preflight()
        mcp_service.delete_server("minitest")
        assert "ya no está configurado" in proxy.preflight()

    def test_permiso_por_prefijo_misma_constante(self):
        """El contrato anti-divergencia: el tool_id del proxy y el mapeo de
        permisos usan LA MISMA constante — si alguien cambia una sin la otra,
        esto revienta."""
        proxy = _proxy_con_catalogo()
        assert proxy.tool_id.startswith(permission_service.MCP_TOOL_PREFIX)
        assert permission_service.permission_for_tool_action(
            proxy.tool_id, "buscar") == "mcp.use"
        # Fail-closed: sin el permiso activado, NO está pre-autorizado.
        assert not permission_service.is_tool_action_pre_authorized(
            proxy.tool_id, "buscar")

    def test_mcp_use_en_catalogo_riesgo_alto_fuera_de_balanced(self):
        ids = {p.id: p for p in permission_service.CATALOG}
        assert "mcp.use" in ids and ids["mcp.use"].risk == "high"
        assert "mcp.use" not in permission_service.PROFILES["balanced"]
        assert "mcp.use" in permission_service.PROFILES["full"]


# ===========================================================================
# 3. INTEGRACIÓN — servidor MCP REAL por stdio (el mini-servidor del venv)
# ===========================================================================
@pytest.mark.anyio
class TestIntegracionServidorReal:
    async def test_cadena_completa_conectar_descubrir_llamar(self):
        mcp_service.upsert_server(_cfg())
        ids = mcp_service.register_enabled_servers(tool_manager)
        assert ids == ["mcp_minitest"]
        conn = mcp_service.get_connection("minitest")
        try:
            await conn.ensure_ready()
            assert {"echo", "suma", "sucio"} <= {t["name"] for t in conn.tools}
            # Llamada por el ToolManager REAL (whitelist + validaciones + timeout).
            r = await tool_manager.execute("mcp_minitest", "echo", {"text": "hola"})
            assert r["success"] and "eco: hola" in r["result"]["text"]
            # Sandbox en la cadena real: argumento colado NO llega al servidor.
            r = await tool_manager.execute("mcp_minitest", "echo",
                                           {"text": "x", "colado": 1})
            assert not r["success"]
            # Sanitización (S9c): el U+FFFC del servidor no sobrevive.
            r = await tool_manager.execute("mcp_minitest", "sucio", {})
            assert r["success"] and "￼" not in r["result"]["text"]
            # Descubrimiento cacheado para el catálogo post-reinicio.
            assert len(mcp_service.cached_tools("minitest")) == 3
        finally:
            await mcp_service.shutdown_all()

    async def test_servidor_muerto_al_arrancar_falla_rapido_y_honesto(self):
        import time
        mcp_service.upsert_server(mcp_service.MCPServerConfig(
            name="roto", transport="stdio", command=sys.executable,
            args=["-c", "import sys; sys.exit(3)"], enabled=True))
        conn = mcp_service.get_connection("roto")
        t0 = time.monotonic()
        with pytest.raises(RuntimeError):
            await conn.ensure_ready()
        # MUCHO antes que el timeout de conexión (45s) — el worker muerto se
        # detecta al morir, no al agotar el plazo (hallazgo de la verificación
        # en vivo de C1: antes tardaba 30s).
        assert time.monotonic() - t0 < 10
        assert conn.last_error


# ===========================================================================
# 4. ENDPOINTS HTTP — la superficie que consume la UI de Ajustes
# ===========================================================================
class TestEndpoints:
    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app) as c:
            yield c

    def test_crud_completo_por_http(self, client):
        # Vacío al empezar (la fixture limpió).
        assert client.get("/api/mcp/servers").json() == []
        # Alta con secretos — la respuesta trae NOMBRES de claves, no valores.
        r = client.post("/api/mcp/servers", json={
            "name": "MiniTest",           # se normaliza a minúsculas
            "transport": "stdio", "command": sys.executable,
            "args": [MINI_SERVER], "description": "de prueba",
            "env": {"TOKEN": "super-secreto"},
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["name"] == "minitest"
        assert body["secret_keys"]["env"] == ["TOKEN"]
        assert "super-secreto" not in r.text
        # El proxy quedó registrado EN CALIENTE en el ToolManager.
        assert tool_manager.get_tool("mcp_minitest") is not None
        # Tools (caché vacía aún, sin /test).
        assert client.get("/api/mcp/servers/minitest/tools").json() == {"tools": []}
        # Borrado retira el proxy.
        assert client.delete("/api/mcp/servers/minitest").json() == {"ok": True}
        assert tool_manager.get_tool("mcp_minitest") is None
        assert client.delete("/api/mcp/servers/minitest").status_code == 404

    def test_validacion_da_400_con_motivo(self, client):
        r = client.post("/api/mcp/servers", json={
            "name": "con espacios", "transport": "stdio", "command": "x"})
        assert r.status_code == 400 and "nombre" in r.json()["detail"]

    def test_probar_conecta_de_verdad_y_descubre(self, client):
        client.post("/api/mcp/servers", json={
            "name": "minitest", "transport": "stdio",
            "command": sys.executable, "args": [MINI_SERVER]})
        r = client.post("/api/mcp/servers/minitest/test")
        assert r.status_code == 200, r.text
        assert r.json()["connected"] is True
        assert r.json()["tools_count"] == 3
        nombres = {t["name"] for t in
                   client.get("/api/mcp/servers/minitest/tools").json()["tools"]}
        assert nombres == {"echo", "suma", "sucio"}
