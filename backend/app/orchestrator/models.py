# app/orchestrator/models.py — persistencia del Orquestador (R2)
#
# Esquema-primero (patrón M1/W1/A1/T1/E1): la migración 24.ª crea la tabla por
# adelantado. Un run se ACTUALIZA en cada transición de objetivo (checkpoint),
# igual que el executor del TIE hace con su grafo: reiniciar el backend a mitad
# de una orquestación no pierde el trabajo ya hecho.
#
# Disciplina modular (doc 16): este modelo vive en `app.orchestrator` (igual que
# `Milestone` en `app.workspace.models`, `Approval` en `app.automation.models` o
# `MelPolicy` en `app.mel.models`), y NADIE de fuera lo importa directamente.
# Base viene de app.db.database → `create_all` lo crea en entornos nuevos.
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text

from app.db.database import Base


class OrchestrationRunRow(Base):
    """Un mensaje del usuario y todas las misiones que generó.

    `objectives` guarda la lista serializada de `Objective` (con su estado,
    dependencias y la misión que lo resolvió). Se persiste entera en cada
    transición: son pocos objetivos por run (unidades), así que reescribir el
    JSON es más simple y más barato que una tabla hija — y deja el run
    consultable de un solo golpe.
    """

    __tablename__ = "orchestration_runs"

    id = Column(String(36), primary_key=True)        # UUID hex
    user_message = Column(Text)                      # lo que pidió el usuario, literal
    objectives = Column(JSON)                        # [Objective.to_dict(), ...]
    state = Column(String(20), index=True, default="running")  # running|done|failed|cancelled
    outcome = Column(Text)                           # la respuesta consolidada final
    channel = Column(String(40))                     # canal de origen (para responder por él)
    source = Column(String(30), default="user")      # user|automation|workspace
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
    duration_ms = Column(Integer)                    # medido al cerrar el run
