"""v085 MOS skeleton — tablas memory_job_runs y decisions

Sprint M1 (PLAN_MAESTRO_2026 doc 07 §5): la columna vertebral SQL del Memory
Operating System.
  - memory_job_runs: tracking de los jobs de memoria (ingesta M2, summarizer M3,
    lifecycle). Una fila por pasada; checkpoint JSON para reanudar (idempotencia).
  - decisions: Decision Memory (fuente de verdad SQL, espejo en mem_decision).
    Incluye la columna mission_id [Δ doc 14 §4.1] que enlaza planes/reflexiones
    del TIE (V1.0) a una mision, sin migracion nueva despues.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotente: el lifespan del backend hace Base.metadata.create_all al
    # arrancar, asi que las tablas pueden existir ya. En ese caso, no-op.
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table('memory_job_runs'):
        op.create_table(
            'memory_job_runs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('job_name', sa.String(length=80), nullable=False),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('finished_at', sa.DateTime(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='running'),
            sa.Column('items_processed', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('error_detail', sa.Text(), nullable=True),
            sa.Column('checkpoint', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_memory_job_runs_job_name'), 'memory_job_runs', ['job_name'], unique=False)
        op.create_index(op.f('ix_memory_job_runs_status'), 'memory_job_runs', ['status'], unique=False)

    if not insp.has_table('decisions'):
        op.create_table(
            'decisions',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('title', sa.String(length=300), nullable=False),
            sa.Column('body', sa.Text(), nullable=True),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('alternatives', sa.Text(), nullable=True),
            sa.Column('project', sa.String(length=200), nullable=True),
            sa.Column('outcome', sa.Text(), nullable=True),
            sa.Column('impact', sa.String(length=10), nullable=True, server_default='med'),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
            sa.Column('superseded_by', sa.String(length=36), nullable=True),
            sa.Column('mission_id', sa.String(length=36), nullable=True),  # [Δ]
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_decisions_project'), 'decisions', ['project'], unique=False)
        op.create_index(op.f('ix_decisions_status'), 'decisions', ['status'], unique=False)
        op.create_index(op.f('ix_decisions_mission_id'), 'decisions', ['mission_id'], unique=False)
        op.create_index(op.f('ix_decisions_created_at'), 'decisions', ['created_at'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table('decisions'):
        op.drop_index(op.f('ix_decisions_created_at'), table_name='decisions')
        op.drop_index(op.f('ix_decisions_mission_id'), table_name='decisions')
        op.drop_index(op.f('ix_decisions_status'), table_name='decisions')
        op.drop_index(op.f('ix_decisions_project'), table_name='decisions')
        op.drop_table('decisions')

    if insp.has_table('memory_job_runs'):
        op.drop_index(op.f('ix_memory_job_runs_status'), table_name='memory_job_runs')
        op.drop_index(op.f('ix_memory_job_runs_job_name'), table_name='memory_job_runs')
        op.drop_table('memory_job_runs')
