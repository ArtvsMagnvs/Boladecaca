# backend/app/learner/cleanup.py — SANEAR LO YA APRENDIDO (V1.1 LC2, doc 41 §6)
#
# El rediseño no empieza en una casa vacía: la bandeja del usuario tiene
# propuestas nacidas del criterio equivocado (misiones de campañas de test,
# encargos repetidos porque FALLABAN, saludos) y las skills abiertas tienen
# evidencias que ya no significan lo que decían.
#
# Dos operaciones, las dos IDEMPOTENTES y las dos AUDITABLES:
#
#   1. `mark_legacy_evidence()` — las evidencias `execution_ok` (la máquina
#      diciendo "terminé") se re-etiquetan `legacy_unjudged`. NO se borran: se
#      pueden seguir leyendo, y el panel puede decir "3 misiones sin juzgar
#      todavía" en vez de dejar la propuesta parada sin explicación. Dejan de
#      contar para subir peldaños (`ladder.POSITIVE_KINDS`), que es justo el
#      punto: lo que se acumuló con el criterio viejo no promociona nada.
#
#   2. `purge_test_corpus()` — las propuestas VIVAS cuya evidencia viene de
#      misiones que no eran trabajo real (o que el juez declaró fallidas) se
#      cierran como `rejected` con nota. Nunca `DELETE`: un rechazo con motivo
#      es historia consultable; un borrado es un agujero.
#
# Por qué no es una migración de Alembic: no cambia el ESQUEMA, cambia el
# significado de unos datos, y hacerlo en Python permite consultar el juez y
# explicar cada decisión. Corre una vez en el arranque (idempotente) y también
# a mano desde el panel.
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

NOTA_PURGA = "corpus de pruebas o misiones que no sirvieron (saneado LC2)"
_FLAG = "learner.cleanup_lc2"          # marca de "ya hecho", en la tabla Config


# ---------------------------------------------------------------------------
# 1 · Las evidencias del criterio viejo
# ---------------------------------------------------------------------------
def mark_legacy_evidence() -> int:
    """Re-etiqueta `execution_ok` → `legacy_unjudged`. Devuelve cuántas filas
    tocó. Idempotente: la segunda pasada no encuentra ninguna."""
    from app.db.database import SessionLocal
    from app.learner.models import LearnerProposal

    tocadas = 0
    with SessionLocal() as s:
        for fila in s.query(LearnerProposal).all():
            evs = fila.evidence if isinstance(fila.evidence, list) else []
            cambio = False
            nuevas = []
            for ev in evs:
                if isinstance(ev, dict) and ev.get("kind") == "execution_ok":
                    ev = dict(ev)
                    ev["kind"] = "legacy_unjudged"
                    ev["note"] = ("evidencia anterior al juez: 'terminó' no es "
                                  "'sirvió' (doc 41 §4.3)")
                    cambio = True
                nuevas.append(ev)
            if cambio:
                fila.evidence = nuevas
                tocadas += 1
        if tocadas:
            s.commit()
    if tocadas:
        logger.info(f"[learner/cleanup] {tocadas} propuesta(s) con evidencia "
                    f"re-etiquetada como pendiente de juicio")
    return tocadas


# ---------------------------------------------------------------------------
# 2 · La bandeja contaminada
# ---------------------------------------------------------------------------
def _contaminada(propuesta: dict, veredictos: dict) -> Optional[str]:
    """¿Hay que retirar esta propuesta, y por qué? None = se queda.

    Se retira si TODA su evidencia viene de misiones que no eran trabajo real
    del usuario, o que el juez declaró fallidas. El "toda" es deliberado: si una
    sola misión de verdad la sostiene, la propuesta sigue viva aunque le sobre
    ruido — retirar de más también es un error."""
    from app.core import corpus

    evs = propuesta.get("evidence") or []
    claves = [str((ev or {}).get("context_key") or "") for ev in evs
              if isinstance(ev, dict)]
    claves = [c for c in claves if c]
    if not claves:
        return None                  # sin evidencia no hay nada que juzgar aquí

    reales, fallidas, prueba = 0, 0, 0
    for c in claves:
        v = veredictos.get(c)
        if v is None:
            continue                 # sin veredicto: no se acusa, se espera
        if not corpus.is_real(v["origin"]):
            prueba += 1
        elif v["verdict"] == "failed":
            fallidas += 1
        else:
            reales += 1

    if reales:
        return None
    if prueba and not fallidas:
        return f"{NOTA_PURGA} — {prueba} misión(es) de prueba"
    if fallidas:
        return (f"{NOTA_PURGA} — las {fallidas} misión(es) que la sostenían "
                f"no le sirvieron al usuario")
    return None


async def purge_test_corpus() -> list[str]:
    """Cierra las propuestas vivas que el criterio nuevo no sostiene.
    Devuelve los ids retirados."""
    import asyncio

    from app.db.database import SessionLocal
    from app.learner.models import MissionVerdict
    from app.learner.proposals import proposal_service

    def _veredictos() -> dict:
        with SessionLocal() as s:
            filas = (s.query(MissionVerdict)
                     .filter(MissionVerdict.superseded_by.is_(None)).all())
            return {f.mission_id: {"verdict": f.verdict, "origin": f.origin}
                    for f in filas}

    veredictos = await asyncio.to_thread(_veredictos)
    if not veredictos:
        return []

    retiradas: list[str] = []
    for p in await proposal_service.pending():
        motivo = _contaminada(p, veredictos)
        if not motivo:
            continue
        try:
            await proposal_service.reject(p["id"], note=motivo)
            retiradas.append(p["id"])
        except Exception as e:
            logger.info(f"[learner/cleanup] no se pudo retirar {p['id']}: {e!r}")
    if retiradas:
        logger.info(f"[learner/cleanup] {len(retiradas)} propuesta(s) retiradas "
                    f"del corpus contaminado")
    return retiradas


# ---------------------------------------------------------------------------
# El saneado completo, para el arranque
# ---------------------------------------------------------------------------
async def run_cleanup(force: bool = False) -> dict:
    """Las dos operaciones. Se ejecuta UNA vez (marca en `Config`) salvo que se
    fuerce desde el panel. Nunca lanza."""
    import asyncio

    from app.db.database import Config, SessionLocal

    def _hecho() -> bool:
        with SessionLocal() as s:
            return s.query(Config).filter(Config.key == _FLAG).first() is not None

    def _marca() -> None:
        with SessionLocal() as s:
            if s.query(Config).filter(Config.key == _FLAG).first() is None:
                s.add(Config(key=_FLAG, value="done"))
                s.commit()

    resumen = {"legacy_evidence": 0, "purged": []}
    try:
        if not force and await asyncio.to_thread(_hecho):
            return resumen
        resumen["legacy_evidence"] = await asyncio.to_thread(mark_legacy_evidence)
        resumen["purged"] = await purge_test_corpus()
        await asyncio.to_thread(_marca)
    except Exception as e:
        logger.error(f"[learner/cleanup] saneado fallido (no crítico): {e!r}")
    return resumen
