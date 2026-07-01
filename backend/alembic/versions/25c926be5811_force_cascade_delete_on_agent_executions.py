"""force_cascade_delete_on_agent_executions

Revision ID: 25c926be5811
Revises: 24b8353ad754
Create Date: 2026-06-27 02:55:00.000000

V0.5 (Fase 2): forzamos ON DELETE CASCADE en agent_executions.agent_id
para permitir que DELETE FROM agents borre en cascada las ejecuciones
historicas. Alembic autogenerate no detecta este cambio porque compara
con la propia introspeccion del modelo; lo escribimos a mano para que
quede explicito en el historial de migraciones.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "25c926be5811"
down_revision: Union[str, None] = "24b8353ad754"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL no permite alterar el ON DELETE de un FK existente
    # directamente: hay que eliminar la constraint y volverla a crear.
    op.drop_constraint(
        "agent_executions_agent_id_fkey",
        "agent_executions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "agent_executions_agent_id_fkey",
        "agent_executions",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Volvemos al estado anterior (sin CASCADE).
    op.drop_constraint(
        "agent_executions_agent_id_fkey",
        "agent_executions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "agent_executions_agent_id_fkey",
        "agent_executions",
        "agents",
        ["agent_id"],
        ["id"],
    )
