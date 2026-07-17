"""v10 MEL — tablas mel_executions + mel_policies (E1, doc 22 §3·E1)

Migración 20.ª. Esquema-primero (patrón M1/W1/A1/T1): crea las 2 tablas del
Model Execution Layer. `mel_executions` = registro operativo de cada ejecución
(async, materia prima del Learning Engine v2). `mel_policies` = políticas
compiladas como JSON versionado (Economy/Quality/Offline).

Las tablas de E1b (`mel_capability_reports`) y E2b (`mel_overrides`) se crean en
sus propias migraciones (21.ª y 22.ª) — no se adelantan aquí (cada sprint su
esquema, para no crear tablas que un sprint no usa todavía).

Aditiva e idempotente (check-before-create vía inspect). Sin ForeignKey en las
referencias cross-tabla — mismo criterio que las migraciones 15-19.

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-07-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("mel_executions"):
        op.create_table(
            "mel_executions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("capability", sa.String(length=20)),
            sa.Column("provider", sa.String(length=40)),
            sa.Column("model", sa.String(length=120)),
            sa.Column("ok", sa.Boolean()),
            sa.Column("latency_ms", sa.Integer()),
            sa.Column("tokens", sa.Integer()),
            sa.Column("cost_estimate", sa.Float()),
            sa.Column("attempts", sa.Integer()),
            sa.Column("fallbacks_used", sa.Integer()),
            sa.Column("fallback_reason", sa.String(length=120)),
            sa.Column("decision_id", sa.String(length=36)),
            sa.Column("context_tags", sa.JSON()),
            sa.Column("created_at", sa.DateTime()),
        )
        op.create_index("ix_mel_executions_capability", "mel_executions", ["capability"])
        op.create_index("ix_mel_executions_ok", "mel_executions", ["ok"])
        op.create_index("ix_mel_executions_decision_id", "mel_executions", ["decision_id"])
        op.create_index("ix_mel_executions_created_at", "mel_executions", ["created_at"])

    if not insp.has_table("mel_policies"):
        op.create_table(
            "mel_policies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=20)),
            sa.Column("version", sa.Integer()),
            sa.Column("compiled", sa.JSON()),
            sa.Column("pristine", sa.Boolean()),
            sa.Column("is_active", sa.Boolean()),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        )
        op.create_index("ix_mel_policies_name", "mel_policies", ["name"])
        op.create_index("ix_mel_policies_is_active", "mel_policies", ["is_active"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("mel_policies"):
        op.drop_table("mel_policies")
    if insp.has_table("mel_executions"):
        op.drop_table("mel_executions")
