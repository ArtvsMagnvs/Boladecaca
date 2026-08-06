# app/learner/proposals.py — la CUARENTENA en acción (V1.1 L1, doc 15 §3)
#
# El servicio que camina `LearnerProposal` por la escalera de confianza. Las
# REGLAS viven en ladder.py (puras); aquí solo persistencia y orquestación.
#
# CÓMO SE APLICA una propuesta consolidada — el registro de APPLIERS: el mismo
# patrón que el registro de ejecutores del ApprovalGate (V0.9 A1) y el de
# runtimes del TIE (doc 10). `proposals` NO sabe escribir preferencias, ni
# reglas, ni pins: cada kind registra su applier (L2/L4 los enchufan), y el
# applier escribe SIEMPRE por APIs públicas (memory_router, skill_library,
# automation...) — nunca SQL ajeno. Consecuencia del diseño: este módulo no
# importa nada del resto de la app salvo sus propios modelos y la escalera, y
# el contrato de producto "el Learner jamás escribe fuera de sus tablas" es
# verificable por inspección estática (test_product_learner.py).
#
# L1 registra UN applier real: `skill_new` (crear la skill DRAFT vía
# skill_library — la vía por la que Mission Learning propondrá skills en L2).
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Optional

from app.core.logging_config import get_system_logger
from app.db.database import SessionLocal
from app.learner import ladder
from app.learner.models import LearnerProposal

logger = get_system_logger("learner.proposals")

# applier(payload) -> snapshot dict de lo que había ANTES (para undo), o None
# si aplicar este kind no tiene estado previo que restaurar (p.ej. crear algo
# nuevo: su undo es retirarlo, y eso lo describe el propio snapshot).
Applier = Callable[[dict], Awaitable[Optional[dict]]]
Undoer = Callable[[dict, Optional[dict]], Awaitable[None]]

_APPLIERS: Dict[str, Applier] = {}
_UNDOERS: Dict[str, Undoer] = {}


def register_applier(kind: str, applier: Applier, undoer: Optional[Undoer] = None) -> None:
    """L2/L4 enchufan aquí. Registrar dos veces el mismo kind es un error de
    cableado, no una situación a tolerar en silencio."""
    if kind in _APPLIERS:
        raise ValueError(f"applier ya registrado para kind={kind!r}")
    _APPLIERS[kind] = applier
    if undoer is not None:
        _UNDOERS[kind] = undoer


def registered_kinds() -> tuple:
    return tuple(sorted(_APPLIERS))


def _touch(row: LearnerProposal) -> None:
    row.updated_at = datetime.utcnow()


class ProposalService:
    """create → add_evidence → advance (por la escalera) → apply | reject → undo.

    TODO cambio de estado pasa por `can_transition` + las rutas de riesgo de
    ladder.py. No hay ningún camino que consolide sin evidencia o aprobación —
    y si alguien lo intenta, la respuesta es una excepción con el motivo, no un
    silencio."""

    async def create(self, *, kind: str, title: str, summary: str = "",
                     payload: Optional[dict] = None, risk: str = "medium",
                     subject_id: Optional[str] = None,
                     project_id: Optional[int] = None,
                     state: str = "observed") -> str:
        if risk not in ladder.RISKS:
            raise ValueError(f"clase de riesgo desconocida: {risk!r}")
        if state not in ("observed", "candidate", "proposed"):
            # Nadie NACE validado ni consolidado: eso sería saltarse la
            # cuarentena en el constructor.
            raise ValueError(f"una propuesta no puede nacer en {state!r}")
        pid = str(uuid.uuid4())

        def _work():
            with SessionLocal() as s:
                s.add(LearnerProposal(id=pid, kind=kind, risk=risk, state=state,
                                      title=title, summary=summary,
                                      payload=payload or {}, subject_id=subject_id,
                                      project_id=project_id))
                s.commit()
        await asyncio.to_thread(_work)
        return pid

    async def get(self, proposal_id: str) -> Optional[dict]:
        def _work():
            with SessionLocal() as s:
                row = s.get(LearnerProposal, proposal_id)
                return self._out(row) if row else None
        return await asyncio.to_thread(_work)

    async def pending(self, *, kind: Optional[str] = None) -> list[dict]:
        """Lo que espera al usuario o a más evidencia (para el panel de L4)."""
        def _work():
            with SessionLocal() as s:
                q = s.query(LearnerProposal).filter(
                    LearnerProposal.state.in_(("observed", "candidate",
                                               "proposed", "validated")))
                if kind:
                    q = q.filter(LearnerProposal.kind == kind)
                return [self._out(r) for r in
                        q.order_by(LearnerProposal.created_at.desc()).all()]
        return await asyncio.to_thread(_work)

    async def decided(self, *, limit: int = 50) -> list[dict]:
        """[L4] Lo que YA se decidió — aceptado, rechazado o deshecho — para el
        historial del panel. Los rechazos se guardan con su motivo a propósito
        (doc 15 §8: el Learner aprende de los noes), así que el usuario puede
        ver por qué dijo que no la última vez que le propusieron lo mismo."""
        def _work():
            with SessionLocal() as s:
                q = (s.query(LearnerProposal)
                     .filter(LearnerProposal.state.in_(("consolidated", "rejected",
                                                        "reverted")))
                     .order_by(LearnerProposal.decided_at.desc().nullslast())
                     .limit(limit))
                return [self._out(r) for r in q.all()]
        return await asyncio.to_thread(_work)

    async def update_payload(self, proposal_id: str, payload: dict, *,
                             project_id: Optional[int] = None,
                             note: str = "") -> Optional[dict]:
        """[L3] Afina el CONTENIDO de una propuesta que aún está en cuarentena.

        Es lo máximo que un análisis puede hacerle a una propuesta sin pasar por
        la escalera: cambiar lo que se propone, nunca en qué peldaño está. Por
        eso una propuesta ya DECIDIDA (consolidada, rechazada, revertida) es
        intocable — reescribir lo que el usuario ya juzgó sería cambiarle el
        voto."""
        def _work():
            with SessionLocal() as s:
                row = s.get(LearnerProposal, proposal_id)
                if row is None:
                    return None
                if row.state not in ("observed", "candidate", "proposed", "validated"):
                    raise ValueError(
                        f"la propuesta {proposal_id} ya está decidida ({row.state}): "
                        f"su contenido no se reescribe")
                row.payload = dict(payload or {})
                row.project_id = project_id
                if note:
                    row.summary = f"{row.summary} ({note})".strip()
                row.updated_at = datetime.utcnow()
                s.commit()
                return self._out(row)
        return await asyncio.to_thread(_work)

    async def add_evidence(self, proposal_id: str, evidence: dict) -> dict:
        """Suma UNA evidencia (con señal externa, o se rechaza) y sube los
        peldaños automáticos que la evidencia justifique: observed→candidate
        con MIN_REP contextos, y proposed→validated SOLO por la ruta automática
        de su clase de riesgo. Nunca pasa de validated: consolidar es una
        acción deliberada (apply), no un efecto colateral de acumular."""
        if not ladder.is_valid_evidence(evidence):
            raise ValueError(
                "evidencia rechazada: hace falta señal EXTERNA "
                f"({', '.join(sorted(ladder.EXTERNAL_SIGNAL_KINDS))}) y un "
                "context_key — 'el LLM dijo que salió bien' no cuenta (doc 15 §3.3)")

        def _work():
            with SessionLocal() as s:
                row = s.get(LearnerProposal, proposal_id)
                if row is None:
                    raise ValueError(f"propuesta {proposal_id} no existe")
                if row.state in ("rejected", "reverted", "consolidated"):
                    raise ValueError(f"la propuesta está en {row.state}: no admite más evidencia")
                evs = list(row.evidence or [])
                evs.append(dict(evidence))
                row.evidence = evs
                if evidence["kind"] == "contradiction":
                    row.contradictions = int(row.contradictions or 0) + 1

                # Peldaños automáticos (solo los que la evidencia justifica):
                if row.state == "observed":
                    ok, _ = ladder.can_be_candidate(evs)
                    if ok and ladder.can_transition(row.state, "candidate"):
                        row.state = "candidate"
                if row.state == "candidate":
                    # candidate → proposed es hacerla VISIBLE: no exige más
                    # evidencia (ya la tuvo para ser candidate), pero sí es un
                    # paso explícito del análisis (L2/L3) — aquí no se auto-sube.
                    pass
                if row.state == "proposed":
                    ok, motivo = ladder.can_validate(row.risk, evs,
                                                     int(row.contradictions or 0))
                    # La ruta automática jamás usa una aprobación implícita:
                    # si el motivo es una aprobación de usuario, ya vendrá por
                    # approve() con su actor real.
                    if ok and not ladder.has_user_approval([evidence]) \
                          and ladder.can_transition(row.state, "validated"):
                        row.state = "validated"
                        row.decided_by = "auto"
                        row.decided_at = datetime.utcnow()
                        row.decision_note = motivo
                _touch(row)
                s.commit()
                return self._out(row)
        return await asyncio.to_thread(_work)

    async def promote_to_proposed(self, proposal_id: str) -> dict:
        """candidate → proposed: hacerla visible al usuario. La llama el
        análisis (L2/L3) cuando el patrón está formulado como algo enseñable."""
        return await self._step(proposal_id, "proposed", by=None)

    async def approve(self, proposal_id: str, *, note: str = "") -> dict:
        """El usuario dice sí: proposed → validated, registrado como HITL.
        Para riesgo alto es LA ÚNICA vía (doc 15 §3.2)."""
        def _work():
            with SessionLocal() as s:
                row = s.get(LearnerProposal, proposal_id)
                if row is None:
                    raise ValueError(f"propuesta {proposal_id} no existe")
                if not ladder.can_transition(row.state, "validated"):
                    raise ValueError(f"transición ilegal: {row.state} → validated")
                evs = list(row.evidence or [])
                evs.append({"kind": "user_approval", "context_key": "panel",
                            "payload": {"note": note}})
                row.evidence = evs
                row.state = "validated"
                row.decided_by = "user"
                row.decided_at = datetime.utcnow()
                row.decision_note = note or "aprobada por el usuario"
                _touch(row)
                s.commit()
                return self._out(row)
        return await asyncio.to_thread(_work)

    async def reject(self, proposal_id: str, *, note: str = "") -> dict:
        """El usuario dice no — y el no SE REGISTRA (L4: 'el Learner aprende
        de los no'). Terminal: una propuesta rechazada no resucita; si el
        patrón reaparece, el análisis crea OTRA con la historia a la vista."""
        def _work():
            with SessionLocal() as s:
                row = s.get(LearnerProposal, proposal_id)
                if row is None:
                    raise ValueError(f"propuesta {proposal_id} no existe")
                if not ladder.can_transition(row.state, "rejected"):
                    raise ValueError(f"transición ilegal: {row.state} → rejected")
                row.state = "rejected"
                row.decided_by = "user"
                row.decided_at = datetime.utcnow()
                row.decision_note = note or "rechazada por el usuario"
                _touch(row)
                s.commit()
                return self._out(row)
        return await asyncio.to_thread(_work)

    async def apply(self, proposal_id: str) -> dict:
        """validated → consolidated EJECUTANDO el applier de su kind. El único
        punto del Learner que cambia el mundo — y solo tras pasar la escalera.
        El applier devuelve el snapshot previo, que queda guardado para undo."""
        prop = await self.get(proposal_id)
        if prop is None:
            raise ValueError(f"propuesta {proposal_id} no existe")
        if prop["state"] != "validated":
            raise ValueError(
                f"solo se aplica lo VALIDADO (está en {prop['state']}): "
                "la cuarentena no tiene puerta de atrás")
        applier = _APPLIERS.get(prop["kind"])
        if applier is None:
            raise ValueError(f"sin applier registrado para kind={prop['kind']!r} "
                             f"(hay: {registered_kinds()})")

        snapshot = await applier(dict(prop["payload"]))

        def _work():
            with SessionLocal() as s:
                row = s.get(LearnerProposal, proposal_id)
                row.state = "consolidated"
                row.applied_snapshot = snapshot
                _touch(row)
                s.commit()
                return self._out(row)
        return await asyncio.to_thread(_work)

    async def undo(self, proposal_id: str) -> dict:
        """consolidated → reverted, restaurando el estado previo vía el undoer
        del kind (con el snapshot que apply guardó). El contrato de producto:
        'undo restaura el estado anterior'."""
        prop = await self.get(proposal_id)
        if prop is None:
            raise ValueError(f"propuesta {proposal_id} no existe")
        if prop["state"] != "consolidated":
            raise ValueError(f"solo se deshace lo consolidado (está en {prop['state']})")
        undoer = _UNDOERS.get(prop["kind"])
        if undoer is None:
            raise ValueError(f"sin undoer registrado para kind={prop['kind']!r}")

        await undoer(dict(prop["payload"]), prop.get("applied_snapshot"))

        def _work():
            with SessionLocal() as s:
                row = s.get(LearnerProposal, proposal_id)
                row.state = "reverted"
                row.decided_by = "user"
                row.decided_at = datetime.utcnow()
                _touch(row)
                s.commit()
                return self._out(row)
        return await asyncio.to_thread(_work)

    # ------------------------------------------------------------------
    async def _step(self, proposal_id: str, to: str, *, by: Optional[str]) -> dict:
        def _work():
            with SessionLocal() as s:
                row = s.get(LearnerProposal, proposal_id)
                if row is None:
                    raise ValueError(f"propuesta {proposal_id} no existe")
                if not ladder.can_transition(row.state, to):
                    raise ValueError(f"transición ilegal: {row.state} → {to}")
                row.state = to
                if by:
                    row.decided_by = by
                    row.decided_at = datetime.utcnow()
                _touch(row)
                s.commit()
                return self._out(row)
        return await asyncio.to_thread(_work)

    @staticmethod
    def _out(row: LearnerProposal) -> dict:
        return {
            "id": row.id, "kind": row.kind, "risk": row.risk, "state": row.state,
            "title": row.title, "summary": row.summary or "",
            "payload": dict(row.payload or {}), "subject_id": row.subject_id,
            "project_id": row.project_id,
            "evidence": list(row.evidence or []),
            "contradictions": int(row.contradictions or 0),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "decided_by": row.decided_by,
            "decision_note": row.decision_note,
            "applied_snapshot": row.applied_snapshot,
        }


proposal_service = ProposalService()


# ---------------------------------------------------------------------------
# Applier real de L1: `skill_new` — la vía por la que Mission Learning (L2)
# propondrá skills. Aplicar = crear la skill en DRAFT (que es SU cuarentena:
# la skill seguirá teniendo que ganarse VALIDATED por la suya). Undo = la
# skill se depreca — nunca se borra (doc 09 §1.2).
# ---------------------------------------------------------------------------
async def _apply_skill_new(payload: dict) -> Optional[dict]:
    from datetime import datetime as _dt

    from app.learner.library import skill_library
    from app.memory import LocalSkill, SkillStatus

    skill = LocalSkill(
        id=payload.get("id") or str(uuid.uuid4()),
        name=str(payload.get("name") or "skill sin nombre"),
        version=str(payload.get("version") or "1.0.0"),
        description=str(payload.get("description") or ""),
        definition=dict(payload.get("definition") or {}),
        input_schema=dict(payload.get("input_schema") or {}),
        output_schema=dict(payload.get("output_schema") or {}),
        runtime_agnostic=bool(payload.get("runtime_agnostic", True)),
        created_by=str(payload.get("created_by") or "local_learning_loop"),
        created_at=_dt.utcnow(),
        status=SkillStatus.DRAFT,
        projects=list(payload.get("projects") or []),
        tags=list(payload.get("tags") or []),
        derived_from=list(payload.get("derived_from") or []),
    )
    await skill_library.create(skill, actor="learner")
    return {"skill_id": skill.id}


async def _undo_skill_new(payload: dict, snapshot: Optional[dict]) -> None:
    from app.learner.library import skill_library

    skill_id = (snapshot or {}).get("skill_id")
    if skill_id:
        await skill_library.deprecate(skill_id, actor="user")


register_applier("skill_new", _apply_skill_new, _undo_skill_new)
