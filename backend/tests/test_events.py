# tests/test_events.py — Event Bus (V0.85 M2, [Δ] doc 17 §8)
#
# Cobertura exigida por doc 17 §8: subscribe/emit/unsubscribe, comodin,
# aislamiento de excepciones, emit sin suscriptores, payload inmutable (frozen).
import asyncio

import pytest

from app.core.events import Event, emit, subscribe, unsubscribe


@pytest.mark.anyio
async def test_emit_sin_suscriptores_no_falla():
    """El caso normal: emitir hacia el vacio es gratis y no lanza."""
    emit("nadie.escucha", source="test", payload={"x": 1})
    await asyncio.sleep(0)  # deja correr cualquier task pendiente (no deberia haber)


@pytest.mark.anyio
async def test_subscribe_y_emit_entregan_el_evento():
    received: list[Event] = []

    async def handler(event: Event) -> None:
        received.append(event)

    subscribe("memory.ingested", handler)
    try:
        emit("memory.ingested", source="mos", payload={"job": "x", "items_new": 3})
        await asyncio.sleep(0.05)  # el handler corre en un create_task
        assert len(received) == 1
        ev = received[0]
        assert ev.name == "memory.ingested"
        assert ev.source == "mos"
        assert ev.payload == {"job": "x", "items_new": 3}
        assert ev.ts is not None
    finally:
        unsubscribe("memory.ingested", handler)


@pytest.mark.anyio
async def test_comodin_recibe_todos_los_eventos():
    received: list[str] = []

    async def handler(event: Event) -> None:
        received.append(event.name)

    subscribe("*", handler)
    try:
        emit("email.triaged", source="mos", payload={"email_id": "1", "category": "urgente"})
        emit("otro.evento", source="test")
        await asyncio.sleep(0.05)
        assert "email.triaged" in received
        assert "otro.evento" in received
    finally:
        unsubscribe("*", handler)


@pytest.mark.anyio
async def test_unsubscribe_detiene_la_entrega():
    received: list[Event] = []

    async def handler(event: Event) -> None:
        received.append(event)

    subscribe("x.y", handler)
    unsubscribe("x.y", handler)
    emit("x.y", source="test")
    await asyncio.sleep(0.05)
    assert received == []


@pytest.mark.anyio
async def test_handler_roto_no_afecta_a_otros_handlers():
    """Aislamiento total (doc 17 §1/§8): una excepcion en un handler se
    loguea y NUNCA rompe al emisor ni a los demas handlers."""
    good_received: list[Event] = []

    async def bad_handler(event: Event) -> None:
        raise RuntimeError("handler roto a proposito")

    async def good_handler(event: Event) -> None:
        good_received.append(event)

    subscribe("z.w", bad_handler)
    subscribe("z.w", good_handler)
    try:
        emit("z.w", source="test")  # no debe lanzar
        await asyncio.sleep(0.05)
        assert len(good_received) == 1
    finally:
        unsubscribe("z.w", bad_handler)
        unsubscribe("z.w", good_handler)


def test_event_es_inmutable():
    from datetime import datetime

    ev = Event(name="a.b", source="test", ts=datetime.utcnow(), payload={"k": "v"})
    with pytest.raises(Exception):
        ev.name = "otro"  # type: ignore[misc]
