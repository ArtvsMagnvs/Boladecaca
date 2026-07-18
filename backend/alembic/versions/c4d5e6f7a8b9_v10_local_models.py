"""V1.0 (Modelos locales especializados): tabla local_models

Permite que convivan VARIOS modelos locales a la vez (Ornith programando, Qwen
conversando, DeepSeek razonando) para que el MEL reparta cada tarea al
especialista. `ai_provider_configs` no sirve porque guarda UN modelo por
proveedor (`provider` es unique) y todos los locales comparten el runtime
`ollama`.

Aditiva e idempotente: crea la tabla solo si no existe (una BD creada por
`create_all` con el modelo ya presente hace que esto sea un no-op).

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "local_models" in inspector.get_table_names():
        return  # ya existe (create_all la creó): no-op

    op.create_table(
        "local_models",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("family", sa.String(length=40), nullable=True),
        sa.Column("model_tag", sa.String(length=250), nullable=False),
        sa.Column("label", sa.String(length=150), nullable=True),
        sa.Column("size_gb", sa.Float(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("installed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_tag"),
    )
    op.create_index("ix_local_models_family", "local_models", ["family"])
    op.create_index("ix_local_models_enabled", "local_models", ["enabled"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "local_models" not in inspector.get_table_names():
        return
    op.drop_index("ix_local_models_enabled", table_name="local_models")
    op.drop_index("ix_local_models_family", table_name="local_models")
    op.drop_table("local_models")
