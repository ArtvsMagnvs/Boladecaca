"""Autonomia por agente + carpetas extra (2026-08-02)

Columnas nuevas, todas ADITIVAS y anulables, en `agents`:
  · `autonomy`    — 'manual' (default) | 'auto'. El usuario decide POR AGENTE si
                    las acciones sensibles (shell/powershell y demas) se le
                    preguntan o se conceden solas. Se elige desde el selector
                    del chat, al lado de los botones de adjuntar.
  · `extra_paths` — carpetas adicionales a las que ese agente tiene acceso,
                    ademas de la del proyecto.

IDEMPOTENTE: se comprueba antes de anadir, porque en una BD creada por
`create_all` (SQLite de desarrollo, tests) las columnas ya estaran ahi.

NOTA (2026-08-02): esta migracion tuvo brevemente una tercera columna,
`agent_executions.model`, anadida editando este mismo archivo DESPUES de que
ya se hubiera aplicado en produccion. Alembic marca la revision aplicada por
ID en `alembic_version`, no por contenido del archivo — reescribir un archivo
YA aplicado no lo vuelve a ejecutar. Esa columna vive ahora en la migracion
siguiente (f7a8b9c0d1e2), la correcta forma de anadir algo despues del hecho.

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# {columna: fabrica}. La fabrica (lambda) y no la Column directamente porque un
# objeto Column solo puede usarse en UN add_column.
_NUEVAS = {
    "autonomy": lambda: sa.Column("autonomy", sa.String(10), nullable=True,
                                  server_default="manual"),
    "extra_paths": lambda: sa.Column("extra_paths", sa.JSON(), nullable=True),
}


def _existentes(tabla: str) -> set:
    bind = op.get_bind()
    return {c["name"] for c in sa.inspect(bind).get_columns(tabla)}


def upgrade() -> None:
    ya = _existentes("agents")
    for nombre, hacer_columna in _NUEVAS.items():
        if nombre not in ya:
            op.add_column("agents", hacer_columna())


def downgrade() -> None:
    ya = _existentes("agents")
    for nombre in _NUEVAS:
        if nombre in ya:
            op.drop_column("agents", nombre)
