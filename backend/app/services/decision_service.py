# app/services/decision_service.py — Decision Memory API (V0.85, MOS M1)
#
# La tabla `decisions` es la FUENTE DE VERDAD; mem_decision es su espejo
# semantico (para busqueda por descripcion). store_decision escribe en ambos:
# primero el SQL (autoritativo, siempre), luego el espejo (best-effort — si
# ChromaDB esta caido, la decision NO se pierde).
#
# Nace en V0.85 aunque su uso real empieza en V0.9 (aprobaciones) y V1.0
# (planes del Orchestrator, enlazados por mission_id [Δ]). Implementa la
# Decision API de 08 RFC-002 (store_decision / search_decisions / link_outcome).
#
# Acceso a memoria SOLO por la API publica `app.memory` (doc 16 §4 — nunca por
# internals del MOS).
from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from app.db.database import SessionLocal
from app.db.models import Decision
from app.memory import MemoryType, memory_router


async def _mirror_to_memory(decision: Decision) -> None:
    """Espejo semantico en mem_decision (best-effort, idempotente por id)."""
    try:
        body = (decision.body or "").strip()
        content = f"{decision.title}\n\n{body}".strip() if body else decision.title
        await memory_router.store(
            content=content,
            memory_type=MemoryType.DECISION,
            source="decision",
            metadata={
                "decision_id": decision.id,
                "project": decision.project,
                "impact": decision.impact,
                "status": decision.status,
                "mission_id": decision.mission_id,
                "reason": decision.reason,
            },
            dedup_key=decision.id,
        )
    except Exception as e:  # el espejo nunca rompe la escritura autoritativa
        print(f"[decision_service] espejo mem_decision fallo (no critico): {e}")


async def store_decision(
    *,
    title: str,
    body: str = "",
    reason: str = "",
    alternatives: Optional[list[Any]] = None,
    project: Optional[str] = None,
    impact: str = "med",
    mission_id: Optional[str] = None,
    db=None,
) -> Decision:
    """Registra una decision. SQL primero (fuente de verdad), luego el espejo.
    Devuelve la Decision (desacoplada de la sesion si esta la creamos aqui)."""
    own = db is None
    session = db or SessionLocal()
    try:
        decision = Decision(
            id=str(uuid.uuid4()),
            title=title,
            body=body or None,
            reason=reason or None,
            alternatives=json.dumps(alternatives, ensure_ascii=False) if alternatives else None,
            project=project,
            impact=impact,
            status="active",
            mission_id=mission_id,
        )
        session.add(decision)
        session.commit()
        session.refresh(decision)
        if own:
            session.expunge(decision)  # detached con atributos cargados
    finally:
        if own:
            session.close()

    await _mirror_to_memory(decision)
    return decision


async def link_outcome(decision_id: str, outcome: str, db=None) -> Optional[Decision]:
    """Enlaza el resultado real de una decision a posteriori (08 RFC-002).
    Actualiza el SQL y re-espeja. None si la decision no existe."""
    own = db is None
    session = db or SessionLocal()
    try:
        decision = session.get(Decision, decision_id)
        if decision is None:
            return None
        decision.outcome = outcome
        session.commit()
        session.refresh(decision)
        if own:
            session.expunge(decision)
    finally:
        if own:
            session.close()

    await _mirror_to_memory(decision)
    return decision


async def search_decisions(query: str, top_k: int = 5) -> list[dict]:
    """Busqueda semantica sobre el espejo mem_decision. Devuelve dicts ligeros
    con la metadata de cada decision (decision_id, project, impact, status...)."""
    items = await memory_router.search(
        query, memory_types=[MemoryType.DECISION], top_k=top_k
    )
    return [
        {
            "decision_id": it.metadata.get("decision_id"),
            "content": it.content,
            "project": it.metadata.get("project"),
            "impact": it.metadata.get("impact"),
            "status": it.metadata.get("status"),
            "mission_id": it.metadata.get("mission_id"),
            "score": it.score,
        }
        for it in items
    ]
