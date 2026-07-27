# tests/test_voice_latency.py — la voz responde con modelo rápido (A·VOZ-8, doc 32)
#
# Contrato: una respuesta de CHAT que viene de VOZ (conversational=True) se enruta
# por la política rápida (VOICE_CHAT_POLICY) vía policy_override; el chat de TEXTO
# (conversational=False) NO la usa — mantiene la política de calidad del usuario.
# Se mockea el seam del MEL (mel.stream) para capturar el ExecutionRequest real.
import pytest

from app.core.config import settings
from app.tie.runtime import AgentTask, NullRuntime


def _capture_stream(monkeypatch):
    """Sustituye mel.stream por un espía que guarda el ExecutionRequest y emite
    un token. Devuelve el dict con la request capturada."""
    cap = {}
    import app.mel as mel

    async def _fake_stream(req):
        cap["req"] = req
        yield "hola"

    monkeypatch.setattr(mel, "stream", _fake_stream)

    # build_system_prompt hace I/O de memoria; lo cortamos (no es lo que se prueba)
    from app.services import chat_service

    async def _fake_prompt(*a, **k):
        return "SYS"
    monkeypatch.setattr(chat_service, "build_system_prompt", _fake_prompt)
    monkeypatch.setattr(chat_service, "recent_turns", lambda *a, **k: [])
    return cap


@pytest.mark.anyio
async def test_voz_usa_politica_rapida(monkeypatch):
    cap = _capture_stream(monkeypatch)
    rt = NullRuntime()
    task = AgentTask(id="t1", instruction="hola", conversational=True)
    _ = [c async for c in rt.stream_task(task, memory=None, tools=None, approval_gate=None)]
    assert cap["req"].policy_override == settings.VOICE_CHAT_POLICY
    assert settings.VOICE_CHAT_POLICY   # no vacío por defecto ("speed")


@pytest.mark.anyio
async def test_texto_no_fuerza_politica(monkeypatch):
    cap = _capture_stream(monkeypatch)
    rt = NullRuntime()
    task = AgentTask(id="t2", instruction="hola", conversational=False)
    _ = [c async for c in rt.stream_task(task, memory=None, tools=None, approval_gate=None)]
    assert cap["req"].policy_override is None, "el chat de texto mantiene la política del usuario"


@pytest.mark.anyio
async def test_voz_con_modelo_explicito_respeta_el_del_usuario(monkeypatch):
    """Si el usuario nombró un modelo (model_hint), ese override manda: la política
    de voz no lo pisa."""
    cap = _capture_stream(monkeypatch)
    rt = NullRuntime()
    task = AgentTask(id="t3", instruction="usa deepseek", conversational=True,
                     model_hint="deepseek:deepseek-v4")
    _ = [c async for c in rt.stream_task(task, memory=None, tools=None, approval_gate=None)]
    assert cap["req"].policy_override is None      # no se fuerza la política de voz
    assert cap["req"].model_override is not None   # manda el modelo explícito
