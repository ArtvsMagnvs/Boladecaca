"""Rastro de actividad en las ejecuciones de agente (2026-08-02)

El chat del ORQUESTADOR de un proyecto no usa SSE: lanza la mision con
POST /api/agents/{id}/execute y sondea `agent_executions`. Para que ahi se vea
lo mismo que en el chat principal (las frases cortas de lo que Aithera va
haciendo), el rastro tiene que estar persistido en la propia fila.

ADITIVA e IDEMPOTENTE: solo anade una columna de texto anulable. Se comprueba
antes si existe, porque en una BD creada por `create_all` (SQLite de desarrollo,
tests) la columna ya estara ahi y un ADD a secas fallaria.

Revision ID: d1e2f3a4b5c6
Revises: c9e0f1a2b3c4
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c9e0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "agent_executions"
_COLUMN = "progress"


def _tiene_columna() -> bool:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns(_TABLE)}
    return _COLUMN in cols


def upgrade() -> None:
    if not _tiene_columna():
        op.add_column(_TABLE, sa.Column(_COLUMN, sa.Text(), nullable=True))


def downgrade() -> None:
    if _tiene_columna():
        op.drop_column(_TABLE, _COLUMN)
