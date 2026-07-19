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
    ("app.tie.toolloop", TIE_DIR),   # R1: el bucle es interno del TIE
    ("app.tie.authority", TIE_DIR),  # R4: la frontera de autoridad es interna del TIE
    ("app.tie.graph", TIE_DIR),
    ("app.tie.enricher", TIE_DIR),
    ("app.tie.planner", TIE_DIR),
    ("app.tie.executor", TIE_DIR),
    ("app.tie.responder", TIE_DIR),
    # V1.0 (MEL v1, E1): fronteras del Model Execution Layer. NADIE de fuera de
    # app.mel importa sus internos — y en particular solo app.mel.registry
    # importa ai_manager (doc 19 §1.2), vigilado por test aparte más abajo.
    ("app.mel.contracts", APP_DIR / "mel"),
    ("app.mel.registry", APP_DIR / "mel"),
    ("app.mel.decision", APP_DIR / "mel"),
    ("app.mel.policies", APP_DIR / "mel"),
    ("app.mel.fallback", APP_DIR / "mel"),
    ("app.mel.executor", APP_DIR / "mel"),
    ("app.mel.catalog", APP_DIR / "mel"),
    ("app.mel.capabilities", APP_DIR / "mel"),
    ("app.mel.models", APP_DIR / "mel"),
    ("app.mel.research", APP_DIR / "mel"),
    ("app.mel.overrides", APP_DIR / "mel"),
    # V1.0 (R2): fronteras del Orquestador. La dependencia va en UN SOLO
    # sentido (orquestador -> TIE); el test de abajo vigila que no haya ciclo.
    ("app.orchestrator.contracts", APP_DIR / "orchestrator"),
    ("app.orchestrator.decomposer", APP_DIR / "orchestrator"),
    ("app.orchestrator.conductor", APP_DIR / "orchestrator"),
    ("app.orchestrator.consolidator", APP_DIR / "orchestrator"),
    ("app.orchestrator.store", APP_DIR / "orchestrator"),
    ("app.orchestrator.models", APP_DIR / "orchestrator"),
)


def test_el_tie_no_importa_el_orquestador():
    """[R2] La capa de misiones se apoya en el TIE, NUNCA al revés.

    Un ciclo aquí rompería el arranque (ambos módulos se importan en el lifespan)
    y, peor, significaría que el TIE ha empezado a saber de orquestación — que es
    justo la separación que este bloque existe para mantener."""
    import re as _re
    from pathlib import Path as _Path

    ofensores = []
    for py in (APP_DIR / "tie").rglob("*.py"):
        texto = py.read_text(encoding="utf-8", errors="ignore")
        for i, linea in enumerate(texto.splitlines(), 1):
            if linea.lstrip().startswith("#"):
                continue
            if _re.search(r"\b(from|import)\s+app\.orchestrator\b", linea):
                ofensores.append(f"{py.relative_to(APP_DIR.parent)}:{i}")
    assert not ofensores, (
        "app.tie importa app.orchestrator (ciclo):\n" + "\n".join(ofensores)
    )


def test_orchestrator_public_api_completa():
    """El barrel app.orchestrator expone la API publica de R2."""
    import app.orchestrator as orch

    esperado = {
        "Objective", "OrchestrationRun",
        "handle", "submit", "recent_runs", "get_run", "cancel_run",
    }
    assert esperado <= set(orch.__all__)
    for nombre in esperado:
        assert hasattr(orch, nombre), f"falta {nombre} en el barrel"


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


def test_mel_public_api_completa():
    """El barrel app.mel expone la API publica del MEL v1 (doc 19 §1.2, E1)."""
    import app.mel as mel

    esperado = {
        # contratos congelados
        "Capability", "PolicyName", "ModelRef", "Constraints",
        "ExecutionRequest", "ExecutionResult", "ServedBy", "Usage", "DecisionTrace",
        # API publica
        "complete", "stream", "decision_trace", "recent_decisions",
        "policies", "set_active_policy", "resolve_model_name", "ensure_ready",
        "register_handlers", "capability_report", "refresh_capability_reports",
        # E2b — personalizacion de politicas + override explicito por proyecto
        "list_models", "set_policy_primary", "restore_policy",
        "set_project_override", "overrides_for", "list_overrides", "clear_override",
    }
    faltan = esperado - set(dir(mel))
    assert not faltan, f"app.mel no exporta: {sorted(faltan)}"
    assert esperado.issubset(set(mel.__all__)), (
        f"faltan en __all__: {sorted(esperado - set(mel.__all__))}"
    )


def test_solo_el_registry_del_mel_importa_ai_manager():
    """Frontera dura del doc 19 §1.2: NADIE fuera de `app.mel.registry` importa
    `ai_manager` desde dentro de `app/mel/` — el resto del MEL habla con
    proveedores SOLO a traves del registry. (Fuera del MEL, chat_service/tie/etc.
    aun usan ai_manager directo hasta la migracion de E2 — eso es esperado.)"""
    mel_dir = APP_DIR / "mel"
    offenders: list[str] = []
    for py in mel_dir.rglob("*.py"):
        if py.name == "registry.py":
            continue
        text = py.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"\b(from|import)\s+app\.ai\.ai_manager\b", text):
            offenders.append(py.name)
    assert not offenders, f"modulos del MEL que importan ai_manager sin ser el registry: {offenders}"


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
