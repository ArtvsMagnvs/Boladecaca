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
# A4 (doc 20 §A4): tras cada ejecución REAL (el executor llegó a correr, ok o
# failed — nunca "skipped"), el motor deja rastro consultable: emite
# `automation.rule_fired` (doc 17 §4) y escribe en el MOS (mem_automation en
# éxito, mem_error en fallo, doc 11 §A.3) para que el futuro Learner (V1.1/
# V1.2) nazca con datos reales. Todo en `_remember()`, best-effort — un fallo
# ahí jamás debe tapar que la regla YA quedó auditada en `automation_executions`.
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional

from app.automation.conditions import build_conditions
from app.automation.models import AutomationExecution, AutomationRule
from app.automation.triggers import Trigger, TriggerContext, TriggerEvent, build_trigger
from app.core.events import emit
from app.core.logging_config import get_system_logger
from app.db.database import SessionLocal
from app.memory import MemoryType, memory_router

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
            ok, text = _interpret_result(result)
            if ok:
                self._record(rule_id, trigger_event, status="ok", result=text, duration_ms=duration_ms)
            else:
                # la acción NO lanzó, pero reportó un fallo de negocio controlado
                # (p.ej. "sin chat_id configurado") — status="failed" con el
                # detail como error, para que la auditoría/UI lo distinga de un
                # éxito real (doc 20 §A3, contrato ActionResult.ok).
                self._record(rule_id, trigger_event, status="failed", error=text, duration_ms=duration_ms)
            await self._remember(rule, trigger_event, ok=ok, duration_ms=duration_ms, detail=text)
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            error_text = f"{type(e).__name__}: {e}"
            self._record(
                rule_id, trigger_event, status="failed",
                error=error_text, duration_ms=duration_ms,
            )
            await self._remember(rule, trigger_event, ok=False, duration_ms=duration_ms, detail=error_text)

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

    # ------------------------------------------------------------------
    # Rastro en el MOS + evento (A4, doc 11 §A.3 / doc 17 §4)
    # ------------------------------------------------------------------
    async def _remember(
        self,
        rule: AutomationRule,
        trigger_event: TriggerEvent,
        *,
        ok: bool,
        duration_ms: Optional[int],
        detail: str,
    ) -> None:
        """Solo se llama cuando el executor SÍ llegó a correr (nunca en
        "skipped" — condiciones no cumplidas, sin ejecutor, o idempotencia ya
        cubierta antes). Best-effort: la ejecución ya quedó auditada en
        `automation_executions` vía `_record()` antes de llegar aquí, así que
        un fallo de memoria/evento aquí no debe hacer parecer que la regla
        falló."""
        emit(
            "automation.rule_fired",
            source="automation",
            payload={"rule_id": rule.id, "trigger": trigger_event.name, "ok": ok, "duration_ms": duration_ms},
        )
        try:
            if ok:
                await memory_router.store(
                    content=f'Regla "{rule.name}" se ejecutó ({trigger_event.name}): {detail}'[:2000],
                    memory_type=MemoryType.AUTOMATION,
                    source="automation",
                    metadata={
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "trigger": trigger_event.name,
                        "duration_ms": duration_ms,
                    },
                )
            else:
                await memory_router.store(
                    content=f'Regla "{rule.name}" falló ({trigger_event.name}): {detail}'[:2000],
                    memory_type=MemoryType.ERROR,
                    source="automation",
                    metadata={
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "trigger": trigger_event.name,
                        "duration_ms": duration_ms,
                    },
                )
        except Exception as e:
            logger.error(f"[engine] no se pudo dejar rastro en el MOS para la regla {rule.id} (no crítico): {e!r}")


def _interpret_result(result: Any) -> tuple[bool, str]:
    """Traduce lo que devolvió el ejecutor a (ok, texto) para la auditoría.

    Los ejecutores reales devuelven `ActionResult` (actions.py) — engine.py
    NUNCA lo importa (evita el ciclo actions<->engine, mismo motivo que el
    registro de ejecutores del ApprovalGate en A1), así que se hace duck-typing
    sobre `.ok`/`.detail`: si el resultado los tiene, se usan; si no (un
    ejecutor de test devuelve un str suelto, p.ej.), se trata como éxito y se
    serializa a texto sin más."""
    ok = getattr(result, "ok", True)
    detail = getattr(result, "detail", None)
    text = detail if isinstance(detail, str) and detail else str(result)
    return bool(ok), text[:2000]


# Singleton — mismo patrón que approval_gate / gateway / scheduler_service.
automation_engine = AutomationEngine()
