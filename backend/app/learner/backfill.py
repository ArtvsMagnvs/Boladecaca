# app/learner/backfill.py — migración mem_skill → tabla `skills` (V1.1 L1)
#
# El "backfill mecánico" que el propio docstring de LocalSkill anunciaba desde
# V0.85: el stub guardaba las skills SOLO en ChromaDB (mem_skill) con el mismo
# shape en metadata que la tabla; esto las trae a SQL, que desde L1 es la
# fuente de verdad.
#
# IDEMPOTENTE y seguro de correr en cada arranque: inserta solo los ids que no
# existan en SQL, jamás pisa una fila existente (si una skill vive en ambos
# sitios, SQL ya manda). Best-effort total: sin ChromaDB no hay nada que
# migrar y no es un error. Se invoca desde el lifespan (create_task + try/except,
# el patrón de todos los jobs de arranque) y es llamable directo en tests.
from __future__ import annotations

import asyncio

from app.core.logging_config import get_system_logger
from app.db.database import SessionLocal
from app.learner.models import Skill

logger = get_system_logger("learner.backfill")


async def backfill_from_mem_skill() -> int:
    """Devuelve cuántas skills se migraron (0 si no había nada o no hay Chroma)."""
    try:
        from app.memory import skill_store  # el stub de V0.85 (lector del legacy)

        legacy = await skill_store.list()
    except Exception as e:
        logger.info(f"[backfill] mem_skill no disponible ({e!r}) — nada que migrar")
        return 0
    if not legacy:
        return 0

    from app.learner.library import _skill_to_row_kwargs

    def _work() -> int:
        migradas = 0
        with SessionLocal() as s:
            existentes = {r[0] for r in s.query(Skill.id).all()}
            for sk in legacy:
                if sk.id in existentes:
                    continue
                s.add(Skill(**_skill_to_row_kwargs(sk)))
                migradas += 1
            if migradas:
                s.commit()
        return migradas

    n = await asyncio.to_thread(_work)
    if n:
        logger.info(f"[backfill] {n} skill(s) migradas de mem_skill a la tabla `skills`")
    return n
