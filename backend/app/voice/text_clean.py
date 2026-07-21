"""
Aithera — limpieza de texto para sintesis de voz (TTS).

WHY: algunos proveedores de TTS (sobre todo modelos "inteligentes" como
ElevenLabs) no se limitan a ignorar los emoticonos: a veces los DESCRIBEN en
voz alta (p.ej. dicen "carita sonriente" al llegar a un "😊"). El usuario
quiere que el emoticono se quede solo en el texto del chat (donde se ve) y
que la voz actue como si no estuviera — ni lo lee, ni lo describe, ni lo
menciona.

Se aplica SOLO al texto que se manda a sintetizar (voice.py), nunca al texto
que se guarda en el historial ni al que se muestra en el chat: el emoticono
sigue estando en la burbuja de texto, solo desaparece de lo que se convierte
a audio.
"""
from __future__ import annotations

import re

# Rango amplio de bloques Unicode usados por emoticonos/pictogramas/dingbats,
# banderas (regional indicators), variation selector (presentacion emoji) y
# el zero-width-joiner (usado para componer emojis compuestos, ej. familias).
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"  # banderas (regional indicator symbols)
    "\U0001F300-\U0001F5FF"  # simbolos y pictogramas
    "\U0001F600-\U0001F64F"  # emoticonos (caras)
    "\U0001F680-\U0001F6FF"  # transporte y mapas
    "\U0001F700-\U0001F77F"  # alquimicos
    "\U0001F780-\U0001F7FF"  # formas geometricas extendidas
    "\U0001F800-\U0001F8FF"  # flechas suplementarias-C
    "\U0001F900-\U0001F9FF"  # simbolos y pictogramas suplementarios
    "\U0001FA00-\U0001FA6F"  # simbolos de ajedrez
    "\U0001FA70-\U0001FAFF"  # simbolos y pictogramas extendidos-A
    "\U0001F000-\U0001F0FF"  # mahjong / domino / cartas
    "\U00002600-\U000026FF"  # simbolos varios (☀☁★☂ etc.)
    "\U00002700-\U000027BF"  # dingbats (✅❌✂️ etc.)
    "\U00002B00-\U00002BFF"  # simbolos y flechas varias (⭐➡️ etc.)
    "\U00002300-\U000023FF"  # tecnico varios (⌚⏰⏳ etc.)
    "\U000025A0-\U000025FF"  # formas geometricas (▪️◻️ etc.)
    "\U00002190-\U000021FF"  # flechas (↔️↩️ etc., usadas como emoji)
    "\U0000FE0F"              # variation selector-16 (presentacion emoji)
    "\U0000200D"              # zero width joiner (emojis compuestos)
    "\U000020E3"              # combining enclosing keycap (1️⃣ 2️⃣ ...)
    "\U00003030\U0000303D\U00003297\U00003299"  # dingbats de estilo japones
    "]+",
    flags=re.UNICODE,
)

# Espacios/saltos de linea que quedan huerfanos al quitar un emoticono
# rodeado de espacios (ej. "genial 😊 gracias" -> "genial  gracias").
_EXTRA_SPACES = re.compile(r"[ \t]{2,}")
_EXTRA_BLANK_LINES = re.compile(r"\n{3,}")


def strip_emojis(text: str) -> str:
    """Quita emoticonos/pictogramas de `text` para que el TTS no los lea ni
    los describa. No toca el resto del texto (puntuacion, acentos, etc.)."""
    if not text:
        return text
    cleaned = _EMOJI_PATTERN.sub("", text)
    cleaned = _EXTRA_SPACES.sub(" ", cleaned)
    cleaned = _EXTRA_BLANK_LINES.sub("\n\n", cleaned)
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Markdown -> habla natural (Opt v0.9.5, V1)
# ---------------------------------------------------------------------------
# EL BUG QUE CIERRA (reportado por el usuario): la voz decia "asterisco
# asterisco" al leer **negrita**, y leia guiones de lista, almohadillas de
# titulo y barras de tabla. Una conversacion natural no pronuncia el formato:
# el markdown es para el OJO, no para el OIDO.
#
# Se aplica SOLO al texto que va al TTS (igual que strip_emojis): el chat sigue
# mostrando el markdown renderizado por miniMarkdown.

# Bloques de codigo: no se leen (leer codigo en voz alta no aporta nada).
_CODE_FENCE = re.compile(r"```[\s\S]*?```")
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
# Enlaces/imagenes markdown: se dice el TEXTO, nunca la URL.
_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
# URLs sueltas: leerlas caracter a caracter es ruido.
_BARE_URL = re.compile(r"https?://\S+")
# Enfasis: **negrita**, __negrita__, *cursiva*, _cursiva_, ~~tachado~~
_BOLD_ITALIC = re.compile(r"(\*{1,3}|_{1,3}|~~)(.+?)\1", flags=re.DOTALL)
# Titulos markdown al principio de linea.
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", flags=re.MULTILINE)
# Citas.
_BLOCKQUOTE = re.compile(r"^\s{0,3}>\s?", flags=re.MULTILINE)
# Vinetas de lista: "- ", "* ", "+ " al principio de linea.
_BULLET = re.compile(r"^\s{0,6}[-*+]\s+", flags=re.MULTILINE)
# Listas numeradas: se conserva el numero (aporta orden al escuchar).
_ORDERED = re.compile(r"^\s{0,6}(\d+)[.)]\s+", flags=re.MULTILINE)
# Separadores horizontales.
_HR = re.compile(r"^\s*([-*_]\s?){3,}\s*$", flags=re.MULTILINE)
# Tablas: las barras se convierten en pausas; la fila de guiones se elimina.
_TABLE_SEP = re.compile(r"^\s*\|?[\s:-]*\|[\s:|-]*$", flags=re.MULTILINE)
_TABLE_PIPES = re.compile(r"\s*\|\s*")
# Restos de asteriscos/guiones bajos sueltos que no formaban par.
_LONE_MARKS = re.compile(r"[*_`~]{1,}")


def clean_for_speech(text: str) -> str:
    """Deja el texto listo para que una voz lo lea NATURALMENTE.

    Quita el formato (markdown, emojis, URLs) y convierte la estructura visual
    en pausas habladas. Nunca pronuncia signos de formato: "**hola**" se lee
    "hola", no "asterisco asterisco hola".
    """
    if not text:
        return text

    t = text
    # 1) Codigo fuera (leerlo en voz alta no aporta); el inline se lee tal cual.
    t = _CODE_FENCE.sub(" ", t)
    t = _INLINE_CODE.sub(r"\1", t)
    # 2) Enlaces e imagenes: solo el texto legible.
    t = _MD_IMAGE.sub(r"\1", t)
    t = _MD_LINK.sub(r"\1", t)
    t = _BARE_URL.sub(" ", t)
    # 3) Tablas -> filas con pausas (antes que las vinetas, por los guiones).
    t = _TABLE_SEP.sub("", t)
    t = _TABLE_PIPES.sub(", ", t)
    # 4) Estructura de bloque.
    t = _HR.sub("", t)
    t = _HEADING.sub("", t)
    t = _BLOCKQUOTE.sub("", t)
    t = _ORDERED.sub(r"\1. ", t)
    t = _BULLET.sub("", t)
    # 5) Enfasis: se conserva el contenido, se tira el marcador.
    for _ in range(3):          # anidados: ***texto*** -> **texto** -> texto
        t = _BOLD_ITALIC.sub(r"\2", t)
    t = _LONE_MARKS.sub("", t)
    # 6) Emojis (el TTS los describe en voz alta si se dejan).
    t = strip_emojis(t)
    # 7) Normalizacion final: comas huerfanas de tabla y espacios.
    t = re.sub(r"(,\s*){2,}", ", ", t)
    t = re.sub(r"^\s*,\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"\s*,\s*$", "", t, flags=re.MULTILINE)   # coma final de fila de tabla
    t = _EXTRA_SPACES.sub(" ", t)
    t = _EXTRA_BLANK_LINES.sub("\n\n", t)
    return t.strip()
