# alembic/env.py - Configuracion del entorno Alembic para Aithera V0.4.
#
# Esta adaptado para:
# 1. Leer la URL desde .env (DATABASE_URL) en lugar de tenerla en alembic.ini.
# 2. Cargar los modelos de app.db.database para autogenerate.
# 3. Anadir backend/ al sys.path para que los imports funcionen cuando se
#    ejecuta `alembic` desde el directorio backend/.
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Anadimos backend/ al path para poder importar app.* desde aqui.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Cargamos .env desde backend/ (no del cwd, para que sea robusto desde
# cualquier directorio donde se invoque alembic).
from dotenv import load_dotenv  # noqa: E402
load_dotenv(BACKEND_DIR / ".env")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Sobrescribimos sqlalchemy.url con la del .env (que es la fuente de verdad).
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# FIX V0.4 (Fase 1b PostgreSQL Migration): cargamos los modelos reales
# para que `alembic revision --autogenerate` pueda detectar cambios
# comparando contra Base.metadata.
from app.db.database import Base  # noqa: E402
# V0.87 (WPMS): los modelos del modulo workspace viven fuera de database.py
# (disciplina modular, doc 16). Import con efecto secundario para que se
# registren en Base.metadata y autogenerate/create_all los vean.
import app.workspace.models  # noqa: E402,F401
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
