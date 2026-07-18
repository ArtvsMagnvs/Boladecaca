"""v10 MEL — tabla mel_overrides (E2b, doc 22 §3·E2b)

Migración 22.ª. Esquema-primero: crea `mel_overrides`, el pin persistente de
modelo por proyecto (doc 19 §7b). Aditiva e idempotente (check-before-create).
Sin ForeignKey (project_id como Integer plano, patrón Milestone/Agent).

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-07-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("mel_overrides"):
        op.create_table(
            "mel_overrides",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("scope", sa.String(length=20)),
            sa.Column("project_id", sa.Integer()),
            sa.Column("capability", sa.String(length=20)),
            sa.Column("model_id", sa.String(length=160)),
            sa.Column("source", sa.String(length=30)),
            sa.Column("created_at", sa.DateTime()),
        )
        op.create_index("ix_mel_overrides_project_id", "mel_overrides", ["project_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("mel_overrides"):
        op.drop_table("mel_overrides")
