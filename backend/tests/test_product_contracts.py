# tests/test_product_contracts.py — LOS CONTRATOS DE PRODUCTO DE AITHERA
# (Auditoría v0.9.5 hallazgo E-1; plan de corrección doc 25 §S4)
#
# ═══════════════════════════════════════════════════════════════════════════
# POR QUÉ EXISTE ESTE ARCHIVO
# ═══════════════════════════════════════════════════════════════════════════
# Los 4 fallos que llegaron a producción en v0.9.5 (misión "completada" sin
# hacer nada, carpeta que nunca se creó, misión que mutó en otra distinta,
# permisos ignorados) pasaron LOS 751 TESTS de la suite. No fue mala suerte:
# los tests de módulo mockean la frontera adyacente, así que validan que cada
# pieza cumple SU contrato — pero nadie validaba el contrato del PRODUCTO, que
# vive en las costuras entre piezas.
#
# Este archivo es esa capa. Cada test enuncia una promesa que Aithera le hace
# al usuario y falla si se rompe, sin importar en qué módulo esté la causa.
#
# ═══════════════════════════════════════════════════════════════════════════
# REGLA DE MANTENIMIENTO (no negociable)
# ═══════════════════════════════════════════════════════════════════════════
# TODO bug que llegue a producción entra AQUÍ como test que falla, ANTES de
# arreglarse. Si un bug no se puede expresar como contrato roto en este
# archivo, es señal de que no se ha entendido todavía qué promesa rompió.
#
# ═══════════════════════════════════════════════════════════════════════════
# MÉTODO
# ═══════════════════════════════════════════════════════════════════════════
# UN solo fake: la frontera del LLM (`mel.complete`). Todo lo demás es real —
# ToolManager real escribiendo en disco de verdad, ApprovalGate real contra la
# BD, permisos reales, executor y responder reales. Sin red. Limpieza total
# por test (BD y disco).
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.automation import Approval, approval_gate
from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine
from app.tie import NodeState, handle, register_handlers, tracer
from app.tie import enricher as enricher_mod


# ---------------------------------------------------------------------------
# Andamiaje
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _clean_all():
    """BD limpia antes y después: estos tests miran filas concretas, y un
    residuo de otro archivo (SQLite reutiliza ids) los haría mentir — la
    lección de A4 (test_automation_mos.py)."""
    Base.metadata.create_all(bind=db_engine)
    register_handlers()
    enricher_mod._cache.clear()
    _wipe()
    yield
    _wipe()
    enricher_mod._cache.clear()


def _wipe():
    s = SessionLocal()
    try:
        s.query(OrchestratorTrace).delete()
        s.query(Approval).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


@pytest.fixture
def workdir():
    """Carpeta REAL dentro de HOME (FilesystemTool solo opera ahí), borrada
    al terminar pase lo que pase."""
    d = Path.home() / "_aithera_contracts_tmp"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


class _Env:
    def __init__(self, text, channel="electron"):
        self.text = text
        self.channel = channel
        self.user_ref = "u1"


def _no_context(monkeypatch):
    async def _enrich(*a, **k):
        return ""
    monkeypatch.setattr(enricher_mod, "enrich", _enrich)


def _llm(monkeypatch, *, classify: dict, plan: str | None = None,
         node_script: list[str] | None = None, summary: str = "resumen final"):
    """La ÚNICA frontera falsa. `node_script` son las respuestas del bucle de
    tool-use (capability AGENTIC) en orden — así se guionizan misiones que usan
    herramientas de verdad. Devuelve el registro de lo que vio el modelo."""
    import app.mel as mel
    from app.mel import Capability, ExecutionResult, ServedBy, Usage

    seen = {"prompts": [], "reason_calls": 0, "agentic_calls": 0}
    script = list(node_script or [])

    def _res(text):
        return ExecutionResult(text=text, ok=True, served_by=ServedBy("fake", "fake"),
                               usage=Usage(tokens=5))

    async def _complete(req):
        seen["prompts"].append((req.capability, req.prompt))
        cap = req.capability
        if cap == Capability.CLASSIFY:
            return _res(json.dumps(classify))
        if cap == Capability.REASON:
            seen["reason_calls"] += 1
            return _res(plan or "no soy un plan")
        if cap == Capability.AGENTIC:
            seen["agentic_calls"] += 1
            return _res(script.pop(0) if script else '{"answer": "no sé seguir"}')
        if cap == Capability.SUMMARIZE:
            return _res(summary)
        return _res("ok")

    monkeypatch.setattr(mel, "complete", _complete)
    return seen


_CLASSIFY_COMPLEX = {
    "type": "execute", "goal": "resumen del encargo para la interfaz",
    "domain": ["file"], "confidence": 0.95, "requires_planning": True,
    "requires_tools": ["filesystem"], "requires_browser": False,
    "requires_computer": False, "requires_automation": False,
    "requires_memory": False, "memory_types": [], "context_query": None,
    "model_capability": "reason",
}


def _plan(*nodes) -> str:
    return json.dumps({"nodes": list(nodes)})


def _node(nid, goal, *, deps=(), tools=(), approval=False):
    return {"id": nid, "goal": goal, "depends_on": list(deps),
            "tools": list(tools), "approval_required": approval}


def _trace_row():
    s = SessionLocal()
    try:
        return s.query(OrchestratorTrace).order_by(OrchestratorTrace.id.desc()).first()
    finally:
        s.close()


# ═══════════════════════════════════════════════════════════════════════════
# CONTRATO 1 — "Si digo que lo he hecho, lo he hecho"
# Fallo de origen: la misión de YouTube terminaba `done` sin ejecutar nada.
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.anyio
async def test_contrato_no_hay_exito_sin_herramientas_ejecutadas(monkeypatch, workdir):
    """Un nodo con herramientas cuyo modelo responde 'ya está' sin usarlas NO
    puede terminar DONE, y la respuesta final debe reconocerlo."""
    _no_context(monkeypatch)
    _llm(monkeypatch,
         classify=_CLASSIFY_COMPLEX,
         plan=_plan(_node("n1", f"Crea un archivo en {workdir}", tools=["filesystem"])),
         node_script=['{"answer": "Listo, ya lo he creado."}'] * 15,
         summary="No he podido crear el archivo.")

    out = await handle(_Env("crea un archivo de notas"))

    graph = tracer.load_graph(_trace_row().id)
    n1 = graph.nodes["n1"]
    assert n1.state == NodeState.FAILED, "sin tools ejecutadas no hay DONE"
    assert not list(workdir.iterdir()), "y en disco no hay nada, coherente"
    assert out, "el usuario recibe respuesta igualmente (nunca silencio)"


# ═══════════════════════════════════════════════════════════════════════════
# CONTRATO 2 — "Lo que pido es lo que se planifica"
# Fallo de origen: "videojuego del Rey León en Godot" → plan de un MMORPG.
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.anyio
async def test_contrato_el_plan_se_hace_sobre_mi_texto_no_sobre_una_reescritura(monkeypatch):
    """El planner debe ver el mensaje ORIGINAL, palabra por palabra — aunque el
    clasificador (modelo barato) lo haya reescrito en otra cosa."""
    _no_context(monkeypatch)
    clasificacion = dict(_CLASSIFY_COMPLEX)
    clasificacion["goal"] = "PLANIFICAR OTRA COSA COMPLETAMENTE DISTINTA"
    seen = _llm(monkeypatch, classify=clasificacion,
                plan=_plan(_node("n1", "paso uno"), _node("n2", "paso dos", deps=["n1"])))

    original = "crea un videojuego tipo el rey león con Godot, sin arte, solo bloques"
    await handle(_Env(original))

    from app.mel import Capability
    prompts_planner = [p for cap, p in seen["prompts"] if cap == Capability.REASON]
    assert prompts_planner, "el planner llegó a ejecutarse"
    assert original in prompts_planner[0], "el planner ve MI texto"
    assert "OTRA COSA" not in prompts_planner[0], "la reescritura NO sustituye al original"


@pytest.mark.anyio
async def test_contrato_la_memoria_no_secuestra_el_objetivo(monkeypatch):
    """El contexto del MOS entra como REFERENCIA, jerárquicamente por debajo del
    objetivo — no como una fuente más de la que el modelo pueda tirar."""
    from app.tie import planner
    from app.tie.contracts import Intent, IntentType

    seen = _llm(monkeypatch, classify=_CLASSIFY_COMPLEX,
                plan=_plan(_node("n1", "a"), _node("n2", "b", deps=["n1"])))

    async def _no_decision(**kw):
        class _D:
            id = "d1"
        return _D()
    import app.services.decision_service as ds
    monkeypatch.setattr(ds, "store_decision", _no_decision)

    await planner.plan(
        "haz un juego de plataformas del Rey León",
        Intent(type=IntentType.EXECUTE, goal="g", confidence=0.9),
        context="El usuario escribe novelas de fantasía y le encantan los MMORPG.",
    )

    from app.mel import Capability
    prompt = [p for cap, p in seen["prompts"] if cap == Capability.REASON][0]
    assert "SOLO REFERENCIA" in prompt
    assert prompt.index("Rey León") < prompt.index("novelas"), "objetivo antes que memoria"


# ═══════════════════════════════════════════════════════════════════════════
# CONTRATO 3 — "Si te doy permiso de antemano, no me preguntas"
# Fallo de origen: perfil Autónomo activo y aun así 5-6 confirmaciones.
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.anyio
async def test_contrato_perfil_autonomo_no_deja_aprobaciones_pendientes(monkeypatch):
    """Con el perfil "full" aplicado, una misión con un paso sensible NO deja
    ningún gate esperando: se auto-resuelven, siempre CON rastro de auditoría."""
    from app.automation.permissions import apply_profile

    _no_context(monkeypatch)
    _llm(monkeypatch, classify=_CLASSIFY_COMPLEX,
         plan=_plan(_node("n1", "preparar algo"),
                    _node("n2", "hacer algo sensible", deps=["n1"], approval=True)),
         node_script=[],
         summary="Hecho todo.")

    from app.services import chat_service

    class _A:
        text, model, tokens = "hecho", "m", 1

    async def _answer(message, **kw):
        return _A()
    monkeypatch.setattr(chat_service, "answer", _answer)

    apply_profile("manual")
    try:
        apply_profile("full")
        await handle(_Env("haz esto que toca algo sensible"))

        s = SessionLocal()
        try:
            pendientes = s.query(Approval).filter(Approval.status == "pending").all()
            resueltas = s.query(Approval).filter(Approval.status == "approved").all()
        finally:
            s.close()

        assert pendientes == [], "el modo autónomo NO debe preguntar"
        assert resueltas, "pero SÍ debe quedar rastro de lo que se autorizó"
        assert any("pre-autorizado" in (a.resolution_note or "") for a in resueltas)
    finally:
        apply_profile("manual")


@pytest.mark.anyio
async def test_contrato_perfil_manual_si_pregunta(monkeypatch):
    """El contrario del anterior: sin permisos concedidos, el plan sensible se
    para y espera — nada se ejecuta a mis espaldas."""
    from app.automation.permissions import apply_profile

    _no_context(monkeypatch)
    _llm(monkeypatch, classify=_CLASSIFY_COMPLEX,
         plan=_plan(_node("n1", "paso normal"),
                    _node("n2", "paso sensible", deps=["n1"], approval=True)))

    apply_profile("manual")
    out = await handle(_Env("haz algo sensible"))

    s = SessionLocal()
    try:
        pendientes = s.query(Approval).filter(Approval.status == "pending").all()
    finally:
        s.close()
    assert len(pendientes) == 1, "debe pedirme permiso"
    graph = tracer.load_graph(_trace_row().id)
    assert all(n.state == NodeState.PENDING for n in graph.nodes.values()), \
        "y NADA se ha ejecutado mientras espera"
    assert out


# ═══════════════════════════════════════════════════════════════════════════
# CONTRATO 4 — "Una aprobación que no sirve para nada, no se queda ahí"
# Fallo de origen: aprobabas tarde y el sistema lo ignoraba en silencio.
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.anyio
async def test_contrato_la_aprobacion_caducada_no_queda_pendiente(monkeypatch):
    """Si el paso siguió sin esperar más, su aprobación se marca `expired`:
    nunca `pending` (un botón que no hace nada al pulsarlo)."""
    from app.tie import toolloop
    from app.tools.tool_manager import tool_manager

    _llm(monkeypatch, classify=_CLASSIFY_COMPLEX, node_script=[
        json.dumps({"tool": {"tool_id": "email", "action": "send_email",
                             "params": {"to": "a@b.com", "subject": "s", "body": "b"}}}),
        '{"answer": "No pude enviarlo: el permiso caducó."}',
    ])

    res = await toolloop.run(
        instruction="envía un email", context="", allowed_tools=["email"],
        tool_manager=tool_manager, max_iters=3,
        approval_gate=approval_gate, approval_wait_s=1,
    )

    s = SessionLocal()
    try:
        estados = [a.status for a in s.query(Approval).all()]
    finally:
        s.close()

    assert estados and all(e != "pending" for e in estados), f"quedó pendiente: {estados}"
    assert "expired" in estados
    assert not res.ok, "y el paso no finge que salió bien"


# ═══════════════════════════════════════════════════════════════════════════
# CONTRATO 5 — "Si te pido un archivo, el archivo existe"
# Fallo de origen: la carpeta AITHERA GAME nunca se creó.
# ═══════════════════════════════════════════════════════════════════════════
@pytest.fixture
def puede_escribir():
    """El usuario ha autorizado escribir archivos (Ajustes → Permisos). Sin
    esto, `write_file` pide confirmación y no se ejecuta — comportamiento
    correcto que este propio fixture documenta."""
    from app.automation.permissions import set_permission

    set_permission("filesystem.write", True)
    yield
    set_permission("filesystem.write", False)


@pytest.mark.anyio
async def test_contrato_una_mision_de_archivos_deja_los_archivos_en_disco(
        monkeypatch, workdir, puede_escribir):
    """Herramientas REALES escribiendo en disco REAL: al terminar, el archivo
    está ahí y el nodo es DONE. Es el contrato que el fallo B rompía."""
    _no_context(monkeypatch)
    destino = workdir / "notas.txt"
    _llm(monkeypatch, classify=_CLASSIFY_COMPLEX,
         plan=_plan(_node("n1", f"Escribe un archivo en {destino}", tools=["filesystem"])),
         node_script=[
             json.dumps({"tool": {"tool_id": "filesystem", "action": "write_file",
                                  "params": {"path": str(destino), "content": "contenido real"}}}),
             '{"answer": "He creado el archivo notas.txt."}',
         ],
         summary="He creado el archivo que pediste.")

    await handle(_Env("créame un archivo de notas"))

    assert destino.exists(), "el archivo EXISTE de verdad"
    assert destino.read_text(encoding="utf-8") == "contenido real"
    graph = tracer.load_graph(_trace_row().id)
    assert graph.nodes["n1"].state == NodeState.DONE


@pytest.mark.anyio
async def test_contrato_si_la_herramienta_falla_la_mision_no_es_done(
        monkeypatch, workdir, puede_escribir):
    """El reverso: una escritura que falla de verdad (ruta fuera de HOME) no
    puede acabar en éxito. Nada de 'lo he hecho' cuando el disco dice que no."""
    _no_context(monkeypatch)
    _llm(monkeypatch, classify=_CLASSIFY_COMPLEX,
         plan=_plan(_node("n1", "Escribe fuera de HOME", tools=["filesystem"])),
         node_script=[
             json.dumps({"tool": {"tool_id": "filesystem", "action": "write_file",
                                  "params": {"path": "C:\\Windows\\aithera.txt", "content": "x"}}}),
             '{"answer": "No he podido: esa ruta está fuera de mi alcance."}',
         ],
         summary="No pude escribir ahí.")

    await handle(_Env("escribe en windows"))

    graph = tracer.load_graph(_trace_row().id)
    assert graph.nodes["n1"].state == NodeState.FAILED
    assert any(c.get("ok") is False for c in (graph.nodes["n1"].tool_calls or [])), \
        "el intento fallido queda auditado"


@pytest.mark.anyio
async def test_contrato_sin_permiso_no_se_escribe_nada(monkeypatch, workdir):
    """Descubierto AL ESCRIBIR ESTOS TESTS (S4, doc 25): sin el permiso
    `filesystem.write` concedido, una escritura ni siquiera se ejecuta — se
    pide confirmación y, sin respuesta, el paso sigue sin ella. Que el disco
    quede intacto es tan contrato como que se escriba cuando sí hay permiso."""
    _no_context(monkeypatch)
    prohibido = workdir / "prohibido.txt"
    _llm(monkeypatch, classify=_CLASSIFY_COMPLEX,
         plan=_plan(_node("n1", "Escribe un archivo", tools=["filesystem"])),
         node_script=[
             json.dumps({"tool": {"tool_id": "filesystem", "action": "write_file",
                                  "params": {"path": str(prohibido), "content": "x"}}}),
             '{"answer": "No tengo permiso para escribir."}',
         ],
         summary="No tengo permiso.")

    await handle(_Env("escribe un archivo"))

    assert not prohibido.exists(), "sin permiso, el disco queda INTACTO"
    graph = tracer.load_graph(_trace_row().id)
    assert graph.nodes["n1"].state == NodeState.FAILED, "y no se finge que salió"


# ═══════════════════════════════════════════════════════════════════════════
# CONTRATO 6 — "Si solo he hecho parte, te digo qué parte"
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.anyio
async def test_contrato_exito_parcial_se_cuenta_como_parcial(
        monkeypatch, workdir, puede_escribir):
    """Un plan con un paso que sale y otro que no: la respuesta entrega lo
    conseguido Y menciona lo que no. Nunca 'todo listo'."""
    _no_context(monkeypatch)
    destino = workdir / "ok.txt"
    _llm(monkeypatch, classify=_CLASSIFY_COMPLEX,
         plan=_plan(_node("n1", f"Escribe {destino}", tools=["filesystem"]),
                    _node("n2", "Escribe fuera de HOME", deps=["n1"], tools=["filesystem"])),
         node_script=[
             json.dumps({"tool": {"tool_id": "filesystem", "action": "write_file",
                                  "params": {"path": str(destino), "content": "ok"}}}),
             '{"answer": "primer archivo creado"}',
             json.dumps({"tool": {"tool_id": "filesystem", "action": "write_file",
                                  "params": {"path": "C:\\Windows\\no.txt", "content": "x"}}}),
             '{"answer": "el segundo no pude"}',
         ],
         summary="He creado el primero pero no pude con el segundo.")

    await handle(_Env("crea dos archivos"))

    graph = tracer.load_graph(_trace_row().id)
    estados = {n.id: n.state for n in graph.nodes.values()}
    assert estados["n1"] == NodeState.DONE
    assert estados["n2"] == NodeState.FAILED
    assert destino.exists(), "lo que sí salió, salió de verdad"
    fila = _trace_row()
    assert fila.state in ("done", "failed")


# ═══════════════════════════════════════════════════════════════════════════
# CONTRATO 7 — "Si te digo que pares, paras"
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.anyio
async def test_contrato_el_kill_switch_para_de_verdad(monkeypatch, workdir):
    """Cancelar una misión detiene la ejecución: los pasos que no habían
    empezado NO se ejecutan, y en disco no aparece nada nuevo."""
    import asyncio

    from app.tie import executor
    from app.tie.contracts import Mission, TaskNode
    from app.tie import graph as graph_mod
    from app.tie.runtime import AgentResult, AgentRuntime, RuntimeHealth, register_runtime

    creado = workdir / "no_deberia_existir.txt"
    arrancado = asyncio.Event()

    class _SlowRuntime(AgentRuntime):
        @property
        def capabilities(self):
            return {"chat"}

        async def execute_task(self, task, memory, tools, approval_gate):
            arrancado.set()
            await asyncio.sleep(30)          # el kill-switch debe cortar esto
            creado.write_text("no", encoding="utf-8")
            return AgentResult(task_id=task.id, success=True, output="tarde")

        async def stream_task(self, task, memory, tools, approval_gate):
            yield None

        async def health_check(self):
            return RuntimeHealth(available=True)

    register_runtime("slow-contract", _SlowRuntime())
    nodes = [TaskNode(id="n1", goal="paso lento", runtime="slow-contract"),
             TaskNode(id="n2", goal="paso siguiente", depends_on=["n1"], runtime="slow-contract")]
    g = graph_mod.build("m-kill", nodes, created_by="test")
    mission = Mission(id="m-kill", goal="larga", state="running", graph_ids=[g.id])
    trace_id = tracer.record_start(mission, channel="test")

    tarea = asyncio.create_task(executor.run(g, mission, trace_id=trace_id))
    await asyncio.wait_for(arrancado.wait(), timeout=5)
    executor.cancel("m-kill")
    await asyncio.wait_for(tarea, timeout=5)

    assert not creado.exists(), "el paso cancelado NO llegó a escribir"
    assert g.nodes["n2"].state != NodeState.DONE, "lo que venía después no se ejecutó"


# ═══════════════════════════════════════════════════════════════════════════
# CONTRATO 8 — "Nunca te quedas sin respuesta"
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.anyio
async def test_contrato_aunque_todo_falle_el_usuario_recibe_algo(monkeypatch):
    """El planner no logra plan, el LLM devuelve basura: el usuario recibe una
    respuesta útil igualmente. `handle` no lanza NUNCA (regla 11-B)."""
    _no_context(monkeypatch)
    _llm(monkeypatch, classify=_CLASSIFY_COMPLEX, plan="{{{ basura no parseable",
         node_script=['{"answer": "te respondo por el camino corto"}'] * 10,
         summary="")

    out = await handle(_Env("haz algo imposible de planificar"))
    assert isinstance(out, str) and out.strip(), "siempre hay respuesta"


@pytest.mark.anyio
async def test_contrato_capacidad_honesta_en_vez_de_mision_fantasma(monkeypatch):
    """Si el objetivo excede lo que Aithera puede hacer, lo dice a la primera —
    en vez de montar una misión que fingirá trabajar y no entregará nada."""
    _no_context(monkeypatch)
    _llm(monkeypatch, classify=_CLASSIFY_COMPLEX,
         plan=json.dumps({"cannot": "necesitaría ejecutar Godot, que no tengo"}))

    out = await handle(_Env("compila un juego con Godot"))

    assert "Godot" in out, "me explica QUÉ le falta"
    graph = tracer.load_graph(_trace_row().id)
    assert graph is None or all(n.state == NodeState.PENDING for n in graph.nodes.values()), \
        "y no ha ejecutado nada"
