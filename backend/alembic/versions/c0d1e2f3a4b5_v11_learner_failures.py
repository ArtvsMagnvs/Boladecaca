"""V1.1 L2b — failure_stats + columnas de stats justas (2026-08-06)

Lo que añade la atribución de fallos (doc 27 §5, sesión L2b):

  · tabla `failure_stats`            — cuántas veces ha pasado cada tipo de
                                       fallo, de quién fue y en qué misiones
                                       mirarlo. Sobrevive a la purga de 30 días
                                       de `mission_events` (doc 31), que es
                                       justo lo que el análisis a largo plazo
                                       necesita.
  · `model_stats.missions_excused`   — misiones que acabaron mal por algo AJENO
                                       al modelo (red, cuota, config, cancelación
                                       del usuario). Salen del denominador de
                                       `mission_success_rate`.
  · `tool_stats.fails_external`      — lo mismo para las tools: un `getaddrinfo`
                                       dentro de `search` es la red, no la tool.

MIGRACIÓN NUEVA, no una edición de `b9c0d1e2f3a4`: Alembic identifica una
revisión por su ID en `alembic_version`, no por el contenido del archivo — si
el usuario ya aplicó L2, reescribir aquella no la reaplicaría (la lección del
2026-08-02, ya documentada en la cabecera de la propia b9c0d1e2f3a4).

IDEMPOTENTE en los dos caminos reales: tabla que ya existe (BD creada por
`create_all` en dev/tests) → no-op; columna que ya existe → no-op.

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c0d1e2f3a4b5"
down_revision: Union[str, None] = "b9c0d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector():
    return sa.inspect(op.get_bind())


def _columnas(tabla: str) -> set:
    insp = _inspector()
    if tabla not in set(insp.get_table_names()):
        return set()
    return {c["name"] for c in insp.get_columns(tabla)}


def upgrade() -> None:
    tablas = set(_inspector().get_table_names())

    if "failure_stats" not in tablas:
        op.create_table(
            "failure_stats",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("kind", sa.String(32), nullable=False, index=True),
            sa.Column("blame", sa.String(16), nullable=False, index=True),
            sa.Column("component", sa.String(120), nullable=False,
                      server_default="", index=True),
            sa.Column("model_key", sa.String(160), nullable=True),
            sa.Column("tool", sa.String(64), nullable=True),
            sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_seen", sa.DateTime(), nullable=True),
            sa.Column("sample_mission_ids", sa.JSON(), nullable=False),
            sa.Column("last_detail", sa.Text(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    if "missions_excused" not in _columnas("model_stats"):
        op.add_column("model_stats",
                      sa.Column("missions_excused", sa.Integer(), nullable=False,
                                server_default="0"))

    if "fails_external" not in _columnas("tool_stats"):
        op.add_column("tool_stats",
                      sa.Column("fails_external", sa.Integer(), nullable=False,
                                server_default="0"))


def downgrade() -> None:
    if "fails_external" in _columnas("tool_stats"):
        op.drop_column("tool_stats", "fails_external")
    if "missions_excused" in _columnas("model_stats"):
        op.drop_column("model_stats", "missions_excused")
    if "failure_stats" in set(_inspector().get_table_names()):
        op.drop_table("failure_stats")
