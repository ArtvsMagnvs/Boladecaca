"""v10 mel benchmark tasks — resultados de tareas agentic reales por modelo

[2026-07-22, petición del usuario] Columna `tasks` (JSON) en `mel_benchmarks`:
por modelo, el resultado VERIFICADO de escenarios de tareas reales con tools
(crear/editar archivos, código ejecutado, documentos, web, búsqueda, memoria)
— éxito, duración, iteraciones del bucle. Lo escribe
scripts/model_task_bench.py. Aditiva e idempotente.

Revision ID: c9e0f1a2b3c4
Revises: b8d9e0f1a2b3
Create Date: 2026-07-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9e0f1a2b3c4"
down_revision: Union[str, None] = "b8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    if not _has_column("mel_benchmarks", "tasks"):
        op.add_column("mel_benchmarks", sa.Column("tasks", sa.JSON(), nullable=True))


def downgrade() -> None:
    if _has_column("mel_benchmarks", "tasks"):
        op.drop_column("mel_benchmarks", "tasks")
