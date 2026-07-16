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
# En T1 la llamada al modelo va por `ai_manager` directo (proveedor activo). En
# T2 `router.fast()` la enruta al modelo barato como política; cuando exista el
# MEL (E1), será `mel.complete(capability="classify")`. Un solo punto que tocar.
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
- "goal": el objetivo en una frase imperativa y verificable (reformula el mensaje).
- "domain": lista de dominios afectados, subconjunto de ["email","calendar","project","task","memory","system","web","file","general"].
- "confidence": número 0..1, tu confianza en esta clasificación.
- "requires_planning": true si hace falta un plan de varios pasos (no una sola acción).
- "requires_tools": lista de herramientas probables, subconjunto de ["filesystem","shell","git","powershell","email","calendar"].
- "requires_browser": true si hace falta navegar por internet (buscar, rellenar formularios web).
- "requires_computer": true si hace falta controlar el ordenador (clics, teclado en apps).
- "requires_automation": true si esto debería convertirse en una regla automática recurrente.
- "requires_memory": true si necesita contexto personal del usuario para responder bien.
- "memory_types": lista, subconjunto de ["mem_conversational","mem_personal","mem_project","mem_decision","mem_skill"].
- "context_query": string con la consulta de memoria a lanzar, o null si no aplica.
- "model_capability": qué tipo de modelo pedir, uno de ["chat","classify","extract","summarize","draft","reason","code","analyze"].

Reglas: si dudas, usa type "conversational" y confidence baja. Para charla simple,
requires_* en false, model_capability "chat". Para tareas complejas de varios pasos,
requires_planning true y model_capability "reason". Devuelve SOLO el JSON."""


def _extract_json(text: str) -> Optional[dict]:
    """Extrae el primer objeto JSON de una respuesta del LLM, tolerante a
    ```json ... ``` y a texto alrededor. None si no hay JSON parseable."""
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
        raw=data if isinstance(data, dict) else {},
    )


async def classify(text: str, *, channel: Optional[str] = None) -> Intent:
    """Clasifica un mensaje → Intent completo. Modelo barato; fail-safe a
    conversational. `channel` es informativo (no cambia la clasificación)."""
    text = (text or "").strip()
    if not text:
        return Intent.conversational_fallback(goal="")

    try:
        # T1: proveedor activo directo. T2 → router.fast(); E1 → mel(capability="classify").
        from app.ai.ai_manager import ai_manager

        result = await ai_manager.chat(message=text, system_prompt=_SYSTEM_PROMPT)
        if result.get("error"):
            logger.info(f"[intents] clasificador devolvió error, fallback conversational: {result.get('response','')[:80]}")
            return Intent.conversational_fallback(goal=text)

        raw = strip_reasoning(result.get("response", "") or "")
        data = _extract_json(raw)
        if not data:
            logger.info("[intents] sin JSON parseable, fallback conversational")
            return Intent.conversational_fallback(goal=text)

        intent = _coerce_intent(data, goal_fallback=text)

        # Umbral de confianza (doc 11 B.1): por debajo, se trata como charla — pero
        # se conservan los campos detectados en `raw` para la traza.
        if intent.confidence < CONFIDENCE_FLOOR:
            intent.type = IntentType.CONVERSATIONAL
            intent.requires_planning = False
        return intent
    except Exception as e:  # jamás romper el pipeline por el clasificador
        logger.error(f"[intents] excepción clasificando (fallback conversational): {type(e).__name__}: {e}")
        return Intent.conversational_fallback(goal=text)
