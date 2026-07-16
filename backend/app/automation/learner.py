# app/automation/learner.py — AutomationLearner (stub congelado, V0.9 A4)
#
# Cuarta capa del AE (doc 11 parte A: Triggers/Conditions/Actions/Learner). El
# AE NO contiene inteligencia — desde V0.9 el feedback real (aprobado/rechazado,
# resultado de cada regla) YA se captura vía la Decision API (`decision_service`)
# y el MOS (`engine.py::_remember`, mem_automation/mem_error). Este stub congela
# la INTERFAZ que V1.2 implementará sobre esos datos ya acumulados — nadie tiene
# que rediseñarla cuando llegue: solo dejar de lanzar.
#
# Sin lógica real a propósito (doc 20 §A4): "el feedback real ya se captura vía
# Decision API desde V0.9" — este módulo es el punto de enganche, no el cerebro.
from __future__ import annotations

from typing import Any, Optional


class AutomationLearner:
    """Singleton (mismo patrón que approval_gate/scheduler_service/
    automation_engine). Cada método documenta de qué datos ya acumulados en
    V0.9 se alimentará su implementación real en V1.2."""

    async def record_feedback(
        self,
        rule_id: int,
        outcome: str,
        detail: Optional[dict] = None,
    ) -> None:
        """V1.2 — registra una señal de feedback sobre una regla (p.ej. el
        usuario rechazó repetidamente una aprobación de esa regla). Fuente de
        datos ya viva desde A1/A3b: `decisions` vía `decision_service.history()`
        y `automation_executions`."""
        raise NotImplementedError("AutomationLearner.record_feedback: V1.2")

    async def suggest_new_rule(self, context: Optional[dict] = None) -> Any:
        """V1.2 — propone una regla nueva a partir de patrones repetidos (LLL,
        doc 09/15). Fuente de datos ya viva desde A4: `mem_automation` (éxitos)
        y `mem_error` (fallos) vía `memory_router.search()`."""
        raise NotImplementedError("AutomationLearner.suggest_new_rule: V1.2")

    async def suggest_rule_improvement(self, rule_id: int) -> Any:
        """V1.2 — propone un ajuste a una regla existente (p.ej. afinar un
        `cooldown_s` que genera fricción). Fuente de datos ya viva desde A2b/A4:
        `automation_executions` de esa regla + su rastro en `mem_automation`/
        `mem_error`."""
        raise NotImplementedError("AutomationLearner.suggest_rule_improvement: V1.2")


# Singleton — mismo patrón que approval_gate / scheduler_service / automation_engine.
automation_learner = AutomationLearner()
