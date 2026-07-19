# tests/test_repetition_guard.py — cortar al modelo cuando se atasca
#
# EL CASO REAL (2026-07-19): el usuario preguntó cómo funcionaba el motor de
# herramientas. MiniMax-M2.7 respondió tres secciones correctas y, a mitad de
# frase, emitió 窗外 doscientas veintiuna veces seguidas. La degeneración es del
# MODELO; lo que arregla este guard es que Aithera la retransmitiera entera.
#
# El listón es alto A PROPÓSITO: cortar una respuesta legítima es peor que
# dejar pasar algo de ruido. Por eso la mitad de estos tests son NEGATIVOS.
from __future__ import annotations

import pytest

from app.mel.repetition import RepetitionGuard, find_repetition

VENTANA = "窗外"   # 窗外 — el token real del incidente


# ---------------------------------------------------------------------------
# Detecta lo que tiene que detectar
# ---------------------------------------------------------------------------
def test_detecta_el_caso_real_del_usuario():
    texto = (
        "## 3. LO QUE NUNCA HAGO\n\n"
        "- No ejecuto comandos sueltos en terminal sin un script guardado\n"
        "- No abro aplicaciones ni" + VENTANA * 221
    )
    assert find_repetition(texto) == VENTANA


def test_detecta_una_palabra_repetida():
    assert find_repetition("bla bla " + "hola" * 40) == "hola"


def test_detecta_un_solo_caracter_repetido_muchas_veces():
    assert find_repetition("respuesta normal " + "x" * 80) == "x"


# ---------------------------------------------------------------------------
# NO corta texto legítimo (lo que más importa)
# ---------------------------------------------------------------------------
def test_no_corta_una_respuesta_normal():
    texto = (
        "El Motor de Herramientas decide qué capacidad usar en cada momento. "
        "Analizo tu petición, identifico qué necesitas, busco en memoria si ya "
        "tengo contexto y selecciono la herramienta más eficiente."
    )
    assert find_repetition(texto) is None


def test_no_corta_un_separador_markdown():
    assert find_repetition("Sección uno\n\n---\n\nSección dos") is None
    assert find_repetition("Título\n" + "=" * 20) is None


def test_no_corta_puntos_suspensivos_ni_espacios():
    assert find_repetition("estoy pensando....................") is None
    assert find_repetition("texto" + " " * 100) is None
    assert find_repetition("linea" + "\n" * 50) is None


def test_no_corta_una_lista_con_guiones():
    lista = "\n".join(f"- elemento {i}" for i in range(30))
    assert find_repetition(lista) is None


def test_no_corta_una_tabla_ascii():
    assert find_repetition("| a | b |\n" + "|---|---|\n" * 3) is None


# ---------------------------------------------------------------------------
# El guard en streaming
# ---------------------------------------------------------------------------
def test_el_guard_avisa_en_cuanto_se_atasca():
    guard = RepetitionGuard()
    assert guard.feed("Respuesta que empieza bien. ") is False
    disparado = False
    for _ in range(100):
        if guard.feed(VENTANA):
            disparado = True
            break
    assert disparado, "no cortó pese a repetirse 100 veces"
    assert guard.pattern == VENTANA


def test_el_guard_no_se_dispara_en_una_respuesta_larga_normal():
    guard = RepetitionGuard()
    parrafos = [
        "Puedo ayudarte con el correo y el calendario. ",
        "También navego por internet y leo tus archivos. ",
        "Cada herramienta tiene un momento en el que tiene sentido usarla. ",
        "Si necesitas algo del sistema, lo consulto de verdad en vez de suponerlo. ",
    ] * 12
    for p in parrafos:
        assert guard.feed(p) is False, f"cortó texto legítimo en: {p!r}"


def test_la_nota_explica_el_corte_sin_jerga():
    guard = RepetitionGuard()
    nota = guard.note.lower()
    assert "repit" in nota          # dice QUÉ pasó
    assert "cortado" in nota        # dice que la respuesta está incompleta
    assert "vuelve a pregunt" in nota   # dice qué puede hacer el usuario
    for tecnico in ("minimax", "token", "traceback", "app.", ".py"):
        assert tecnico not in nota


# ---------------------------------------------------------------------------
# Integrado en el ÚNICO punto de salida de streaming (protege a toda la app)
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_mel_stream_corta_un_modelo_atascado(monkeypatch):
    """Se simula un proveedor que degenera y se comprueba que `mel.stream` deja
    de emitir en vez de retransmitir cientos de repeticiones."""
    from app.mel import executor, registry
    from app.mel.contracts import Capability, ExecutionRequest, ModelRef

    ref = ModelRef(provider="fake", model="degenerado", is_local=False)

    async def _stream_degenerado(r, prompt, system_prompt=None):
        yield "Empiezo a responder bien. "
        for _ in range(500):
            yield VENTANA

    monkeypatch.setattr(registry, "list_available", lambda: [ref])
    monkeypatch.setattr(registry, "stream", _stream_degenerado)
    monkeypatch.setattr(executor.policy_store, "ensure_compiled", lambda a: None)
    monkeypatch.setattr(executor, "_chain_for", lambda req, av: [ref])

    trozos = []
    async for chunk in executor.stream(ExecutionRequest(capability=Capability.CHAT, prompt="x")):
        trozos.append(chunk)

    salida = "".join(trozos)
    repeticiones = salida.count(VENTANA)
    assert repeticiones < 500, "retransmitió la degeneración entera"
    assert "repit" in salida.lower(), "no avisó al usuario de por qué se cortó"
    assert "Empiezo a responder bien" in salida, "se perdió la parte buena"
