# app/learner/models.py — Modelos SQL del Learner (V1.1 L1, docs 09 §1.1 + 15 §3/§6)
#
# TRES tablas, esquema-primero (patrón M1/W1/A1: la migración 25.ª las crea por
# adelantado; L1 usa `skills`+`skill_events` de verdad y deja `learner_proposals`
# lista para que L2 escriba sin otra migración):
#
#   · `skills`            — la LSL. FUENTE DE VERDAD de las skills (hasta hoy el
#                           stub de V0.85 vivía solo en ChromaDB/mem_skill; desde
#                           L1, SQL manda y mem_skill queda como espejo semántico
#                           de búsqueda — exactamente el patrón `decisions`/
#                           `mem_decision` de decision_service).
#   · `skill_events`      — el "git log" de cada skill (doc 15 §6.2). Cada
#                           transición guarda el estado PREVIO en su payload:
#                           es lo que hace el undo posible sin una tabla extra.
#   · `learner_proposals` — la CUARENTENA (doc 15 §3): todo aprendizaje que NO
#                           es una skill (preferencias, pins, reglas sugeridas,
#                           operaciones de evolución) camina aquí la escalera de
#                           confianza. Las skills NO usan esta tabla: su propio
#                           `status` ES su escalera (mapeo documentado en
#                           ladder.py) — dos maquinarias para el mismo camino
#                           sería frameworkitis (doc 16).
#
# Disciplina modular (doc 16): estos modelos viven en `app.learner` (igual que
# `Milestone` en app.workspace.models y las tablas del AE en app.automation.
# models), se exportan por el __init__ y NADIE de fuera importa este archivo.
# Referencias cross-tabla (`skill_id` en events, `subject_id` en proposals) como
# columnas planas indexadas, NO ForeignKey — mismo criterio de todo el proyecto
# (init_db corre create_all al importar; la integridad la lleva el servicio).
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text

from app.db.database import Base


class Skill(Base):
    """Espejo SQL 1:1 del contrato congelado `LocalSkill` (memory/interfaces.py,
    doc 09 §1.1). Mismos nombres de campo a propósito: la conversión
    fila↔dataclass de library.py es mecánica y un campo nuevo en el contrato
    grita aquí en vez de perderse en un mapeo con renombres."""

    __tablename__ = "skills"

    id = Column(String(64), primary_key=True)              # UUID
    name = Column(String(200), nullable=False, index=True)
    version = Column(String(32), nullable=False, default="1.0.0")
    description = Column(Text, nullable=False, default="")
    definition = Column(JSON, nullable=False, default=dict)
    input_schema = Column(JSON, nullable=False, default=dict)
    output_schema = Column(JSON, nullable=False, default=dict)
    runtime_agnostic = Column(Boolean, nullable=False, default=True)

    # Provenance (idéntico al de la GSN, doc 08 RFC-004)
    created_by = Column(String(64), nullable=False, default="user")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    evidence_count = Column(Integer, nullable=False, default=0)
    last_used = Column(DateTime, nullable=True)
    use_count = Column(Integer, nullable=False, default=0)

    # Calidad (las alimenta el LLL — análisis 4, L3)
    status = Column(String(24), nullable=False, default="draft", index=True)
    quality_score = Column(Float, nullable=False, default=0.0)
    error_rate = Column(Float, nullable=False, default=0.0)

    # Contexto
    projects = Column(JSON, nullable=False, default=list)
    tags = Column(JSON, nullable=False, default=list)

    # Linaje [Δ doc 14 §4.1 / doc 15 §6]
    derived_from = Column(JSON, nullable=False, default=list)
    superseded_by = Column(String(64), nullable=True)

    # Sincronización GSN (V2.0+; NULL hasta entonces)
    gsn_id = Column(String(64), nullable=True)
    gsn_version = Column(String(32), nullable=True)
    gsn_last_sync = Column(DateTime, nullable=True)


class SkillEvent(Base):
    """Historial de una skill — doc 15 §6.2 LITERAL:
    `id, skill_id (ix), event, payload JSON, actor, created_at`.

    `event` ∈ created|validated|improved|merged|split|deprecated|executed_ok|
    executed_fail (los 8 del doc) + `reverted` (necesario para el contrato de
    producto "undo restaura el estado anterior": el undo también es historia,
    nunca una goma de borrar). `actor` ∈ learner|user|runtime.

    El payload de toda transición de estado lleva `{"prior": {...}}` — el
    snapshot completo de la skill ANTES del cambio. Es la fuente del undo, de
    las métricas del panel (L4) y del provenance real que la GSN exigirá
    (V2.0+). Se guarda entero y no un diff a propósito: un diff exige aplicar
    la cadena entera para reconstruir; un snapshot restaura en una operación y
    no puede corromperse por un eslabón perdido."""

    __tablename__ = "skill_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_id = Column(String(64), nullable=False, index=True)
    event = Column(String(32), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    actor = Column(String(24), nullable=False, default="learner")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ModelStat(Base):
    """[V1.1 L2] Qué modelo funciona mejor, medido a nivel de MISIÓN.

    LA DISTINCIÓN QUE JUSTIFICA ESTA TABLA (doc 19 §9.2): `mel_executions` ya
    registra las señales OPERATIVAS de cada llamada — 200 OK, latencia, coste.
    Pero un modelo puede devolver 200 OK y producir una respuesta inútil: la
    llamada fue un éxito y la MISIÓN un fracaso. Esto agrega lo otro: de las
    misiones en las que participó este modelo, ¿cuántas acabaron sirviendo para
    algo? Es la señal que el Model Router necesita en V1.2, y la que ninguna
    métrica de transporte puede dar.

    Una fila por (capability, provider, model). Se actualiza incrementalmente
    tras cada misión — nunca se recalcula desde cero (la telemetría se purga a
    los 30 días; estas medias tienen que sobrevivir a esa purga)."""

    __tablename__ = "model_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    capability = Column(String(24), nullable=False, index=True)
    provider = Column(String(40), nullable=False)
    model = Column(String(120), nullable=False, index=True)

    missions = Column(Integer, nullable=False, default=0)       # misiones en las que participó
    missions_ok = Column(Integer, nullable=False, default=0)    # ...y acabaron bien
    # [L2b] ...y las que acabaron mal por algo AJENO al modelo (red caída,
    # cuota agotada, una API sin habilitar, el usuario cancelando). Salen del
    # DENOMINADOR: castigar a un modelo por un timeout de DNS es medir mal, y
    # con el tiempo el Model Router de V1.2 tomaría decisiones sobre ruido.
    missions_excused = Column(Integer, nullable=False, default=0)
    calls = Column(Integer, nullable=False, default=0)          # llamadas totales
    call_fails = Column(Integer, nullable=False, default=0)
    total_ms = Column(Integer, nullable=False, default=0)
    slowest_ms = Column(Integer, nullable=False, default=0)
    last_used = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ToolStat(Base):
    """[V1.1 L2] Qué herramientas fallan y en qué misiones (doc 15 §4,
    `tool_stats`). Alimenta el análisis 2 del LLL (patrones de error, L3) y,
    más adelante, la elección de herramienta del planner."""

    __tablename__ = "tool_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tool = Column(String(64), nullable=False, index=True)

    missions = Column(Integer, nullable=False, default=0)
    calls = Column(Integer, nullable=False, default=0)
    fails = Column(Integer, nullable=False, default=0)
    # [L2b] De esos fallos, los que NO son culpa de la tool: un `getaddrinfo`
    # dentro de `search` es la red, no la herramienta. `error_rate` los resta.
    fails_external = Column(Integer, nullable=False, default=0)
    total_ms = Column(Integer, nullable=False, default=0)
    last_used = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class FailureStat(Base):
    """[V1.1 L2b, doc 27 §5] Cuántas veces ha pasado cada tipo de fallo, de
    quién fue, y en qué misiones mirarlo.

    Por qué una tabla y no una consulta sobre `mission_events`: la telemetría se
    PURGA a los 30 días (doc 31) y el análisis de patrones necesita ver
    tendencias más largas — "esto lleva fallando desde marzo" es justo el tipo
    de hallazgo que se pierde con una ventana corta. Mismo criterio incremental
    que `model_stats`.

    `component` es el eje que hace accionable el dato: `tie` / `mel` /
    `orchestrator` / `tool:<id>` / `model:<provider:model>` / `email`… — sin él
    solo se sabría QUÉ falla, nunca DÓNDE.

    `sample_mission_ids` es un ring de 10: suficiente para que el panel (L4)
    enlace a misiones reales y el usuario compruebe por sí mismo, y acotado para
    que la fila no crezca sin límite."""

    __tablename__ = "failure_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kind = Column(String(32), nullable=False, index=True)      # FailureKind
    blame = Column(String(16), nullable=False, index=True)     # external|config|model|tool|aithera|none|unknown
    component = Column(String(120), nullable=False, default="", index=True)
    model_key = Column(String(160), nullable=True)             # "provider:model" si aplica
    tool = Column(String(64), nullable=True)

    count = Column(Integer, nullable=False, default=0)
    last_seen = Column(DateTime, nullable=True)
    sample_mission_ids = Column(JSON, nullable=False, default=list)
    last_detail = Column(Text, nullable=True)                  # el mensaje real, recortado
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class LearnerProposal(Base):
    """La cuarentena (doc 15 §3) para el aprendizaje NO-skill: preferencias
    observadas, pins, propuestas de regla, operaciones de evolución de skills
    (improve/merge/split — V1.2). L1 crea la tabla y las reglas de la escalera
    (ladder.py); L2 (Mission Learning) escribe las primeras filas reales.

    `state` camina la escalera de doc 15 §3.1:
        observed → candidate → proposed → validated → consolidated
    con terminales `rejected` (el usuario dijo no — SE REGISTRA: el Learner
    aprende de los "no", L4) y `reverted` (estaba consolidada y el usuario la
    deshizo). `risk` ∈ low|medium|high decide la RUTA de validación (§3.2) —
    la implementa ladder.py, nunca el llamador.

    `evidence` es una lista de evidencias con SEÑAL EXTERNA obligatoria
    (§3.3 anti-contaminación): cada una con kind/context_key/payload. "El LLM
    dijo que salió bien" NO es una evidencia válida y ladder.py la rechaza.

    `applied_snapshot` guarda el estado del mundo ANTES de consolidar (lo que
    el applier reporta haber cambiado) — la otra mitad del contrato de undo."""

    __tablename__ = "learner_proposals"

    id = Column(String(64), primary_key=True)              # UUID
    kind = Column(String(48), nullable=False, index=True)  # skill_new|skill_improve|rule|pin|preference|forget|...
    risk = Column(String(12), nullable=False, default="medium")
    state = Column(String(24), nullable=False, default="observed", index=True)

    title = Column(String(300), nullable=False)
    summary = Column(Text, nullable=False, default="")
    payload = Column(JSON, nullable=False, default=dict)     # el cambio propuesto, autocontenido
    subject_id = Column(String(64), nullable=True, index=True)  # p.ej. skill_id si mejora una existente
    project_id = Column(Integer, nullable=True, index=True)

    evidence = Column(JSON, nullable=False, default=list)
    contradictions = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    decided_by = Column(String(24), nullable=True)           # user|auto
    decided_at = Column(DateTime, nullable=True)
    decision_note = Column(Text, nullable=True)

    applied_snapshot = Column(JSON, nullable=True)
