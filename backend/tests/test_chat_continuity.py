# tests/test_chat_continuity.py — R6.5b: continuidad real de la conversación
#
# EL PROBLEMA QUE CIERRA ESTE SPRINT, en las palabras del usuario: «el chat no
# recuerda ni siquiera el mensaje anterior dentro de la misma sesión de chat».
#
# Eran DOS agujeros independientes, y por eso hay dos bloques de tests:
#   1. Al modelo nunca se le mandaban los turnos anteriores (R6.5a abrió el
#      canal; aquí se llena).
#   2. La búsqueda semántica en el MOS usaba el mensaje actual A SECAS, así que
#      un «¿y cuánto cuesta?» no se parecía a nada y no recuperaba nada.
#
# El tercer bloque es el que evita el fallo MÁS caro de todos: mezclar dos
# pestañas de chat distintas. Eso no es "poca memoria", es filtrar una
# conversación dentro de otra.
from __future__ import annotations

import pytest

from app.db.database import SessionLocal
from app.db.models import ChatMessage
from app.services import chat_service


SESION_A = "test-r65b-sesion-a"
SESION_B = "test-r65b-sesion-b"


def _limpiar():
    db = SessionLocal()
    try:
        db.query(ChatMessage).filter(
            ChatMessage.session_id.in_([SESION_A, SESION_B])
        ).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def _sembrar(session_id: str, turnos: list[tuple[str, str]]):
    db = SessionLocal()
    try:
        for rol, texto in turnos:
            db.add(ChatMessage(role=rol, content=texto, session_id=session_id))
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _entorno_limpio():
    # Se limpia al ENTRAR y al SALIR: si un test anterior murió a medias, sus
    # restos no deben contaminar a éste (misma lección que en A4).
    _limpiar()
    yield
    _limpiar()


# ---------------------------------------------------------------------------
# 1 — La ventana de turnos
# ---------------------------------------------------------------------------
def test_recupera_los_turnos_de_la_conversacion_en_orden():
    _sembrar(SESION_A, [
        ("user", "quiero una bici de montaña"),
        ("assistant", "te recomiendo la Rockrider 540"),
        ("user", "¿y cuánto cuesta?"),
    ])
    turnos = chat_service.recent_turns(SESION_A)

    assert [t["role"] for t in turnos] == ["user", "assistant", "user"]
    assert turnos[0]["content"] == "quiero una bici de montaña"
    assert turnos[-1]["content"] == "¿y cuánto cuesta?"


def test_sin_sesion_no_hay_historial():
    """Un mensaje sin conversación (el AE, un agente, un canal sin sesión) no
    tiene hilo que recuperar. Adivinarle uno mezclaría conversaciones ajenas."""
    _sembrar(SESION_A, [("user", "hola")])
    assert chat_service.recent_turns(None) == []
    assert chat_service.recent_turns("") == []


def test_el_presupuesto_de_turnos_recorta_lo_VIEJO():
    """Sin tope, una conversación larga se come la ventana del modelo. Lo que
    se suelta tiene que ser lo antiguo: lo reciente es lo que da continuidad."""
    _sembrar(SESION_A, [("user", f"mensaje {i}") for i in range(30)])
    turnos = chat_service.recent_turns(SESION_A, max_turns=5)

    assert len(turnos) == 5
    assert turnos[-1]["content"] == "mensaje 29", "se perdió el turno más reciente"
    assert turnos[0]["content"] == "mensaje 25"


def test_el_presupuesto_de_caracteres_tambien_corta():
    _sembrar(SESION_A, [("user", "x" * 1000) for _ in range(10)])
    turnos = chat_service.recent_turns(SESION_A, max_turns=10, max_chars=2500)

    assert 0 < len(turnos) <= 3
    assert sum(len(t["content"]) for t in turnos) <= 3000


def test_un_solo_turno_gigante_no_deja_al_modelo_sin_contexto():
    """Si el único turno reciente ya excede el presupuesto, se manda igualmente:
    devolver [] dejaría la conversación sin hilo por ser demasiado buena."""
    _sembrar(SESION_A, [("user", "y" * 50_000)])
    assert len(chat_service.recent_turns(SESION_A, max_chars=100)) == 1


def test_los_turnos_vacios_no_ensucian_el_historial():
    """Una respuesta abortada deja una fila vacía. Mandarla al modelo es basura
    (y algunos proveedores devuelven 400 con un content en blanco)."""
    _sembrar(SESION_A, [
        ("user", "hola"),
        ("assistant", "   "),
        ("user", "¿sigues ahí?"),
    ])
    turnos = chat_service.recent_turns(SESION_A)
    assert len(turnos) == 2
    assert all(t["content"].strip() for t in turnos)


# ---------------------------------------------------------------------------
# 2 — Aislamiento entre pestañas (el fallo más caro)
# ---------------------------------------------------------------------------
def test_dos_pestanas_no_se_mezclan():
    _sembrar(SESION_A, [("user", "hablemos de bicis")])
    _sembrar(SESION_B, [("user", "hablemos de mi divorcio")])

    a = chat_service.recent_turns(SESION_A)
    b = chat_service.recent_turns(SESION_B)

    assert len(a) == 1 and len(b) == 1
    assert "bicis" in a[0]["content"]
    assert "divorcio" in b[0]["content"]
    assert "divorcio" not in str(a), "una conversación se filtró dentro de otra"


def test_los_mensajes_sin_sesion_no_se_cuelan_en_ninguna():
    """Los ~190 mensajes anteriores a R6.5b tienen session_id=NULL. No pueden
    aparecer como historial de una conversación que no era la suya."""
    db = SessionLocal()
    try:
        huerfano = ChatMessage(role="user", content="mensaje viejo sin sesión")
        db.add(huerfano)
        db.commit()
        huerfano_id = huerfano.id
    finally:
        db.close()

    try:
        _sembrar(SESION_A, [("user", "conversación nueva")])
        turnos = chat_service.recent_turns(SESION_A)
        assert len(turnos) == 1
        assert "viejo" not in str(turnos)
    finally:
        db = SessionLocal()
        try:
            db.query(ChatMessage).filter(ChatMessage.id == huerfano_id).delete()
            db.commit()
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 3 — La consulta semántica (el arreglo de más impacto)
# ---------------------------------------------------------------------------
def test_la_consulta_al_MOS_incluye_el_turno_anterior():
    """SIN esto, «¿y cuánto cuesta?» no se parece a NADA en la memoria y la
    búsqueda vuelve vacía. Con el turno previo, la consulta tiene de qué
    agarrarse. Es la razón de que Aithera recordara cosas de hace días pero no
    de qué se estaba hablando hace diez segundos."""
    historial = [
        {"role": "user", "content": "quiero una bici de montaña"},
        {"role": "assistant", "content": "te recomiendo la Rockrider 540"},
    ]
    consulta = chat_service._memory_query("¿y cuánto cuesta?", historial)

    assert "bici de montaña" in consulta
    assert "¿y cuánto cuesta?" in consulta


def test_la_consulta_usa_el_turno_del_USUARIO_no_el_del_asistente():
    """La respuesta del asistente es larga y llena de relleno; lo que ancla la
    búsqueda es lo que pidió el usuario."""
    consulta = chat_service._memory_query("¿y eso?", [
        {"role": "user", "content": "ANCLA"},
        {"role": "assistant", "content": "RELLENO " * 200},
    ])
    assert "ANCLA" in consulta
    assert "RELLENO" not in consulta


def test_sin_historial_la_consulta_es_el_mensaje_de_siempre():
    """NO-REGRESIÓN: el primer mensaje de una conversación tiene que buscar
    exactamente igual que antes de este sprint."""
    assert chat_service._memory_query("hola", []) == "hola"


def test_la_consulta_no_crece_sin_limite():
    """Es una CONSULTA, no contexto: meterle un turno anterior de 10.000
    caracteres degradaría la búsqueda semántica en vez de mejorarla."""
    consulta = chat_service._memory_query("¿y eso?", [
        {"role": "user", "content": "z" * 10_000},
    ])
    assert len(consulta) < chat_service.QUERY_PREV_CHARS + 100


# ---------------------------------------------------------------------------
# 4 — La tubería entera: de `answer()` al proveedor
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_answer_manda_los_turnos_previos_al_modelo(monkeypatch):
    """El criterio de cierre del sprint: preguntar «¿y cuánto cuesta?» después
    de hablar de una bici tiene que llegar al modelo CON la bici delante."""
    from app.mel import contracts as mel_contracts

    visto = {}

    async def _fake_complete(req):
        visto["messages"] = req.messages
        visto["prompt"] = req.prompt
        return mel_contracts.ExecutionResult(text="cuesta 500 €", ok=True)

    monkeypatch.setattr("app.mel.complete", _fake_complete)
    monkeypatch.setattr(chat_service, "build_system_prompt",
                        lambda *a, **k: _async_str("sys"))

    _sembrar(SESION_A, [
        ("user", "quiero una bici de montaña"),
        ("assistant", "te recomiendo la Rockrider 540"),
    ])

    res = await chat_service.answer("¿y cuánto cuesta?", session_id=SESION_A,
                                    persist_chat_message=False)

    assert res.text == "cuesta 500 €"
    assert visto["prompt"] == "¿y cuánto cuesta?"
    assert [m["content"] for m in visto["messages"]] == [
        "quiero una bici de montaña", "te recomiendo la Rockrider 540",
    ], "el modelo recibió el mensaje suelto, sin la conversación"


@pytest.mark.anyio
async def test_sin_sesion_answer_se_comporta_como_antes(monkeypatch):
    """NO-REGRESIÓN dura: el AE, los agentes y cualquier canal sin conversación
    tienen que seguir mandando exactamente lo de siempre — un prompt y nada más."""
    from app.mel import contracts as mel_contracts

    visto = {}

    async def _fake_complete(req):
        visto["messages"] = req.messages
        return mel_contracts.ExecutionResult(text="ok", ok=True)

    monkeypatch.setattr("app.mel.complete", _fake_complete)
    monkeypatch.setattr(chat_service, "build_system_prompt",
                        lambda *a, **k: _async_str("sys"))

    await chat_service.answer("hola", persist_chat_message=False)
    assert visto["messages"] == []


@pytest.mark.anyio
async def test_answer_guarda_el_turno_en_su_conversacion():
    """Si el turno nuevo no se etiqueta con la sesión, la continuidad dura
    exactamente un mensaje: la siguiente pregunta ya no lo encontraría."""
    from app.mel import contracts as mel_contracts

    async def _fake_complete(req):
        return mel_contracts.ExecutionResult(text="respuesta", ok=True)

    import app.mel as mel
    original = mel.complete
    mel.complete = _fake_complete
    try:
        await chat_service.answer("primer mensaje", session_id=SESION_A)
    finally:
        mel.complete = original

    turnos = chat_service.recent_turns(SESION_A)
    assert [t["content"] for t in turnos] == ["primer mensaje", "respuesta"]


async def _async_str(v):
    return v


def test_la_consulta_no_duplica_el_mensaje_actual():
    """Hallazgo de la verificación en vivo de R6.5b: si quien llama lee el
    historial DESPUÉS de persistir el turno, el "turno anterior" es el mensaje
    actual y la consulta salía duplicada («¿y cuánto cuesta?\n¿y cuánto
    cuesta?»). Se salta al turno de usuario de antes."""
    consulta = chat_service._memory_query("¿y cuánto cuesta?", [
        {"role": "user", "content": "quiero una bici"},
        {"role": "assistant", "content": "la Rockrider 540"},
        {"role": "user", "content": "¿y cuánto cuesta?"},   # ya persistido
    ])
    assert consulta.count("¿y cuánto cuesta?") == 1
    assert "quiero una bici" in consulta
