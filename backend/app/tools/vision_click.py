# backend/app/tools/vision_click.py
#
# B·WEB-2 (doc 32): localizar un elemento POR VISION cuando los selectores
# fallan. El cerebro compartido de las dos acciones `find_and_click` —
# `desktop_tool` (pantalla, coordenadas puras) y `browser_tool` (pagina, con
# set-of-mark sobre el DOM).
#
# Por que un modulo aparte y no dentro de cada tool: el prompt, el parseo de la
# respuesta del modelo y la conversion de coordenadas son EXACTAMENTE los
# mismos en los dos casos. Duplicarlos garantizaria que uno de los dos se
# quedase atras (patron LOG-1: ya ha pasado tres veces en este proyecto).
#
# Las funciones de parseo/escala son PURAS y sin dependencias: se pueden probar
# sin pantalla, sin navegador y sin modelo. La unica que habla con el mundo es
# `locate`, y solo con el MEL (jamas con un proveedor concreto).
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging_config import get_system_logger

logger = get_system_logger("tools.vision_click")

# Cuantos elementos numerados se le describen al modelo como maximo. Con mas, el
# prompt crece sin aportar: una pagina real tiene decenas de elementos
# interactivos y el que se busca casi siempre esta entre los primeros del flujo
# de lectura. Es un tope de coste, no una limitacion de capacidad.
MAX_MARKS = 60


@dataclass
class Located:
    """Donde dice el modelo que esta el elemento. Exactamente UNA de las dos vias
    viene rellena: `index` (eligio por set-of-mark, la precisa) o `x/y` (eligio
    por coordenadas, la de ultimo recurso)."""
    index: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None
    raw: str = ""

    @property
    def ok(self) -> bool:
        return self.index is not None or (self.x is not None and self.y is not None)


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------
_BASE_RULES = """Eres un localizador de elementos en una captura de pantalla. Tu ÚNICA
salida es un objeto JSON, sin texto alrededor y sin markdown.

Reglas que no puedes saltarte:
1. Si NO ves el elemento con seguridad, responde {"not_found": true} y una razón
   breve en "reason". NUNCA te inventes una posición: un clic en el sitio
   equivocado hace daño de verdad en el ordenador del usuario.
2. No expliques nada fuera del JSON."""


def build_prompt(description: str, *, width: int, height: int,
                 marks: Optional[List[Dict[str, Any]]] = None,
                 scale_note: str = "") -> str:
    """El prompt de localizacion. Dos modos, segun haya DOM o no.

    Las dimensiones van SIEMPRE dentro (paso 5 del plan): el modelo necesita
    saber en que sistema de coordenadas responder, y la escala/multi-monitor es
    la fragilidad conocida de esta tecnica — documentarla en el prompt es la
    mitad barata del arreglo (la otra mitad es `to_screen_coords`)."""
    cabecera = (
        f"{_BASE_RULES}\n\n"
        f"La imagen mide {width}x{height} píxeles."
        f"{(' ' + scale_note) if scale_note else ''}\n\n"
        f"ELEMENTO A LOCALIZAR: {description}\n"
    )
    if marks:
        listado = "\n".join(
            f'  [{m["index"]}] {m.get("role") or "elemento"}: '
            f'{(m.get("text") or "").strip()[:80]}'
            for m in marks[:MAX_MARKS]
        )
        return (
            cabecera
            + "\nLa captura lleva CAJAS NUMERADAS sobre los elementos con los que se "
              "puede interactuar. Esta es la lista:\n" + listado
            + '\n\nResponde con el número de la caja: {"index": <número>}\n'
              'Si el elemento que buscas NO tiene caja, responde con su centro en '
              'píxeles: {"x": <x>, "y": <y>}\n'
              'Prefiere SIEMPRE el número si existe: es exacto; las coordenadas son '
              'una aproximación.'
        )
    return (
        cabecera
        + '\nResponde con el centro del elemento en píxeles de ESTA imagen:\n'
          '{"x": <x>, "y": <y>}'
    )


# ---------------------------------------------------------------------------
# Parseo (puro)
# ---------------------------------------------------------------------------
def parse_location(text: str) -> Optional[Located]:
    """Interpreta la respuesta del modelo. None = no lo encontro (o no se
    entiende lo que dijo, que a efectos de seguridad es lo mismo: no se hace
    clic). Acepta el JSON envuelto en markdown y, como ultimo recurso, un
    "x,y" suelto — los modelos pequenos responden asi a menudo, y rechazar la
    respuesta por su formato seria perder una localizacion correcta."""
    if not text:
        return None
    crudo = text.strip()
    # Bloque markdown: ```json { ... } ```
    m = re.search(r"```(?:json)?\s*(.+?)```", crudo, re.DOTALL)
    if m:
        crudo = m.group(1).strip()
    # Objeto JSON (el primero equilibrado que aparezca)
    inicio = crudo.find("{")
    if inicio >= 0:
        profundidad, fin = 0, -1
        for i, ch in enumerate(crudo[inicio:], start=inicio):
            if ch == "{":
                profundidad += 1
            elif ch == "}":
                profundidad -= 1
                if profundidad == 0:
                    fin = i
                    break
        if fin > inicio:
            try:
                data = json.loads(crudo[inicio:fin + 1])
            except (ValueError, TypeError):
                data = None
            if isinstance(data, dict):
                if data.get("not_found"):
                    return None
                idx = _as_int(data.get("index"))
                if idx is not None and idx >= 0:
                    return Located(index=idx, raw=text)
                x, y = _as_int(data.get("x")), _as_int(data.get("y"))
                if x is not None and y is not None:
                    return Located(x=x, y=y, raw=text)
                return None
    # Ultimo recurso: "412, 268" suelto en la respuesta.
    par = re.search(r"(-?\d{1,5})\s*[,;]\s*(-?\d{1,5})", crudo)
    if par:
        return Located(x=int(par.group(1)), y=int(par.group(2)), raw=text)
    return None


def _as_int(v: Any) -> Optional[int]:
    if isinstance(v, bool):        # True es int en Python; aqui no es una coordenada
        return None
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        try:
            return int(float(v.strip()))
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Escala y multi-monitor (paso 5 del plan) — puro
# ---------------------------------------------------------------------------
def to_screen_coords(x: int, y: int, *, image_size: Tuple[int, int],
                     screen_size: Tuple[int, int]) -> Tuple[int, int]:
    """Traduce coordenadas de la IMAGEN a coordenadas de PANTALLA.

    Por que hace falta (la fragilidad que Mark-L documenta y no resuelve): con
    escalado de pantalla de Windows (125%, 150%…) la captura sale en píxeles
    FÍSICOS y el ratón se mueve en píxeles LÓGICOS. Un modelo que acierta de
    pleno en la imagen 2560x1440 haría clic 1,5 veces más abajo y a la derecha
    de lo que debe si nadie convierte. Con las dos medidas iguales, esta
    función es la identidad — que es el caso sin escalado.

    El resultado se acota SIEMPRE a la pantalla: ni un clic fuera de límites."""
    iw, ih = image_size
    sw, sh = screen_size
    if iw > 0 and ih > 0 and sw > 0 and sh > 0:
        x = round(x * sw / iw)
        y = round(y * sh / ih)
    return max(0, min(int(x), max(0, sw - 1))), max(0, min(int(y), max(0, sh - 1)))


# ---------------------------------------------------------------------------
# La única parte que habla con el mundo: el MEL
# ---------------------------------------------------------------------------
async def locate(description: str, image_b64: str, *, width: int, height: int,
                 marks: Optional[List[Dict[str, Any]]] = None,
                 scale_note: str = "") -> Tuple[Optional[Located], Optional[str]]:
    """Pregunta a un modelo con visión dónde está el elemento.

    Devuelve `(Located|None, error|None)`. FAIL-CLOSED en las tres formas de
    fallar: sin modelo de visión configurado, con el MEL devolviendo error, o
    con una respuesta que no se entiende → `(None, motivo)` y NADIE hace clic.
    Jamás se devuelve una coordenada que no venga de un modelo que vio la
    imagen de verdad (el MEL lo garantiza: un proveedor que no acepta imágenes
    hace fallar ese candidato en vez de responder a ciegas)."""
    import app.mel as mel

    if not mel.vision_available():
        return None, ("no hay ningún modelo con visión configurado. Conecta uno "
                      "multimodal (Gemini, Claude, GPT) o instala un modelo VL "
                      "local (p. ej. `ollama pull qwen2.5vl:7b`)")

    req = mel.ExecutionRequest(
        capability=mel.Capability.VISION,
        prompt=build_prompt(description, width=width, height=height,
                            marks=marks, scale_note=scale_note),
        images=(image_b64,),
    )
    resultado = await mel.complete(req)
    if not resultado.ok:
        return None, f"el modelo de visión no pudo mirar la captura: {resultado.error}"

    ubic = parse_location(resultado.text)
    if ubic is None or not ubic.ok:
        logger.info(f"[vision_click] sin localización utilizable para «{description}»: "
                    f"{(resultado.text or '')[:200]!r}")
        return None, (f"el modelo no ha localizado «{description}» en la pantalla "
                      f"(no se hace clic a ciegas)")
    return ubic, None
