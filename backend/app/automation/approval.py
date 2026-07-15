# app/automation/approval.py — ApprovalGate: el primitivo genérico (V0.9, doc 11 §A.2)
#
# HITL (principio 1 del AE): toda acción con consecuencias pasa por aquí. El gate
# NO sabe de canales ni de acciones concretas — sólo persiste una solicitud,
# notifica por el canal de origen (best-effort) y, al resolverse, ejecuta la
# acción por su registro de ejecutores (que A3 rellena) o la descarta.
#
# Persistente y reanudable (la "prueba de fuego"): TODO lo necesario para reanudar
# vive en la tabla `approvals` (incl. `action_payload`). Por eso una aprobación
# pendiente sobrevive a un reinicio del backend — al arrancar, los ejecutores se
# re-registran y cualquier `pending` se resuelve reconstruyendo la acción desde su
# payload. El gate en memoria no guarda estado de negocio, sólo el registro de
# ejecutores (que es configuración, no datos).
#
# Contrato CONGELADO (lo reusan V1.0 Orchestrator y V1.1 Hermes/skills):
#   request_approval(...) -> gate_id · resolve(gate_id, approved, note) -> ApprovalResult
#   list_pending() · get(gate_id) · register_executor(action_type, fn)
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional
from uuid import uuid4

from app.core.events import emit
from app.core.logging_config import get_system_logger
from app.db.database import SessionLocal
from app.automation.models import Approval

logger = get_system_logger("approval")

# Un ejecutor recibe el action_payload (dict) y ejecuta la acción real. A3
# registra los ejecutores reales (email_send, workspace, ...) SIN que el gate
# importe actions.py — evita el ciclo automation.approval <-> automation.actions.
ActionExecutor = Callable[[dict], Awaitable[Any]]

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
EXPIRED = "expired"
NOT_FOUND = "not_found"


@dataclass
class ApprovalResult:
    """Resultado de resolver una aprobación. `executed` distingue 'se aprobó y la
    acción corrió' de 'se aprobó pero no había ejecutor / falló'."""
    gate_id: str
    status: str
    executed: bool = False
    result: Any = None
    error: Optional[str] = None


class ApprovalGate:
    """Registro de ejecutores + ciclo de vida de las aprobaciones. Singleton
    (mismo patrón que gateway / memory_router / ai_manager)."""

    def __init__(self) -> None:
        self._executors: dict[str, ActionExecutor] = {}

    # ------------------------------------------------------------------
    # Registro de ejecutores (inyectable — A3 enchufa las acciones reales)
    # ------------------------------------------------------------------
    def register_executor(self, action_type: str, fn: ActionExecutor) -> None:
        """Re-registrar sobreescribe (idempotente ante recargas del módulo)."""
        self._executors[action_type] = fn

    def has_executor(self, action_type: str) -> bool:
        return action_type in self._executors

    # ------------------------------------------------------------------
    # Solicitar una aprobación
    # ------------------------------------------------------------------
    async def request_approval(
        self,
        *,
        kind: str,
        title: str,
        summary: str = "",
        action_type: str,
        action_payload: Optional[dict] = None,
        channel: str = "hub",
        target: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> str:
        """Crea una aprobación pendiente, la persiste, notifica por el canal de
        origen (best-effort) y emite `approval.requested`. Devuelve el gate_id."""
        gate_id = uuid4().hex
        db = SessionLocal()
        try:
            db.add(
                Approval(
                    id=gate_id,
                    kind=kind,
                    title=title,
                    summary=summary or None,
                    action_type=action_type,
                    action_payload=action_payload or {},
                    status=PENDING,
                    channel=channel,
                    target=target,
                    requested_at=datetime.utcnow(),
                    expires_at=expires_at,
                )
            )
            db.commit()
        finally:
            db.close()

        await self._notify(gate_id, kind, title, summary, channel, target)
        emit(
            "approval.requested",
            source="automation",
            payload={"gate_id": gate_id, "action": action_type},
        )
        return gate_id

    async def _notify(self, gate_id, kind, title, summary, channel, target) -> None:
        """Push por el canal de origen. El Hub NO recibe push (su UI sondea
        GET /api/automation/approvals); sólo los canales con adapter (Telegram)
        reciben el mensaje. Fail-soft TOTAL: la aprobación ya está persistida, la
        notificación es best-effort (doc 11 §A.2)."""
        if not channel or channel == "hub" or not target:
            return
        try:
            from app.gateway.gateway import gateway
            from app.gateway.envelope import OutboundMessage

            text = f"🔔 Aprobación pendiente: {title}"
            if summary:
                text += f"\n{summary}"
            text += "\n\nApruébala o recházala desde Aithera."
            await gateway.notify(
                channel,
                target,
                OutboundMessage(text=text, metadata={"gate_id": gate_id, "kind": kind}),
            )
        except Exception as e:
            logger.error(f"[approval] no se pudo notificar {gate_id} por {channel}: {e!r}")

    # ------------------------------------------------------------------
    # Resolver una aprobación (idempotente por claim atómico)
    # ------------------------------------------------------------------
    async def resolve(self, gate_id: str, approved: bool, note: str = "") -> ApprovalResult:
        """Resuelve una aprobación. IDEMPOTENTE: un `UPDATE ... WHERE status=pending`
        reclama la transición; sólo el primer resolver la gana y ejecuta la acción
        (un segundo resolve, o un doble clic, es no-op). Si se aprueba, reconstruye
        la acción desde (action_type, action_payload) y la ejecuta; escribe en la
        Decision API; emite `approval.resolved`."""
        new_status = APPROVED if approved else REJECTED

        db = SessionLocal()
        try:
            appr = db.get(Approval, gate_id)
            if appr is None:
                return ApprovalResult(gate_id=gate_id, status=NOT_FOUND, error="aprobación no encontrada")
            if appr.status != PENDING:
                # Ya resuelta/expirada: no re-ejecutar (idempotencia).
                return ApprovalResult(gate_id=gate_id, status=appr.status, executed=False)

            # Claim atómico: sólo un resolver gana la transición pending -> new_status.
            claimed = (
                db.query(Approval)
                .filter(Approval.id == gate_id, Approval.status == PENDING)
                .update(
                    {
                        Approval.status: new_status,
                        Approval.resolved_at: datetime.utcnow(),
                        Approval.resolution_note: note or None,
                    },
                    synchronize_session=False,
                )
            )
            db.commit()
            if not claimed:
                # Otro resolver ganó la carrera entre el get() y el update().
                current = db.get(Approval, gate_id)
                return ApprovalResult(
                    gate_id=gate_id,
                    status=current.status if current else NOT_FOUND,
                    executed=False,
                )
            action_type = appr.action_type
            payload = dict(appr.action_payload or {})
            kind = appr.kind
            title = appr.title
        finally:
            db.close()

        # A partir de aquí SOMOS el único resolver: la fila ya está en new_status.
        executed = False
        result: Any = None
        error: Optional[str] = None

        if approved:
            executor = self._executors.get(action_type)
            if executor is None:
                error = f"sin ejecutor para action_type={action_type!r}"
                logger.error(f"[approval] {error} (gate {gate_id})")
            else:
                try:
                    result = await executor(payload)
                    executed = True
                except Exception as e:  # la acción falló, pero la aprobación SÍ se dio
                    error = f"{type(e).__name__}: {e}"
                    logger.error(f"[approval] ejecutor de {action_type} falló (gate {gate_id}): {e!r}")

        # Decision API: registrar qué aprobó/rechazó el usuario (materia del Learner).
        decision_id = await self._record_decision(kind, title, approved, note)
        if decision_id:
            db = SessionLocal()
            try:
                appr = db.get(Approval, gate_id)
                if appr is not None:
                    appr.decision_id = decision_id
                    db.commit()
            finally:
                db.close()

        emit(
            "approval.resolved",
            source="automation",
            payload={"gate_id": gate_id, "action": action_type, "resolution": new_status},
        )
        return ApprovalResult(
            gate_id=gate_id, status=new_status, executed=executed, result=result, error=error
        )

    async def _record_decision(self, kind, title, approved, note) -> Optional[str]:
        """Escribe la decisión en la Decision API (SQL `decisions` + espejo). Best-
        effort: un fallo aquí no revierte la resolución ya persistida."""
        try:
            from app.services import decision_service

            verb = "concedida" if approved else "rechazada"
            decision = await decision_service.store_decision(
                title=f"Aprobación {verb}: {title}",
                body=note or "",
                reason=f"kind={kind}",
                impact="med",
            )
            return decision.id
        except Exception as e:
            logger.error(f"[approval] no se pudo registrar la decisión (gate resuelto igual): {e!r}")
            return None

    # ------------------------------------------------------------------
    # Consultar
    # ------------------------------------------------------------------
    def list_pending(self) -> list[Approval]:
        db = SessionLocal()
        try:
            rows = (
                db.query(Approval)
                .filter(Approval.status == PENDING)
                .order_by(Approval.requested_at.desc())
                .all()
            )
            for r in rows:
                db.expunge(r)  # detached con atributos cargados (patrón decision_service)
            return rows
        finally:
            db.close()

    def get(self, gate_id: str) -> Optional[Approval]:
        db = SessionLocal()
        try:
            appr = db.get(Approval, gate_id)
            if appr is not None:
                db.expunge(appr)
            return appr
        finally:
            db.close()


# Singleton — mismo patrón que gateway / memory_router / ai_manager.
approval_gate = ApprovalGate()
