# tests/test_audit_s2s6_grounding.py — narración anclada en las TRES capas
# (S2·S6 del doc 34; fusión de las antiguas S2 [P2] y S6 [P6])
#
# LOS DOS FALLOS REALES QUE SE BLINDAN AQUÍ:
#
#   · 25-jul (campaña 00) — el email SE ENVIÓ (tool_call con message_id) y el
#     chat dijo "está preparado pero NO se ha enviado, necesito tu
#     confirmación". No había ninguna aprobación pendiente donde confirmarlo:
#     el texto se inventó. Y el 26-jul dijo LA MISMA frase con el gate
#     realmente abierto — la misma frase en los dos casos opuestos demuestra
#     que el texto no se derivaba del estado.
#   · 27-jul (campaña 01) — el camino corto, que no tiene NINGUNA herramienta,
#     citó 5 fuentes web nunca visitadas, describió una estructura de carpetas
#     inventada y resumió un documento sin leerlo.
#
# El único fake es la frontera del LLM. El resto (patrones, consolidator,
# responder, runtime) es código real.
from __future__ import annotations

import pytest

from app.core import grounding
from app.orchestrator.consolidator import consolidate
from app.orchestrator.contracts import Objective, OrchestrationRun
from app.tie import responder
from app.tie.contracts import Mission, NodeState, TaskGraph, TaskNode


# ===========================================================================
# 1) Los patrones — positivos, y sobre todo NEGATIVOS
# ===========================================================================
# El riesgo real de esta sesión no es no detectar: es detectar de más y meter
# una coletilla de honestidad en una respuesta perfectamente normal.

@pytest.mark.parametrize("texto", [
    "He enviado el email a Ana.",
    "Ya he creado el archivo notas.txt en tu carpeta",
    "He visitado la web y dice que la versión estable es la 3.14",
    "El email ha sido enviado correctamente",
    "Acabo de guardar el documento",
    "he leido el GDD del proyecto y trata sobre un juego de terror",
    "I sent the email to your address",
    "The file has been created",
])
def test_detecta_accion_realizada(texto):
    assert grounding.claims_completed_action(texto)


@pytest.mark.parametrize("texto", [
    # verbos COGNITIVOS: pensar/entender no exige ninguna herramienta
    "He pensado que sería mejor usar Python para esto.",
    "He entendido tu pregunta, te explico.",
    # acción sobre la propia conversación, no sobre el mundo
    "He leído tu mensaje y creo que te refieres a otra cosa.",
    "I read your message carefully before answering",
    # explicación normal, sin ninguna afirmación de acción
    "Un bucle for en Python se escribe: for x in lista:",
    "Tu proyecto Cordyceps tiene 3 tareas abiertas.",
])
def test_no_marca_texto_normal(texto):
    assert not grounding.claims_completed_action(texto)


@pytest.mark.parametrize("texto", [
    "Está preparado pero necesito tu confirmación para enviarlo",
    "Falta tu aprobación",
    "Queda pendiente de tu permiso",
    "waiting for your approval",
    "Necesito que lo confirmes antes de seguir",
])
def test_detecta_aprobacion_pendiente(texto):
    assert grounding.claims_pending_approval(texto)


@pytest.mark.parametrize("texto", [
    "He enviado el email, el ID del mensaje es 19f9b127",
    "Te dejo el resumen del proyecto: son 3 hitos.",
])
def test_no_ve_aprobacion_donde_no_la_hay(texto):
    assert not grounding.claims_pending_approval(texto)


def test_detecta_promesa_sin_cumplir():
    """El caso T02/H1 de la campaña 01: 'voy a intentar leerlo…' y el stream
    se corta ahí, sin ejecutar nada y sin decir que no pudo."""
    assert grounding.claims_future_action("Voy a leer ese archivo para buscar el dato")
    assert grounding.claims_future_action("Déjame comprobar el estado del proyecto")
    assert grounding.claims_future_action("let me check that file")


def test_promesa_cumplida_no_cuenta():
    """Narrar el proceso NO es prometer en falso: si después de anunciarlo
    cuenta lo que encontró, el texto está bien."""
    assert not grounding.claims_future_action(
        "Voy a leer el archivo... Lo he leído y dice: hola mundo."
    )


# ===========================================================================
# 2) Consolidator — CERO llamadas al modelo, en cualquier número de objetivos
# ===========================================================================
def _run(objectives, message="haz varias cosas"):
    return OrchestrationRun(id="r1", user_message=message, objectives=objectives)


@pytest.mark.anyio
async def test_consolidator_no_llama_nunca_al_modelo(monkeypatch):
    """La reescritura por LLM era la que inventó el 'falta tu confirmación'
    del 25-jul. Ya no existe: si alguien la reintroduce, este test revienta."""
    import app.mel as mel

    async def _boom(*a, **k):
        raise AssertionError("el consolidator NO debe llamar al modelo (S2·S6)")

    monkeypatch.setattr(mel, "complete", _boom)

    objs = [
        Objective(id="o1", goal="enviar el email", state="done",
                  outcome="Email enviado a losmagnoviajes@gmail.com, ID 19f9b127"),
        Objective(id="o2", goal="crear el proyecto", state="done",
                  outcome="Proyecto Aitherusiom creado con 6 agentes"),
        Objective(id="o3", goal="abrir YouTube", state="failed", error="sin red"),
    ]
    text = await consolidate(_run(objs))

    # Los outcomes que el responder ya redactó llegan ENTEROS al usuario.
    assert "19f9b127" in text
    assert "Aitherusiom" in text
    assert "sin red" in text


@pytest.mark.anyio
async def test_consolidator_un_objetivo_devuelve_su_outcome():
    """No regresión: con 1 objetivo se comportaba ya así, y sigue igual."""
    objs = [Objective(id="o1", goal="a", state="done", outcome="ya está hecho")]
    assert await consolidate(_run(objs)) == "ya está hecho"


# ===========================================================================
# 3) Responder — el caso del email, y su contrario
# ===========================================================================
def _graph(nodes):
    return TaskGraph(id="g1", mission_id="m1", nodes={n.id: n for n in nodes})


def _fake_llm(monkeypatch, texto):
    """Sustituye la frontera del LLM del responder (router.complete)."""
    async def _complete(prompt, system_prompt=None, capability=None, **kw):
        return {"response": texto, "error": None}
    monkeypatch.setattr(responder.router, "complete", _complete)


@pytest.mark.anyio
async def test_email_enviado_no_puede_decir_que_falta_confirmacion(monkeypatch):
    """EL caso del 25-jul. El paso se completó y no hay ningún gate abierto:
    un texto que diga 'necesito tu confirmación' es falso y se descarta."""
    _fake_llm(monkeypatch, "Está preparado pero necesito tu confirmación para enviarlo.")

    mission = Mission(id="m1", goal="enviar un email a Ana")
    nodo = TaskNode(id="n1", goal="enviar el email", state=NodeState.DONE,
                    result={"output": "Email enviado, ID 19f9b127f79cbdac"})
    text = await responder.build(mission, _graph([nodo]))

    assert "confirmación" not in text.lower()
    assert "19f9b127f79cbdac" in text      # sale la plantilla, con el hecho real


@pytest.mark.anyio
async def test_gate_realmente_abierto_si_puede_decirlo(monkeypatch):
    """El contrario (T08 de la campaña 00): si un paso SÍ espera aprobación,
    la frase es verdadera y se conserva. No vale arreglar un caso rompiendo
    el otro."""
    _fake_llm(monkeypatch, "He redactado el borrador; necesito tu confirmación para enviarlo.")

    mission = Mission(id="m1", goal="enviar un email a Ana")
    hecho = TaskNode(id="n1", goal="redactar", state=NodeState.DONE,
                     result={"output": "borrador listo"})
    esperando = TaskNode(id="n2", goal="enviar", state=NodeState.WAITING_APPROVAL)
    text = await responder.build(mission, _graph([hecho, esperando]))

    assert "confirmación" in text.lower()   # el texto del modelo se respeta


@pytest.mark.anyio
async def test_texto_honesto_del_modelo_se_respeta(monkeypatch):
    """No regresión: un resumen normal del modelo pasa tal cual."""
    _fake_llm(monkeypatch, "He creado el proyecto y le he añadido dos agentes.")

    mission = Mission(id="m1", goal="crear el proyecto")
    nodo = TaskNode(id="n1", goal="crear", state=NodeState.DONE,
                    result={"output": "proyecto creado"})
    text = await responder.build(mission, _graph([nodo]))

    assert text == "He creado el proyecto y le he añadido dos agentes."


# ===========================================================================
# 4) Camino corto — la coletilla honesta
# ===========================================================================
def test_camino_corto_marca_la_fabricacion():
    """Los 3 casos de T05 (campaña 01): el camino corto no ejecuta ninguna
    herramienta, así que afirmar una acción es falso por construcción."""
    out = grounding.with_honesty_note(
        "He visitado la documentación oficial y confirma que la versión es la 3.14."
    )
    assert "no he ejecutado ninguna herramienta" in out


def test_camino_corto_marca_la_promesa_incumplida():
    out = grounding.with_honesty_note("Voy a leer ese archivo y te digo qué pone.")
    assert "no he ejecutado ninguna herramienta" in out


def test_camino_corto_no_molesta_en_una_respuesta_normal():
    """El riesgo de este fix es el ruido: una explicación normal NO lleva nota."""
    texto = "Un bucle for en Python se escribe: for x in lista: print(x)"
    assert grounding.with_honesty_note(texto) == texto


def test_camino_corto_texto_vacio_no_revienta():
    assert grounding.with_honesty_note("") == ""


async def _stream_del_runtime(monkeypatch, chunks: list[str]) -> str:
    """Ejecuta `NullRuntime.stream_task` REAL con el MEL fake, y devuelve el
    texto completo que le habría llegado al usuario. La afirmación puede venir
    repartida entre chunks — por eso el runtime la juzga al final, no chunk a
    chunk, y por eso este helper la parte a propósito."""
    from app.tie import runtime as runtime_mod
    from app.tie.runtime import AgentTask, NullRuntime
    from app.services import chat_service

    async def _fake_stream(req):
        for c in chunks:
            yield c

    async def _no_history(*a, **k):
        return "sys"

    monkeypatch.setattr(runtime_mod, "mel_stream", _fake_stream, raising=False)
    monkeypatch.setattr("app.mel.stream", _fake_stream)
    monkeypatch.setattr(chat_service, "build_system_prompt", _no_history)
    monkeypatch.setattr(chat_service, "recent_turns", lambda *a, **k: [])

    task = AgentTask(id=AgentTask.new_id(), instruction="lee el archivo x.txt")
    out = []
    async for chunk in NullRuntime().stream_task(task, memory=None, tools=None,
                                                 approval_gate=None):
        if chunk.kind == "text":
            out.append(chunk.payload)
    return "".join(out)


@pytest.mark.anyio
async def test_stream_del_camino_corto_anade_la_nota(monkeypatch):
    """La afirmación repartida en dos chunks ('He visita' + 'do la web…') se
    detecta igual: el runtime juzga la respuesta ENTERA al terminar."""
    texto = await _stream_del_runtime(
        monkeypatch, ["He visita", "do la web oficial y dice que la versión es la 3.14."])
    assert "no he ejecutado ninguna herramienta" in texto


@pytest.mark.anyio
async def test_stream_de_una_respuesta_normal_no_lleva_nota(monkeypatch):
    texto = await _stream_del_runtime(
        monkeypatch, ["Un bucle for ", "en Python se escribe: for x in lista:"])
    assert "no he ejecutado ninguna herramienta" not in texto
