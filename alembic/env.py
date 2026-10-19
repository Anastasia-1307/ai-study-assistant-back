
import os
from pathlib import Path
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Calea către directorul principal al backend-ului
BASE_DIR = Path(__file__).resolve().parent.parent

# Încarcă variabilele exclusiv din .env.local
load_dotenv(BASE_DIR / ".env.local", override=True)

# Configurația Alembic
config = context.config

# Citește conexiunea din .env.local
database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise ValueError(
        "DATABASE_URL nu este definită în fișierul .env.local"
    )

# Suprascrie URL-ul implicit din alembic.ini
config.set_main_option(
    "sqlalchemy.url",
    database_url.replace("%", "%%")
)

# Configurarea logării
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


from database.models import Base  

target_metadata = Base.metadata


def run_migrations_offline() -> None:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
