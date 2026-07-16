# app/memory/lifecycle.py — MemoryLifecycleManager (V0.9 A2a, doc 08 RFC-007)
#
# "La memoria no se borra: se destila." Sin este job la ingesta de email/agenda
# crece sin límite y la búsqueda degrada (doc 11 §A.5 [Δ 2026-07-13]: lifecycle.py
# NO se construyó en V0.85 pese a lo que decía el RFC — se construye AQUÍ).
#
# Job nocturno post-summarizer (04:00 local). Micro-batch ≤500 items/noche
# (trabajo acotado, converge en varias noches). Cuatro fases (RFC-007 §Mecanismos):
#   (1) dedup semántico: items casi idénticos del mismo tipo (sim > 0.97) → merge
#       conservando el de metadata más rica.
#   (2/3) prune: borra items crudos viejos (fuera de la ventana HOT) CUYO
#       significado ya está preservado en un resumen diario (el summarizer los
#       genera). SALVAGUARDAS DURAS — nunca borra: pinned, category=urgente,
#       kind=daily_summary, ni tipos NEVER_COMPACT (decision/skill).
#   (4) archive: antes de podar, escribe el contenido al vault Markdown (legible,
#       fuera de índice) — la poda pierde resolución, no el hecho.
#   presupuesto: si la BD vectorial supera MEMORY_BUDGET_MB, aprieta la ventana
#       HOT (30→21→14→7 d) empezando por reducir lo más voluminoso.
#
# Cada pasada escribe un MemoryJobRun (trazabilidad de la poda, RFC-007) y emite
# `memory.compacted {pruned, merged, tier}`. Reloj LOCAL (como el store/summarizer).
#
# Interno del MOS: vive en app/memory/, usa el store/manager por dentro (owner del
# módulo, doc 16). Se expone via el barrel app.memory.
from __future__ import annotations

import asyncio
import os
from datetime import date, datetime, timedelta
from typing import Any, Optional

from app.core.events import emit
from app.core.logging_config import get_system_logger
from app.db.database import SessionLocal
from app.db.models import MemoryJobRun
from app.memory.interfaces import MemoryType
from app.memory.memory_manager import CHROMA_PATH, memory_manager
from app.memory.stores.local_store import _collection_name

logger = get_system_logger("lifecycle")

JOB_LIFECYCLE = "memory_lifecycle"

# NUNCA se compactan (conocimiento destilado, tamaño marginal) — RFC-007.
NEVER_COMPACT: frozenset[MemoryType] = frozenset({MemoryType.DECISION, MemoryType.SKILL})
# Tipos con detalle disposable: el patrón extraído (regla/skill) es lo permanente,
# el detalle se poda a los 90 días sin necesitar resumen (RFC-007).
SHORT_DETAIL_DAYS = 90
SHORT_DETAIL: frozenset[MemoryType] = frozenset({MemoryType.ERROR, MemoryType.AUTOMATION})
# Tipos crudos que se podan si su día ya tiene resumen (emails/agenda + chat).
PRUNABLE_WITH_SUMMARY: tuple[MemoryType, ...] = (MemoryType.PERSONAL, MemoryType.CONVERSATIONAL)
# Tipos sobre los que se hace dedup (crudos, pueden traer casi-duplicados).
DEDUP_TYPES: tuple[MemoryType, ...] = (
    MemoryType.PERSONAL,
    MemoryType.CONVERSATIONAL,
    MemoryType.PROJECT,
)

DEDUP_THRESHOLD = 0.97
MICRO_BATCH = 500
BASE_HOT_DAYS = 30


def _is_protected(meta: dict) -> bool:
    """Salvaguarda dura: un item protegido NUNCA se poda ni se deduplica-borra.
    pinned=true (marcado por el usuario), category=urgente (email importante) o
    kind=daily_summary (es el propio resumen que preserva el significado)."""
    if not meta:
        return False
    if str(meta.get("pinned")).lower() in ("true", "1"):
        return True
    if str(meta.get("category", "")).lower() == "urgente":
        return True
    if str(meta.get("kind", "")) == "daily_summary":
        return True
    return False


class MemoryLifecycleManager:
    """Compactación nocturna del MOS. Fail-soft total: cualquier error deja la
    memoria intacta y se registra en el MemoryJobRun."""

    # ------------------------------------------------------------------ tracking
    def _start_run(self) -> int:
        db = SessionLocal()
        try:
            run = MemoryJobRun(job_name=JOB_LIFECYCLE, started_at=datetime.utcnow(), status="running")
            db.add(run)
            db.commit()
            db.refresh(run)
            return run.id
        finally:
            db.close()

    def _finish_run(self, run_id: int, *, status: str, items: int = 0, detail: Optional[str] = None) -> None:
        db = SessionLocal()
        try:
            run = db.get(MemoryJobRun, run_id)
            if run is None:
                return
            run.finished_at = datetime.utcnow()
            run.status = status
            run.items_processed = items
            run.error_detail = detail
            db.commit()
        finally:
            db.close()

    def last_run(self) -> Optional[MemoryJobRun]:
        db = SessionLocal()
        try:
            return (
                db.query(MemoryJobRun)
                .filter(MemoryJobRun.job_name == JOB_LIFECYCLE)
                .order_by(MemoryJobRun.id.desc())
                .first()
            )
        finally:
            db.close()

    # ------------------------------------------------------------------ entrada
    async def run(self) -> dict:
        """Una pasada del lifecycle. Envuelve el trabajo Chroma (síncrono, lento)
        en to_thread para no bloquear el event loop."""
        if not memory_manager.is_healthy():
            return {"job": JOB_LIFECYCLE, "status": "skipped", "reason": "memoria no sana"}

        run_id = self._start_run()
        try:
            from app.core.config import settings

            budget_mb = int(getattr(settings, "MEMORY_BUDGET_MB", 512))
            hot_days = self._effective_hot_days(budget_mb)

            merged = await asyncio.to_thread(self._dedup_all)
            pruned = await asyncio.to_thread(self._prune_all, hot_days)

            detail = f"merged={merged} pruned={pruned} hot_days={hot_days}"
            self._finish_run(run_id, status="ok", items=merged + pruned, detail=detail)
            if merged or pruned:
                emit(
                    "memory.compacted",
                    source="mos",
                    payload={"pruned": pruned, "merged": merged, "tier": "hot"},
                )
            logger.info(f"[lifecycle] pasada ok — {detail}")
            return {"job": JOB_LIFECYCLE, "status": "ok", "merged": merged, "pruned": pruned, "hot_days": hot_days}
        except Exception as e:
            self._finish_run(run_id, status="error", detail=f"{type(e).__name__}: {e}")
            logger.error(f"[lifecycle] pasada falló (memoria intacta): {e!r}")
            return {"job": JOB_LIFECYCLE, "status": "error", "reason": str(e)}

    # ------------------------------------------------------------------ presupuesto
    def _chroma_size_mb(self) -> float:
        total = 0
        try:
            for root, _dirs, files in os.walk(CHROMA_PATH):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total += os.path.getsize(fp)
                    except OSError:
                        pass
        except Exception:
            return 0.0
        return total / (1024 * 1024)

    def _effective_hot_days(self, budget_mb: int) -> int:
        """Ventana HOT efectiva. Si la BD vectorial supera el presupuesto, se
        aprieta (30→21→14→7) — cuanto más se pasa, más corta la ventana. Aviso al
        log; el evento memory.compacted y el MemoryJobRun dejan el rastro."""
        size_mb = self._chroma_size_mb()
        if budget_mb <= 0 or size_mb <= budget_mb:
            return BASE_HOT_DAYS
        over = size_mb / budget_mb
        tightened = 7 if over > 2 else 14 if over > 1.5 else 21
        logger.warning(
            f"[lifecycle] memoria {size_mb:.0f}MB > presupuesto {budget_mb}MB "
            f"({over*100:.0f}%) — ventana HOT apretada a {tightened}d"
        )
        return tightened

    # ------------------------------------------------------------------ dedup
    def _dedup_all(self) -> int:
        total = 0
        for mt in DEDUP_TYPES:
            if mt in NEVER_COMPACT:
                continue
            try:
                total += self._dedup_type(mt)
            except Exception as e:
                logger.error(f"[lifecycle] dedup {mt.value} falló (ignorado): {e!r}")
        return total

    def _dedup_type(self, mt: MemoryType) -> int:
        import numpy as np

        col = memory_manager.get_or_create_collection(_collection_name(mt))
        if col is None:
            return 0
        got = col.get(limit=MICRO_BATCH, include=["embeddings", "metadatas"])
        ids = got.get("ids") or []
        embs = got.get("embeddings")
        metas = got.get("metadatas") or []
        if embs is None or len(ids) < 2:
            return 0

        arr = np.asarray(embs, dtype=float)
        if arr.ndim != 2 or arr.shape[0] != len(ids):
            return 0
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        unit = arr / norms
        sims = unit @ unit.T  # matriz de similitud coseno

        to_delete: set[str] = set()
        n = len(ids)
        for i in range(n):
            if ids[i] in to_delete:
                continue
            for j in range(i + 1, n):
                if ids[j] in to_delete:
                    continue
                if sims[i, j] < DEDUP_THRESHOLD:
                    continue
                mi = metas[i] or {}
                mj = metas[j] or {}
                # nunca borrar un item protegido; borra el de metadata más pobre.
                if len(mj) < len(mi):
                    victim = j
                elif len(mi) < len(mj):
                    victim = i
                else:
                    victim = j  # empate: conserva el primero (más antiguo)
                victim_meta = metas[victim] or {}
                if _is_protected(victim_meta):
                    # si el "perdedor" está protegido, intenta borrar el otro
                    other = i if victim == j else j
                    if _is_protected(metas[other] or {}):
                        continue  # ambos protegidos → no se toca ninguno
                    to_delete.add(ids[other])
                else:
                    to_delete.add(ids[victim])
                    if victim == i:
                        break  # i eliminado: pasa al siguiente i
        if to_delete:
            col.delete(ids=list(to_delete))
        return len(to_delete)

    # ------------------------------------------------------------------ prune + archive
    def _days_with_summary(self) -> set[str]:
        """Días que YA tienen resumen diario (kind=daily_summary en mem_personal).
        Podar un item crudo solo es seguro si su día tiene resumen que preserve el
        significado."""
        col = memory_manager.get_or_create_collection(_collection_name(MemoryType.PERSONAL))
        if col is None:
            return set()
        got = col.get(where={"kind": "daily_summary"})
        metas = got.get("metadatas") or []
        return {str((m or {}).get("date", "")) for m in metas if m and m.get("date")}

    def _prune_all(self, hot_days: int) -> int:
        total = 0
        summary_days = self._days_with_summary()
        cutoff = (date.today() - timedelta(days=hot_days)).isoformat()
        for mt in PRUNABLE_WITH_SUMMARY:
            try:
                total += self._prune_with_summary(mt, cutoff, summary_days)
            except Exception as e:
                logger.error(f"[lifecycle] prune {mt.value} falló (ignorado): {e!r}")
        # tipos de detalle disposable (error/automation): poda por edad, sin resumen.
        short_cutoff = (date.today() - timedelta(days=SHORT_DETAIL_DAYS)).isoformat()
        for mt in SHORT_DETAIL:
            try:
                total += self._prune_by_age(mt, short_cutoff)
            except Exception as e:
                logger.error(f"[lifecycle] prune(edad) {mt.value} falló (ignorado): {e!r}")
        return total

    def _prune_with_summary(self, mt: MemoryType, cutoff: str, summary_days: set[str]) -> int:
        col = memory_manager.get_or_create_collection(_collection_name(mt))
        if col is None:
            return 0
        got = col.get(limit=MICRO_BATCH * 4, include=["metadatas", "documents"])
        ids = got.get("ids") or []
        metas = got.get("metadatas") or []
        docs = got.get("documents") or []

        to_delete: list[str] = []
        archive: list[tuple[str, str]] = []  # (date, content)
        for i, iid in enumerate(ids):
            if len(to_delete) >= MICRO_BATCH:
                break
            meta = metas[i] or {}
            if _is_protected(meta):
                continue
            d = str(meta.get("date", ""))
            if not d or d >= cutoff:  # dentro de la ventana HOT o sin fecha → se conserva
                continue
            if d not in summary_days:  # sin resumen que preserve el significado → NO podar
                continue
            to_delete.append(iid)
            archive.append((d, docs[i] if i < len(docs) else ""))

        if to_delete:
            self._archive(mt, archive)  # escribe al vault ANTES de borrar
            col.delete(ids=to_delete)
        return len(to_delete)

    def _prune_by_age(self, mt: MemoryType, cutoff: str) -> int:
        """Poda por edad pura (detalle disposable). El pattern extraído es
        permanente; el detalle de >90d se descarta sin resumen."""
        col = memory_manager.get_or_create_collection(_collection_name(mt))
        if col is None:
            return 0
        got = col.get(limit=MICRO_BATCH, include=["metadatas", "documents"])
        ids = got.get("ids") or []
        metas = got.get("metadatas") or []
        docs = got.get("documents") or []
        to_delete: list[str] = []
        archive: list[tuple[str, str]] = []
        for i, iid in enumerate(ids):
            meta = metas[i] or {}
            if _is_protected(meta):
                continue
            d = str(meta.get("date", ""))
            if not d or d >= cutoff:
                continue
            to_delete.append(iid)
            archive.append((d, docs[i] if i < len(docs) else ""))
        if to_delete:
            self._archive(mt, archive)
            col.delete(ids=to_delete)
        return len(to_delete)

    def _archive(self, mt: MemoryType, entries: list[tuple[str, str]]) -> None:
        """Escribe el contenido podado al vault Markdown antes de borrarlo
        (best-effort; si falla, se registra y NO se aborta la poda — el resumen
        diario ya preserva el significado; el archive es un extra de rastro)."""
        try:
            from app.memory.vault import append_archive_entries

            append_archive_entries(mt.value, entries)
        except Exception as e:
            logger.error(f"[lifecycle] archive {mt.value} falló (no crítico): {e!r}")


# Singleton — mismo patrón que el resto del MOS.
lifecycle_manager = MemoryLifecycleManager()
