# tests/test_session_context.py — Contexto del MOS cacheado por sesión (A·VOZ-7, doc 32)
#
# Verifica que en la charla el contexto del MOS se resuelve UNA vez por (sesión,
# tema) y se reutiliza — y que se REFRESCA cuando debe: cambio de sesión, cambio
# de tema, escritura en memoria (memoria fresca nunca invisible) y TTL. No toca
# ChromaDB: se mockea `_mos_context_block` (el seam de la llamada al MOS), así
# que el test es determinista y corre sin el stack de memoria real.
import time

import pytest

from app.memory import memory_router
from app.services import chat_service


@pytest.fixture(autouse=True)
def _clean():
    chat_service.clear_session_context()
    yield
    chat_service.clear_session_context()


def _spy_block(monkeypatch):
    """Sustituye la llamada real al MOS por un contador. Devuelve un dict con el
    nº de consultas reales al MOS y permite fijar el texto de contexto."""
    estado = {"llamadas": 0, "ctx": "CTX-de-memoria"}

    async def _fake(query, project_id=None):
        estado["llamadas"] += 1
        return estado["ctx"]

    monkeypatch.setattr(chat_service, "_mos_context_block", _fake)
    return estado


# ---------------------------------------------------------------------------
# HIT: dos turnos de la misma sesión y tema → 1 sola consulta al MOS
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_mismo_tema_misma_sesion_una_sola_consulta(monkeypatch):
    st = _spy_block(monkeypatch)
    q1 = "cuéntame del proyecto Aithera y su arquitectura"
    q2 = "y la arquitectura del proyecto Aithera qué tal va"   # mismo tema

    c1 = await chat_service._memory_blocks_session(q1, session_id="s-1")
    c2 = await chat_service._memory_blocks_session(q2, session_id="s-1")

    # el bundle es (prefs, profile, mos); el 3.º es el bloque del MOS
    assert c1[2] == c2[2] == "CTX-de-memoria"
    assert st["llamadas"] == 1, "el segundo turno del mismo tema no debe re-consultar el MOS"


# ---------------------------------------------------------------------------
# MISS: cambio de sesión → nueva consulta
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_cambio_de_sesion_reconsulta(monkeypatch):
    st = _spy_block(monkeypatch)
    q = "cuéntame del proyecto Aithera"
    await chat_service._memory_blocks_session(q, session_id="s-1")
    await chat_service._memory_blocks_session(q, session_id="s-2")
    assert st["llamadas"] == 2, "otra sesión debe consultar el MOS por su cuenta"


# ---------------------------------------------------------------------------
# MISS: cambio de tema dentro de la misma sesión → nueva consulta
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_cambio_de_tema_reconsulta(monkeypatch):
    st = _spy_block(monkeypatch)
    await chat_service._memory_blocks_session(
        "cuéntame del proyecto Aithera", session_id="s-1")
    await chat_service._memory_blocks_session(
        "qué tiempo hace mañana en Madrid", session_id="s-1")   # tema distinto
    assert st["llamadas"] == 2, "un cambio de tema no puede reutilizar el contexto anterior"


# ---------------------------------------------------------------------------
# MISS: memoria escrita a mitad de sesión → el siguiente turno la ve (no invisible)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_escritura_en_memoria_refresca(monkeypatch):
    st = _spy_block(monkeypatch)
    q = "cuéntame del proyecto Aithera"

    await chat_service._memory_blocks_session(q, session_id="s-1")
    assert st["llamadas"] == 1

    # el usuario/agente guarda algo en memoria → sube la versión de escritura
    memory_router._write_version += 1
    # el nuevo dato debe entrar: se re-consulta aunque sea el mismo tema y sesión
    st["ctx"] = "CTX-con-dato-nuevo"
    c = await chat_service._memory_blocks_session(q, session_id="s-1")

    assert st["llamadas"] == 2, "una memoria nueva NO puede quedar invisible en la charla"
    assert c[2] == "CTX-con-dato-nuevo"


# ---------------------------------------------------------------------------
# MISS: TTL expirado → nueva consulta
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_ttl_expirado_reconsulta(monkeypatch):
    st = _spy_block(monkeypatch)
    q = "cuéntame del proyecto Aithera"
    await chat_service._memory_blocks_session(q, session_id="s-1")
    assert st["llamadas"] == 1

    # forzar la expiración: se envejece la entrada de caché a mano
    query, ctx, _exp, ver = chat_service._SESSION_CTX["s-1"]
    chat_service._SESSION_CTX["s-1"] = (query, ctx, time.monotonic() - 1.0, ver)

    await chat_service._memory_blocks_session(q, session_id="s-1")
    assert st["llamadas"] == 2, "un snapshot expirado debe re-consultar el MOS"


# ---------------------------------------------------------------------------
# Sin caché: sin session_id o con project_id → siempre consulta (no charla general)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_sin_session_id_nunca_cachea(monkeypatch):
    st = _spy_block(monkeypatch)
    q = "cuéntame del proyecto Aithera"
    await chat_service._memory_blocks_session(q, session_id=None)
    await chat_service._memory_blocks_session(q, session_id=None)
    assert st["llamadas"] == 2, "sin sesión (AE/agente/canal) no hay caché de sesión"


@pytest.mark.anyio
async def test_con_project_id_no_usa_cache_de_sesion(monkeypatch):
    st = _spy_block(monkeypatch)
    q = "cuéntame del proyecto"
    await chat_service._memory_blocks_session(q, session_id="s-1", project_id=7)
    await chat_service._memory_blocks_session(q, session_id="s-1", project_id=7)
    assert st["llamadas"] == 2, "un chat de proyecto no comparte el caché de charla general"


# ---------------------------------------------------------------------------
# Utilidades de comparación de tema (unidad)
# ---------------------------------------------------------------------------
def test_same_topic_sin_tokens_de_contenido_es_el_mismo_no_tema():
    # consultas sin ninguna palabra de contenido (≥3 letras) → mismo "no-tema"
    # → se reutiliza el snapshot (el contexto de esa charla es estable/vacío)
    assert chat_service._same_topic("ok", "ya") is True


def test_same_topic_saludos_distintos_son_temas_distintos():
    # 'hola' y 'gracias' SÍ son tokens de contenido: temas distintos → re-consulta
    # (barato: el contexto de una charla trivial es casi vacío de todos modos)
    assert chat_service._same_topic("hola", "gracias") is False


def test_same_topic_distingue_temas():
    assert chat_service._same_topic(
        "cuéntame del proyecto Aithera", "qué tiempo hace en Madrid") is False
