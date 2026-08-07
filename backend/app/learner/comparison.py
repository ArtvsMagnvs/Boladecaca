# backend/app/learner/comparison.py — LA PRUEBA DE MEJORA EFECTIVA (V1.1 LC3)
#
# PETICIÓN DIRECTA DEL USUARIO al abrir LC3: una "mejora de skill" no se
# propone solo porque la consolidación (LC2) lo sugiera — antes de llegar al
# usuario, se COMPARA de verdad con la versión actual, y si no hay una mejora
# real y demostrable en el resultado, NO se propone. "Incumbente que gana =
# sin propuesta" (el mismo criterio que SE1, doc 27 §6, adelantado aquí a una
# forma segura y sin ejecución real de herramientas).
#
# CÓMO SE GENERALIZA A DOMINIOS DISTINTOS (frontend, backend, marketing…): una
# skill es, en ejecución, un bloque de instrucciones que se antepone al
# contexto del agente (`_persona_block`, PU2). Comparar "cómo abordaría la
# tarea un agente guiado por la versión A" contra "guiado por la versión B" es
# la forma de prueba que NO depende del dominio — se compara la RESPUESTA que
# cada versión produce ante la MISMA tarea real, no se ejecuta nada (sin
# herramientas, sin efectos secundarios: es texto contra texto). Es más
# modesto que un torneo con ejecución real (eso es SE1, V1.2), pero es
# genuino, seguro, y funciona igual para cualquier ámbito porque compara
# SALIDAS, no un arnés de tests por dominio que habría que inventar de cero
# para cada skill.
#
# LA FRONTERA DE HONESTIDAD (doc 41 §5): quien genera las dos respuestas
# candidatas NO es quien las juzga — son llamadas distintas, y el juez EXCLUYE
# (cuando puede) a los modelos que generaron los candidatos, mismo principio
# anti-sesgo que el juez de misiones (judge.py). Encuadre ESCÉPTICO: sin
# mejora clara y consistente, el veredicto es "no hay mejora" — la carga de
# la prueba la lleva la propuesta nueva, no la que ya existe.
from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Cuántas tareas de ejemplo se usan para comparar. Cada una cuesta 2 llamadas
# (candidato actual + candidato propuesto) más 1 llamada de juicio al final —
# con 2 tareas son 5 llamadas por decisión `improve_skill`, aceptable porque
# mejorar una skill existente es un caso raro frente a proponer una nueva.
MAX_SAMPLE_TASKS = 2
_MAX_TASK_CHARS = 400
_MAX_CANDIDATE_CHARS = 1200

_SYSTEM_CANDIDATE = """Eres un agente de Aithera guiado por estas
instrucciones de comportamiento (una "skill"):

{skill_text}

Se te da una tarea real. Responde EXACTAMENTE como abordarías esa tarea
siguiendo esas instrucciones: qué harías y en qué orden, o la respuesta
directa si la tarea es informativa. Sé concreto, no genérico. No uses
herramientas ni digas que las vas a usar: describe tu enfoque en texto."""

# Encuadre ESCÉPTICO (doc 41 §3.3, mismo principio que el juez de misiones):
# el listón para declarar mejora es alto a propósito.
_SYSTEM_COMPARE = """Eres el sistema de aprendizaje de Aithera. Vas a comparar
DOS versiones de las instrucciones de una misma habilidad para decidir si la
versión NUEVA es de verdad una mejora sobre la versión ACTUAL.

Te doy, para cada una de varias tareas reales, la respuesta que un agente
daría guiado por la versión ACTUAL ("before") y la que daría guiado por la
versión NUEVA ("after"). Compara cada par contra lo que la tarea pedía.

SÉ EXIGENTE. El listón es alto: declara mejora SOLO si la versión nueva
produce respuestas más útiles, más completas o más correctas de forma clara y
CONSISTENTE entre las tareas. Si son parecidas, si la nueva es distinta pero
no mejor, o si solo gana en una tarea de varias, NO es una mejora real — di
que no. Es mucho mejor conservar lo que ya funciona que sustituirlo por algo
que no está probado que sea mejor.

Responde SOLO con este JSON, sin texto alrededor:
{"improved": true|false,
 "confidence": 0.0-1.0,
 "verdict": "2-4 frases explicando la comparación, en español",
 "per_task": [{"better": "before|after|tie", "why": "una frase"}]}"""


async def _generate_candidate(skill_text: str, task: str,
                              *, exclude: tuple = ()) -> tuple[str, Optional[str]]:
    """Cómo abordaría la tarea un agente guiado por ESTA versión de la skill.
    Texto puro, sin herramientas: es lo que hace la comparación segura y
    agnóstica de dominio (frontend/backend/marketing… todas producen texto).

    Devuelve (texto, modelo_que_lo_generó) — vacío si el MEL no responde."""
    import app.mel as mel

    peticion = mel.ExecutionRequest(
        capability=mel.Capability.ANALYZE,
        prompt=f"Tarea:\n{task[:_MAX_TASK_CHARS]}",
        system_prompt=_SYSTEM_CANDIDATE.format(skill_text=skill_text[:2000]),
        exclude=tuple(exclude),
    )
    # [2026-08-08] Sin plazo propio — es una llamada del trabajo nocturno de
    # comparación de skills, no algo que el usuario esté esperando.
    try:
        res = await mel.complete(peticion)
    except Exception as e:
        logger.info(f"[learner/comparison] candidato falló ({e!r})")
        return "", None
    if not getattr(res, "ok", False):
        return "", None
    servido = getattr(res, "served_by", None)
    modelo = f"{servido.provider}:{servido.model}" if servido else None
    return (res.text or "").strip()[:_MAX_CANDIDATE_CHARS], modelo


async def compare_skill_change(*, skill_name: str, current_description: str,
                               proposed_change: str,
                               sample_tasks: list[str]) -> Optional[dict]:
    """¿La versión NUEVA de una skill es de verdad mejor que la actual?

    LÍMITE HONESTO: "antes" y "después" se generan con llamadas MEL
    independientes, así que la política puede servirlas con modelos
    distintos — no es un banco de pruebas de laboratorio con el mismo modelo
    fijado en ambos lados. Lo que sí se controla es lo que de verdad importa
    para la pregunta ("¿el texto de la skill cambia el resultado?"): la
    MISMA tarea entra en los dos lados, y el juez ve qué modelo sirvió cada
    candidato (`candidate_models`) para que la comparación sea auditable.

    Genera, para cada tarea de ejemplo (recortadas a `MAX_SAMPLE_TASKS`), la
    respuesta de un agente guiado por la versión actual y por la propuesta,
    y las compara con un juez independiente (capacidad LEARN, excluyendo si
    puede a los modelos que generaron los candidatos — mismo anti-sesgo que
    el juez de misiones).

    Devuelve None si no se pudo comparar (sin tareas, MEL caído, timeout) —
    el llamador trata eso como "sin verificar", NUNCA como "mejora
    confirmada": lo mecánico solo puede quitar confianza, jamás ponerla
    (doc 41 §5, la misma regla que el grounding del juez)."""
    tareas = [t.strip() for t in (sample_tasks or []) if t and t.strip()][:MAX_SAMPLE_TASKS]
    if not tareas:
        return None

    proposed_description = f"{current_description}\n\nCAMBIO PROPUESTO: {proposed_change}"

    muestras: list[dict] = []
    modelos_candidatos: set = set()
    for tarea in tareas:
        antes, modelo_antes = await _generate_candidate(current_description, tarea)
        despues, modelo_despues = await _generate_candidate(proposed_description, tarea)
        if not antes or not despues:
            continue          # esta tarea no se pudo comparar; se sigue con las demás
        if modelo_antes:
            modelos_candidatos.add(modelo_antes)
        if modelo_despues:
            modelos_candidatos.add(modelo_despues)
        muestras.append({"task": tarea, "before": antes, "after": despues})

    if not muestras:
        return None            # ninguna tarea se pudo comparar: sin verificar, no sin mejora

    data, modelo_juez = await _ask_judge(skill_name, muestras,
                                         exclude=tuple(sorted(modelos_candidatos)))
    if not data:
        return None

    mejora = bool(data.get("improved") is True)
    try:
        confianza = max(0.0, min(1.0, float(data.get("confidence") or 0.0)))
    except Exception:
        confianza = 0.0
    por_tarea = data.get("per_task") if isinstance(data.get("per_task"), list) else []

    return {
        "improved": mejora,
        "confidence": confianza,
        "verdict": str(data.get("verdict") or "")[:600],
        "per_task": [
            {"task": m["task"][:200],
             "better": (por_tarea[i] or {}).get("better") if i < len(por_tarea) else None,
             "why": (por_tarea[i] or {}).get("why", "")[:200] if i < len(por_tarea) else ""}
            for i, m in enumerate(muestras)
        ],
        "samples": muestras,
        "judge_model": modelo_juez,
        "candidate_models": sorted(modelos_candidatos),
    }


async def _ask_judge(skill_name: str, muestras: list[dict],
                     *, exclude: tuple) -> tuple[Optional[dict], Optional[str]]:
    import app.mel as mel

    entrada = {"skill": skill_name,
              "comparaciones": [{"tarea": m["task"], "before": m["before"],
                                 "after": m["after"]} for m in muestras]}
    peticion = mel.ExecutionRequest(
        capability=mel.Capability.LEARN,
        prompt=("Compara estas dos versiones de la skill «" + skill_name + "»:\n\n"
                + json.dumps(entrada, ensure_ascii=False, indent=1)[:12000]),
        system_prompt=_SYSTEM_COMPARE,
        exclude=exclude,
    )
    # [2026-08-08] Sin plazo propio (capacidad LEARN, trabajo de fondo — ver
    # judge.py). El `except` genérico sigue siendo la red de seguridad ante
    # un fallo real.
    try:
        res = await mel.complete(peticion)
    except Exception as e:
        logger.info(f"[learner/comparison] el juez de la comparación falló ({e!r})")
        return None, None
    if not getattr(res, "ok", False):
        return None, None
    servido = getattr(res, "served_by", None)
    modelo = f"{servido.provider}:{servido.model}" if servido else None
    try:
        from app.tie import extract_json

        data = extract_json(res.text or "")
    except Exception:
        data = None
    return (data if isinstance(data, dict) else None), modelo
