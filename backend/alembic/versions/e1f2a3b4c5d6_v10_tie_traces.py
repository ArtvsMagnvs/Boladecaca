"""v10 TIE — tabla orchestrator_traces (T1, doc 21 §3·T1)

Migración 19.ª. Esquema-primero (patrón M1/W1/A1): crea `orchestrator_traces`,
el estado operativo del Task Intelligence Engine. En T1 se usan las columnas de
identidad/intent/estado; `plan`/`steps`/`outcome`/`decision_id` quedan listas
para T2-T4 sin otra migración.

CORRIGE el supuesto de doc 11-B (§B.1 la daba por "ya prevista"): la tabla NO
existía en el modelo real — se crea aquí por primera vez.

Aditiva e idempotente (check-before-create vía inspect). Sin ForeignKey en las
referencias cross-tabla (`mission_id`, `decision_id`) — mismo criterio que las
migraciones 15-18.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("orchestrator_traces"):
        op.create_table(
            "orchestrator_traces",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("mission_id", sa.String(length=36)),
            sa.Column("channel", sa.String(length=40)),
            sa.Column("intent", sa.JSON()),
            sa.Column("model_used", sa.String(length=80)),
            sa.Column("plan", sa.JSON()),
            sa.Column("context_query_id", sa.String(length=36)),
            sa.Column("decision_id", sa.String(length=36)),
            sa.Column("steps", sa.JSON()),
            sa.Column("result", sa.Text()),
            sa.Column("outcome", sa.Text()),
            sa.Column("state", sa.String(length=20)),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        )
        op.create_index("ix_orchestrator_traces_mission_id", "orchestrator_traces", ["mission_id"])
        op.create_index("ix_orchestrator_traces_decision_id", "orchestrator_traces", ["decision_id"])
        op.create_index("ix_orchestrator_traces_state", "orchestrator_traces", ["state"])
        op.create_index("ix_orchestrator_traces_created_at", "orchestrator_traces", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("orchestrator_traces"):
        op.drop_table("orchestrator_traces")
