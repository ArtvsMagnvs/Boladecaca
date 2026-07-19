# app/orchestrator/decomposer.py — de un mensaje a N objetivos (R2)
#
# CUÁNDO SE LLAMA: SOLO cuando el clasificador del TIE ya detectó que el mensaje
# trae varios encargos (`Intent.objectives` con >= 2). El ~80% de los mensajes
# tiene un solo objetivo y NUNCA pasa por aquí: esa es la regla de no-regresión
# de doc 23 §0 — el camino corto no paga ni una llamada extra.
#
# QUÉ APORTA sobre lo que ya trae el Intent: el clasificador enumera los encargos
# (barato, un solo modelo pequeño), pero no analiza las DEPENDENCIAS entre ellos
# ("cuando termines todo, avísame por WhatsApp") ni si alguno sigue siendo
# demasiado amplio para una sola misión ("crea 15 canales de YouTube"). Eso pide
# razonamiento, y es lo único que se hace aquí — una llamada, y solo en el caso
# multi.
from __future__ import annotations

import json
import re
from typing import Optional

from app.core.logging_config import get_system_logger
from app.orchestrator.contracts import Objective

logger = get_system_logger("orchestrator.decomposer")

_SYSTEM_PROMPT = """Eres el orquestador de Aithera. Recibes un mensaje del usuario que
contiene VARIOS encargos, y devuelves SOLO un objeto JSON (sin texto extra, sin markdown)
que los organiza para ejecutarlos.

Formato:
{
  "objectives": [
    {
      "id": "o1",
      "goal": "encargo concreto, en imperativo y verificable",
      "depends_on": [],
      "needs_decomposition": false,
      "priority": 0
    }
  ]
}

Reglas:
- "id": único y correlativo (o1, o2, o3...).
- "goal": UN encargo por objetivo. No los mezcles ni los partas en pasos: los pasos
  internos los planifica después cada misión por su cuenta.
- "depends_on": ids de los objetivos que deben TERMINAR antes que éste. Úsalo SOLO
  cuando de verdad haya dependencia (p.ej. "cuando acabes todo, avísame" depende de
  los demás; "resume el informe que acabas de escribir" depende de escribirlo).
  Si dos encargos pueden hacerse a la vez, deja la lista vacía: se ejecutarán en
  paralelo y el usuario tendrá antes su resultado.
- "needs_decomposition": true SOLO si el objetivo es tan amplio que necesita a su vez
  varios trabajos independientes (p.ej. "crea 15 canales de YouTube con su estrategia
  y contenido"). Para un encargo normal de varios pasos, false.
- "priority": 0 normal; usa un número mayor para lo que el usuario marque como urgente.
- No inventes encargos que el usuario no ha pedido. No omitas ninguno de los que sí.

Devuelve SOLO el JSON."""


def _extract_json(text: str) -> Optional[dict]:
    """Extrae el primer objeto JSON de una respuesta del LLM, tolerante a
    ```json ... ``` y a texto alrededor.

    El TIE tiene su propia copia de esto (`tie.intents`), y no se importa a
    propósito: es un interno suyo y cruzar esa frontera acopla los dos módulos
    por una utilidad de parseo que no es de nadie en particular. Son 15 líneas
    puras — duplicarlas cuesta menos que el acoplamiento. Si un tercer módulo
    llega a necesitarlas, entonces sí: a `app/core/`."""
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else None
    if candidate is None:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None


def _fallback(objectives: list[str], depth: int = 0) -> list[Objective]:
    """Degradación: los objetivos que YA trae el Intent, sin dependencias.

    Se usa cuando el razonamiento falla o devuelve basura. Es honesto: se pierde
    el análisis de dependencias (todo va en paralelo) pero NO se pierde ningún
    encargo del usuario, que es lo que importa."""
    return [
        Objective(id=f"o{i}", goal=goal, depth=depth)
        for i, goal in enumerate(objectives, start=1)
    ]


async def decompose(
    message: str,
    *,
    objectives_hint: list[str],
    depth: int = 0,
) -> list[Objective]:
    """Convierte un mensaje multi-encargo en objetivos con sus dependencias.

    `objectives_hint` son los que ya detectó el clasificador: se le pasan al
    modelo como punto de partida y se usan como red de seguridad si falla.

    NUNCA lanza: ante cualquier problema devuelve el fallback. Que el usuario
    pierda el orden óptimo es tolerable; que pierda un encargo, no."""
    from app.mel import Capability, ExecutionRequest, complete as mel_complete

    prompt = (
        f"MENSAJE DEL USUARIO:\n{message}\n\n"
        f"ENCARGOS YA DETECTADOS (organízalos, no los cambies):\n"
        + "\n".join(f"- {o}" for o in objectives_hint)
    )

    try:
        res = await mel_complete(ExecutionRequest(
            capability=Capability.REASON,
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
        ))
        if not res.ok:
            logger.info(f"[decomposer] el modelo falló, uso los objetivos del intent: {res.error}")
            return _fallback(objectives_hint, depth)

        data = _extract_json(res.text)
        parsed = _parse(data, depth) if data else []
        if not parsed:
            logger.info("[decomposer] respuesta sin objetivos utilizables, uso el fallback")
            return _fallback(objectives_hint, depth)
        return parsed
    except Exception as e:      # el orquestador nunca cae por el decomposer
        logger.error(f"[decomposer] excepción, uso el fallback: {type(e).__name__}: {e}")
        return _fallback(objectives_hint, depth)


def _parse(data: dict, depth: int) -> list[Objective]:
    """Valida la salida del modelo. Descarta dependencias inventadas (a ids que
    no existen) en vez de rechazar el plan entero: un `depends_on` roto dejaría
    ese objetivo esperando para siempre a algo que nunca llega."""
    raw = data.get("objectives")
    if not isinstance(raw, list):
        return []

    objetivos: list[Objective] = []
    for i, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        goal = str(item.get("goal") or "").strip()
        if not goal:
            continue
        objetivos.append(Objective(
            id=str(item.get("id") or f"o{i}").strip(),
            goal=goal,
            depends_on=[str(d).strip() for d in (item.get("depends_on") or []) if str(d).strip()],
            needs_decomposition=bool(item.get("needs_decomposition")),
            priority=int(item.get("priority") or 0) if str(item.get("priority", "")).lstrip("-").isdigit() else 0,
            depth=depth,
        ))

    ids = {o.id for o in objetivos}
    for o in objetivos:
        limpias = [d for d in o.depends_on if d in ids and d != o.id]
        if len(limpias) != len(o.depends_on):
            logger.info(f"[decomposer] dependencias descartadas en {o.id}: no existen o son cíclicas")
        o.depends_on = limpias

    return _romper_ciclos(objetivos)


def _romper_ciclos(objetivos: list[Objective]) -> list[Objective]:
    """Un ciclo de dependencias dejaría los objetivos implicados en `pending`
    para siempre (nunca estarían listos). Se detecta con el mismo recorrido
    topológico que usa `graph.py` para los nodos del TIE, y se rompe soltando las
    dependencias de los objetivos atrapados — mejor ejecutarlos en paralelo que
    no ejecutarlos nunca."""
    pendientes = {o.id: set(o.depends_on) for o in objetivos}
    resueltos: set[str] = set()

    while True:
        listos = {oid for oid, deps in pendientes.items() if deps <= resueltos}
        if not listos:
            break
        resueltos |= listos
        for oid in listos:
            pendientes.pop(oid, None)

    if pendientes:
        logger.info(f"[decomposer] ciclo detectado en {sorted(pendientes)}: se sueltan sus dependencias")
        atrapados = set(pendientes)
        for o in objetivos:
            if o.id in atrapados:
                o.depends_on = []
    return objetivos
