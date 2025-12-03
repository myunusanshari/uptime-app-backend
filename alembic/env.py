import sys
import os
from logging.config import fileConfig
from sqlalchemy import create_engine
from sqlalchemy import pool
from alembic import context
from dotenv import load_dotenv

# Load .env
load_dotenv(".env")

# Add app folder to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import Base from database.py
from app.database import Base
from app.models import domain, downtime_log, device_token

# This is the Alembic Config object
config = context.config

# Interpret .ini file for Python logging.
fileConfig(config.config_file_name)

# Get database URL from .env
config.set_main_option("sqlalchemy.url", os.getenv("DB_URL"))

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
        future=True
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # detect ALTER COLUMN changes
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
