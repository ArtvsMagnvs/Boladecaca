# app/automation/engine.py — el motor de reglas (V0.9 A2b, doc 11 §A.1/§A.5)
#
# Carga las reglas `enabled=True`, arma su trigger, y cuando dispara: evalúa
# condiciones -> resuelve la acción por el registro `action_type -> executor`
# (que A3 rellena; aquí vacío, todo se registra como `skipped`) -> ejecuta ->
# audita. Garantías (doc 11 §A.5, P06 §4):
#   - AISLAMIENTO TOTAL: una regla que revienta jamás mata al engine ni afecta
#     a otras reglas — ni siquiera al handler de events.py o al job de
#     APScheduler que la invocó (ambos aíslan por su cuenta, pero el motor no
#     confía en eso: se blinda él mismo).
#   - IDEMPOTENCIA: `(rule_id, event_key)` con una ejecución `ok` previa nunca
#     se re-ejecuta.
#   - AUDITORÍA COMPLETA: toda evaluación que llega a tener un TriggerEvent
#     válido escribe una fila en `automation_executions` (ok/failed/skipped).
#
# La emisión de `automation.rule_fired` (doc 17 §4) es trabajo de A4 — aquí NO
# se emite todavía (evita adelantar un evento sin su consumidor aún definido).
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional

from app.automation.conditions import build_conditions
from app.automation.models import AutomationExecution, AutomationRule
from app.automation.triggers import Trigger, TriggerContext, TriggerEvent, build_trigger
from app.core.logging_config import get_system_logger
from app.db.database import SessionLocal

logger = get_system_logger("engine")

# Un ejecutor recibe (action_config, TriggerEvent) y devuelve el resultado (lo
# que sea, se serializa a texto para la auditoría). A3 los registra; el engine
# nunca importa app.automation.actions (evita el ciclo, mismo patrón que el
# registro de ejecutores del ApprovalGate en A1).
ActionExecutor = Callable[[dict, TriggerEvent], Awaitable[Any]]


class AutomationEngine:
    """Motor de evaluación. Singleton (mismo patrón que approval_gate/gateway)."""

    def __init__(self) -> None:
        self._armed: dict[int, Trigger] = {}
        self._action_executors: dict[str, ActionExecutor] = {}

    # ------------------------------------------------------------------
    # Registro de ejecutores de acción (inyectable — A3 enchufa las reales)
    # ------------------------------------------------------------------
    def register_action_executor(self, action_type: str, fn: ActionExecutor) -> None:
        self._action_executors[action_type] = fn

    def has_action_executor(self, action_type: str) -> bool:
        return action_type in self._action_executors

    # ------------------------------------------------------------------
    # Ciclo de vida de reglas
    # ------------------------------------------------------------------
    def load_rules(self) -> int:
        """Carga y arma TODAS las reglas `enabled=True`. Llamar en el lifespan
        tras arrancar APScheduler y registrar los adapters del Gateway (doc 20
        §A2b) — ScheduleTrigger necesita el scheduler vivo; EventTrigger no
        depende de nada más, pero se arma aquí por uniformidad. Devuelve cuántas
        se armaron (0 no es un error: puede no haber reglas todavía)."""
        db = SessionLocal()
        try:
            rules = db.query(AutomationRule).filter(AutomationRule.enabled == True).all()  # noqa: E712
            for rule in rules:
                try:
                    self.arm_rule(rule.id, rule.trigger_type, rule.trigger_config or {})
                except Exception as e:
                    logger.error(f"[engine] no se pudo armar la regla {rule.id} (se omite): {e!r}")
        finally:
            db.close()
        logger.info(f"[engine] {len(self._armed)} regla(s) armada(s)")
        return len(self._armed)

    def arm_rule(self, rule_id: int, trigger_type: str, trigger_config: dict) -> None:
        """Arma UNA regla (usada por `load_rules` y por la UI de A3 al activar
        una regla en caliente, sin reiniciar el backend)."""
        self.disarm_rule(rule_id)  # re-armar es seguro (desarma lo anterior primero)
        trigger = build_trigger(trigger_type, trigger_config)
        trigger.arm(self, rule_id)
        self._armed[rule_id] = trigger

    def disarm_rule(self, rule_id: int) -> None:
        """Desarma una regla (desactivar/borrar desde la UI de A3). Idempotente."""
        trigger = self._armed.pop(rule_id, None)
        if trigger is not None:
            try:
                trigger.disarm()
            except Exception as e:
                logger.error(f"[engine] error al desarmar la regla {rule_id} (ignorado): {e!r}")

    def disarm_all(self) -> None:
        """Desarma todas las reglas (shutdown del lifespan / limpieza de tests)."""
        for rule_id in list(self._armed.keys()):
            self.disarm_rule(rule_id)

    def armed_rule_ids(self) -> list[int]:
        return list(self._armed.keys())

    # ------------------------------------------------------------------
    # Punto de entrada de CUALQUIER trigger armado
    # ------------------------------------------------------------------
    async def handle_trigger(self, rule_id: int, ctx: TriggerContext) -> None:
        """Aislamiento total: nada de lo que pase aquí dentro se propaga hacia
        arriba (el handler de events.py o el job de APScheduler que llamó)."""
        try:
            await self._handle_trigger_inner(rule_id, ctx)
        except Exception as e:
            logger.error(f"[engine] regla {rule_id} falló de forma inesperada (aislado): {e!r}")

    async def _handle_trigger_inner(self, rule_id: int, ctx: TriggerContext) -> None:
        db = SessionLocal()
        try:
            rule = db.get(AutomationRule, rule_id)
            if rule is not None:
                db.expunge(rule)
        finally:
            db.close()
        if rule is None or not rule.enabled:
            return  # la regla se desactivó/borró entre el arm() y este disparo

        trigger = self._armed.get(rule_id)
        if trigger is None:
            return
        trigger_event = trigger.evaluate(ctx)
        if trigger_event is None:
            return  # el propio trigger decidió que este disparo no cuenta

        if self._already_executed(rule_id, trigger_event.event_key):
            return  # idempotencia — ya se ejecutó con éxito para este hecho

        conditions = build_conditions(rule_id, rule.condition_config or {}, rule.cooldown_s or 0)
        if not all(c.check(trigger_event, ctx) for c in conditions):
            self._record(rule_id, trigger_event, status="skipped", result="condiciones no cumplidas")
            return

        executor = self._action_executors.get(rule.action_type)
        if executor is None:
            self._record(
                rule_id, trigger_event, status="skipped",
                result=f"sin ejecutor para action_type={rule.action_type!r} (A3 lo registrará)",
            )
            return

        start = time.monotonic()
        try:
            result = await executor(rule.action_config or {}, trigger_event)
            duration_ms = int((time.monotonic() - start) * 1000)
            self._record(rule_id, trigger_event, status="ok", result=_to_text(result), duration_ms=duration_ms)
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            self._record(
                rule_id, trigger_event, status="failed",
                error=f"{type(e).__name__}: {e}", duration_ms=duration_ms,
            )

    # ------------------------------------------------------------------
    # Idempotencia + auditoría
    # ------------------------------------------------------------------
    def _already_executed(self, rule_id: int, event_key: str) -> bool:
        db = SessionLocal()
        try:
            existing = (
                db.query(AutomationExecution)
                .filter(
                    AutomationExecution.rule_id == rule_id,
                    AutomationExecution.event_key == event_key,
                    AutomationExecution.status == "ok",
                )
                .first()
            )
            return existing is not None
        finally:
            db.close()

    def _record(
        self,
        rule_id: int,
        trigger_event: TriggerEvent,
        *,
        status: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        db = SessionLocal()
        try:
            db.add(
                AutomationExecution(
                    rule_id=rule_id,
                    trigger_source=trigger_event.name,
                    event_key=trigger_event.event_key,
                    status=status,
                    result=result,
                    error=error,
                    duration_ms=duration_ms,
                    created_at=datetime.utcnow(),
                )
            )
            db.commit()
        except Exception as e:
            logger.error(f"[engine] no se pudo registrar la ejecución de la regla {rule_id}: {e!r}")
        finally:
            db.close()


def _to_text(value: Any) -> str:
    """Serializa el resultado de una acción para la columna Text de auditoría."""
    text = str(value)
    return text[:2000]


# Singleton — mismo patrón que approval_gate / gateway / scheduler_service.
automation_engine = AutomationEngine()
