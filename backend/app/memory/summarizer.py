# app/memory/summarizer.py — Resumen nocturno + datos del briefing (V0.85 M3)
#
# Job diario a las 03:30 LOCAL (no UTC: es una hora pensada para el usuario
# dormido, no para bookkeeping interno — por eso usa datetime.now(), a
# diferencia del resto del codigo que usa datetime.utcnow()). Genera el
# resumen del dia: emails por categoria de triaje + agenda + nº conversaciones.
#
# Modelo: Ollama si esta sano (coste 0) -> proveedor activo -> plantilla
# determinista (el sistema degrada, NUNCA se salta el dia). Salida siempre por
# strip_reasoning() (B21).
#
# Persistencia: item en mem_personal (kind=daily_summary, dedup_key=day:{date}
# -> re-ejecutar un dia lo sobreescribe) + MemoryJobRun. La misma funcion de
# recogida de datos (_gather_day_data) la usa tambien GET /api/memory/briefing
# (endpoints/memory.py) para no duplicar logica entre el job y el endpoint.
from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta
from typing import Any, Optional

from app.core.events import emit
from app.db.database import SessionLocal
from app.db.models import EmailActivityLog, EmailTriage, MemoryJobRun
from app.memory import MemoryType, memory_manager, memory_router, vault_write_daily_summary

JOB_SUMMARIZER = "memory_summarize_daily"
DAILY_HOUR, DAILY_MINUTE = 3, 30  # hora local del job nocturno (doc 07 §7)

TOP_SENDERS_LIMIT = 5
URGENT_PENDING_LIMIT = 10
AGENDA_LIMIT = 10


# ---------------------------------------------------------------------------
# Tracking (mismo patron que ingestion.py)
# ---------------------------------------------------------------------------
def _start_run() -> int:
    db = SessionLocal()
    try:
        run = MemoryJobRun(job_name=JOB_SUMMARIZER, started_at=datetime.utcnow(), status="running")
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id
    finally:
        db.close()


def _finish_run(run_id: int, *, status: str, items_processed: int = 0, error_detail: Optional[str] = None) -> None:
    db = SessionLocal()
    try:
        run = db.get(MemoryJobRun, run_id)
        if run is None:
            return
        run.finished_at = datetime.utcnow()
        run.status = status
        run.items_processed = items_processed
        run.error_detail = error_detail
        db.commit()
    finally:
        db.close()


def last_run() -> Optional[MemoryJobRun]:
    db = SessionLocal()
    try:
        return (
            db.query(MemoryJobRun)
            .filter(MemoryJobRun.job_name == JOB_SUMMARIZER)
            .order_by(MemoryJobRun.id.desc())
            .first()
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Recogida de datos del dia — la usan el job Y el endpoint /briefing
# ---------------------------------------------------------------------------
def _triage_rows_for_date(db, target_date: date) -> list[EmailTriage]:
    """EmailTriage no tiene indice por fecha de creacion (solo por email_id/
    category); son pocas filas por dia, se filtra en Python (mismo patron que
    daily_digest en email_activity.py)."""
    return [
        r for r in db.query(EmailTriage).all()
        if r.created_at and r.created_at.date() == target_date
    ]


def _urgent_pending(db) -> tuple[list[dict[str, Any]], int]:
    """'Pendiente' = triado como urgente y SIN ninguna accion registrada
    todavia (no es un estado del dia: sigue pendiente hasta que se actua)."""
    touched = {
        row[0] for row in db.query(EmailActivityLog.email_id)
        .filter(EmailActivityLog.email_id.isnot(None)).distinct().all()
    }
    rows = (
        db.query(EmailTriage)
        .filter(EmailTriage.category == "urgente")
        .order_by(EmailTriage.created_at.desc())
        .all()
    )
    pending = [r for r in rows if r.email_id not in touched]
    return [
        {"email_id": r.email_id, "sender": r.sender, "subject": r.subject}
        for r in pending[:URGENT_PENDING_LIMIT]
    ], len(pending)


def _top_senders(rows: list[EmailTriage]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for r in rows:
        if r.sender:
            counts[r.sender] = counts.get(r.sender, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    return [{"sender": s, "count": c} for s, c in ranked[:TOP_SENDERS_LIMIT]]


def _agenda_for_date(target_date: date) -> list[dict[str, Any]]:
    """Lee los items kind=agenda_item ya ingestados en mem_personal (M2 —
    local + Google, sin llamar a Google en caliente). event_start viene sin
    formato uniforme (fecha sola en eventos de dia completo, datetime en el
    resto), asi que el filtro por dia se hace en Python, NUNCA con un
    where $gte/$lte de Chroma sobre ese campo (comparacion lexicografica
    incorrecta entre 'YYYY-MM-DD' y 'YYYY-MM-DDTHH:MM:SS')."""
    col = memory_manager.get_or_create_collection(MemoryType.PERSONAL.value)
    if col is None:
        return []
    got = col.get(where={"kind": "agenda_item"})
    metas = got.get("metadatas", []) if got else []
    docs = got.get("documents", []) if got else []
    target_iso = target_date.isoformat()
    items = []
    for meta, doc in zip(metas, docs):
        start = str((meta or {}).get("event_start", ""))
        if start[:10] == target_iso:
            items.append({"title": (doc or "").split("\n", 1)[0], "start": start})
    items.sort(key=lambda it: it["start"])
    return items[:AGENDA_LIMIT]


def _conversations_count(target_date: date) -> int:
    """Cuenta turnos de usuario ese dia en la coleccion legacy 'conversations'
    (mem_conversational). NOTA: esta version de ChromaDB (1.5.x) solo admite
    $gte/$lte sobre numeros, no sobre strings (fecha ISO) — asi que el filtro
    por dia se hace en Python, no con un where-range de Chroma."""
    col = memory_manager.get_or_create_collection("conversations")
    if col is None:
        return 0
    got = col.get(where={"role": "user"})
    target_iso = target_date.isoformat()
    metas = got.get("metadatas", []) if got else []
    return sum(1 for m in metas if str((m or {}).get("timestamp", "")).startswith(target_iso))


def gather_day_data(target_date: date) -> dict[str, Any]:
    """TODO lo que necesita el resumen/briefing de un dia. Solo BD/Chroma
    local — nunca Gmail ni Google Calendar en caliente (doc 07 §7/§8)."""
    db = SessionLocal()
    try:
        triage_rows = _triage_rows_for_date(db, target_date)
        triage_counts: dict[str, int] = {}
        for r in triage_rows:
            triage_counts[r.category] = triage_counts.get(r.category, 0) + 1
        urgent_items, urgent_total = _urgent_pending(db)
        top_senders = _top_senders(triage_rows)
    finally:
        db.close()

    return {
        "date": target_date.isoformat(),
        "triage_counts": triage_counts,
        "triaged_total": len(triage_rows),
        "urgent_pending": {"count": urgent_total, "items": urgent_items},
        "agenda": _agenda_for_date(target_date),
        "top_senders": top_senders,
        "conversations_count": _conversations_count(target_date),
    }


# ---------------------------------------------------------------------------
# Texto del resumen — determinista (siempre disponible) + LLM (mejor esfuerzo)
# ---------------------------------------------------------------------------
def build_deterministic_summary(data: dict[str, Any]) -> str:
    """Plantilla con conteos y asuntos top. Cero coste, cero red — el sistema
    NUNCA se queda sin resumen (doc 07 §7)."""
    d = data["date"]
    parts = [f"Resumen del {d}: {data['triaged_total']} emails triados."]
    if data["triage_counts"]:
        by_cat = ", ".join(f"{v} {k}" for k, v in sorted(data["triage_counts"].items(), key=lambda kv: -kv[1]))
        parts.append(f"Categorías: {by_cat}.")
    urgent = data["urgent_pending"]["count"]
    if urgent:
        subjects = "; ".join(it["subject"] or "(sin asunto)" for it in data["urgent_pending"]["items"][:3])
        parts.append(f"{urgent} urgentes pendientes de atención: {subjects}.")
    if data["agenda"]:
        parts.append(f"{len(data['agenda'])} eventos en la agenda de hoy.")
    if data["conversations_count"]:
        parts.append(f"{data['conversations_count']} intervenciones en el chat.")
    if len(parts) == 1:
        parts.append("Sin actividad relevante.")
    return " ".join(parts)


_SUMMARY_SYSTEM = (
    "Eres el asistente personal de Aithera. Redactas un resumen diario breve "
    "(2-4 frases), en español, tono natural y directo, a partir de datos ya "
    "calculados. No inventes datos que no esten en la entrada."
)


async def _try_llm_summary(data: dict[str, Any]) -> Optional[str]:
    """Ollama primero (coste 0) -> proveedor activo -> None (el caller usa la
    plantilla determinista). Nunca lanza."""
    from app.ai.ai_manager import ai_manager
    from app.ai.reasoning_filter import strip_reasoning

    prompt = (
        f"Datos del {data['date']}: {data['triaged_total']} emails triados "
        f"({data['triage_counts']}); {data['urgent_pending']['count']} urgentes "
        f"pendientes; {len(data['agenda'])} eventos en la agenda; "
        f"{data['conversations_count']} intervenciones en el chat.\n"
        "Escribe el resumen del dia."
    )

    ollama = ai_manager.providers.get("ollama")
    if ollama is not None:
        try:
            if await ollama.health_check():
                result = await ollama.generate(prompt, system_prompt=_SUMMARY_SYSTEM)
                if not result.get("error") and result.get("response"):
                    return strip_reasoning(result["response"]).strip() or None
        except Exception as e:
            print(f"[summarizer] Ollama fallo (fail-soft, sigo con proveedor activo): {e}")

    try:
        result = await ai_manager.chat(prompt, system_prompt=_SUMMARY_SYSTEM)
        if not result.get("error") and result.get("response"):
            return strip_reasoning(result["response"]).strip() or None
    except Exception as e:
        print(f"[summarizer] proveedor activo fallo (fail-soft, uso plantilla): {e}")
    return None


async def build_summary_text(data: dict[str, Any]) -> str:
    """LLM si hay algo sano; si no, determinista. Nunca vacio."""
    llm_text = await _try_llm_summary(data)
    return llm_text or build_deterministic_summary(data)


# ---------------------------------------------------------------------------
# Lectura cacheada (la usa GET /api/memory/briefing) + escritura (el job)
# ---------------------------------------------------------------------------
async def get_cached_summary(target_date: date) -> Optional[str]:
    item = await memory_router.retrieve(f"{MemoryType.PERSONAL.value}:day:{target_date.isoformat()}")
    return item.content if item else None


async def run_summarizer(target_date: Optional[date] = None) -> dict[str, Any]:
    """Una pasada del resumen nocturno. Idempotente (dedup_key=day:{date}):
    re-ejecutar el mismo dia sobreescribe, nunca duplica."""
    target = target_date or datetime.utcnow().date()
    run_id = _start_run()
    try:
        data = gather_day_data(target)
        summary = await build_summary_text(data)
        await memory_router.store(
            content=summary,
            memory_type=MemoryType.PERSONAL,
            source="summarizer",
            metadata={"kind": "daily_summary", "date": target.isoformat()},
            dedup_key=f"day:{target.isoformat()}",
        )
        vault_write_daily_summary(target, summary)  # espejo Markdown (doc 07 §9, best-effort)
        _finish_run(run_id, status="ok", items_processed=1)
        emit("memory.ingested", source="mos", payload={"job": JOB_SUMMARIZER, "items_new": 1})
        return {"job": JOB_SUMMARIZER, "status": "ok", "date": target.isoformat(), "summary": summary}
    except Exception as e:
        _finish_run(run_id, status="error", error_detail=f"{type(e).__name__}: {e}")
        return {"job": JOB_SUMMARIZER, "status": "error", "date": target.isoformat(), "reason": str(e)}


# ---------------------------------------------------------------------------
# Loop de background (03:30 local)
# ---------------------------------------------------------------------------
def _seconds_until_next(hour: int, minute: int) -> float:
    now = datetime.now()  # hora LOCAL a proposito (doc 07 §7)
    target = datetime.combine(now.date(), time(hour, minute))
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def _loop() -> None:
    while True:
        try:
            await asyncio.sleep(_seconds_until_next(DAILY_HOUR, DAILY_MINUTE))
            await run_summarizer()
        except Exception as e:
            print(f"[summarizer] loop fallo (se reintenta manana): {e}")
            await asyncio.sleep(3600)  # red de seguridad: no busy-loop si algo va mal


def start_summarizer_job():
    return asyncio.create_task(_loop())
