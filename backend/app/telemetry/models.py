# app/telemetry/models.py — tabla de eventos de misión (observabilidad, 2026-07-21)
#
# UNA fila por hecho relevante del pipeline de Misiones (Orchestrator/TIE/MEL):
# intent, plan, nodo, llamada LLM, llamada a tool, gate, cierre. Con timings y
# resultado — la materia prima del ciclo revisión→test→mejora (doc 31).
#
# Diseño deliberado:
# - Append-only, sin FKs (mismo criterio laxo que orchestrator_traces): la
#   integridad la da el pipeline, no el esquema; los ids son strings de traza.
# - `detail` JSON pequeño (resúmenes, motivos) — NUNCA contenido del usuario
#   completo: esto es observabilidad, no un segundo historial de chat.
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String

from app.db.database import Base


class MissionEvent(Base):
    __tablename__ = "mission_events"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(String, index=True, nullable=True)   # None = llamada suelta (chat corto)
    trace_id = Column(String, index=True, nullable=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    # intent | plan | gate | node_end | tool_call | llm_call | responder |
    # mission_end | error
    stage = Column(String, index=True)
    # qué exactamente: capability ("chat"), "browser.click", node_id, etc.
    name = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    ok = Column(Boolean, nullable=True)
    detail = Column(JSON, nullable=True)
