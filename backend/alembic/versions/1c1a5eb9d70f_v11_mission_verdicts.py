"""V1.1 LC1 — mission_verdicts: el veredicto del juez (2026-08-07)

La tabla que faltaba. Hasta ahora el aprendizaje usaba
`orchestrator_traces.state` como señal de éxito, y ese campo significa "la
maquinaria terminó sin colgarse" — no "al usuario le sirvió". Con ese criterio
el Learner proponía convertir en procedimientos fijos ocho intentos FALLIDOS
del mismo encargo (post-mortem completo en doc 41 §0).

`mission_verdicts` guarda el dictamen de un JUEZ (capacidad LEARN, un modelo
que NO ejecutó la misión) sobre si sirvió, con las señales que citó para
sostenerlo. Desde LC2, la escalera de confianza solo aceptará evidencia
respaldada por una fila de aquí.

MIGRACIÓN NUEVA encadenada tras `c0d1e2f3a4b5` (L2b) — jamás editar una ya
aplicada (la lección del 2026-08-02). IDEMPOTENTE: en una BD creada por
`create_all` la tabla ya existirá.

NOTA sobre el ID: la primera versión de esta migración usaba `d1e2f3a4b5c6`,
que YA estaba cogido por `d1e2f3a4b5c6_rastro_actividad_ejecuciones.py`. Alembic
identifica las revisiones por id, así que duplicarlo rompe el grafo entero
("Multiple revisions with id"). Los ids "bonitos" tipo a1b2c3… se agotan
rápido en un proyecto con 34 migraciones; de ahí este, aleatorio.

Revision ID: 1c1a5eb9d70f
Revises: c0d1e2f3a4b5
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "1c1a5eb9d70f"
down_revision: Union[str, None] = "c0d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tablas() -> set:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "mission_verdicts" in _tablas():
        return
    op.create_table(
        "mission_verdicts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("mission_id", sa.String(64), nullable=False, index=True),
        sa.Column("trace_id", sa.String(64), nullable=True, index=True),
        sa.Column("origin", sa.String(16), nullable=False,
                  server_default="user", index=True),
        sa.Column("verdict", sa.String(16), nullable=False, index=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reasons", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("signals", sa.JSON(), nullable=False),
        sa.Column("lesson", sa.JSON(), nullable=True),
        sa.Column("judge_model", sa.String(160), nullable=True),
        sa.Column("judge_bias", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.Column("superseded_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
    )


def downgrade() -> None:
    if "mission_verdicts" in _tablas():
        op.drop_table("mission_verdicts")
