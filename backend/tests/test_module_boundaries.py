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
    """El barrel app.automation expone la API publica de A1/A2a/A2b/A3/A3b (doc 20)."""
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
    }
    faltan = esperado - set(dir(auto))
    assert not faltan, f"app.automation no exporta: {sorted(faltan)}"
    assert esperado.issubset(set(auto.__all__)), (
        f"faltan en __all__: {sorted(esperado - set(auto.__all__))}"
    )


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
