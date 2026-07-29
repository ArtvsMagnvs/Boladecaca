# tests/test_audit_new7_fabricacion.py — NEW-7 (doc 34): el camino corto ya no
# puede fabricar datos concretos.
#
# EL FALLO REAL (verificación en vivo del usuario, 2026-07-28). Mensaje:
#   "Lista los archivos de la carpeta Aithera, dime cuántos .py hay en
#    backend/app/tie, y léeme las primeras líneas de pipeline.py"
# Log del backend:
#   [intents] sin JSON parseable, fallback conversational
# Respuesta: un listado inventado, "Total de archivos .py en backend/app/tie: 7"
# (falso) y un bloque de código con imports que NO existen en el archivo real.
# Sin ninguna nota de honestidad: el fix de S2·S6 no disparó porque el texto no
# usaba ningún verbo delator ("he leído") — presentaba los datos y ya está.
#
# DOS CAPAS, DOS BLOQUES DE TESTS:
#   1. `action_intent.world_intent` — la petición ya no degrada a charla cuando
#      el clasificador falla su JSON (la causa raíz).
#   2. `grounding.presents_unverifiable_evidence` — si aun así se llega al
#      camino corto, la respuesta sale marcada (el respaldo).
from __future__ import annotations

import pytest

from app.core import grounding
from app.tie import action_intent, intents, router
from app.tie.contracts import Intent, IntentType


# ===========================================================================
# CAPA 1 · el detector determinista de "esto pide leer el mundo"
# ===========================================================================
CASOS_SI = [
    # el mensaje EXACTO del fallo real
    "Lista los archivos de la carpeta Aithera, dime cuántos .py hay en "
    "backend/app/tie, y léeme las primeras líneas de pipeline.py",
    "léeme el GDD del proyecto",
    "lee el archivo config.py",
    "busca en internet las novedades de FastAPI",
    "revisa mi correo de hoy",
    "abre el documento de diseño",
    "dime cuántos .py hay en backend/app/tie",
    "resume el pdf que te pasé",
    "lista los archivos de mi carpeta de descargas",
    "visita https://ejemplo.com y dime qué pone",
    "consulta mi agenda de mañana",
]

CASOS_NO = [
    "hola qué tal",
    "gracias, muy bien",
    "cuéntame un chiste",
    "explícame cómo funciona la memoria de Aithera",
    "qué es un archivo .py",              # sin verbo de acción: es una pregunta
    "muéstrame cómo se escribe un bucle for",
    "cómo puedo organizar mejor mis carpetas",
    # EL falso positivo que justifica los dos niveles de verbo: verbo genérico
    # ("dime") + palabra de dominio ("archivos") pero NINGÚN archivo real.
    "dime qué archivos suele tener un proyecto FastAPI",
]


@pytest.mark.parametrize("texto", CASOS_SI)
def test_pide_leer_el_mundo(texto):
    assert action_intent.looks_like_world_read(texto) is True


@pytest.mark.parametrize("texto", CASOS_NO)
def test_no_pide_leer_el_mundo(texto):
    assert action_intent.looks_like_world_read(texto) is False


def test_world_intent_lleva_herramientas_y_no_es_camino_corto():
    """Lo CRÍTICO: el intent resultante no puede caer en `is_short_path` — ahí
    es donde no hay herramientas y donde el modelo fabrica."""
    intent = action_intent.world_intent("léeme el archivo backend/app/tie/pipeline.py")
    assert intent is not None
    assert intent.type == IntentType.EXECUTE
    assert intent.requires_tools, "sin herramientas volveríamos al problema"
    assert intent.is_short_path is False
    assert intent.is_direct_action is True
    assert intent.requires_planning is False
    assert intent.raw_text.startswith("léeme el archivo")   # fidelidad (C-1, S2)


def test_world_intent_detecta_la_familia_correcta():
    assert "email" in action_intent.world_intent("revisa mi correo").requires_tools
    assert "calendar" in action_intent.world_intent("consulta mi agenda").requires_tools
    web = action_intent.world_intent("busca en internet noticias de IA")
    assert "search" in web.requires_tools and web.requires_browser is True
    doc = action_intent.world_intent("resume el documento del proyecto")
    # leer un documento suele exigir localizarlo primero
    assert "document" in doc.requires_tools and "filesystem" in doc.requires_tools


def test_world_intent_devuelve_none_si_no_aplica():
    assert action_intent.world_intent("hola, ¿qué tal?") is None
    assert action_intent.world_intent("") is None


def test_una_orden_sobre_aithera_sigue_teniendo_prioridad():
    """No-regresión del detector del 25-jul: "crea una tarea" sigue yendo por
    `action_intent()` con la tool `aithera`, no por el detector nuevo."""
    act = action_intent.action_intent("crea una tarea de revisar el informe")
    assert act is not None and act.requires_tools == ["aithera"]


@pytest.mark.anyio
async def test_sin_json_parseable_una_lectura_ya_no_degrada_a_charla(monkeypatch):
    """LA REGRESIÓN DEL FALLO: se simula exactamente el log real (el modelo
    devuelve algo que no es JSON) y se comprueba que el intent resultante SÍ
    lleva herramientas, en vez del `conversational_fallback` de antes."""
    async def _fake_complete(prompt, *, system_prompt=None, capability="chat", **kw):
        return {"response": "Claro, te ayudo con eso.", "model": "llama3", "error": False}

    monkeypatch.setattr(router, "complete", _fake_complete)

    texto = ("Lista los archivos de la carpeta Aithera, dime cuántos .py hay en "
             "backend/app/tie, y léeme las primeras líneas de pipeline.py")
    intent = await intents.classify(texto)

    assert intent.type != IntentType.CONVERSATIONAL
    assert intent.is_short_path is False, "esto es lo que provocaba la fabricación"
    assert intent.requires_tools


@pytest.mark.anyio
async def test_confianza_baja_no_degrada_una_lectura_a_charla(monkeypatch):
    """El suelo de confianza (0.55) también acababa en el camino sin
    herramientas. Ahora, si el mensaje pide DEMOSTRABLEMENTE leer el mundo, el
    detector determinista manda."""
    async def _fake_complete(prompt, *, system_prompt=None, capability="chat", **kw):
        return {"response": '{"type":"query","goal":"algo","domain":["file"],'
                            '"confidence":0.2,"requires_tools":[],'
                            '"requires_planning":false,"requires_browser":false,'
                            '"requires_computer":false,"requires_automation":false,'
                            '"model_capability":"chat","requires_memory":false,'
                            '"memory_types":[],"context_query":""}',
                "model": "llama3", "error": False}

    monkeypatch.setattr(router, "complete", _fake_complete)

    intent = await intents.classify("léeme el archivo backend/app/tie/pipeline.py")
    assert intent.is_short_path is False
    assert intent.requires_tools


@pytest.mark.anyio
async def test_la_charla_con_json_roto_sigue_siendo_charla(monkeypatch):
    """No-regresión IMPORTANTE: el fail-safe conversational sigue existiendo
    para lo que de verdad es charla. El detector no puede tragarse todo."""
    async def _fake_complete(prompt, *, system_prompt=None, capability="chat", **kw):
        return {"response": "no soy JSON", "model": "llama3", "error": False}

    monkeypatch.setattr(router, "complete", _fake_complete)

    intent = await intents.classify("cuéntame algo interesante sobre el espacio")
    assert intent.type == IntentType.CONVERSATIONAL
    assert intent.is_short_path is True


# ===========================================================================
# CAPA 2 · evidencia que solo una herramienta podría producir
# ===========================================================================
FABRICADA = """Aquí tienes lo que has pedido:

Archivos en la carpeta Aithera:
- backend/
- frontend/
- CLAUDE.md

Total de archivos .py en backend/app/tie: 7

Primeras líneas de pipeline.py:
```python
from .config_loader import load_config
from .orchestrator import orchestrate
```
"""


def test_detecta_la_respuesta_fabricada_real():
    """El texto del fallo real: NINGÚN verbo delator ("he leído"), así que los
    patrones de S2·S6 no lo veían. Este sí."""
    assert grounding.claims_completed_action(FABRICADA) is False, \
        "si esto cambia, el test ya no prueba el hueco que NEW-7 cierra"
    assert grounding.presents_unverifiable_evidence(FABRICADA) is True


@pytest.mark.parametrize("texto", [
    "Los archivos son:\n- main.py\n- config.py\n- utils.py\n- models.py\n",
    "El contenido de backend/app/tie/pipeline.py es:\n```python\nfrom .x import y\n```",
    "Total de archivos .py en backend/app/tie: 7",
    "Fuentes:\n- [Doc](https://a.com/x)\n- [Guía](https://b.com/y)",
])
def test_evidencia_inverificable(texto):
    assert grounding.presents_unverifiable_evidence(texto) is True


@pytest.mark.parametrize("texto", [
    # un ejemplo de código PEDIDO no es evidencia: no hay archivo real detrás
    "Aquí tienes un ejemplo:\n```python\ndef suma(a, b):\n    return a + b\n```",
    "Un proyecto FastAPI suele tener un main.py, pero no he mirado el tuyo.",
    "Necesitarás un main.py y un requirements.txt para empezar.",
    "Puedes mirarlo en [la doc](https://fastapi.tiangolo.com/).",   # un solo enlace
    "Hola, ¿en qué te ayudo?",
    "No tengo una herramienta para extraer el texto de ese formato en este momento.",
    "",
])
def test_no_marca_respuestas_legitimas(texto):
    """El riesgo de este fix es el RUIDO: marcar respuestas correctas erosiona
    la confianza igual que mentir. Estos casos deben salir limpios."""
    assert grounding.presents_unverifiable_evidence(texto) is False


def test_la_nota_del_camino_corto_es_la_fuerte_si_hay_fabricacion():
    salida = grounding.with_honesty_note(FABRICADA)
    assert salida != FABRICADA
    assert grounding.fabrication_note() in salida
    assert grounding.honesty_note() not in salida     # la suave se queda corta aquí


def test_la_nota_suave_sigue_usandose_cuando_toca():
    """No-regresión de S2·S6: una afirmación de acción sin datos concretos
    sigue llevando la coletilla suave, no el aviso fuerte."""
    texto = "He enviado el correo que me pediste."
    salida = grounding.with_honesty_note(texto)
    assert grounding.honesty_note() in salida
    assert grounding.fabrication_note() not in salida


def test_note_for_es_el_punto_unico_de_decision():
    """La variante con streaming (`runtime.stream_task`) y la que no
    (`with_honesty_note`) deben decidir con la MISMA función, o divergen."""
    assert grounding.note_for(FABRICADA) == grounding.fabrication_note()
    assert grounding.note_for("He enviado el correo.") == grounding.honesty_note()
    assert grounding.note_for("Hola, ¿qué tal?") is None
    assert grounding.note_for("") is None
