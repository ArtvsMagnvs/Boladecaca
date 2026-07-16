# app/automation/conditions.py — Capa 2: condiciones (V0.9 A2b, doc 11 §A.1)
#
# Contrato CONGELADO (P06 §4): condición nueva = implementar Condition, CERO
# cambios en engine.py. La composición (And/Or/Not) es barata y evita rediseño
# cuando una regla necesita combinar varias condiciones.
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.automation.triggers import TriggerContext, TriggerEvent


class Condition(ABC):
    """Interfaz congelada de una condición. `check` nunca lanza — un error de
    lectura (p.ej. BD caída) debe resolverse a `False` dentro de la propia
    condición (fail-closed: ante la duda, la regla NO se dispara)."""

    @abstractmethod
    def check(self, trigger_event: "TriggerEvent", ctx: "TriggerContext") -> bool:
        ...


# ---------------------------------------------------------------------------
# CooldownCondition — ventana mínima entre ejecuciones OK de una regla
# ---------------------------------------------------------------------------
class CooldownCondition(Condition):
    """True si han pasado >= `cooldown_s` segundos desde la última ejecución
    `ok` de esta regla (con independencia de qué trigger la disparó). Lee
    `automation_executions` — sin estado en memoria, sobrevive a un reinicio."""

    def __init__(self, rule_id: int, cooldown_s: int):
        self.rule_id = rule_id
        self.cooldown_s = cooldown_s

    def check(self, trigger_event, ctx) -> bool:
        if self.cooldown_s <= 0:
            return True
        from app.automation.models import AutomationExecution
        from app.db.database import SessionLocal

        db = SessionLocal()
        try:
            last = (
                db.query(AutomationExecution)
                .filter(AutomationExecution.rule_id == self.rule_id, AutomationExecution.status == "ok")
                .order_by(AutomationExecution.created_at.desc())
                .first()
            )
            if last is None or last.created_at is None:
                return True
            elapsed = (datetime.utcnow() - last.created_at).total_seconds()
            return elapsed >= self.cooldown_s
        except Exception:
            return False  # fail-closed
        finally:
            db.close()


# ---------------------------------------------------------------------------
# TimeWindowCondition — franja horaria LOCAL
# ---------------------------------------------------------------------------
class TimeWindowCondition(Condition):
    """True si la hora LOCAL actual cae en `[start_hour, end_hour)`. Soporta
    ventanas que cruzan medianoche (`start_hour > end_hour`, p.ej. 22-6)."""

    def __init__(self, start_hour: int, end_hour: int):
        self.start_hour = start_hour
        self.end_hour = end_hour

    def check(self, trigger_event, ctx) -> bool:
        hour = datetime.now().hour  # LOCAL a proposito, doc 07 §7
        if self.start_hour <= self.end_hour:
            return self.start_hour <= hour < self.end_hour
        return hour >= self.start_hour or hour < self.end_hour


# ---------------------------------------------------------------------------
# Composables
# ---------------------------------------------------------------------------
class And(Condition):
    def __init__(self, *conditions: Condition):
        self.conditions = conditions

    def check(self, trigger_event, ctx) -> bool:
        return all(c.check(trigger_event, ctx) for c in self.conditions)


class Or(Condition):
    def __init__(self, *conditions: Condition):
        self.conditions = conditions

    def check(self, trigger_event, ctx) -> bool:
        return any(c.check(trigger_event, ctx) for c in self.conditions)


class Not(Condition):
    def __init__(self, condition: Condition):
        self.condition = condition

    def check(self, trigger_event, ctx) -> bool:
        return not self.condition.check(trigger_event, ctx)


# ---------------------------------------------------------------------------
# Stub con interfaz definida (doc 11 §A.1)
# ---------------------------------------------------------------------------
class UserStateCondition(Condition):
    """V1.x — condiciona por estado del usuario (activo/ausente/en reunión).
    Requiere una señal de presencia que hoy no existe."""

    def check(self, trigger_event, ctx) -> bool:
        raise NotImplementedError("UserStateCondition: V1.x")


# ---------------------------------------------------------------------------
# Fábrica — construye las condiciones de una regla desde su `condition_config`
# declarativo + el `cooldown_s` propio de la tabla (doc 20 §3). Único lugar que
# conoce este mapeo; una condición nueva no obliga a tocar engine.py.
# ---------------------------------------------------------------------------
def build_conditions(rule_id: int, condition_config: dict, cooldown_s: int) -> list[Condition]:
    conditions: list[Condition] = []
    if cooldown_s and cooldown_s > 0:
        conditions.append(CooldownCondition(rule_id, cooldown_s))
    time_window = (condition_config or {}).get("time_window")
    if time_window:
        conditions.append(TimeWindowCondition(int(time_window["start_hour"]), int(time_window["end_hour"])))
    return conditions
