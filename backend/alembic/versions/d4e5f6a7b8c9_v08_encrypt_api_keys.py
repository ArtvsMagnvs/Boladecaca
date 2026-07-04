"""v08 hardening — cifrar api_key de ai_provider_configs en reposo (DPAPI)

V0.8 Security Hardening (PLAN_MAESTRO_2026): las API keys de los proveedores IA
estaban en TEXTO PLANO en la tabla ai_provider_configs. Esta migracion las cifra
en reposo reutilizando app/core/secrets.py (DPAPI en Windows; el AIManager las
descifra al instanciar cada proveedor).

Idempotente: solo cifra valores que NO lleven ya prefijo de cifrado
(secrets.is_encrypted), asi re-ejecutarla es seguro. El downgrade descifra de
vuelta a texto plano. Si la tabla aun no existe (BD muy nueva), no hace nada.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "ai_provider_configs"


def _rows(bind):
    if not sa.inspect(bind).has_table(_TABLE):
        return []
    return bind.execute(sa.text(f"SELECT id, api_key FROM {_TABLE}")).fetchall()


def _update(bind, rid, value):
    bind.execute(
        sa.text(f"UPDATE {_TABLE} SET api_key=:k WHERE id=:i"),
        {"k": value, "i": rid},
    )


def upgrade() -> None:
    from app.core import secrets
    bind = op.get_bind()
    for rid, api_key in _rows(bind):
        if api_key and not secrets.is_encrypted(api_key):
            _update(bind, rid, secrets.encrypt(api_key))


def downgrade() -> None:
    from app.core import secrets
    bind = op.get_bind()
    for rid, api_key in _rows(bind):
        if api_key and secrets.is_encrypted(api_key):
            _update(bind, rid, secrets.decrypt(api_key))
