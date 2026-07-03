# tests/test_reasoning_filter.py
#
# B21 (PLAN_MAESTRO_2026): el filtro que separa la cadena de pensamiento
# (<think>...</think>) de la respuesta real de los modelos razonadores.
# Cubre la version completa (strip_reasoning) y la incremental para SSE
# (StreamingReasoningFilter), incluido el caso duro: tag partido entre chunks.

import pytest

from app.ai.reasoning_filter import strip_reasoning, StreamingReasoningFilter


# ----------------------------------------------------------------------
# strip_reasoning — respuesta completa (no streaming)
# ----------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    # bloque simple
    ("<think>razonando...</think>Hola", "Hola"),
    # con espacios y salto tras el cierre
    ("<think>x</think>\n\nRespuesta final", "Respuesta final"),
    # variantes de tag
    ("<thinking>y</thinking>Texto", "Texto"),
    ("<reasoning>z</reasoning>Texto", "Texto"),
    # mayusculas/minusculas
    ("<THINK>Y</THINK>Hola", "Hola"),
    # varios bloques
    ("<think>a</think>Uno <think>b</think>Dos", "Uno Dos"),
    # sin razonamiento: passthrough intacto
    ("Respuesta normal sin tags", "Respuesta normal sin tags"),
    # cierre huerfano al principio (provider omite apertura)
    ("pensando en voz alta</think>Respuesta", "Respuesta"),
])
def test_strip_reasoning(raw, expected):
    assert strip_reasoning(raw) == expected


def test_strip_reasoning_bloque_sin_cerrar_queda_vacio():
    # si empieza a pensar y nunca cierra, no hay respuesta utilizable
    assert strip_reasoning("<think>y nunca termino de pensar") == ""


def test_strip_reasoning_vacio_o_none():
    assert strip_reasoning("") == ""
    assert strip_reasoning(None) is None


# ----------------------------------------------------------------------
# StreamingReasoningFilter — SSE chunk a chunk
# ----------------------------------------------------------------------

def _run_stream(chunks):
    """Alimenta chunks al filtro y devuelve la salida visible concatenada."""
    f = StreamingReasoningFilter()
    out = "".join(f.feed(c) for c in chunks)
    out += f.flush()
    return out, f


def test_stream_bloque_completo_en_un_chunk():
    out, _ = _run_stream(["<think>razono</think>Hola mundo"])
    assert out == "Hola mundo"


def test_stream_sin_razonamiento_es_passthrough():
    out, _ = _run_stream(["Hola ", "que ", "tal"])
    assert out == "Hola que tal"


def test_stream_tag_partido_entre_chunks():
    # el <think> llega roto y el </think> tambien
    chunks = ["<thi", "nk>estoy ", "pensando", "</thi", "nk>", "Respuesta real"]
    out, f = _run_stream(chunks)
    assert out == "Respuesta real"
    assert "pensando" in f.reasoning_text  # el razonamiento se guardo aparte


def test_stream_cierre_partido_al_final():
    chunks = ["<think>x</th", "ink>", "Fin"]
    out, _ = _run_stream(chunks)
    assert out == "Fin"


def test_stream_razonamiento_sin_cierre_no_emite_nada():
    out, f = _run_stream(["<think>pienso ", "y pienso ", "sin parar"])
    assert out == ""
    assert "sin parar" in f.reasoning_text


def test_stream_razonamiento_va_a_reasoning_text():
    out, f = _run_stream(["<think>secreto</think>", "publico"])
    assert out == "publico"
    assert "secreto" in f.reasoning_text  # el razonamiento se retuvo aparte


def test_stream_respuesta_larga_sin_tag_no_se_retiene_para_siempre():
    # una respuesta que NO empieza con tag debe empezar a fluir enseguida
    texto = "Esta es una respuesta bastante larga que no lleva razonamiento."
    out, _ = _run_stream(list(texto))  # char a c