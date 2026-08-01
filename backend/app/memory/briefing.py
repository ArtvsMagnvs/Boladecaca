# app/memory/briefing.py — Briefing 2.0: version hablada del briefing (PU4, doc 35)
#
# QUE AÑADE sobre lo que ya existia (V0.85 M3, summarizer.py): `summary` (2-4
# frases, texto) ya se generaba y cacheaba cada noche. Esta pieza añade
# `spoken_text` — una locucion de 30-60s pensada para VOZ, priorizada por
# accionabilidad (urgente -> agenda -> proyectos -> ayer), sintetizada por el
# MEL (SUMMARIZE, politica economy, igual que el resumen) con una plantilla
# determinista de respaldo (patron M3, obligatorio: el sistema NUNCA se queda
# sin texto que narrar).
#
# COSTE: el `spoken_text` se calcula UNA VEZ por noche (el job nocturno de
# summarizer.py lo cachea junto al resumen, ver `run_summarizer`) y se lee de
# cache el resto del dia — el mismo principio que ya regia para `summary`:
# "cero LLM en el critical path de un GET" (memory.py). Esto importa el doble
# aqui porque `GET /api/memory/briefing` lo sondea el Dock cada 30s (Dock.tsx)
# y el boton manual/el disparo automatico de las 8:15h deben responder al
# instante, sin esperar a un LLM.
#
# Bloque de NOTICIAS: deliberadamente FUERA de esta pieza (doc 35 PU4,
# "decision pendiente" resuelta 2026-07-31: se hace la base primero, la
# seleccion de fuentes de noticias sera una sesion aparte).
from __future__ import annotations

from datetime import date as date_cls
from typing import Any, Optional

from app.memory import MemoryType, memory_router

SPOKEN_KIND = "daily_briefing_spoken"


def _spoken_dedup_key(target: date_cls) -> str:
    return f"day:{target.isoformat()}:spoken"


def _plural(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


# ---------------------------------------------------------------------------
# Plantilla determinista — SIEMPRE disponible, cero coste, cero red.
# ---------------------------------------------------------------------------
def build_deterministic_spoken(data: dict[str, Any], summary: str) -> str:
    """Locucion de respaldo en español (mismo criterio que
    `summarizer.build_deterministic_summary`: plantilla fija, no traducida —
    el idioma de la locucion LLM si lo respeta via `language_directive()`,
    ver `_try_llm_spoken`). Ordenada por accionabilidad, sin bloque de
    noticias (fuera de alcance de esta sesion)."""
    parts: list[str] = []

    urgent = data["urgent_pending"]["count"]
    if urgent:
        subjects = ", ".join(
            it["subject"] or "sin asunto" for it in data["urgent_pending"]["items"][:3]
        )
        parts.append(
            f"Tienes {urgent} {_plural(urgent, 'correo urgente pendiente', 'correos urgentes pendientes')}: {subjects}."
        )

    agenda = data.get("agenda") or []
    if agenda:
        primero = agenda[0].get("title") or "un evento"
        parts.append(
            f"Hoy tienes {len(agenda)} {_plural(len(agenda), 'cosa', 'cosas')} en la agenda, "
            f"empezando por {primero}."
        )

    ws = data.get("workspace") or {}
    milestones = ws.get("active_milestones") or []
    if milestones:
        m = milestones[0]
        ratio = int(round((m.get("ratio") or 0) * 100))
        parts.append(
            f"El proyecto {m.get('project_name') or ''} va al {ratio} por ciento en su milestone activo.".replace("  ", " ")
        )

    deadlines = ws.get("upcoming_deadlines") or []
    if deadlines:
        n = len(deadlines)
        parts.append(f"Hay {n} {_plural(n, 'tarea', 'tareas')} con fecha límite esta semana.")

    blocked = ws.get("blocked") or []
    if blocked:
        n = len(blocked)
        parts.append(f"{n} {_plural(n, 'tarea sigue', 'tareas siguen')} bloqueada{'s' if n != 1 else ''}.")

    if not parts:
        return f"Buenos días. Hoy no hay nada urgente ni agendado. De ayer: {summary}"

    parts.append(f"De ayer: {summary}")
    return "Buenos días. " + " ".join(parts)


# ---------------------------------------------------------------------------
# Locucion via MEL (mejor esfuerzo) — misma politica economy que el resumen.
# ---------------------------------------------------------------------------
_SPOKEN_SYSTEM = (
    "Eres el asistente personal de Aithera. Vas a locutar un briefing "
    "matutino de 30 a 60 segundos hablados (unas 90-150 palabras), en voz "
    "alta para el usuario nada mas despertarse. Prioriza lo mas urgente/"
    "accionable primero (correos urgentes, agenda de hoy, proyectos, y por "
    "ultimo un resumen de ayer). Tono natural, como quien informa a alguien "
    "de confianza — nunca leas los datos como una lista, cuentalo con "
    "naturalidad y frases fluidas. No inventes nada que no este en los "
    "datos de entrada. No uses markdown ni emojis (esto se lee en voz alta)."
)


def _spoken_system() -> str:
    """Mismo patron que `summarizer._summary_system()` (PU8, doc 35): la
    directiva de idioma va primero si el usuario eligio uno; sin directiva,
    el prompt base (español) manda."""
    try:
        from app.core.language import language_directive

        directive = language_directive()
        if directive:
            return f"{_SPOKEN_SYSTEM}\n\n{directive}"
    except Exception as e:
        print(f"[briefing] no se pudo resolver el idioma (uso el default): {e}")
    return _SPOKEN_SYSTEM


def _facts_prompt(data: dict[str, Any], summary: str) -> str:
    urgent = data["urgent_pending"]
    agenda = data.get("agenda") or []
    ws = data.get("workspace") or {}
    lines = [
        f"Fecha: {data.get('date')}",
        f"Correos urgentes pendientes: {urgent['count']}"
        + (
            " (" + "; ".join(it["subject"] or "sin asunto" for it in urgent["items"][:3]) + ")"
            if urgent["items"]
            else ""
        ),
        f"Agenda de hoy: {len(agenda)} evento(s)"
        + (": " + "; ".join(a.get("title") or "" for a in agenda[:5]) if agenda else ""),
    ]
    milestones = ws.get("active_milestones") or []
    if milestones:
        m = milestones[0]
        ratio = int(round((m.get("ratio") or 0) * 100))
        lines.append(f"Milestone activo: {m.get('project_name')} — {ratio}%")
    deadlines = ws.get("upcoming_deadlines") or []
    if deadlines:
        lines.append(f"Tareas con fecha límite esta semana: {len(deadlines)}")
    blocked = ws.get("blocked") or []
    if blocked:
        lines.append(f"Tareas bloqueadas: {len(blocked)}")
    lines.append(f"Resumen de ayer: {summary}")
    return "\n".join(lines)


async def _try_llm_spoken(data: dict[str, Any], summary: str) -> Optional[str]:
    """[E2, doc 22] Locucion via MEL, capacidad SUMMARIZE, `policy_override=
    "economy"` (job de fondo — nunca se encarece porque el usuario tenga
    Quality en el chat, mismo criterio que `summarizer._try_llm_summary`).
    None si falla (el caller usa la plantilla determinista). Nunca lanza."""
    try:
        from app.ai.personalities import active_prompt
        from app.mel import Capability, ExecutionRequest, complete as mel_complete

        prompt = _facts_prompt(data, summary) + "\n\nRedacta la locución del briefing de hoy."
        res = await mel_complete(ExecutionRequest(
            capability=Capability.SUMMARIZE,
            prompt=prompt,
            system_prompt=f"{_spoken_system()}\n\n{active_prompt()}",
            policy_override="economy",
        ))
        if res.ok and res.text.strip():
            from app.voice.text_clean import clean_for_speech

            return clean_for_speech(res.text.strip())
    except Exception as e:
        print(f"[briefing] MEL falló para la locución (fail-soft, uso plantilla): {e}")
    return None


async def build_spoken_text(data: dict[str, Any], summary: str) -> str:
    """LLM si hay algo sano; si no, determinista. Nunca vacío."""
    llm_text = await _try_llm_spoken(data, summary)
    return llm_text or build_deterministic_spoken(data, summary)


# ---------------------------------------------------------------------------
# Cache diaria (mismo patron que get_cached_summary) + escritura (job nocturno)
# ---------------------------------------------------------------------------
async def get_cached_spoken(target: date_cls) -> Optional[str]:
    item = await memory_router.retrieve(f"{MemoryType.PERSONAL.value}:{_spoken_dedup_key(target)}")
    return item.content if item else None


async def store_spoken(target: date_cls, text: str) -> None:
    await memory_router.store(
        content=text,
        memory_type=MemoryType.PERSONAL,
        source="briefing",
        metadata={"kind": SPOKEN_KIND, "date": target.isoformat()},
        dedup_key=_spoken_dedup_key(target),
    )


async def spoken_text_for(target: date_cls, data: dict[str, Any], summary: str) -> tuple[str, str]:
    """(texto, fuente). Cache si existe (la escribió el job nocturno); si no,
    plantilla determinista AL VUELO — cero LLM en el critical path
    interactivo (mismo principio que `summary`/`summary_source` en
    `endpoints/memory.py`). Nunca lanza: cualquier fallo de lectura de cache
    cae a la plantilla."""
    try:
        cached = await get_cached_spoken(target)
    except Exception as e:
        print(f"[briefing] no se pudo leer la cache de la locución (uso plantilla): {e}")
        cached = None
    if cached:
        return cached, "cached"
    return build_deterministic_spoken(data, summary), "live_deterministic"


# ---------------------------------------------------------------------------
# [PU4b, doc 35] SEGMENTOS hablados — la partitura del "show" visual.
#
# El frontend no puede sincronizar visuales con una locución monolítica: para
# abrir la tarjeta del proyecto EXACTAMENTE cuando se habla de él, necesita la
# locución PARTIDA en pasos, cada uno con la referencia de lo que menciona
# (`focus`). Por eso los segmentos son DETERMINISTAS (plantilla, no LLM): la
# estructura ES el contrato de sincronización. `spoken_text` (arriba) sigue
# siendo la narración fluida para el chat ("dame el briefing" escrito); el
# show usa esto. Ambos salen de los MISMOS datos.
#
# Forma: [{kind, refs, steps: [{text, focus|null}]}] — kinds: greeting, email,
# calendar, projects, tasks, news, yesterday. Coste: cero LLM, cero red (las
# noticias vienen de la cache que escribió el job de preparación).
# ---------------------------------------------------------------------------
def _greeting_for_hour(hour: int) -> str:
    if 5 <= hour < 13:
        return "Buenos días."
    if 13 <= hour < 21:
        return "Buenas tardes."
    return "Buenas noches."


def build_spoken_segments(
    data: dict[str, Any],
    summary: str,
    news_cache: Optional[dict[str, Any]],
    config: dict[str, Any],
    *,
    hour: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Nunca lanza; con datos vacíos devuelve saludo + resumen de ayer."""
    from datetime import datetime

    sections = (config or {}).get("sections") or {}
    on = lambda key: bool(sections.get(key, True))  # noqa: E731
    if hour is None:
        hour = datetime.now().hour
    segments: list[dict[str, Any]] = []

    segments.append({
        "kind": "greeting",
        "refs": {},
        "steps": [{"text": _greeting_for_hour(hour) + " Este es tu briefing.", "focus": None}],
    })

    # --- Email: urgentes pendientes (los que piden acción YA) ---
    urgent = (data.get("urgent_pending") or {"count": 0, "items": []})
    if on("email") and urgent.get("count"):
        items = (urgent.get("items") or [])[:3]
        refs = {
            "items": [
                {
                    "email_id": it.get("email_id"),
                    "sender": it.get("sender"),
                    "subject": it.get("subject"),
                }
                for it in items
            ],
            "total": urgent["count"],
        }
        n = urgent["count"]
        steps = [{
            "text": f"Tienes {n} {_plural(n, 'correo urgente pendiente', 'correos urgentes pendientes')}.",
            "focus": None,
        }]
        for it in items:
            sender = (it.get("sender") or "remitente desconocido").split("<")[0].strip()
            subject = it.get("subject") or "sin asunto"
            steps.append({"text": f"De {sender}: {subject}.", "focus": it.get("email_id")})
        segments.append({"kind": "email", "refs": refs, "steps": steps})

    # --- Calendario: agenda de hoy ---
    agenda = data.get("agenda") or []
    if on("calendar") and agenda:
        refs = {"events": [{"title": a.get("title"), "start": a.get("start")} for a in agenda[:8]]}
        n = len(agenda)
        steps = [{
            "text": f"En la agenda de hoy, {n} {_plural(n, 'cita', 'citas')}.",
            "focus": None,
        }]
        for i, a in enumerate(agenda[:4]):
            title = a.get("title") or "un evento"
            hora = ""
            start = a.get("start") or ""
            if "T" in str(start):
                hora = f" a las {str(start).split('T')[1][:5]}"
            steps.append({"text": f"{title}{hora}.", "focus": f"ev:{i}"})
        segments.append({"kind": "calendar", "refs": refs, "steps": steps})

    ws = data.get("workspace") or {}

    # --- Proyectos: milestone activo + progreso ---
    milestones = ws.get("active_milestones") or []
    if on("projects") and milestones:
        refs = {
            "projects": [
                {
                    "project_id": m.get("project_id"),
                    "project_name": m.get("project_name"),
                    "milestone": m.get("name"),
                    "version": m.get("version"),
                    "ratio": m.get("ratio") or 0,
                    "done": m.get("done"),
                    "total": m.get("total"),
                }
                for m in milestones[:4]
            ]
        }
        steps = []
        for m in milestones[:3]:
            ratio = int(round((m.get("ratio") or 0) * 100))
            name = m.get("project_name") or "un proyecto"
            steps.append({
                "text": f"{name} va al {ratio} por ciento de su milestone activo.",
                "focus": f"proj:{m.get('project_id')}",
            })
        segments.append({"kind": "projects", "refs": refs, "steps": steps})

    # --- Tareas: deadlines de la semana + bloqueos ---
    deadlines = ws.get("upcoming_deadlines") or []
    blocked = ws.get("blocked") or []
    if on("tasks") and (deadlines or blocked):
        refs = {
            "deadlines": [
                {
                    "task_id": t.get("task_id"),
                    "title": t.get("title"),
                    "due_date": t.get("due_date"),
                    "project_id": t.get("project_id"),
                }
                for t in deadlines[:6]
            ],
            "blocked": [
                {"task_id": t.get("task_id"), "title": t.get("title")} for t in blocked[:4]
            ],
        }
        steps = []
        if deadlines:
            n = len(deadlines)
            top = ", ".join((t.get("title") or "")[:60] for t in deadlines[:2] if t.get("title"))
            extra = f": {top}" if top else ""
            steps.append({
                "text": f"{n} {_plural(n, 'tarea con fecha límite', 'tareas con fecha límite')} esta semana{extra}.",
                "focus": "deadlines",
            })
        if blocked:
            n = len(blocked)
            steps.append({
                "text": f"{n} {_plural(n, 'tarea sigue bloqueada', 'tareas siguen bloqueadas')}.",
                "focus": "blocked",
            })
        segments.append({"kind": "tasks", "refs": refs, "steps": steps})

    # --- Noticias: de la CACHE del job de preparación (nunca red aquí) ---
    if on("news") and news_cache and not news_cache.get("unavailable"):
        topics = [t for t in (news_cache.get("topics") or []) if t.get("items")]
        if topics:
            spoken_per_topic = int(((config or {}).get("news") or {}).get("spoken_per_topic", 2))
            refs = {"topics": topics, "prepared_at": news_cache.get("prepared_at")}
            steps = [{"text": "Y en las noticias de hoy.", "focus": None}]
            for topic in topics:
                for it in topic["items"][:spoken_per_topic]:
                    summary_line = (it.get("summary") or "").strip()
                    text = f"{topic['label']}: {it.get('title')}."
                    if summary_line:
                        text += f" {summary_line}"
                        if not text.endswith((".", "!", "?", "…")):
                            text += "."
                    steps.append({"text": text, "focus": it.get("id")})
            segments.append({"kind": "news", "refs": refs, "steps": steps})

    # --- Ayer ---
    if on("yesterday") and summary:
        segments.append({
            "kind": "yesterday",
            "refs": {},
            "steps": [{"text": f"De ayer: {summary}", "focus": None}],
        })

    # Día completamente vacío: que el saludo lo diga en vez de callar.
    if len(segments) == 1:
        segments[0]["steps"].append(
            {"text": "Hoy no hay nada urgente ni agendado.", "focus": None}
        )

    return segments


# ---------------------------------------------------------------------------
# [PU4b] Job de PREPARACIÓN por horario (lo arma briefing_config.arm_prep_jobs
# a slot − prep_minutes). Deja TODO cacheado: noticias frescas + locución LLM.
# A la hora del briefing, el GET es lectura pura. Best-effort en cada pieza:
# que fallen las noticias no roba la locución, y viceversa.
# ---------------------------------------------------------------------------
async def prepare_for_slot(slot: str) -> dict[str, Any]:
    import asyncio
    from datetime import datetime

    from app.memory import briefing_config, news, summarizer

    result: dict[str, Any] = {"slot": slot, "news": "skipped", "spoken": "failed"}
    cfg = briefing_config.get_config()
    target = datetime.now().date()  # reloj LOCAL, como el resto de jobs del MOS

    if cfg["sections"].get("news", True):
        try:
            cache = await news.prepare(cfg, slot=slot)
            result["news"] = "unavailable" if cache.get("unavailable") else "ok"
        except Exception as e:
            print(f"[briefing] preparación de noticias falló (no crítico): {e}")
            result["news"] = "failed"

    try:
        data = await asyncio.to_thread(summarizer.gather_day_data, target)
        cached_summary = await summarizer.get_cached_summary(target)
        summary = cached_summary or summarizer.build_deterministic_summary(data)
        spoken = await build_spoken_text(data, summary)
        await store_spoken(target, spoken)
        result["spoken"] = "ok"
    except Exception as e:
        print(f"[briefing] preparación de la locución falló (no crítico): {e}")

    result["status"] = "ok" if ("ok" in (result["news"], result["spoken"])) else "failed"
    return result
