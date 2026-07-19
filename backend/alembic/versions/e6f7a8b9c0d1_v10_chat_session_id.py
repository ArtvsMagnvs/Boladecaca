"""R6.5b: chat_messages.session_id — identidad de conversación

Migración 25.ª. ADITIVA e IDEMPOTENTE: añade una columna nullable + su índice.

POR QUÉ HACE FALTA: `chat_messages` era una tabla plana, sin ningún concepto de
conversación. El frontend YA tenía pestañas con su propio id (localStorage
`aithera.chat.sessions`) pero nunca lo enviaba. Sin esta columna, "los últimos
turnos de esta conversación" mezclaría pestañas distintas — que es justo el
criterio de cierre #3 de doc 23 R6.5b.

NULLABLE A PROPÓSITO: todos los mensajes anteriores a R6.5b se quedan sin
sesión y siguen siendo perfectamente válidos. No se inventa un id para ellos:
agruparlos en una conversación falsa daría una continuidad que nunca existió.

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
"""
from alembic import op
import sqlalchemy as sa


revision = "e6f7a8b9c0d1"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def _tiene_columna(inspector, tabla: str, columna: str) -> bool:
    return columna in {c["name"] for c in inspector.get_columns(tabla)}


def _tiene_indice(inspector, tabla: str, indice: str) -> bool:
    return indice in {i["name"] for i in inspector.get_indexes(tabla)}


def upgrade() -> None:
    # Idempotente: la BD del usuario puede tener la columna ya creada por el
    # `create_all()` del arranque (que corre antes que Alembic). Mismo patrón
    # que las migraciones aditivas de W1/W2c/A1 — comprobado en los dos caminos.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _tiene_columna(inspector, "chat_messages", "session_id"):
        op.add_column("chat_messages", sa.Column("session_id", sa.String(64), nullable=True))
        inspector = sa.inspect(bind)
    if not _tiene_indice(inspector, "chat_messages", "ix_chat_messages_session_id"):
        op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _tiene_indice(inspector, "chat_messages", "ix_chat_messages_session_id"):
        op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    if _tiene_columna(inspector, "chat_messages", "session_id"):
        op.drop_column("chat_messages", "session_id")
