# tests/test_memory_context.py — Contexto con fuentes en el chat (V0.85 M4)
#
# Cubre: chat_service.build_system_prompt (preferencias legacy + memoria del
# MOS con atribucion + presupuesto de 300ms), chat_service.answer() (orden de
# persistencia, flag persist_chat_message), y la consolidacion real: /api/chat
# y el Gateway comparten la MISMA implementacion (doc 12 A4).
import asyncio

import pytest

from app.memory import MemoryType, memory_router
from app.services import chat_service

pytestmark = pytest.mark.skipif(
    not memory_router.healthy, reason="ChromaDB no disponible en el entorno de test"
)


def _fake_mel(monkeypatch, text="respuesta de prueba", ok=True, raises=False):
    """[E2] chat_service.answer llama al MEL (mel.complete), no a ai_manager.
    Este helper reemplaza el seam correcto (la API pública del MEL)."""
    import app.mel as mel
    from app.mel import ExecutionResult, ServedBy, Usage

    async def _complete(req):
        if raises:
            raise RuntimeError("proveedor caido")
        return ExecutionResult(
            text=text if ok else "", ok=ok,
            served_by=ServedBy("fake", "fake-model"), usage=Usage(tokens=7),
        )
    monkeypatch.setattr(mel, "complete", _complete)


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    import asyncio as _asyncio

    async def _clean():
        await memory_router.forget(MemoryType.PERSONAL, {"source": "test_context"})

    _asyncio.run(_clean())


# ======================================================================
# build_system_prompt
# ======================================================================

@pytest.mark.anyio
async def test_build_system_prompt_vacio_sin_mensaje():
    prompt = await chat_service.build_system_prompt("")
    assert prompt == chat_service.DEFAULT_SYSTEM_PROMPT


@pytest.mark.anyio
async def test_build_system_prompt_cita_fuente_de_memoria_mos():
    await memory_router.store(
        content="el usuario prefiere que le llamen Ale, no Alejandro",
        memory_type=MemoryType.PERSONAL,
        source="test_context",
        metadata={"kind": "preference_note"},
        dedup_key="ctx_test_1",
    )
    prompt = await chat_service.build_system_prompt("como debo llamar al usuario")
    assert "Memoria relevante (con fuente):" in prompt
    assert "test_context" in prompt  # atribucion de fuente presente
    assert "Ale" in prompt


@pytest.mark.anyio
async def test_build_system_prompt_respeta_presupuesto_de_latencia(monkeypatch):
    """[doc 07 §8] Si memory_router.context() excede 300ms, contexto vacio —
    el chat no espera. Se fuerza con un context() artificialmente lento."""
    async def _slow_context(*args, **kwargs):
        await asyncio.sleep(1.0)
        return "esto nunca deberia llegar al prompt"

    monkeypatch.setattr(memory_router, "context", _slow_context)

    import time
    t0 = time.monotonic()
    prompt = await chat_service.build_system_prompt("cualquier cosa")
    elapsed = time.monotonic() - t0

    assert elapsed < 0.5  # el timeout de 300ms protegio la llamada
    assert "esto nunca deberia llegar" not in prompt


# ======================================================================
# answer() — orden de persistencia + flags
# ======================================================================

@pytest.mark.anyio
async def test_answer_persiste_chat_message_por_defecto(monkeypatch, client):
    from app.db.database import SessionLocal
    from app.db.models import ChatMessage

    _fake_mel(monkeypatch, text="hola desde el test")

    before = SessionLocal()
    try:
        count_before = before.query(ChatMessage).count()
    finally:
        before.close()

    result = await chat_service.answer("mensaje de prueba unico xyz", channel="web")
    assert result.text == "hola desde el test"

    after = SessionLocal()
    try:
        count_after = after.query(ChatMessage).count()
        rows = after.query(ChatMessage).order_by(ChatMessage.id.desc()).limit(2).all()
    finally:
        after.close()
    assert count_after == count_before + 2
    contents = {r.content for r in rows}
    assert "mensaje de prueba unico xyz" in contents
    assert "hola desde el test" in contents


@pytest.mark.anyio
async def test_answer_persist_chat_message_false_no_escribe_sql(monkeypatch):
    from app.db.database import SessionLocal
    from app.db.models import ChatMessage

    _fake_mel(monkeypatch, text="respuesta de telegram")

    db = SessionLocal()
    try:
        count_before = db.query(ChatMessage).count()
    finally:
        db.close()

    result = await chat_service.answer(
        "mensaje via telegram", channel="telegram", persist_chat_message=False
    )
    assert result.text == "respuesta de telegram"

    db = SessionLocal()
    try:
        count_after = db.query(ChatMessage).count()
    finally:
        db.close()
    assert count_after == count_before  # nada nuevo en ChatMessage


@pytest.mark.anyio
async def test_answer_indexa_mensaje_de_usuario_aunque_la_ia_falle(monkeypatch):
    """[V0.6, preservado en la consolidacion] El mensaje del usuario se
    indexa ANTES de llamar a la IA: si la IA lanza, el mensaje no se pierde.
    El `store_conversation` del user va antes de `mel.complete` — un fallo
    catastrofico del MEL (que en produccion NO lanza, pero aqui se fuerza para
    validar el orden) propaga la excepcion tras haber indexado ya el mensaje."""
    _fake_mel(monkeypatch, raises=True)

    marker = "mensaje-que-debe-sobrevivir-al-fallo-de-ia"
    with pytest.raises(RuntimeError):
        await chat_service.answer(marker, channel="web", persist_chat_message=False)

    # Verificamos en la coleccion legacy 'conversations' (ChromaDB), no en SQL.
    from app.memory import memory_manager
    results = memory_manager.search_conversations(marker, n_results=5)
    assert any(marker in (r.get("content") or "") for r in results)


# ======================================================================
# Consolidacion: /api/chat y el Gateway comparten chat_service.answer()
# ======================================================================

@pytest.mark.anyio
async def test_endpoint_chat_delega_en_chat_service(monkeypatch, client):
    calls = []

    async def _fake_answer(message, *, channel="web", persist_chat_message=True):
        calls.append((message, channel, persist_chat_message))
        return chat_service.ChatAnswer(text="respuesta simulada", model="m", tokens=1)

    monkeypatch.setattr(chat_service, "answer", _fake_answer)

    r = client.post("/api/chat/", json={"message": "hola"})
    assert r.status_code == 200
    assert r.json()["response"] == "respuesta simulada"
    assert calls == [("hola", "web", True)]


@pytest.mark.anyio
async def test_gateway_handler_delega_en_chat_service_con_persist_false(monkeypatch):
    from app.gateway.gateway import chat_message_handler
    from app.gateway.envelope import MessageEnvelope

    calls = []

    async def _fake_answer(message, *, channel="web", persist_chat_message=True):
        calls.append((message, channel, persist_chat_message))
        return chat_service.ChatAnswer(text="", model=None, tokens=None)

    monkeypatch.setattr(chat_service, "answer", _fake_answer)

    envelope = MessageEnvelope(channel="telegram", user_ref="123", text="hola desde tg")
    result = await chat_message_handler(envelope)

    assert calls == [("hola desde tg", "telegram", False)]
    assert result == "(sin respuesta)"  # fallback propio del gateway cuando el texto viene vacio
