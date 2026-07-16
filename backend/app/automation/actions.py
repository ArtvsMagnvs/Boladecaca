# app/automation/actions.py — Capa 3: acciones (V0.9 A3, doc 11 §A.1)
#
# Contrato CONGELADO: acción nueva = implementar Action, CERO cambios en
# engine.py (se registra por action_type en el motor, mismo patrón que el
# ApprovalGate registra ejecutores de aprobación en A1). Aislamiento: una
# acción que lanza una excepción la captura engine.py (status="failed",
# mem_error en A4) — nunca mata el motor ni a otras reglas.
#
# Las 5 acciones reales cablean sobre APIs que YA EXISTEN — el AE nunca
# reimplementa lógica de negocio, solo la dispara:
#   TelegramMessageAction -> gateway.notify (A1, Δ8)
#   EmailSummaryAction    -> GET /api/email/digest (V0.7.3 B7), reusado tal cual
#   ChatQueryAction       -> chat_service.answer() (V0.85 M4)
#   AgentTaskAction        -> agent_manager.create_execution() — ÚNICO punto de
#                             delegación: en V1.0 se cambia por
#                             orchestrator.handle sin tocar nada más (doc 11 §B.4)
#   WorkspaceAction        -> workspace_service (Δ2) — el AE NUNCA recalcula
#                             progreso a mano; usa los mismos side effects que
#                             el endpoint HTTP (doc 18 §8/§10)
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.automation.triggers import TriggerEvent


@dataclass
class ActionResult:
    """Resultado de ejecutar una acción. `ok=False` con `detail` explicando por
    qué NO es lo mismo que una excepción: es un fallo de negocio controlado
    (p.ej. "sin chat_id configurado"), engine.py lo registra como `status=ok`
    si `ok=True`. Si la acción lanza de verdad, engine.py lo captura aparte
    (`status=failed`) — este dataclass es el camino feliz Y el de error suave."""
    ok: bool
    detail: str = ""
    data: Optional[dict] = None


class Action(ABC):
    """Interfaz congelada de una acción."""

    @abstractmethod
    async def execute(self, config: dict, trigger_event: "TriggerEvent") -> ActionResult:
        ...


# ---------------------------------------------------------------------------
# Helpers compartidos
# ---------------------------------------------------------------------------
def _default_telegram_target() -> Optional[str]:
    """Primer chat_id de la whitelist de Telegram (Config key `telegram_chat_id`,
    CSV — mismo dato que usa `app/api/endpoints/telegram.py`). None si no hay
    ninguno configurado."""
    from app.db.database import SessionLocal
    from app.db.models import Config

    db = SessionLocal()
    try:
        row = db.query(Config).filter(Config.key == "telegram_chat_id").first()
        if not row or not row.value:
            return None
        first = row.value.split(",")[0].strip()
        return first or None
    finally:
        db.close()


async def _daily_briefing_text() -> str:
    """Reusa exactamente los datos de GET /api/memory/briefing (doc 20 Δ3: ya
    trae el bloque `workspace` desde V0.87 W4) — sin llamadas nuevas a Gmail/LLM."""
    from datetime import datetime

    from app.memory.summarizer import build_deterministic_summary, gather_day_data, get_cached_summary

    target = datetime.utcnow().date()
    data = gather_day_data(target)
    summary = await get_cached_summary(target) or build_deterministic_summary(data)

    lines = [f"📋 Briefing de hoy ({data['date']})", summary]
    ws = data.get("workspace") or {}
    milestones = ws.get("active_milestones") or []
    if milestones:
        m = milestones[0]
        ratio = int(round((m.get("ratio") or 0) * 100))
        lines.append(f"Milestone activo: {m.get('name')} ({m.get('project_name')}) — {ratio}%")
    deadlines = ws.get("upcoming_deadlines") or []
    if deadlines:
        lines.append(f"{len(deadlines)} tarea(s) con fecha límite esta semana.")
    blocked = ws.get("blocked") or []
    if blocked:
        lines.append(f"{len(blocked)} tarea(s) bloqueada(s).")
    return "\n".join(lines)


async def _system_monitor_text() -> str:
    """Backend/proveedores IA — estilo Mark-XLVII (doc 11 §A.4)."""
    from app.ai.ai_manager import ai_manager

    health = await ai_manager.health_check()
    status = "✅ sana" if health.get("healthy") else "⚠️ caída"
    lines = [
        "🩺 Estado de Aithera",
        f"IA activa: {health.get('provider') or '(ninguna)'} ({health.get('model') or '—'}) — {status}",
    ]
    if health.get("fallback_active"):
        lines.append(f"Fallback activo (proveedor primario: {health.get('primary_provider')})")
    return "\n".join(lines)


def _urgent_email_text(trigger_event: "TriggerEvent") -> str:
    """El evento email.triaged solo trae {email_id, category} (doc 17 §4 —
    metadatos mínimos); remitente/asunto se resuelven contra EmailTriage."""
    from app.db.database import SessionLocal
    from app.db.models import EmailTriage

    email_id = trigger_event.payload.get("email_id")
    sender, subject = None, None
    if email_id:
        db = SessionLocal()
        try:
            row = db.query(EmailTriage).filter(EmailTriage.email_id == email_id).first()
            if row:
                sender, subject = row.sender, row.subject
        finally:
            db.close()
    return f"🚨 Email urgente de {sender or 'remitente desconocido'}: {subject or '(sin asunto)'}"


async def _build_dynamic_text(source: str, trigger_event: "TriggerEvent") -> str:
    if source == "daily_briefing":
        return await _daily_briefing_text()
    if source == "system_monitor":
        return await _system_monitor_text()
    if source == "urgent_email":
        return _urgent_email_text(trigger_event)
    return f"[{trigger_event.name}] {trigger_event.payload}"


# ---------------------------------------------------------------------------
# 1 · TelegramMessageAction
# ---------------------------------------------------------------------------
class TelegramMessageAction(Action):
    """Envía por el Gateway (`gateway.notify`, A1 Δ8), NUNCA por el bot
    directo — el AE no sabe de canales, igual que el resto del sistema.

    `config`: `{"text": "..."}` mensaje literal, O `{"source": "daily_briefing"
    | "system_monitor" | "urgent_email"}` para construir el texto en el momento
    a partir de datos ya calculados. `channel`/`target` opcionales (default:
    Telegram + primer chat_id autorizado)."""

    async def execute(self, config: dict, trigger_event: "TriggerEvent") -> ActionResult:
        from app.gateway.envelope import OutboundMessage
        from app.gateway.gateway import gateway

        text = config.get("text")
        source = config.get("source")
        if not text and source:
            text = await _build_dynamic_text(source, trigger_event)
        if not text:
            text = f"[{trigger_event.name}] {trigger_event.payload}"

        channel = config.get("channel", "telegram")
        target = config.get("target") or _default_telegram_target()
        if not target:
            return ActionResult(ok=False, detail="sin chat_id configurado para Telegram")

        delivered = await gateway.notify(channel, target, OutboundMessage(text=text))
        return ActionResult(
            ok=delivered,
            detail=text if delivered else f"no se pudo entregar por {channel!r} (¿canal registrado?)",
        )


# ---------------------------------------------------------------------------
# 2 · EmailSummaryAction
# ---------------------------------------------------------------------------
class EmailSummaryAction(Action):
    """Resume el inbox del día vía el digest YA existente (V0.7.3 B7) — solo
    BD local, sin Gmail ni LLM en caliente. `config.channel`/`target`
    opcionales para reenviar el resumen por un canal (Telegram)."""

    async def execute(self, config: dict, trigger_event: "TriggerEvent") -> ActionResult:
        from app.api.endpoints.email_activity import daily_digest

        data = await daily_digest(date=None)
        text = (
            f"📧 Digest de hoy: {data['triaged_total']} triados, "
            f"{data['urgent_pending']} urgentes sin leer, "
            f"{data['drafts_awaiting']} borrador(es) por revisar, "
            f"{data['meetings']['today']} reunión(es) hoy."
        )

        channel = config.get("channel")
        if channel:
            from app.gateway.envelope import OutboundMessage
            from app.gateway.gateway import gateway

            target = config.get("target") or _default_telegram_target()
            if target:
                await gateway.notify(channel, target, OutboundMessage(text=text))

        return ActionResult(ok=True, detail=text, data=data)


# ---------------------------------------------------------------------------
# 3 · ChatQueryAction
# ---------------------------------------------------------------------------
class ChatQueryAction(Action):
    """Reusa `chat_service.answer()` (V0.85 M4) — el MISMO pipeline que
    `/api/chat` y el Gateway, sin duplicar nada. `config.message` es el prompt;
    si falta, se compone uno genérico a partir del hecho que disparó la regla."""

    async def execute(self, config: dict, trigger_event: "TriggerEvent") -> ActionResult:
        from app.services import chat_service

        message = config.get("message") or (
            f"Resume brevemente este hecho para el usuario: {trigger_event.name} — {trigger_event.payload}"
        )
        result = await chat_service.answer(message, channel="automation", persist_chat_message=False)
        return ActionResult(ok=bool(result.text), detail=result.text or "(el modelo no devolvió texto)")


# ---------------------------------------------------------------------------
# 4 · AgentTaskAction — único punto de delegación genérica
# ---------------------------------------------------------------------------
class AgentTaskAction(Action):
    """Delega en `agent_manager.create_execution()`. Único punto que V1.0
    reconecta al Orchestrator (`orchestrator.handle`) sin tocar nada más del
    Automation Engine (doc 11 §B.4) — por eso vive aislado en su propia clase,
    sin lógica adicional aquí que luego haya que desenredar."""

    async def execute(self, config: dict, trigger_event: "TriggerEvent") -> ActionResult:
        from app.agents.agent_manager import agent_manager

        agent_id = config.get("agent_id")
        if not agent_id:
            return ActionResult(ok=False, detail="agent_id no configurado en la regla")
        task = config.get("task") or f"Tarea automática disparada por {trigger_event.name}"
        try:
            execution = agent_manager.create_execution(agent_id=int(agent_id), task=task)
        except ValueError as e:
            return ActionResult(ok=False, detail=str(e))
        return ActionResult(ok=True, detail=f"execution_id={execution.id}", data={"execution_id": execution.id})


# ---------------------------------------------------------------------------
# 5 · WorkspaceAction (Δ2, doc 18 §7)
# ---------------------------------------------------------------------------
class WorkspaceAction(Action):
    """Crear/cerrar/mover tarea vía `workspace_service` — el AE NUNCA
    recalcula progreso ni emite los eventos del WPMS a mano: reusa
    EXACTAMENTE los mismos side effects que `POST/PUT /api/tasks` (doc 18
    §8/§10): `apply_task_status_side_effects` + `recompute_project_progress`
    + `emit_task_created`/`emit_task_status_changed` + `on_task_closed`.

    `config.op`: "create_task" | "close_task" | "move_task" | "update_task"."""

    async def execute(self, config: dict, trigger_event: "TriggerEvent") -> ActionResult:
        from app.db.database import SessionLocal
        from app.db.models import Task
        from app.workspace import workspace_service

        op = config.get("op")
        db = SessionLocal()
        try:
            if op == "create_task":
                task = Task(
                    title=config.get("title") or f"Tarea automática ({trigger_event.name})",
                    description=config.get("description"),
                    status=config.get("status", "pending"),
                    priority=config.get("priority", "medium"),
                    project_id=config.get("project_id"),
                    milestone_id=config.get("milestone_id"),
                )
                just_closed = workspace_service.apply_task_status_side_effects(task)
                db.add(task)
                db.commit()
                db.refresh(task)
                workspace_service.recompute_project_progress(task.project_id, db)
                workspace_service.emit_task_created(task)
                if just_closed:
                    await workspace_service.on_task_closed(task, db)
                return ActionResult(ok=True, detail=f"tarea creada id={task.id}", data={"task_id": task.id})

            if op in ("close_task", "move_task", "update_task"):
                task_id = config.get("task_id")
                task = db.get(Task, task_id) if task_id else None
                if task is None:
                    return ActionResult(ok=False, detail=f"tarea {task_id!r} no encontrada")

                old_status, old_project_id = task.status, task.project_id
                if op == "close_task":
                    task.status = config.get("status", "done")
                elif op == "move_task":
                    task.project_id = config.get("project_id")
                    if "milestone_id" in config:
                        task.milestone_id = config.get("milestone_id")
                else:  # update_task genérico
                    for field in ("title", "description", "status", "priority", "project_id", "milestone_id"):
                        if field in config:
                            setattr(task, field, config[field])

                just_closed = workspace_service.apply_task_status_side_effects(task)
                db.commit()
                db.refresh(task)
                workspace_service.recompute_project_progress(task.project_id, db)
                if old_project_id is not None and old_project_id != task.project_id:
                    workspace_service.recompute_project_progress(old_project_id, db)
                if task.status != old_status:
                    workspace_service.emit_task_status_changed(task, old_status, task.status)
                if just_closed:
                    await workspace_service.on_task_closed(task, db)
                return ActionResult(ok=True, detail=f"tarea {task.id} actualizada", data={"task_id": task.id})

            return ActionResult(ok=False, detail=f"op desconocida: {op!r}")
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Stubs con interfaz definida (doc 11 §A.1) — NotImplementedError deliberado.
# Registrados igualmente (ver DEFAULT_ACTIONS): si una regla mal configurada
# apunta a uno de estos, el fallo debe ser CLARO ("V1.1 (LSL)"), no un genérico
# "sin ejecutor" — engine.py lo captura y lo audita como `status=failed`.
# ---------------------------------------------------------------------------
class _StubAction(Action):
    _note: str = "V1.x"

    async def execute(self, config: dict, trigger_event: "TriggerEvent") -> ActionResult:
        raise NotImplementedError(f"{type(self).__name__}: {self._note}")


class SkillExecutionAction(_StubAction):
    """V1.1 — ejecuta una skill del LSL (doc 09)."""
    _note = "V1.1 (LSL)"


class CalendarBlockAction(_StubAction):
    """V1.x — bloquea un hueco en el calendario."""
    _note = "V1.x"


class ChainedRuleAction(_StubAction):
    """V1.x — dispara otra regla como efecto de esta (composición de reglas)."""
    _note = "V1.x"


class MemoryUpdateAction(_StubAction):
    """V1.x — escribe/actualiza un item de memoria directamente."""
    _note = "V1.x"


# ---------------------------------------------------------------------------
# Registro — action_type (string declarativo de AutomationRule) -> instancia.
# Único lugar que conoce este mapeo; una acción nueva no obliga a tocar
# engine.py (P06 §4). Las instancias son sin estado (stateless) — reutilizables.
# ---------------------------------------------------------------------------
DEFAULT_ACTIONS: dict[str, Action] = {
    "telegram_message": TelegramMessageAction(),
    "email_summary": EmailSummaryAction(),
    "chat_query": ChatQueryAction(),
    "agent_task": AgentTaskAction(),
    "workspace": WorkspaceAction(),
    "skill_execution": SkillExecutionAction(),
    "calendar_block": CalendarBlockAction(),
    "chained_rule": ChainedRuleAction(),
    "memory_update": MemoryUpdateAction(),
}


def register_default_actions(engine: Any) -> None:
    """Registra el catálogo completo en el motor. Llamar UNA vez en el
    lifespan, antes de `engine.load_rules()` (doc 20 §A3)."""
    for action_type, action in DEFAULT_ACTIONS.items():
        engine.register_action_executor(action_type, action.execute)
