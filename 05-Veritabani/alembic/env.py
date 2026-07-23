"""Alembic çalışma ortamı; bağlantı bilgisi yalnız environment üzerinden gelir."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.schema import CreateSchema

from veri_kalitesi.persistence import DatabaseSettings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _settings() -> DatabaseSettings:
    configured_url = config.get_main_option("sqlalchemy.url")
    raw_url = configured_url or os.environ.get("DATA_QUALITY_DATABASE_URL", "")
    schema = config.get_main_option("data_quality_schema", "dq")
    return DatabaseSettings.from_url(raw_url, schema=schema)


def run_migrations_offline() -> None:
    settings = _settings()
    context.configure(
        url=settings.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=settings.schema,
    )
    context.execute(CreateSchema(settings.schema, if_not_exists=True))
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    settings = _settings()
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = settings.url.render_as_string(hide_password=False)
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        connection.execute(CreateSchema(settings.schema, if_not_exists=True))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=settings.schema,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
