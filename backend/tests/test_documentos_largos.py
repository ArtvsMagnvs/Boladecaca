# tests/test_documentos_largos.py — [2026-08-04] ESCRIBIR UN DOCUMENTO LARGO
# ES POSIBLE.
#
# LA CAUSA RAÍZ (reportada por el usuario tras varios intentos fallidos del plan
# de Cordyceps, y confirmada en el código): el modelo emite su llamada a
# herramienta dentro de UN objeto JSON, y su respuesta tiene un techo de tokens
# de salida — 2048 en MiniMax (`max_completion_tokens`), 4096 en el resto. Un
# documento de 40.000 caracteres son ~12.000 tokens: NO CABE. La respuesta se
# corta a mitad del string JSON, el JSON queda inválido, y el reintento produce
# exactamente lo mismo porque el techo no cambia.
#
# No era mala suerte ni un modelo tonto: era imposible por construcción. Y
# explica el patrón exacto que el usuario observó — «otras veces sí escribe
# documentos»: los cortos caben, los largos JAMÁS.
#
# El arreglo tiene tres piezas y aquí se prueban las tres:
#   1. `filesystem.append_file` — la salida que no existía (write_file
#      sobrescribe, así que no había forma de escribir por partes).
#   2. `_looks_truncated` + mensaje ACCIONABLE — el bucle distingue "se cortó
#      por tamaño" de "respondió en prosa" y dice cómo salir del atolladero.
#   3. La regla en el system prompt, para que no llegue a fallar la 1.ª vez.
from __future__ import annotations

import json

import pytest

from app.tie import toolloop


# ===========================================================================
# 1 — append_file: la acción que faltaba
# ===========================================================================
@pytest.mark.anyio
async def test_append_file_escribe_por_partes(tmp_path, monkeypatch):
    """Un documento largo se construye en varias llamadas y queda ÍNTEGRO."""
    import app.tools.filesystem_tool as fs

    destino = tmp_path / "PLAN.md"
    monkeypatch.setattr(fs, "_is_path_allowed", lambda p: True)
    tool = fs.FilesystemTool()

    r1 = await tool.execute("write_file", {"path": str(destino), "content": "# Plan\n\n"})
    r2 = await tool.execute("append_file", {"path": str(destino), "content": "## Etapa 1\n"})
    r3 = await tool.execute("append_file", {"path": str(destino), "content": "## Etapa 2\n"})

    assert r1["success"] and r2["success"] and r3["success"]
    assert destino.read_text(encoding="utf-8") == "# Plan\n\n## Etapa 1\n## Etapa 2\n"
    # El tamaño acumulado se devuelve para que el modelo vea el avance real.
    assert r3["result"]["size"] > r2["result"]["size"] > r1["result"]["size"]
    assert r3["result"]["appended"] == len("## Etapa 2\n")


@pytest.mark.anyio
async def test_append_file_crea_el_archivo_si_no_existe(tmp_path, monkeypatch):
    import app.tools.filesystem_tool as fs

    monkeypatch.setattr(fs, "_is_path_allowed", lambda p: True)
    destino = tmp_path / "sub" / "nuevo.md"
    res = await fs.FilesystemTool().execute("append_file", {"path": str(destino), "content": "hola"})

    assert res["success"], res["error"]
    assert destino.read_text(encoding="utf-8") == "hola"


@pytest.mark.anyio
async def test_append_file_respeta_la_frontera_de_paths(tmp_path, monkeypatch):
    """No-regresión de seguridad: la MISMA validación que write_file. Una
    acción nueva de escritura no puede abrir un agujero."""
    import app.tools.filesystem_tool as fs

    monkeypatch.setattr(fs, "_is_path_allowed", lambda p: False)
    res = await fs.FilesystemTool().execute(
        "append_file", {"path": str(tmp_path / "x.md"), "content": "no"})

    assert not res["success"]
    assert "fuera de zonas permitidas" in res["error"]


def test_append_file_esta_en_el_catalogo_y_pide_confirmacion():
    """Escribir es sensible: tiene que pasar por el ApprovalGate igual que
    write_file, y el modelo tiene que poder verla en el catálogo."""
    import app.tools.filesystem_tool as fs

    acciones = {a["id"]: a for a in fs.FilesystemTool().list_actions()}
    assert "append_file" in acciones
    assert acciones["append_file"]["requires_confirmation"] is True
    # La descripción tiene que ENSEÑAR el patrón: sin esto el modelo no sabe
    # que existe una salida para los documentos largos.
    assert "largo" in acciones["append_file"]["description"].lower()
    assert "largo" in acciones["write_file"]["description"].lower()


# ===========================================================================
# 2 — Detección del truncamiento y consejo accionable
# ===========================================================================
@pytest.mark.parametrize("texto", [
    # El caso real: JSON de un write_file que se corta a mitad del contenido.
    '{"tool": {"tool_id": "filesystem", "action": "write_file", "params": '
    '{"path": "C:/x/PLAN.md", "content": "# Plan\\n\\n## Etapa 0\\n\\nSesión 0.1 — bootstrap',
    '{"tool": {"tool_id": "document", "action": "write_docx", "params": {"blocks": [{"type"',
    '  {"tool": {"tool_id": "filesystem", "action": "append_file"',
])
def test_detecta_una_respuesta_cortada_a_medias(texto):
    assert toolloop._looks_truncated(texto)


@pytest.mark.parametrize("texto", [
    # JSON completo y válido: no está truncado.
    '{"tool": {"tool_id": "filesystem", "action": "list_dir", "params": {"path": "C:/x"}}}',
    '{"answer": "he terminado"}',
    # Prosa: es OTRO fallo (el modelo no siguió el formato), no truncamiento.
    "Voy a escribir el documento ahora mismo.",
    "",
    # Llaves dentro de texto, pero balanceadas.
    '{"answer": "el objeto {a: 1} es un ejemplo"}',
])
def test_no_confunde_prosa_ni_json_completo_con_truncamiento(texto):
    assert not toolloop._looks_truncated(texto)


def _fake_mel(monkeypatch, responses: list[str]):
    import app.mel as mel
    from app.mel import ExecutionResult, ServedBy, Usage

    seen: list[str] = []
    queue = list(responses)

    async def _complete(req):
        seen.append(req.prompt)
        text = queue.pop(0) if queue else '{"answer": "listo"}'
        return ExecutionResult(text=text, ok=True,
                               served_by=ServedBy("fake", "f"), usage=Usage(tokens=1))

    monkeypatch.setattr(mel, "complete", _complete)
    return seen


class _TM:
    def tie_catalog(self, include_internal: bool = True):
        return [{"tool_id": "filesystem", "actions": [
            {"id": "write_file", "description": "escribe", "params": {"path": "string"},
             "requires_confirmation": False},
            {"id": "append_file", "description": "añade", "params": {"path": "string"},
             "requires_confirmation": False},
        ]}]

    def get_tool(self, tool_id):
        return object() if tool_id == "filesystem" else None

    async def execute(self, tool_id, action, params, allowed_tools=None, timeout=None):
        return {"success": True, "result": {"size": 100}, "error": None}


@pytest.mark.anyio
async def test_el_bucle_le_dice_como_salir_del_atolladero(monkeypatch):
    """LA REGRESIÓN DEL FALLO REAL. Antes, ante una respuesta cortada el bucle
    repetía 'responde SOLO con JSON' — inútil, porque el modelo SÍ estaba
    escribiendo JSON: el problema era el tamaño. Se quedaba en bucle hasta
    agotarse ('5 vueltas sin ninguna herramienta ejecutada con éxito').
    Ahora se le dice el problema real y la salida concreta."""
    cortada = ('{"tool": {"tool_id": "filesystem", "action": "write_file", "params": '
               '{"path": "C:/x/PLAN.md", "content": "# Plan enorme que se corta aqui')
    seen = _fake_mel(monkeypatch, [
        cortada,
        json.dumps({"tool": {"tool_id": "filesystem", "action": "write_file",
                             "params": {"path": "C:/x/PLAN.md", "content": "# Plan\n"}}}),
        json.dumps({"tool": {"tool_id": "filesystem", "action": "append_file",
                             "params": {"path": "C:/x/PLAN.md", "content": "## Etapa 1\n"}}}),
        '{"answer": "documento escrito por partes"}',
    ])

    res = await toolloop.run(instruction="escribe el plan maestro", context="",
                             allowed_tools=["filesystem"], tool_manager=_TM(), max_iters=10)

    # El consejo llegó al modelo, y es el ACCIONABLE (no el genérico).
    prompt_tras_el_corte = seen[1]
    assert "se CORTÓ" in prompt_tras_el_corte
    assert "append_file" in prompt_tras_el_corte
    assert "POR PARTES" in prompt_tras_el_corte
    # Y el trabajo salió adelante.
    assert res.ok, res.error
    acciones = [c.get("action") for c in res.tool_calls]
    assert "write_file" in acciones and "append_file" in acciones


@pytest.mark.anyio
async def test_una_respuesta_en_prosa_sigue_recibiendo_su_consejo_de_siempre(monkeypatch):
    """No-regresión: el otro fallo (el modelo contesta en prosa) NO debe
    recibir el consejo de los documentos largos, que no viene a cuento."""
    seen = _fake_mel(monkeypatch, [
        "Claro, ahora mismo lo hago.",
        '{"tool": {"tool_id": "filesystem", "action": "write_file", "params": {"path": "x"}}}',
        '{"answer": "hecho"}',
    ])

    await toolloop.run(instruction="escribe algo", context="",
                       allowed_tools=["filesystem"], tool_manager=_TM(), max_iters=10)

    assert "responde SOLO con JSON" in seen[1]
    assert "append_file" not in seen[1].split("HERRAMIENTAS DISPONIBLES")[-1].split("ERROR")[-1]


# ===========================================================================
# 3 — La regla preventiva y el rastro de entregable
# ===========================================================================
def test_el_system_prompt_ensena_a_escribir_por_partes():
    """Que el modelo lo sepa ANTES de estrellarse: el consejo reactivo cuesta
    una vuelta entera del bucle."""
    p = toolloop._SYSTEM_PROMPT
    assert "LÍMITE DE TAMAÑO" in p
    assert "append_file" in p
    assert "write_file" in p


def test_append_file_cuenta_como_entregable():
    """Sin esto, la Sesión B descartaría por 'no lo escribió nadie' un
    documento escrito por partes — justo el caso que este fix habilita: todas
    las partes menos la primera son appends."""
    assert ("filesystem", "append_file") in toolloop._DELIVERABLE_ACTIONS
    assert toolloop._deliverable_target(
        "filesystem", "append_file", {"path": "C:/x/PLAN.md"}) == "C:/x/PLAN.md"
