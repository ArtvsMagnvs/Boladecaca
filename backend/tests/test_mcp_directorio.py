# tests/test_mcp_directorio.py — directorio + /comando + uso por contexto
# (V1.2 C1b, doc 42)
#
# Tres bloques, uno por pieza del diseño:
#   1. DIRECTORIO — el mapeo entrada-del-registro → config conectable, con
#      RESPUESTAS REALES grabadas (`fixtures_mcp_registry.json`, capturadas del
#      registro oficial el 2026-08-08). Sin red: lo que se prueba es la
#      traducción, no que internet funcione.
#   2. /COMANDO — el atajo explícito: parseo, respuestas deterministas, y el
#      pin sobre el intent. Con los NEGATIVOS que importan (un mensaje normal
#      no se toca; "/algo" sin servidores conectados tampoco).
#   3. POR CONTEXTO — el bloque que entra en el prompt del clasificador y la
#      línea del mapa de capacidades, incluida la no-regresión de que SIN
#      servidores conectados nada cambia.
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import mcp as mcp_service
from app.automation import permission_service
from app.db.database import Base, SessionLocal, engine as db_engine
from app.db.models import Config
from app.mcp import directory
from app.tie import capabilities_map, mcp_command
from app.tie.contracts import Intent, IntentType
from app.tools.tool_manager import tool_manager

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures_mcp_registry.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _limpio():
    """Config es una tabla GLOBAL (LOG-1): limpiar al ENTRAR y al SALIR, y
    tirar las cachés del TIE para que un test no herede el bloque de otro."""
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
        mcp_command.invalidate_cache()
        directory.clear_cache()

    Base.metadata.create_all(bind=db_engine)
    _purge()
    yield
    _purge()


def _conectar(name="github", desc="repositorios, issues y pull requests",
              transport="stdio", **kw):
    cfg = mcp_service.MCPServerConfig(
        name=name, transport=transport, command=kw.get("command", "npx"),
        args=kw.get("args", ["-y", "server"]), url=kw.get("url", ""),
        description=desc, enabled=kw.get("enabled", True))
    mcp_service.upsert_server(cfg)
    mcp_command.invalidate_cache()
    return cfg


# ===========================================================================
# 1. DIRECTORIO — mapeo con respuestas REALES del registro oficial
# ===========================================================================
class TestMapeoDelRegistro:
    def test_paquete_npm_se_traduce_a_stdio_con_npx(self):
        e = directory.map_entry(FIXTURES["npm_stdio"][0])
        assert e.connectable and e.transport == "stdio"
        assert e.command == "npx"
        # El "-y" viene de los runtimeArguments REALES de la entrada, y el
        # identificador del paquete va después.
        assert e.args[0] == "-y" and e.args[-1] == "remote-filesystem-mcp-server"
        assert e.suggested_slug == "remote-filesystem"      # sin el reverse-DNS

    def test_variables_de_entorno_se_traducen_a_campos_de_secreto(self):
        e = directory.map_entry(FIXTURES["npm_stdio"][0])
        por_clave = {s.key: s for s in e.secrets}
        assert "GCS_BUCKET" in por_clave and por_clave["GCS_BUCKET"].required
        # `isSecret` real de la entrada: la clave privada SÍ, el bucket no.
        assert por_clave["GCS_PRIVATE_KEY"].is_secret
        assert all(s.kind == "env" for s in e.secrets)
        assert por_clave["GCS_BUCKET"].description        # el texto de ayuda viaja

    def test_remoto_streamable_http_se_traduce_a_http_con_headers(self):
        e = directory.map_entry(FIXTURES["remote_http"][0])
        assert e.connectable and e.transport == "http"
        assert e.url.startswith("https://")
        assert [s.key for s in e.secrets] == ["Authorization"]
        assert e.secrets[0].kind == "header" and e.secrets[0].is_secret

    def test_pypi_sin_runtime_hint_cae_en_uvx(self):
        """Entrada REAL sin `runtimeHint`: el registryType basta para saber
        con qué lanzarlo. Sin este respaldo, media docena de servidores
        Python del registro aparecerían como no conectables."""
        e = directory.map_entry(FIXTURES["pypi_sin_hint"][0])
        assert e.connectable and e.command == "uvx"

    def test_solo_docker_se_marca_no_conectable_con_motivo(self):
        """Entrada REAL con un paquete OCI: NO se adivina un `docker run`.
        Ejecutar lo que uno se inventa es justo lo que no se hace con código
        externo — se dice que no y se enseña el repositorio."""
        e = directory.map_entry(FIXTURES["no_conectable"][0])
        assert not e.connectable
        assert e.reason and "repositorio" in e.reason
        assert e.command == "" and e.url == ""
        assert e.repository_url                       # el usuario puede ir a mirar

    def test_slug_sugerido_es_valido_como_nombre_de_servidor(self):
        """El slug acaba siendo parte del tool_id, así que tiene que pasar la
        MISMA validación que un alta manual (`store.validate_config`)."""
        for grupo in FIXTURES.values():
            for srv in grupo:
                e = directory.map_entry(srv)
                cfg = mcp_service.MCPServerConfig(
                    name=e.suggested_slug, transport="stdio", command="npx")
                assert mcp_service.validate_config(cfg) is None, e.suggested_slug

    def test_entrada_basura_no_revienta(self):
        for basura in ({}, {"name": None}, {"packages": "no-es-lista"},
                       {"remotes": [{"type": "ftp", "url": "ftp://x"}]}):
            e = directory.map_entry(basura)
            assert e.connectable is False or e.transport in ("", "stdio", "http", "sse")


# ===========================================================================
# 2. /COMANDO — el atajo explícito
# ===========================================================================
class TestComando:
    def test_mensaje_normal_no_se_toca(self):
        _conectar()
        for texto in ("hola", "¿qué tal?", "lee el informe y resúmelo",
                      "usa C:/ruta/archivo.txt", ""):
            assert mcp_command.parse(texto) is None

    def test_sin_servidores_conectados_barra_no_es_comando(self):
        """Sin ningún MCP, "/loquesea" puede ser cualquier cosa (una ruta, un
        fragmento de código) y no debe secuestrar el mensaje."""
        assert mcp_command.parse("/github dame mis PRs") is None

    def test_comando_valido_separa_servidor_y_peticion(self):
        _conectar()
        cmd = mcp_command.parse("/github dame mis PRs abiertos")
        assert cmd is not None and cmd.reply is None
        assert cmd.tool_id == "mcp_github"
        assert cmd.rest == "dame mis PRs abiertos"      # el prefijo se retira

    def test_comando_a_secas_lista_las_acciones_sin_llm(self):
        _conectar()
        from app.mcp import store as _store
        _store.cache_tools("github", [
            {"name": "list_prs", "description": "lista pull requests", "input_schema": {}},
            {"name": "create_issue", "description": "crea una issue", "input_schema": {}},
        ])
        cmd = mcp_command.parse("/github")
        assert cmd is not None and cmd.tool_id is None
        assert "list_prs" in cmd.reply and "create_issue" in cmd.reply

    def test_servidor_desconocido_responde_con_los_que_hay(self):
        _conectar(name="github")
        cmd = mcp_command.parse("/gitlab dame mis MRs")
        assert cmd is not None and cmd.tool_id is None
        assert "/github" in cmd.reply and "gitlab" in cmd.reply

    def test_servidor_desactivado_no_es_invocable(self):
        _conectar(name="github", enabled=False)
        assert mcp_command.parse("/github algo") is None

    def test_pin_anade_la_tool_y_saca_del_camino_corto(self):
        """Lo CRÍTICO: el camino corto no tiene herramientas. Un intent
        conversational con un servidor pedido a mano tiene que subir a
        EXECUTE, o el comando se aceptaría sin usar el servicio."""
        intent = Intent(type=IntentType.CONVERSATIONAL, goal="dame mis PRs")
        assert intent.is_short_path
        out = mcp_command.pin(intent, "mcp_github")
        assert "mcp_github" in out.requires_tools
        assert not out.is_short_path and out.type == IntentType.EXECUTE

    def test_pin_no_duplica_ni_pisa_otras_tools(self):
        intent = Intent(type=IntentType.EXECUTE, goal="x",
                        requires_tools=["filesystem", "mcp_github"])
        out = mcp_command.pin(intent, "mcp_github")
        assert out.requires_tools == ["filesystem", "mcp_github"]

    @pytest.mark.anyio
    async def test_el_comando_esta_CABLEADO_en_el_pipeline_real(self):
        """EL test que importa: no que `parse` funcione, sino que el pipeline
        REAL lo llame. Ya ha pasado dos veces en este proyecto (S9b, S9c) que
        la lógica fuera correcta y estuviera desconectada — aquí se ejercita
        `tie.handle_stream` de verdad, con un único doble: el clasificador."""
        import app.tie as tie
        from app.tie import intents

        _conectar(name="github")
        visto: dict = {}

        async def _fake_classify(text, **kw):
            visto["texto"] = text        # lo que llega al clasificador
            return Intent(type=IntentType.CONVERSATIONAL, goal=text, confidence=0.9)

        original = intents.classify
        intents.classify = _fake_classify
        try:
            async for _ev in tie.handle_stream("/github dame mis PRs abiertos"):
                break                    # con el primer evento basta
        except Exception:
            pass                         # sin LLM real el turno acaba como sea
        finally:
            intents.classify = original

        # El prefijo se retiró ANTES de clasificar: el modelo nunca ve "/github".
        assert visto.get("texto") == "dame mis PRs abiertos"

    def test_el_comando_no_es_una_autorizacion(self):
        """`/github` fija QUÉ herramienta, jamás concede permiso: `mcp.use`
        sigue apagado y la acción seguirá pasando por el gate."""
        _conectar()
        cmd = mcp_command.parse("/github borra el repo")
        assert permission_service.permission_for_tool_action(cmd.tool_id, "x") == "mcp.use"
        assert not permission_service.is_tool_action_pre_authorized(cmd.tool_id, "x")


# ===========================================================================
# 3. POR CONTEXTO — el clasificador y el mapa de capacidades
# ===========================================================================
class TestPorContexto:
    def test_sin_servidores_el_prompt_es_identico(self):
        """No-regresión por defecto: quien no use MCP no paga ni un carácter
        de prompt extra."""
        assert mcp_command.classifier_block() == ""

    def test_el_bloque_lleva_el_tool_id_y_la_descripcion(self):
        _conectar(name="nausika", desc="navegación a vela y motor, rutas navales, mareas")
        bloque = mcp_command.classifier_block()
        assert "mcp_nausika" in bloque
        assert "rutas navales" in bloque
        # Y le dice al modelo que son valores válidos de requires_tools — sin
        # eso, el techo de la lista estática dejaría el servicio fuera (PU8).
        assert "requires_tools" in bloque

    def test_el_bloque_se_cachea_pero_la_invalidacion_lo_refresca(self):
        _conectar(name="uno", desc="primero")
        assert "mcp_uno" in mcp_command.classifier_block()
        mcp_service.upsert_server(mcp_service.MCPServerConfig(
            name="dos", transport="stdio", command="npx", description="segundo"))
        # Sin invalidar, la caché aún no lo ve (es lo que evita un viaje a la
        # BD por mensaje).
        assert "mcp_dos" not in mcp_command.classifier_block()
        mcp_command.invalidate_cache()
        assert "mcp_dos" in mcp_command.classifier_block()

    def test_el_clasificador_recibe_de_verdad_el_bloque(self):
        """El cableado REAL: no basta con que la función exista, tiene que
        llegar al system prompt que ve el modelo."""
        import asyncio

        _conectar(name="nausika", desc="rutas navales")
        visto = {}

        async def _fake_complete(prompt, system_prompt=None, capability=None, **kw):
            visto["system"] = system_prompt or ""
            return {"response": '{"type":"execute","goal":"ruta","confidence":0.9,'
                                '"requires_tools":["mcp_nausika"]}', "model": "fake"}

        from app.tie import intents, router
        original = router.complete
        router.complete = _fake_complete
        try:
            intent = asyncio.run(intents.classify(
                "dame la ruta naval de Barcelona a Mallorca"))
        finally:
            router.complete = original

        assert "mcp_nausika" in visto["system"], "el bloque debe ir en el prompt"
        assert "mcp_nausika" in intent.requires_tools

    def test_el_mapa_de_capacidades_menciona_los_servicios_sin_perder_nada(self):
        """La línea es ADITIVA: se suma al mapa base, no lo desplaza (medido:
        el base ya ocupa 1449 de 1500, así que meterla dentro expulsaba la
        última categoría)."""
        base = capabilities_map.summary(force=True)
        _conectar(name="nausika", desc="rutas navales")
        mcp_service.register_enabled_servers(tool_manager)
        con = capabilities_map.summary(force=True)

        assert "nausika" in con and "rutas navales" in con
        for linea in base.split("\n"):
            assert linea in con, f"el mapa base perdió: {linea[:60]}"
        assert len(con) <= capabilities_map.MAX_CHARS + capabilities_map._MCP_LINE_MAX + 4

    def test_el_mapa_no_lista_el_servidor_como_tool_generica(self):
        """Sin el marcado de `used`, el cajón "Además" lo repetiría como
        "mcp · nausika (0 acciones disponibles)", que no informa de nada."""
        _conectar(name="nausika", desc="rutas navales")
        mcp_service.register_enabled_servers(tool_manager)
        texto = capabilities_map.summary(force=True)
        assert "acciones disponibles)" not in texto.split("servicios externos")[-1]

    def test_conectar_por_la_api_refresca_las_dos_caches(self):
        """El endpoint invalida ambas cachés: sin esto, conectar un servidor y
        preguntar "¿qué sabes hacer?" seguiría sin mencionarlo (TTL de 1 h)."""
        from fastapi.testclient import TestClient

        from app.main import app

        capabilities_map.summary(force=True)
        assert mcp_command.classifier_block() == ""
        with TestClient(app) as client:
            r = client.post("/api/mcp/servers", json={
                "name": "nausika", "transport": "stdio", "command": "npx",
                "args": ["-y", "x"], "description": "rutas navales"})
            assert r.status_code == 200, r.text
        assert "mcp_nausika" in mcp_command.classifier_block()
        assert "nausika" in capabilities_map.summary()
