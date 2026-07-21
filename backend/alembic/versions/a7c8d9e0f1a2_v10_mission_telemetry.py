"""v10 mission telemetry — tabla mission_events (observabilidad punta a punta)

[2026-07-21, doc 31] Un evento por hecho relevante del pipeline de Misiones
(intent/plan/nodo/llm_call/tool_call/gate/cierre) con timings y resultado.
Aditiva e idempotente (patrón M1/W1/A1).

Revision ID: a7c8d9e0f1a2
Revises: e6f7a8b9c0d1
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7c8d9e0f1a2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    if _has_table("mission_events"):
        return  # idempotente: ya creada (p.ej. por create_all en dev)
    op.create_table(
        "mission_events",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("mission_id", sa.String(), nullable=True, index=True),
        sa.Column("trace_id", sa.String(), nullable=True, index=True),
        sa.Column("ts", sa.DateTime(), nullable=True, index=True),
        sa.Column("stage", sa.String(), nullable=True, index=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("ok", sa.Boolean(), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    if _has_table("mission_events"):
        op.drop_table("mission_events")
