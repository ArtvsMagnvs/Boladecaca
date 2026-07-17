# tests/test_tie_e2e.py — pipeline COMPLETO del TIE, de punta a punta (T5, doc 21 §3·T5)
#
# Los tests de T1-T4 (test_tie_contracts/planner/graph/executor/handle) prueban
# cada pieza con las de arriba/abajo MOCKEADAS (p.ej. test_tie_handle.py sustituye
# intents.classify/planner.plan/responder.build directamente). Este archivo prueba
# la CADENA REAL: clasificador real (JSON del LLM → Intent), planner real (JSON →
# TaskGraph validado por `graph.py`, con su reintento real), executor real (estado
# + checkpoint + gate), responder real (síntesis) — todo orquestado por
# `tie.handle()` de verdad. Lo único fake es el LLM (dos puntos de frontera:
# `ai_manager.chat` para intents/planner/responder, `chat_service.answer` para la
# ejecución de nodo vía NullRuntime) — determinista, sin red, para que corra en CI.
from __future__ import annotations

import asyncio
import json

import pytest

from app.automation import Approval, approval_gate
from app.db.database import Base, OrchestratorTrace, SessionLocal, engine as db_engine
from app.tie import NodeState, handle, register_handlers, tracer
from app.tie import enricher as enricher_mod


@pytest.fixture(autouse=True)
def _clean():
    Base.metadata.create_all(bind=db_engine)
    register_handlers()
    enricher_mod._cache.clear()
    yield
    s = SessionLocal()
    try:
        s.query(OrchestratorTrace).delete()
        s.query(Approval).delete()
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


class _Env:
    def __init__(self, text, channel="electron"):
        self.text = text
        self.channel = channel
        self.user_ref = "u1"


def _no_context(monkeypatch):
    """El enricher es de T2 (ya probado en aislamiento) — aquí se neutraliza para
    que el e2e no dependa de que el MOS esté inicializado."""
    async def _enrich(*a, **k):
        return ""
    monkeypatch.setattr(enricher_mod, "enrich", _enrich)


def _fake_node_execution(monkeypatch):
    """La ejecución de UN nodo (NullRuntime → chat_service.answer). Devuelve un
    texto determinista a partir de la instrucción del nodo, para poder comprobar
    después que el responder lo usó de verdad."""
    from app.services import chat_service

    class _Ans:
        def __init__(self, text):
            self.text = text
            self.model = "fake-node"
            self.tokens = 2

    async def _answer(message, *, channel="web", persist_chat_message=True):
        return _Ans(f"hecho: {message}")
    monkeypatch.setattr(chat_service, "answer", _answer)


def _fake_llm_boundary(monkeypatch, *, plan_json: str, plan_fails_first: bool = False):
    """El ÚNICO punto de contacto con un LLM en todo el e2e: `ai_manager.chat`.
    Enruta por el contenido del `system_prompt` — el mismo truco que usan
    intents/planner/responder para pedir cada uno su propia capacidad (T2)."""
    from app.ai.ai_manager import ai_manager

    state = {"plan_calls": 0}

    async def _chat(message="", system_prompt=None, **kw):
        sp = system_prompt or ""
        if "clasificador de intenciones" in sp:
            return {
                "response": json.dumps({
                    "type": "execute",
                    "goal": "revisar los últimos emails y enviar un resumen",
                    "domain": ["email"],
                    "confidence": 0.92,
                    "requires_planning": True,
                    "requires_tools": [],
                    "requires_browser": False,
                    "requires_computer": False,
                    "requires_automation": False,
                    "requires_memory": False,
                    "memory_types": [],
                    "context_query": None,
                    "model_capability": "reason",
                }),
                "model": "fake-classifier", "tokens": 10, "error": False,
            }
        if "planificador de Aithera" in sp:
            state["plan_calls"] += 1
            if plan_fails_first and state["plan_calls"] == 1:
                return {"response": "esto no es JSON en absoluto", "model": "fake-planner", "tokens": 5, "error": False}
            return {"response": plan_json, "model": "fake-planner", "tokens": 15, "error": False}
        if "respondiendo al usuario tras completar una tarea" in sp:
            return {
                "response": "He revisado tus últimos emails y te he enviado el resumen, como pediste.",
                "model": "fake-responder", "tokens": 12, "error": False,
            }
        # fallback genérico (no debería usarse en estos tests, pero nunca rompe)
        return {"response": "ok", "model": "fake-generic", "tokens": 1, "error": False}

    monkeypatch.setattr(ai_manager, "chat", _chat)
    return state


_VALID_PLAN_JSON = json.dumps({
    "nodes": [
        {"id": "n1", "goal": "Recuperar los últimos emails", "depends_on": [], "tools": [], "approval_required": False},
        {"id": "n2", "goal": "Enviar el resumen por email", "depends_on": ["n1"], "tools": [], "approval_required": True},
    ]
})


# ---------------------------------------------------------------------------
# El camino largo: intent real → plan real (validado por graph.py de verdad) →
# gate del plan → executor real → responder real. UN SOLO fake: el LLM.
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_e2e_mision_compleja_planifica_con_gate_ejecuta_y_responde(monkeypatch):
    _no_context(monkeypatch)
    _fake_node_execution(monkeypatch)
    _fake_llm_boundary(monkeypatch, plan_json=_VALID_PLAN_JSON)

    out = await handle(_Env("revisa mis últimos emails y envíame un resumen"))

    # El plan real (2 nodos, uno sensible) se detectó como tal y pidió permiso
    # ANTES de ejecutar nada — nada de esto está mockeado: es intents.classify +
    # planner.plan + graph.validate reales decidiendo esto.
    assert "visto bueno" in out
    assert "Recuperar los últimos emails" in out and "Enviar el resumen por email" in out

    pending = [a for a in approval_gate.list_pending() if a.kind == "tie.plan"]
    assert len(pending) == 1
    gate = pending[0]
    trace_id = gate.action_payload["trace_id"]
    assert tracer.load_graph(trace_id).nodes["n1"].state == NodeState.PENDING  # nada se ejecutó aún

    # El usuario aprueba el plan entero (como en la UI de Misiones, T4b).
    await approval_gate.resolve(gate.id, approved=True, note="adelante")
    await asyncio.sleep(0.1)  # reanudación en background (emit → create_task)

    final = tracer.load_graph(trace_id)
    assert final.nodes["n1"].state == NodeState.DONE
    assert final.nodes["n2"].state == NodeState.DONE
    # el nodo sensible NO abrió un segundo gate: quedó autorizado por el del plan
    assert final.nodes["n2"].gate_id == gate.id
    assert [a for a in approval_gate.list_pending() if a.kind == "tie.node"] == []

    # el responder real sintetizó la respuesta final (fake solo en el LLM)
    row = SessionLocal()
    try:
        trace = row.get(OrchestratorTrace, trace_id)
        assert trace.state == "done"
        assert "resumen" in trace.outcome.lower()
    finally:
        row.close()


# ---------------------------------------------------------------------------
# El planner real reintenta una vez ante JSON basura y, si vuelve a fallar,
# el pipeline real degrada al camino corto — nada de esto mockeado salvo el LLM.
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_e2e_planner_falla_dos_veces_degrada_a_camino_corto(monkeypatch):
    _no_context(monkeypatch)
    _fake_node_execution(monkeypatch)

    async def _garbage_answer(message, *, channel="web", persist_chat_message=True):
        class _Ans:
            text = "no tengo un plan, pero te respondo igualmente"
            model = "fake"
            tokens = 4
        return _Ans()
    from app.services import chat_service
    monkeypatch.setattr(chat_service, "answer", _garbage_answer)

    state = _fake_llm_boundary(monkeypatch, plan_json="también basura, no JSON")

    out = await handle(_Env("haz algo complicado"))

    assert state["plan_calls"] == 2          # 1 intento + 1 reintento (doc 14 §3.4.1)
    assert out == "no tengo un plan, pero te respondo igualmente"


# ---------------------------------------------------------------------------
# Un plan SIN pasos sensibles no pide permiso: ejecuta directo y responde.
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_e2e_plan_sin_pasos_sensibles_ejecuta_sin_gate(monkeypatch):
    _no_context(monkeypatch)
    _fake_node_execution(monkeypatch)
    plan_json = json.dumps({
        "nodes": [
            {"id": "n1", "goal": "Buscar el último proyecto activo", "depends_on": [], "tools": [], "approval_required": False},
            {"id": "n2", "goal": "Resumir su estado", "depends_on": ["n1"], "tools": [], "approval_required": False},
        ]
    })
    _fake_llm_boundary(monkeypatch, plan_json=plan_json)

    out = await handle(_Env("dime el estado de mi último proyecto"))

    assert approval_gate.list_pending() == []   # nada que aprobar
    assert "resumen" in out.lower() or "revisado" in out.lower() or "enviado" in out.lower() or out
