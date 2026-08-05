# tests/test_agente_cli.py — [2026-08-04] LOS AGENTES CLI TRABAJAN EN LA CARPETA
# DEL PROYECTO CON SUS PROPIAS HERRAMIENTAS.
#
# Corrección de diseño pedida por el usuario: Claude Code y Codex no son
# "modelos de chat lentos", son AGENTES completos. Meterlos en el bucle de tools
# de Aithera es un agente dentro de otro agente — de ahí salían las respuestas
# "soy Claude Code, no tengo acceso a...". Lo correcto es delegarles la tarea
# ENTERA con `cwd` en la carpeta del proyecto.
#
# Contrato que se fija aquí:
#   1. Un modelo CLI se reconoce como tal (y uno normal, no).
#   2. Un agente con modelo CLI NO pasa por el TIE/bucle de tools.
#   3. Se le pide CODE (no AGENTIC) y se le pasa la carpeta del proyecto.
#   4. Sin carpeta asignada se le dice que no toque ficheros (nunca escribir a ciegas).
#   5. Un agente con modelo normal sigue yendo por el TIE — cero regresión.
from __future__ import annotations

import pytest

import app.mel as mel
from app.agents.agent_manager import agent_manager


# --- 1. Reconocimiento del modelo -----------------------------------------

@pytest.mark.parametrize("key,esperado", [
    ("claude_code:opus", True),
    ("claude_code:sonnet", True),
    ("codex:gpt-5.1-codex", True),
    ("minimax:MiniMax-M2.7-highspeed", False),
    ("ollama:llama3", False),
    (None, False),
    ("", False),
])
def test_reconoce_los_agentes_cli(key, esperado):
    assert mel.is_cli_agent_model(key) is esperado


# --- 2/3. El agente CLI recibe la tarea entera y la carpeta ----------------

@pytest.mark.anyio
async def test_agente_cli_no_pasa_por_el_bucle_de_tools(monkeypatch):
    """Lo esencial: con un modelo CLI NO se crea misión del TIE. Si esto se
    rompe, volvemos al agente-dentro-de-agente que el usuario reportó."""
    visto = {}

    async def _fake_complete(req):
        visto["capability"] = req.capability
        visto["workdir"] = req.workdir
        visto["model_override"] = req.model_override
        visto["system_prompt"] = req.system_prompt or ""
        visto["prompt"] = req.prompt
        return mel.ExecutionResult(text="He creado el fichero.", ok=True)

    async def _no_llamar(*a, **k):
        raise AssertionError("un agente CLI NO debe crear una misión del TIE")

    monkeypatch.setattr(mel, "complete", _fake_complete)
    import app.tie as tie
    monkeypatch.setattr(tie, "submit_mission", _no_llamar)
    monkeypatch.setattr("app.agents.agent_manager._project_repo_path",
                        lambda pid: r"C:\proyectos\Cordyceps")

    res = await agent_manager._delegate_to_tie(
        task="crea un script de build",
        allowed_tools=["filesystem"],
        project_id=7,
        model="claude_code:opus",
    )

    assert res.state == "done"
    assert res.outcome == "He creado el fichero."
    # CODE, nunca AGENTIC: AGENTIC significa "usa el bucle de Aithera", que es
    # justo lo que no se quiere aquí.
    assert visto["capability"] == mel.Capability.CODE
    assert visto["model_override"] == "claude_code:opus"
    # LA carpeta del proyecto: sin esto trabajaría donde corra el backend.
    assert visto["workdir"] == r"C:\proyectos\Cordyceps"
    assert r"C:\proyectos\Cordyceps" in visto["system_prompt"]
    assert visto["prompt"] == "crea un script de build"


@pytest.mark.anyio
async def test_sin_carpeta_no_se_le_deja_tocar_ficheros(monkeypatch):
    """Un proyecto sin `repo_path` no debe acabar con el CLI escribiendo donde
    corra el backend: se le dice explícitamente que no modifique nada."""
    visto = {}

    async def _fake_complete(req):
        visto["workdir"] = req.workdir
        visto["system_prompt"] = req.system_prompt or ""
        return mel.ExecutionResult(text="ok", ok=True)

    monkeypatch.setattr(mel, "complete", _fake_complete)
    monkeypatch.setattr("app.agents.agent_manager._project_repo_path", lambda pid: None)

    await agent_manager._delegate_to_tie(
        task="dime qué opinas", allowed_tools=[], project_id=7,
        model="codex:gpt-5.1-codex",
    )
    assert visto["workdir"] is None
    assert "NO" in visto["system_prompt"] and "modifiques" in visto["system_prompt"]


@pytest.mark.anyio
async def test_el_fallo_del_cli_se_reporta_como_fallo(monkeypatch):
    """Si el CLI no devuelve nada, la ejecución tiene que quedar en `failed` con
    el motivo — nunca en `done` con la respuesta vacía."""
    async def _fake_complete(req):
        return mel.ExecutionResult(text="", ok=False, error="sesión de Claude caducada")

    monkeypatch.setattr(mel, "complete", _fake_complete)
    monkeypatch.setattr("app.agents.agent_manager._project_repo_path", lambda pid: None)

    res = await agent_manager._delegate_to_tie(
        task="haz algo", allowed_tools=[], project_id=1, model="claude_code:opus")
    assert res.state == "failed"
    assert "caducada" in res.outcome


# --- 5. No-regresión: un modelo normal sigue yendo por el TIE --------------

@pytest.mark.anyio
async def test_un_modelo_normal_sigue_yendo_por_el_tie(monkeypatch):
    llamado = {}

    async def _fake_submit(task, **kw):
        llamado["task"] = task
        llamado["model"] = kw.get("model")
        return "MISION"

    async def _no_llamar(req):
        raise AssertionError("un modelo normal no debe ir por el camino del CLI")

    import app.tie as tie
    monkeypatch.setattr(tie, "submit_mission", _fake_submit)
    monkeypatch.setattr(mel, "complete", _no_llamar)
    monkeypatch.setattr("app.agents.agent_manager._project_repo_path", lambda pid: None)

    res = await agent_manager._delegate_to_tie(
        task="revisa el inbox", allowed_tools=["email"], project_id=1,
        model="minimax:MiniMax-M2.7-highspeed")
    assert res == "MISION"
    assert llamado["model"] == "minimax:MiniMax-M2.7-highspeed"


# --- El contrato de transporte: la carpeta llega al proveedor --------------

@pytest.mark.anyio
async def test_el_registry_pasa_la_carpeta_al_proveedor(monkeypatch):
    """`workdir` tiene que llegar de verdad al provider — es lo que hace que
    Claude Code trabaje EN el repositorio del proyecto."""
    from app.mel import registry
    from app.mel.contracts import ModelRef

    recibido = {}

    class _FakeCli:
        model = "opus"

        async def generate(self, prompt, system_prompt=None, messages=None, workdir=None):
            recibido["workdir"] = workdir
            return {"response": "hecho"}

    monkeypatch.setattr(registry, "_instance_for", lambda ref: _FakeCli())
    ref = ModelRef(provider="claude_code", model="opus", is_local=False)
    out = await registry.execute(ref, "tarea", None, workdir="/proyecto/x")
    assert recibido["workdir"] == "/proyecto/x"
    assert out["response"] == "hecho"


@pytest.mark.anyio
async def test_un_proveedor_sin_carpeta_no_se_rompe(monkeypatch):
    """No-regresión: un proveedor HTTP no acepta `workdir` y eso NO es un fallo
    — se reintenta sin él (mismo patrón que el historial)."""
    from app.mel import registry
    from app.mel.contracts import ModelRef

    class _FakeHttp:
        model = "m"

        async def generate(self, prompt, system_prompt=None, messages=None):
            return {"response": "ok"}

    monkeypatch.setattr(registry, "_instance_for", lambda ref: _FakeHttp())
    ref = ModelRef(provider="minimax", model="m", is_local=False)
    out = await registry.execute(ref, "tarea", None, workdir="/proyecto/x")
    assert out["response"] == "ok"
