"""V1.1 L1 — LSL completa + cuarentena del Learner (2026-08-05)

Crea las TRES tablas del Learner (esquema-primero, patrón M1/W1/A1 — L1 usa
`skills`+`skill_events` de verdad; `learner_proposals` queda lista para que L2
escriba sin otra migración):

  · `skills`            — la Local Skill Library. FUENTE DE VERDAD SQL de las
                          skills (el stub de V0.85 vivía solo en ChromaDB;
                          el backfill mecánico corre en el arranque, no aquí:
                          alembic no ve ChromaDB y una migración de datos que
                          depende de otro almacén no es idempotente).
  · `skill_events`      — el "git log" de cada skill (doc 15 §6.2), con el
                          snapshot previo por transición → undo real.
  · `learner_proposals` — la cuarentena de la escalera de confianza (doc 15 §3).

IDEMPOTENTE por tabla: en una BD creada por `create_all` (SQLite de tests/dev)
ya existirán — se comprueba antes de crear. Modelos ORM en `app/learner/models.py`
(disciplina modular doc 16, mismo criterio que Milestone/automation).

LA LECCIÓN DE LAS 4 VECES (W1, W2c, A1, 2026-08-02): esta migración se escribe
en la MISMA sesión que los modelos, cubre TODO lo que el ORM declara (vigilado
por test_learner_lsl.py con el mismo invariante de test_migracion_columnas), y
hay que aplicarla al Postgres real (`alembic upgrade head`) ANTES de arrancar
el backend — check_schema_drift() avisará si se olvida.

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tablas() -> set:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existentes = _tablas()

    if "skills" not in existentes:
        op.create_table(
            "skills",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("name", sa.String(200), nullable=False, index=True),
            sa.Column("version", sa.String(32), nullable=False, server_default="1.0.0"),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("definition", sa.JSON(), nullable=False),
            sa.Column("input_schema", sa.JSON(), nullable=False),
            sa.Column("output_schema", sa.JSON(), nullable=False),
            sa.Column("runtime_agnostic", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by", sa.String(64), nullable=False, server_default="user"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_used", sa.DateTime(), nullable=True),
            sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(24), nullable=False, server_default="draft", index=True),
            sa.Column("quality_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("error_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("projects", sa.JSON(), nullable=False),
            sa.Column("tags", sa.JSON(), nullable=False),
            sa.Column("derived_from", sa.JSON(), nullable=False),
            sa.Column("superseded_by", sa.String(64), nullable=True),
            sa.Column("gsn_id", sa.String(64), nullable=True),
            sa.Column("gsn_version", sa.String(32), nullable=True),
            sa.Column("gsn_last_sync", sa.DateTime(), nullable=True),
        )

    if "skill_events" not in existentes:
        op.create_table(
            "skill_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("skill_id", sa.String(64), nullable=False, index=True),
            sa.Column("event", sa.String(32), nullable=False, index=True),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("actor", sa.String(24), nullable=False, server_default="learner"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if "learner_proposals" not in existentes:
        op.create_table(
            "learner_proposals",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("kind", sa.String(48), nullable=False, index=True),
            sa.Column("risk", sa.String(12), nullable=False, server_default="medium"),
            sa.Column("state", sa.String(24), nullable=False, server_default="observed", index=True),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("subject_id", sa.String(64), nullable=True, index=True),
            sa.Column("project_id", sa.Integer(), nullable=True, index=True),
            sa.Column("evidence", sa.JSON(), nullable=False),
            sa.Column("contradictions", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("decided_by", sa.String(24), nullable=True),
            sa.Column("decided_at", sa.DateTime(), nullable=True),
            sa.Column("decision_note", sa.Text(), nullable=True),
            sa.Column("applied_snapshot", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    existentes = _tablas()
    for tabla in ("learner_proposals", "skill_events", "skills"):
        if tabla in existentes:
            op.drop_table(tabla)
