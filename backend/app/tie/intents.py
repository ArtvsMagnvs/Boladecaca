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

import asyncio
import json
import re
import unicodedata
from typing import Optional

from app.ai.reasoning_filter import strip_reasoning
from app.core.logging_config import get_system_logger
from app.tie import action_intent
from app.tie.contracts import MEL_CAPABILITIES, Intent, IntentType

logger = get_system_logger("tie.intents")

CONFIDENCE_FLOOR = 0.55  # < esto → se fuerza conversational (doc 11 B.1)


# ===========================================================================
# [A·VOZ-2, doc 32] Pre-clasificador barato: la charla trivial NO paga LLM
# ===========================================================================
# EL PROBLEMA (medido en código): `classify()` es una llamada LLM completa
# (prompt de sistema de ~120 líneas + salida JSON) que se ESPERA antes del
# primer token de respuesta — el 100% de los mensajes la paga, incluida la
# charla trivial ("hola", "gracias"). Con un modelo de classify lento o
# razonador (`<think>`) son decenas de segundos antes de responder. En la
# conversación por voz eso la hace inusable (el usuario reporta ~1 min).
#
# LA SOLUCIÓN: un heurístico DETERMINISTA (0 LLM) resuelve la charla obvia
# antes de tocar el modelo. Conservador por diseño — ante CUALQUIER duda
# devuelve None (que clasifique el LLM): un falso "no es charla" solo cuesta
# el round-trip de siempre; un falso "es charla" perdería una acción, así que
# jamás se arriesga. Solo dispara cuando TODOS los tokens del mensaje son de
# cortesía/saludo (o coincide una frase de charla exacta) — si aparece
# cualquier palabra de acción, dominio, o un mensaje largo, cae a None.

def _normalize(text: str) -> str:
    """minúsculas + sin acentos + sin signos de puntuación de los extremos, para
    que 'Adiós!' y 'adios' o '¿Cómo estás?' y 'como estas' coincidan igual."""
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t


# Frases de charla EXACTAS (ya normalizadas). Cubren el grueso de la charla real.
_CHITCHAT_PHRASES: frozenset[str] = frozenset({
    # saludos
    "hola", "holaa", "holaaa", "buenas", "hey", "ey", "hola aithera",
    "buenos dias", "buenas tardes", "buenas noches", "saludos", "hi", "hello",
    # cómo estás / qué tal
    "que tal", "que tal aithera", "que tal todo", "como estas", "como estas aithera",
    "como te va", "como va", "como va todo", "todo bien", "que pasa", "que hay",
    "how are you", "how are you doing", "whats up", "good morning", "good evening",
    # agradecimientos
    "gracias", "muchas gracias", "muchisimas gracias", "mil gracias",
    "gracias aithera", "vale gracias", "ok gracias", "perfecto gracias",
    "thanks", "thank you", "thanks a lot",
    # despedidas
    "adios", "hasta luego", "hasta pronto", "hasta manana", "hasta la proxima",
    "nos vemos", "chao", "chau", "bye", "goodbye", "see you",
    # confirmaciones / cortesía
    "vale", "ok", "okay", "okey", "dale", "de acuerdo", "perfecto", "genial",
    "estupendo", "guay", "bien", "muy bien", "entendido", "listo", "claro",
    "sure", "cool", "nice", "great", "fine", "alright", "got it",
})

# Tokens de cortesía/saludo/relleno. Si TODOS los tokens de un mensaje corto
# están aquí, es charla (cubre combinaciones no listadas: "hola buenas gracias").
_COURTESY_TOKENS: frozenset[str] = frozenset({
    "hola", "holaa", "holaaa", "buenas", "hey", "ey", "hi", "hello", "saludos", "aithera",
    "gracias", "muchas", "muchisimas", "mil", "thx", "thanks", "thank", "you", "ty",
    "adios", "chao", "chau", "bye", "goodbye", "hasta", "luego", "pronto", "manana",
    "proxima", "nos", "vemos", "see",
    "vale", "ok", "oka", "okay", "okey", "dale", "listo", "perfecto", "genial", "guay",
    "bien", "muy", "estupendo", "entendido", "claro", "exacto", "correcto", "acuerdo",
    "si", "no", "por", "favor", "nada", "un", "placer", "encantado", "de",
    "que", "tal", "como", "estas", "va", "todo", "tu", "pasa", "hay", "te", "y",
    "buenos", "dias", "tardes", "noches",
    "please", "cool", "nice", "great", "fine", "alright", "got", "it", "sure", "yes",
    "good", "morning", "evening", "night", "how", "are", "whats", "up", "doing", "a", "lot",
})

_MAX_PRECHECK_WORDS = 6   # un mensaje largo casi nunca es charla pura → al LLM


def fast_precheck(text: str) -> Optional[Intent]:
    """Devuelve un Intent CONVERSACIONAL instantáneo (0 LLM) si el mensaje es
    charla obvia; None si hay que clasificar con el modelo. Función pura,
    determinista y conservadora (ante la duda, None)."""
    raw = (text or "").strip()
    if not raw:
        return None
    norm = _normalize(raw)
    # tokens sin puntuación (una URL/@/número rompe el patrón de cortesía)
    tokens = [tok.strip(".,;:!?¡¿()[]{}\"'…-") for tok in norm.split()]
    tokens = [tok for tok in tokens if tok]
    if not tokens or len(tokens) > _MAX_PRECHECK_WORDS:
        return None

    # frase exacta de charla (normalizada, colapsando espacios)
    phrase = " ".join(tokens)
    is_chitchat = phrase in _CHITCHAT_PHRASES
    # o TODOS los tokens son de cortesía (cubre combinaciones no listadas)
    if not is_chitchat:
        is_chitchat = all(tok in _COURTESY_TOKENS for tok in tokens)
    if not is_chitchat:
        return None

    return Intent(
        type=IntentType.CONVERSATIONAL,
        goal=raw,
        confidence=1.0,           # el heurístico está seguro; no fuerza el floor
        model_capability="chat",
        raw_text=raw,             # fidelidad del texto original (S2)
    )

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
- "requires_tools": lista de herramientas probables, subconjunto de ["filesystem","shell","git","powershell","email","calendar","aithera","memory","search","browser","document","download","process"].
    USA "document" para leer o crear PDF, Word (.docx) o Excel (.xlsx) — "filesystem"
    solo maneja texto plano, no abre esos formatos (si hace falta localizar el archivo,
    incluye AMBAS). "download" para descargar un archivo de internet al ordenador.
    "process" para ver, abrir o cerrar programas del equipo.
    USA "aithera" siempre que el usuario quiera OPERAR LA PROPIA APP: gestionar SUS
    proyectos, hitos, tareas, agentes, reglas de automatización o recordatorios —
    p.ej. "crea un proyecto llamado X", "abre el proyecto Y", "en el proyecto Z crea
    un agente con el modelo Minimax y skills de backend", "crea una regla de email
    que…", "muéstrame/lista mis proyectos o agentes". Esas peticiones son type
    "execute" o "create" con requires_tools=["aithera"] y requires_planning=false
    (una acción directa, no un plan que revisar) SALVO que encadenen varios pasos
    dependientes. Los DATOS de sus proyectos ya están en tu contexto: para "¿qué
    proyectos tengo?" NO hace falta herramienta (respóndelo de tu contexto); "aithera"
    es para ACTUAR (crear/abrir/modificar), no para leer lo que ya sabes.
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
    # [2026-07-22, task-bench] ARRAY de tool calls: MiniMax-M2.7 emite a veces
    # `[{"tool": A}, {"tool": B}]` — varios objetos de golpe. La heurística
    # primer-{...último-} produce `{A}, {B}` (inválido) y la iteración se
    # perdía; medido en el banco: TODOS los code_write de M2.7/M2.7-highspeed
    # caían por esto. Se parsea el array y se toma el PRIMER dict útil (el
    # bucle es elegir-UNA-acción-observar: ejecutar la primera y devolver la
    # observación es exactamente el contrato).
    arr_start = text.find("[")
    obj_start = text.find("{")
    if arr_start != -1 and (obj_start == -1 or arr_start < obj_start):
        arr_end = text.rfind("]")
        if arr_end > arr_start:
            data = _try_parse(text[arr_start:arr_end + 1])
            if isinstance(data, list):
                for el in data:
                    if isinstance(el, dict) and ("tool" in el or "answer" in el):
                        return el
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
    out = _try_parse(candidate)
    if isinstance(out, dict):
        return out
    # [2026-08-02] VARIOS objetos SUELTOS en un mismo mensaje: `{A}\n{B}` (sin
    # array que los envuelva, así que el camino de arriba no aplica). La
    # heurística primer-{...último-} produce `{A}\n{B}`, que NO es JSON válido,
    # y hasta aquí eso equivalía a "el modelo respondió en prosa": la vuelta se
    # quemaba y, si era la ÚLTIMA, el texto CRUDO —con los tool-calls dentro—
    # se guardaba como resultado del nodo y aparecía tal cual en el Log de
    # Misiones (caso real reportado por el usuario: un nodo "Hecha" cuyo
    # contenido eran dos líneas `{"tool": {...}}`). Se toma el PRIMER objeto
    # BALANCEADO, que es exactamente el contrato del bucle (elegir UNA acción,
    # ejecutarla, observar) y el mismo criterio que ya se aplicaba al array.
    first = _first_balanced_object(text)
    if first is not None:
        out = _try_parse(first)
        if isinstance(out, dict):
            return out
    return None


def _first_balanced_object(text: str) -> Optional[str]:
    """El primer `{...}` con las llaves equilibradas, ignorando las que estén
    dentro de una cadena JSON (y sus escapes). None si no hay ninguno cerrado."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _try_parse(candidate: str):
    """json.loads estricto y, si falla, la reparación de claves desnudas. None
    si ni así. (Compartido por el camino objeto y el camino array.)"""
    try:
        return json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return _parse_lax_json_any(candidate)


def _parse_lax_json_any(candidate: str):
    """Reparación de claves desnudas (`{tool:` → `{"tool":`) admitiendo
    también arrays como raíz. None si ni así parsea."""
    repaired = re.sub(r'([{,\[]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)', r'\1"\2"\3', candidate)
    if repaired == candidate:
        return None
    try:
        return json.loads(repaired)
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
    conversational. `channel` es informativo (no cambia la clasificación).

    [A·VOZ-2] La charla obvia se resuelve ANTES de tocar el LLM: `fast_precheck`
    (0 LLM, determinista) corta el round-trip del clasificador para ~la mayoría
    de turnos conversacionales. Es el arreglo de latencia — un "hola" ya no
    espera una llamada completa al modelo antes de responder.

    [NEW-7b, doc 34] `ensure_persistence_tool` se aplica al final, sobre
    CUALQUIER salida de `_classify_core` (venga del LLM o de un rescate
    determinista) — "guárdame un resumen" necesita `filesystem` sin importar
    por qué camino se clasificó el mensaje."""
    intent = await _classify_core(text, channel=channel)
    return action_intent.ensure_persistence_tool(intent, text)


async def _classify_core(text: str, *, channel: Optional[str] = None) -> Intent:
    text = (text or "").strip()
    if not text:
        return Intent.conversational_fallback(goal="")

    pre = fast_precheck(text)
    if pre is not None:
        logger.info(f"[tie-perfil] precheck HIT (charla, 0 LLM): {text[:40]!r}")
        return pre

    # [2026-07-25] RED DE SEGURIDAD DE ACCIONES. `_safe_action` se usa en TODOS
    # los caminos de fallo de abajo: si el LLM no da JSON, devuelve error o
    # lanza, una petición de ACCIÓN sobre Aithera NO puede degradar a charla
    # (era el fallo real: el turno acababa en chat sin tools y el modelo fingía
    # haber creado la milestone/agente). Determinista, 0 LLM.
    def _safe_action() -> Optional[Intent]:
        try:
            return action_intent.action_intent(text)
        except Exception:
            return None

    # [NEW-7, doc 34] MISMA red de seguridad, un escalón más afuera: una
    # petición de LEER EL MUNDO (archivos, web, correo, agenda) tampoco puede
    # degradar a charla — el camino corto no tiene NINGUNA herramienta, así que
    # ahí el modelo solo puede inventarse el listado, el número o el contenido
    # (verificado en vivo el 28-jul: inventó los imports de `pipeline.py`).
    # Se consulta DESPUÉS de `_safe_action`: una orden sobre la propia Aithera
    # es más específica y manda si ambas coinciden.
    def _safe_rescue() -> Optional[Intent]:
        act = _safe_action()
        if act is not None:
            return act
        try:
            return action_intent.world_intent(text)
        except Exception:
            return None

    try:
        from app.core.config import settings as _settings
        from app.tie import router

        # [S4·P5] Modelo/política del clasificador — MISMO patrón que el bucle de
        # tool-use (`toolloop.run`): un modelo fijado manda; si no, la política
        # rápida. `classify` corre en el camino caliente de CADA mensaje no
        # trivial, así que no puede heredar la política de CALIDAD del usuario
        # (custom→opus = decenas de segundos para un parseo estructurado).
        _cls_model = _settings.TIE_CLASSIFY_MODEL or None
        _cls_policy = None if _cls_model else (_settings.TIE_CLASSIFY_POLICY or None)

        # [A·VOZ-6 profiling] Cuánto tarda el clasificador de verdad, y con qué
        # modelo: es lo que domina el "analizando" de un mensaje NO trivial. Si
        # esto son decenas de segundos, el modelo de `classify` está mal
        # enrutado (debería ser rápido/local, doc 19 §3) — se ve en el log.
        import time as _t
        _c0 = _t.monotonic()
        # [S4 · NEW-2] DEADLINE del clasificador. Sin él, un proveedor lento
        # podía dejar el turno entero en "analizando" durante minutos (el único
        # tope era el del propio provider, y por salto de cadena). Al vencer se
        # degrada por el MISMO camino que ya existía para su error — no hay una
        # segunda forma de fallar que mantener.
        _deadline = _settings.TIE_CLASSIFY_DEADLINE_S
        _call = router.complete(text, system_prompt=_SYSTEM_PROMPT, capability="classify",
                                model_override=_cls_model, policy_override=_cls_policy)
        result = await (asyncio.wait_for(_call, timeout=_deadline) if _deadline > 0 else _call)
        _cms = int((_t.monotonic() - _c0) * 1000)
        logger.info(f"[tie-perfil] classify LLM: {_cms}ms modelo={result.get('model')!r}")
        if result.get("error"):
            act = _safe_rescue()
            if act is not None:
                logger.info("[intents] clasificador con error PERO el mensaje pide una acción "
                            "o una lectura real → intent determinista (no charla)")
                return act
            logger.info(f"[intents] clasificador devolvió error, fallback conversational: {result.get('response','')[:80]}")
            return Intent.conversational_fallback(goal=text)

        raw = strip_reasoning(result.get("response", "") or "")
        data = _extract_json(raw)
        if not data:
            act = _safe_rescue()
            if act is not None:
                logger.info("[intents] sin JSON parseable PERO el mensaje pide una acción "
                            "o una lectura real → intent determinista (no charla)")
                return act
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
            # [NEW-7] …salvo que el mensaje pida DEMOSTRABLEMENTE leer el mundo
            # real. El suelo existe para no actuar sobre una corazonada; pero
            # "charla sin herramientas" tampoco es un default seguro cuando el
            # usuario ha pedido un archivo concreto: ahí el modelo se lo inventa.
            rescate = _safe_rescue()
            if rescate is not None:
                logger.info(f"[intents] confianza {intent.confidence:.2f} < suelo PERO el "
                            f"mensaje pide una lectura real → intent determinista (no charla)")
                return rescate
            intent.type = IntentType.CONVERSATIONAL
            intent.requires_planning = False

        # [2026-07-25] CORRECCIÓN de una clasificación floja. Los modelos
        # pequeños confunden una ORDEN ("créame una milestone MVP") con charla, o
        # aciertan el tipo pero se olvidan de pedir la herramienta. Si el
        # detector determinista ve una acción sobre Aithera:
        #   · tipo conversational/query → se sube a EXECUTE (si no, el turno
        #     acabaría en chat sin tools y el modelo fingiría haberlo hecho);
        #   · falte la tool `aithera` → se añade (sin quitar las que sí detectó).
        # NO se toca nada más del intent del LLM (objetivos, memoria, planning
        # cuando él lo pidió): su criterio se respeta donde es fiable.
        if _safe_action() is not None:
            if intent.type in (IntentType.CONVERSATIONAL, IntentType.QUERY):
                logger.info(f"[intents] el modelo dijo {intent.type.value!r} pero el mensaje "
                            f"es una ORDEN sobre Aithera → EXECUTE con tool 'aithera'")
                intent.type = IntentType.EXECUTE
            if "aithera" not in (intent.requires_tools or []):
                intent.requires_tools = list(intent.requires_tools or []) + ["aithera"]
        return intent
    except Exception as e:  # jamás romper el pipeline por el clasificador
        act = _safe_rescue()
        if act is not None:
            logger.error(f"[intents] excepción clasificando PERO el mensaje pide una acción "
                         f"o una lectura real → intent determinista: {type(e).__name__}: {e}")
            return act
        logger.error(f"[intents] excepción clasificando (fallback conversational): {type(e).__name__}: {e}")
        return Intent.conversational_fallback(goal=text)
