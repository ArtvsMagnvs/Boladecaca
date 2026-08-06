# tests/test_learner_failures.py — V1.1 L2b: taxonomía y atribución de fallos
#
# Lo que se prueba, en el orden en que importa:
#   1. La TAXONOMÍA con mensajes de error REALES del proyecto (recogidos de
#      logs, mem_error y las campañas 00-02), no inventados para el test.
#   2. Los ENGANCHES: que el kind LLEGA al payload de telemetría. Probar solo
#      que la función clasifica bien dejaría pasar el fallo que ya ha aparecido
#      TRES veces en este proyecto (S9b, S9c, rastro): lógica correcta y
#      DESCONECTADA.
#   3. La JUSTICIA: el contrato de producto nº 5 de la fase — un fallo de
#      conexión jamás cuenta como fallo del modelo ni del sistema.
#   4. Las propuestas `config_fix`: a las 3, no a las 2, y sin applier.
from __future__ import annotations

import pytest

from app.core.failures import (
    EXCUSED_BLAMES,
    FailureKind,
    annotate,
    blame_of,
    classify_failure,
    dominant,
    is_excused,
    kind_from_loop_event,
    kind_from_mel_reason,
    settings_hint,
)
from app.db.database import Base, SessionLocal, engine
from app.learner.models import FailureStat, ModelStat, ToolStat
from app.learner.stats import (
    aggregate_from_timeline,
    config_gaps,
    failure_summary,
    failures_in,
    model_ranking,
    record_failures,
    tool_ranking,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _limpia():
    """Al ENTRAR y al SALIR. La lección de L2: estas tablas son globales y otro
    archivo de test puede haberlas dejado con residuos que se colarían en el
    primer test de éste cuando corren en la misma sesión de pytest."""
    Base.metadata.create_all(bind=engine)

    def _borra():
        with SessionLocal() as s:
            for modelo in (FailureStat, ModelStat, ToolStat):
                s.query(modelo).delete()
            s.commit()
    _borra()
    yield
    _borra()


def _ev(stage, *, name=None, provider=None, model=None, ok=False, detail=None):
    return {"stage": stage, "name": name, "provider": provider, "model": model,
            "ok": ok, "detail": detail}


# ===========================================================================
# 1 · La taxonomía, con mensajes reales
# ===========================================================================
class TestTaxonomia:
    @pytest.mark.parametrize("source,texto,esperado", [
        # --- lo externo (mensajes REALES vistos en este proyecto) ---
        ("model", "getaddrinfo failed", FailureKind.CONNECTION),
        ("tool", "ConnectionError: Connection refused", FailureKind.CONNECTION),
        ("model", "Read timed out after 120s", FailureKind.CONNECTION),
        ("tool", "503 Service Unavailable", FailureKind.CONNECTION),
        ("model", "401 Unauthorized", FailureKind.PROVIDER_AUTH),
        ("model", "429 Too Many Requests", FailureKind.PROVIDER_LIMIT),
        ("tool", "se ha detectado un captcha en la página", FailureKind.EXTERNAL_CONTENT),
        # --- config (el texto que de verdad escribe el preflight de la Sesión A) ---
        ("tool", "añade una API key de SerpAPI o Brave en Ajustes → Búsqueda web",
         FailureKind.CONFIG_MISSING),
        ("tool", "Google Calendar API has not been used in project 1234",
         FailureKind.CONFIG_MISSING),
        ("tool", "la integración no está configurada", FailureKind.CONFIG_MISSING),
        # --- nuestro ---
        ("tool", "TypeError: 'NoneType' object is not subscriptable",
         FailureKind.SYSTEM_BUG),
        ("model", "KeyError: 'tools'", FailureKind.SYSTEM_BUG),
        ("planner", "el objetivo excede las capacidades reales", FailureKind.PLANNING),
        # --- el modelo ---
        ("model", "la respuesta no contenía un JSON parseable", FailureKind.MODEL_FORMAT),
        ("model", "no puedo completar este objetivo", FailureKind.MODEL_REASONING),
        # --- lo que no es un fallo ---
        ("gate", "el usuario rechazó el permiso", FailureKind.PERMISSION_DENIED),
        ("cancel", "kill-switch", FailureKind.USER_CANCELLED),
        # --- lo que no se sabe ---
        ("", "algo raro pasó", FailureKind.UNKNOWN),
    ])
    def test_clasifica_mensajes_reales(self, source, texto, esperado):
        assert classify_failure(source, texto) is esperado

    def test_un_bug_nuestro_disfrazado_de_red_sigue_siendo_nuestro(self):
        """LA REGLA DE DIRECCIÓN DEL DAÑO (corrección de la revisión): si un
        traceback nuestro arrastra la palabra "connection", clasificarlo como
        red lo EXCUSA y desaparece de las stats para siempre. Al revés solo
        cuesta una revisión de más. Ante la duda, la culpa se la queda casa."""
        k = classify_failure("tool", "AttributeError in connection pool: timeout")
        assert k is FailureKind.SYSTEM_BUG
        assert blame_of(k) == "aithera"
        assert not is_excused(k)

    def test_clasificar_jamas_lanza(self):
        for basura in (None, "", 12345, {"a": 1}, object()):
            assert isinstance(classify_failure(basura, basura), FailureKind)  # type: ignore

    def test_blame_desconocido_no_culpa_a_nadie(self):
        assert blame_of("inventado_que_no_existe") == "unknown"
        assert blame_of(None) == "unknown"

    def test_las_razones_del_mel_se_traducen_todas(self):
        """El MEL lleva desde E1 clasificando fallos de proveedor en SU
        vocabulario. Aquí solo se traduce — reimplementar esa detección sería
        tener dos verdades sobre el mismo error. Este test vigila que ninguna
        razón real se quede sin traducción y caiga en UNKNOWN por olvido."""
        from app.mel.fallback import _BREAKER_REASONS, classify_failure as mel_clasifica

        reales = {"transient", "timeout", "auth", "quota", "empty_response",
                  "context_length", "content_policy", "bad_model", "request_invalid",
                  "no_chain"}
        for razon in reales:
            assert kind_from_mel_reason(razon) is not FailureKind.UNKNOWN, razon
        # y las que abren el breaker existen de verdad en el MEL
        assert "transient" in _BREAKER_REASONS
        assert mel_clasifica(detail="getaddrinfo failed")[1] == "transient"

    def test_un_401_es_config_y_no_una_fatalidad_externa(self):
        """Corrección de la revisión: una API key caducada la arregla el
        usuario en dos clics. Con blame "external" el panel lo habría
        enterrado bajo "no es culpa de Aithera" y `config_gaps` nunca habría
        propuesto el arreglo."""
        assert blame_of(FailureKind.PROVIDER_AUTH) == "config"
        assert is_excused(FailureKind.PROVIDER_AUTH)     # sigue sin castigar al modelo

    def test_una_pregunta_al_usuario_no_es_una_averia(self):
        """`user_question` pasa por el MISMO funnel de telemetría que los
        fallos (se graba con ok=False), pero no es uno. Sin esta exención el
        panel de Salud contaría preguntas como averías."""
        assert kind_from_loop_event("user_question") is None
        assert annotate({"a": 1}, None) == {"a": 1}          # sale intacto, sin marca
        assert kind_from_loop_event("stalled") is FailureKind.MODEL_REASONING
        assert kind_from_loop_event("evento_del_futuro") is FailureKind.UNKNOWN

    def test_dominante_prioriza_lo_nuestro(self):
        assert dominant(["connection", "system_bug"]) is FailureKind.SYSTEM_BUG
        assert dominant(["connection", "model_reasoning"]) is FailureKind.MODEL_REASONING
        assert dominant(["permission_denied", "connection"]) is FailureKind.CONNECTION
        assert dominant([]) is None
        assert dominant(["basura_inexistente"]) is None

    def test_la_pista_de_ajustes_es_util_o_es_nada(self):
        assert settings_hint("añade una API key de SerpAPI") == "conexiones"
        assert settings_hint("el modelo no existe en ese proveedor") == "ia"
        assert settings_hint("algo completamente ajeno") is None

    def test_anotar_no_pisa_lo_que_ya_habia(self):
        salida = annotate({"error": "boom", "attempts": 2}, FailureKind.TOOL_ERROR,
                          tool="search")
        assert salida["error"] == "boom" and salida["attempts"] == 2
        assert salida["failure_kind"] == "tool_error" and salida["blame"] == "tool"
        assert salida["tool"] == "search"

    def test_el_enum_es_append_only(self):
        """Contrato congelado (mismo régimen que MemoryType/Capability): hay
        filas de `failure_stats` guardadas con estos valores. Renombrar uno las
        dejaría huérfanas."""
        assert {k.value for k in FailureKind} >= {
            "connection", "provider_auth", "provider_limit", "config_missing",
            "external_content", "tool_error", "model_reasoning", "model_format",
            "planning", "system_bug", "permission_denied", "user_cancelled", "unknown"}
        assert EXCUSED_BLAMES == frozenset({"external", "config", "none"})


# ===========================================================================
# 2 · Los enganches — que el kind LLEGA al payload
# ===========================================================================
class TestEnganches:
    def test_el_mel_atribuye_solo_los_fallos(self, monkeypatch):
        from app.mel import executor as mel_exec
        from app.mel.contracts import Capability, ExecutionRequest, ModelRef

        grabados = []
        import app.telemetry as _tel
        monkeypatch.setattr(_tel, "record", lambda *a, **k: grabados.append((a, k)))
        monkeypatch.setattr(mel_exec, "_record_async",
                            mel_exec._record_async)   # el real, sin tocar

        req = ExecutionRequest(capability=Capability.CHAT, prompt="hola")
        ref = ModelRef(provider="minimax", model="M3")
        mel_exec._record_async(req, ref, ok=False, latency_ms=10,
                               fallback_reason="transient", error="getaddrinfo failed")
        detalle = grabados[0][1]["detail"]
        assert detalle["failure_kind"] == "connection"
        assert detalle["blame"] == "external"

        grabados.clear()
        mel_exec._record_async(req, ref, ok=True, latency_ms=10)
        assert not (grabados[0][1].get("detail") or {}).get("failure_kind"), (
            "una llamada que fue bien no tiene dueño que buscar")

    def test_el_toolloop_atribuye_por_el_texto_del_error(self, monkeypatch):
        from app.tie import toolloop

        grabados = []
        import app.telemetry as _tel
        monkeypatch.setattr(_tel, "record", lambda *a, **k: grabados.append(k))

        toolloop._record_loop_event("preflight_not_ready", {"tools": {"search": "sin key"}})
        assert grabados[-1]["detail"]["failure_kind"] == "config_missing"

        toolloop._record_loop_event("invalid_json", {"text": "..."})
        assert grabados[-1]["detail"]["failure_kind"] == "model_format"

        toolloop._record_loop_event("user_question", {"answered": True})
        assert "failure_kind" not in (grabados[-1]["detail"] or {})

    def test_una_tool_inventada_no_se_le_carga_a_ninguna_tool(self, monkeypatch):
        """Pedir una herramienta que no existe es razonamiento del modelo. La
        tool ni corrió — y de hecho ni existe."""
        from app.tie import toolloop

        grabados = []
        import app.telemetry as _tel
        monkeypatch.setattr(_tel, "record", lambda *a, **k: grabados.append(k))
        toolloop._record_denial("bananas", "hacer_magia", "tool desconocida")
        assert grabados[-1]["detail"]["failure_kind"] == "model_reasoning"

    def test_el_planner_registra_su_propio_fallo(self, monkeypatch):
        from app.tie import planner

        grabados = []
        import app.telemetry as _tel
        monkeypatch.setattr(_tel, "record", lambda *a, **k: grabados.append(k))
        planner._record_planning_failure("invalid_graph", "ciclo detectado")
        assert grabados[-1]["detail"]["failure_kind"] == "planning"
        assert grabados[-1]["detail"]["blame"] == "aithera"

    def test_el_nodo_que_se_rinde_queda_atribuido_al_modelo(self, monkeypatch):
        """NEW-4 dejó la rendición en FAILED. L2b le pone dueño: es
        razonamiento del modelo, no una tool rota ni una red caída — y sin esa
        distinción el análisis de patrones de L3 los mezclaría."""
        from app.tie import executor as tie_exec
        from app.tie.contracts import NodeState, TaskGraph, TaskNode

        grabados = []
        import app.telemetry as _tel
        monkeypatch.setattr(_tel, "record", lambda *a, **k: grabados.append(k))
        monkeypatch.setattr(tie_exec, "_checkpoint", lambda *a, **k: None)

        nodo = TaskNode(id="n1", goal="leer el informe")
        nodo.validation = {"ok": False, "method": "grounding", "notes": "se rindió"}
        grafo = TaskGraph(id="g1", mission_id="m1", nodes={"n1": nodo})
        tie_exec._transition(nodo, NodeState.FAILED, grafo, "t1")
        assert grabados[-1]["detail"]["failure_kind"] == "model_reasoning"

        grabados.clear()
        nodo2 = TaskNode(id="n2", goal="otro")
        grafo.nodes["n2"] = nodo2
        tie_exec._transition(nodo2, NodeState.DONE, grafo, "t1")
        assert "failure_kind" not in (grabados[-1]["detail"] or {}), (
            "un nodo que fue bien no lleva atribución")


# ===========================================================================
# 3 · La justicia — el contrato de producto nº 5 de la fase
# ===========================================================================
class TestJusticia:
    def test_extraer_fallos_de_un_timeline(self):
        tl = {"events": [
            _ev("llm_call", name="chat", provider="minimax", model="M3",
                detail={"failure_kind": "connection", "blame": "external",
                        "error": "getaddrinfo failed"}),
            _ev("tool_call", name="search.search_web",
                detail={"failure_kind": "config_missing", "blame": "config",
                        "tool": "search", "error": "sin api key"}),
            _ev("llm_call", name="chat", provider="minimax", model="M3", ok=True),
        ]}
        fallos = failures_in(tl)
        assert len(fallos) == 2
        assert fallos[0]["component"] == "model:minimax:M3"
        assert fallos[1]["component"] == "tool:search"
        assert fallos[1]["event_key"] == "search.search_web"

    def test_el_componente_sigue_a_la_culpa_no_a_la_etapa(self):
        """CORRECCIÓN DE LA REVISIÓN: una tool INVENTADA se graba como
        `tool_call` denegado. Derivando el componente de la etapa, cada nombre
        que el modelo se sacara de la manga creaba una fila `tool:<alucinación>`
        permanente — basura en la tabla y la culpa apuntando a algo que no
        existe."""
        tl = {"events": [
            _ev("tool_call", name="bananas.hacer_magia",
                detail={"failure_kind": "model_reasoning", "blame": "model",
                        "denied": True}),
        ]}
        fallos = failures_in(tl)
        assert fallos[0]["component"] == "tie:toolloop"
        assert not fallos[0]["component"].startswith("tool:")

    def test_pero_una_config_ausente_SI_nombra_su_herramienta(self):
        """La otra mitad, que la primera versión de la corrección rompió: si la
        culpa NO es del modelo, el nombre de la tool es justo lo que hace
        accionable el aviso. "Falta la API key de search" sirve; "algo del
        bucle de herramientas no está configurado" no sirve para nada."""
        tl = {"events": [
            _ev("tool_call", name="search.search_web",
                detail={"failure_kind": "config_missing", "blame": "config",
                        "tool": "search", "error": "sin api key"}),
        ]}
        assert failures_in(tl)[0]["component"] == "tool:search"

    async def test_una_mision_caida_por_la_red_NO_castiga_al_modelo(self):
        """CONTRATO DE PRODUCTO Nº 5: 'un fallo de conexión jamás cuenta como
        fallo del modelo ni del sistema'. Es la petición literal del usuario."""
        tl = {"events": [
            _ev("llm_call", name="chat", provider="minimax", model="M3",
                detail={"failure_kind": "connection", "blame": "external"}),
        ], "summary": {"llm_by_model": {"minimax:M3": {"calls": 1, "fails": 1, "ms": 50}},
                       "tools": {}, "slowest_llm_ms": 50}}
        fallos = failures_in(tl)
        dom = dominant([f["kind"] for f in fallos])
        aggregate_from_timeline(tl, mission_ok=False,
                                excused=is_excused(dom), fallos=fallos)

        fila = model_ranking()[0]
        assert fila["missions"] == 1 and fila["missions_excused"] == 1
        assert fila["mission_success_rate"] == 0.0   # sin misiones contables aún

        # ...y con una misión buena encima, el modelo está al 100%, no al 50%.
        tl2 = {"events": [], "summary": {
            "llm_by_model": {"minimax:M3": {"calls": 1, "fails": 0, "ms": 30}},
            "tools": {}, "slowest_llm_ms": 30}}
        aggregate_from_timeline(tl2, mission_ok=True)
        fila = model_ranking()[0]
        assert fila["missions"] == 2 and fila["missions_ok"] == 1
        assert fila["mission_success_rate"] == 1.0, (
            "castigar al modelo por un timeout de DNS es medir ruido")

    async def test_un_fallo_del_modelo_si_cuenta(self):
        """La otra mitad del contrato: excusar de más sería igual de falso."""
        tl = {"events": [
            _ev("node_end", name="n1",
                detail={"failure_kind": "model_reasoning", "blame": "model"}),
        ], "summary": {"llm_by_model": {"minimax:M3": {"calls": 1, "fails": 0, "ms": 10}},
                       "tools": {}, "slowest_llm_ms": 10}}
        fallos = failures_in(tl)
        dom = dominant([f["kind"] for f in fallos])
        assert not is_excused(dom)
        aggregate_from_timeline(tl, mission_ok=False, excused=False, fallos=fallos)
        fila = model_ranking()[0]
        assert fila["missions_excused"] == 0 and fila["mission_success_rate"] == 0.0

    async def test_dos_acciones_de_la_misma_tool_no_se_suman_los_fallos_externos(self):
        """CORRECCIÓN DE LA REVISIÓN: agrupando por tool en vez de por
        `tool.action`, `search.search_web` y `search.search_news` se sumaban
        mutuamente sus fallos externos y `fails_external` podía superar a
        `fails` — una tasa de error negativa antes del clamp."""
        tl = {"events": [
            _ev("tool_call", name="search.search_web",
                detail={"failure_kind": "connection", "blame": "external", "tool": "search"}),
            _ev("tool_call", name="search.search_news",
                detail={"failure_kind": "connection", "blame": "external", "tool": "search"}),
        ], "summary": {"llm_by_model": {}, "tools": {
            "search.search_web": {"calls": 1, "fails": 1, "ms": 10},
            "search.search_news": {"calls": 1, "fails": 1, "ms": 10}}}}
        aggregate_from_timeline(tl, mission_ok=False, excused=True)
        for fila in tool_ranking():
            assert fila["fails_external"] == 1, fila
            assert fila["fails_external"] <= fila["fails"]
            assert fila["error_rate"] == 0.0, "la red no condena a la herramienta"

    async def test_una_tool_que_falla_de_verdad_si_sube_su_tasa(self):
        tl = {"events": [
            _ev("tool_call", name="document.read_pdf",
                detail={"failure_kind": "tool_error", "blame": "tool", "tool": "document"}),
        ], "summary": {"llm_by_model": {}, "tools": {
            "document.read_pdf": {"calls": 2, "fails": 1, "ms": 20}}}}
        aggregate_from_timeline(tl, mission_ok=True)
        fila = tool_ranking()[0]
        assert fila["fails_external"] == 0 and fila["error_rate"] == 0.5

    async def test_failure_stats_acumula_y_acota_los_ejemplos(self):
        f = [{"kind": "connection", "blame": "external", "component": "model:x:y",
              "model_key": "x:y", "tool": None, "event_key": None, "detail": "boom"}]
        for i in range(15):
            record_failures(f"mision-{i}", f)
        with SessionLocal() as s:
            fila = s.query(FailureStat).one()
        assert fila.count == 15
        assert len(fila.sample_mission_ids) == 10, "el ring de ejemplos está acotado"

        resumen = failure_summary()
        assert resumen["total"] == 15 and resumen["by_blame"]["external"] == 15

    async def test_lo_que_no_se_sabe_atribuir_se_ve(self):
        """El bucket `unknown` es un bucket más, a propósito: esconderlo daría
        una foto más bonita y menos cierta."""
        record_failures("m1", [{"kind": "unknown", "blame": "unknown",
                                "component": "?", "model_key": None, "tool": None,
                                "event_key": None, "detail": ""}])
        assert failure_summary()["by_blame"]["unknown"] == 1


# ===========================================================================
# 4 · Propuestas de configuración — a las 3, no a las 2, y sin applier
# ===========================================================================
class TestConfigFix:
    def _gap(self, n, kind="config_missing", blame="config"):
        record_failures("m-x", [{"kind": kind, "blame": blame,
                                 "component": "tool:search", "model_key": None,
                                 "tool": "search", "event_key": None,
                                 "detail": "añade una API key de SerpAPI en Ajustes"}] * n)

    async def test_a_las_dos_no_molesta_a_las_tres_si(self):
        self._gap(2)
        assert config_gaps() == []
        self._gap(1)
        huecos = config_gaps()
        assert len(huecos) == 1 and huecos[0]["count"] == 3
        assert huecos[0]["settings_tab"] == "conexiones"
        assert huecos[0]["dedup_key"] == "config:tool:search"

    async def test_una_api_key_caducada_tambien_es_accionable(self):
        """Consecuencia de mover `provider_auth` a la culpa "config": un 401
        repetido genera propuesta igual que una key ausente. Filtrar por culpa
        y no por un kind concreto es lo que lo hace posible."""
        self._gap(3, kind="provider_auth")
        huecos = config_gaps()
        assert len(huecos) == 1 and huecos[0]["kind"] == "provider_auth"

    async def test_un_fallo_del_modelo_no_genera_propuesta_de_configuracion(self):
        record_failures("m1", [{"kind": "model_reasoning", "blame": "model",
                                "component": "model:x:y", "model_key": "x:y",
                                "tool": None, "event_key": None, "detail": ""}] * 9)
        assert config_gaps() == []

    async def test_config_fix_no_tiene_applier_y_por_eso_no_se_puede_aplicar(self):
        """Configurar una API key es del usuario, no de Aithera. La garantía de
        L1 (sin applier no hay consolidación) hace que el panel ofrezca "Ir a
        Ajustes" en vez de "Aceptar" — y lo hace por construcción, no por una
        condición en la UI que alguien pueda olvidar."""
        from app.learner import registered_kinds

        assert "config_fix" not in registered_kinds()

    async def test_las_propuestas_no_se_duplican(self):
        from app.learner import proposal_service
        from app.learner.mission_learning import _propose_config_fixes

        self._gap(3)
        assert await _propose_config_fixes() == 1
        assert await _propose_config_fixes() == 0, "idempotente por dedup_key"
        abiertas = await proposal_service.pending(kind="config_fix")
        assert len(abiertas) == 1
        assert abiertas[0]["payload"]["settings_tab"] == "conexiones"
        assert abiertas[0]["risk"] == "low"
        for p in abiertas:                       # limpieza
            with SessionLocal() as s:
                from app.learner.models import LearnerProposal
                s.query(LearnerProposal).filter(LearnerProposal.id == p["id"]).delete()
                s.commit()


# ===========================================================================
# 5 · La migración (la lección de las 4 veces)
# ===========================================================================
class TestMigracionL2b:
    def test_toda_columna_de_l2b_esta_en_alguna_migracion(self):
        from pathlib import Path

        versiones = Path(__file__).resolve().parent.parent / "alembic" / "versions"
        corpus = "\n".join(p.read_text(encoding="utf-8")
                           for p in versiones.glob("*.py"))
        for modelo in (ModelStat, ToolStat, FailureStat):
            for col in modelo.__table__.columns:
                assert f'"{col.name}"' in corpus, (
                    f"{modelo.__tablename__}.{col.name} está en el ORM pero en "
                    f"ninguna migración — el desfase que rompió la app 4 veces")

    def test_la_migracion_nueva_encadena_y_no_edita_la_ya_aplicada(self):
        from pathlib import Path

        versiones = Path(__file__).resolve().parent.parent / "alembic" / "versions"
        nueva = (versiones / "c0d1e2f3a4b5_v11_learner_failures.py").read_text(encoding="utf-8")
        assert 'down_revision: Union[str, None] = "b9c0d1e2f3a4"' in nueva
        for col in ("failure_stats", "missions_excused", "fails_external"):
            assert col in nueva
        # Y la revisión ya aplicada no gana columnas nuevas en su CUERPO (su
        # docstring sí puede mencionarlas): editarla no la reejecutaría.
        vieja = (versiones / "b9c0d1e2f3a4_v11_learner_stats.py").read_text(encoding="utf-8")
        cuerpo = vieja.split('"""', 2)[-1]
        assert "missions_excused" not in cuerpo and "fails_external" not in cuerpo
