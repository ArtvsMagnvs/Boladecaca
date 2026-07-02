"""v073 email triage — tabla de categorias del clasificador 2 etapas

Sprint 3 PLAN_MAESTRO_2026 (B5): persiste la categoria de triaje por email
(urgente/responder/reunion/newsletter/factura/spam-social/fyi) junto con el
metodo usado (heuristic/llm/fallback).

Revision ID: a1f2e3d4c5b6
Revises: bff7a3fd8d7d
Create Date: 2026-07-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1f2e3d4c5b6'
down_revision: Union[str, None] = 'bff7a3fd8d7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotente: el lifespan del backend hace Base.metadata.create_all al
    # arrancar, asi que la tabla puede existir ya si el backend arranco antes
    # de migrar. En ese caso solo estampamos la revision.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table('email_triage'):
        return
    op.create_table(
        'email_triage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email_id', sa.String(length=120), nullable=False),
        sa.Column('sender', sa.String(length=300), nullable=True),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('method', sa.String(length=12), nullable=False, server_default='heuristic'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_triage_id'), 'email_triage', ['id'], unique=False)
    op.create_index(op.f('ix_email_triage_email_id'), 'email_triage', ['email_id'], unique=True)
    op.create_index(op.f('ix_email_triage_category'), 'email_triage', ['category'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_email_triage_category'), table_name='email_triage')
    op.drop_index(op.f('ix_email_triage_email_id'), table_name='email_triage')
    op.drop_index(op.f('ix_email_triage_id'), table_name='email_triage')
    op.drop_table('email_triage')
