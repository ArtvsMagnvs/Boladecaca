# backend/app/automation/__init__.py — API PÚBLICA del Automation Engine (V0.9)
#
# [doc 16] Disciplina modular: este __init__ ES la API pública del paquete. El
# resto de la app importa SOLO desde `app.automation` — nunca de
# app.automation.models ni app.automation.approval (internos). La frontera la
# vigila tests/test_module_boundaries.py.
#
# V0.9 A1: modelos del esquema + ApprovalGate (primitivo genérico). El motor,
# triggers, conditions, actions y learner se añaden en A2b/A3/A4.

from app.automation.models import AutomationRule, AutomationExecution, Approval
from app.automation.approval import ApprovalGate, ApprovalResult, approval_gate

__all__ = [
    # modelos (esquema V0.9)
    "AutomationRule",
    "AutomationExecution",
    "Approval",
    # ApprovalGate (primitivo genérico)
    "ApprovalGate",
    "ApprovalResult",
    "approval_gate",
]
