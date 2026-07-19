# tests/test_capabilities_map.py — R6: Aithera se conoce (doc 23, cierra Δ9)
#
# Los 4 criterios de éxito del sprint. El más importante estructuralmente es
# el #3 (una tool nueva aparece SIN tocar el mapa): es lo que demuestra que el
# mapa se GENERA desde `tool_manager.list_tools()` en cada llamada, en vez de
# ser una lista escrita a mano que se queda obsoleta. El #2 (confidencialidad)
# es una frontera dura: nunca rutas, `.py`, nombres de módulo ni tablas.
from __future__ import annotations

import pytest

from app.tie import capabilities_map
from app.tools.base import BaseTool
from app.tools.tool_manager import tool_manager

# Términos de implementación que NUNCA deben aparecer en el mapa — el
# usuario pregunta qué puede pedir, no cómo está construido por dentro.
_LEAKS = (
    "app.", "app/", ".py", "sqlite", "postgres", "chromadb", "playwright",
    "dpapi", "sqlalchemy", "fastapi", "tool_manager", "mel", "tie/", "backend/",
    "config.py", "models.py", "database.py",
)


@pytest.fixture(autouse=True)
def _clear_cache():
    capabilities_map._cache.clear()
    yield
    capabilities_map._cache.clear()


class _FakeToolNueva(BaseTool):
    """Una tool sintética SIN entrada en `_TOOL_BLURBS` — el caso exacto del
    criterio de cierre #3: debe aparecer igualmente."""
    tool_id = "cosa_nueva_de_prueba"
    name = "Cosa Nueva Tool"
    description = "Descripción interna con detalles de implementación, irrelevante aquí."

    async def execute(self, action, params):
        return {"success": True, "result": None, "error": None}

    def list_actions(self):
        return [
            {"id": "hacer_algo", "description": "x", "requires_confirmation": False, "params": {}},
            {"id": "hacer_otra_cosa", "description": "x", "requires_confirmation": False, "params": {}},
        ]


# ---------------------------------------------------------------------------
# Criterio 1 — enumera capacidades reales
# ---------------------------------------------------------------------------
def test_el_mapa_enumera_capacidades_reales():
    text = capabilities_map.summary(force=True)
    assert text, "el mapa salió vacío contra el catálogo real"
    lower = text.lower()
    # Categorías de alto nivel que SÍ deben poder reconocerse (email, agenda,
    # navegador/web) sin exigir la frase exacta — el fraseo puede evolucionar.
    assert "correo" in lower or "email" in lower
    assert "calendario" in lower or "agenda" in lower
    assert "internet" in lower or "navegar" in lower or "web" in lower


# ---------------------------------------------------------------------------
# Criterio 2 — frontera de confidencialidad (la regla dura del sprint)
# ---------------------------------------------------------------------------
def test_el_mapa_nunca_revela_implementacion():
    text = capabilities_map.summary(force=True)
    lower = text.lower()
    ofensores = [term for term in _LEAKS if term in lower]
    assert not ofensores, f"el mapa filtra detalles internos: {ofensores}\n\n{text}"


def test_las_frases_curadas_tambien_pasan_la_frontera():
    """Las frases de `_TOOL_BLURBS` son código, no input del usuario — pero si
    alguien añade una nueva con un desliz técnico, este test lo caza en CI en
    vez de en producción."""
    lower_all = " ".join(capabilities_map._TOOL_BLURBS.values()).lower()
    ofensores = [term for term in _LEAKS if term in lower_all]
    assert not ofensores, f"una frase curada filtra detalles internos: {ofensores}"


# ---------------------------------------------------------------------------
# Criterio 3 — una tool nueva aparece SIN tocar el mapa (el corazón del sprint)
# ---------------------------------------------------------------------------
def test_una_tool_nueva_aparece_sin_tocar_el_mapa():
    assert "cosa_nueva_de_prueba" not in capabilities_map._TOOL_BLURBS, (
        "esta tool sintética no debe estar curada — es justo el caso que se prueba"
    )
    tool_manager.register(_FakeToolNueva())
    try:
        text = capabilities_map.summary(force=True)
    finally:
        del tool_manager._tools["cosa_nueva_de_prueba"]

    # El nombre curado ("Cosa Nueva") aparece vía el fallback genérico —
    # nunca la descripción interna cruda (que sí tiene detalles de implementación).
    assert "cosa nueva" in text.lower()
    assert "Descripción interna con detalles de implementación" not in text


def test_el_generico_usa_el_nombre_no_la_descripcion_cruda():
    blurb = capabilities_map._generic_blurb("Cosa Nueva Tool", 2)
    assert "cosa nueva" in blurb.lower()
    assert "2" in blurb


# ---------------------------------------------------------------------------
# Criterio 4 — navegación fluida: search → browser, nunca google_search
# ---------------------------------------------------------------------------
def test_el_bucle_de_tool_use_prefiere_search_sobre_google_search():
    from app.tie.toolloop import _SYSTEM_PROMPT

    assert "google_search" in _SYSTEM_PROMPT
    assert "NUNCA" in _SYSTEM_PROMPT or "nunca" in _SYSTEM_PROMPT
    assert "search.search_web" in _SYSTEM_PROMPT
    assert "browser.open_url" in _SYSTEM_PROMPT


def test_google_search_desaconsejada_en_su_propio_catalogo():
    """La advertencia vive también en la propia acción, no solo en el prompt
    general: así sobrevive aunque el prompt del bucle cambie de redacción."""
    from app.tools.browser_tool import BrowserTool

    actions = {a["id"]: a for a in BrowserTool().list_actions()}
    desc = actions["google_search"]["description"].lower()
    assert "desaconsejada" in desc or "bloquea" in desc
    assert "search" in desc


def test_el_planner_pide_las_dos_tools_para_buscar_y_abrir():
    from app.tie.planner import _SYSTEM_PROMPT

    assert "search" in _SYSTEM_PROMPT and "browser" in _SYSTEM_PROMPT
    assert "AMBAS" in _SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Presupuesto + caché (no puede comerse el contexto del chat en cada mensaje)
# ---------------------------------------------------------------------------
def test_respeta_el_presupuesto_de_caracteres():
    text = capabilities_map.summary(force=True)
    assert len(text) <= capabilities_map.MAX_CHARS


def test_nunca_corta_a_media_frase():
    """El recorte por presupuesto es por LÍNEAS completas. Con un presupuesto
    absurdamente bajo, debe quedar solo la cabecera — nunca una línea rota."""
    original = capabilities_map.MAX_CHARS
    capabilities_map.MAX_CHARS = 80
    try:
        text = capabilities_map.summary(force=True)
    finally:
        capabilities_map.MAX_CHARS = original
    assert text == "Esto es lo que puedo hacer de verdad (no solo hablar de ello):"


def test_el_resultado_se_cachea():
    a = capabilities_map.summary(force=True)
    tool_manager.register(_FakeToolNueva())
    try:
        b = capabilities_map.summary()  # sin force: debe devolver lo cacheado
    finally:
        del tool_manager._tools["cosa_nueva_de_prueba"]
    assert a == b, "no debería haber recalculado sin force=True"


def test_build_system_prompt_incluye_el_mapa():
    """Integración con chat_service — el bloque real que se inyecta."""
    from app.services import chat_service

    import asyncio
    prompt = asyncio.run(chat_service.build_system_prompt(""))
    assert "puedo hacer" in prompt.lower()
