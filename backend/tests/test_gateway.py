# tests/test_gateway.py
#
# V0.8 (PLAN_MAESTRO_2026, B... Gateway multi-canal): tests del nucleo
# channel-agnostic. Los adapters reales (Telegram, Web) llegan despues; aqui
# validamos el CONTRATO del esqueleto con un adapter falso en memoria.

import pytest

from app.gateway import (
    Gateway,
    GatewayError,
    ChannelAdapter,
    MessageEnvelope,
    OutboundMessage,
)


class FakeAdapter(ChannelAdapter):
    """Adapter de test: guarda lo entregado y permite forzar authorize."""

    def __init__(self, name="fake", authorized=True):
        self.name = name
        self._authorized = authorized
        self.delivered = []          # OutboundMessages entregados
        self.started = False
        self.stopped = False

    async def to_envelope(self, raw):
        return MessageEnvelope(channel=self.name, user_ref="u1", text=str(raw))

    async def deliver(self, message, envelope):
        self.delivered.append(message)

    async def authorize(self, envelope):
        return self._authorized

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True


def _envelope(channel="fake", text="hola"):
    return MessageEnvelope(channel=channel, user_ref="u1", text=text)


# ----------------------------------------------------------------------
# Envelope
# ----------------------------------------------------------------------

def test_envelope_genera_id_unico():
    a = MessageEnvelope(channel="web", user_ref="s1")
    b = MessageEnvelope(channel="web", user_ref="s1")
    assert a.envelope_id and b.envelope_id and a.envelope_id != b.envelope_id


# ----------------------------------------------------------------------
# Registro de adapters
# ----------------------------------------------------------------------

def test_register_y_listar():
    gw = Gateway()
    ad = FakeAdapter("telegram")
    gw.register(ad)
    assert "telegram" in gw.adapters()


def test_register_normaliza_nombre():
    gw = Gateway()
    gw.register(FakeAdapter("  Telegram  "))
    assert "telegram" in gw.adapters()


def test_register_sin_nombre_falla():
    gw = Gateway()
    with pytest.raises(GatewayError):
        gw.register(FakeAdapter(""))


def test_register_duplicado_falla():
    gw = Gateway()
    gw.register(FakeAdapter("web"))
    with pytest.raises(GatewayError):
        gw.register(FakeAdapter("web"))


# ----------------------------------------------------------------------
# Dispatch
# ----------------------------------------------------------------------

@pytest.mark.anyio
async def test_dispatch_canal_desconocido_explota():
    gw = Gateway()
    with pytest.raises(GatewayError):
        await gw.dispatch(_envelope("fantasma"))


@pytest.mark.anyio
async def test_dispatch_llama_handler_y_entrega():
    async def handler(env):
        return f"eco: {env.text}"

    gw = Gateway(handler=handler)
    ad = FakeAdapter("fake")
    gw.register(ad)

    out = await gw.dispatch(_envelope(text="ping"))
    assert out.text == "eco: ping"
    assert not out.error
    assert ad.delivered and ad.delivered[0].text == "eco: ping"
    # correlacion de envelope_id
    assert out.envelope_id


@pytest.mark.anyio
async def test_dispatch_handler_devuelve_outbound_completo():
    async def handler(env):
        return OutboundMessage(text="rico", metadata={"foo": "bar"})

    gw = Gateway(handler=handler)
    gw.register(FakeAdapter("fake"))
    out = await gw.dispatch(_envelope())
    assert out.text == "rico"
    assert out.metadata["foo"] == "bar"
    assert out.envelope_id  # se rellena si venia vacio


@pytest.mark.anyio
async def test_dispatch_no_autorizado_no_llama_handler():
    llamado = {"v": False}

    async def handler(env):
        llamado["v"] = True
        return "no deberia"

    gw = Gateway(handler=handler)
    ad = FakeAdapter("fake", authorized=False)
    gw.register(ad)

    out = await gw.dispatch(_envelope())
    assert out.error is True
    assert out.metadata.get("reason") == "unauthorized"
    assert llamado["v"] is False          # el handler NI se toco
    assert ad.delivered[0].error is True  # el rechazo se entrego al usuario


@pytest.mark.anyio
async def test_dispatch_handler_falla_es_fail_soft():
    async def handler(env):
        raise RuntimeError("boom")

    gw = Gateway(handler=handler)
    ad = FakeAdapter("fake")
    gw.register(ad)

    out = await gw.dispatch(_envelope())
    assert out.error is True
    assert out.metadata.get("exception") == "RuntimeError"
    assert ad.delivered  # el usuario recibio un mensaje amable, no una excepcion


@pytest.mark.anyio
async def test_set_handler_reemplaza_el_handler():
    gw = Gateway()
    gw.register(FakeAdapter("fake"))

    async def nuevo(env):
        return "orchestrator v1.0"

    gw.set_handler(nuevo)
    out = await gw.dispatch(_envelope())
    assert out.text == "orchestrator v1.0"


# ----------------------------------------------------------------------
# Ciclo de vida
# ----------------------------------------------------------------------

@pytest.mark.anyio
async def test_start_all_y_stop_all():
    gw = Gateway()
    a, b = FakeAdapter("uno"), FakeAdapter("dos")
    gw.register(a)
    gw.register(b)
    await gw.start_all()
    assert a.started and b.started
    await gw.stop_all()
    assert a.stopped and b.stopped
