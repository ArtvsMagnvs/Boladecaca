# tests/test_audit_s11_grant.py — auditoría runtime, sesión S11 (doc 34 §S11)
#
# EL CASO QUE CIERRA (Cordyceps, mismo origen que S10): un agente con `document`
# NO asignado a un paso necesitaba leer un archivo local. El bucle denegaba la
# tool en silencio, el modelo seguía adelante con información genérica, y el
# documento final salió sin ninguna advertencia de que no se basaba en la
# fuente real. Nadie paró a preguntar "¿te doy la herramienta, o sigues sin
# ella?" — pese a que el mecanismo YA existe para acciones sensibles
# (`_ask_permission`/`ApprovalGate`): una tool AUSENTE de la whitelist caía por
# un camino más débil que una tool presente pero sensible.
#
# Lo que se blinda aquí:
#   1. Una tool REAL fuera de la whitelist del nodo abre un gate de CONCESIÓN
#      (`tool.grant.<id>`), UNA sola vez por tool y por ejecución del bucle.
#   2. Aprobada → se concede, se ejecuta, y el resultado es un éxito normal.
#   3. Rechazada → `limitations` la recuerda y la respuesta final lleva la
#      advertencia determinista (nunca en silencio).
#   4. Una tool INVENTADA (no existe en el ToolManager) sigue el camino de
#      siempre: denegación con motivo, SIN abrir ningún gate.
#   5. El perfil Autónomo (full) auto-concede al instante, con rastro real en
#      `approvals` — el gate nuevo no necesita entrada propia en el catálogo
#      de permisos (D-1: "cualquier gate, presente o futuro").
#   6. LA FRONTERA DE SEGURIDAD (no pedida explícitamente por el doc, pero
#      necesaria): si la tool está fuera de `Authority.allowed_tools` (lo que
#      el AGENTE tiene permitido, R4) — no solo fuera de la whitelist de ESTE
#      nodo — NO es concedible: eso seguiría siendo la frontera de R4, y un
#      gate aquí la saltaría en silencio.
from __future__ import annotations

import json

import pytest

from app.automation import Approval, approval_gate
from app.db.database import Base, SessionLocal, engine as db_engine
from app.tie import toolloop
from app.tie.authority import Authority
from app.tools.tool_manager import tool_manager


@pytest.fixture(autouse=True)
def _clean_approvals():
    """[LOG-1] `approvals` es una tabla GLOBAL — limpiar en ambos extremos."""
    def _purge():
        s = SessionLocal()
        try:
            s.query(Approval).delete()
            s.commit()
        except Exception:
            s.rollback()
        finally:
            s.close()

    Base.metadata.create_all(bind=db_engine)
    _purge()
    yield
    _purge()


def _fake_mel(monkeypatch, responses: list[str]):
    """Mismo patrón que test_tie_toolloop.py: encola respuestas del modelo."""
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


class _FakeGate:
    """Gate de prueba en memoria (mismo patrón que test_tie_toolloop.py) — para
    los tests que no necesitan la BD real (todo salvo el de perfil full)."""
    def __init__(self, verdict: str):
        self.verdict = verdict            # "approved" | "rejected" | "pending"
        self.asked: list[dict] = []

    async def request_approval(self, **kwargs):
        self.asked.append(kwargs)
        return "gate-de-prueba"

    def get(self, gate_id):
        class _A:
            status = self.verdict
        return _A()

    async def expire(self, gate_id, note=""):
        if self.verdict == "pending":
            self.expired = getattr(self, "expired", [])
            self.expired.append(gate_id)
            self.verdict = "expired"
            return True
        return False


# ---------------------------------------------------------------------------
# 1-2. Tool real fuera de whitelist → gate de concesión, aprobado → se ejecuta
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_tool_real_fuera_de_whitelist_abre_gate_de_concesion(monkeypatch):
    """`process` es una tool REAL registrada; el nodo solo tiene `filesystem`
    pero el agente (Authority) SÍ tiene `process` permitida — el caso exacto
    de Cordyceps/NEW-5: el planner no se la dio al nodo pese a estar
    disponible para el agente."""
    # Concedida NO es lo mismo que ejecutada: `run()` "continúa el bucle" tras
    # el gate (diseño S11), así que el modelo tiene que RE-PEDIR la misma tool
    # en la siguiente vuelta, ahora que ya está en su catálogo — de ahí el
    # request repetido en la cola.
    _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "process", "action": "cpu_status", "params": {}}}),
        json.dumps({"tool": {"tool_id": "process", "action": "cpu_status", "params": {}}}),
        '{"answer": "la CPU está al 10%"}',
    ])
    gate = _FakeGate("approved")

    ejecutadas = []

    async def _spy(**kwargs):
        ejecutadas.append(kwargs)
        return {"success": True, "result": {"cpu_percent": 10}, "error": None}

    monkeypatch.setattr(tool_manager, "execute", _spy)

    res = await toolloop.run(
        instruction="dime cómo está la CPU", context="",
        allowed_tools=["filesystem"], tool_manager=tool_manager, max_iters=5,
        approval_gate=gate, approval_wait_s=5,
        authority=Authority(allowed_tools=["filesystem", "process"]),
    )

    assert len(gate.asked) == 1
    assert gate.asked[0]["kind"] == "tool.grant.process"
    assert ejecutadas, "tras conceder, la tool debe ejecutarse de verdad"
    assert res.ok, res.error
    assert res.limitations == []


@pytest.mark.anyio
async def test_gate_de_concesion_se_pregunta_una_sola_vez(monkeypatch):
    """Aunque el modelo insista, el gate de UNA tool concreta se abre UNA vez
    por ejecución del bucle — no una por cada reintento."""
    _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "process", "action": "cpu_status", "params": {}}}),
        json.dumps({"tool": {"tool_id": "process", "action": "cpu_status", "params": {}}}),
        json.dumps({"tool": {"tool_id": "process", "action": "cpu_status", "params": {}}}),
        '{"answer": "no he podido"}',
    ])
    gate = _FakeGate("rejected")

    await toolloop.run(
        instruction="dime cómo está la CPU", context="",
        allowed_tools=["filesystem"], tool_manager=tool_manager, max_iters=6,
        approval_gate=gate, approval_wait_s=5,
        authority=Authority(allowed_tools=["filesystem", "process"]),
    )

    assert len(gate.asked) == 1, "solo se pregunta una vez por tool en todo el bucle"


# ---------------------------------------------------------------------------
# 3. Rechazado → limitations + advertencia en la respuesta final (responder)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_gate_rechazado_deja_limitations_y_el_modelo_se_entera(monkeypatch):
    seen = _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "process", "action": "cpu_status", "params": {}}}),
        '{"answer": "no pude comprobar la CPU, pero el resto está hecho"}',
    ])
    gate = _FakeGate("rejected")

    res = await toolloop.run(
        instruction="dime cómo está la CPU", context="",
        allowed_tools=["filesystem"], tool_manager=tool_manager, max_iters=5,
        approval_gate=gate, approval_wait_s=5,
        authority=Authority(allowed_tools=["filesystem", "process"]),
    )

    assert "process" in res.limitations
    assert "NO CONCEDIDA" in seen[-1] or "no concedida" in seen[-1].lower()


@pytest.mark.anyio
async def test_responder_avisa_de_la_limitacion_en_la_respuesta_final(monkeypatch):
    """[Criterio de cierre] El caso Cordyceps: el resultado puede sonar a
    éxito completo, pero si algo se le negó, el usuario se entera SIEMPRE."""
    from app.tie import contracts
    from app.tie.responder import build

    m = contracts.Mission(id="m1", goal="comprobar la CPU", source="user")
    node = contracts.TaskNode(id="n1", goal="comprobar la CPU")
    node.state = contracts.NodeState.DONE
    node.result = {"output": "todo bien", "limitations": ["process"]}
    graph = contracts.TaskGraph(id="g1", mission_id="m1", nodes={"n1": node})

    # Fuerza el camino de plantilla determinista (sin tocar la síntesis LLM):
    # monkeypatchear a que falle simula "el LLM no está disponible" y basta
    # para comprobar que la nota se añade sobre CUALQUIER texto final.
    import app.tie.responder as responder_mod

    async def _boom(*a, **kw):
        return {"error": True, "response": ""}

    monkeypatch.setattr(responder_mod.router, "complete", _boom)

    text = await build(m, graph)
    assert "process" in text
    assert "incompleto" in text.lower() or "ojo" in text.lower()


# ---------------------------------------------------------------------------
# 4. Tool INVENTADA → sigue el camino de siempre, SIN abrir ningún gate
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_tool_inventada_no_abre_gate(monkeypatch):
    _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "no_existe_esta_tool", "action": "hacer_algo", "params": {}}}),
        '{"answer": "no disponible"}',
    ])
    gate = _FakeGate("approved")

    res = await toolloop.run(
        instruction="haz algo raro", context="",
        allowed_tools=["filesystem"], tool_manager=tool_manager, max_iters=3,
        approval_gate=gate, approval_wait_s=5,
    )

    assert gate.asked == [], "una tool inexistente NUNCA abre un gate de concesión"
    denegadas = [c for c in res.tool_calls if c.get("denied")]
    assert denegadas and "no existe" in denegadas[0]["reason"]


@pytest.mark.anyio
async def test_accion_invalida_de_tool_ya_permitida_no_abre_gate(monkeypatch):
    """Una tool que YA está en la whitelist del nodo, con una acción que no
    existe, NO es "concedible" (no hay nada que conceder): sigue el camino de
    denegación de siempre."""
    _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "filesystem", "action": "accion_rara", "params": {}}}),
        '{"answer": "no disponible"}',
    ])
    gate = _FakeGate("approved")

    await toolloop.run(
        instruction="haz algo raro", context="",
        allowed_tools=["filesystem"], tool_manager=tool_manager, max_iters=3,
        approval_gate=gate, approval_wait_s=5,
    )

    assert gate.asked == []


# ---------------------------------------------------------------------------
# 6. FRONTERA DE SEGURIDAD: fuera de Authority.allowed_tools → NO concedible
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_tool_fuera_de_authority_no_es_concedible(monkeypatch):
    """`process` existe de verdad, pero el AGENTE (Authority) nunca la tuvo
    permitida — un gate aquí saltaría la frontera de R4 en silencio. Debe
    seguir el camino de denegación normal, nunca un gate de concesión."""
    _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "process", "action": "cpu_status", "params": {}}}),
        '{"answer": "no disponible"}',
    ])
    gate = _FakeGate("approved")

    res = await toolloop.run(
        instruction="dime cómo está la CPU", context="",
        allowed_tools=["filesystem"], tool_manager=tool_manager, max_iters=3,
        approval_gate=gate, approval_wait_s=5,
        authority=Authority(allowed_tools=["filesystem"]),  # SIN "process"
    )

    assert gate.asked == [], "fuera de Authority.allowed_tools no debe abrir gate"
    assert res.limitations == []
    denegadas = [c for c in res.tool_calls if c.get("denied")]
    assert denegadas and "no está permitida" in denegadas[0]["reason"]


# ---------------------------------------------------------------------------
# 5. Perfil Autónomo (full) → auto-concede al instante, CON rastro real
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_perfil_autonomo_auto_concede_con_rastro(monkeypatch):
    from app.automation import permission_service

    monkeypatch.setattr(permission_service, "autonomy_is_full", lambda: True)
    _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "process", "action": "cpu_status", "params": {}}}),
        json.dumps({"tool": {"tool_id": "process", "action": "cpu_status", "params": {}}}),
        '{"answer": "la CPU está al 10%"}',
    ])

    async def _spy(**kwargs):
        return {"success": True, "result": {"cpu_percent": 10}, "error": None}

    monkeypatch.setattr(tool_manager, "execute", _spy)

    res = await toolloop.run(
        instruction="dime cómo está la CPU", context="",
        allowed_tools=["filesystem"], tool_manager=tool_manager, max_iters=5,
        approval_gate=approval_gate, approval_wait_s=5,   # el ApprovalGate REAL
        authority=Authority(allowed_tools=["filesystem", "process"]),
    )

    assert res.ok
    assert res.limitations == []
    # Rastro real en `approvals`: auto-aprobado, nunca silencioso (regla de A3b).
    s = SessionLocal()
    try:
        rows = s.query(Approval).filter(Approval.kind == "tool.grant.process").all()
        assert len(rows) == 1
        assert rows[0].status == "approved"
        assert "auto" in (rows[0].resolution_note or "")
    finally:
        s.close()
