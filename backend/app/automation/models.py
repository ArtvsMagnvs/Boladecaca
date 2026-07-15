# app/automation/models.py — Modelos del Automation Engine (V0.9, doc 11 parte A + doc 20 §3)
#
# Esquema-primero (patrón M1/W1): la migración 18.ª crea las 3 tablas de V0.9 por
# adelantado. En A1 sólo se USA `approvals` (el ApprovalGate); `automation_rules`
# y `automation_executions` quedan listas para el motor de A2b sin otra migración.
#
# Disciplina modular (doc 16): estos modelos viven en el módulo `app.automation`
# (igual que `Milestone` en `app.workspace.models`), se exportan por el __init__ y
# NADIE de fuera importa este archivo directamente. Base viene de app.db.database
# (todos los modelos comparten metadata → create_all los crea en BD nuevas).
#
# Referencias cross-tabla (`rule_id`, `project_id`, `decision_id`) como columnas
# planas indexadas, NO ForeignKey: mismo criterio del resto del proyecto —
# `init_db()` corre create_all al importar, la integridad la lleva la app.
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text

from app.db.database import Base


class AutomationRule(Base):
    """Definición declarativa de una regla: disparador → condición → acción.
    `enabled=False` por defecto — HITL: toda regla nace desactivada (doc 11 §A.4).
    La activa el usuario desde la UI (A3). Se USA en A2b; aquí sólo se crea la
    tabla."""

    __tablename__ = "automation_rules"

    id = Column(Integer, primary_key=True)
    name = Column(String(120))
    enabled = Column(Boolean, default=False, index=True)
    trigger_type = Column(String(40))          # "schedule" | "event" | ...
    trigger_config = Column(JSON)              # {cron|interval|event_name...}
    condition_config = Column(JSON)            # árbol And/Or/Not serializado
    action_type = Column(String(40))           # clave del registro de acciones
    action_config = Column(JSON)               # parámetros de la acción
    project_id = Column(Integer, index=True)   # -> projects.id (nullable)
    cooldown_s = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class AutomationExecution(Base):
    """Auditoría de cada evaluación de regla. `(rule_id, event_key)` = dedup
    idempotente (doc 11 §A.5). `checkpoint` = estado para reanudar tras una
    aprobación (paralelo a `approvals`). Se USA en A2b; aquí sólo se crea."""

    __tablename__ = "automation_executions"

    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, index=True)      # -> automation_rules.id
    trigger_source = Column(String(60))        # de dónde vino el disparo
    event_key = Column(String(200), index=True)  # idempotencia por evento
    status = Column(String(20), default="ok", index=True)  # ok|failed|skipped|waiting_approval
    result = Column(Text)
    error = Column(Text)
    checkpoint = Column(JSON)                  # estado para reanudar
    duration_ms = Column(Integer)
    approved = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)


class Approval(Base):
    """Store del ApprovalGate — el primitivo genérico (doc 11 §A.2). `action_payload`
    es la "clausura" serializada que se re-ejecuta al aprobar. TODO lo necesario
    para reanudar vive en esta fila: por eso una aprobación pendiente sobrevive a
    un reinicio del backend (al arrancar, los ejecutores se re-registran y la
    aprobación se resuelve reconstruyendo la acción desde su action_payload).

    Lo reusan el AE (V0.9), el executor del Orchestrator (V1.0, step con
    approval_required) y Hermes/skills (V1.1) — misma tabla, mismo contrato."""

    __tablename__ = "approvals"

    id = Column(String(36), primary_key=True)  # uuid (hex) = gate_id
    kind = Column(String(40), index=True)      # "email_send" | "automation_action" | ...
    title = Column(String(200))
    summary = Column(Text)
    action_type = Column(String(40))           # clave del registro de ejecutores
    action_payload = Column(JSON)              # lo que se ejecuta al aprobar
    status = Column(String(20), default="pending", index=True)  # pending|approved|rejected|expired
    channel = Column(String(40))               # canal de origen para notificar
    target = Column(String(120))               # chat_id etc. (nullable)
    decision_id = Column(String(36))           # -> decisions.id (nullable)
    resolution_note = Column(Text)
    requested_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    expires_at = Column(DateTime)
