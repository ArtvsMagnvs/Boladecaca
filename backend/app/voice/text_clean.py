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
