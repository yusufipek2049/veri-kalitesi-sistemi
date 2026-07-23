"""SQLAlchemy 2 tabanlı PostgreSQL session ve transaction sınırı."""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import URL, Engine, create_engine, make_url
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_NAME = "data_quality"
DEFAULT_SCHEMA_NAME = "dq"
DATABASE_URL_ENV = "DATA_QUALITY_DATABASE_URL"
SCHEMA_ENV = "DATA_QUALITY_DATABASE_SCHEMA"
_SCHEMA_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,62}")

SessionFactory = sessionmaker[Session]


class DatabaseConfigurationError(ValueError):
    """PostgreSQL kalıcılık ayarı eksik veya güvenli değil."""


@dataclass(frozen=True)
class DatabaseSettings:
    url: URL
    schema: str = DEFAULT_SCHEMA_NAME

    @classmethod
    def from_environment(cls) -> DatabaseSettings:
        raw_url = os.environ.get(DATABASE_URL_ENV)
        if not raw_url:
            raise DatabaseConfigurationError(f"{DATABASE_URL_ENV} is required.")
        return cls.from_url(raw_url, schema=os.environ.get(SCHEMA_ENV, DEFAULT_SCHEMA_NAME))

    @classmethod
    def from_url(cls, raw_url: str, *, schema: str = DEFAULT_SCHEMA_NAME) -> DatabaseSettings:
        try:
            url = make_url(raw_url)
        except (TypeError, ValueError) as exc:
            raise DatabaseConfigurationError("Database URL is invalid.") from exc
        if url.drivername != "postgresql+psycopg":
            raise DatabaseConfigurationError("Only postgresql+psycopg persistence is supported.")
        if url.database != DEFAULT_DATABASE_NAME:
            raise DatabaseConfigurationError(
                f"Application database must be {DEFAULT_DATABASE_NAME}."
            )
        if not _SCHEMA_PATTERN.fullmatch(schema):
            raise DatabaseConfigurationError("Database schema is invalid.")
        return cls(url=url, schema=schema)

    def safe_url(self) -> str:
        return self.url.render_as_string(hide_password=True)


def create_session_factory(
    settings: DatabaseSettings,
    *,
    engine: Engine | None = None,
) -> SessionFactory:
    bound_engine = engine or create_engine(
        settings.url,
        pool_pre_ping=True,
        pool_recycle=1800,
    )
    if bound_engine.dialect.name != "postgresql":
        raise DatabaseConfigurationError("Only PostgreSQL engines are supported.")
    return sessionmaker(
        bind=bound_engine,
        class_=Session,
        expire_on_commit=False,
        autoflush=False,
    )


@contextmanager
def transactional_session(session_factory: SessionFactory) -> Iterator[Session]:
    session = session_factory()
    try:
        with session.begin():
            yield session
    finally:
        session.close()
