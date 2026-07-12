# app/memory/stores/skill_store.py — LocalSkillStore(ISkillStore) (stub LSL, V0.85)
#
# Persiste LocalSkill en la coleccion mem_skill con el MISMO shape en metadata
# que usara la tabla `skills` de V1.1 (doc 09 §1.1) — la migracion futura es un
# backfill mecanico. La LSL completa (ciclo de vida, metricas, ejecucion via
# AgentRuntime) llega en V1.1; aqui solo lo minimo para congelar el contrato:
# create/get/list/search/improve/validate reales; publish no-op; execute lanza.
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Optional

from app.memory.interfaces import (
    ISkillStore,
    LocalSkill,
    MemoryType,
    SkillStatus,
)
from app.memory.memory_manager import memory_manager
from app.memory.router import memory_router

_SKILL_SOURCE = "skill"


# ---------------------------------------------------------------------------
# Serializacion LocalSkill <-> metadata (escalares + JSON para contenedores)
# ---------------------------------------------------------------------------
def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _skill_to_meta(skill: LocalSkill) -> dict[str, Any]:
    """LocalSkill -> metadata plana. Contenedores a JSON, datetimes a ISO,
    enums a .value. Descarta None (ChromaDB no los admite)."""
    raw: dict[str, Any] = {
        "skill_id": skill.id,
        "name": skill.name,
        "version": skill.version,
        "description": skill.description,
        "definition": json.dumps(skill.definition, ensure_ascii=False),
        "input_schema": json.dumps(skill.input_schema, ensure_ascii=False),
        "output_schema": json.dumps(skill.output_schema, ensure_ascii=False),
        "runtime_agnostic": skill.runtime_agnostic,
        "created_by": skill.created_by,
        "created_at": _iso(skill.created_at),
        "evidence_count": skill.evidence_count,
        "last_used": _iso(skill.last_used),
        "use_count": skill.use_count,
        "status": skill.status.value,
        "quality_score": skill.quality_score,
        "error_rate": skill.error_rate,
        "projects": json.dumps(skill.projects, ensure_ascii=False),
        "tags": json.dumps(skill.tags, ensure_ascii=False),
        "derived_from": json.dumps(skill.derived_from, ensure_ascii=False),
        "superseded_by": skill.superseded_by,
        "gsn_id": skill.gsn_id,
        "gsn_version": skill.gsn_version,
        "gsn_last_sync": _iso(skill.gsn_last_sync),
    }
    return {k: v for k, v in raw.items() if v is not None}


def _parse_dt(v: Any) -> Optional[datetime]:
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v))
    except (ValueError, TypeError):
        return None


def _json_list(v: Any) -> list:
    if not v:
        return []
    if isinstance(v, list):
        return v
    try:
        parsed = json.loads(v)
        return parsed if isinstance(parsed, list) else []
    except (ValueError, TypeError):
        return []


def _json_obj(v: Any) -> dict:
    if not v:
        return {}
    if isinstance(v, dict):
        return v
    try:
        parsed = json.loads(v)
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, TypeError):
        return {}


def _meta_to_skill(meta: dict) -> Optional[LocalSkill]:
    """metadata -> LocalSkill. Tolerante: si falta el shape esencial, None."""
    skill_id = meta.get("skill_id")
    if not skill_id:
        return None
    try:
        status = SkillStatus(meta.get("status", SkillStatus.DRAFT.value))
    except ValueError:
        status = SkillStatus.DRAFT
    return LocalSkill(
        id=str(skill_id),
        name=str(meta.get("name", "")),
        version=str(meta.get("version", "1.0.0")),
        description=str(meta.get("description", "")),
        definition=_json_obj(meta.get("definition")),
        input_schema=_json_obj(meta.get("input_schema")),
        output_schema=_json_obj(meta.get("output_schema")),
        runtime_agnostic=bool(meta.get("runtime_agnostic", True)),
        created_by=str(meta.get("created_by", "user")),
        created_at=_parse_dt(meta.get("created_at")) or datetime.utcnow(),
        evidence_count=int(meta.get("evidence_count", 0) or 0),
        last_used=_parse_dt(meta.get("last_used")),
        use_count=int(meta.get("use_count", 0) or 0),
        status=status,
        quality_score=float(meta.get("quality_score", 0.0) or 0.0),
        error_rate=float(meta.get("error_rate", 0.0) or 0.0),
        projects=_json_list(meta.get("projects")),
        tags=_json_list(meta.get("tags")),
        derived_from=_json_list(meta.get("derived_from")),
        superseded_by=meta.get("superseded_by"),
        gsn_id=meta.get("gsn_id"),
        gsn_version=meta.get("gsn_version"),
        gsn_last_sync=_parse_dt(meta.get("gsn_last_sync")),
    )


class LocalSkillStore(ISkillStore):
    """Stub de la Local Skill Library sobre mem_skill (doc 09)."""

    async def create(self, skill: LocalSkill) -> str:
        """Persiste (idempotente por skill.id). El contenido indexado es la
        descripcion (busqueda semantica); el shape completo va en metadata."""
        await memory_router.store(
            content=skill.description or skill.name,
            memory_type=MemoryType.SKILL,
            source=_SKILL_SOURCE,
            metadata=_skill_to_meta(skill),
            dedup_key=skill.id,
        )
        return skill.id

    async def get(self, skill_id: str) -> Optional[LocalSkill]:
        item = await memory_router.retrieve(f"{MemoryType.SKILL.value}:{skill_id}")
        if item is None:
            return None
        return _meta_to_skill(item.metadata)

    async def list(
        self,
        status: Optional[SkillStatus] = None,
        tags: Optional[list[str]] = None,
    ) -> list[LocalSkill]:
        """Lista todas las skills (opcionalmente filtradas). Usa el accesor
        compartido de ChromaDB — el contrato IMemoryStore no tiene 'list-all',
        y las skills son pocas en V0.85 (stub)."""
        def _work() -> list[LocalSkill]:
            col = memory_manager.get_or_create_collection(MemoryType.SKILL.value)
            if col is None:
                return []
            got = col.get()
            metas = got.get("metadatas", []) if got else []
            skills = [s for s in (_meta_to_skill(m or {}) for m in metas) if s]
            if status is not None:
                skills = [s for s in skills if s.status == status]
            if tags:
                wanted = set(tags)
                skills = [s for s in skills if wanted & set(s.tags)]
            return skills

        try:
            return await asyncio.to_thread(_work)
        except Exception as e:
            print(f"[LocalSkillStore] list error: {e}")
            return []

    async def search(self, query: str, top_k: int = 5) -> list[LocalSkill]:
        items = await memory_router.search(
            query, memory_types=[MemoryType.SKILL], top_k=top_k
        )
        return [s for s in (_meta_to_skill(it.metadata) for it in items) if s]

    async def improve(self, skill_id: str, changes: dict) -> Optional[LocalSkill]:
        """Aplica cambios de campo a una skill y la re-persiste (idempotente)."""
        skill = await self.get(skill_id)
        if skill is None:
            return None
        for key, value in changes.items():
            if hasattr(skill, key):
                setattr(skill, key, value)
        await self.create(skill)
        return skill

    async def validate(self, skill_id: str) -> Optional[LocalSkill]:
        """DRAFT -> VALIDATED (en V1.1 lo hara el LLL con evidencia)."""
        return await self.improve(skill_id, {"status": SkillStatus.VALIDATED})

    async def publish(self, skill_id: str) -> None:
        """No-op hasta la GSN (V2.0+)."""
        return None

    async def execute(self, skill_id: str, inputs: dict) -> dict:
        raise NotImplementedError(
            "LocalSkillStore.execute requiere un AgentRuntime — V1.1 (doc 10)."
        )


# Singleton — mismo patron que memory_router / ai_manager.
skill_store = LocalSkillStore()
