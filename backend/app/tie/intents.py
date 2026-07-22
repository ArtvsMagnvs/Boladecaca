# app/tie/intents.py — Goal/Intent classifier (doc 11-B §B.1, enriquecido, T1)
#
# La primera etapa del TIE, SIEMPRE con modelo barato (doc 14 §Model Router:
# fast_model). Lee un mensaje y produce un `Intent` COMPLETO: qué quiere el
# usuario, qué necesita (tools/planner/browser/computer/automation), qué contexto
# pedir al MOS y qué capacidad pedir al MEL. Es lo que permite al TIE, tras T1,
# "entender" antes de que existan planner/executor (T2-T4).
#
# Fail-safe barato (doc 11 B.1): ante CUALQUIER duda (LLM caído, JSON inválido,
# confianza < 0.55) → conversational. Nunca romper; siempre responder algo.
#
# La llamada al modelo va por `router.complete(capability="classify")` (T2) — el
# punto ÚNICO de llamada al LLM del TIE. Hoy el router delega en el proveedor
# activo del AIManager; cuando exista el MEL (E1) pasa a `mel.complete(...)` sin
# tocar este módulo. "classify" es una capacidad barata (doc 19 §3).
from __future__ import annotations

import json
import re
from typing import Optional

from app.ai.reasoning_filter import strip_reasoning
from app.core.logging_config import get_system_logger
from app.tie.contracts import MEL_CAPABILITIES, Intent, IntentType

logger = get_system_logger("tie.intents")

CONFIDENCE_FLOOR = 0.55  # < esto → se fuerza conversational (doc 11 B.1)

_SYSTEM_PROMPT = """Eres el clasificador de intenciones de Aithera (un asistente personal).
Recibes UN mensaje del usuario y devuelves SOLO un objeto JSON (sin texto extra, sin
markdown) que describe qué quiere y qué hace falta para resolverlo.

Campos del JSON (todos obligatorios):
- "type": uno de ["conversational","query","create","execute","automate"].
    conversational = charla o pregunta trivial que se responde de memoria.
    query = pregunta que puede requerir mirar datos del usuario (email, agenda, proyectos).
    create = crear algo (una tarea, un evento, un borrador de email, un documento).
    execute = ejecutar una acción o herramienta (enviar, mover ficheros, correr algo).
    automate = crear o gestionar una automatización/regla recurrente.
- "goal": RESUMEN FIEL del encargo en una frase imperativa, para mostrar en la interfaz.
    NO añadas información que no esté en el mensaje. NO interpretes ni amplíes.
    El sistema planifica sobre el mensaje ORIGINAL del usuario, no sobre tu resumen.
- "domain": lista de dominios afectados, subconjunto de ["email","calendar","project","task","memory","system","web","file","general"].
- "confidence": número 0..1, tu confianza en esta clasificación.
- "requires_planning": true SOLO si la tarea necesita un PLAN estructurado — pasos que
    dependen unos de otros, entregables intermedios que el usuario debe revisar, o
    coordinar varios dominios distintos (ej: "investiga los avances en IA, escribe un
    informe y envíamelo por email"). Una SECUENCIA MECÁNICA de acciones con
    herramientas NO necesita plan aunque tenga varios pasos: "abre YouTube y pon una
    canción", "crea una carpeta y dentro un archivo con este texto", "búscame un vuelo
    y ábrelo" son requires_planning=FALSE — se ejecutan de corrido con herramientas,
    sin plan que revisar. Ante la duda en tareas mecánicas, requires_planning=false.
- "requires_tools": lista de herramientas probables, subconjunto de ["filesystem","shell","git","powershell","email","calendar"].
- "requires_browser": true si hace falta navegar por internet (buscar, rellenar formularios web).
- "requires_computer": true si hace falta controlar el ordenador (clics, teclado en apps).
- "requires_automation": true si esto debería convertirse en una regla automática recurrente.
- "requires_memory": true si necesita contexto personal del usuario para responder bien.
- "memory_types": lista, subconjunto de ["mem_conversational","mem_personal","mem_project","mem_decision","mem_skill"].
- "context_query": string con la consulta de memoria a lanzar, o null si no aplica.
- "model_capability": qué tipo de modelo pedir, uno de ["chat","classify","extract","summarize","draft","reason","code","analyze"].
- "explicit_model": si el usuario NOMBRA un modelo de IA concreto para usar (p.ej. "usa DeepSeek para esto", "responde con Claude", "a partir de ahora todo el proyecto con GPT"), un objeto {"name": <el nombre tal cual lo dijo>, "scope": <"task"|"project"|"unspecified">}; si NO nombra ningún modelo, null.
    scope "task" = solo para ESTA petición o este mensaje.
    scope "project" = de forma permanente para todo el proyecto ("a partir de ahora", "siempre", "para todo el proyecto").
    scope "unspecified" = nombra un modelo pero no deja claro si es solo para esto o para siempre.
- "objectives": lista de los encargos DISTINTOS e INDEPENDIENTES que contiene el mensaje,
  cada uno como una frase imperativa.

  LA PRUEBA para decidir, y es la ÚNICA que importa: ¿el segundo encargo NECESITA el
  resultado del primero? Si NO lo necesita, son encargos SEPARADOS y van en la lista
  (se harán a la vez, en paralelo). Si SÍ lo necesita, es UN solo encargo con varios
  pasos encadenados y devuelves [].
  No cuentes verbos ni pasos: lo que decide es la DEPENDENCIA entre ellos.

    UNO (encadenado, devuelve []): "busca los vuelos más baratos a Roma y reserva el
      mejor" -> [] (no puedes reservar sin haber buscado antes).
    UNO (encadenado, devuelve []): "lee el informe y hazme un resumen" -> [] (el
      resumen necesita la lectura).

    VARIOS (independientes, van en la lista): "envía un email a X con asunto Y, y
      también abre YouTube y pon la canción Z"
      -> ["Enviar un email a X con asunto Y", "Abrir YouTube y reproducir la canción Z"]
      (poner música no necesita para nada que el email se haya enviado).
    VARIOS: "investiga los avances en IA, responde el email de Ana, y dime cómo va el
      proyecto X" -> ["Investigar los últimos avances en IA", "Responder el email de
      Ana", "Informar del estado del proyecto X"].

  Palabras como "también", "y además", "por otro lado", "aparte" casi siempre separan
  encargos independientes: fíjate en ellas.

Reglas: si dudas, usa type "conversational" y confidence baja. Para charla simple,
requires_* en false, model_capability "chat". Para tareas complejas de varios pasos,
requires_planning true y model_capability "reason". Si el usuario no menciona ningún
modelo de IA por su nombre, "explicit_model" es null. Devuelve SOLO el JSON."""


def _extract_json(text: str) -> Optional[dict]:
    """Extrae el primer objeto JSON de una respuesta del LLM, tolerante a
    ```json ... ``` y a texto alrededor. None si no hay JSON parseable.

    [2026-07-22, #209] Tolerante además a claves SIN comillas. Caso real
    medido en el Mission Lab: MiniMax-M2.7 emite sistemáticamente
    `[TOOL_CALL]\\n{tool: {"tool_id": ...}}\\n[/TOOL_CALL]` — el envoltorio ya
    lo cubría la heurística de llaves, pero `{tool:` (sin comillas) hacía
    fallar `json.loads` y el toolloop quemaba la iteración con un "responde
    SOLO con JSON" (7 de 12 vueltas perdidas en una misión real, y en el peor
    caso el texto crudo del tool-call se filtraba al usuario como respuesta).
    La reparación SOLO se intenta cuando el parseo estricto ya falló: un JSON
    válido jamás se toca."""
    if not text:
        return None
    # bloque ```json ... ``` o ``` ... ```
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else None
    if candidate is None:
        # primer { ... último } equilibrado (heurística simple pero robusta)
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return _parse_lax_json(candidate)


def _parse_lax_json(candidate: str) -> Optional[dict]:
    """Segundo intento: pone comillas a las claves desnudas (`{tool:` →
    `{"tool":`) y reintenta. Devuelve None si ni así parsea o si el resultado
    no es un objeto."""
    repaired = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)', r'\1"\2"\3', candidate)
    if repaired == candidate:
        return None
    try:
        out = json.loads(repaired)
        return out if isinstance(out, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


def _coerce_intent(data: dict, goal_fallback: str) -> Intent:
    """Sanea la salida cruda del LLM a un Intent válido. Cualquier campo ausente
    o inválido cae a un default seguro (nunca lanza)."""
    def _slist(v) -> list[str]:
        return [str(x) for x in v] if isinstance(v, list) else []

    def _bool(v) -> bool:
        return bool(v) if isinstance(v, (bool, int)) else str(v).strip().lower() in ("true", "1", "yes", "sí", "si")

    # type
    raw_type = str(data.get("type", "")).strip().lower()
    try:
        itype = IntentType(raw_type)
    except ValueError:
        itype = IntentType.CONVERSATIONAL

    # confidence 0..1
    try:
        conf = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))

    # model_capability ∈ MEL_CAPABILITIES
    cap = str(data.get("model_capability", "chat")).strip().lower()
    if cap not in MEL_CAPABILITIES:
        cap = "chat"

    goal = str(data.get("goal") or goal_fallback).strip() or goal_fallback
    ctx_q = data.get("context_query")
    ctx_q = str(ctx_q).strip() if ctx_q else None

    # explicit_model (E2b): {name, scope} si el usuario nombró un modelo, o None.
    explicit_model = None
    em = data.get("explicit_model")
    if isinstance(em, dict) and str(em.get("name") or "").strip():
        scope = str(em.get("scope", "unspecified")).strip().lower()
        if scope not in ("task", "project", "unspecified"):
            scope = "unspecified"
        explicit_model = {"name": str(em["name"]).strip(), "scope": scope}

    return Intent(
        type=itype,
        goal=goal,
        domain=_slist(data.get("domain")),
        confidence=conf,
        requires_planning=_bool(data.get("requires_planning")),
        requires_tools=_slist(data.get("requires_tools")),
        requires_browser=_bool(data.get("requires_browser")),
        requires_computer=_bool(data.get("requires_computer")),
        requires_automation=_bool(data.get("requires_automation")),
        requires_memory=_bool(data.get("requires_memory")),
        memory_types=_slist(data.get("memory_types")),
        context_query=ctx_q,
        model_capability=cap,
        explicit_model=explicit_model,
        # [R2] Un solo objetivo no es "descomposición": se normaliza a lista
        # vacía para que el Orquestador tenga UNA condición clara (>=2 = multi).
        objectives=_objectives(data.get("objectives")),
        raw=data if isinstance(data, dict) else {},
    )


def _objectives(value) -> list[str]:
    """Normaliza la lista de objetivos del clasificador. Con 0 o 1 devuelve []:
    un único encargo va por el camino de siempre, sin capa de orquestación."""
    items = [str(v).strip() for v in value if str(v).strip()] if isinstance(value, list) else []
    return items if len(items) >= 2 else []


async def classify(text: str, *, channel: Optional[str] = None) -> Intent:
    """Clasifica un mensaje → Intent completo. Modelo barato; fail-safe a
    conversational. `channel` es informativo (no cambia la clasificación)."""
    text = (text or "").strip()
    if not text:
        return Intent.conversational_fallback(goal="")

    try:
        from app.tie import router

        result = await router.complete(text, system_prompt=_SYSTEM_PROMPT, capability="classify")
        if result.get("error"):
            logger.info(f"[intents] clasificador devolvió error, fallback conversational: {result.get('response','')[:80]}")
            return Intent.conversational_fallback(goal=text)

        raw = strip_reasoning(result.get("response", "") or "")
        data = _extract_json(raw)
        if not data:
            logger.info("[intents] sin JSON parseable, fallback conversational")
            return Intent.conversational_fallback(goal=text)

        intent = _coerce_intent(data, goal_fallback=text)
        # [S2, C-1] El texto ORIGINAL viaja SIEMPRE en el intent, intacto. El
        # planner planifica sobre esto; `goal` (reescrito por el LLM) queda
        # como resumen para UI/trazas. Se estampa AQUÍ, no en _coerce_intent,
        # para que ningún JSON del modelo pueda pisarlo.
        intent.raw_text = text

        # Umbral de confianza (doc 11 B.1): por debajo, se trata como charla — pero
        # se conservan los campos detectados en `raw` para la traza.
        if intent.confidence < CONFIDENCE_FLOOR:
            intent.type = IntentType.CONVERSATIONAL
            intent.requires_planning = False
        return intent
    except Exception as e:  # jamás romper el pipeline por el clasificador
        logger.error(f"[intents] excepción clasificando (fallback conversational): {type(e).__name__}: {e}")
        return Intent.conversational_fallback(goal=text)
