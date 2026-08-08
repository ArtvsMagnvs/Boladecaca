# tests/test_product_v12.py — PRODUCT-CONTRACTS de la fase V1.2 (doc 27 §6)
#
# [Regla de la primera sesión, patrón L1/doc 27 §3] C1 escribe los contratos
# de TODA la fase. Son la definición ejecutable de su cierre: V1.2 no se
# cierra hasta que los 6 estén en verde SIN marcas.
#
# Estado al escribirse (C1):
#   1. una tool MCP jamás se ejecuta sin pasar el gate ....... VERDE (C1)
#   2. un servidor MCP caído no rompe el ToolManager ......... VERDE (C1)
#   3. misión con paralelismo no mezcla sesiones ............. EN ROJO
#      (xfail estricto: lo implementa T1 — olas paralelas del TIE v2; cuando
#       pase, el xfail REVIENTA la suite y obliga a quitar la marca en la
#       misma sesión — el flip es un acto deliberado, no una casualidad)
#   4. un modelo mal puntuado N veces baja en la cadena tras el
#      ciclo nocturno ..................................... EN ROJO (ML1)
#   5. una exploración jamás cambia el output del usuario .... EN ROJO (PE2)
#   6. una variante solo llega a la bandeja tras ganar en el
#      banco .............................................. EN ROJO (SE1)
#
# Nota de honestidad sobre los rojos: los contratos 4 y 6 apuntan a APIs que
# AÚN NO EXISTEN (el ciclo nocturno de MEL Learning; el torneo de variantes).
# La sesión que los implemente puede renombrar la API — el xfail estricto le
# obliga a tocar ESTE archivo a conciencia — pero el COMPORTAMIENTO afirmado
# (el orden de la cadena cambia; una mejora sin torneo ganado no llega a la
# bandeja) es el contrato y no se rebaja.
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import pytest

from app import mcp as mcp_service
from app.automation import permission_service
from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine
from app.db.models import Config
from app.tools.tool_manager import tool_manager

MINI_SERVER = str(Path(__file__).parent / "mcp_mini_server.py")


@pytest.fixture(autouse=True)
def _clean():
    """Config y orchestrator_traces son globales — limpiar en ambos extremos
    (LOG-1/S3), y dejar el perfil de autonomía en manual para que ningún test
    previo con `full` convierta el contrato nº 1 en un falso verde."""
    def _purge():
        s = SessionLocal()
        try:
            s.query(Config).filter(Config.key.like("mcp.%")).delete(
                synchronize_session=False)
            s.query(Config).filter(Config.key == "permission.mcp.use").delete(
                synchronize_session=False)
            s.commit()
        except Exception:
            s.rollback()
        finally:
            s.close()
        for tid in [t for t in list(tool_manager._tools)
                    if t.startswith(permission_service.MCP_TOOL_PREFIX)]:
            tool_manager.unregister(tid)
        mcp_service.drop_connection("contrato")
        mcp_service.drop_connection("caido")

    Base.metadata.create_all(bind=db_engine)
    _purge()
    perfil_previo = permission_service.get_catalog().profile
    permission_service.apply_profile("manual")
    yield
    _purge()
    try:
        permission_service.apply_profile(perfil_previo)
    except Exception:
        pass


def _fake_mel(monkeypatch, responses: list[str]):
    """Mismo patrón que test_audit_s11_grant.py: encola respuestas del modelo."""
    import app.mel as mel
    from app.mel import ExecutionResult, ServedBy, Usage

    queue = list(responses)

    async def _complete(req):
        text = queue.pop(0) if queue else '{"answer": "sin más que decir"}'
        return ExecutionResult(text=text, ok=True,
                               served_by=ServedBy("fake", "fake-model"), usage=Usage(tokens=1))

    monkeypatch.setattr(mel, "complete", _complete)


class _GateEspia:
    """Gate que RECHAZA y registra cada petición — para afirmar que el gate se
    abrió ANTES de cualquier ejecución."""
    def __init__(self):
        self.asked: list[dict] = []

    async def request_approval(self, **kwargs):
        self.asked.append(kwargs)
        return "gate-contrato"

    def get(self, gate_id):
        class _A:
            status = "rejected"
        return _A()


def _servidor_con_catalogo(name="contrato"):
    mcp_service.upsert_server(mcp_service.MCPServerConfig(
        name=name, transport="stdio", command=sys.executable,
        args=[MINI_SERVER], enabled=True))
    from app.mcp import store as _store
    _store.cache_tools(name, [{
        "name": "accion_externa", "description": "hace algo fuera",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    }])
    mcp_service.register_enabled_servers(tool_manager)


# ===========================================================================
# CONTRATO 1 (VERDE, C1): una tool MCP jamás se ejecuta sin pasar el gate
# ===========================================================================
@pytest.mark.anyio
async def test_contrato_1_tool_mcp_jamas_sin_gate(monkeypatch):
    """El bucle de tool-use REAL con una tool MCP real registrada: el modelo
    la pide, el gate se ABRE antes de ejecutar nada, y con el gate rechazado
    la tool NO se ejecuta. Con el permiso `mcp.use` apagado y perfil manual
    (fixture), no hay ningún atajo que la deje pasar."""
    from app.tie import toolloop

    _servidor_con_catalogo()
    _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "mcp_contrato", "action": "accion_externa",
                             "params": {}}}),
        '{"answer": "no me dieron permiso, no lo he ejecutado"}',
    ])
    gate = _GateEspia()

    ejecutadas = []
    _execute_real = tool_manager.execute

    async def _spy(tool_id, action, params, **kw):
        if tool_id.startswith(permission_service.MCP_TOOL_PREFIX):
            ejecutadas.append((tool_id, action))
        return await _execute_real(tool_id, action, params, **kw)

    monkeypatch.setattr(tool_manager, "execute", _spy)

    await toolloop.run(
        instruction="usa la acción externa", context="",
        allowed_tools=["mcp_contrato"], tool_manager=tool_manager,
        max_iters=4, approval_gate=gate,
    )

    assert gate.asked, "el gate DEBE abrirse para una acción MCP"
    assert gate.asked[0]["kind"] == "tool.mcp_contrato.accion_externa"
    assert ejecutadas == [], "rechazado el gate, la tool MCP no puede ejecutarse"


def test_contrato_1b_todo_el_catalogo_mcp_es_sensible():
    """La mitad estática del contrato: CUALQUIER acción de un proxy MCP entra
    al catálogo del bucle marcada `needs_approval` (tool y acción lo fuerzan
    por separado), y su permiso se traduce a `mcp.use` — fail-closed."""
    from app.tie import toolloop

    _servidor_con_catalogo()
    catalogo = toolloop.build_catalog(["mcp_contrato"], tool_manager)
    assert catalogo and all(e["needs_approval"] for e in catalogo)
    assert permission_service.permission_for_tool_action(
        "mcp_contrato", "accion_externa") == "mcp.use"
    assert not permission_service.is_tool_action_pre_authorized(
        "mcp_contrato", "accion_externa")


# ===========================================================================
# CONTRATO 2 (VERDE, C1): un servidor MCP caído no rompe el ToolManager
# ===========================================================================
@pytest.mark.anyio
async def test_contrato_2_servidor_caido_no_rompe_el_toolmanager():
    """Un servidor que muere al arrancar: su tool falla HONESTA (success
    False con motivo), y el resto del ToolManager sigue intacto — catálogo
    listable, otras tools ejecutables, cero excepciones hacia arriba."""
    mcp_service.upsert_server(mcp_service.MCPServerConfig(
        name="caido", transport="stdio", command=sys.executable,
        args=["-c", "import sys; sys.exit(3)"], enabled=True))
    mcp_service.register_enabled_servers(tool_manager)

    r = await tool_manager.execute("mcp_caido", "loquesea", {})
    assert r["success"] is False and r["error"]

    # El ToolManager entero sigue vivo: catálogo + otra tool real.
    assert any(t["tool_id"] == "mcp_caido" for t in tool_manager.tie_catalog())
    ok = await tool_manager.execute(
        "filesystem", "file_exists", {"path": "Desktop"})
    assert isinstance(ok, dict) and "success" in ok

    # Y el preflight (Sesión A) reporta el motivo en 1 ms, sin relanzar nada.
    proxy = tool_manager.get_tool("mcp_caido")
    conn = mcp_service.get_connection("caido")
    try:
        await conn.ensure_ready()
    except RuntimeError:
        pass
    assert proxy.preflight() and "caido" in proxy.preflight()


# ===========================================================================
# CONTRATO 3 (EN ROJO — lo implementa T1): misión con paralelismo no mezcla
# sesiones
# ===========================================================================
@pytest.mark.xfail(
    strict=True,
    reason="Lo implementa T1 (TIE v2, olas paralelas): dos nodos independientes "
           "deben ejecutarse EN PARALELO y cada AgentTask debe conservar su "
           "propio mission_id/sesión. Hoy el executor ejecuta uno por ola "
           "(V1.0, ola=1) — sin paralelismo real, este contrato no puede "
           "cumplirse. Al implementarlo, quitar esta marca EN LA MISMA sesión.")
@pytest.mark.anyio
async def test_contrato_3_paralelismo_no_mezcla_sesiones():
    from app.tie import (AgentResult, AgentRuntime, RuntimeHealth, TaskGraph,
                         TaskNode, executor, new_mission, register_runtime,
                         tracer)

    tiempos: dict[str, tuple[float, float]] = {}
    misiones_vistas: dict[str, str] = {}

    class _RuntimeLento(AgentRuntime):
        @property
        def capabilities(self):
            return {"chat"}

        async def execute_task(self, task, memory, tools, approval_gate):
            t0 = time.monotonic()
            await asyncio.sleep(0.35)
            tiempos[task.id] = (t0, time.monotonic())
            misiones_vistas[task.id] = getattr(task, "mission_id", None) or ""
            return AgentResult(task_id=task.id, success=True, output=f"ok {task.id}")

        async def stream_task(self, task, memory, tools, approval_gate):
            yield None

        async def health_check(self):
            return RuntimeHealth(available=True)

    register_runtime("lento-c1", _RuntimeLento())
    m = new_mission("contrato de paralelismo", source="user", channel="hub")
    trace_id = tracer.record_start(m, channel="hub")
    g = TaskGraph(id="g-par", mission_id=m.id, nodes={
        "a": TaskNode(id="a", goal="rama A", runtime="lento-c1"),
        "b": TaskNode(id="b", goal="rama B", runtime="lento-c1"),
    })
    tracer.record_plan(trace_id, g)
    try:
        await executor.run(g, m, trace_id=trace_id)
    finally:
        s = SessionLocal()
        try:
            s.query(OrchestratorTrace).filter(
                OrchestratorTrace.id == trace_id).delete()
            s.commit()
        finally:
            s.close()

    # Mitad 1 — PARALELISMO: dos nodos sin dependencia entre sí deben
    # solaparse en el tiempo (hoy: secuencial → no se solapan → ROJO).
    (a0, a1), (b0, b1) = tiempos["a"], tiempos["b"]
    assert a0 < b1 and b0 < a1, "los nodos independientes deben solaparse"
    # Mitad 2 — SIN MEZCLA: cada tarea vio SU misión.
    assert misiones_vistas["a"] == m.id and misiones_vistas["b"] == m.id


# ===========================================================================
# CONTRATO 4 (EN ROJO — lo implementa ML1): un modelo mal puntuado N veces
# baja en la cadena tras el ciclo nocturno
# ===========================================================================
@pytest.mark.xfail(
    strict=True,
    reason="Lo implementa ML1 (MEL Learning): un ciclo nocturno que consume "
           "mission_verdicts/model_stats y REORDENA la cadena de una capacidad "
           "cuando un modelo acumula N misiones juzgadas como fallo. La API "
           "aún no existe (`mel.apply_nightly_scoring`); ML1 puede renombrarla "
           "— tocando este archivo a conciencia — pero el comportamiento "
           "(la cadena CAMBIA con la evidencia) es el contrato.")
def test_contrato_4_modelo_mal_puntuado_baja_en_la_cadena():
    import app.mel as mel

    assert hasattr(mel, "apply_nightly_scoring"), \
        "ML1 debe exponer el ciclo nocturno de puntuación en el barrel del MEL"


# ===========================================================================
# CONTRATO 5 (EN ROJO — lo implementa PE2): una exploración jamás cambia el
# output del usuario
# ===========================================================================
@pytest.mark.xfail(
    strict=True,
    reason="Lo implementa PE2 (exploración en paralelo): `Authority` debe "
           "aceptar `shadow=True` y, bajo esa marca, el bucle debe BLOQUEAR "
           "toda acción con efectos (aunque el permiso esté pre-autorizado) — "
           "el usuario recibe siempre el output del camino fiable. Hoy "
           "Authority no tiene el campo.")
def test_contrato_5_exploracion_jamas_cambia_el_output():
    from app.tie.authority import Authority

    a = Authority(allowed_tools=["filesystem"], shadow=True)   # TypeError hoy
    assert a.shadow is True


# ===========================================================================
# CONTRATO 6 (EN ROJO — lo implementa SE1): una variante solo llega a la
# bandeja tras ganar en el banco
# ===========================================================================
@pytest.mark.xfail(
    strict=True,
    reason="Lo implementa SE1 (torneo de variantes): una propuesta de mejora "
           "de skill debe llegar a la bandeja SOLO con evidencia de haber "
           "ganado el torneo en el banco de evals (LC3 ya compara texto "
           "contra texto, pero su camino `verified=False` —sin tareas de "
           "ejemplo— todavía deja pasar variantes sin verificar; SE1 lo "
           "cierra con ejecución real en banco). API esperada en el barrel: "
           "`learner.run_variant_tournament`.")
def test_contrato_6_variante_solo_tras_ganar_el_banco():
    import app.learner as learner

    assert hasattr(learner, "run_variant_tournament"), \
        "SE1 debe exponer el torneo de variantes en el barrel del Learner"
