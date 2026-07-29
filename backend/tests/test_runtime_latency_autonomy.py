# tests/test_runtime_latency_autonomy.py — Optimización de latencia del runtime +
# modo Autónomo 100% (2026-07-20, petición directa del usuario).
#
# Dos fixes verificados aquí:
#   1. MODO AUTÓNOMO 100%: el perfil `full` auto-resuelve CUALQUIER gate/permiso,
#      presente o futuro, sin depender de toggles que puedan estar obsoletos
#      (el bug del navegador que seguía preguntando en Autónomo).
#   2. CAMINO DE ACCIÓN DIRECTA: una tarea mecánica ("abre YouTube y pon X",
#      "crea carpeta y archivo") NO pasa por el planner (2 llamadas al modelo
#      lento + grafo multi-nodo); un solo bucle de tool-use la resuelve con el
#      modelo rápido → mucha menos latencia, sin timeouts que rompan misiones.
from __future__ import annotations

import pytest

from app.tie.contracts import Intent, IntentType


# ---------------------------------------------------------------------------
# 1) MODO AUTÓNOMO 100%
# ---------------------------------------------------------------------------
@pytest.fixture
def _clean_profile():
    from app.db.database import Base, SessionLocal, engine as db_engine
    from app.db.models import Config
    Base.metadata.create_all(bind=db_engine)
    yield
    s = SessionLocal()
    try:
        s.query(Config).filter(Config.key == "autonomy_profile").delete()
        s.query(Config).filter(Config.key.like("permission.%")).delete(synchronize_session=False)
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


def test_autonomo_total_auto_aprueba_cualquier_gate(_clean_profile):
    """Con el perfil `full`, TODO gate se pre-autoriza — incluidos los que no
    existían cuando el usuario activó full, y hasta kinds inventados del futuro.
    Es el fix definitivo del bug del navegador que seguía preguntando."""
    from app.automation import permissions as P
    from app.db.database import SessionLocal

    db = SessionLocal()
    P._config_set(db, P._PROFILE_KEY, "full")
    db.commit()
    db.close()

    assert P.autonomy_is_full()
    # Gates del TIE (aunque sus toggles individuales estén OFF por config vieja):
    assert P.is_kind_pre_authorized("tie.plan")
    assert P.is_kind_pre_authorized("tie.node")
    assert P.is_kind_pre_authorized("tie.checkpoint")
    # Acción de tool sensible (el navegador del bug reportado):
    assert P.is_tool_action_pre_authorized("browser", "click")
    assert P.is_pre_authorized("browser.use")
    # Kind que aún no existe: en Autónomo también se auto-aprueba (a prueba de futuro).
    assert P.is_kind_pre_authorized("capacidad.que.no.existe.todavia")


def test_manual_sigue_preguntando_fail_closed(_clean_profile):
    """El fix no afloja el modo seguro: en manual (default), sin permisos, todo
    gate sigue preguntando."""
    from app.automation import permissions as P
    from app.db.database import SessionLocal

    db = SessionLocal()
    P._config_set(db, P._PROFILE_KEY, "manual")
    db.commit()
    db.close()

    assert not P.autonomy_is_full()
    assert not P.is_kind_pre_authorized("tie.plan")
    assert not P.is_pre_authorized("browser.use")
    assert not P.is_tool_action_pre_authorized("browser", "click")


@pytest.mark.anyio
async def test_autonomo_no_deja_aprobaciones_pendientes(_clean_profile):
    """End-to-end contra el ApprovalGate real: en Autónomo, un gate de navegador
    se auto-resuelve al instante CON rastro (nunca queda pending)."""
    from app.automation import approval_gate, permissions as P, Approval
    from app.db.database import SessionLocal

    db = SessionLocal()
    P._config_set(db, P._PROFILE_KEY, "full")
    db.commit()
    db.close()

    gate_id = await approval_gate.request_approval(
        kind="tie.node", title="paso con navegador",
        action_type="tie_resume", action_payload={"trace_id": "t", "node_id": "n1"},
    )
    appr = approval_gate.get(gate_id)
    assert appr.status == "approved", "Autónomo no debe dejar el gate pendiente"
    assert "pre-autorizado" in (appr.resolution_note or ""), "pero SÍ deja rastro (regla de oro A3b)"

    # limpieza
    db = SessionLocal()
    try:
        row = db.get(Approval, gate_id)
        if row:
            db.delete(row)
            db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 2) CAMINO DE ACCIÓN DIRECTA (latencia)
# ---------------------------------------------------------------------------
def _mk(**kw):
    return Intent(type=kw.pop("type"), goal="g", confidence=0.9, raw_text="x", **kw)


def test_tarea_mecanica_va_por_accion_directa():
    """Las tareas mecánicas de un solo encargo evitan el planner (rápidas)."""
    # abrir web + poner música
    assert _mk(type=IntentType.EXECUTE, requires_browser=True).is_direct_action
    # crear carpeta + archivo
    assert _mk(type=IntentType.CREATE, requires_tools=["filesystem"]).is_direct_action
    # controlar el escritorio
    assert _mk(type=IntentType.EXECUTE, requires_computer=True).is_direct_action


def test_tareas_complejas_NO_van_por_accion_directa():
    """Lo que de verdad necesita plan/orquestación sigue por su camino."""
    # necesita plan estructurado
    assert not _mk(type=IntentType.EXECUTE, requires_tools=["email"],
                   requires_planning=True).is_direct_action
    # multi-objetivo → orquestador
    assert not _mk(type=IntentType.EXECUTE, requires_browser=True,
                   objectives=["a", "b"]).is_direct_action
    # charla → camino corto, no directa
    assert not _mk(type=IntentType.CONVERSATIONAL).is_direct_action
    # query sin herramientas → camino corto
    assert not _mk(type=IntentType.QUERY).is_direct_action


def test_agentic_usa_modelo_rapido_no_reason():
    """El bucle de tool-use (una llamada POR ACCIÓN) debe enrutar a un modelo
    RÁPIDO, no al de razonamiento lento. Se comprueba en el catálogo del MEL:
    el score de AGENTIC debe seguir al de CLASSIFY (rápido), no al de REASON."""
    from app.mel.catalog import CATALOG
    from app.mel.contracts import Capability

    for provider, entry in CATALOG.items():
        scores = entry.get("default", {}).get("scores")
        if not scores:
            continue
        # AGENTIC ya no hereda de REASON; sigue el patrón de CLASSIFY (rápido).
        assert scores[Capability.AGENTIC] == scores[Capability.CLASSIFY], (
            f"{provider}: AGENTIC debe ir con CLASSIFY (rápido), no con REASON (lento)"
        )


@pytest.mark.anyio
async def test_toolloop_fuerza_politica_rapida_no_la_de_calidad(monkeypatch):
    """EL fix de los 15s/paso: el bucle NO debe usar la política de calidad del
    usuario (que puede ser opus/gpt), sino la política rápida de Settings.
    [2026-07-22] El default pasó de "economy" a "speed" (la política MEDIDA por
    mel/benchmark: el más rápido de esta máquina con suelo de calidad — barato
    no siempre es rápido: el local barato tardaba 100s+/paso, medido). Un
    modelo fijado (TIE_TOOL_MODEL) sigue teniendo máxima prioridad."""
    import json
    import sys
    import types
    from dataclasses import dataclass
    from typing import Any, Optional

    from app.tie import toolloop

    reqs = []
    mel = types.ModuleType("app.mel")

    class Capability:
        AGENTIC = "agentic"

    @dataclass
    class ExecutionRequest:
        capability: Any = None
        prompt: str = ""
        system_prompt: str = ""
        model_override: Optional[str] = None
        policy_override: Optional[str] = None
        context_tags: Optional[dict] = None
        fitness_exempt: bool = False

    @dataclass
    class _R:
        text: str
        ok: bool = True
        error: Optional[str] = None
        served_by: str = "fake"

    cola = [json.dumps({"tool": {"tool_id": "browser", "action": "open_url",
                                 "params": {"url": "youtube.com"}}}),
            '{"answer": "listo"}']

    async def _complete(req):
        reqs.append((req.policy_override, req.model_override))
        return _R(text=cola.pop(0) if cola else '{"answer": "x"}')

    mel.Capability, mel.ExecutionRequest, mel.complete = Capability, ExecutionRequest, _complete
    monkeypatch.setitem(sys.modules, "app.mel", mel)

    class _TM:
        def list_tools(self, include_internal=False):
            return [{"tool_id": "browser", "description": "nav", "actions": [
                {"id": "open_url", "description": "abre", "requires_confirmation": False}]}]

        def tie_catalog(self):
            # [P1, doc 34] mismo contrato que ToolManager real — ver la nota
            # gemela en test_audit_s3_browser.py.
            return self.list_tools(include_internal=True)

        def get_tool(self, tid):
            return object() if tid == "browser" else None

        async def execute(self, **kw):
            return {"success": True, "result": {"ok": True}, "error": None}

    res = await toolloop.run(instruction="abre youtube", context="",
                             allowed_tools=["browser"], tool_manager=_TM(), max_iters=3)
    assert res.ok
    # Todas las llamadas del bucle van por la política rápida (speed, la medida
    # por benchmark), NUNCA por la política de calidad del usuario.
    assert all(p == "speed" and m is None for p, m in reqs), reqs
