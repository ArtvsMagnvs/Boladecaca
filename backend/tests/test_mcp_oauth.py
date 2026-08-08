# tests/test_mcp_oauth.py — «Autorizar» en la web del servicio (V1.2 C1c)
#
# LO QUE BLINDA, y por qué cada cosa:
#   1. Los tokens se guardan CIFRADOS y no salen nunca por la API — es la
#      credencial de una cuenta ajena del usuario.
#   2. El puente navegador↔callback: `redirect_handler` captura la URL,
#      `resolve_callback` la resuelve, y un `state` que no espera a nadie NO
#      se acepta (o un callback ajeno podría inyectar un código).
#   3. La autorización se va con el servidor al borrarlo: dejar el token de un
#      servicio ya borrado es guardar la llave de una puerta que no existe.
#   4. El flujo SOLO se arma con `auth="oauth"`: un servidor de token no puede
#      acabar disparando un login por accidente.
#   5. El catálogo curado es COHERENTE — cada entrada declara lo que su tipo de
#      autenticación exige (un `token` sin campos que pedir sería inconectable).
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app import mcp as mcp_service
from app.core import secrets as secrets_helper
from app.db.database import Base, SessionLocal, engine as db_engine
from app.db.models import Config
from app.mcp import oauth as mcp_oauth

CATALOGO = json.loads(
    (Path(__file__).parent.parent.parent / "frontend" / "src" / "data" /
     "mcpCatalog.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _limpio():
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
        mcp_oauth._PENDING.clear()
        mcp_oauth._BY_STATE.clear()

    Base.metadata.create_all(bind=db_engine)
    _purge()
    yield
    _purge()


# ===========================================================================
# 1. Los tokens, cifrados y nunca expuestos
# ===========================================================================
class TestAlmacen:
    @pytest.mark.anyio
    async def test_token_se_guarda_cifrado_y_se_recupera(self):
        from mcp.shared.auth import OAuthToken

        store = mcp_oauth._TokenStore("linear")
        assert await store.get_tokens() is None
        await store.set_tokens(OAuthToken(access_token="secreto-123",
                                          token_type="Bearer"))

        s = SessionLocal()
        try:
            row = s.query(Config).filter(Config.key == "mcp.oauth.linear").first()
        finally:
            s.close()
        assert row is not None
        assert "secreto-123" not in (row.value or ""), "el token NO puede estar en claro"
        assert secrets_helper.is_encrypted(row.value)

        assert (await store.get_tokens()).access_token == "secreto-123"
        assert mcp_service.is_authorized("linear")

    @pytest.mark.anyio
    async def test_el_cliente_registrado_tambien_persiste(self):
        """Sin guardar el `client_info` del registro dinámico, cada reconexión
        daría de alta un cliente NUEVO en la cuenta del usuario."""
        from mcp.shared.auth import OAuthClientInformationFull

        store = mcp_oauth._TokenStore("linear")
        await store.set_client_info(OAuthClientInformationFull(
            client_id="abc123", redirect_uris=[mcp_service.oauth_redirect_uri()]))
        info = await store.get_client_info()
        assert info is not None and info.client_id == "abc123"

    def test_la_api_no_devuelve_el_token(self):
        from fastapi.testclient import TestClient

        from app.main import app

        asyncio.get_event_loop_policy()  # sin efecto: solo evita warnings de loop
        mcp_oauth._save("linear", {"tokens": {"access_token": "secreto-123",
                                              "token_type": "Bearer"}})
        mcp_service.upsert_server(mcp_service.MCPServerConfig(
            name="linear", transport="http", url="https://mcp.linear.app/mcp",
            auth="oauth"))
        with TestClient(app) as client:
            r = client.get("/api/mcp/servers")
        assert r.status_code == 200
        assert "secreto-123" not in r.text
        fila = [s for s in r.json() if s["name"] == "linear"][0]
        assert fila["auth"] == "oauth" and fila["authorized"] is True


# ===========================================================================
# 2. El puente navegador ↔ callback
# ===========================================================================
class TestPuente:
    @pytest.mark.anyio
    async def test_la_url_se_captura_y_el_callback_la_resuelve(self):
        """El SDK llamaría a `redirect_handler` (abrir navegador) y luego a
        `callback_handler` (esperar el código). Aquí se comprueba el puente
        completo sin red: la URL queda disponible para el frontend, y el
        código que llega por el endpoint desbloquea la espera."""
        provider = mcp_oauth.build_provider("linear", "https://mcp.linear.app/mcp")
        assert provider is not None
        flow = mcp_oauth._PENDING["linear"]

        await flow_redirect(provider, "https://mcp.linear.app/authorize?state=ST-1&x=1")
        assert mcp_service.pending_authorize_url("linear").startswith("https://mcp.linear.app")
        assert flow.state == "ST-1"

        assert mcp_service.resolve_oauth_callback("CODE-9", "ST-1") is True
        assert flow.done.is_set() and flow.code == "CODE-9"

    def test_un_state_desconocido_no_se_acepta(self):
        """Sin esto, un callback ajeno podría inyectar un código en un flujo
        que no le corresponde."""
        assert mcp_service.resolve_oauth_callback("CODE", "ST-INVENTADO") is False

    @pytest.mark.anyio
    async def test_dos_flujos_a_la_vez_no_se_mezclan(self):
        p1 = mcp_oauth.build_provider("linear", "https://mcp.linear.app/mcp")
        p2 = mcp_oauth.build_provider("notion", "https://mcp.notion.com/mcp")
        assert p1 is not None and p2 is not None
        f1, f2 = mcp_oauth._PENDING["linear"], mcp_oauth._PENDING["notion"]
        await flow_redirect(p1, "https://a/authorize?state=A")
        await flow_redirect(p2, "https://b/authorize?state=B")
        assert mcp_service.resolve_oauth_callback("c1", "A") is True
        assert f1.done.is_set() and not f2.done.is_set()

    def test_cancelar_libera_el_flujo(self):
        mcp_oauth.build_provider("linear", "https://mcp.linear.app/mcp")
        mcp_service.cancel_oauth("linear", "prueba")
        assert mcp_service.pending_authorize_url("linear") is None

    def test_el_redirect_uri_es_un_endpoint_de_esta_api(self):
        """Se declara en el registro dinámico, así que cambiarlo obliga a
        re-autorizar: que quede fijado por un test."""
        assert mcp_service.oauth_redirect_uri().endswith("/api/mcp/oauth/callback")

    def test_el_callback_http_responde_una_pagina(self):
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app) as client:
            r = client.get("/api/mcp/oauth/callback?code=X&state=NO-EXISTE")
            assert r.status_code == 409 and "Aithera" in r.text
            r = client.get("/api/mcp/oauth/callback?error=access_denied")
            assert r.status_code == 400


async def flow_redirect(provider, url):
    """Invoca el `redirect_handler` REAL que `build_provider` cableó — el que
    el SDK llamaría de verdad. Simularlo aquí habría dejado el handler sin
    probar (lección S9b/S9c: la lógica puede ser correcta y estar
    desconectada)."""
    await provider.context.redirect_handler(url)


# ===========================================================================
# 3 y 4. Ciclo de vida y activación del flujo
# ===========================================================================
class TestCicloDeVida:
    def test_borrar_el_servidor_borra_su_autorizacion(self):
        mcp_service.upsert_server(mcp_service.MCPServerConfig(
            name="linear", transport="http", url="https://mcp.linear.app/mcp",
            auth="oauth"))
        mcp_oauth._save("linear", {"tokens": {"access_token": "t", "token_type": "Bearer"}})
        assert mcp_service.is_authorized("linear")
        mcp_service.delete_server("linear")
        assert not mcp_service.is_authorized("linear")

    def test_el_campo_auth_sobrevive_al_round_trip(self):
        mcp_service.upsert_server(mcp_service.MCPServerConfig(
            name="linear", transport="http", url="https://x/mcp", auth="oauth"))
        assert mcp_service.get_server("linear").auth == "oauth"

    def test_config_de_c1_sin_campo_auth_sigue_valiendo(self):
        """Append-only con default seguro: un servidor guardado antes de C1c
        (sin `auth`) no puede volverse OAuth por sorpresa."""
        cfg = mcp_service.MCPServerConfig.from_dict(
            {"name": "viejo", "transport": "stdio", "command": "npx"})
        assert cfg.auth == "none"

    @pytest.mark.anyio
    async def test_solo_auth_oauth_arma_el_flujo(self):
        """El transporte lo decide la config; el LOGIN lo decide `auth`. Un
        servidor de token no puede acabar abriendo un navegador."""
        mcp_service.upsert_server(mcp_service.MCPServerConfig(
            name="conclave", transport="http", url="https://x/mcp", auth="token"))
        conn = mcp_service.get_connection("conclave")
        try:
            conn._make_transport()
        except Exception:
            pass                     # la conexión real no importa aquí
        assert "conclave" not in mcp_oauth._PENDING

        mcp_service.upsert_server(mcp_service.MCPServerConfig(
            name="conoauth", transport="http", url="https://x/mcp", auth="oauth"))
        mcp_service.drop_connection("conoauth")
        conn = mcp_service.get_connection("conoauth")
        try:
            conn._make_transport()
        except Exception:
            pass
        assert "conoauth" in mcp_oauth._PENDING
        mcp_service.cancel_oauth("conoauth", "fin del test")


# ===========================================================================
# 5. El catálogo curado es coherente
# ===========================================================================
class TestCatalogo:
    def test_todas_las_entradas_son_conectables_tal_como_estan(self):
        """Cada entrada tiene que pasar la MISMA validación que un alta
        manual: un catálogo con una config inválida es peor que no tenerlo."""
        for s in CATALOGO["servers"]:
            cfg = mcp_service.MCPServerConfig(
                name=s["slug"], transport=s["config"]["transport"],
                command=s["config"].get("command", ""),
                args=s["config"].get("args", []),
                url=s["config"].get("url", ""), auth=s["auth"])
            assert mcp_service.validate_config(cfg) is None, s["slug"]

    def test_cada_tipo_de_auth_declara_lo_que_le_toca(self):
        for s in CATALOGO["servers"]:
            if s["auth"] == "token":
                assert s["secrets"], f"{s['slug']}: 'token' sin campos que pedir"
                assert all(x.get("help_url") for x in s["secrets"]), \
                    f"{s['slug']}: un token sin decir dónde conseguirlo no sirve"
            else:
                # oauth y none NO piden nada al usuario: pedirlo sería la
                # fricción que C1c viene a quitar.
                assert not s["secrets"], f"{s['slug']}: {s['auth']} no debe pedir claves"
            if s["auth"] == "oauth":
                assert s["config"]["transport"] in ("http", "sse"), \
                    f"{s['slug']}: el login web solo aplica a servidores remotos"

    def test_las_descripciones_estan_pensadas_para_alguien_que_no_sabe(self):
        """Petición explícita del usuario. Se comprueba lo comprobable: que
        existan, que no sean un eslogan de tres palabras, y que no sean el
        título repetido."""
        for s in CATALOGO["servers"]:
            d = s["description_es"]
            assert len(d) >= 60, f"{s['slug']}: descripción demasiado corta"
            assert d.strip().lower() != s["title"].strip().lower()
            assert d.rstrip().endswith("."), f"{s['slug']}: frase sin terminar"

    def test_ni_slugs_ni_categorias_sueltas(self):
        slugs = [s["slug"] for s in CATALOGO["servers"]]
        assert len(slugs) == len(set(slugs)), "hay slugs repetidos"
        cats = {c["id"] for c in CATALOGO["categories"]}
        for s in CATALOGO["servers"]:
            assert s["category"] in cats, f"{s['slug']}: categoría inexistente"

    def test_hay_bastantes_y_la_mayoria_son_de_un_clic(self):
        """La petición era 20-30 servicios, y que el «Autorizar» directo se
        use SIEMPRE que se pueda."""
        total = len(CATALOGO["servers"])
        assert 20 <= total <= 30, total
        oauth = sum(1 for s in CATALOGO["servers"] if s["auth"] == "oauth")
        assert oauth >= 12, f"solo {oauth} de {total} con login de un clic"
