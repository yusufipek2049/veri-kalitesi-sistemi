"""Gerçek psycopg 3 ve SQLAlchemy PostgreSQL bağlantı testi adaptörü."""

from __future__ import annotations

import socket
from collections.abc import Mapping
from typing import Any, NoReturn

import psycopg
from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError

from veri_kalitesi.data_sources.models import (
    DataField,
    Dataset,
    MetadataDatasetCandidate,
    ProfileComputationResult,
    ProfileOptions,
)
from veri_kalitesi.data_sources.postgresql import (
    AuthenticationConnectionError,
    DNSConnectionError,
    DriverConnectionError,
    NetworkConnectionError,
    PermissionConnectionError,
    PostgreSQLProbeResult,
    TLSConnectionError,
    TimeoutConnectionError,
)

_ROLE_CAPABILITY_QUERY = """
SELECT
    current_database() AS database_name,
    current_user AS user_name,
    version() AS server_version,
    current_setting('transaction_read_only') = 'on' AS transaction_read_only,
    NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = current_user
          AND (rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls)
    ) AS role_is_unprivileged,
    NOT has_database_privilege(current_user, current_database(), 'CREATE') AS no_database_create,
    NOT EXISTS (
        SELECT 1
        FROM pg_namespace
        WHERE nspname NOT IN ('pg_catalog', 'information_schema')
          AND nspname NOT LIKE 'pg_toast%'
          AND nspname NOT LIKE 'pg_temp_%'
          AND has_schema_privilege(current_user, oid, 'CREATE')
    ) AS no_schema_create,
    NOT EXISTS (
        SELECT 1
        FROM pg_class
        WHERE relkind IN ('r', 'p', 'v', 'm', 'f')
          AND relnamespace NOT IN (
              SELECT oid FROM pg_namespace
              WHERE nspname IN ('pg_catalog', 'information_schema')
                 OR nspname LIKE 'pg_toast%'
                 OR nspname LIKE 'pg_temp_%'
          )
          AND has_table_privilege(
              current_user,
              oid,
              'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'
          )
    ) AS no_table_write
"""


class SQLAlchemyPostgreSQLDriver:
    """FR-008 için TLS zorunlu ve salt okunur PostgreSQL probe adaptörü."""

    def probe(
        self,
        *,
        config: Mapping[str, Any],
        credentials: Mapping[str, Any],
        test_query: str,
        connect_timeout_seconds: int,
        statement_timeout_ms: int,
    ) -> PostgreSQLProbeResult:
        engine = self._create_engine(
            config=config,
            credentials=credentials,
            connect_timeout_seconds=connect_timeout_seconds,
            statement_timeout_ms=statement_timeout_ms,
        )
        try:
            with engine.connect() as connection:
                connection.exec_driver_sql(test_query).fetchone()
                capability = connection.exec_driver_sql(_ROLE_CAPABILITY_QUERY).mappings().one()
            read_only = all(
                bool(capability[field])
                for field in (
                    "transaction_read_only",
                    "role_is_unprivileged",
                    "no_database_create",
                    "no_schema_create",
                    "no_table_write",
                )
            )
            return PostgreSQLProbeResult(
                database_name=str(capability["database_name"]),
                user_name=str(capability["user_name"]),
                server_version=str(capability["server_version"]),
                read_only=read_only,
            )
        except Exception as exc:
            _raise_classified(exc)
        finally:
            engine.dispose()

    def discover_metadata(
        self,
        *,
        config: Mapping[str, Any],
        credentials: Mapping[str, Any],
        scope: Mapping[str, Any],
        page_size: int,
        max_objects: int,
        timeout_seconds: int,
    ) -> tuple[MetadataDatasetCandidate, ...]:
        raise DriverConnectionError("PostgreSQL metadata driver is not configured.")

    def profile_dataset(
        self,
        *,
        config: Mapping[str, Any],
        credentials: Mapping[str, Any],
        dataset: Dataset,
        fields: tuple[DataField, ...],
        options: ProfileOptions,
    ) -> ProfileComputationResult:
        raise DriverConnectionError("PostgreSQL profile driver is not configured.")

    @staticmethod
    def _create_engine(
        *,
        config: Mapping[str, Any],
        credentials: Mapping[str, Any],
        connect_timeout_seconds: int,
        statement_timeout_ms: int,
    ) -> Engine:
        username = credentials.get("username")
        password = credentials.get("password")
        if not isinstance(username, str) or not username or not isinstance(password, str):
            raise AuthenticationConnectionError()

        connect_args: dict[str, object] = {
            "connect_timeout": connect_timeout_seconds,
            "sslmode": str(config["ssl_mode"]),
            "options": (
                f"-c statement_timeout={statement_timeout_ms} -c default_transaction_read_only=on"
            ),
            "application_name": "veri-kalitesi-connection-probe",
        }
        ssl_root_cert = config.get("ssl_root_cert")
        if ssl_root_cert is not None:
            if not isinstance(ssl_root_cert, str) or not ssl_root_cert:
                raise TLSConnectionError()
            connect_args["sslrootcert"] = ssl_root_cert

        url = URL.create(
            "postgresql+psycopg",
            username=username,
            password=password,
            host=str(config["host"]),
            port=int(config["port"]),
            database=str(config["database"]),
        )
        try:
            return create_engine(
                url,
                connect_args=connect_args,
                hide_parameters=True,
                pool_pre_ping=True,
            )
        except SQLAlchemyError as exc:
            raise DriverConnectionError() from exc


def _raise_classified(exc: Exception) -> NoReturn:
    original = exc.orig if isinstance(exc, DBAPIError) else exc
    sqlstate = getattr(original, "sqlstate", None)
    message = str(original).lower()

    if isinstance(original, psycopg.errors.InvalidPassword) or sqlstate == "28P01":
        raise AuthenticationConnectionError() from exc
    if isinstance(original, psycopg.errors.InsufficientPrivilege) or sqlstate == "42501":
        raise PermissionConnectionError() from exc
    if isinstance(original, (TimeoutError, psycopg.errors.QueryCanceled)) or any(
        marker in message for marker in ("timeout expired", "timed out", "statement timeout")
    ):
        raise TimeoutConnectionError() from exc
    if isinstance(original, socket.gaierror) or any(
        marker in message
        for marker in ("could not translate host name", "name or service not known")
    ):
        raise DNSConnectionError() from exc
    if any(
        marker in message
        for marker in (
            "certificate verify failed",
            "root certificate file",
            "server does not support ssl",
            "ssl error",
            "tls",
        )
    ):
        raise TLSConnectionError() from exc
    if isinstance(exc, OperationalError):
        raise NetworkConnectionError() from exc
    if isinstance(exc, SQLAlchemyError):
        raise DriverConnectionError() from exc
    raise DriverConnectionError() from exc
