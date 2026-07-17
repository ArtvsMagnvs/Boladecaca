# app/mel/models.py — Modelos del Model Execution Layer (V1.0, doc 19 §9.1/§5.2)
#
# Esquema-primero (patrón M1/W1/A1/T1): la migración 20.ª crea las 2 tablas del
# MEL v1 por adelantado. `mel_executions` es el registro operativo (una fila por
# ejecución, escrita async fuera del hot path) — materia prima del Learning
# Engine (v2, doc 19 §9.2). `mel_policies` guarda las políticas compiladas como
# JSON versionado (doc 19 §5.2).
#
# Disciplina modular (doc 16): estos modelos viven en `app.mel` (igual que
# `Milestone` en `app.workspace.models` o `Approval` en `app.automation.models`),
# se exportan por el __init__ y NADIE de fuera importa este archivo directamente.
# Base viene de app.db.database (metadata compartida → create_all los crea).
#
# Referencias cross-tabla (`project_id`, `decision_id`) como columnas planas
# indexadas, NO ForeignKey: mismo criterio del resto del proyecto.
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text

from app.db.database import Base


class MelExecution(Base):
    """Auditoría de cada ejecución REAL del MEL (async, fuera del hot path — un
    fallo aquí nunca afecta a la respuesta). Es el registro del que el Learning
    Engine (v2) aprende qué modelos funcionan mejor por capacidad. Comparte
    semántica con `model_stats` del Learner (doc 19 §9.2): aquí las señales
    OPERATIVAS (éxito técnico, latencia, coste, reintentos)."""

    __tablename__ = "mel_executions"

    id = Column(Integer, primary_key=True)
    capability = Column(String(20), index=True)      # "chat" | "reason" | ...
    provider = Column(String(40))
    model = Column(String(120))
    ok = Column(Boolean, index=True)
    latency_ms = Column(Integer)
    tokens = Column(Integer)
    cost_estimate = Column(Float)
    attempts = Column(Integer, default=1)            # candidatos intentados
    fallbacks_used = Column(Integer, default=0)      # saltos de cadena
    fallback_reason = Column(String(120))            # clasificación del último fallo, si hubo
    decision_id = Column(String(36), index=True)     # -> DecisionTrace (ring buffer/muestreo)
    context_tags = Column(JSON)                      # dominio/proyecto/origen (métrica, no selección)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class MelCapabilityReport(Base):
    """[E1b, doc 19 §5.4] Informe auto-investigado de un (provider, model) para
    UNA capacidad. Lo genera `research.py` al conectar/cambiar un modelo, y se
    re-genera cada `MEL_RESEARCH_REFRESH_DAYS`. `confidence` es la honestidad
    del propio modelo investigador sobre lo bien que conoce a ese modelo
    concreto — un informe "bajo" NO desplaza el catálogo curado (doc 19 §5.4.3).
    Varias filas por (provider, model): una por capacidad investigada."""

    __tablename__ = "mel_capability_reports"

    id = Column(Integer, primary_key=True)
    provider = Column(String(40), index=True)
    model = Column(String(120), index=True)
    capability = Column(String(20), index=True)
    score = Column(Integer)                    # 0-100
    rationale = Column(Text)                   # justificación de 1 línea
    confidence = Column(String(10))            # "alto" | "medio" | "bajo"
    researched_by_model = Column(String(160))  # provider:model que hizo la investigación
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class MelPolicy(Base):
    """Una política compilada (doc 19 §5.2), como JSON versionado. `name` ∈
    economy|quality|offline|custom. `compiled` = {capability → [model_key...]}
    (la cadena ordenada). `pristine=True` mientras el usuario no la edite — el
    compilador puede actualizarla en silencio; editada → solo con propuesta
    (doc 19 §5.3). `is_active` marca la política vigente (una sola)."""

    __tablename__ = "mel_policies"

    id = Column(Integer, primary_key=True)
    name = Column(String(20), index=True)            # economy|quality|offline|custom
    version = Column(Integer, default=1)
    compiled = Column(JSON)                           # {capability: [model_key, ...]}
    pristine = Column(Boolean, default=True)          # ¿sin editar por el usuario?
    is_active = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
