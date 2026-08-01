# app/memory/quick_memory.py — router DETERMINISTA de comandos de memoria
# (PU10, doc 35): "guarda que...", "¿qué sabes de...?", "olvida lo de..." se
# resuelven SIN LLM y SIN pasar por el pipeline completo del chat — ni
# clasificador, ni planificador, ni toolloop. Mismo espíritu que
# `app.tie.quick_answers` (SQL/ChromaDB directo, plantilla, 0 alucinación).
#
# UN SOLO CAMINO DE ESCRITURA (PU10 §2/§3): dos consumidores comparten esta
# MISMA función —
#   1. La pestaña Memoria de Ajustes (mini-chat directo, `POST /api/memory/
#      quick`), donde CUALQUIER frase es sobre memoria por definición del
#      panel: "guarda que..." ya basta, sin ancla.
#   2. El chat principal (`app.tie.pipeline` y `app.orchestrator`, los
#      MISMOS dos puntos donde PU4 enganchó el briefing — el orquestador
#      tiene su propio precheck síncrono anterior al del TIE), donde SÍ se
#      exige un ancla explícita ("en la memoria", "como preferencia") para
#      no confundirse con `app.tie.action_intent._wants_to_persist` (NEW-7b,
#      que detecta "guárdame un resumen" para escribir un ARCHIVO — un caso
#      completamente distinto: aquí no se toca el disco, solo `user_context`).
#
# GUARDAR SIEMPRE escribe en `user_context` (la colección de preferencias que
# `chat_service.build_system_prompt()` YA inyecta en cada turno) — NUNCA en
# `mem_personal` genérica, que solo sale por similitud semántica y no
# garantiza que una instrucción de comportamiento se "aplique" en la
# siguiente respuesta. Es la decisión explícita de PU10 §2.
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal, Optional

from app.core.strings import t as _t

Action = Literal["save", "search", "forget"]

_MAX_WORDS = 80  # una instrucción de comportamiento puede ser larga


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def _slug(text: str, maxlen: int = 40) -> str:
    """Genera una key estable a partir del contenido — mismo patrón que
    `app.memory.profile._normalize_key`. Guardar dos veces una instrucción muy
    parecida ACTUALIZA en vez de duplicar (comportamiento ya incorporado en
    `store_user_context`), que es lo deseable para una preferencia."""
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:maxlen] or "preferencia"


# ---------------------------------------------------------------------------
# Parseo — prefijos SIN ancla (mini-chat de Ajustes: el panel ya es memoria) y
# CON ancla (chat principal: hace falta mencionar explícitamente la memoria).
# ---------------------------------------------------------------------------
_SAVE_PREFIXES = (
    "guarda que ", "guardame que ", "guarda esto: ", "guarda esto ",
    "recuerda que ", "recuerda esto: ", "recuerda esto ",
    "anota que ", "apunta que ", "anota esto: ", "apunta esto: ",
    "save that ", "remember that ", "remember: ", "remember this: ",
    "souviens-toi que ", "note que ",
    "lembra-te que ", "lembra que ", "anota que ",
)
_SAVE_ANCHORED_PREFIXES = (
    "guarda esto en la memoria: ", "guarda esto en la memoria ",
    "guarda en la memoria que ", "guarda en la memoria: ", "guarda en la memoria ",
    "guarda en tu memoria que ", "guarda en tu memoria: ", "guarda en tu memoria ",
    "guarda como preferencia que ", "guarda como preferencia: ",
    "save this in memory: ", "save this in memory that ", "save this to memory: ",
    "remember this as a preference: ",
    "garde ceci dans ta memoire : ", "garde ceci en memoire : ",
    "guarda isto na memoria: ", "guarda isto na tua memoria: ",
)

# "Bare" (mini-chat, sin ancla): genéricas, valdrían igual en cualquier charla.
_SEARCH_PREFIXES = (
    "que sabes de ", "que sabes sobre ", "que recuerdas de ", "que recuerdas sobre ",
    "que tienes guardado de ", "que tienes guardado sobre ",
    "what do you know about ", "what do you remember about ",
    "que sais-tu de ", "que sais-tu sur ",
    "o que sabes sobre ", "o que sabes de ",
)
# "Ancladas" (mención EXPLÍCITA a la memoria): las únicas válidas desde el chat
# principal — inequívocas incluso en mitad de una charla normal.
_SEARCH_ANCHORED_PREFIXES = (
    "busca en la memoria ", "busca en tu memoria ", "busca en memoria ",
    "search your memory for ", "search memory for ",
    "cherche dans ta memoire ", "cherche dans la memoire ",
    "procura na tua memoria ", "procura na memoria ",
)

# Bare (mini-chat): "olvida que"/"olvida esto" ya son inequívocos DENTRO del
# panel de memoria, pero demasiado genéricos para interceptarlos a media
# charla normal ("olvídalo, no importa" es una muletilla, no un comando).
_FORGET_PREFIXES = (
    "olvida que ", "olvida esto: ", "olvida esto ", "olvida lo de ",
    "forget that ", "forget this: ",
    "oublie que ", "oublie ceci : ",
    "esquece que ", "esquece isto: ",
)
# Ancladas (chat principal): mencionan "memoria" de forma explícita.
_FORGET_ANCHORED_PREFIXES = (
    "borra de la memoria ", "borra esto de la memoria ", "borra de tu memoria ",
    "elimina de la memoria ", "elimina de tu memoria ",
    "olvida esto de la memoria ", "olvida esto de tu memoria ",
    "forget this from memory: ", "forget this from memory ",
    "oublie ceci de ta memoire : ", "oublie ceci de la memoire : ",
    "esquece isto da memoria: ", "esquece isto da tua memoria: ",
)


@dataclass
class MemoryCommand:
    action: Action
    payload: str  # contenido a guardar/buscar/olvidar, ya sin el prefijo


def _clean_leading(raw: str) -> str:
    """Quita signos de apertura ("¿"/"¡") y espacio suelto al principio, para
    que el prefijo (siempre ASCII llano) pueda alinearse con el texto real."""
    return raw.lstrip("¿¡ \t\n")


def _strip_prefix(raw: str, prefixes: tuple) -> Optional[str]:
    cleaned = _clean_leading(raw)
    norm = _norm(cleaned)
    for p in prefixes:
        if norm.startswith(p):
            resto = cleaned[len(p):].strip(" .:\"'¡!¿?")
            return resto
    return None


def parse(text: str, *, require_anchor: bool = False) -> Optional[MemoryCommand]:
    """Determinista, 0 LLM. `require_anchor=True` (chat principal): solo
    dispara con un prefijo que menciona explícitamente la memoria — evita que
    "guárdame un resumen de la reunión" (NEW-7b, un archivo) o un "olvida lo
    que dije antes" suelto a media charla se confundan con un comando de
    memoria. `require_anchor=False` (mini-chat de Ajustes): el panel entero ya
    es sobre memoria, así que "guarda que X" solo basta."""
    raw = (text or "").strip()
    if not raw or len(raw.split()) > _MAX_WORDS:
        return None

    # Mismo patrón en los tres: solo las ANCLADAS valen desde el chat
    # principal; el mini-chat de Ajustes admite además las "bare" (el panel
    # entero ya es sobre memoria, no hace falta que lo repita el usuario).
    save_prefixes = _SAVE_ANCHORED_PREFIXES if require_anchor else (
        _SAVE_ANCHORED_PREFIXES + _SAVE_PREFIXES
    )
    payload = _strip_prefix(raw, save_prefixes)
    if payload:
        return MemoryCommand(action="save", payload=payload)

    search_prefixes = _SEARCH_ANCHORED_PREFIXES if require_anchor else (
        _SEARCH_ANCHORED_PREFIXES + _SEARCH_PREFIXES
    )
    payload = _strip_prefix(raw, search_prefixes)
    if payload:
        return MemoryCommand(action="search", payload=payload)

    forget_prefixes = _FORGET_ANCHORED_PREFIXES if require_anchor else (
        _FORGET_ANCHORED_PREFIXES + _FORGET_PREFIXES
    )
    payload = _strip_prefix(raw, forget_prefixes)
    if payload:
        return MemoryCommand(action="forget", payload=payload)

    return None


# ---------------------------------------------------------------------------
# Ejecución — SIEMPRE async (I/O de ChromaDB), nunca lanza.
# ---------------------------------------------------------------------------
async def _do_save(payload: str) -> dict:
    from app.memory.memory_manager import memory_manager

    content = (payload or "").strip()
    if not content:
        return {"ok": False, "action": "save", "reply": _t("quick.memory.save_empty")}
    if not memory_manager.is_healthy():
        return {"ok": False, "action": "save", "reply": _t("quick.memory.unavailable")}
    key = _slug(content)
    doc_id = memory_manager.store_user_context(key=key, content=content, category="preference")
    if not doc_id:
        return {"ok": False, "action": "save", "reply": _t("quick.memory.save_failed")}
    return {
        "ok": True, "action": "save", "key": key, "content": content,
        "reply": _t("quick.memory.saved", content=content),
    }


async def _do_search(payload: str) -> dict:
    from app.memory import MemoryType, memory_router
    from app.memory import profile as _profile
    from app.memory.memory_manager import memory_manager

    query = (payload or "").strip()
    if not query:
        return {"ok": False, "action": "search", "reply": _t("quick.memory.search_empty")}

    prefs: list = []
    if memory_manager.is_healthy():
        try:
            prefs = memory_manager.search_user_context(query, n_results=5)
        except Exception:
            prefs = []

    # [Fix 2026-08-02, reportado por el usuario] `mem_personal` NO es "hechos
    # sobre ti": la ingesta de email (M2, ingestion.py) escribe AHÍ MISMO cada
    # asunto+snippet del inbox con `kind="inbox_item"` (para el briefing/
    # triaje), mezclado con los hechos curados que sí destila R6.5c
    # (`profile.py`, `kind=FACT_KIND`). Sin filtrar por `kind`, una pregunta
    # vaga como "¿qué sabes de mí?" devolvía lo que fuera semánticamente más
    # cercano de TODA la colección — incluidos boletines/notificaciones de
    # marketing del inbox, presentados como si Aithera los hubiera "aprendido"
    # sobre la persona. El filtro restringe la búsqueda a los hechos REALMENTE
    # destilados de lo que el usuario ha contado en el chat (R6.5c) — la misma
    # fuente que ya muestra "Lo que Aithera sabe de ti" en Ajustes → Memoria.
    facts: list[str] = []
    try:
        items = await memory_router.search(
            query, memory_types=[MemoryType.PERSONAL], top_k=5,
            filters={"kind": _profile.FACT_KIND},
        )
        facts = [it.content for it in items]
    except Exception:
        facts = []

    if not prefs and not facts:
        return {
            "ok": True, "action": "search", "results": [],
            "reply": _t("quick.memory.search_empty_result", query=query),
        }

    lines: list[str] = []
    if prefs:
        lines.append(_t("quick.memory.search_prefs_header"))
        lines += [f"- {p['content']}" for p in prefs]
    if facts:
        lines.append(_t("quick.memory.search_facts_header"))
        lines += [f"- {f}" for f in facts]
    return {
        "ok": True, "action": "search",
        "results": [p["content"] for p in prefs] + facts,
        "reply": "\n".join(lines),
    }


async def _do_forget(payload: str) -> dict:
    from app.memory.memory_manager import memory_manager

    raw_query = (payload or "").strip()
    query = _norm(raw_query)
    if not query:
        return {"ok": False, "action": "forget", "reply": _t("quick.memory.forget_empty")}
    if not memory_manager.is_healthy():
        return {"ok": False, "action": "forget", "reply": _t("quick.memory.unavailable")}

    items = memory_manager.list_user_context()
    matches = [it for it in items if query in _norm(it.get("content") or "")]

    if not matches:
        return {
            "ok": True, "action": "forget",
            "reply": _t("quick.memory.forget_none", query=raw_query),
        }
    if len(matches) > 1:
        lines = [_t("quick.memory.forget_ambiguous", n=len(matches))]
        lines += [f"- {m['content']}" for m in matches]
        return {"ok": True, "action": "forget", "ambiguous": True, "reply": "\n".join(lines)}

    target = matches[0]
    ok = memory_manager.delete_user_context(target["key"])
    if not ok:
        return {"ok": False, "action": "forget", "reply": _t("quick.memory.forget_failed")}
    return {
        "ok": True, "action": "forget", "content": target["content"],
        "reply": _t("quick.memory.forgotten", content=target["content"]),
    }


async def execute(cmd: MemoryCommand) -> dict:
    """Ejecuta un `MemoryCommand` ya parseado. Nunca lanza: cualquier fallo
    del backend de memoria vuelve como `{"ok": False, "reply": "..."}`."""
    try:
        if cmd.action == "save":
            return await _do_save(cmd.payload)
        if cmd.action == "search":
            return await _do_search(cmd.payload)
        return await _do_forget(cmd.payload)
    except Exception as e:
        return {"ok": False, "action": cmd.action, "reply": f"{type(e).__name__}: {e}"}


async def handle(text: str, *, require_anchor: bool = False) -> Optional[dict]:
    """Punto único: parsea Y ejecuta. `None` si el texto no es un comando de
    memoria reconocible — el mini-chat de Ajustes muestra entonces una pista,
    el chat principal sigue su pipeline normal (nunca sustituye al LLM)."""
    try:
        cmd = parse(text, require_anchor=require_anchor)
        if cmd is None:
            return None
        return await execute(cmd)
    except Exception:
        return None


async def try_answer_async(text: str) -> Optional[str]:
    """Hermano de `app.tie.quick_answers.try_answer_async` (mismo tipo de
    retorno, mismo criterio de enganche): para el chat PRINCIPAL, con ancla
    OBLIGATORIA. `None` si no aplica → sigue el pipeline normal."""
    result = await handle(text, require_anchor=True)
    if result is None:
        return None
    return result.get("reply")
