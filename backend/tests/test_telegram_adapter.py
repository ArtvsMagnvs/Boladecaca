# tests/test_telegram_adapter.py
#
# V0.8 (PLAN_MAESTRO_2026): tests del TelegramAdapter SIN red ni la lib
# python-telegram-bot. Se validan las piezas puras y testeables:
#   - to_envelope() con un doble de Update (SimpleNamespace)
#   - authorize()/is_allowed() (whitelist de chat_id)
#   - formateadores de comandos con una BD en memoria
# El polling (start/stop) y los callbacks de telegram NO se testean aqui:
# son cableado sobre la lib externa (integracion manual).

from types import SimpleNamespace

import pytest

from app.gateway.adapters.telegram_adapter import (
    TelegramAdapter,
    format_proyectos,
    format_tareas,
    format_estado,
)


def _update(chat_id=123, text="hola", message_id=7):
    """Doble minimo de telegram.Update: solo los atributos que lee el adapter."""
    return SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id),
        effective_message=SimpleNamespace(text=text, message_id=message_id),
        message=SimpleNamespace(text=text, message_id=message_id),
    )


# ----------------------------------------------------------------------
# whitelist / authorize
# ----------------------------------------------------------------------

def test_is_allowed_normaliza_int_y_str():
    ad = TelegramAdapter("t", {"123", "456"})
    assert ad.is_allowed(123) is True      # int
    assert ad.is_allowed("123") is True    # str
    assert ad.is_allowed(999) is False


def test_whitelist_vacia_cierra_el_canal():
    ad = TelegramAdapter("t", set())
    assert ad.is_allowed(123) is False


@pytest.mark.anyio
async def test_authorize_usa_la_whitelist():
    ad = TelegramAdapter("t", {"123"})
    env_ok = await ad.to_envelope(_update(chat_id=123))
    env_no = await ad.to_envelope(_update(chat_id=888))
    assert await ad.authorize(env_ok) is True
    assert await ad.authorize(env_no) is False


# ----------------------------------------------------------------------
# to_envelope
# ----------------------------------------------------------------------

@pytest.mark.anyio
async def test_to_envelope_mapea_campos():
    ad = TelegramAdapter("t", {"123"})
    env = await ad.to_envelope(_update(chat_id=123, text="qué tal", message_id=42))
    assert env.channel == "telegram"
    assert env.user_ref == "123"
    assert env.text == "qué tal"
    assert env.metadata["message_id"] == 42


@pytest.mark.anyio
async def test_to_envelope_tolera_mensaje_sin_texto():
    ad = TelegramAdapter("t", {"123"})
    upd = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123),
        effective_message=SimpleNamespace(text=None, message_id=1),
        message=None,
    )
    env = await ad.to_envelope(upd)
    assert env.text == ""
    assert env.user_ref == "123"


# ----------------------------------------------------------------------
# formateadores de comandos (BD en memoria via fixture db_session)
# ----------------------------------------------------------------------

def test_format_proyectos_vacio(db_session):
    assert "No tienes proyectos" in format_proyectos(db_session)


def test_format_proyectos_lista(db_session):
    from app.db.models import Project
    db_session.add(Project(name="Aithera", status="active", progress=70.0))
    db_session.commit()
    out = format_proyectos(db_session)
    assert "Aithera" in out and "70%" in out


def test_format_tareas_vacio(db_session):
    assert "pendientes" in format_tareas(db_session)


def test_format_tareas_excluye_completadas(db_session):
    from app.db.models import Task
    db_session.add(Task(title="Pendiente X", status="pending", priority="high"))
    db_session.add(Task(title="Ya hecha", status="done", priority="low"))
    db_session.commit()
    out = format_tareas(db_session)
    assert "Pendiente X" in out
    assert "Ya hecha" not in out


def test_format_estado_cuenta(db_session):
    from app.db.models import Project, Task
    db_session.add(Project(name="P1", status="active"))
    db_session.add(Task(title="T1", status="pending", priority="medium"))
    db_session.commit()
    out = format_estado(db_session)
    assert "Proyectos activos: 1" in out
    assert "Tareas pendientes: 1" in out
