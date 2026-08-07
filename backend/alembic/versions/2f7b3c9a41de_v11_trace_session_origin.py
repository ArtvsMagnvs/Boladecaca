"""V1.1 LC1 — orchestrator_traces: session_id + origin (2026-08-07)

Las dos columnas que el juez del Learner necesita y que no se pueden deducir
a posteriori (doc 41 §3.2 señal 7 y §6):

  - `session_id`: en qué conversación del chat nació la misión. Es lo que hace
    posible leer "el DESPUÉS" (qué dijo el usuario justo después de la
    respuesta). `chat_messages` es plano entre pestañas, así que sin este
    enlace habría que adivinar por tiempo — justo el problema que R6.5b
    resolvió para el propio chat.
  - `origin`: trabajo real (`user`) o corpus de pruebas (`test`/`campaign`/
    `e2e`/`automation`). Se decide al CREAR la misión porque la marca de prueba
    la pone el entorno que la lanza; de madrugada, cuando el juez trabaja, esa
    información ya no existe en ningún sitio.

MIGRACIÓN NUEVA encadenada tras `1c1a5eb9d70f` — jamás editar una ya aplicada
(la lección del 2026-08-02). IDEMPOTENTE en los dos sentidos: en una BD creada
por `create_all` las columnas ya existirán.

Revision ID: 2f7b3c9a41de
Revises: 1c1a5eb9d70f
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2f7b3c9a41de"
down_revision: Union[str, None] = "1c1a5eb9d70f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLA = "orchestrator_traces"

# Fábricas, no instancias: un objeto `Column` solo puede usarse en UN
# `add_column`; compartirlo entre upgrade y downgrade revienta a la segunda
# (incidente real del 2026-08-02).
_COLUMNAS = {
    "session_id": lambda: sa.Column("session_id", sa.String(64), nullable=True),
    "origin": lambda: sa.Column("origin", sa.String(16), nullable=True,
                                server_default="user"),
}


def _existentes() -> set:
    insp = sa.inspect(op.get_bind())
    if _TABLA not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLA)}


def upgrade() -> None:
    hay = _existentes()
    if not hay:                      # la tabla no existe: nada que ampliar
        return
    for nombre, fabrica in _COLUMNAS.items():
        if nombre not in hay:
            op.add_column(_TABLA, fabrica())
    hay = _existentes()
    for nombre in ("session_id", "origin"):
        if nombre in hay:
            try:
                op.create_index(f"ix_{_TABLA}_{nombre}", _TABLA, [nombre])
            except Exception:
                pass                 # ya existía


def downgrade() -> None:
    hay = _existentes()
    for nombre in _COLUMNAS:
        if nombre in hay:
            op.drop_column(_TABLA, nombre)
