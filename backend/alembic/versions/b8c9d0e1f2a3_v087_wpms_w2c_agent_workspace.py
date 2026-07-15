"""v087 WPMS W2c — Agent gana project_id/skills/icon (doc 18 lienzo)

Sprint W2c (PLAN_MAESTRO_2026 doc 18, revision 15-jul con las tarjetas de
agente): extension ADITIVA de `agents` para que un agente pueda pertenecer a
un proyecto y mostrarse en su tarjeta.

- agents.project_id: Integer plano + indice, NO ForeignKey. Se intento como FK
  real primero (Agent y Project viven en el mismo archivo, sin problema de
  orden de registro) pero fallo en pruebas reales: SQLite no soporta anadir
  una columna con constraint FK via ALTER TABLE ADD COLUMN fuera de "batch
  mode" (NotImplementedError de SQLAlchemy). Mismo criterio laxo que
  Milestone/Task.milestone_id en la migracion 15.a, por un motivo distinto
  pero igual de real — integridad a nivel app.
- agents.skills: JSON list[str] — tags simples que teclea el usuario. NO es
  el sistema LSL de doc 09 (derivacion automatica, linaje, versionado) — eso
  sigue siendo un stub sin construir hasta V1.1.
- agents.icon: String corto (un emoji) — NO subida de imagen (necesitaria
  almacenamiento de ficheros nuevo, fuera de alcance).

Idempotente (comprueba columna/indice antes de crear) para tolerar una BD
donde Base.metadata.create_all ya haya creado el esquema nuevo.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _agent_columns():
    return [
        sa.Column("project_id", sa.Integer()),
        sa.Column("skills", sa.JSON()),
        sa.Column("icon", sa.String(length=16)),
    ]


def _existing_columns(insp, table: str) -> set:
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _index_name(table: str, column: str) -> str:
    return f"ix_{table}_{column}"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    existing = _existing_columns(insp, "agents")
    for col in _agent_columns():
        if col.name in existing:
            continue
        op.add_column("agents", col)

    insp = sa.inspect(bind)
    existing_indexes = {ix["name"] for ix in insp.get_indexes("agents")}
    name = _index_name("agents", "project_id")
    if name not in existing_indexes:
        op.create_index(op.f(name), "agents", ["project_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    existing_indexes = {ix["name"] for ix in insp.get_indexes("agents")}
    name = _index_name("agents", "project_id")
    if name in existing_indexes:
        op.drop_index(op.f(name), table_name="agents")

    existing = _existing_columns(insp, "agents")
    for col in reversed(_agent_columns()):
        if col.name in existing:
            op.drop_column("agents", col.name)
