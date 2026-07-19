# tests/test_profile.py — R6.5c: "que te vaya conociendo" (doc 23)
#
# Los 4 criterios de éxito del sprint (doc 23), en orden:
#   1. Un hecho estable -> tras el destilado -> se usa en una conversación
#      NUEVA y sin relación.
#   2. Algo efímero -> NO se guarda.
#   3. Repetir un hecho con otro valor -> se ACTUALIZA (no dos versiones).
#   4. Borrar un hecho -> deja de aparecer.
#
# Parte 1 (siempre): funciones puras — normalización de key, parseo de JSON,
# presupuesto del texto que se manda a extraer.
# Parte 2 (si ChromaDB disponible): el destilado real contra el store real.
from __future__ import annotations

from datetime import datetime

import pytest

from app.db.database import SessionLocal
from app.db.models import ChatMessage, MemoryJobRun
from app.memory import memory_router
from app.memory import profile

_HEALTHY = memory_router.healthy
requires_chroma = pytest.mark.skipif(
    not _HEALTHY, reason="ChromaDB no disponible en el entorno de test"
)

SESION = "test-r65c-perfil"


def _limpiar_chat():
    db = SessionLocal()
    try:
        db.query(ChatMessage).filter(ChatMessage.session_id == SESION).delete(
            synchronize_session=False
        )
        db.query(MemoryJobRun).filter(MemoryJobRun.job_name == profile.JOB_PROFILE).delete(
            synchronize_session=False
        )
        db.commit()
    finally:
        db.close()


def _sembrar_usuario(*textos: str) -> list[int]:
    db = SessionLocal()
    try:
        ids = []
        for t in textos:
            m = ChatMessage(role="user", content=t, session_id=SESION)
            db.add(m)
            db.commit()
            db.refresh(m)
            ids.append(m.id)
        return ids
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _entorno_limpio():
    _limpiar_chat()
    yield
    _limpiar_chat()


# ---------------------------------------------------------------------------
# Parte 1 — funciones puras
# ---------------------------------------------------------------------------
def test_normalize_key_reconcilia_variantes_razonables():
    assert profile._normalize_key("Nombre") == profile._normalize_key("nombre")
    assert profile._normalize_key("Estilo de Comunicación") == "estilo_de_comunicacion"


def test_normalize_key_nunca_vacio():
    assert profile._normalize_key("") == "hecho"
    assert profile._normalize_key("¿¿¿???") == "hecho"


def test_extract_json_array_tolera_fences_y_texto_alrededor():
    texto = 'Aquí tienes:\n```json\n[{"key": "nombre", "value": "X"}]\n```\ngracias'
    assert profile._extract_json_array(texto) == [{"key": "nombre", "value": "X"}]


def test_extract_json_array_vacio_es_vacio():
    assert profile._extract_json_array("[]") == []


def test_extract_json_array_basura_no_rompe():
    assert profile._extract_json_array("esto no es json en absoluto") is None
    assert profile._extract_json_array("") is None
    assert profile._extract_json_array("{'no': 'es lista'}") is None


def test_build_chat_text_ignora_lineas_vacias():
    msgs = [
        ChatMessage(role="user", content="  "),
        ChatMessage(role="user", content="hola de verdad"),
    ]
    assert profile._build_chat_text(msgs) == "hola de verdad"


def test_build_chat_text_respeta_el_presupuesto():
    msgs = [ChatMessage(role="user", content="x" * 1000) for _ in range(20)]
    texto = profile._build_chat_text(msgs)
    assert len(texto) <= profile.MAX_CHARS_PER_RUN + 20  # + saltos de línea


# ---------------------------------------------------------------------------
# Parte 2 — extracción: el corazón del sprint (mock del MEL, sin red)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_extract_facts_hecho_estable(monkeypatch):
    """Criterio 1 (mitad extracción): un hecho duradero SE devuelve."""
    from app.mel import contracts as mel_contracts

    async def _fake_complete(req):
        assert req.policy_override == "economy", "el job nocturno debe pedir coste 0 primero"
        return mel_contracts.ExecutionResult(
            text='[{"key": "nombre", "value": "Se llama Alejandro"}]', ok=True,
        )

    monkeypatch.setattr("app.mel.complete", _fake_complete)
    hechos = await profile.extract_facts("me llamo Alejandro")
    assert hechos == [{"key": "nombre", "label": "nombre", "value": "Se llama Alejandro"}]


@pytest.mark.anyio
async def test_extract_facts_anecdota_no_se_guarda(monkeypatch):
    """Criterio 2: el modelo puede devolver [] y el sistema no inventa nada."""
    from app.mel import contracts as mel_contracts

    async def _fake_complete(req):
        return mel_contracts.ExecutionResult(text="[]", ok=True)

    monkeypatch.setattr("app.mel.complete", _fake_complete)
    assert await profile.extract_facts("hoy estoy agotado, ábreme el navegador") == []


@pytest.mark.anyio
async def test_extract_facts_descarta_entradas_incompletas(monkeypatch):
    from app.mel import contracts as mel_contracts

    async def _fake_complete(req):
        return mel_contracts.ExecutionResult(
            text='[{"key": "nombre"}, {"value": "sin key"}, '
                 '{"key": "ocupacion", "value": "Es ingeniero"}]',
            ok=True,
        )

    monkeypatch.setattr("app.mel.complete", _fake_complete)
    hechos = await profile.extract_facts("texto")
    assert [h["key"] for h in hechos] == ["ocupacion"]


@pytest.mark.anyio
async def test_extract_facts_falla_sin_romper(monkeypatch):
    """Fail-soft: si el MEL revienta, no hay hechos esta pasada — nunca excepción."""
    async def _fake_complete(req):
        raise RuntimeError("proveedor caído")

    monkeypatch.setattr("app.mel.complete", _fake_complete)
    assert await profile.extract_facts("cualquier cosa") == []


@pytest.mark.anyio
async def test_extract_facts_sin_texto_no_llama_al_mel(monkeypatch):
    llamado = {"veces": 0}

    async def _fake_complete(req):
        llamado["veces"] += 1
        from app.mel import contracts as mel_contracts
        return mel_contracts.ExecutionResult(text="[]", ok=True)

    monkeypatch.setattr("app.mel.complete", _fake_complete)
    assert await profile.extract_facts("   ") == []
    assert llamado["veces"] == 0


# ---------------------------------------------------------------------------
# Parte 3 — el destilado completo, contra el store REAL
# ---------------------------------------------------------------------------
@requires_chroma
@pytest.mark.anyio
async def test_distill_guarda_hechos_y_avanza_el_checkpoint(monkeypatch):
    from app.mel import contracts as mel_contracts

    async def _fake_complete(req):
        return mel_contracts.ExecutionResult(
            text='[{"key": "nombre", "value": "Se llama Alejandro"}]', ok=True,
        )

    monkeypatch.setattr("app.mel.complete", _fake_complete)
    _sembrar_usuario("me llamo Alejandro")

    resultado = await profile.distill()
    assert resultado["status"] == "ok"
    assert resultado["facts_stored"] == 1

    try:
        item = await memory_router.retrieve("mem_personal:profile:nombre")
        assert item is not None
        assert item.content == "Se llama Alejandro"

        # Segunda pasada sin mensajes nuevos: no reprocesa, no llama al MEL.
        llamado = {"veces": 0}

        async def _no_deberia_llamarse(req):
            llamado["veces"] += 1
            return mel_contracts.ExecutionResult(text="[]", ok=True)

        monkeypatch.setattr("app.mel.complete", _no_deberia_llamarse)
        resultado2 = await profile.distill()
        assert resultado2["messages_seen"] == 0
        assert llamado["veces"] == 0
    finally:
        from app.memory import MemoryType
        await memory_router.forget(MemoryType.PERSONAL, {"source": "profile"})


@requires_chroma
@pytest.mark.anyio
async def test_criterio_1_hecho_se_usa_en_conversacion_nueva_sin_relacion(monkeypatch):
    """El criterio de cierre #1, literal: destila un hecho y confirma que
    `memory_router.context()` (lo que el chat consulta en CUALQUIER conversación
    nueva, vía chat_service) lo trae de vuelta."""
    from app.mel import contracts as mel_contracts
    from app.memory import MemoryType

    async def _fake_complete(req):
        return mel_contracts.ExecutionResult(
            text='[{"key": "ocupacion", "value": "Se dedica a la ingeniería de datos"}]',
            ok=True,
        )

    monkeypatch.setattr("app.mel.complete", _fake_complete)
    _sembrar_usuario("trabajo como ingeniero de datos")
    await profile.distill()

    try:
        contexto = await memory_router.context(
            "¿a qué se dedica el usuario?", memory_types=[MemoryType.PERSONAL],
        )
        assert "ingeniería de datos" in contexto
    finally:
        await memory_router.forget(MemoryType.PERSONAL, {"source": "profile"})


@requires_chroma
@pytest.mark.anyio
async def test_criterio_3_repetir_un_hecho_actualiza_no_duplica(monkeypatch):
    from app.mel import contracts as mel_contracts
    from app.memory import MemoryType

    async def _primera(req):
        return mel_contracts.ExecutionResult(
            text='[{"key": "ciudad", "value": "Vive en Madrid"}]', ok=True,
        )

    monkeypatch.setattr("app.mel.complete", _primera)
    _sembrar_usuario("vivo en Madrid")
    await profile.distill()

    async def _segunda(req):
        return mel_contracts.ExecutionResult(
            text='[{"key": "ciudad", "value": "Vive en Barcelona"}]', ok=True,
        )

    monkeypatch.setattr("app.mel.complete", _segunda)
    _sembrar_usuario("me mudé a Barcelona")
    await profile.distill()

    try:
        item = await memory_router.retrieve("mem_personal:profile:ciudad")
        assert item is not None
        assert item.content == "Vive en Barcelona", "no se actualizó: quedó la versión vieja"

        hechos = profile.list_facts()
        ciudades = [h for h in hechos if h["key"] == "ciudad"]
        assert len(ciudades) == 1, "se duplicó en vez de actualizarse"
    finally:
        await memory_router.forget(MemoryType.PERSONAL, {"source": "profile"})


@requires_chroma
@pytest.mark.anyio
async def test_criterio_4_borrar_deja_de_aparecer(monkeypatch):
    from app.mel import contracts as mel_contracts
    from app.memory import MemoryType

    async def _fake_complete(req):
        return mel_contracts.ExecutionResult(
            text='[{"key": "mascota", "value": "Tiene un perro"}]', ok=True,
        )

    monkeypatch.setattr("app.mel.complete", _fake_complete)
    _sembrar_usuario("tengo un perro")
    await profile.distill()

    try:
        antes = [h["key"] for h in profile.list_facts()]
        assert "mascota" in antes

        borrado = await profile.delete_fact("mascota")
        assert borrado is True

        despues = [h["key"] for h in profile.list_facts()]
        assert "mascota" not in despues
        assert await memory_router.retrieve("mem_personal:profile:mascota") is None
    finally:
        await memory_router.forget(MemoryType.PERSONAL, {"source": "profile"})


@requires_chroma
@pytest.mark.anyio
async def test_borrar_hecho_inexistente_no_rompe():
    assert await profile.delete_fact("no_existe_de_verdad") is False


@requires_chroma
@pytest.mark.anyio
async def test_distill_sin_mensajes_nuevos_no_falla():
    """Base limpia (sin mensajes de usuario todavía): el job termina 'ok' con
    cero hechos, nunca en error."""
    resultado = await profile.distill()
    assert resultado["status"] == "ok"
    assert resultado["facts_stored"] == 0


@requires_chroma
@pytest.mark.anyio
async def test_facts_stored_refleja_lo_REALMENTE_guardado_no_lo_extraido(monkeypatch):
    """Hallazgo real de la verificación en vivo: `memory_router.store()` es
    fail-soft (devuelve "" si la memoria está caída, nunca lanza). Sin contar
    aparte, un fallo silencioso de la memoria se reportaría como "N hechos
    guardados" con el perfil realmente vacío."""
    from app.mel import contracts as mel_contracts

    async def _fake_complete(req):
        return mel_contracts.ExecutionResult(
            text='[{"key": "nombre", "value": "X"}, {"key": "ocupacion", "value": "Y"}]',
            ok=True,
        )

    async def _store_que_falla(*a, **k):
        return ""  # memoria caída, fail-soft por contrato

    monkeypatch.setattr("app.mel.complete", _fake_complete)
    monkeypatch.setattr(memory_router, "store", _store_que_falla)
    _sembrar_usuario("me llamo X, trabajo en Y")

    resultado = await profile.distill()
    assert resultado["facts_stored"] == 0, (
        "reportó hechos guardados que en realidad nunca se persistieron"
    )


@pytest.mark.anyio
async def test_descarta_hechos_que_son_el_ejemplo_del_prompt_copiado(monkeypatch):
    """Hallazgo REAL de la verificación en vivo (no un supuesto): un modelo
    económico, ante un mensaje sin hechos, devolvió los ejemplos ilustrativos
    del prompt literalmente en vez de []. Defensa en profundidad — el prompt
    ya lo pide, esto es el respaldo en código."""
    from app.mel import contracts as mel_contracts

    async def _fake_complete(req):
        return mel_contracts.ExecutionResult(
            text='[{"key": "nombre", "value": "Se llama Fulano"}, '
                 '{"key": "ocupacion", "value": "Trabaja como electricista"}]',
            ok=True,
        )

    monkeypatch.setattr("app.mel.complete", _fake_complete)
    assert await profile.extract_facts("hoy hace sol") == []


def test_extract_json_array_reconstruye_objetos_sueltos_sin_envolver():
    """Hallazgo real de la verificación en vivo: el modelo local a veces
    devuelve varios `{...}` sueltos, uno por línea, en vez de envolverlos en
    `[]`. Se reconstruye la lista a partir de los que sí parsean."""
    texto = '{"key": "nombre", "value": "X"}\n{"key": "ocupacion", "value": "Y"}'
    assert profile._extract_json_array(texto) == [
        {"key": "nombre", "value": "X"}, {"key": "ocupacion", "value": "Y"},
    ]


def test_extract_json_array_objeto_roto_no_tumba_a_los_demas():
    texto = '{"key": "nombre", "value": "X"}\n{esto no es json valido}\n{"key": "b", "value": "Y"}'
    assert profile._extract_json_array(texto) == [
        {"key": "nombre", "value": "X"}, {"key": "b", "value": "Y"},
    ]


@pytest.mark.anyio
async def test_extract_facts_tolera_objetos_json_sueltos_del_modelo(monkeypatch):
    from app.mel import contracts as mel_contracts

    async def _fake_complete(req):
        return mel_contracts.ExecutionResult(
            text='{"key": "nombre", "value": "Se llama X"}\n{"key": "ocupacion", "value": "Es Y"}',
            ok=True,
        )

    monkeypatch.setattr("app.mel.complete", _fake_complete)
    hechos = await profile.extract_facts("me llamo X, soy Y")
    assert {h["key"] for h in hechos} == {"nombre", "ocupacion"}
