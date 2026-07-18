# tests/test_tie_toolloop.py — el bucle de tool-use del TIE (R1, doc 23 Δ2)
#
# El test más importante de este archivo es el PRIMERO: la regresión del
# hallazgo. Hasta R1, la misión "lista los archivos de mi carpeta" terminaba
# `done` con 0 tools ejecutadas y 5 archivos INVENTADOS. Aquí se comprueba con un
# ToolManager REAL sobre una carpeta REAL que los nombres que salen son los que
# hay en disco.
#
# Se mockea SOLO la frontera del LLM (`mel.complete`): el ToolManager, la
# whitelist, los timeouts y el filesystem son reales.
from __future__ import annotations

import json

import pytest

from app.tie import toolloop
from app.tools.tool_manager import tool_manager


def _fake_mel(monkeypatch, responses: list[str]):
    """Encola respuestas del modelo; cada llamada consume una. Devuelve la lista
    de prompts recibidos para poder asertar QUÉ vio el modelo."""
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
# LA REGRESIÓN DEL HALLAZGO
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_regresion_del_hallazgo_lista_archivos_reales(monkeypatch, tmp_path):
    """Antes de R1 esto devolvía 5 archivos inventados con 0 tools ejecutadas."""
    from pathlib import Path
    import os

    # Carpeta real DENTRO de HOME (FilesystemTool solo opera ahí).
    testdir = Path.home() / "_aithera_toolloop_test"
    testdir.mkdir(exist_ok=True)
    (testdir / "informe_real.txt").write_text("contenido", encoding="utf-8")
    (testdir / "datos_reales.csv").write_text("a,b", encoding="utf-8")

    try:
        seen = _fake_mel(monkeypatch, [
            json.dumps({"tool": {"tool_id": "filesystem", "action": "list_dir",
                                 "params": {"path": str(testdir)}}}),
            # 2.ª vuelta: el modelo ya tiene el resultado real y responde con él.
            '{"answer": "Hay 2 archivos: informe_real.txt y datos_reales.csv"}',
        ])

        res = await toolloop.run(
            instruction=f"Lista los archivos de {testdir} y dime cuántos hay",
            context="", allowed_tools=["filesystem"], tool_manager=tool_manager,
            max_iters=5,
        )

        assert res.ok, res.error
        # 1) La tool se ejecutó DE VERDAD.
        assert any(c["tool_id"] == "filesystem" and c["action"] == "list_dir" and c["ok"]
                   for c in res.tool_calls), res.tool_calls
        # 2) Los nombres REALES del disco llegaron al modelo como observación.
        observacion = seen[-1]
        assert "informe_real.txt" in observacion
        assert "datos_reales.csv" in observacion
    finally:
        for f in testdir.iterdir():
            f.unlink()
        testdir.rmdir()


# ---------------------------------------------------------------------------
# Límite de seguridad
# ---------------------------------------------------------------------------
def test_catalogo_excluye_las_acciones_sensibles():
    catalog = toolloop.build_catalog(["email"], tool_manager)
    pares = {(e["tool_id"], e["action"]) for e in catalog}
    assert ("email", "send_email") not in pares      # requiere confirmación
    assert ("email", "list_inbox") in pares          # lectura, sí


def test_catalogo_excluye_tools_enteras_que_piden_confirmacion():
    catalog = toolloop.build_catalog(["shell", "filesystem"], tool_manager)
    ids = {e["tool_id"] for e in catalog}
    assert "shell" not in ids            # requires_confirmation=True a nivel de tool
    assert "filesystem" in ids


@pytest.mark.anyio
async def test_accion_sensible_se_rechaza_sin_ejecutarse(monkeypatch):
    """Aunque el modelo la pida a pesar de no estar en el catálogo."""
    seen = _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "email", "action": "send_email",
                             "params": {"to": "x@y.com", "subject": "s", "body": "b"}}}),
        '{"answer": "No he podido enviarlo: necesita tu permiso."}',
    ])

    ejecutadas = []
    original = tool_manager.execute

    async def _spy(**kwargs):
        ejecutadas.append(kwargs)
        return await original(**kwargs)

    monkeypatch.setattr(tool_manager, "execute", _spy)

    res = await toolloop.run(
        instruction="envía un email", context="", allowed_tools=["email"],
        tool_manager=tool_manager, max_iters=3,
    )

    assert ejecutadas == []                                   # NO se ejecutó nada
    assert any(c.get("denied") for c in res.tool_calls)       # queda el rastro
    assert "permiso" in seen[-1] or "aprobación" in seen[-1]  # el motivo volvió al modelo


@pytest.mark.anyio
async def test_tool_fuera_de_la_whitelist_del_nodo_se_rechaza(monkeypatch):
    _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "process", "action": "list_processes", "params": {}}}),
        '{"answer": "no disponible"}',
    ])
    res = await toolloop.run(
        instruction="lista procesos", context="", allowed_tools=["filesystem"],
        tool_manager=tool_manager, max_iters=3,
    )
    denegadas = [c for c in res.tool_calls if c.get("denied")]
    assert denegadas and "no está permitida" in denegadas[0]["reason"]


def test_el_catalogo_solo_muestra_las_tools_del_nodo():
    catalog = toolloop.build_catalog(["filesystem"], tool_manager)
    assert {e["tool_id"] for e in catalog} == {"filesystem"}


# ---------------------------------------------------------------------------
# Honestidad y límites
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_sin_tools_disponibles_no_hay_bucle():
    res = await toolloop.run(
        instruction="algo", context="", allowed_tools=[], tool_manager=tool_manager,
        max_iters=3,
    )
    assert not res.ok and "sin herramientas" in res.error


@pytest.mark.anyio
async def test_agotar_iteraciones_falla_en_vez_de_inventar(monkeypatch):
    """El modelo nunca da una respuesta: el paso DEBE fallar, no fabricar una."""
    peticion = json.dumps({"tool": {"tool_id": "filesystem", "action": "file_exists",
                                    "params": {"path": "~/no_existe_xyz"}}})
    _fake_mel(monkeypatch, [peticion] * 10)

    res = await toolloop.run(
        instruction="comprueba algo", context="", allowed_tools=["filesystem"],
        tool_manager=tool_manager, max_iters=3,
    )
    assert not res.ok
    assert res.answer == ""            # NUNCA una respuesta inventada
    assert res.iterations == 3         # respetó el tope
    assert "3 iteraciones" in res.error


@pytest.mark.anyio
async def test_respeta_el_maximo_de_iteraciones(monkeypatch):
    peticion = json.dumps({"tool": {"tool_id": "filesystem", "action": "file_exists",
                                    "params": {"path": "~/x"}}})
    seen = _fake_mel(monkeypatch, [peticion] * 10)
    await toolloop.run(
        instruction="x", context="", allowed_tools=["filesystem"],
        tool_manager=tool_manager, max_iters=2,
    )
    assert len(seen) == 2              # exactamente 2 llamadas al modelo


@pytest.mark.anyio
async def test_el_fallo_de_una_tool_vuelve_al_modelo(monkeypatch):
    """Un error no corta el bucle: el modelo lo ve y puede buscar otra vía."""
    seen = _fake_mel(monkeypatch, [
        json.dumps({"tool": {"tool_id": "filesystem", "action": "read_file",
                             "params": {"path": "~/no_existe_en_absoluto.txt"}}}),
        '{"answer": "Ese archivo no existe."}',
    ])
    res = await toolloop.run(
        instruction="lee un archivo", context="", allowed_tools=["filesystem"],
        tool_manager=tool_manager, max_iters=3,
    )
    assert res.ok
    assert "FALLÓ" in seen[-1]
    assert any(c["ok"] is False for c in res.tool_calls)


@pytest.mark.anyio
async def test_respuesta_no_json_en_la_ultima_vuelta_se_acepta(monkeypatch):
    """Degradación: si el modelo contesta en prosa justo al final, mejor eso que
    perder su respuesta."""
    _fake_mel(monkeypatch, ["Esto es una respuesta en prosa, sin JSON."])
    res = await toolloop.run(
        instruction="x", context="", allowed_tools=["filesystem"],
        tool_manager=tool_manager, max_iters=1,
    )
    assert res.ok and "prosa" in res.answer


# ---------------------------------------------------------------------------
# Integración con el runtime
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_nullruntime_usa_el_bucle_cuando_el_nodo_tiene_tools(monkeypatch):
    from app.tie.runtime import AgentTask, NullRuntime

    _fake_mel(monkeypatch, ['{"answer": "hecho con herramientas"}'])
    task = AgentTask(id="t1", instruction="haz algo", tools=["filesystem"])
    res = await NullRuntime().execute_task(task, memory=None, tools=tool_manager,
                                           approval_gate=None)
    assert res.success and res.output == "hecho con herramientas"


@pytest.mark.anyio
async def test_nullruntime_sin_tools_sigue_por_el_chat(monkeypatch):
    """Cero regresión: un nodo sin tools se comporta exactamente como antes."""
    from app.services import chat_service
    from app.tie.runtime import AgentTask, NullRuntime

    async def _fake_answer(message, **kwargs):
        return chat_service.ChatAnswer(text="respuesta de chat", model="m", tokens=1)

    monkeypatch.setattr(chat_service, "answer", _fake_answer)

    task = AgentTask(id="t2", instruction="conversemos", tools=[])
    res = await NullRuntime().execute_task(task, memory=None, tools=tool_manager,
                                           approval_gate=None)
    assert res.success and res.output == "respuesta de chat"
