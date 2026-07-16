# app/automation/triggers.py — Capa 1: disparadores (V0.9 A2b, doc 11 §A.1)
#
# Contrato CONGELADO (P06 §4): trigger nuevo = implementar Trigger, CERO cambios
# en engine.py. Dos ciclos de vida distintos, mismo contrato:
#   - arm(engine, rule_id): se llama UNA vez al activar la regla. Conecta el
#     trigger a su fuente real — un job de APScheduler (ScheduleTrigger) o una
#     suscripción al Event Bus (EventTrigger) — y hace que, al dispararse esa
#     fuente, se llame a `engine.handle_trigger(rule_id, ctx)`.
#   - evaluate(ctx): decide si ESTE disparo cuenta de verdad. Para
#     ScheduleTrigger casi siempre cuenta (el propio disparo del cron ES el
#     hecho); para EventTrigger filtra por nombre/payload del evento y deriva
#     el `event_key` de idempotencia.
#   - disarm(): desconecta (unsubscribe / remove_job). Al desactivar una regla.
#
# Sin polling propio (principio 4 del AE, P07 §6.2): EventTrigger NUNCA sondea
# Gmail/Calendar — reacciona a los eventos que el MOS y el WPMS ya emiten.
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class TriggerEvent:
    """El 'hecho disparador' ya resuelto — lo que la regla necesita para
    evaluar condiciones y ejecutar la acción. `event_key` es la clave de
    idempotencia: `(rule_id, event_key)` nunca se ejecuta dos veces con éxito
    (doc 11 §A.5)."""
    name: str
    event_key: str
    payload: dict = field(default_factory=dict)


@dataclass
class TriggerContext:
    """Lo que arma cada disparo concreto. `event` es el Event del bus si el
    disparo vino de ahí (None en un disparo de horario — el cron no trae
    payload propio)."""
    event: Optional[Any] = None  # app.core.events.Event
    now: datetime = field(default_factory=datetime.utcnow)


class Trigger(ABC):
    """Interfaz congelada de un disparador."""

    @abstractmethod
    def evaluate(self, ctx: TriggerContext) -> Optional[TriggerEvent]:
        """None si este disparo NO debe activar la regla (p.ej. el evento no
        matchea el filtro configurado). Nunca lanza — un trigger roto se trata
        como 'no dispara', el aislamiento real lo garantiza engine.py."""

    @abstractmethod
    def arm(self, engine: "AutomationEngine", rule_id: int) -> None:  # noqa: F821
        """Conecta el trigger a su fuente real. `engine` es el motor que recibe
        el disparo via `engine.handle_trigger(rule_id, ctx)`."""

    @abstractmethod
    def disarm(self) -> None:
        """Desconecta la fuente (remove_job / unsubscribe). Idempotente."""


# ---------------------------------------------------------------------------
# ScheduleTrigger — cron/interval sobre APScheduler (usa A2a)
# ---------------------------------------------------------------------------
class ScheduleTrigger(Trigger):
    """Dispara por horario. `cron={"hour":H,"minute":M}` (diario, hora LOCAL,
    mismo criterio que summarizer/lifecycle) o `interval_minutes=N`. Exactamente
    uno de los dos debe venir informado."""

    def __init__(self, *, cron: Optional[dict] = None, interval_minutes: Optional[int] = None):
        if not cron and not interval_minutes:
            raise ValueError("ScheduleTrigger necesita cron o interval_minutes")
        self.cron = cron
        self.interval_minutes = interval_minutes
        self._job_id: Optional[str] = None

    def evaluate(self, ctx: TriggerContext) -> Optional[TriggerEvent]:
        # El propio disparo del scheduler ES el hecho — no hay nada que filtrar.
        # event_key por minuto: si el proceso se reinicia y APScheduler recupera
        # un disparo perdido (misfire), no se duplica dentro del mismo minuto.
        return TriggerEvent(name="schedule", event_key=f"schedule:{ctx.now.strftime('%Y-%m-%dT%H:%M')}")

    def arm(self, engine: "AutomationEngine", rule_id: int) -> None:  # noqa: F821
        from app.automation.scheduler import scheduler_service

        job_id = f"automation_rule_{rule_id}"

        async def _fire() -> None:
            await engine.handle_trigger(rule_id, TriggerContext())

        if self.cron:
            scheduler_service.add_cron_job(
                _fire, hour=int(self.cron["hour"]), minute=int(self.cron.get("minute", 0)), id=job_id
            )
        else:
            scheduler_service.add_interval_job(_fire, minutes=int(self.interval_minutes), id=job_id)
        self._job_id = job_id

    def disarm(self) -> None:
        from app.automation.scheduler import scheduler_service

        if self._job_id:
            scheduler_service.remove_job(self._job_id)
            self._job_id = None


# ---------------------------------------------------------------------------
# EventTrigger — reactivo sobre app/core/events.py (V0.85 M2 + WPMS V0.87 §10)
# ---------------------------------------------------------------------------
class EventTrigger(Trigger):
    """Se suscribe a UN nombre de evento exacto (sin wildcards parciales, doc 17
    §3.1). `payload_filter` exige coincidencia exacta en las claves dadas (p.ej.
    `{"category": "urgente"}` sobre `email.triaged`). `event_key_field` es la
    clave del payload que identifica el hecho para idempotencia (p.ej.
    `email_id`, `task_id`); si no hay campo claro, se usa el timestamp del Event
    (perder idempotencia real solo en ese caso residual).

    Eventos ya emitidos y listos para usarse (Δ1, doc 20 §1): `memory.ingested`,
    `email.triaged` (MOS V0.85) y `task.created`/`task.status_changed`/
    `task.closed`/`milestone.completed`/`project.progress_changed` (WPMS V0.87,
    doc 18 §10) — el WPMS "emite y sigue", el AE se suscribe sin tocar
    `app/workspace/`."""

    def __init__(
        self,
        *,
        event_name: str,
        payload_filter: Optional[dict] = None,
        event_key_field: Optional[str] = None,
    ):
        self.event_name = event_name
        self.payload_filter = payload_filter or {}
        self.event_key_field = event_key_field
        self._handler: Optional[Callable] = None

    def evaluate(self, ctx: TriggerContext) -> Optional[TriggerEvent]:
        event = ctx.event
        if event is None or event.name != self.event_name:
            return None
        for key, expected in self.payload_filter.items():
            if event.payload.get(key) != expected:
                return None
        key_val = event.payload.get(self.event_key_field) if self.event_key_field else None
        event_key = (
            f"{self.event_name}:{key_val}" if key_val is not None else f"{self.event_name}:{event.ts.isoformat()}"
        )
        return TriggerEvent(name=self.event_name, event_key=event_key, payload=dict(event.payload))

    def arm(self, engine: "AutomationEngine", rule_id: int) -> None:  # noqa: F821
        from app.core.events import subscribe

        async def _handler(event) -> None:
            await engine.handle_trigger(rule_id, TriggerContext(event=event))

        subscribe(self.event_name, _handler)
        self._handler = _handler

    def disarm(self) -> None:
        from app.core.events import unsubscribe

        if self._handler:
            unsubscribe(self.event_name, self._handler)
            self._handler = None


# ---------------------------------------------------------------------------
# Stubs con interfaz definida (doc 11 §A.1) — NotImplementedError deliberado:
# el catálogo de triggers ya está completo, la implementación llega con su fase.
# ---------------------------------------------------------------------------
class ConditionTrigger(Trigger):
    """V1.x — dispara cuando una condición arbitraria pasa a ser verdadera
    (polling ligero sobre estado interno, no red externa)."""

    def evaluate(self, ctx: TriggerContext) -> Optional[TriggerEvent]:
        raise NotImplementedError("ConditionTrigger: V1.x")

    def arm(self, engine, rule_id: int) -> None:
        raise NotImplementedError("ConditionTrigger: V1.x")

    def disarm(self) -> None:
        pass


class PatternTrigger(Trigger):
    """V1.2 — lo alimenta el LLL (doc 09): dispara sobre patrones detectados en
    el comportamiento del usuario (tareas repetidas, secuencias recurrentes)."""

    def evaluate(self, ctx: TriggerContext) -> Optional[TriggerEvent]:
        raise NotImplementedError("PatternTrigger: V1.2 (LLL)")

    def arm(self, engine, rule_id: int) -> None:
        raise NotImplementedError("PatternTrigger: V1.2 (LLL)")

    def disarm(self) -> None:
        pass


class MemoryTrigger(Trigger):
    """V1.2 — dispara cuando una búsqueda semántica sobre el MOS supera un
    umbral de relevancia (p.ej. 'algo parecido a esto ya pasó antes')."""

    def evaluate(self, ctx: TriggerContext) -> Optional[TriggerEvent]:
        raise NotImplementedError("MemoryTrigger: V1.2")

    def arm(self, engine, rule_id: int) -> None:
        raise NotImplementedError("MemoryTrigger: V1.2")

    def disarm(self) -> None:
        pass


class WebhookTrigger(Trigger):
    """V1.x — dispara por una llamada HTTP entrante externa. Requiere superficie
    de red nueva (fuera del alcance de V0.9, doc 11)."""

    def evaluate(self, ctx: TriggerContext) -> Optional[TriggerEvent]:
        raise NotImplementedError("WebhookTrigger: V1.x")

    def arm(self, engine, rule_id: int) -> None:
        raise NotImplementedError("WebhookTrigger: V1.x")

    def disarm(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Fábrica — construye un Trigger desde el trigger_config declarativo de una
# AutomationRule. Único lugar que conoce el mapeo trigger_type -> clase.
# ---------------------------------------------------------------------------
_TRIGGER_TYPES: dict[str, type] = {
    "schedule": ScheduleTrigger,
    "event": EventTrigger,
    "condition": ConditionTrigger,
    "pattern": PatternTrigger,
    "memory": MemoryTrigger,
    "webhook": WebhookTrigger,
}


def build_trigger(trigger_type: str, config: dict) -> Trigger:
    cls = _TRIGGER_TYPES.get(trigger_type)
    if cls is None:
        raise ValueError(f"trigger_type desconocido: {trigger_type!r}")
    if cls is ScheduleTrigger:
        return ScheduleTrigger(cron=config.get("cron"), interval_minutes=config.get("interval_minutes"))
    if cls is EventTrigger:
        return EventTrigger(
            event_name=config["event_name"],
            payload_filter=config.get("payload_filter"),
            event_key_field=config.get("event_key_field"),
        )
    return cls()  # stubs: no toman config, fallan en evaluate/arm por diseño
