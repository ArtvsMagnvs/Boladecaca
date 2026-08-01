# app/memory/briefing_config.py — configuración del Briefing 2.0 (PU4b, doc 35)
#
# QUÉ GOBIERNA: qué secciones menciona el briefing (proyectos/tareas/email/
# calendario/noticias/ayer), a qué horas del día se lanza SOLO (N horarios,
# no uno), cuánto antes se PREPARA cada uno (noticias + locución cacheadas
# para que a la hora del briefing todo sea lectura instantánea), y la
# selección de noticias: temas con su consulta, fuentes bloqueadas/preferidas
# y un prompt libre del usuario que guía la curación (ver news.py).
#
# DÓNDE VIVE: tabla `Config` (key-value, columna Text) — mismo patrón que
# telegram.py / permissions.py: sin migración nueva, sobrevive a reinicios,
# editable por endpoint. El JSON guardado se FUSIONA sobre DEFAULT_CONFIG al
# leer, así añadir un campo nuevo en una versión futura no rompe una config
# vieja (evolución aditiva, mismo criterio que los contratos del TIE).
#
# QUIÉN LA USA: `GET/PUT /api/memory/briefing/config` (endpoints/memory.py),
# `briefing.build_spoken_segments()` (qué secciones entran), `news.prepare()`
# (temas/fuentes/prompt), y `arm_prep_jobs()` — llamado por el lifespan de
# main.py al arrancar y por el PUT al guardar (re-arma EN CALIENTE, mismo
# espíritu que el PATCH de reglas del AE).
from __future__ import annotations

import copy
import json
import re
from typing import Any, Optional

from app.core.logging_config import get_system_logger

logger = get_system_logger("briefing_config")

_CONFIG_KEY = "briefing.config"
_PREP_JOB_PREFIX = "briefing_prep_"

# ---------------------------------------------------------------------------
# Defaults — los 5 temas y el criterio de curación los fijó el usuario
# (2026-08-01): geopolítica global y española, IA general, IA/Claude e
# IA/herramientas-agentes-MCP-repos; "no quiero noticias basura de los
# grandes medios corruptos, quiero información contrastada, de medios
# honestos". Todo editable desde Ajustes → Briefing.
# ---------------------------------------------------------------------------
DEFAULT_CONFIG: dict[str, Any] = {
    "sections": {
        "email": True,      # urgentes pendientes + los que piden acción
        "calendar": True,   # agenda de las próximas 24h
        "projects": True,   # milestone activo + progreso
        "tasks": True,      # deadlines de la semana + bloqueos
        "news": True,       # titulares curados (ver `news`)
        "yesterday": True,  # resumen del día anterior
    },
    # Horas LOCALES "HH:MM" a las que el briefing se lanza SOLO (el frontend
    # observa esta lista; puede haber varias al día: 08:00, 14:00, 21:00…).
    "schedules": ["08:00"],
    # Cuántos minutos ANTES de cada horario corre el job de preparación
    # (noticias + locución → cache). A la hora del briefing, todo es lectura.
    "prep_minutes_before": 30,
    "news": {
        "topics": [
            {
                "id": "geo_global",
                "label": "Geopolítica global",
                "query": "geopolitica ultima hora hoy conflicto crisis internacional",
                "vertical": "news",
                "freshness": "d",
            },
            {
                "id": "geo_es",
                "label": "Geopolítica española",
                "query": "España ultima hora hoy conflicto crisis frontera exterior",
                "vertical": "news",
                "freshness": "d",
            },
            {
                "id": "ia_general",
                "label": "Inteligencia artificial",
                "query": "inteligencia artificial noticia hoy avance modelo lanzamiento",
                "vertical": "news",
                "freshness": "d",
            },
            {
                "id": "ia_claude",
                "label": "Claude / Anthropic",
                "query": "Anthropic Claude update release new feature announcement",
                "vertical": "news",
                "freshness": "w",
            },
            {
                "id": "ia_tools",
                "label": "Agentes, MCP y herramientas",
                "query": "AI agents MCP servers open source repository release automation",
                "vertical": "web",  # repos/releases viven mejor en la web que en "news"
                "freshness": "w",
            },
        ],
        # Dominios que NUNCA entran / que se prefieren si aparecen. Aditivos
        # al prompt: el filtro por dominio es determinista, el prompt guía al
        # curador LLM en lo que el dominio no captura.
        # [hotfix 2026-08-01] youtube/vimeo/dailymotion bloqueados por
        # defecto: "noticias son noticias, no vídeos ni documentales" (el
        # usuario, 2026-08-01) — un vídeo puede ser una fuente legítima para
        # OTRAS cosas, pero nunca para el briefing de noticias.
        "blocked_sources": ["youtube.com", "vimeo.com", "dailymotion.com"],
        "preferred_sources": [],
        "prompt": (
            "Selecciona solo noticias con sustancia: análisis contrastado, hechos "
            "verificables, fuentes primarias (blogs oficiales, papers, repositorios, "
            "organismos) y medios independientes o especializados con reputación seria. "
            "Descarta clickbait, sensacionalismo y el ruido de los grandes medios "
            "generalistas. En IA prioriza: novedades de Anthropic/Claude, sistemas de "
            "agentes, MCP y conectores, y repositorios open source populares que puedan "
            "mejorar la producción, automatizar trabajo o aportar capacidades reales a "
            "Aithera. En geopolítica prioriza el análisis serio sobre el titular de "
            "última hora."
        ),
        # Ítems que guarda la cache por tema (los que muestra la pantalla de
        # noticias) y cuántos de ellos se LOCUTAN por tema (titular + resumen
        # — el briefing no lee la noticia entera, decisión del usuario
        # 2026-08-01). [hotfix 2026-08-02] Este "per_topic" es ahora el
        # DEFAULT: cada tema puede fijar su propio "count" (ver validate())
        # que lo pisa — el usuario pidió elegir cuántas noticias quiere de
        # CADA tema, no un número uniforme para los 5.
        "per_topic": 4,
        "spoken_per_topic": 2,
    },
}

_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


# ---------------------------------------------------------------------------
# Persistencia (tabla Config, mismo patrón _get/_set que telegram.py)
# ---------------------------------------------------------------------------
def _read_raw() -> Optional[str]:
    from app.db.database import Config, SessionLocal

    db = SessionLocal()
    try:
        row = db.query(Config).filter(Config.key == _CONFIG_KEY).first()
        return row.value if row and row.value else None
    finally:
        db.close()


def _write_raw(value: str) -> None:
    from app.db.database import Config, SessionLocal

    db = SessionLocal()
    try:
        row = db.query(Config).filter(Config.key == _CONFIG_KEY).first()
        if row:
            row.value = value
        else:
            db.add(Config(key=_CONFIG_KEY, value=value))
        db.commit()
    finally:
        db.close()


def _merge(base: dict, override: dict) -> dict:
    """Fusión recursiva: lo guardado pisa el default campo a campo, pero un
    campo NUEVO del default (versión futura) aparece aunque la config guardada
    sea vieja. Las LISTAS se sustituyen enteras (fusionar listas por índice no
    tiene semántica sensata para horarios/temas)."""
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def get_config() -> dict[str, Any]:
    """Config efectiva (guardada ⊕ defaults). Nunca lanza: una config corrupta
    en BD cae a los defaults con un aviso en el log."""
    raw = None
    try:
        raw = _read_raw()
    except Exception as e:
        logger.error(f"[briefing_config] no se pudo leer la config: {e!r}")
    if not raw:
        return copy.deepcopy(DEFAULT_CONFIG)
    try:
        stored = json.loads(raw)
        if not isinstance(stored, dict):
            raise ValueError("la config guardada no es un objeto")
        return _merge(DEFAULT_CONFIG, stored)
    except Exception as e:
        logger.error(f"[briefing_config] config corrupta, uso defaults: {e!r}")
        return copy.deepcopy(DEFAULT_CONFIG)


def _slug(text: str) -> str:
    import unicodedata

    t = unicodedata.normalize("NFKD", (text or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    return t or "tema"


def validate(cfg: dict[str, Any]) -> dict[str, Any]:
    """Normaliza y valida. Lanza ValueError con un mensaje CONCRETO (el PUT lo
    devuelve como 400) — nunca guarda a medias."""
    merged = _merge(DEFAULT_CONFIG, cfg if isinstance(cfg, dict) else {})

    # Secciones: solo booleanos, solo claves conocidas.
    sections = {}
    for key in DEFAULT_CONFIG["sections"]:
        sections[key] = bool(merged["sections"].get(key, True))
    merged["sections"] = sections

    # Horarios: 1-8, "HH:MM", sin duplicados, ordenados.
    schedules = merged.get("schedules") or []
    if not isinstance(schedules, list) or not schedules:
        raise ValueError("hace falta al menos un horario (formato HH:MM)")
    norm: list[str] = []
    for s in schedules:
        s = str(s).strip()
        m = _TIME_RE.match(s)
        if not m:
            raise ValueError(f"horario inválido: {s!r} (formato HH:MM, 24h)")
        norm.append(f"{int(m.group(1)):02d}:{m.group(2)}")
    norm = sorted(set(norm))
    if len(norm) > 8:
        raise ValueError("máximo 8 horarios al día")
    merged["schedules"] = norm

    prep = merged.get("prep_minutes_before", 30)
    try:
        prep = int(prep)
    except (TypeError, ValueError):
        raise ValueError("prep_minutes_before debe ser un número de minutos")
    if not (5 <= prep <= 120):
        raise ValueError("prep_minutes_before debe estar entre 5 y 120 minutos")
    merged["prep_minutes_before"] = prep

    news = merged["news"]
    topics = news.get("topics") or []
    if not isinstance(topics, list):
        raise ValueError("news.topics debe ser una lista")
    if len(topics) > 10:
        raise ValueError("máximo 10 temas de noticias")
    seen_ids: set[str] = set()
    clean_topics = []
    for t in topics:
        if not isinstance(t, dict):
            raise ValueError("cada tema debe ser un objeto {label, query}")
        label = str(t.get("label") or "").strip()
        query = str(t.get("query") or "").strip()
        if not label or not query:
            raise ValueError("cada tema necesita 'label' y 'query' no vacíos")
        tid = str(t.get("id") or "").strip() or _slug(label)
        base_tid = tid
        n = 2
        while tid in seen_ids:
            tid = f"{base_tid}_{n}"
            n += 1
        seen_ids.add(tid)
        vertical = t.get("vertical") if t.get("vertical") in ("news", "web") else "news"
        # [hotfix 2026-08-01] ventana de actualidad por tema — "d"/"w"/"m"
        # (ver search_tool._BRAVE_FRESHNESS/_SERPAPI_TBS); por defecto "d"
        # porque el fallo real reportado fue justo la falta de esto.
        freshness = t.get("freshness") if t.get("freshness") in ("d", "w", "m") else "d"
        topic: dict[str, Any] = {
            "id": tid, "label": label[:60], "query": query[:200],
            "vertical": vertical, "freshness": freshness,
        }
        # [hotfix 2026-08-02] "count" por tema, OPCIONAL — el usuario pidió
        # poder elegir cuántas noticias quiere de CADA tema por separado
        # (antes solo existía el "per_topic" global de más abajo, uniforme
        # para los 5 temas). Ausente/None => ese tema sigue usando el global
        # como valor por defecto (ver news.py::prepare, "counts").
        raw_count = t.get("count")
        if raw_count not in (None, ""):
            try:
                count = int(raw_count)
            except (TypeError, ValueError):
                raise ValueError(f"el número de noticias del tema {label!r} debe ser un número")
            topic["count"] = max(1, min(8, count))
        clean_topics.append(topic)
    news["topics"] = clean_topics

    for key in ("blocked_sources", "preferred_sources"):
        vals = news.get(key) or []
        if not isinstance(vals, list):
            raise ValueError(f"news.{key} debe ser una lista de dominios")
        news[key] = [
            str(v).strip().lower().removeprefix("www.")[:100]
            for v in vals
            if str(v).strip()
        ][:30]

    news["prompt"] = str(news.get("prompt") or "")[:4000]
    for key, lo, hi in (("per_topic", 1, 8), ("spoken_per_topic", 1, 4)):
        try:
            v = int(news.get(key, DEFAULT_CONFIG["news"][key]))
        except (TypeError, ValueError):
            raise ValueError(f"news.{key} debe ser un número")
        news[key] = max(lo, min(hi, v))
    # Lo locutado nunca excede lo guardado.
    news["spoken_per_topic"] = min(news["spoken_per_topic"], news["per_topic"])

    return merged


def save_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """Valida + persiste + devuelve la config normalizada."""
    clean = validate(cfg)
    _write_raw(json.dumps(clean, ensure_ascii=False))
    return clean


# ---------------------------------------------------------------------------
# Armado de los jobs de preparación (uno por horario, a slot − prep_minutes).
# El scheduler llega POR PARÁMETRO (inyección): app.memory no importa
# app.automation — la dirección de dependencia la fija el composition root
# (main.py), y el PUT del endpoint (capa API, libre de importar ambos).
# ---------------------------------------------------------------------------
def arm_prep_jobs(scheduler) -> list[str]:
    """Quita los jobs `briefing_prep_*` existentes y arma uno por horario
    configurado. Idempotente; devuelve los ids armados. Nunca lanza."""
    armed: list[str] = []
    try:
        cfg = get_config()
        for jid in list(scheduler.jobs()):
            if jid.startswith(_PREP_JOB_PREFIX):
                scheduler.remove_job(jid)
        prep_min = int(cfg["prep_minutes_before"])
        for slot in cfg["schedules"]:
            h, m = (int(x) for x in slot.split(":"))
            total = (h * 60 + m - prep_min) % (24 * 60)
            ph, pm = divmod(total, 60)
            jid = f"{_PREP_JOB_PREFIX}{slot.replace(':', '')}"

            def _make(slot_str: str):
                async def _job() -> None:
                    from app.memory import briefing

                    await briefing.prepare_for_slot(slot_str)

                return _job

            scheduler.add_cron_job(_make(slot), hour=ph, minute=pm, id=jid)
            armed.append(jid)
        logger.info(f"[briefing_config] jobs de preparación armados: {armed}")
    except Exception as e:
        logger.error(f"[briefing_config] no se pudieron armar los jobs de preparación: {e!r}")
    return armed
