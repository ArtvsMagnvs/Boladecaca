# tests/test_selector_modelos.py — [2026-08-04] EL SELECTOR DE MODELOS NO OCULTA
# NADA.
#
# EL FALLO QUE CIERRA (reportado por el usuario TRES veces): en el chat de los
# agentes solo aparecían los modelos de MiniMax. Causa raíz: `ChatComposer.tsx`
# tenía un `continue` que BORRABA de la lista, sin decir nada, todo modelo
# marcado no apto para chat/agentic. Como `unfit` se alimenta del catálogo (los
# CLI de Claude y Codex) Y de la medición del task-bench, en una máquina real
# desaparecía casi todo y desde fuera parecía "faltan modelos".
#
# El contrato que se fija aquí, y que ningún cambio futuro debe romper:
#   1. `list_models()` NUNCA omite un (proveedor, modelo) configurado — ni
#      siquiera uno no apto. Ocultar es lo que generó el bug.
#   2. Expone POR SEPARADO de dónde viene la no-aptitud (catálogo vs medición),
#      para que la UI pueda decir el MOTIVO en vez de un hueco silencioso.
#   3. `unfit` (la unión) se conserva: Ajustes → Inteligencia ya lo consume.
from __future__ import annotations

import app.mel as mel
from app.mel import benchmark as _bench
from app.mel.contracts import ModelRef


def _fake_registry(monkeypatch, refs: list[ModelRef]):
    monkeypatch.setattr(mel._registry, "list_available", lambda: refs)


def test_un_modelo_no_apto_por_catalogo_sigue_apareciendo(monkeypatch):
    """Claude CLI es no apto para el bucle de tools (decisión de catálogo, por
    un fallo real de producción) — pero TIENE que salir en la lista. Que no
    saliera es exactamente lo que el usuario reportó tres veces."""
    _fake_registry(monkeypatch, [
        ModelRef(provider="claude_code", model="opus", is_local=False),
        ModelRef(provider="minimax", model="MiniMax-M2.7-highspeed", is_local=False),
    ])
    keys = {m["key"] for m in mel.list_models()}
    assert "claude_code:opus" in keys, "un modelo no apto por catálogo se está ocultando"
    assert "minimax:MiniMax-M2.7-highspeed" in keys


def test_el_motivo_de_la_no_aptitud_viaja_separado(monkeypatch):
    """La UI necesita distinguir 'excluido por diseño' de 'falló las pruebas'
    para poder explicarlo. Sin esto solo puede decir 'no está'."""
    _fake_registry(monkeypatch, [ModelRef(provider="claude_code", model="opus", is_local=False)])
    m = mel.list_models()[0]
    assert "agentic" in m["unfit_catalog"]
    assert m["unfit_measured"] == []
    # La unión se conserva para quien ya la consumía (Ajustes → Inteligencia).
    assert "agentic" in m["unfit"]


def test_la_no_aptitud_medida_se_reporta_como_medida(monkeypatch):
    """Un modelo que el task-bench vio fallar de verdad se marca como MEDIDO,
    no como decisión de catálogo — son cosas distintas y se explican distinto.

    [B·WEB-2, 2026-08-05] `llama3` es CIEGO, así que desde la activación de la
    capacidad de visión también arrastra `vision` en `unfit_catalog`.
    [LC1, 2026-08-07] Y desde la capacidad de APRENDIZAJE arrastra también
    `learn`: un modelo pequeño no sirve de juez, y eso es dato de catálogo igual
    que la ceguera. Lo que este test fija no es la lista concreta —crecerá cada
    vez que se active una capacidad que dependa del modelo— sino la SEPARACIÓN
    de las dos fuentes: lo que decide el catálogo y lo que se MIDIÓ fallando."""
    _fake_registry(monkeypatch, [ModelRef(provider="ollama", model="llama3", is_local=True)])
    monkeypatch.setattr(_bench, "measured_unfit", lambda ref: {"agentic"})
    m = mel.list_models()[0]
    assert m["unfit_measured"] == ["agentic"]
    # Ciego y pequeño: ni ve imágenes ni sirve para juzgar. Las dos por catálogo.
    assert m["unfit_catalog"] == ["learn", "vision"]
    assert "agentic" in m["unfit"]


def test_un_modelo_apto_no_arrastra_marcas(monkeypatch):
    """No-regresión: lo que sí vale sale limpio, sin motivo que mostrar.

    [B·WEB-2] MiniMax tampoco acepta imágenes en la API que usa Aithera, así
    que `vision` es su ÚNICA marca. Para comprobar de verdad "sin marcas" hace
    falta un modelo que sí lo pueda todo — Gemini."""
    _fake_registry(monkeypatch, [
        ModelRef(provider="minimax", model="MiniMax-M2.7-highspeed", is_local=False),
    ])
    monkeypatch.setattr(_bench, "measured_unfit", lambda ref: set())
    m = mel.list_models()[0]
    assert m["unfit"] == ["vision"]
    assert m["unfit_measured"] == []

    _fake_registry(monkeypatch, [ModelRef(provider="gemini", model="gemini-3.5-flash")])
    g = mel.list_models()[0]
    assert g["unfit"] == []
    assert g["unfit_catalog"] == []
    assert g["unfit_measured"] == []


def test_ningun_modelo_configurado_se_pierde(monkeypatch):
    """El invariante de fondo: tantos modelos salen como entran. Es la barrera
    contra que alguien vuelva a 'limpiar' la lista filtrando por aptitud."""
    refs = [
        ModelRef(provider="claude_code", model="opus", is_local=False),
        ModelRef(provider="claude_code", model="sonnet", is_local=False),
        ModelRef(provider="codex", model="gpt-5.1-codex", is_local=False),
        ModelRef(provider="ollama", model="llama3", is_local=True),
        ModelRef(provider="minimax", model="MiniMax-M2.7-highspeed", is_local=False),
    ]
    _fake_registry(monkeypatch, refs)
    monkeypatch.setattr(_bench, "measured_unfit", lambda ref: {"agentic"})
    out = mel.list_models()
    assert len(out) == len(refs)
    assert {m["key"] for m in out} == {r.key for r in refs}
