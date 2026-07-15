"""v09 Automation — esquema completo del Automation Engine (A1, doc 20 §3)

Migración 18.ª. Esquema-primero (patrón M1/W1): crea las 3 tablas de V0.9 por
adelantado + añade la columna de reanudación a agent_executions. En A1 sólo se
USA `approvals` (el ApprovalGate); `automation_rules`/`automation_executions`
quedan listas para el motor de A2b sin otra migración.

Aditiva e idempotente (check-before-create vía inspect). Sin ForeignKey en las
referencias cross-tabla (`rule_id`, `project_id`, `decision_id`) — mismo criterio
que las migraciones 15-17 del WPMS.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-07-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(insp, table: str) -> set:
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # --- approvals (el store del ApprovalGate) ---
    if not insp.has_table("approvals"):
        op.create_table(
            "approvals",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("kind", sa.String(length=40)),
            sa.Column("title", sa.String(length=200)),
            sa.Column("summary", sa.Text()),
            sa.Column("action_type", sa.String(length=40)),
            sa.Column("action_payload", sa.JSON()),
            sa.Column("status", sa.String(length=20)),
            sa.Column("channel", sa.String(length=40)),
            sa.Column("target", sa.String(length=120)),
            sa.Column("decision_id", sa.String(length=36)),
            sa.Column("resolution_note", sa.Text()),
            sa.Column("requested_at", sa.DateTime()),
            sa.Column("resolved_at", sa.DateTime()),
            sa.Column("expires_at", sa.DateTime()),
        )
        op.create_index("ix_approvals_kind", "approvals", ["kind"])
        op.create_index("ix_approvals_status", "approvals", ["status"])

    # --- automation_rules ---
    if not insp.has_table("automation_rules"):
        op.create_table(
            "automation_rules",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=120)),
            sa.Column("enabled", sa.Boolean()),
            sa.Column("trigger_type", sa.String(length=40)),
            sa.Column("trigger_config", sa.JSON()),
            sa.Column("condition_config", sa.JSON()),
            sa.Column("action_type", sa.String(length=40)),
            sa.Column("action_config", sa.JSON()),
            sa.Column("project_id", sa.Integer()),
            sa.Column("cooldown_s", sa.Integer()),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        )
        op.create_index("ix_automation_rules_enabled", "automation_rules", ["enabled"])
        op.create_index("ix_automation_rules_project_id", "automation_rules", ["project_id"])

    # --- automation_executions ---
    if not insp.has_table("automation_executions"):
        op.create_table(
            "automation_executions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("rule_id", sa.Integer()),
            sa.Column("trigger_source", sa.String(length=60)),
            sa.Column("event_key", sa.String(length=200)),
            sa.Column("status", sa.String(length=20)),
            sa.Column("result", sa.Text()),
            sa.Column("error", sa.Text()),
            sa.Column("checkpoint", sa.JSON()),
            sa.Column("duration_ms", sa.Integer()),
            sa.Column("approved", sa.Boolean()),
            sa.Column("created_at", sa.DateTime()),
        )
        op.create_index("ix_automation_executions_rule_id", "automation_executions", ["rule_id"])
        op.create_index("ix_automation_executions_event_key", "automation_executions", ["event_key"])
        op.create_index("ix_automation_executions_status", "automation_executions", ["status"])

    # --- agent_executions.checkpoint_data (columna nueva, aditiva) ---
    if "checkpoint_data" not in _existing_columns(insp, "agent_executions"):
        op.add_column("agent_executions", sa.Column("checkpoint_data", sa.JSON()))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "checkpoint_data" in _existing_columns(insp, "agent_executions"):
        op.drop_column("agent_executions", "checkpoint_data")
    if insp.has_table("automation_executions"):
        op.drop_table("automation_executions")
    if insp.has_table("automation_rules"):
        op.drop_table("automation_rules")
    if insp.has_table("approvals"):
        op.drop_table("approvals")
