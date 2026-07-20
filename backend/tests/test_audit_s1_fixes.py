# tests/test_audit_s1_fixes.py — Regresiones de la Sesión 1 del plan de
# corrección post-auditoría v0.9.5 (doc 24 hallazgos A-1, A-2, D-1; doc 25 S1).
#
# Cada test protege UN contrato del producto que falló en producción:
#   A-1: un answer sin herramientas ejecutadas NUNCA es un éxito
#   A-2: el timeout de una aprobación la EXPIRA (no deja cadáveres en la UI)
#   D-1: el perfil de autonomía cubre los gates del TIE (tie.plan/node/checkpoint)
#
# Patrón: se mockea SOLO la frontera del LLM (mismo criterio que
# test_tie_toolloop.py / test_tie_e2e.py); ToolManager, gate y permisos reales.
from __future__ import annotations

import json

import pytest

from app.tie import toolloop
from app.tools.tool_manager import tool_manager


def _fake_mel(monkeypatch, responses: list[str]):
    import app.mel as mel
    from app.mel import ExecutionResult, ServedBy, Usage

    seen: list[str] = []
    queue = list(responses)

    async def _complete(req):
        seen.append(req.prompt)
        text = queue.pop(0) if queue else '{"answer": "sin más que decir"}'
        return ExecutionResult(text=text, ok=True,
                               served_by=ServedBy("fake", "fake-model"), usage=Usage(tokens=1))

    monkeypatch.setattr(mel, "complete", _complete)
    return seen


# ---------------------------------------------------------------------------
# A-1 — Grounding: sin herramienta ejecutada no hay éxito
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_a1_answer_inmediato_sin_tools_se_rechaza_y_se_le_exige_usarlas(monkeypatch):
    """EL fallo A de producción: el modelo respondía "hecho" en la iteración 1
    sin tocar ninguna herramienta y la misión terminaba `done`. Ahora el bucle
    rechaza ese answer y le exige fundamentarlo; si insiste sin herramientas,
    el resultado es un FALLO con su rastro."""
    seen = _fake_mel(monkeypatch, [
        '{"answer": "He abierto YouTube y puesto la canción."}',   # inventado
        '{"answer": "De verdad que sí, ya está puesta."}',          # insiste
        '{"answer": "Bueno, no lo hice."}',
    ])

    res = await toolloop.run(
        instruction="abre youtube y pon una canción", context="",
        allowed_tools=["filesystem"], tool_manager=tool_manager, max_iters=3,
    )

    assert not res.ok, "un answer sin ninguna tool ejecutada jamás puede ser éxito"
    assert res.tool_calls == []
    assert "sin fundamento" in (res.error or "")
    # El bucle le dijo explícitamente que estaba inventando:
    assert any("RECHAZADO" in p for p in seen[1:])


@pytest.mark.anyio
async def test_a1_answer_con_tool_exitosa_si_es_exito(monkeypatch):
    """El caso legítimo sigue intacto: tool real ejecutada → answer aceptado."""
    _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "filesystem", "action": "file_exists",
                             "params": {"path": "archivo_que_no_existe_9999.txt"}}}),
        '{"answer": "Comprobado: el archivo no existe."}',
    ])

    res = await toolloop.run(
        instruction="comprueba si existe el archivo", context="",
        allowed_tools=["filesystem"], tool_manager=tool_manager, max_iters=3,
    )

    assert res.ok
    assert any(c.get("ok") for c in res.tool_calls)


@pytest.mark.anyio
async def test_a1_todo_denegado_answer_es_fallo_honesto_no_bucle(monkeypatch):
    """Si el modelo LO INTENTÓ y todo le fue denegado, su answer es la
    explicación honesta del límite: se acepta al momento (sin forzar más
    vueltas) pero como FALLO, nunca como éxito."""
    _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "process", "action": "list_processes",
                             "params": {}}}),                       # fuera de whitelist
        '{"answer": "No tengo acceso a esa herramienta en este paso."}',
    ])

    res = await toolloop.run(
        instruction="lista los procesos", context="",
        allowed_tools=["filesystem"], tool_manager=tool_manager, max_iters=5,
    )

    assert not res.ok
    assert res.iterations == 2              # aceptado en cuanto respondió, sin bucle extra
    assert any(c.get("denied") for c in res.tool_calls)
    assert "acceso" in res.answer


# ---------------------------------------------------------------------------
# A-2 — El timeout expira la aprobación
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_a2_timeout_expira_la_aprobacion_en_bd_real():
    """Contra el ApprovalGate REAL (BD de tests): request → sin respuesta →
    expire() la deja en `expired` con nota, y un resolve posterior del usuario
    NO ejecuta nada (el claim atómico ya se consumió)."""
    from app.automation import approval_gate

    gate_id = await approval_gate.request_approval(
        kind="tool.email.send_email", title="test A-2",
        action_type="tie_tool_permission",
        action_payload={"tool_id": "email", "action": "send_email"},
    )
    appr = approval_gate.get(gate_id)
    assert appr.status == "pending"

    expired = await approval_gate.expire(gate_id, note="test: caducada")
    assert expired is True
    appr = approval_gate.get(gate_id)
    assert appr.status == "expired"
    assert "caducada" in (appr.resolution_note or "")

    # Aprobar DESPUÉS no revive nada: idempotencia del claim.
    result = await approval_gate.resolve(gate_id, approved=True)
    assert result.status == "expired"
    assert result.executed is False

    # Limpieza
    from app.db.database import SessionLocal
    from app.automation import Approval
    db = SessionLocal()
    try:
        row = db.get(Approval, gate_id)
        if row:
            db.delete(row)
            db.commit()
    finally:
        db.close()


@pytest.mark.anyio
async def test_a2_expire_pierde_la_carrera_si_el_usuario_resolvio():
    """Si el usuario resolvió justo antes del timeout, expire() devuelve False
    y el veredicto real se respeta."""
    from app.automation import approval_gate

    gate_id = await approval_gate.request_approval(
        kind="tool.email.send_email", title="test A-2 carrera",
        action_type="tie_tool_permission", action_payload={},
    )
    await approval_gate.resolve(gate_id, approved=False, note="rechazo del usuario")

    expired = await approval_gate.expire(gate_id)
    assert expired is False
    assert approval_gate.get(gate_id).status == "rejected"

    from app.db.database import SessionLocal
    from app.automation import Approval
    db = SessionLocal()
    try:
        row = db.get(Approval, gate_id)
        if row:
            db.delete(row)
            db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# D-1 — Los gates del TIE están gobernados por el catálogo de permisos
# ---------------------------------------------------------------------------
def test_d1_los_kinds_del_tie_estan_en_el_catalogo_o_mapeados():
    """Ningún kind de gate del TIE puede volver a ser fantasma: o es un permiso
    del catálogo, o tiene traducción declarada en _GATE_KIND_PERMISSION."""
    from app.automation.permissions import CATALOG, _GATE_KIND_PERMISSION

    ids = {p.id for p in CATALOG}
    for kind in ("tie.plan", "tie.node", "tie.checkpoint"):
        traducido = _GATE_KIND_PERMISSION.get(kind)
        assert traducido in ids, f"kind {kind!r} sin permiso real en el catálogo"

    # Los permisos nuevos existen y son gobernables.
    assert "tie.plan_approval" in ids
    assert "tie.checkpoint" in ids


def test_d1_perfil_full_incluye_los_permisos_de_mision():
    """El perfil "full" (Autónomo) debe cubrir los gates del TIE — el fallo D
    era exactamente que no los cubría."""
    from app.automation.permissions import PROFILES

    assert "tie.plan_approval" in PROFILES["full"]
    assert "tie.checkpoint" in PROFILES["full"]
    # balanced: solo el de riesgo bajo.
    assert "tie.checkpoint" in PROFILES["balanced"]
    assert "tie.plan_approval" not in PROFILES["balanced"]


@pytest.mark.anyio
async def test_d1_gate_del_plan_se_autoresuelve_con_el_permiso_activado():
    """Integración end-to-end del fix: con `tie.plan_approval` en ON, un gate
    kind="tie.plan" se auto-resuelve al instante CON rastro (la regla de oro de
    A3b intacta); con OFF vuelve a preguntar."""
    from app.automation import approval_gate
    from app.automation.permissions import set_permission
    from app.db.database import SessionLocal
    from app.automation import Approval

    creados = []
    try:
        set_permission("tie.plan_approval", True)
        gate_id = await approval_gate.request_approval(
            kind="tie.plan", title="plan de prueba", action_type="tie_plan",
            action_payload={"trace_id": "t-test", "mission_id": "m-test"},
        )
        creados.append(gate_id)
        appr = approval_gate.get(gate_id)
        assert appr.status == "approved"
        assert "pre-autorizado" in (appr.resolution_note or "")

        set_permission("tie.plan_approval", False)
        gate_id2 = await approval_gate.request_approval(
            kind="tie.plan", title="plan de prueba 2", action_type="tie_plan",
            action_payload={"trace_id": "t-test2", "mission_id": "m-test2"},
        )
        creados.append(gate_id2)
        assert approval_gate.get(gate_id2).status == "pending"
    finally:
        set_permission("tie.plan_approval", False)
        db = SessionLocal()
        try:
            for gid in creados:
                row = db.get(Approval, gid)
                if row:
                    db.delete(row)
            db.commit()
        finally:
            db.close()


def test_d1_kind_desconocido_sigue_fail_closed():
    """La puerta nueva no abre agujeros: un kind sin catálogo ni traducción
    jamás se pre-autoriza."""
    from app.automation.permissions import is_kind_pre_authorized

    assert is_kind_pre_authorized("tie.algo_inventado") is False
    assert is_kind_pre_authorized("") is False


# ---------------------------------------------------------------------------
# #10 — events.py retiene las tasks en vuelo
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_10_emit_retiene_referencia_de_la_task_hasta_terminar():
    import asyncio

    from app.core import events

    done = asyncio.Event()

    async def _handler(event):
        await asyncio.sleep(0.05)
        done.set()

    events.subscribe("audit.s1.test", _handler)
    try:
        events.emit("audit.s1.test", source="test", payload={})
        assert len(events._inflight) >= 1      # la referencia EXISTE mientras corre
        await asyncio.wait_for(done.wait(), timeout=2)
        await asyncio.sleep(0.01)              # deja correr el done_callback
        assert all(t.done() for t in events._inflight)  # y se suelta sola al acabar
    finally:
        events.unsubscribe("audit.s1.test", _handler)
