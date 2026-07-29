# app/core/sanitize.py — limpieza de texto que viene de FUERA (S9c, doc 34)
#
# EL FALLO QUE CIERRA (verificación en vivo, 2026-07-28): una búsqueda de vídeos
# devolvió resultados REALES y correctos, pero los enlaces salieron rotos:
#
#   [https://www.youtube.com/watch?v=iy35dCK0iaI](https://…iy35dCK0iaI￼Ritmos)
#                                                              ^^^^^^^^
# Ese `￼` (OBJECT REPLACEMENT CHARACTER) es INVISIBLE: no se ve en el JSON,
# no se ve en el log, y el modelo no tiene forma de saber que no forma parte de
# la URL. Lo pega al final del enlace, el markdown se corrompe y el usuario
# acaba con un enlace que no lleva a ninguna parte. Viene de la API de búsqueda
# (los `description` de los proveedores traen restos de marcado enriquecido).
#
# POR QUÉ AQUÍ Y NO EN UN SITIO SUELTO: el problema no es de la búsqueda, es de
# CUALQUIER texto que entra desde fuera — una página web (`browser.get_text`),
# un documento, un email. Basura invisible en el prompt es basura invisible en
# la respuesta. Una función pura, sin dependencias, en la capa compartida
# (mismo sitio que `strings.py`, `events.py`, `grounding.py`).
#
# QUÉ NO HACE, a propósito: no toca acentos, ni emojis, ni CJK, ni saltos de
# línea, ni tabuladores. Solo quita lo que NO se ve y no debería estar.
from __future__ import annotations

import unicodedata

# Invisibles concretos que aparecen en contenido web real y estropean el texto.
# La categoría Unicode `Cf` (format) cubre la mayoría, pero `￼` es `So`
# (symbol, other) — hay que nombrarlo aparte, y es justo el que rompió la URL.
_INVISIBLES = {
    "￼",   # OBJECT REPLACEMENT CHARACTER — el del fallo real
    "�",   # REPLACEMENT CHARACTER (decodificación fallida aguas arriba)
    "­",   # SOFT HYPHEN
    "​", "‌", "‍",   # zero-width space / non-joiner / joiner
    "⁠",   # WORD JOINER
    "﻿",   # BOM / zero-width no-break space
}

# Controles C0/C1 que no aportan nada en texto plano. Se conservan los tres
# que SÍ significan algo: salto de línea, retorno y tabulador.
_KEEP_CONTROL = {"\n", "\r", "\t"}


def strip_invisible(text: str) -> str:
    """Quita caracteres invisibles y de control de un texto externo.

    Función PURA. Si `text` no es una cadena, se devuelve tal cual (para poder
    aplicarla sin comprobar el tipo en cada llamada)."""
    if not isinstance(text, str) or not text:
        return text
    out = []
    for ch in text:
        if ch in _KEEP_CONTROL:
            out.append(ch)
            continue
        if ch in _INVISIBLES:
            continue
        cat = unicodedata.category(ch)
        if cat in ("Cc", "Cf"):     # control, format
            continue
        out.append(ch)
    return "".join(out)


def clean_url(url: str) -> str:
    """Una URL se CORTA en el primer carácter invisible o en blanco.

    Cortar, no limpiar: es la diferencia entre `…iaI` (correcto) y
    `…iaIRitmos` (una URL que no existe). En texto normal un invisible es
    ruido que se quita; dentro de una URL es la FRONTERA — marca dónde
    terminaba el enlace y empezaba otra cosa pegada a él. Ese matiz es
    justo el fallo real del 28-jul, y confundirlo produce un enlace roto
    igualmente, solo que más difícil de ver."""
    if not isinstance(url, str):
        return url
    url = url.strip()          # los blancos de los EXTREMOS solo sobran
    corte = len(url)
    for i, ch in enumerate(url):
        if ch.isspace() or ch in _INVISIBLES or unicodedata.category(ch) in ("Cc", "Cf"):
            corte = i
            break
    return url[:corte].strip()


def clean_external(value):
    """Limpia recursivamente cadenas dentro de dicts/listas, dejando el resto
    de tipos intacto. Pensada para el resultado ya normalizado de una tool:
    una llamada y todo el árbol queda limpio, sin recorrerlo a mano en cada
    sitio (y sin que se olvide un campo nuevo el día que se añada)."""
    if isinstance(value, str):
        return strip_invisible(value)
    if isinstance(value, dict):
        return {k: (clean_url(v) if k == "url" and isinstance(v, str) else clean_external(v))
                for k, v in value.items()}
    if isinstance(value, list):
        return [clean_external(v) for v in value]
    return value
