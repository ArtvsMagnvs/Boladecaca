# tests/test_i18n_language.py — idioma de RESPUESTA del LLM (I18N-9, doc 30)
#
# Verifica que `app.core.language` lee correctamente `Config.app_language` y que
# `chat_service.build_system_prompt` inyecta la directiva de idioma (o el
# fallback histórico cuando no hay idioma elegido). Es el corazón de I18N-9:
# "cuando hay un idioma seleccionado, ese es el idioma con el que habla el chat".
import pytest

from app.core import language
from app.db.database import SessionLocal
from app.db.models import Config
from app.services import chat_service


def _set_lang(value):
    """Fija (o borra si value=None) Config.app_language, con commit — para que
    la sesión propia de `language.ui_language()` lo vea."""
    db = SessionLocal()
    try:
        db.query(Config).filter(Config.key == "app_language").delete()
        if value is not None:
            db.add(Config(key="app_language", value=value))
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _clean_lang():
    """Cada test arranca y termina sin idioma fijado (no contamina a otros)."""
    _set_lang(None)
    yield
    _set_lang(None)


# ---------------------------------------------------------------------------
# app.core.language — la unidad
# ---------------------------------------------------------------------------
def test_sin_idioma_devuelve_none_y_directiva_vacia():
    assert language.ui_language() is None
    assert language.ui_language_name() is None
    # Sin idioma elegido: NO se fuerza nada (comportamiento histórico intacto).
    assert language.language_directive() == ""


@pytest.mark.parametrize("stored,code,name", [
    ("es", "es", "español"),
    ("en", "en", "English"),
    ("en-US", "en", "English"),   # se normaliza a los 2 primeros caracteres
    ("fr", "fr", "français"),
    ("pt-PT", "pt", "português"),
])
def test_idioma_soportado(stored, code, name):
    _set_lang(stored)
    assert language.ui_language() == code
    assert language.ui_language_name() == name
    d = language.language_directive()
    # [A·VOZ-8] la directiva va ESCRITA EN EL IDIOMA OBJETIVO y es forzosa.
    assert d   # no vacía
    assert "SIEMPRE" in d.upper() or "MUST" in d.upper() or "DOIS" in d.upper() or "DEVES" in d.upper()


@pytest.mark.parametrize("code,marker", [
    ("en", "in English"),
    ("fr", "en français"),
    ("pt", "em português"),
    ("es", "en español"),
])
def test_directiva_en_el_idioma_objetivo(code, marker):
    """[A·VOZ-8] La instrucción de idioma está escrita EN el idioma objetivo (no
    en español) — es lo que hace que un modelo local la obedezca."""
    _set_lang(code)
    assert marker in language.language_directive()


def test_idioma_desconocido_se_ignora():
    """Un valor raro (idioma no soportado) equivale a 'sin idioma': fail-safe."""
    _set_lang("de")   # alemán no está en los 4 soportados
    assert language.ui_language() is None
    assert language.language_directive() == ""


# ---------------------------------------------------------------------------
# chat_service.build_system_prompt — la integración
# ---------------------------------------------------------------------------
def test_prompt_base_ya_no_hardcodea_el_idioma():
    """La frase 'en el idioma del usuario' salió del prompt base: ahora se
    inyecta dinámicamente (o como fallback)."""
    assert "en el idioma del usuario" not in chat_service.DEFAULT_SYSTEM_PROMPT


@pytest.mark.anyio
async def test_build_system_prompt_fuerza_el_idioma_elegido():
    _set_lang("en-US")
    prompt = await chat_service.build_system_prompt("hola, ¿qué puedes hacer?")
    assert "in English" in prompt
    # [A·VOZ-8] la directiva va LA PRIMERA del prompt (máxima obediencia).
    assert prompt.lstrip().startswith("CRITICAL")
    # No debe quedar el fallback suave cuando SÍ hay idioma forzado.
    assert "mismo idioma en el que te escriba" not in prompt


@pytest.mark.anyio
async def test_build_system_prompt_sin_idioma_usa_el_del_mensaje():
    _set_lang(None)
    prompt = await chat_service.build_system_prompt("hola")
    # Fallback histórico: responder en el idioma del usuario, sin forzar.
    assert "mismo idioma en el que te escriba" in prompt
    assert "RESPONSE LANGUAGE" not in prompt


@pytest.mark.anyio
async def test_build_system_prompt_portugues():
    _set_lang("pt")
    prompt = await chat_service.build_system_prompt("oi")
    assert "em português" in prompt
    assert prompt.lstrip().startswith("CRÍTICO")
