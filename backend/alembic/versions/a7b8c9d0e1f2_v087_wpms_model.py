"""v087 WPMS W1 — modelo Workspace/Project Management (doc 18)

Sprint W1 (PLAN_MAESTRO_2026 doc 18): extension ADITIVA del modelo real
Project/Task (evolucion, no reescritura) + entidad nueva `milestones` (el eje de
version). NUNCA hace DROP: las rutas /api/projects y /api/tasks siguen por
contrato. Idempotente (comprueba tabla/columna/indice antes de crear) para
tolerar una BD donde Base.metadata.create_all ya haya creado el esquema nuevo.

- milestones: tabla nueva (id, project_id, name, version, description, status,
  target_date, order_index, created_at, completed_at, updated_at).
- projects +=: repo_path, current_version, target_version, start_date, tags(JSON),
  docs(JSON), archived_at.
- tasks +=: milestone_id(ix), checklist(JSON), depends_on(JSON), estimate,
  order_index, closed_at, links(JSON).

Nota sobre milestone_id: se anade como INTEGER simple (sin constraint FK a nivel
de ALTER, que SQLite no soporta bien sin table-rebuild). El modelo ORM declara la
ForeignKey (la respeta create_all en BD nuevas y Postgres); la integridad a nivel
app (nullar tareas al borrar su milestone) la maneja el endpoint DELETE. Mismo
criterio laxo de FK que el resto del esquema (p.ej. Conversation.agent_id).

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Fabricas de columnas (funciones, no instancias): op.add_column consume la
# Column y la "adjunta"; construir una fresca por uso evita el error de reusar
# una misma instancia entre upgrade/downgrade o entre corridas. JSON -> TEXT en
# SQLite (ok). server_default="0" para no dejar NULL en filas existentes.
def _project_columns():
    return [
        sa.Column("repo_path", sa.String(length=500)),
        sa.Column("current_version", sa.String(length=40)),
        sa.Column("target_version", sa.String(length=40)),
        sa.Column("start_date", sa.DateTime()),
        sa.Column("tags", sa.JSON()),
        sa.Column("docs", sa.JSON()),
        sa.Column("archived_at", sa.DateTime()),
    ]


def _task_columns():
    return [
        sa.Column("milestone_id", sa.Integer()),
        sa.Column("checklist", sa.JSON()),
        sa.Column("depends_on", sa.JSON()),
        sa.Column("estimate", sa.String(length=40)),
        sa.Column("order_index", sa.Integer(), server_default="0"),
        sa.Column("closed_at", sa.DateTime()),
        sa.Column("links", sa.JSON()),
    ]


# (tabla, columna) -> ix_<tabla>_<columna> (mismo naming que op.f()/create_all).
_INDEXES = [
    ("tasks", "milestone_id"),
    ("milestones", "project_id"),
    ("milestones", "status"),
]


def _index_name(table: str, column: str) -> str:
    return f"ix_{table}_{column}"


def _existing_columns(insp, table: str) -> set:
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _add_columns(insp, table: str, columns) -> None:
    existing = _existing_columns(insp, table)
    for col in columns:
        if col.name in existing:
            continue
        op.add_column(table, col)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1) tabla milestones (si no existe)
    if not insp.has_table("milestones"):
        op.create_table(
            "milestones",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(length=120), nullable=True),
            sa.Column("version", sa.String(length=40), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), server_default="planned", nullable=True),
            sa.Column("target_date", sa.DateTime(), nullable=True),
            sa.Column("order_index", sa.Integer(), server_default="0", nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    # 2) columnas aditivas en projects y tasks
    _add_columns(insp, "projects", _project_columns())
    _add_columns(insp, "tasks", _task_columns())

    # 3) indices (re-inspeccionar: milestones puede acabar de crearse)
    insp = sa.inspect(bind)
    for table, column in _INDEXES:
        if not insp.has_table(table):
            continue
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
        if name in {ix["name"] for ix in insp.get_indexes(table)}:
            op.drop_index(op.f(name), table_name=table)

    task_cols = _existing_columns(insp, "tasks")
    for col in reversed(_task_columns()):
        if col.name in task_cols:
            op.drop_column("tasks", col.name)
    proj_cols = _existing_columns(insp, "projects")
    for col in reversed(_project_columns()):
        if col.name in proj_cols:
            op.drop_column("projects", col.name)

    if insp.has_table("milestones"):
        op.drop_table("milestones")
