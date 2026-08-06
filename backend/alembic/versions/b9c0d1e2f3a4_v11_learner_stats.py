"""V1.1 L2 — model_stats + tool_stats (Mission Learning) (2026-08-05)

Las dos tablas que Mission Learning agrega tras cada misión:

  · `model_stats` — qué modelo funciona mejor medido a nivel de MISIÓN (doc 19
                    §9.2). `mel_executions` ya tiene lo OPERATIVO (200 OK,
                    latencia, coste); esto tiene lo otro: de las misiones en
                    las que participó, cuántas acabaron sirviendo. Un modelo
                    puede devolver 200 OK y una respuesta inútil.
  · `tool_stats`  — qué herramientas fallan y en qué misiones (doc 15 §4).

MIGRACIÓN SEPARADA de `a8b9c0d1e2f3` (L1) a propósito, aunque sean del mismo
bloque y de la misma tarde: si el usuario ya aplicó L1 en su Postgres, editar
aquella no la reaplicaría (Alembic identifica una revisión por su ID en
`alembic_version`, no por el contenido del archivo — la lección del 2026-08-02).
Añadir algo después del hecho es SIEMPRE una migración nueva.

IDEMPOTENTE por tabla: en una BD creada por `create_all` ya existirán.

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b9c0d1e2f3a4"
down_revision: Union[str, None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tablas() -> set:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existentes = _tablas()

    if "model_stats" not in existentes:
        op.create_table(
            "model_stats",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("capability", sa.String(24), nullable=False, index=True),
            sa.Column("provider", sa.String(40), nullable=False),
            sa.Column("model", sa.String(120), nullable=False, index=True),
            sa.Column("missions", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("missions_ok", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("calls", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("call_fails", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("slowest_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_used", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    if "tool_stats" not in existentes:
        op.create_table(
            "tool_stats",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tool", sa.String(64), nullable=False, index=True),
            sa.Column("missions", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("calls", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("fails", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_used", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )


def downgrade() -> None:
    existentes = _tablas()
    for tabla in ("tool_stats", "model_stats"):
        if tabla in existentes:
            op.drop_table(tabla)
