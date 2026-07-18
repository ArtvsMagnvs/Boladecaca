# tests/test_mel_migration.py — la migración de call-sites al MEL (E2, doc 22 §3·E2)
#
# Verifica que los call-sites migrados delegan DE VERDAD en `mel.complete`
# (no solo "no rompen"): con `mel.complete` mockeado se comprueba que cada uno
# pide la capacidad correcta y adapta el resultado. Un test aparte confirma que
# ya NO queda ningún `ai_manager.chat(` real fuera de `app/mel/registry.py`.
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.mel import Capability, ExecutionResult, ServedBy, Usage

APP_DIR = Path(__file__).resolve().parent.parent / "app"


def _fake_mel(monkeypatch, text="ok", ok=True, capture=None):
    """Mockea la API pública del MEL (mel.complete). `capture` recoge la
    capability de cada request para asertar el mapeo call-site→capacidad."""
    import app.mel as mel

    async def _complete(req):
        if capture is not None:
            capture.append(req.capability)
        return ExecutionResult(text=text if ok else "", ok=ok,
                               served_by=ServedBy("fake", "fake-model"), usage=Usage(tokens=3))
    monkeypatch.setattr(mel, "complete", _complete)


# ---------------------------------------------------------------------------
# El grep-cero: ningún ai_manager.chat( real fuera del registry (doc 22 E2 Done)
# ---------------------------------------------------------------------------
def test_ningun_call_site_usa_ai_manager_chat_directo():
    offenders: list[str] = []
    pattern = re.compile(r"ai_manager\.(chat|chat_stream)\s*\(")
    for py in APP_DIR.rglob("*.py"):
        if py.name == "registry.py" and py.parent.name == "mel":
            continue  # el registry SÍ habla con los proveedores (por diseño)
        text = py.read_text(encoding="utf-8", errors="ignore")
        # ignora líneas de comentario (documentación que menciona el patrón)
        for i, line in enumerate(text.splitlines(), 1):
            if pattern.search(line) and not line.lstrip().startswith("#"):
                offenders.append(f"{py.relative_to(APP_DIR.parent)}:{i}")
    assert not offenders, (
        "Quedan llamadas directas a ai_manager.chat( fuera del MEL:\n" + "\n".join(offenders)
    )


# ---------------------------------------------------------------------------
# router.py del TIE delega en mel.complete con la capability correcta
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_router_delega_en_mel_con_la_capability(monkeypatch):
    from app.tie import router

    caps: list = []
    _fake_mel(monkeypatch, text="respuesta", capture=caps)

    res = await router.complete("hola", capability="reason")
    assert res["response"] == "respuesta" and res["error"] is False
    assert caps == [Capability.REASON]


@pytest.mark.anyio
async def test_router_capability_invalida_cae_a_chat(monkeypatch):
    from app.tie import router

    caps: list = []
    _fake_mel(monkeypatch, capture=caps)
    await router.complete("x", capability="capacidad-inventada")
    assert caps == [Capability.CHAT]


# ---------------------------------------------------------------------------
# chat_service.answer → CHAT
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_chat_service_answer_pide_chat(monkeypatch):
    from app.services import chat_service

    caps: list = []
    _fake_mel(monkeypatch, text="hola soy aithera", capture=caps)
    ans = await chat_service.answer("hola", persist_chat_message=False)
    assert ans.text == "hola soy aithera"
    assert caps == [Capability.CHAT]


# ---------------------------------------------------------------------------
# email: triaje → CLASSIFY, ai_reply → DRAFT
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_email_triage_pide_classify(monkeypatch):
    from app.services import email_service

    caps: list = []
    _fake_mel(monkeypatch, text="urgente", capture=caps)
    cat = await email_service.llm_triage("Reunión mañana", "jefe@empresa.com", "es urgente")
    assert cat == "urgente"
    assert caps == [Capability.CLASSIFY]


@pytest.mark.anyio
async def test_email_ai_reply_pide_draft(monkeypatch):
    from app.services import email_service

    caps: list = []
    _fake_mel(monkeypatch, text="Hola, gracias por tu mensaje.", capture=caps)
    out = await email_service.generate_ai_reply("responde amable", "a@b.com", "hola", "cuerpo")
    assert out == "Hola, gracias por tu mensaje."
    assert caps == [Capability.DRAFT]


# ---------------------------------------------------------------------------
# summarizer → SUMMARIZE con policy_override economy (job de fondo barato)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_summarizer_pide_summarize_offline_economy(monkeypatch):
    from app.memory import summarizer

    seen = {}
    import app.mel as mel

    async def _complete(req):
        seen["capability"] = req.capability
        seen["policy_override"] = req.policy_override
        return ExecutionResult(text="Resumen del día.", ok=True,
                               served_by=ServedBy("ollama", "llama3"), usage=Usage())
    monkeypatch.setattr(mel, "complete", _complete)

    data = {
        "date": "2026-07-18", "triaged_total": 3, "triage_counts": {"urgente": 1},
        "urgent_pending": {"count": 1}, "agenda": [], "conversations_count": 2,
    }
    out = await summarizer._try_llm_summary(data)
    assert out == "Resumen del día."
    assert seen["capability"] == Capability.SUMMARIZE
    assert seen["policy_override"] == "economy"  # no encarece el job nocturno


# ---------------------------------------------------------------------------
# email_tool: las 6 llamadas pasan por el helper _mel_chat (shape dict)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_email_tool_mel_chat_devuelve_shape_dict(monkeypatch):
    from app.tools import email_tool

    _fake_mel(monkeypatch, text="respuesta del tool")
    res = await email_tool._mel_chat("prompt", "system", capability="extract")
    assert res == {"response": "respuesta del tool", "error": False}

    _fake_mel(monkeypatch, ok=False)
    res2 = await email_tool._mel_chat("prompt", "system", capability="draft")
    assert res2 == {"response": "", "error": True}
