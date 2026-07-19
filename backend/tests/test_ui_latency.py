# tests/test_ui_latency.py — la UI nunca espera a la red (2026-07-19)
#
# EL BUG QUE BLINDA (reportado por el usuario, reproducible): tras borrar un
# agente/misión y volver a la pantalla, la interfaz se quedaba ~30 s sin
# responder. No era el hilo del navegador bloqueado: eran peticiones colgadas
# ocupando las 6 conexiones que Chromium permite por origen, con el input
# `disabled` esperando una respuesta que no llegaba.
#
# Del lado del backend, el mayor generador de esas peticiones colgadas era
# `GET /api/ai/status`: hacía un health check REAL (una petición de chat al
# proveedor, 10-15 s sin internet) y su caché de 30 s tenía el MISMO valor que
# el sondeo del Sidebar, así que no acertaba casi nunca.
from __future__ import annotations

import asyncio
import time

import pytest

from app.core.latency import StaleWhileRevalidate, with_budget


# ---------------------------------------------------------------------------
# El primitivo: presupuesto de latencia
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_with_budget_corta_lo_que_tarda_demasiado():
    async def _lenta():
        await asyncio.sleep(5)
        return "tarde"

    t0 = time.monotonic()
    out = await with_budget(_lenta(), ms=100, default="por defecto", label="prueba")
    elapsed = time.monotonic() - t0

    assert out == "por defecto"
    assert elapsed < 1.0, f"no respetó el presupuesto: {elapsed:.2f}s"


@pytest.mark.anyio
async def test_with_budget_nunca_lanza():
    """Quien llama es una ruta de UI: su obligación es responder algo."""
    async def _explota():
        raise RuntimeError("boom")

    assert await with_budget(_explota(), ms=100, default="ok") == "ok"


# ---------------------------------------------------------------------------
# Stale-while-revalidate: responde YA, refresca por detrás
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_el_valor_rancio_se_sirve_al_instante_sin_esperar_a_la_red():
    """El corazón del arreglo: con un valor previo, una sonda LENTA no puede
    hacer esperar a la UI. Antes, cada consulta pagaba los 10-15 s."""
    cache = StaleWhileRevalidate(ttl_s=0.01, first_ms=2000)   # caduca enseguida

    async def _sonda_lenta():
        await asyncio.sleep(5)
        return "fresco"

    cache.put("p", "conocido")
    await asyncio.sleep(0.05)                                  # ya está rancio

    t0 = time.monotonic()
    out = await cache.get("p", _sonda_lenta, default=None)
    elapsed = time.monotonic() - t0

    assert out == "conocido", "debería servir el valor rancio"
    assert elapsed < 0.5, f"esperó a la red: {elapsed:.2f}s"


@pytest.mark.anyio
async def test_solo_un_refresco_en_vuelo_por_clave():
    """N peticiones concurrentes NO pueden disparar N llamadas a un proveedor
    que ya sabemos que va lento."""
    cache = StaleWhileRevalidate(ttl_s=0.01)
    llamadas = {"n": 0}

    async def _sonda():
        llamadas["n"] += 1
        await asyncio.sleep(0.3)
        return "fresco"

    cache.put("p", "conocido")
    await asyncio.sleep(0.05)

    await asyncio.gather(*[cache.get("p", _sonda) for _ in range(10)])
    await asyncio.sleep(0.05)
    assert llamadas["n"] == 1, f"se dispararon {llamadas['n']} sondas a la vez"


@pytest.mark.anyio
async def test_la_primera_vez_espera_pero_poco():
    """Sin nada cacheado no queda otra que esperar — pero con presupuesto, no
    los 10-15 s del proveedor."""
    cache = StaleWhileRevalidate(ttl_s=60, first_ms=100)

    async def _sonda_lenta():
        await asyncio.sleep(5)
        return "fresco"

    t0 = time.monotonic()
    out = await cache.get("nueva", _sonda_lenta, default="desconocido")
    elapsed = time.monotonic() - t0

    assert out == "desconocido"
    assert elapsed < 1.0, f"la primera consulta tardó {elapsed:.2f}s"


@pytest.mark.anyio
async def test_el_refresco_de_fondo_acaba_actualizando_el_valor():
    """Servir lo rancio no puede significar quedarse rancio para siempre."""
    cache = StaleWhileRevalidate(ttl_s=0.01)

    async def _sonda():
        return "fresco"

    cache.put("p", "viejo")
    await asyncio.sleep(0.05)

    assert await cache.get("p", _sonda) == "viejo"    # sirve lo que hay
    await asyncio.sleep(0.05)                          # deja correr el refresco
    assert await cache.get("p", _sonda) == "fresco"    # ya actualizado


# ---------------------------------------------------------------------------
# El caso real: /api/ai/status con un proveedor que no responde
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_ai_status_no_espera_a_un_proveedor_caido(monkeypatch):
    """Reproduce el escenario del usuario: proveedor inalcanzable. La primera
    consulta paga el presupuesto corto; las siguientes responden al instante en
    vez de volver a colgarse 10 s cada 30 s."""
    from app.ai.ai_manager import ai_manager

    async def _health_colgado():
        await asyncio.sleep(30)
        return True

    if ai_manager.current_provider is None:
        pytest.skip("sin proveedor activo en este entorno")

    monkeypatch.setattr(ai_manager.current_provider, "health_check", _health_colgado)
    # Caché limpia: se fuerza el camino de "primera vez".
    ai_manager._health = type(ai_manager._health)(ttl_s=120.0, first_ms=300)

    t0 = time.monotonic()
    primera = await ai_manager.health_check()
    t_primera = time.monotonic() - t0

    t0 = time.monotonic()
    segunda = await ai_manager.health_check()
    t_segunda = time.monotonic() - t0

    assert t_primera < 2.0, f"la primera consulta tardó {t_primera:.2f}s"
    assert t_segunda < 0.5, f"la segunda tardó {t_segunda:.2f}s (debería ser caché)"
    assert primera["healthy"] is False        # honesto: no se pudo comprobar
    assert "provider" in segunda
