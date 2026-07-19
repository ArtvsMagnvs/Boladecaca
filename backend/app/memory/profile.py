# app/memory/profile.py — R6.5c: "que te vaya conociendo" (doc 23)
#
# Del historial reciente del chat se destilan HECHOS ESTABLES sobre el usuario
# — su nombre, a qué se dedica, cómo prefiere que le hablen, qué herramientas
# usa — y se guardan en mem_personal para que cualquier conversación NUEVA y
# sin relación pueda usarlos (vía memory_router.context(), ya enganchado al
# chat desde V0.85 M4).
#
# EL CORAZÓN DEL SPRINT es distinguir hecho de anécdota: "me llamo X" o
# "trabajo en Y" son hechos; "hoy estoy cansado" o "ábreme el navegador" no.
# Ante la duda, NO se guarda — un perfil lleno de ruido es peor que uno corto.
#
# Corre en el job nocturno (mismo horario que el resumen diario de
# summarizer.py), NUNCA en el camino caliente del chat: conocerte no puede
# costar latencia en cada mensaje.
#
# FRONTERA CON doc 15 (Learning System): esto NO es el Learner. El Learner
# (V1.1+) aprende a hacer TAREAS — skills, patrones repetidos. Esto solo
# recuerda HECHOS sobre el usuario. Anotado en doc 15 para que V1.1 no lo
# duplique.
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from typing import Optional

from app.db.database import SessionLocal
from app.db.models import ChatMessage, MemoryJobRun

JOB_PROFILE = "memory_profile_distill"
FACT_KIND = "profile_fact"

# El job es nocturno, no "reconstruye toda tu vida" cada vez: unos días de
# historial bastan, los hechos estables se repiten. Topes duros para que una
# pasada nunca sea desproporcionada ni en coste ni en tiempo.
MAX_MESSAGES_PER_RUN = 200
MAX_CHARS_PER_RUN = 12_000
MAX_FACTS_PER_RUN = 20


# ---------------------------------------------------------------------------
# Tracking del job (mismo patrón que ingestion.py/summarizer.py)
# ---------------------------------------------------------------------------
def _start_run() -> int:
    db = SessionLocal()
    try:
        run = MemoryJobRun(job_name=JOB_PROFILE, started_at=datetime.utcnow(), status="running")
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id
    finally:
        db.close()


def _finish_run(run_id: int, *, status: str, items_processed: int = 0,
                error_detail: Optional[str] = None, checkpoint: Optional[dict] = None) -> None:
    db = SessionLocal()
    try:
        run = db.get(MemoryJobRun, run_id)
        if run is None:
            return
        run.finished_at = datetime.utcnow()
        run.status = status
        run.items_processed = items_processed
        run.error_detail = error_detail
        if checkpoint is not None:
            run.checkpoint = json.dumps(checkpoint, ensure_ascii=False)
        db.commit()
    finally:
        db.close()


def last_run() -> Optional[MemoryJobRun]:
    db = SessionLocal()
    try:
        return (
            db.query(MemoryJobRun)
            .filter(MemoryJobRun.job_name == JOB_PROFILE)
            .order_by(MemoryJobRun.id.desc())
            .first()
        )
    finally:
        db.close()


def _last_checkpoint_id() -> int:
    """El id del último ChatMessage ya procesado. Sin checkpoint, se procesa
    desde el principio (primera pasada del job)."""
    run = last_run()
    if run is None or not run.checkpoint:
        return 0
    try:
        return int(json.loads(run.checkpoint).get("last_chat_id", 0))
    except (ValueError, TypeError, json.JSONDecodeError):
        return 0


# ---------------------------------------------------------------------------
# Selección del historial — solo lo que el usuario ESCRIBIÓ
# ---------------------------------------------------------------------------
def _pending_user_messages(after_id: int) -> list[ChatMessage]:
    """Mensajes de usuario nuevos desde el checkpoint. Solo `role="user"`: el
    hecho vive en lo que la persona cuenta de sí misma, no en lo que Aithera
    le contesta — meter las respuestas del asistente solo añadiría ruido."""
    db = SessionLocal()
    try:
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.role == "user")
            .filter(ChatMessage.id > after_id)
            .order_by(ChatMessage.id.asc())
            .limit(MAX_MESSAGES_PER_RUN)
            .all()
        )
    finally:
        db.close()


def _build_chat_text(messages: list[ChatMessage]) -> str:
    lines: list[str] = []
    total = 0
    for m in messages:
        line = (m.content or "").strip()
        if not line:
            continue
        if total + len(line) > MAX_CHARS_PER_RUN:
            break
        lines.append(line)
        total += len(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Extracción — el corazón del sprint
# ---------------------------------------------------------------------------
_EXTRACTION_SYSTEM = """Extraes HECHOS ESTABLES sobre un usuario a partir de sus mensajes a un asistente.

Un HECHO sigue siendo cierto días o meses después: su nombre, a qué se dedica,
dónde vive, qué herramientas usa habitualmente, cómo prefiere que le hablen,
sus gustos duraderos.

NO es un hecho: su estado de ánimo de hoy, una tarea puntual que pidió hacer,
una pregunta suelta, un dato de una conversación de una sola vez.

Ejemplos SOLO PARA ENSEÑARTE EL FORMATO Y EL CRITERIO — NO son datos reales de
nadie, y NUNCA debes repetirlos en tu respuesta salvo que el texto real de abajo
diga LITERALMENTE lo mismo:
  "me llamo Fulano" -> HECHO (nombre)
  "trabajo como electricista" -> HECHO (ocupación)
  "prefiero que me hables de tú, sin rodeos" -> HECHO (estilo de comunicación)
  "uso Excel y Photoshop para casi todo" -> HECHO (herramientas)
  "hoy estoy agotado" -> NO es un hecho (estado de ánimo pasajero)
  "ábreme el navegador y busca vuelos a Roma" -> NO es un hecho (una tarea)
  "¿cuánto cuesta una Rockrider 540?" -> NO es un hecho (una pregunta suelta)

Ante la duda, NO lo incluyas: un perfil lleno de ruido es peor que uno corto. Si
el texto real de abajo no contiene ningún hecho estable de verdad, la respuesta
correcta es [] — NO inventes ni copies "Fulano", "electricista" ni ningún otro
dato de los ejemplos, son solo ilustración.

Devuelve SOLO un JSON: una lista de objetos
  {"key": "<2-3 palabras en snake_case, en español, ej. nombre / ocupacion / estilo_comunicacion>",
   "value": "<el hecho en una frase corta, tercera persona, ej. 'Se llama Fulano'>"}
Si no hay ningún hecho estable, devuelve []."""


# [R6.5c, hallazgo de la verificación en vivo] Defensa en profundidad: un
# modelo económico procesó un mensaje SIN hechos reales y, en vez de devolver
# [], copió literalmente los ejemplos ilustrativos del prompt como si fueran
# datos del usuario — 4 hechos falsos llegaron a persistirse. La instrucción
# de arriba ya avisa de no copiarlos; esto es el respaldo si el modelo no la
# sigue: cualquier valor idéntico a la salida esperada de un ejemplo se
# descarta, nunca se guarda. Mismo criterio que la defensa en profundidad de
# `miniMarkdown.tsx` (el prompt no es 100% fiable, el código sí).
_FEWSHOT_TRAPS = {
    "se llama fulano",
    "trabaja como electricista",
    "prefiere que le hablen de tú, sin rodeos",
    "usa excel y photoshop para casi todo",
}


def _extract_json_array(text: str) -> Optional[list]:
    """Extrae el array JSON de una respuesta del LLM, tolerante a
    ```json ... ``` y a texto alrededor. Réplica local (no importada de
    app.tie, que es un módulo consumidor de app.memory, no al revés — doc 16).

    Respaldo [hallazgo real de la verificación en vivo con el modelo local
    económico]: en vez de un array, a veces devuelve varios objetos `{...}`
    sueltos, uno por línea, sin envolverlos en `[]`. Se reconstruye la lista a
    partir de los objetos individuales que sí parsean — más tolerante sin
    dejar de ser determinista (un objeto malformado se descarta, no rompe
    a los demás)."""
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else None
    if candidate is None:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]
    if candidate:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

    objetos = []
    for m in re.finditer(r"\{[^{}]*\}", text):
        try:
            obj = json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, dict):
            objetos.append(obj)
    return objetos or None


def _normalize_key(raw: str) -> str:
    """Reconciliación best-effort entre pasadas: si el modelo dice "Nombre" un
    día y "nombre del usuario" otro, normalizar reduce (no elimina del todo)
    la divergencia — límite conocido y aceptado del sprint (doc 23 R6.5c: se
    afina un prompt, no un motor de reconciliación semántica)."""
    s = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:40] or "hecho"


async def extract_facts(chat_text: str) -> list[dict]:
    """[R6.5c] `policy_override="economy"`: job nocturno, coste 0 primero —
    igual que el resumen diario, no debe encarecerse porque el usuario tenga
    Quality puesto para el chat. Fail-soft total: cualquier fallo devuelve []
    (sin hechos esta pasada), nunca rompe el job."""
    if not chat_text.strip():
        return []
    from app.mel import Capability, ExecutionRequest, complete as mel_complete

    try:
        res = await mel_complete(ExecutionRequest(
            capability=Capability.EXTRACT, prompt=chat_text, system_prompt=_EXTRACTION_SYSTEM,
            policy_override="economy",
        ))
    except Exception as e:
        print(f"[profile] extracción falló (fail-soft, sin hechos esta pasada): {e}")
        return []
    if not res.ok or not res.text.strip():
        return []

    data = _extract_json_array(res.text)
    if not data:
        return []

    hechos: list[dict] = []
    for item in data[:MAX_FACTS_PER_RUN]:
        if not isinstance(item, dict):
            continue
        raw_key = str(item.get("key") or "").strip()
        value = str(item.get("value") or "").strip()
        if not raw_key or not value:
            continue
        if value.lower() in _FEWSHOT_TRAPS:
            continue
        hechos.append({"key": _normalize_key(raw_key), "label": raw_key, "value": value})
    return hechos


# ---------------------------------------------------------------------------
# El job — orquesta checkpoint + extracción + persistencia
# ---------------------------------------------------------------------------
async def distill() -> dict:
    """Una pasada del destilado nocturno. Solo procesa mensajes NUEVOS desde
    el último checkpoint: reprocesar toda la historia cada noche sería caro y
    no cambiaría el resultado (los hechos ya guardados se ACTUALIZAN, no se
    duplican, por `dedup_key`)."""
    from app.core.events import emit
    from app.memory import MemoryType, memory_router

    # El checkpoint se lee ANTES de abrir la fila `running` de esta pasada:
    # `_start_run()` inserta una fila nueva (la más reciente por id), así que
    # leerlo después se vería a sí mismo — checkpoint vacío siempre, y cada
    # pasada reprocesaría TODO el historial de nuevo.
    after_id = _last_checkpoint_id()
    run_id = _start_run()
    try:
        messages = _pending_user_messages(after_id)
        if not messages:
            _finish_run(run_id, status="ok", items_processed=0)
            return {"job": JOB_PROFILE, "status": "ok", "facts_stored": 0, "messages_seen": 0}

        chat_text = _build_chat_text(messages)
        hechos = await extract_facts(chat_text)

        today = datetime.utcnow().date().isoformat()
        # `memory_router.store()` es fail-soft por contrato (nunca lanza; "" si
        # la memoria está caída) — contarlo aparte de `len(hechos)` importa: sin
        # esto, una memoria caída se reportaría igual como "N hechos guardados"
        # cuando en realidad no se guardó ninguno (encontrado en la
        # verificación en vivo de R6.5c: un script sin ChromaDB inicializado
        # devolvía "facts_stored: 2" con el perfil realmente vacío).
        stored = 0
        for hecho in hechos:
            item_id = await memory_router.store(
                content=hecho["value"],
                memory_type=MemoryType.PERSONAL,
                source="profile",
                metadata={
                    "kind": FACT_KIND, "key": hecho["key"], "label": hecho["label"], "date": today,
                },
                dedup_key=f"profile:{hecho['key']}",
            )
            if item_id:
                stored += 1

        last_id = messages[-1].id
        _finish_run(run_id, status="ok", items_processed=stored,
                    checkpoint={"last_chat_id": last_id})
        if stored:
            emit("memory.ingested", source="mos",
                payload={"job": JOB_PROFILE, "items_new": stored})
        return {
            "job": JOB_PROFILE, "status": "ok",
            "facts_stored": stored, "messages_seen": len(messages),
        }
    except Exception as e:
        _finish_run(run_id, status="error", error_detail=f"{type(e).__name__}: {e}")
        return {"job": JOB_PROFILE, "status": "error", "reason": str(e)}


# ---------------------------------------------------------------------------
# Lectura/borrado — para la pantalla de Ajustes (visible y reversible)
# ---------------------------------------------------------------------------
def list_facts() -> list[dict]:
    """Todos los hechos guardados. Lectura DIRECTA de la colección (mismo
    patrón que /api/memory/stats): "listar todo por metadata" no es una
    operación del contrato `IMemoryStore` (que solo ofrece búsqueda semántica
    o borrado por filtro) — forzar un método nuevo en un contrato congelado
    por una pantalla de settings no está justificado (doc 16)."""
    from app.memory.interfaces import MemoryType
    from app.memory.memory_manager import memory_manager

    col = memory_manager.get_or_create_collection(MemoryType.PERSONAL.value)
    if col is None:
        return []
    got = col.get(where={"kind": FACT_KIND})
    ids = got.get("ids", []) or []
    docs = got.get("documents", []) or []
    metas = got.get("metadatas", []) or []
    items = [
        {
            "key": (meta or {}).get("key", ""),
            "label": (meta or {}).get("label") or (meta or {}).get("key", ""),
            "value": doc,
            "updated_at": (meta or {}).get("created_at_iso"),
        }
        for _id, doc, meta in zip(ids, docs, metas)
    ]
    items.sort(key=lambda it: it["label"].lower())
    return items


async def delete_fact(key: str) -> bool:
    """Borra un hecho por su key normalizada. Reversible: si el modelo lo
    vuelve a ver en el chat, se re-extrae la próxima noche — borrar no lo
    "prohíbe", solo lo olvida ahora. Sin esto el perfil sería una caja negra
    que solo acumula suposiciones sobre datos personales."""
    from app.memory import MemoryType, memory_router

    n = await memory_router.forget(
        MemoryType.PERSONAL, filters={"$and": [{"kind": FACT_KIND}, {"key": key}]}
    )
    return n > 0


# V0.9 (A2a): la programación nocturna vive en APScheduler, wiring en el
# lifespan de main.py (mismo patrón que ingestion.py/summarizer.py). `distill`
# (arriba) es la función de trabajo — la llama el scheduler.
