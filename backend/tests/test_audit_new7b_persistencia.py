# tests/test_audit_new7b_persistencia.py — NEW-7b (doc 34): guardar/anotar no
# se pierde por el camino.
#
# EL FALLO REAL (verificación en vivo, 2026-07-28): "Investiga qué es FastAPI y
# guárdame un resumen de tres líneas" investigó bien (world_intent detectó la
# lectura), pero al llegar al paso de guardar Aithera respondió "no tengo
# herramienta de escritura de ficheros disponible en este paso (solo búsqueda
# web y navegador)". La orden de guardar iba en el MISMO mensaje y se perdió:
# `world_intent()` (NEW-7) solo reconoce verbos de LECTURA del mundo
# ("lee", "lista", "busca"...), nunca los de ESCRITURA ("guarda", "anota").
#
# Consecuencia scoped, no el patrón general NEW-5 (tools que no llegan al nodo
# por el planner/Authority): aquí la tool ni siquiera se PIDE.
from __future__ import annotations

import pytest

from app.tie.action_intent import _wants_to_persist, ensure_persistence_tool
from app.tie.contracts import Intent, IntentType
from app.tie import intents as intents_mod


def _intent(tipo=IntentType.EXECUTE, tools=None, raw="") -> Intent:
    return Intent(
        type=tipo,
        goal="investigar y guardar",
        requires_tools=list(tools or []),
        raw_text=raw,
    )


# ===========================================================================
# _wants_to_persist — detector puro
# ===========================================================================
@pytest.mark.parametrize("texto", [
    "Investiga qué es FastAPI y guárdame un resumen de tres líneas",
    "guardame esto en un archivo",
    "anota estas ideas en un fichero",
    "apunta lo que encuentres",
    "guarda el resultado en la carpeta del proyecto",
    "Save this summary to a file",
    "please keep a note of this",
])
def test_detecta_peticion_de_guardar(texto):
    assert _wants_to_persist(texto) is True


@pytest.mark.parametrize("texto", [
    "guarda silencio un momento",
    "guarda las distancias con él",
    "guarda la calma por favor",
    "guarda la compostura",
    "guarda cama unos días",
    "¿qué hora es?",
    "cuéntame un chiste",
    "busca información sobre FastAPI",  # solo lectura, sin verbo de guardar
])
def test_no_dispara_con_modismos_ni_charla(texto):
    assert _wants_to_persist(texto) is False


def test_no_dispara_con_texto_vacio():
    assert _wants_to_persist("") is False
    assert _wants_to_persist(None) is False


# ===========================================================================
# ensure_persistence_tool — integración con el Intent
# ===========================================================================
def test_anade_filesystem_cuando_falta_y_se_pide_guardar():
    it = _intent(tools=["search"], raw="Investígalo en internet y guárdame un resumen")
    out = ensure_persistence_tool(it, it.raw_text)
    assert "filesystem" in out.requires_tools
    assert "search" in out.requires_tools  # no pisa lo que ya había


def test_no_duplica_si_ya_estaba():
    it = _intent(tools=["filesystem", "search"], raw="guárdame esto")
    out = ensure_persistence_tool(it, it.raw_text)
    assert out.requires_tools.count("filesystem") == 1


def test_no_toca_conversational():
    it = _intent(tipo=IntentType.CONVERSATIONAL, tools=[], raw="guárdame un resumen")
    out = ensure_persistence_tool(it, it.raw_text)
    assert out.requires_tools == []


def test_intent_none_no_rompe():
    assert ensure_persistence_tool(None, "guárdame esto") is None


def test_no_anade_nada_si_no_se_pide_guardar():
    it = _intent(tools=["search"], raw="Investiga qué es FastAPI")
    out = ensure_persistence_tool(it, it.raw_text)
    assert "filesystem" not in out.requires_tools


def test_usa_intent_raw_text_si_no_se_pasa_texto_explicito():
    it = _intent(tools=["search"], raw="anótame el resultado")
    out = ensure_persistence_tool(it, "")  # texto vacío -> cae a intent.raw_text
    assert "filesystem" in out.requires_tools


# ===========================================================================
# classify() end-to-end — el mensaje REAL que falló en vivo
# ===========================================================================
@pytest.mark.anyio
async def test_classify_real_mensaje_fastapi_incluye_filesystem(monkeypatch):
    """El mensaje exacto del fallo en vivo: world_intent detecta la lectura
    (search), y el wrapper de classify() debe añadir filesystem por el verbo
    de guardar en el mismo mensaje."""
    msg = ("Investiga qué es FastAPI y guárdame un resumen de tres líneas "
           "Investigalo en internet")
    intent = await intents_mod.classify(msg)
    assert "filesystem" in intent.requires_tools
    assert "search" in intent.requires_tools or intent.requires_browser


@pytest.mark.anyio
async def test_classify_llm_exitoso_tambien_pasa_por_el_wrapper(monkeypatch):
    """Aunque el clasificador LLM tenga éxito y devuelva un intent válido sin
    world_intent/action_intent de por medio, ensure_persistence_tool debe
    aplicarse igual — el LLM también puede olvidar filesystem.

    Se mockea `app.mel.complete` (la frontera REAL que `router.complete`
    invoca) en vez de `router.complete` directamente, para ejercitar el mismo
    camino que usa `intents.classify()` en producción."""
    import json
    from app.mel.contracts import ExecutionResult

    async def _fake_mel_complete(req):
        payload = json.dumps({
            "type": "execute", "goal": "buscar y guardar",
            "requires_tools": ["search"], "requires_planning": False,
            "requires_browser": False, "requires_computer": False,
            "requires_automation": False, "model_capability": "chat",
            "requires_memory": False, "memory_types": [], "context_query": "",
            "confidence": 0.9,
        })
        return ExecutionResult(text=payload, ok=True)

    import app.mel as _mel
    monkeypatch.setattr(_mel, "complete", _fake_mel_complete)

    intent = await intents_mod.classify("busca esto y guárdamelo en un archivo")
    assert "filesystem" in intent.requires_tools


@pytest.mark.anyio
async def test_classify_no_anade_filesystem_sin_verbo_de_guardar(monkeypatch):
    """No-regresión: un mensaje de solo lectura no gana filesystem porque sí."""
    intent = await intents_mod.classify("Investiga qué es FastAPI")
    assert "filesystem" not in intent.requires_tools
