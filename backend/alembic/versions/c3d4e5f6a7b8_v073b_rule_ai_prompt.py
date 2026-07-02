"""v073b rule ai_prompt — respuesta generada por IA por regla

Sprint 4b PLAN_MAESTRO_2026: el usuario puede dar una instruccion de estilo
("Responde cordialmente proponiendo otra fecha...") en vez de una plantilla
estricta. Si ai_prompt esta relleno, la respuesta se genera con el proveedor
IA activo; la plantilla queda como fallback.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotente (ver migracion a1f2e3d4c5b6)
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {c['name'] for c in insp.get_columns('email_auto_reply_rules')}
    if 'ai_prompt' not in existing:
        op.add_column('email_auto_reply_rules', sa.Column('ai_prompt', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('email_auto_reply_rules', 'ai_prompt')
