"""V1.0 (R2, Orquestador): orchestration_runs + jerarquía de trazas

Un mensaje del usuario puede contener VARIOS encargos independientes. El TIE
ejecuta UNA misión; el Orquestador reparte N y las supervisa. Esta migración
crea el registro de esa capa:

- `orchestration_runs`: el run (mensaje del usuario + sus objetivos + estado).
- `orchestrator_traces.run_id`: a qué run pertenece cada misión.
- `orchestrator_traces.parent_trace_id`: si la misión nació de descomponer otra
  demasiado amplia ("crea 15 canales" → una sub-misión por canal).

Aditiva e idempotente: comprueba antes de crear/añadir, así que es un no-op
sobre una BD donde `create_all` ya dejó la tabla, y un ADD real sobre una BD
existente con datos.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(inspector, table: str) -> set:
    if table not in inspector.get_table_names():
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "orchestration_runs" not in inspector.get_table_names():
        op.create_table(
            "orchestration_runs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_message", sa.Text(), nullable=True),
            sa.Column("objectives", sa.JSON(), nullable=True),
            sa.Column("state", sa.String(length=20), nullable=True),
            sa.Column("outcome", sa.Text(), nullable=True),
            sa.Column("channel", sa.String(length=40), nullable=True),
            sa.Column("source", sa.String(length=30), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_orchestration_runs_state", "orchestration_runs", ["state"])
        op.create_index("ix_orchestration_runs_created_at", "orchestration_runs", ["created_at"])

    # Jerarquía en las trazas del TIE. Referencias planas indexadas, SIN
    # ForeignKey — mismo criterio que el resto del proyecto (Milestone.project_id,
    # Agent.project_id, mel_overrides.project_id): la integridad la lleva el
    # código, y así el orden de creación de tablas nunca rompe el arranque.
    existentes = _columns(inspector, "orchestrator_traces")
    if existentes:
        if "run_id" not in existentes:
            op.add_column("orchestrator_traces", sa.Column("run_id", sa.String(length=36), nullable=True))
            op.create_index("ix_orchestrator_traces_run_id", "orchestrator_traces", ["run_id"])
        if "parent_trace_id" not in existentes:
            op.add_column("orchestrator_traces", sa.Column("parent_trace_id", sa.String(length=36), nullable=True))
            op.create_index("ix_orchestrator_traces_parent_trace_id", "orchestrator_traces", ["parent_trace_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existentes = _columns(inspector, "orchestrator_traces")
    if "parent_trace_id" in existentes:
        op.drop_index("ix_orchestrator_traces_parent_trace_id", table_name="orchestrator_traces")
        op.drop_column("orchestrator_traces", "parent_trace_id")
    if "run_id" in existentes:
        op.drop_index("ix_orchestrator_traces_run_id", table_name="orchestrator_traces")
        op.drop_column("orchestrator_traces", "run_id")

    if "orchestration_runs" in inspector.get_table_names():
        op.drop_index("ix_orchestration_runs_created_at", table_name="orchestration_runs")
        op.drop_index("ix_orchestration_runs_state", table_name="orchestration_runs")
        op.drop_table("orchestration_runs")
