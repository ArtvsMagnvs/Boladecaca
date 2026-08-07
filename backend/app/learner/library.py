# app/learner/library.py — SkillLibrary: la LSL completa sobre SQL (V1.1 L1)
#
# Implementa `ISkillStore` (contrato congelado de V0.85 M1) con la tabla
# `skills` como FUENTE DE VERDAD y `mem_skill` (ChromaDB) como espejo semántico
# best-effort — el MISMO reparto que decision_service lleva un año haciendo con
# `decisions`/`mem_decision`: SQL primero (autoritativo, siempre), espejo
# después (si ChromaDB está caído, la skill NO se pierde).
#
# Lo que añade sobre el stub de V0.85 (append-only respecto al ABC):
#   · CADA mutación deja un `SkillEvent` con el snapshot PREVIO → undo real.
#   · `validate()` aplica la escalera de verdad (ladder.skill_can_validate):
#     3 ejecuciones OK o el usuario — antes promocionaba sin preguntar nada.
#   · `deprecate()` (doc 09 §1.3): nunca borra, marca superseded_by.
#   · `record_execution()` — el punto ÚNICO por el que el uso real alimenta
#     evidence_count/use_count/error_rate (lo llamará L2).
#   · `undo_last()` / `history()` — el contrato de producto "undo restaura el
#     estado anterior", con su rastro.
#
# BD por `asyncio.to_thread` (SQLAlchemy es sync; mismo patrón que el resto del
# proyecto). El espejo reusa la serialización YA TESTEADA del stub de V0.85
# (_skill_to_meta) en vez de duplicarla — si el contrato LocalSkill evoluciona,
# hay UN serializador que actualizar, no dos (patrón LOG-1).
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Optional

from app.core.logging_config import get_system_logger
from app.db.database import SessionLocal
from app.learner import ladder
from app.learner.models import Skill, SkillEvent
from app.memory import ISkillStore, LocalSkill, MemoryType, SkillStatus, memory_router

logger = get_system_logger("learner.library")

# Campos que forman el snapshot de undo. Es la lista COMPLETA de columnas
# mutables — si el modelo gana una columna y no se añade aquí, el test de
# invariante de test_learner_lsl.py lo caza (snapshot ⊇ columnas mutables).
_SNAPSHOT_FIELDS = (
    "name", "version", "description", "definition", "input_schema",
    "output_schema", "runtime_agnostic", "evidence_count", "last_used",
    "use_count", "status", "quality_score", "error_rate", "projects", "tags",
    "derived_from", "superseded_by", "gsn_id", "gsn_version", "gsn_last_sync",
)


def _snapshot(row: Skill) -> dict:
    out: dict[str, Any] = {}
    for f in _SNAPSHOT_FIELDS:
        v = getattr(row, f)
        out[f] = v.isoformat() if isinstance(v, datetime) else v
    return out


def _restore(row: Skill, snap: dict) -> None:
    for f in _SNAPSHOT_FIELDS:
        if f not in snap:
            continue
        v = snap[f]
        if f in ("last_used", "gsn_last_sync") and isinstance(v, str):
            try:
                v = datetime.fromisoformat(v)
            except ValueError:
                v = None
        setattr(row, f, v)


def _row_to_skill(row: Skill) -> LocalSkill:
    return LocalSkill(
        id=row.id, name=row.name, version=row.version,
        description=row.description or "",
        definition=dict(row.definition or {}),
        input_schema=dict(row.input_schema or {}),
        output_schema=dict(row.output_schema or {}),
        runtime_agnostic=bool(row.runtime_agnostic),
        created_by=row.created_by, created_at=row.created_at,
        evidence_count=int(row.evidence_count or 0),
        last_used=row.last_used, use_count=int(row.use_count or 0),
        status=SkillStatus(row.status),
        quality_score=float(row.quality_score or 0.0),
        error_rate=float(row.error_rate or 0.0),
        projects=list(row.projects or []), tags=list(row.tags or []),
        derived_from=list(row.derived_from or []),
        superseded_by=row.superseded_by,
        gsn_id=row.gsn_id, gsn_version=row.gsn_version,
        gsn_last_sync=row.gsn_last_sync,
    )


def _skill_to_row_kwargs(skill: LocalSkill) -> dict:
    return dict(
        id=skill.id, name=skill.name, version=skill.version,
        description=skill.description, definition=skill.definition,
        input_schema=skill.input_schema, output_schema=skill.output_schema,
        runtime_agnostic=skill.runtime_agnostic, created_by=skill.created_by,
        created_at=skill.created_at, evidence_count=skill.evidence_count,
        last_used=skill.last_used, use_count=skill.use_count,
        status=skill.status.value, quality_score=skill.quality_score,
        error_rate=skill.error_rate, projects=skill.projects, tags=skill.tags,
        derived_from=skill.derived_from, superseded_by=skill.superseded_by,
        gsn_id=skill.gsn_id, gsn_version=skill.gsn_version,
        gsn_last_sync=skill.gsn_last_sync,
    )


class SkillLibrary(ISkillStore):
    """La LSL. Fuente de verdad SQL + espejo semántico + historia con undo."""

    # ------------------------------------------------------------------
    # Espejo semántico (best-effort, nunca rompe la escritura autoritativa)
    # ------------------------------------------------------------------
    async def _mirror(self, skill: LocalSkill) -> None:
        try:
            # Por la API PÚBLICA del MOS (doc 16 — `app.memory.stores` es
            # interno): el stub de V0.85 serializa con su _skill_to_meta ya
            # testeado y su store() upserta por dedup_key=skill.id — un solo
            # serializador (LOG-1) y cero imports a internos ajenos.
            from app.memory import skill_store

            await skill_store.create(skill)
        except Exception as e:
            logger.info(f"[lsl] espejo mem_skill falló (no crítico): {e!r}")

    def _log_event(self, session, skill_id: str, event: str, actor: str,
                   payload: Optional[dict] = None) -> None:
        session.add(SkillEvent(skill_id=skill_id, event=event,
                               actor=actor, payload=payload or {}))

    # ------------------------------------------------------------------
    # ISkillStore (contrato congelado)
    # ------------------------------------------------------------------
    async def create(self, skill: LocalSkill, *, actor: str = "learner") -> str:
        def _work() -> str:
            with SessionLocal() as s:
                if s.get(Skill, skill.id) is not None:
                    return skill.id            # idempotente por id (contrato)
                s.add(Skill(**_skill_to_row_kwargs(skill)))
                self._log_event(s, skill.id, "created", actor,
                                {"name": skill.name, "status": skill.status.value,
                                 "created_by": skill.created_by})
                s.commit()
                return skill.id

        sid = await asyncio.to_thread(_work)
        await self._mirror(skill)
        return sid

    async def get(self, skill_id: str) -> Optional[LocalSkill]:
        def _work():
            with SessionLocal() as s:
                row = s.get(Skill, skill_id)
                return _row_to_skill(row) if row else None
        return await asyncio.to_thread(_work)

    async def list(self, status: Optional[SkillStatus] = None,
                   tags: Optional[list[str]] = None) -> list[LocalSkill]:
        def _work():
            with SessionLocal() as s:
                q = s.query(Skill)
                if status is not None:
                    q = q.filter(Skill.status == status.value)
                rows = q.order_by(Skill.created_at.desc()).all()
                skills = [_row_to_skill(r) for r in rows]
                if tags:
                    wanted = set(tags)
                    skills = [x for x in skills if wanted & set(x.tags)]
                return skills
        return await asyncio.to_thread(_work)

    def list_compact(self, limit: int = 40) -> list[dict]:
        """[LC2] El catálogo en tres campos, SÍNCRONO y barato — para meterlo en
        un prompt: qué skills existen ya, con qué id y para qué sirven.

        Existe aparte de `list()` a propósito: `list()` reconstruye
        `LocalSkill` completos (definición, métricas, linaje) y es async; lo
        que un prompt necesita es una lista corta que quepa. Se excluyen las
        deprecadas — ofrecerle al juez skills retiradas solo puede llevarle a
        proponer mejoras sobre algo que ya nadie usa."""
        with SessionLocal() as s:
            filas = (s.query(Skill)
                     .filter(Skill.status != SkillStatus.DEPRECATED.value)
                     .order_by(Skill.created_at.desc()).limit(limit).all())
            return [{"id": r.id, "name": r.name,
                     "description": (r.description or "")} for r in filas]

    async def search(self, query: str, top_k: int = 5) -> list[LocalSkill]:
        """Semántica sobre el espejo; las filas AUTORITATIVAS se releen de SQL
        (el espejo puede ir por detrás en status/metricas). Sin ChromaDB,
        degrada a LIKE sobre nombre/descripción — nunca a cero capacidad."""
        ids: list[str] = []
        try:
            hits = await memory_router.search(query, memory_types=[MemoryType.SKILL],
                                              top_k=top_k)
            ids = [h.metadata.get("skill_id") for h in hits
                   if h.metadata.get("skill_id")]
        except Exception as e:
            logger.info(f"[lsl] búsqueda semántica no disponible ({e!r}); degrado a SQL")

        def _work():
            with SessionLocal() as s:
                if ids:
                    rows = s.query(Skill).filter(Skill.id.in_(ids)).all()
                    por_id = {r.id: r for r in rows}
                    return [_row_to_skill(por_id[i]) for i in ids if i in por_id]
                like = f"%{query}%"
                rows = (s.query(Skill)
                        .filter(Skill.name.ilike(like) | Skill.description.ilike(like))
                        .limit(top_k).all())
                return [_row_to_skill(r) for r in rows]
        return await asyncio.to_thread(_work)

    async def improve(self, skill_id: str, changes: dict,
                      *, actor: str = "learner") -> Optional[LocalSkill]:
        """Cambios de contenido/calidad. El STATUS no se toca por aquí — las
        transiciones de estado van por validate/deprecate/undo, que son las que
        aplican la escalera. Colar un cambio de estado por improve() sería
        saltarse la cuarentena por la puerta de atrás."""
        cambios = {k: v for k, v in (changes or {}).items()
                   if k in _SNAPSHOT_FIELDS and k != "status"}
        if not cambios:
            return await self.get(skill_id)

        def _work():
            with SessionLocal() as s:
                row = s.get(Skill, skill_id)
                if row is None:
                    return None
                prior = _snapshot(row)
                for k, v in cambios.items():
                    setattr(row, k, v)
                self._log_event(s, skill_id, "improved", actor,
                                {"prior": prior, "changes": sorted(cambios)})
                s.commit()
                return _row_to_skill(row)
        skill = await asyncio.to_thread(_work)
        if skill:
            await self._mirror(skill)
        return skill

    async def validate(self, skill_id: str,
                       *, actor: str = "learner") -> Optional[LocalSkill]:
        """DRAFT → VALIDATED **aplicando la escalera** (riesgo medio, doc 15
        §3.2): 3 ejecuciones OK acumuladas en evidence_count, o actor='user'.
        Sin base, lanza ValueError con el motivo — el contrato de producto
        'ninguna propuesta se aplica sin evidencia o aprobación' vive aquí."""
        def _work():
            with SessionLocal() as s:
                row = s.get(Skill, skill_id)
                if row is None:
                    return None
                if not ladder.skill_can_transition(row.status, "validated"):
                    raise ValueError(
                        f"transición ilegal: {row.status} → validated "
                        f"(la escalera se sube peldaño a peldaño)")
                ok, motivo = ladder.skill_can_validate(int(row.evidence_count or 0), actor)
                if not ok:
                    raise ValueError(f"sin base para validar: {motivo}")
                prior = _snapshot(row)
                row.status = SkillStatus.VALIDATED.value
                self._log_event(s, skill_id, "validated", actor,
                                {"prior": prior, "reason": motivo})
                s.commit()
                return _row_to_skill(row)
        skill = await asyncio.to_thread(_work)
        if skill:
            await self._mirror(skill)
        return skill

    async def publish(self, skill_id: str) -> None:
        """No-op hasta la GSN (V2.0+). Firma viva desde V0.85."""
        return None

    async def execute(self, skill_id: str, inputs: dict) -> dict:
        raise NotImplementedError(
            "SkillLibrary.execute llega con el cableado al AgentRuntime "
            "(fuera del alcance de L1 — doc 27 §5, terreno verificado). "
            "Una skill jamás se ejecuta 'a medias'.")

    # ------------------------------------------------------------------
    # LSL completa (append-only sobre el ABC)
    # ------------------------------------------------------------------
    async def consolidate(self, skill_id: str,
                          *, actor: str = "user") -> Optional[LocalSkill]:
        """VALIDATED → LOCAL (el reposo normal; 'consolidated' en la escalera).
        El evento `consolidated` es extensión honesta de la lista de doc 15
        §6.2 (como `reverted`): etiquetarlo `improved` habría mentido."""
        return await self._transition(skill_id, SkillStatus.LOCAL, "consolidated",
                                      actor, reason="consolidada a LOCAL")

    async def deprecate(self, skill_id: str, *, superseded_by: Optional[str] = None,
                        actor: str = "learner") -> Optional[LocalSkill]:
        """Retira sin borrar (doc 09 §1.2: 'nunca se borra: se archiva con
        historia'). `superseded_by` enlaza el reemplazo si existe — el linaje
        completo se reconstruye siguiendo derived_from/superseded_by."""
        def _work():
            with SessionLocal() as s:
                row = s.get(Skill, skill_id)
                if row is None:
                    return None
                if not ladder.skill_can_transition(row.status, "deprecated"):
                    raise ValueError(f"transición ilegal: {row.status} → deprecated")
                prior = _snapshot(row)
                row.status = SkillStatus.DEPRECATED.value
                row.superseded_by = superseded_by
                self._log_event(s, skill_id, "deprecated", actor,
                                {"prior": prior, "superseded_by": superseded_by})
                s.commit()
                return _row_to_skill(row)
        skill = await asyncio.to_thread(_work)
        if skill:
            await self._mirror(skill)
        return skill

    async def record_execution(self, skill_id: str, ok: bool,
                               *, context_key: str = "",
                               actor: str = "runtime") -> Optional[LocalSkill]:
        """EL punto único por el que el uso real alimenta las métricas.
        error_rate se recalcula del total acumulado — nunca lo escribe un LLM."""
        def _work():
            with SessionLocal() as s:
                row = s.get(Skill, skill_id)
                if row is None:
                    return None
                row.use_count = int(row.use_count or 0) + 1
                row.last_used = datetime.utcnow()
                if ok:
                    row.evidence_count = int(row.evidence_count or 0) + 1
                fallos_previos = round(float(row.error_rate or 0.0) * (row.use_count - 1))
                fallos = fallos_previos + (0 if ok else 1)
                row.error_rate = fallos / row.use_count
                self._log_event(s, skill_id, "executed_ok" if ok else "executed_fail",
                                actor, {"context_key": context_key})
                s.commit()
                return _row_to_skill(row)
        return await asyncio.to_thread(_work)

    async def history(self, skill_id: str) -> list[dict]:
        """El 'git log' de la skill, más reciente primero."""
        def _work():
            with SessionLocal() as s:
                rows = (s.query(SkillEvent).filter(SkillEvent.skill_id == skill_id)
                        .order_by(SkillEvent.id.desc()).all())
                return [{"id": r.id, "event": r.event, "actor": r.actor,
                         "payload": dict(r.payload or {}),
                         "created_at": r.created_at.isoformat()} for r in rows]
        return await asyncio.to_thread(_work)

    async def undo_last(self, skill_id: str,
                        *, actor: str = "user") -> Optional[LocalSkill]:
        """Deshace la última mutación CON snapshot (validated/improved/
        deprecated), restaurando el estado previo EXACTO. El undo también es
        historia: deja su propio evento `reverted` apuntando al que deshizo —
        nunca reescribe el pasado, añade encima."""
        def _work():
            with SessionLocal() as s:
                row = s.get(Skill, skill_id)
                if row is None:
                    return None
                ultimo = (s.query(SkillEvent)
                          .filter(SkillEvent.skill_id == skill_id,
                                  SkillEvent.event.in_(("validated", "improved",
                                                        "deprecated", "consolidated")))
                          .order_by(SkillEvent.id.desc()).first())
                if ultimo is None or "prior" not in (ultimo.payload or {}):
                    raise ValueError("no hay ninguna mutación reversible en la historia")
                _restore(row, ultimo.payload["prior"])
                self._log_event(s, skill_id, "reverted", actor,
                                {"undid_event_id": ultimo.id, "undid_event": ultimo.event})
                s.commit()
                return _row_to_skill(row)
        skill = await asyncio.to_thread(_work)
        if skill:
            await self._mirror(skill)
        return skill

    # interno compartido por consolidate (transición simple con snapshot)
    async def _transition(self, skill_id: str, to: SkillStatus, event: str,
                          actor: str, *, reason: str) -> Optional[LocalSkill]:
        def _work():
            with SessionLocal() as s:
                row = s.get(Skill, skill_id)
                if row is None:
                    return None
                if not ladder.skill_can_transition(row.status, to.value):
                    raise ValueError(f"transición ilegal: {row.status} → {to.value}")
                prior = _snapshot(row)
                row.status = to.value
                self._log_event(s, skill_id, event, actor,
                                {"prior": prior, "reason": reason})
                s.commit()
                return _row_to_skill(row)
        skill = await asyncio.to_thread(_work)
        if skill:
            await self._mirror(skill)
        return skill


skill_library = SkillLibrary()
