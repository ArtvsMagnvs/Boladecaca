"""v073 rule autonomy — autonomia gradual por regla (propose/auto)

Sprint 4 PLAN_MAESTRO_2026 (B6, patron Inbox Zero): cada regla nace en
'propose' (borrador + aprobacion) y el usuario la sube a 'auto' cuando
confia. Backfill: las reglas existentes con action='auto_send' se marcan
'auto' para NO cambiar su comportamiento actual (principio 1: no romper
lo que funciona).

Revision ID: b2c3d4e5f6a7
Revises: a1f2e3d4c5b6
Create Date: 2026-07-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1f2e3d4c5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotente (ver migracion a1f2e3d4c5b6): solo anade lo que falte.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {c['name'] for c in insp.get_columns('email_auto_reply_rules')}
    if 'autonomy' not in existing:
        op.add_column('email_auto_reply_rules',
            sa.Column('autonomy', sa.String(length=10), nullable=False, server_default='propose'))
        # Backfill: preservar comportamiento de reglas auto_send ya consentidas
        op.execute("UPDATE email_auto_reply_rules SET autonomy = 'auto' WHERE action = 'auto_send'")
    if 'approved_count' not in existing:
        op.add_column('email_auto_reply_rules',
            sa.Column('approved_count', sa.Integer(), nullable=False, server_default='0'))
    if 'edited_count' not in existing:
        op.add_column('email_auto_reply_rules',
            sa.Column('edited_count', sa.Integer(), nullable=False, server_default='0'))
    if 'rejected_count' not in existing:
        op.add_column('email_auto_reply_rules',
            sa.Column('rejected_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('email_auto_reply_rules', 'rejected_count')
    op.drop_column('email_auto_reply_rules', 'edited_count')
    op.drop_column('email_auto_reply_rules', 'approved_count')
    op.drop_column('email_auto_reply_rules', 'autonomy')
