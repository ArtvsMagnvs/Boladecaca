# backend/app/automation/__init__.py — API PÚBLICA del Automation Engine (V0.9)
#
# [doc 16] Disciplina modular: este __init__ ES la API pública del paquete. El
# resto de la app importa SOLO desde `app.automation` — nunca de los internos
# (models/approval/scheduler/engine/triggers/conditions). La frontera la vigila
# tests/test_module_boundaries.py.
#
# V0.9 A1: modelos del esquema + ApprovalGate (primitivo genérico).
# V0.9 A2a: SchedulerService (planificador único, APScheduler).
# V0.9 A2b: motor de reglas + triggers + conditions.
# V0.9 A3: acciones + reglas predefinidas.
# V0.9 A3b: permission_service (Permisos & Autonomía, capa de política sobre
# el gate).
# V0.9 A4: AutomationLearner (stub congelado) + mem_automation/mem_error +
# evento automation.rule_fired (en engine.py, sin API pública nueva).

from app.automation.models import AutomationRule, AutomationExecution, Approval
from app.automation.approval import ApprovalGate, ApprovalResult, approval_gate
from app.automation.scheduler import SchedulerService, scheduler_service
from app.automation.triggers import (
    Trigger,
    TriggerContext,
    TriggerEvent,
    ScheduleTrigger,
    EventTrigger,
    ConditionTrigger,
    PatternTrigger,
    MemoryTrigger,
    WebhookTrigger,
    build_trigger,
)
from app.automation.conditions import (
    Condition,
    CooldownCondition,
    TimeWindowCondition,
    And,
    Or,
    Not,
    UserStateCondition,
    build_conditions,
)
from app.automation.engine import AutomationEngine, automation_engine
from app.automation.actions import (
    Action,
    ActionResult,
    TelegramMessageAction,
    EmailSummaryAction,
    ChatQueryAction,
    AgentTaskAction,
    WorkspaceAction,
    SkillExecutionAction,
    CalendarBlockAction,
    ChainedRuleAction,
    MemoryUpdateAction,
    DEFAULT_ACTIONS,
    register_default_actions,
)
from app.automation.rules_builtin import BUILTIN_RULES, seed_builtin_rules
import app.automation.permissions as permission_service
from app.automation.permissions import PermissionDef, PermissionState, PermissionCatalog
from app.automation.learner import AutomationLearner, automation_learner

__all__ = [
    # modelos (esquema V0.9)
    "AutomationRule",
    "AutomationExecution",
    "Approval",
    # ApprovalGate (primitivo genérico)
    "ApprovalGate",
    "ApprovalResult",
    "approval_gate",
    # planificador (A2a)
    "SchedulerService",
    "scheduler_service",
    # triggers (A2b)
    "Trigger",
    "TriggerContext",
    "TriggerEvent",
    "ScheduleTrigger",
    "EventTrigger",
    "ConditionTrigger",
    "PatternTrigger",
    "MemoryTrigger",
    "WebhookTrigger",
    "build_trigger",
    # conditions (A2b)
    "Condition",
    "CooldownCondition",
    "TimeWindowCondition",
    "And",
    "Or",
    "Not",
    "UserStateCondition",
    "build_conditions",
    # motor (A2b)
    "AutomationEngine",
    "automation_engine",
    # acciones (A3)
    "Action",
    "ActionResult",
    "TelegramMessageAction",
    "EmailSummaryAction",
    "ChatQueryAction",
    "AgentTaskAction",
    "WorkspaceAction",
    "SkillExecutionAction",
    "CalendarBlockAction",
    "ChainedRuleAction",
    "MemoryUpdateAction",
    "DEFAULT_ACTIONS",
    "register_default_actions",
    # reglas predefinidas (A3)
    "BUILTIN_RULES",
    "seed_builtin_rules",
    # permisos & autonomía (A3b)
    "permission_service",
    "PermissionDef",
    "PermissionState",
    "PermissionCatalog",
    # learner (A4, stub congelado — V1.2)
    "AutomationLearner",
    "automation_learner",
]
