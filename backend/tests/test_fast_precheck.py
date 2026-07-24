# tests/test_fast_precheck.py — A·VOZ-2 (doc 32): la charla trivial NO paga LLM
#
# El arreglo de latencia: un heurístico determinista (0 LLM) resuelve la charla
# obvia antes de tocar el clasificador. Conservador — ante la duda, None (que
# clasifique el LLM): un falso "no es charla" solo cuesta el round-trip de
# siempre; un falso "es charla" perdería una acción, y eso NUNCA debe pasar.
from __future__ import annotations

import pytest

from app.tie.contracts import IntentType
from app.tie.intents import fast_precheck


# ---------------------------------------------------------------------------
# HIT — charla obvia → Intent conversacional instantáneo (sin LLM)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("msg", [
    "hola", "Hola", "HOLA", "hola!", "hola aithera",
    "buenas", "buenos días", "buenas tardes", "buenas noches",
    "gracias", "Gracias!", "muchas gracias", "muchísimas gracias", "mil gracias",
    "vale gracias", "ok gracias",
    "adiós", "adios", "hasta luego", "hasta pronto", "nos vemos", "chao", "bye",
    "qué tal", "que tal", "¿qué tal?", "cómo estás", "como estas", "¿cómo estás?",
    "cómo va todo", "todo bien",
    "vale", "ok", "okay", "perfecto", "genial", "entendido", "listo", "claro",
    "hi", "hello", "thanks", "thank you", "good morning", "how are you",
    "hola buenas gracias",   # combinación no listada pero todo cortesía
])
def test_charla_obvia_es_hit(msg):
    intent = fast_precheck(msg)
    assert intent is not None, f"{msg!r} debería ser charla (HIT)"
    assert intent.type == IntentType.CONVERSATIONAL
    assert intent.is_short_path is True
    assert intent.requires_planning is False
    assert intent.requires_browser is False
    assert intent.objectives == []
    assert intent.confidence >= 0.55        # no cae por el floor
    assert intent.raw_text == msg.strip()   # fidelidad del texto original (S2)


# ---------------------------------------------------------------------------
# MISS — cualquier cosa con acción/dominio/duda → None (que decida el LLM)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("msg", [
    "abre YouTube y pon una canción",
    "búscame un vuelo a Roma",
    "manda un email a Ana",
    "crea una carpeta con este texto",
    "descarga el último informe",
    "resúmeme este PDF",
    "reserva una mesa para dos",
    "gracias, y ahora búscame un vuelo",   # cortesía + ACCIÓN → no es charla
    "cómo va el proyecto Aithera",          # 'proyecto' no es cortesía → query
    "qué hora es",                          # 'hora' no es cortesía
    "usa Claude para esto",                 # nombra un modelo → al clasificador
    "abre https://youtube.com",             # URL
    "recuérdame llamar al médico mañana a las 5",  # largo + acción
])
def test_no_charla_es_miss(msg):
    assert fast_precheck(msg) is None, f"{msg!r} NO debería ser charla (MISS)"


def test_vacio_es_miss():
    assert fast_precheck("") is None
    assert fast_precheck("   ") is None


def test_mensaje_largo_de_solo_cortesia_igual_es_miss():
    """Un mensaje largo casi nunca es charla pura: aunque todas las palabras
    fueran de cortesía, por encima del límite se manda al clasificador (barato
    seguro > barato arriesgado)."""
    largo = "hola buenas gracias vale perfecto genial estupendo bien"  # 8 palabras
    assert fast_precheck(largo) is None


# ---------------------------------------------------------------------------
# Integración: classify() usa el precheck y NO llama al LLM en la charla
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_classify_charla_no_toca_el_llm(monkeypatch):
    from app.tie import intents as intents_mod

    llamado = {"n": 0}

    async def _spy_complete(*a, **k):
        llamado["n"] += 1
        raise AssertionError("classify NO debe llamar al LLM para charla obvia")

    # El router se importa DENTRO de classify (import diferido); parcheamos el
    # módulo real para que un uso accidental reviente el test.
    from app.tie import router as router_mod
    monkeypatch.setattr(router_mod, "complete", _spy_complete)

    intent = await intents_mod.classify("hola")
    assert intent.type == IntentType.CONVERSATIONAL
    assert intent.is_short_path is True
    assert llamado["n"] == 0


@pytest.mark.anyio
async def test_classify_accion_si_llama_al_llm(monkeypatch):
    """No-regresión: un mensaje de acción SÍ pasa por el clasificador LLM."""
    from app.tie import intents as intents_mod
    from app.tie import router as router_mod

    llamado = {"n": 0}

    async def _fake_complete(text, *, system_prompt=None, capability=None):
        llamado["n"] += 1
        return {"response": '{"type":"execute","goal":"abrir youtube","confidence":0.9,'
                            '"requires_browser":true}', "error": False}

    monkeypatch.setattr(router_mod, "complete", _fake_complete)

    intent = await intents_mod.classify("abre YouTube y pon una canción")
    assert llamado["n"] == 1                     # el LLM SÍ se usó
    assert intent.type == IntentType.EXECUTE
    assert intent.requires_browser is True
