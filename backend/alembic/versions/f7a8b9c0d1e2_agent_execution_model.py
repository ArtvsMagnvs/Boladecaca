"""agent_executions.model — proveedor:modelo elegido por mensaje (2026-08-02)

Columna ADITIVA y anulable en `agent_executions`:
  · `model` — "proveedor:modelo" elegido para ESE mensaje concreto desde el
              selector del chat. Es una decision por interaccion, no una
              configuracion del agente; por eso vive en la ejecucion, no en
              `agents`.

Migracion SEPARADA de `e2f3a4b5c6d7` a proposito: esa revision ya estaba
aplicada en el Postgres real cuando se detecto que le faltaba esta columna
(reportado en vivo: "column model of relation agent_executions does not
exist" pese a `alembic upgrade head` ya ejecutado). Alembic identifica una
revision aplicada por su ID en `alembic_version`, no por el contenido del
archivo — editar una migracion YA aplicada no la reaplica. La forma correcta
de anadir algo despues del hecho es una migracion nueva, no reescribir la
vieja (por eso `check_schema_drift()` en `app/db/database.py` existe: para
que este tipo de desfase se vea en un log, no en un traceback de 500).

IDEMPOTENTE: se comprueba antes de anadir, porque en una BD creada por
`create_all` (SQLite de desarrollo, tests) la columna ya estara ahi.

Revision ID: f7a8b9c0d1e2
Revises: e2f3a4b5c6d7
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existentes(tabla: str) -> set:
    bind = op.get_bind()
    return {c["name"] for c in sa.inspect(bind).get_columns(tabla)}


def upgrade() -> None:
    if "model" not in _existentes("agent_executions"):
        op.add_column(
            "agent_executions",
            sa.Column("model", sa.String(120), nullable=True),
        )


def downgrade() -> None:
    if "model" in _existentes("agent_executions"):
        op.drop_column("agent_executions", "model")
