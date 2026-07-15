"""v087 WPMS W2e — Project.github_url + Agent.role (esqueletos)

Sprint W2e (doc 18 + doc 14 §4.3c). Dos columnas aditivas, ninguna con logica
todavia:

- projects.github_url: enlace al repo remoto. SOLO el campo — la integracion
  real (crear repo, leer issues, etc.) llega con el MCP de GitHub en V1.2. El
  usuario pidio explicitamente NO construir la integracion ahora, solo dejar
  el dato listo para cuando exista.
- agents.role: reservado para "orchestrator" (doc 14 §4.3c, Δ 2026-07-15) — el
  TIE v1 (V1.0) creara agentes orquestadores por proyecto con autoridad
  limitada a los agentes/carpetas de ESE proyecto. Nullable, sin UI ni logica
  en V0.87 — solo evita una migracion de esquema cuando se construya el TIE.

Ambas Integer/String planas, aditivas, idempotentes (patron ya establecido en
las migraciones 15.a/16.a).

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(insp, table: str) -> set:
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    proj_cols = _existing_columns(insp, "projects")
    if "github_url" not in proj_cols:
        op.add_column("projects", sa.Column("github_url", sa.String(length=500)))

    agent_cols = _existing_columns(insp, "agents")
    if "role" not in agent_cols:
        op.add_column("agents", sa.Column("role", sa.String(length=20)))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "role" in _existing_columns(insp, "agents"):
        op.drop_column("agents", "role")
    if "github_url" in _existing_columns(insp, "projects"):
        op.drop_column("projects", "github_url")
