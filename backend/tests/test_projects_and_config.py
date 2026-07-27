# tests/test_projects_and_config.py — Aithera VE sus proyectos reales y puede
# operarse a sí misma (2026-07-24, arreglo de raíz reportado por el usuario).
#
# Los 3 fallos que blinda:
#   1. El chat inventaba proyectos ("Proyecto 1/2") porque el prompt NO inyectaba
#      los reales → ahora `_workspace_block` mete la tabla SQL `projects`.
#   2. El clasificador no conocía la tool `aithera` (self-operación) y el toolloop
#      no MOSTRABA sus acciones al modelo → ahora sí.
#   3. La voz no seguía al idioma (acento portugués con español) → reasigna.
import asyncio

import pytest

from app.db.database import Base, Config, Project, SessionLocal, engine


@pytest.fixture(autouse=True)
def _clean():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(Project).delete()
        db.query(Config).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(Project).delete()
        db.query(Config).delete()
        db.commit()
    finally:
        db.close()


def _add_projects(*names):
    db = SessionLocal()
    try:
        for n in names:
            db.add(Project(name=n, status="active", progress=0.2))
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 1) El chat inyecta los proyectos REALES (no los inventa)
# ---------------------------------------------------------------------------
def test_workspace_block_lista_proyectos_reales():
    from app.services import chat_service
    _add_projects("OT Saas", "Waterquest", "Quicky Dungeons")
    block = chat_service._workspace_block()
    for n in ("OT Saas", "Waterquest", "Quicky Dungeons"):
        assert n in block
    assert "NO inventes" in block


def test_workspace_vacio_no_rompe():
    from app.services import chat_service
    assert chat_service._workspace_block() == ""


@pytest.mark.anyio
async def test_build_system_prompt_incluye_proyectos_reales():
    from app.services import chat_service
    _add_projects("OT Saas", "Waterquest")
    prompt = await chat_service.build_system_prompt("¿qué proyectos tengo?")
    assert "OT Saas" in prompt and "Waterquest" in prompt


# ---------------------------------------------------------------------------
# 2) El toolloop MUESTRA las acciones de aithera + el clasificador la conoce
# ---------------------------------------------------------------------------
def test_toolloop_muestra_las_acciones_de_aithera():
    import app.tools  # noqa: F401  (registra)
    from app.tie.toolloop import build_catalog
    from app.tools import tool_manager

    catalog = build_catalog(["aithera"], tool_manager)
    acciones = {c["action"] for c in catalog if c["tool_id"] == "aithera"}
    # las acciones clave que el usuario pidió deben ser visibles al modelo
    for a in ("list_projects", "create_project", "create_agent", "create_rule",
              "set_language", "set_chat_model"):
        assert a in acciones, f"la acción {a} no se muestra al modelo en el toolloop"


def test_clasificador_conoce_la_tool_aithera():
    from app.tie import intents
    assert "aithera" in intents._SYSTEM_PROMPT
    assert "crea un proyecto" in intents._SYSTEM_PROMPT.lower()


# ---------------------------------------------------------------------------
# 2b) aithera_tool ejecuta las acciones nuevas de configuración
# ---------------------------------------------------------------------------
def test_set_language_cambia_config():
    from app.tools.aithera_tool import AitheraTool
    r = asyncio.run(AitheraTool().execute("set_language", {"language": "inglés"}))
    assert r["success"] and r["result"]["app_language"] == "en"
    db = SessionLocal()
    try:
        row = db.query(Config).filter(Config.key == "app_language").first()
        assert row and row.value == "en"
    finally:
        db.close()


def test_set_language_idioma_no_soportado():
    from app.tools.aithera_tool import AitheraTool
    r = asyncio.run(AitheraTool().execute("set_language", {"language": "klingon"}))
    assert not r["success"]


# ---------------------------------------------------------------------------
# 3) La voz sigue al idioma (fin del acento portugués)
# ---------------------------------------------------------------------------
def _set_cfg(**kv):
    db = SessionLocal()
    try:
        for k, v in kv.items():
            db.add(Config(key=k, value=v))
        db.commit()
    finally:
        db.close()


def test_voz_pt_heredada_con_idioma_es_se_reasigna():
    import app.api.endpoints.voice as v
    _set_cfg(app_language="es", tts_selected_voice="pt-BR-FranciscaNeural",
             tts_active_provider="edgetts")
    r = v.voice_defaults()
    assert r.voice_id == "es-ES-ElviraNeural"
    assert r.was_assigned is True


def test_voz_propia_del_idioma_se_conserva():
    import app.api.endpoints.voice as v
    _set_cfg(app_language="es", tts_selected_voice="es-ES-AlvaroNeural",
             tts_active_provider="edgetts")
    r = v.voice_defaults()
    assert r.voice_id == "es-ES-AlvaroNeural"
    assert r.was_assigned is False


def test_voz_kokoro_de_otro_idioma_se_reasigna():
    import app.api.endpoints.voice as v
    _set_cfg(app_language="en", tts_selected_voice="ef_dora",  # ef_ = español
             tts_active_provider="kokoro")
    r = v.voice_defaults()
    assert r.voice_id == "en-US-AriaNeural"
    assert r.provider == "edgetts"


def test_voice_language_deteccion():
    import app.api.endpoints.voice as v
    assert v._voice_language("pt-BR-FranciscaNeural", "edgetts") == "pt"
    assert v._voice_language("es-ES-ElviraNeural", "edgetts") == "es"
    assert v._voice_language("pf_dora", "kokoro") == "pt"
    assert v._voice_language("af_heart", "kokoro") == "en"
    assert v._voice_language("XB0fDUnXU5powGXd8GSW", "elevenlabs") is None  # opaca
