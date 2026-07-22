"""v10 mel benchmarks — mediciones reales de velocidad/calidad por modelo

[2026-07-22, petición del usuario] Tabla `mel_benchmarks`: una fila por
(provider, model) con la latencia MEDIDA (mediana de sondas estandarizadas) y
la calidad verificable (% de sondas deterministas superadas). La escriben las
sondas automáticas de `app/mel/benchmark.py` (al conectar un modelo y en el
catch-up de arranque); la consumen las políticas SPEED y BALANCED.

Aditiva e idempotente (patrón de la casa): no toca nada existente y no falla
si la tabla ya existe (create_all de dev).

Revision ID: b8d9e0f1a2b3
Revises: a7c8d9e0f1a2
Create Date: 2026-07-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8d9e0f1a2b3"
down_revision: Union[str, None] = "a7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    if _has_table("mel_benchmarks"):
        return
    op.create_table(
        "mel_benchmarks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=40), nullable=True),
        sa.Column("model", sa.String(length=160), nullable=True),
        sa.Column("ok", sa.Boolean(), nullable=True),
        sa.Column("latency_ms_median", sa.Integer(), nullable=True),
        sa.Column("speed_score", sa.Integer(), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("probes", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_mel_benchmarks_provider", "mel_benchmarks", ["provider"])
    op.create_index("ix_mel_benchmarks_model", "mel_benchmarks", ["model"])


def downgrade() -> None:
    if _has_table("mel_benchmarks"):
        op.drop_table("mel_benchmarks")
