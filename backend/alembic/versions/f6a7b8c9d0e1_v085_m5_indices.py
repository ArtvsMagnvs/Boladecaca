"""v085 M5 — indices de rendimiento (doc 12 A3)

Sprint M5 (PLAN_MAESTRO_2026 doc 07 §10, doc 12 A3): la auditoria encontro solo
3 columnas indexadas en toda la BD. Anade indice a las 8 columnas de filtro
frecuente identificadas: email_activity_log(action_type, read, timestamp),
email_triage(created_at), agent_executions(status), tasks(status),
calendar_events(start_date), chat_messages(created_at).

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (tabla, columna) -> nombre de indice. Mismo naming que op.f() generaria
# (ix_<tabla>_<columna>), para que autogenerate futuro no detecte drift.
_INDEXES = [
    ("email_activity_log", "action_type"),
    ("email_activity_log", "read"),
    ("email_activity_log", "timestamp"),
    ("email_triage", "created_at"),
    ("agent_executions", "status"),
    ("tasks", "status"),
    ("calendar_events", "start_date"),
    ("chat_messages", "created_at"),
]


def _index_name(table: str, column: str) -> str:
    return f"ix_{table}_{column}"


def upgrade() -> None:
    # Idempotente: si Base.metadata.create_all ya creo el indice (backend
    # arrancado antes de migrar, con el modelo ya actualizado), no-op.
    bind = op.get_bind()
    insp = sa.inspect(bind)

    for table, column in _INDEXES:
        if not insp.has_table(table):
            continue  # tabla no existe en esta BD (no deberia pasar, defensivo)
        existing = {ix["name"] for ix in insp.get_indexes(table)}
        name = _index_name(table, column)
        if name in existing:
            continue
        op.create_index(op.f(name), table, [column], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    for table, column in reversed(_INDEXES):
        if not insp.has_table(table):
            continue
        name = _index_name(table, column)
        existing = {ix["name"] for ix in insp.get_indexes(table)}
        if name not in existing:
            continue
        op.drop_index(op.f(name), table_name=table)
