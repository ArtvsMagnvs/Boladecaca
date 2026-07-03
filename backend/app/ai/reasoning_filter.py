# app/ai/reasoning_filter.py
#
# B21 (PLAN_MAESTRO_2026, 2026-07-02): los modelos de razonamiento (MiniMax
# M2.7, DeepSeek R-series...) emiten su cadena de pensamiento en bloques
# <think>...</think> ANTES de la respuesta real. Este modulo la separa:
#
#   - strip_reasoning(text): para respuestas completas (no streaming).
#     Es la implementacion canonica (email_tool delega aqui).
#   - StreamingReasoningFilter: para SSE chunk a chunk. Stateful, porque
#     el tag puede llegar partido entre chunks ("<thi" + "nk>...").
#
# Politica actual: el razonamiento SE OCULTA en el chat y en los emails.
# Si en el futuro la UI quiere mostrarlo colapsado, el filtro ya lo separa
# (ver .reasoning_text) — solo habria que emitirlo como evento SSE aparte.

import re

_OPEN_RE = re.compile(r"^\s*<(think|thinking|reasoning)>", re.I)
_TAGS = ("think", "thinking", "reasoning")


def strip_reasoning(text: str) -> str:
    """Quita bloques de razonamiento de una respuesta completa."""
    if not text:
        return text
    out = re.sub(r"<(think|thinking|reasoning)>.*?</\1>", "", text, flags=re.S | re.I)
    # bloque abierto sin cerrar: no hay respuesta utilizable
    out = re.sub(r"<(think|thinking|reasoning)>(?!.*</\1>).*", "", out, flags=re.S | re.I)
    # cierre huerfano al principio (algunos providers omiten la apertura)
    m = re.search(r"</(think|thinking|reasoning)>", out, flags=re.I)
    if m:
        out = out[m.end():]
    return out.strip()


class StreamingReasoningFilter:
    """Filtro incremental para streams SSE.

    Estados:
      - 'sniffing': aun no sabemos si la respuesta empieza con un bloque de
        razonamiento. Retenemos hasta poder decidir (los primeros bytes).
      - 'reasoning': dentro del bloque; se acumula en reasoning_text y no
        se emite nada hasta ver el tag de cierre.
      - 'passthrough': respuesta normal; todo se emite tal cual.

    Uso:
        f = StreamingReasoningFilter()
        for chunk in stream: emit(f.feed(chunk))
        emit(f.flush())
    """

    # cuantos caracteres retener como maximo mientras decidimos si empieza
    # con un tag de razonamiento ("<thinking>" son 10 chars + espacios)
    _SNIFF_MAX = 24

    def __init__(self) -> None:
        self._state = "sniffing"
        self._buf = ""
        self._close_tag = ""
        self.reasoning_text = ""

    def feed(self, chunk: str) -> str:
        if not chunk:
            return ""
        if self._state == "passthrough":
            return chunk

        self._buf += chunk

        if self._state == "sniffing":
            stripped = self._buf.lstrip()
            m = _OPEN_RE.match(self._buf)
            if m:
                self._state = "reasoning"
                self._close_tag = f"</{m.group(1).lower()}>"
                # seguimos en este feed() para procesar lo ya acumulado
            elif stripped and not any(
                f"<{t}>".startswith(stripped[: len(t) + 2].lower()) for t in _TAGS
            ):
                # ya es seguro que NO empieza con tag de razonamiento
                out, self._buf = self._buf, ""
                self._state = "passthrough"
                return out
            elif len(self._buf) > self._SNIFF_MAX:
                out, self._buf = self._buf, ""
                self._state = "passthrough"
                return out
            else:
                return ""  # aun decidiendo

        # estado 'reasoning': buscar el cierre (case-insensitive)
        idx = self._buf.lower().find(self._close_tag)
        if idx == -1:
            # todo sigue siendo razonamiento; retener (dejamos una cola en el
            # buffer por si el tag de cierre llega partido entre chunks)
            keep = len(self._close_tag) - 1
            if len(self._buf) > keep:
                self.reasoning_text += self._buf[:-keep] if keep else self._buf
                self._buf = self._buf[-keep:] if keep else ""
            return ""
        # cierre encontrado: emitir lo que venga despues
        self.reasoning_text += self._buf[:idx]
        rest = self._buf[idx + len(self._close_tag):]
        self._buf = ""
        self._state = "passthrough"
        return rest.lstrip("\n").lstrip()

    def flush(self) -> str:
        """Al terminar el stream: si seguiamos decidiendo, el retenido era
        respuesta normal. Si seguiamos en razonamiento, no hay respuesta."""
        if self._state == "sniffing":
            out, self._buf = self._buf, ""
            return out
        if self._state == "reasoning":
            self.reasoning_text += self._buf
            self._buf = ""
            return ""
        return ""
