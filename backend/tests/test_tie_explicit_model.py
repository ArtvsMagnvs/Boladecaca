# tests/test_tie_explicit_model.py — Override explícito en el TIE (E2b, doc 14 §3.5)
#
# El clasificador detecta `explicit_model`; el pipeline lo interpreta: scope=task
# → llega a ExecutionRequest.model_override (cierra Δ5); scope=unspecified →
# pregunta sin ejecutar; scope=project → set_project_override; nombre no resuelto
# → responde con las opciones reales. LLM y MEL mockeados (sin red).
import json

import pytest

from app.tie import pipeline
from app.tie.contracts import Intent, IntentType


def _fake_classifier(monkeypatch, explicit_model, *, itype="conversational", planning=False):
    """Sustituye intents.classify para devolver un Intent con el explicit_model dado."""
    async def _classify(text, *, channel=None):
        return Intent(
            type=IntentType(itype), goal=text, confidence=0.9,
            requires_planning=planning, explicit_model=explicit_model,
        )
    monkeypatch.setattr(pipeline.intents, "classify", _classify)


class _Env:
    def __init__(self, text, channel="web"):
        self.text = text
        self.channel = channel


# ---------------------------------------------------------------------------
# El clasificador REAL detecta explicit_model (LLM fake)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_clasificador_detecta_explicit_model(monkeypatch):
    from app.tie import intents

    payload = {
        "type": "query", "goal": "resume esto con DeepSeek", "confidence": 0.9,
        "explicit_model": {"name": "DeepSeek", "scope": "task"},
    }

    from app.tie import router

    async def _complete(prompt, *, system_prompt=None, capability="chat", **kw):
        return {"response": json.dumps(payload), "error": False}
    monkeypatch.setattr(router, "complete", _complete)

    intent = await intents.classify("resume esto con DeepSeek")
    assert intent.explicit_model == {"name": "DeepSeek", "scope": "task"}


@pytest.mark.anyio
async def test_clasificador_sin_modelo_deja_explicit_none(monkeypatch):
    from app.tie import intents, router

    async def _complete(prompt, *, system_prompt=None, capability="chat", **kw):
        return {"response": json.dumps({"type": "conversational", "goal": "resumen", "confidence": 0.9}),
                "error": False}
    monkeypatch.setattr(router, "complete", _complete)

    # [A·VOZ-2] input NO trivial para llegar al LLM (un saludo iría al precheck,
    # que también deja explicit_model=None, pero no ejercitaría el camino LLM).
    intent = await intents.classify("resume el informe del proyecto")
    assert intent.explicit_model is None


# ---------------------------------------------------------------------------
# scope=task → llega a ExecutionRequest.model_override (cierra Δ5)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_scope_task_llega_al_model_override_del_mel(monkeypatch):
    _fake_classifier(monkeypatch, {"name": "DeepSeek", "scope": "task"})

    # el MEL ve la petición: capturamos el model_override que le llega
    seen = {}
    import app.mel as mel
    from app.mel import ExecutionResult, ServedBy, Usage

    async def _mel_complete(req):
        seen["model_override"] = req.model_override
        return ExecutionResult(text="resumen con deepseek", ok=True,
                               served_by=ServedBy("deepseek", "deepseek-v4"), usage=Usage())
    monkeypatch.setattr(mel, "complete", _mel_complete)
    # resolve_model_name resuelve "DeepSeek" a un id concreto
    monkeypatch.setattr(mel, "resolve_model_name",
                        lambda name: type("R", (), {"key": "deepseek:deepseek-v4",
                                                    "provider": "deepseek", "model": "deepseek-v4"})())

    out = await pipeline.handle(_Env("resume esto con DeepSeek"))
    assert out == "resumen con deepseek"
    assert seen["model_override"] == "deepseek:deepseek-v4"   # Δ5 cerrado


# ---------------------------------------------------------------------------
# scope=unspecified → pregunta, NO ejecuta nada
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_scope_unspecified_pregunta_sin_ejecutar(monkeypatch):
    _fake_classifier(monkeypatch, {"name": "Claude", "scope": "unspecified"})

    import app.mel as mel
    called = {"mel": False}

    async def _mel_complete(req):
        called["mel"] = True
        from app.mel import ExecutionResult
        return ExecutionResult(text="NO DEBERÍA", ok=True)
    monkeypatch.setattr(mel, "complete", _mel_complete)
    monkeypatch.setattr(mel, "resolve_model_name",
                        lambda name: type("R", (), {"key": "anthropic:claude", "provider": "anthropic", "model": "claude"})())

    out = await pipeline.handle(_Env("usa Claude"))
    assert "solo para esta petición" in out or "a partir de ahora" in out
    assert called["mel"] is False   # no ejecutó nada este turno


# ---------------------------------------------------------------------------
# [PU3, doc 35, 2026-07-30] scope=unspecified + perfil Autónomo → NO pregunta,
# asume 'task' y avisa con una nota transparente (nunca en silencio).
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_scope_unspecified_bajo_autonomo_no_pregunta_asume_task(monkeypatch):
    from app.automation.permissions import apply_profile

    apply_profile("full")
    try:
        _fake_classifier(monkeypatch, {"name": "Claude", "scope": "unspecified"})

        import app.mel as mel
        called = {"mel": False}

        async def _mel_complete(req):
            called["mel"] = True
            called["model_override"] = req.model_override
            from app.mel import ExecutionResult, ServedBy, Usage
            return ExecutionResult(text="respuesta con claude", ok=True,
                                   served_by=ServedBy("anthropic", "claude"), usage=Usage())
        monkeypatch.setattr(mel, "complete", _mel_complete)
        monkeypatch.setattr(mel, "resolve_model_name",
                            lambda name: type("R", (), {"key": "anthropic:claude",
                                                        "provider": "anthropic", "model": "claude"})())

        out = await pipeline.handle(_Env("usa Claude"))

        assert called["mel"] is True, "bajo Autónomo SÍ ejecuta este turno, no pregunta"
        assert called["model_override"] == "anthropic:claude"
        # Nunca en silencio: la respuesta lleva la nota de qué se asumió y por qué.
        assert "Autónomo" in out or "autónomo" in out
        assert "respuesta con claude" in out
    finally:
        apply_profile("manual")


# ---------------------------------------------------------------------------
# nombre no resuelto → responde con las opciones reales, sin inventar
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_nombre_no_resuelto_responde_con_opciones(monkeypatch):
    _fake_classifier(monkeypatch, {"name": "ModeloInventado9000", "scope": "task"})

    import app.mel as mel
    monkeypatch.setattr(mel, "resolve_model_name", lambda name: None)
    monkeypatch.setattr(mel, "list_models", lambda: [{"label": "Ollama (Local)"}, {"label": "MiniMax"}])

    out = await pipeline.handle(_Env("usa ModeloInventado9000"))
    assert "ModeloInventado9000" in out
    assert "Ollama (Local)" in out and "MiniMax" in out   # dice qué SÍ hay


# ---------------------------------------------------------------------------
# scope=project → set_project_override con el project_id correcto
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_scope_project_fija_el_pin(monkeypatch):
    _fake_classifier(monkeypatch, {"name": "Claude", "scope": "project"}, itype="conversational")

    import app.mel as mel
    pinned = {}

    def _set(project_id, model_id, capability=None):
        pinned["project_id"] = project_id
        pinned["model_id"] = model_id
        return True
    monkeypatch.setattr(mel, "set_project_override", _set)
    monkeypatch.setattr(mel, "resolve_model_name",
                        lambda name: type("R", (), {"key": "anthropic:claude", "provider": "anthropic", "model": "claude"})())
    # store_decision es best-effort — que no falle
    from app.services import decision_service

    async def _store(**kw):
        return None
    monkeypatch.setattr(decision_service, "store_decision", _store)

    # entrada programática CON project_id (submit_mission salta el camino corto,
    # pero el pin se aplica antes de planificar)
    res = await pipeline._resolve_explicit_model(
        Intent(type=IntentType.CONVERSATIONAL, goal="todo con Claude", confidence=0.9,
               explicit_model={"name": "Claude", "scope": "project"}),
        project_id=55,
    )
    assert res["action"] == "reply"
    assert pinned == {"project_id": 55, "model_id": "anthropic:claude"}


@pytest.mark.anyio
async def test_scope_project_sin_proyecto_explica(monkeypatch):
    import app.mel as mel
    monkeypatch.setattr(mel, "resolve_model_name",
                        lambda name: type("R", (), {"key": "anthropic:claude", "provider": "anthropic", "model": "claude"})())

    res = await pipeline._resolve_explicit_model(
        Intent(type=IntentType.CONVERSATIONAL, goal="todo con Claude", confidence=0.9,
               explicit_model={"name": "Claude", "scope": "project"}),
        project_id=None,
    )
    assert res["action"] == "reply"
    assert "no está ligada a ningún proyecto" in res["text"]
