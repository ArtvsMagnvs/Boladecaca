"""v10 MEL — tabla mel_capability_reports (E1b, doc 22 §3·E1b)

Migración 21.ª. Esquema-primero (patrón M1/W1/A1/T1/E1): crea
`mel_capability_reports`, el informe auto-investigado por (proveedor, modelo,
capacidad) del Catálogo Auto-Investigado (doc 19 §5.4).

Aditiva e idempotente (check-before-create vía inspect). Sin ForeignKey.

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("mel_capability_reports"):
        op.create_table(
            "mel_capability_reports",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider", sa.String(length=40)),
            sa.Column("model", sa.String(length=120)),
            sa.Column("capability", sa.String(length=20)),
            sa.Column("score", sa.Integer()),
            sa.Column("rationale", sa.Text()),
            sa.Column("confidence", sa.String(length=10)),
            sa.Column("researched_by_model", sa.String(length=160)),
            sa.Column("created_at", sa.DateTime()),
        )
        op.create_index("ix_mel_capability_reports_provider", "mel_capability_reports", ["provider"])
        op.create_index("ix_mel_capability_reports_model", "mel_capability_reports", ["model"])
        op.create_index("ix_mel_capability_reports_capability", "mel_capability_reports", ["capability"])
        op.create_index("ix_mel_capability_reports_created_at", "mel_capability_reports", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("mel_capability_reports"):
        op.drop_table("mel_capability_reports")
