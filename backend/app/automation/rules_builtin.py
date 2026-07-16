# app/automation/rules_builtin.py — 5 reglas predefinidas (V0.9 A3, doc 11 §A.4)
#
# Todas nacen `enabled=False` (HITL, principio 1 del AE): el usuario las activa
# desde Ajustes → Automatizaciones cuando quiera, y puede editar su
# `action_config` (p.ej. poner un `agent_id` real en `agent_task`) antes.
from __future__ import annotations

from datetime import datetime
from typing import Any

# Cada entrada es el `trigger_config`/`action_config` declarativo que consume
# `build_trigger`/el registro de acciones — NUNCA se instancia una clase de
# Trigger/Action aquí, solo se describe la regla (doc 20 §3, esquema-primero).
BUILTIN_RULES: list[dict[str, Any]] = [
    {
        "name": "daily_briefing",
        "trigger_type": "schedule",
        "trigger_config": {"cron": {"hour": 8, "minute": 0}},
        "condition_config": {},
        "action_type": "telegram_message",
        "action_config": {"source": "daily_briefing"},
        "cooldown_s": 0,
    },
    {
        "name": "system_monitor",
        "trigger_type": "schedule",
        "trigger_config": {"interval_minutes": 30},
        "condition_config": {},
        "action_type": "telegram_message",
        "action_config": {"source": "system_monitor"},
        "cooldown_s": 300,  # 5 min, estilo Mark-XLVII (doc 11 §A.4)
    },
    {
        "name": "urgent_email_alert",
        "trigger_type": "event",
        "trigger_config": {
            "event_name": "email.triaged",
            "payload_filter": {"category": "urgente"},
            "event_key_field": "email_id",
        },
        "condition_config": {},
        "action_type": "telegram_message",
        "action_config": {"source": "urgent_email"},
        "cooldown_s": 0,
    },
    {
        "name": "email_summary",
        "trigger_type": "schedule",
        "trigger_config": {"cron": {"hour": 18, "minute": 0}},
        "condition_config": {},
        "action_type": "email_summary",
        "action_config": {},
        "cooldown_s": 0,
    },
    {
        # Delegación genérica — plantilla: el usuario debe rellenar agent_id/
        # task desde la UI antes de activarla (agent_id=None la deja inofensiva
        # incluso si alguien la activa sin configurar: AgentTaskAction falla
        # con un detail claro, nunca ejecuta un agente al azar).
        "name": "agent_task",
        "trigger_type": "event",
        "trigger_config": {"event_name": "task.created"},
        "condition_config": {},
        "action_type": "agent_task",
        "action_config": {"agent_id": None, "task": ""},
        "cooldown_s": 0,
    },
]


def seed_builtin_rules() -> int:
    """Inserta las reglas predefinidas que aún no existan (por `name`, único
    lógico) — idempotente, seguro de llamar en cada arranque. Devuelve cuántas
    se crearon en ESTA pasada (0 en arranques posteriores, el caso normal)."""
    from app.automation.models import AutomationRule
    from app.db.database import SessionLocal

    db = SessionLocal()
    created = 0
    try:
        existing = {row[0] for row in db.query(AutomationRule.name).all()}
        for spec in BUILTIN_RULES:
            if spec["name"] in existing:
                continue
            db.add(
                AutomationRule(
                    name=spec["name"],
                    enabled=False,
                    trigger_type=spec["trigger_type"],
                    trigger_config=spec["trigger_config"],
                    condition_config=spec["condition_config"],
                    action_type=spec["action_type"],
                    action_config=spec["action_config"],
                    cooldown_s=spec["cooldown_s"],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            )
            created += 1
        if created:
            db.commit()
    finally:
        db.close()
    return created
