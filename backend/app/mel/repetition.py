# app/mel/repetition.py — corta al modelo cuando se atasca repitiendo
#
# EL CASO REAL (2026-07-19): el usuario preguntó cómo funcionaba el motor de
# herramientas. MiniMax-M2.7 respondió bien durante tres secciones y, a mitad de
# una frase ("No abro aplicaciones ni…"), entró en bucle y emitió el token 窗外
# DOSCIENTAS VEINTIUNA veces seguidas hasta agotar su límite de salida.
#
# DE QUIÉN ES EL FALLO, con honestidad: la degeneración es del MODELO, no de
# Aithera — ningún prompt provoca eso, y le puede pasar a cualquier LLM (es un
# modo de fallo conocido del muestreo autorregresivo). Lo que SÍ es de Aithera
# es haberlo retransmitido entero a la pantalla del usuario sin inmutarse. Un
# sistema que habla por ti tiene que notar cuándo se ha quedado atascado.
#
# DÓNDE VIVE: lo usa `mel.executor.stream()`, que desde E2 es el ÚNICO punto por
# el que sale texto de un modelo en streaming (chat, agentes, todo). Un guard
# aquí protege la aplicación entera; ponerlo en el chat solo habría dejado
# desprotegido al resto.
#
# EL LISTÓN, a propósito alto: cortar una respuesta legítima es peor que dejar
# pasar un poco de ruido. Por eso hacen falta MUCHAS repeticiones seguidas Y una
# longitud total considerable — un separador markdown ("-----"), unos puntos
# suspensivos o una tabla ASCII no lo disparan.
from __future__ import annotations

from typing import Optional

# Cuánta cola se examina. Suficiente para ver el patrón; acotada para que el
# coste sea constante por chunk, no proporcional a la respuesta entera.
_TAIL = 400

# Un patrón de hasta 24 caracteres repetido sin descanso. Más largo que eso ya
# no es "atascarse": es un texto que se repite, y eso lo juzga el usuario.
_MAX_UNIT = 24

# Umbrales. Un carácter suelto necesita muchas más repeticiones que una
# secuencia: "………………" o una línea de guiones son legítimos; 窗外×221 no.
_MIN_REPS_MULTI = 10      # patrón de 2+ caracteres
_MIN_REPS_SINGLE = 40     # un solo carácter repetido
_MIN_SPAN = 48            # caracteres totales que ocupa la repetición


def find_repetition(text: str) -> Optional[str]:
    """Si el final de `text` es un patrón corto repitiéndose sin parar, devuelve
    ese patrón. None si el texto va bien.

    Mira solo el FINAL: lo que importa es si el modelo está atascado AHORA, no
    si repitió algo hace tres párrafos."""
    if not text:
        return None
    tail = text[-_TAIL:]

    for unit_len in range(1, _MAX_UNIT + 1):
        if len(tail) < unit_len * _MIN_REPS_MULTI:
            continue
        unit = tail[-unit_len:]
        if not unit.strip():
            continue          # espacios/saltos repetidos no son degeneración

        # ¿Cuántas veces seguidas aparece justo antes del final?
        reps = 0
        pos = len(tail)
        while pos - unit_len >= 0 and tail[pos - unit_len:pos] == unit:
            reps += 1
            pos -= unit_len

        minimo = _MIN_REPS_SINGLE if unit_len == 1 else _MIN_REPS_MULTI
        if reps >= minimo and reps * unit_len >= _MIN_SPAN:
            return unit
    return None


class RepetitionGuard:
    """Vigila un stream y avisa cuando el modelo se ha atascado.

    Uso: `guard.feed(chunk)` por cada trozo; devuelve True si hay que cortar.
    Acumula solo la cola necesaria — una respuesta larga no le cuesta memoria."""

    def __init__(self) -> None:
        self._tail = ""
        self.pattern: Optional[str] = None

    def feed(self, chunk: str) -> bool:
        if not chunk:
            return False
        self._tail = (self._tail + chunk)[-_TAIL:]
        self.pattern = find_repetition(self._tail)
        return self.pattern is not None

    @property
    def note(self) -> str:
        """Qué se le dice al usuario. Honesto: se explica que la respuesta se
        cortó y por qué, en vez de dejar un texto truncado sin explicación —
        y sin echarle la culpa a nadie con jerga técnica."""
        return (
            "\n\n[He cortado aquí: el modelo se quedó repitiéndose. "
            "Vuelve a preguntármelo y lo intento de nuevo.]"
        )
