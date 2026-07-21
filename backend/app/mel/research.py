# app/mel/research.py — Catálogo auto-investigado por modelo conectado (E1b, doc 19 §5.4)
#
# Cuando el usuario conecta/cambia un modelo, un job investiga sus capacidades
# reales — usando el conocimiento entrenado del mejor modelo disponible (Δ7, doc
# 22 §1: Aithera NO tiene navegación web real todavía; nada de esto la finge) — y
# guarda un informe consultable con confianza declarada. El informe DESPLAZA el
# catálogo curado (catalog.py), nunca lo sustituye: `effective_score()` es lo que
# el compilador de políticas (policies.py) usa en vez de `catalog.score_of()`
# directo, y es un desplazamiento SIMPLE de un solo informe — sin prior
# bayesiano, sin historial, sin decaimiento (eso es el Learning Engine real, MEL
# v2, doc 19 §9.2).
#
# BEST-EFFORT SIEMPRE: un fallo aquí (JSON inválido, LLM caído) nunca debe
# afectar a que el usuario pueda configurar un proveedor — se loguea y se sigue.
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings
from app.core.logging_config import get_system_logger
from app.mel.contracts import Capability, Constraints, ExecutionRequest, ModelRef

logger = get_system_logger("mel.research")

# Las 8 capacidades activas de la taxonomía (doc 19 §3) — las 3 reservadas
# (RESEARCH/VISION/AGENTIC) no tienen call-sites reales todavía; preguntarle a
# un modelo que se autoevalúe en ellas sería especulativo (anti-sobreingeniería).
_RESEARCHABLE: tuple[Capability, ...] = tuple(
    c for c in Capability if c not in (Capability.RESEARCH, Capability.VISION, Capability.AGENTIC)
)

_CAP_DESCRIPTIONS = {
    Capability.CHAT: "conversación general con memoria, tono natural",
    Capability.CLASSIFY: "etiquetar/categorizar texto corto, rápido",
    Capability.EXTRACT: "extraer datos estructurados (JSON, fechas) de texto libre, precisión literal",
    Capability.SUMMARIZE: "condensar texto sin inventar",
    Capability.DRAFT: "redactar texto en nombre de otra persona, tono natural",
    Capability.REASON: "razonamiento profundo multi-paso, análisis complejo",
    Capability.CODE: "generar/editar código",
    Capability.ANALYZE: "análisis de datos y patrones",
}

_SYSTEM_PROMPT = """Eres un evaluador técnico de modelos de IA. Vas a evaluar las
capacidades REALES de un modelo concreto por el que te preguntan — NO tus propias
capacidades salvo que coincida.

Para CADA capacidad de la lista, da: un score 0-100, una justificación de UNA
línea, y tu nivel de confianza ("alto"|"medio"|"bajo").

IMPORTANTE — honestidad ante todo: si el modelo es una versión reciente o poco
conocida que no conoces bien, dilo con confidence="bajo" en vez de inventar un
score preciso. No inventes benchmarks que no recuerdas con certeza. Es preferible
un score aproximado con confianza baja declarada que uno inventado con confianza
falsa.

Devuelve SOLO un objeto JSON (sin texto adicional, sin markdown) con esta forma
exacta:
{"capabilities": {"<capacidad>": {"score": <0-100>, "rationale": "<una línea>", "confidence": "alto"|"medio"|"bajo"}, ...}}
Una entrada por cada capacidad de la lista."""


def _extract_json(text: str) -> Optional[dict]:
    """Extrae el primer objeto JSON de una respuesta del LLM (mismo patrón que
    `app.tie.intents._extract_json` — copia local a propósito: el MEL no importa
    el TIE, doc 19 §13.1)."""
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else None
    if candidate is None:
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


def _is_stale(provider: str, model: str) -> bool:
    """True si NO hay informe reciente (< MEL_RESEARCH_REFRESH_DAYS) para este
    (provider, model) — o sea, hace falta investigar."""
    from app.db.database import SessionLocal
    from app.mel.models import MelCapabilityReport

    cutoff = datetime.utcnow() - timedelta(days=settings.MEL_RESEARCH_REFRESH_DAYS)
    db = SessionLocal()
    try:
        recent = (
            db.query(MelCapabilityReport)
            .filter(MelCapabilityReport.provider == provider, MelCapabilityReport.model == model)
            .filter(MelCapabilityReport.created_at >= cutoff)
            .first()
        )
        return recent is None
    except Exception as e:
        logger.error(f"[research] _is_stale falló, se investiga por si acaso: {type(e).__name__}: {e}")
        return True
    finally:
        db.close()


async def investigate(provider: str, model: str, *, force: bool = False) -> bool:
    """Investiga UN (provider, model) y persiste un informe por capacidad
    (best-effort: nunca lanza). `force=True` lo usa el job de refresco (ignora
    la comprobación de frescura — ya sabe que toca re-investigar). Devuelve True
    si se generó/actualizó un informe."""
    if not force and not _is_stale(provider, model):
        return False

    from app.mel import registry
    from app.mel.executor import complete as mel_complete

    caps_txt = "\n".join(
        f"- {c.value}: {_CAP_DESCRIPTIONS[c]}" for c in _RESEARCHABLE
    )
    prompt = f"Modelo a evaluar: {provider}/{model}\n\nCapacidades a evaluar:\n{caps_txt}"

    # Evita que el modelo se autoevalúe si hay alternativa (doc 19 §5.4.2).
    own_key = ModelRef(provider=provider, model=model).key
    available = registry.list_available()
    exclude = (own_key,) if len(available) > 1 else ()

    req = ExecutionRequest(
        capability=Capability.RESEARCH,
        prompt=prompt,
        system_prompt=_SYSTEM_PROMPT,
        constraints=Constraints(timeout_s=30.0),
        exclude=exclude,
        # [Opt latencia 2026-07-21] Investigar las capacidades de un modelo es una
        # tarea de FONDO — no debe pelearse con las peticiones EN VIVO del usuario
        # por el proveedor de calidad (que las estaba serializando y las hacía
        # tardar). Con "economy" (local-primero) el auto-catálogo usa un modelo
        # barato/local para investigar, dejando el proveedor caro libre para el
        # chat/las misiones del usuario.
        policy_override="economy",
    )
    res = await mel_complete(req)
    if not res.ok:
        logger.info(f"[research] investigación de {provider}/{model} falló (no crítico): {res.error}")
        return False

    data = _extract_json(res.text)
    if not data or not isinstance(data.get("capabilities"), dict):
        logger.info(f"[research] respuesta sin JSON parseable para {provider}/{model}")
        return False

    researched_by = res.served_by.provider + ":" + res.served_by.model if res.served_by else "?"
    _persist(provider, model, data["capabilities"], researched_by)
    return True


def _persist(provider: str, model: str, capabilities: dict, researched_by: str) -> None:
    """Valida y guarda una fila por capacidad reconocida. Entradas inválidas se
    descartan individualmente (nunca tumba el resto del informe)."""
    from app.db.database import SessionLocal
    from app.mel.models import MelCapabilityReport

    valid_names = {c.value for c in _RESEARCHABLE}
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        n = 0
        for cap_name, entry in capabilities.items():
            if cap_name not in valid_names or not isinstance(entry, dict):
                continue
            try:
                score = max(0, min(100, int(entry.get("score", 50))))
            except (TypeError, ValueError):
                continue
            confidence = str(entry.get("confidence", "bajo")).strip().lower()
            if confidence not in ("alto", "medio", "bajo"):
                confidence = "bajo"
            rationale = str(entry.get("rationale", ""))[:500]
            db.add(MelCapabilityReport(
                provider=provider, model=model, capability=cap_name,
                score=score, rationale=rationale, confidence=confidence,
                researched_by_model=researched_by[:160], created_at=now,
            ))
            n += 1
        db.commit()
        logger.info(f"[research] informe guardado: {provider}/{model} ({n} capacidad(es))")
    except Exception as e:
        logger.error(f"[research] no se pudo persistir el informe (no crítico): {type(e).__name__}: {e}")
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Consulta — el compilador de políticas (E1) desplaza el catálogo con esto
# ---------------------------------------------------------------------------
def effective_score(ref: ModelRef, capability: Capability) -> int:
    """Score para el compilador (policies.py): el catálogo curado (catalog.py),
    desplazado por el informe auto-investigado más reciente de este modelo, si lo
    hay y su confianza no es "bajo" (doc 19 §5.4.3 — un informe de confianza baja
    NO mueve nada por sí solo). Desplazamiento simple 50/50, sin historial."""
    from app.mel.catalog import score_of as catalog_score_of

    base = catalog_score_of(ref, capability)
    report = _latest_report(ref.provider, ref.model, capability)
    if report is None or report["confidence"] == "bajo":
        return base
    return round(base * 0.5 + report["score"] * 0.5)


def _latest_report(provider: str, model: str, capability: Capability) -> Optional[dict]:
    from app.db.database import SessionLocal
    from app.mel.models import MelCapabilityReport

    db = SessionLocal()
    try:
        row = (
            db.query(MelCapabilityReport)
            .filter(MelCapabilityReport.provider == provider, MelCapabilityReport.model == model,
                    MelCapabilityReport.capability == capability.value)
            .order_by(MelCapabilityReport.created_at.desc())
            .first()
        )
        if row is None:
            return None
        return {"score": row.score, "confidence": row.confidence}
    except Exception as e:
        logger.error(f"[research] _latest_report falló (uso solo catálogo): {type(e).__name__}: {e}")
        return None
    finally:
        db.close()


def report_summary() -> list[dict]:
    """El informe legible por (provider, model) — GET /api/mel/capability-report
    (doc 19 §5.4.3, "documento interno" consultable). Agrupa las capacidades de
    cada modelo en una lista, más reciente primero por capacidad."""
    from app.db.database import SessionLocal
    from app.mel.models import MelCapabilityReport

    db = SessionLocal()
    try:
        rows = db.query(MelCapabilityReport).order_by(MelCapabilityReport.created_at.desc()).all()
    except Exception:
        return []
    finally:
        db.close()

    by_model: dict[tuple, dict] = {}
    for r in rows:
        key = (r.provider, r.model)
        entry = by_model.setdefault(key, {
            "provider": r.provider, "model": r.model, "capabilities": {},
        })
        if r.capability not in entry["capabilities"]:  # más reciente ya viene primero
            entry["capabilities"][r.capability] = {
                "score": r.score, "rationale": r.rationale, "confidence": r.confidence,
            }
    return list(by_model.values())


# ---------------------------------------------------------------------------
# Suscripción al evento + job de refresco periódico
# ---------------------------------------------------------------------------
async def _on_model_configured(event) -> None:
    payload = event.payload or {}
    provider, model = payload.get("provider"), payload.get("model")
    if not provider or not model:
        return
    try:
        await investigate(provider, model)
    except Exception as e:
        logger.error(f"[research] fallo investigando {provider}/{model} (no crítico): {type(e).__name__}: {e}")


def register() -> None:
    """Suscribe el handler de `provider.model_configured`. Idempotente. Lo llama
    `mel.register_handlers()` desde el lifespan."""
    from app.core.events import subscribe, unsubscribe

    unsubscribe("provider.model_configured", _on_model_configured)
    subscribe("provider.model_configured", _on_model_configured)


async def refresh_all() -> int:
    """Re-investiga TODOS los modelos configurados actualmente (job periódico,
    cada MEL_RESEARCH_REFRESH_DAYS) — los proveedores cambian de versión sin
    avisar, así que un informe viejo puede describir un modelo que ya no es el
    mismo. `force=True`: el propio disparo del job ya es la señal de que toca.
    Best-effort: un fallo en un modelo no detiene a los demás."""
    from app.mel import registry

    refreshed = 0
    for ref in registry.list_available():
        try:
            if await investigate(ref.provider, ref.model, force=True):
                refreshed += 1
        except Exception as e:
            logger.error(f"[research] refresh_all: fallo en {ref.key} (no crítico): {type(e).__name__}: {e}")
    if refreshed:
        logger.info(f"[research] refresh_all: {refreshed} modelo(s) re-investigado(s)")
    return refreshed
