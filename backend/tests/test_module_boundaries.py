# tests/test_module_boundaries.py — [Δ doc 16 §4.4] fronteras modulares
#
# Disciplina modular sin frameworkitis (doc 16): cada modulo expone su API en su
# __init__.py y el resto de la app la consume SOLO por ahi. Este test vigila las
# fronteras de los modulos con API publica congelada:
#   1. app.memory (MOS) y app.workspace (WPMS) exportan su API publica esperada.
#   2. Ningun modulo FUERA de un modulo importa sus internos
#      (app.memory.stores/.router/.interfaces/.vault; app.workspace.models/
#      .service/.progress).
#
# Se permite el import legacy `app.memory.memory_manager` (grandfathered).
import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
MEMORY_DIR = APP_DIR / "memory"
WORKSPACE_DIR = APP_DIR / "workspace"
AUTOMATION_DIR = APP_DIR / "automation"
TIE_DIR = APP_DIR / "tie"

# Internos que NADIE de fuera del propio modulo debe importar directamente.
# Cada entrada: (prefijo de import prohibido, directorio propietario que SI puede).
FORBIDDEN_MODULES = (
    ("app.memory.stores", MEMORY_DIR),
    ("app.memory.router", MEMORY_DIR),
    ("app.memory.interfaces", MEMORY_DIR),
    ("app.memory.vault", MEMORY_DIR),
    ("app.workspace.models", WORKSPACE_DIR),
    ("app.workspace.service", WORKSPACE_DIR),
    ("app.workspace.progress", WORKSPACE_DIR),
    # V0.9 (Automation A1/A2a/A2b/A3): fronteras del Automation Engine.
    ("app.automation.models", AUTOMATION_DIR),
    ("app.automation.approval", AUTOMATION_DIR),
    ("app.automation.scheduler", AUTOMATION_DIR),
    ("app.automation.engine", AUTOMATION_DIR),
    ("app.automation.triggers", AUTOMATION_DIR),
    ("app.automation.conditions", AUTOMATION_DIR),
    ("app.automation.actions", AUTOMATION_DIR),
    ("app.automation.rules_builtin", AUTOMATION_DIR),
    ("app.automation.permissions", AUTOMATION_DIR),
    ("app.automation.learner", AUTOMATION_DIR),
    # V1.0 (TIE v1, T1/T2): fronteras del Task Intelligence Engine.
    ("app.tie.contracts", TIE_DIR),
    ("app.tie.runtime", TIE_DIR),
    ("app.tie.intents", TIE_DIR),
    ("app.tie.tracer", TIE_DIR),
    ("app.tie.missions", TIE_DIR),
    ("app.tie.pipeline", TIE_DIR),
    ("app.tie.router", TIE_DIR),
    ("app.tie.graph", TIE_DIR),
    ("app.tie.enricher", TIE_DIR),
    ("app.tie.planner", TIE_DIR),
    ("app.tie.executor", TIE_DIR),
    ("app.tie.responder", TIE_DIR),
)


def test_public_api_completa():
    """El barrel app.memory expone toda la API publica congelada de M1."""
    import app.memory as mem

    esperado = {
        # contratos
        "IMemoryStore", "ISkillStore", "MemoryType", "MemoryItem",
        "MemoryQuery", "LocalSkill", "SkillStatus",
        # acceso
        "MemoryRouter", "memory_router", "LocalSkillStore", "skill_store",
        # legacy
        "MemoryManager", "memory_manager", "CHROMA_PATH",
        # vault
        "vault_write_daily_summary", "vault_write_decision",
    }
    faltan = esperado - set(dir(mem))
    assert not faltan, f"app.memory no exporta: {sorted(faltan)}"
    # __all__ debe declararlos (contrato explicito, no accidental).
    assert esperado.issubset(set(mem.__all__)), (
        f"faltan en __all__: {sorted(esperado - set(mem.__all__))}"
    )


def test_workspace_public_api_completa():
    """El barrel app.workspace expone la API publica del WPMS (doc 18 §11)."""
    import app.workspace as ws

    esperado = {"Milestone", "workspace_service", "compute_progress", "is_done", "DONE_STATUSES"}
    faltan = esperado - set(dir(ws))
    assert not faltan, f"app.workspace no exporta: {sorted(faltan)}"
    assert esperado.issubset(set(ws.__all__)), (
        f"faltan en __all__: {sorted(esperado - set(ws.__all__))}"
    )


def test_automation_public_api_completa():
    """El barrel app.automation expone la API publica de A1/A2a/A2b/A3/A3b/A4 (doc 20)."""
    import app.automation as auto

    esperado = {
        # A1
        "AutomationRule", "AutomationExecution", "Approval",
        "ApprovalGate", "ApprovalResult", "approval_gate",
        # A2a
        "SchedulerService", "scheduler_service",
        # A2b
        "Trigger", "TriggerContext", "TriggerEvent",
        "ScheduleTrigger", "EventTrigger",
        "ConditionTrigger", "PatternTrigger", "MemoryTrigger", "WebhookTrigger",
        "build_trigger",
        "Condition", "CooldownCondition", "TimeWindowCondition",
        "And", "Or", "Not", "UserStateCondition", "build_conditions",
        "AutomationEngine", "automation_engine",
        # A3
        "Action", "ActionResult",
        "TelegramMessageAction", "EmailSummaryAction", "ChatQueryAction",
        "AgentTaskAction", "WorkspaceAction",
        "SkillExecutionAction", "CalendarBlockAction", "ChainedRuleAction", "MemoryUpdateAction",
        "DEFAULT_ACTIONS", "register_default_actions",
        "BUILTIN_RULES", "seed_builtin_rules",
        # A3b
        "permission_service", "PermissionDef", "PermissionState", "PermissionCatalog",
        # A4
        "AutomationLearner", "automation_learner",
    }
    faltan = esperado - set(dir(auto))
    assert not faltan, f"app.automation no exporta: {sorted(faltan)}"
    assert esperado.issubset(set(auto.__all__)), (
        f"faltan en __all__: {sorted(esperado - set(auto.__all__))}"
    )


def test_tie_public_api_completa():
    """El barrel app.tie expone la API publica del TIE v1 (doc 21 T1)."""
    import app.tie as tie

    esperado = {
        # contratos congelados
        "NodeState", "IntentType", "Intent", "MEL_CAPABILITIES",
        "TaskNode", "TaskGraph", "Mission",
        # runtime (doc 10)
        "AgentRuntime", "AgentTask", "AgentResult", "AgentChunk", "RuntimeHealth",
        "NullRuntime", "register_runtime", "get_runtime", "list_runtimes",
        # intent + misiones + trazas + motor de ejecución + responder
        "classify", "new_mission", "tracer", "executor", "responder",
        # pipeline (interfaz de orquestacion) — T4a/T4b completo
        "handle", "handle_stream", "submit_mission", "resolve_plan", "register_handlers",
    }
    faltan = esperado - set(dir(tie))
    assert not faltan, f"app.tie no exporta: {sorted(faltan)}"
    assert esperado.issubset(set(tie.__all__)), (
        f"faltan en __all__: {sorted(esperado - set(tie.__all__))}"
    )


def test_tie_handle_respeta_la_firma_de_messagehandler():
    """`tie.handle` es EL handler que instala `gateway.set_handler()` desde T4a —
    debe respetar exactamente `MessageHandler = Callable[[MessageEnvelope],
    Awaitable[Union[str, OutboundMessage]]]` (doc 21 Δ3). Si algún día cambia de
    firma sin querer, el switch del Gateway se rompe en silencio: este test lo
    blinda estáticamente (inspecciona la firma) y dinámicamente (lo instala de
    verdad en un Gateway y comprueba que queda como el handler activo)."""
    import inspect

    from app.gateway.gateway import Gateway
    from app.tie import handle

    assert inspect.iscoroutinefunction(handle)
    params = list(inspect.signature(handle).parameters.values())
    assert len(params) == 1, "MessageHandler recibe exactamente un envelope"

    gw = Gateway()
    gw.set_handler(handle)
    assert gw._handler is handle


def test_nadie_de_fuera_importa_internos_de_un_modulo():
    """Ningun .py fuera de un modulo importa sus internos (MOS y WPMS)."""
    offenders: list[str] = []
    for py in APP_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="ignore")
        for internal, owner_dir in FORBIDDEN_MODULES:
            # El propio modulo duenno SI puede usar sus internos.
            if owner_dir in py.parents or py.parent == owner_dir:
                continue
            # coincide con `import app.x.y...` y `from app.x.y import`
            pattern = rf"\b(from|import)\s+{re.escape(internal)}\b"
            if re.search(pattern, text):
                offenders.append(f"{py.relative_to(APP_DIR.parent)} -> {internal}")
    assert not offenders, (
        "Modulos que saltan una frontera (usa `from app.<modulo> import ...`):\n"
        + "\n".join(offenders)
    )
