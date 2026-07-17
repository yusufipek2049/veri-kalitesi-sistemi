"""PostgreSQL salt-okunur bağlantı testi sözleşmesi."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol

from veri_kalitesi.data_sources.connectors import _elapsed_ms, _failure
from veri_kalitesi.data_sources.models import (
    ConnectionTestResult,
    DataField,
    DataSource,
    Dataset,
    ErrorClass,
    MetadataDatasetCandidate,
    MetadataDiscoveryOptions,
    ProfileComputationResult,
    ProfileOptions,
    SourceType,
)

DEFAULT_POSTGRESQL_TEST_QUERY = "SELECT current_database(), current_user, version()"
READ_ONLY_START_KEYWORDS = {"select", "show"}
FORBIDDEN_SQL_KEYWORDS = {
    "alter",
    "analyze",
    "call",
    "cluster",
    "copy",
    "create",
    "delete",
    "do",
    "drop",
    "grant",
    "insert",
    "listen",
    "lock",
    "merge",
    "notify",
    "refresh",
    "reindex",
    "revoke",
    "set",
    "truncate",
    "update",
    "vacuum",
}


@dataclass(frozen=True)
class PostgreSQLProbeResult:
    database_name: str
    user_name: str
    server_version: str
    read_only: bool


class PostgreSQLDriver(Protocol):
    def probe(
        self,
        *,
        config: Mapping[str, Any],
        credentials: Mapping[str, Any],
        test_query: str,
        connect_timeout_seconds: int,
        statement_timeout_ms: int,
    ) -> PostgreSQLProbeResult:
        """PostgreSQL bağlantısını dener ve salt-okunur sağlık bilgisini döndürür."""

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
        """PostgreSQL katalogundan Dataset/DataField adaylarını döndürür."""

    def profile_dataset(
        self,
        *,
        config: Mapping[str, Any],
        credentials: Mapping[str, Any],
        dataset: Dataset,
        fields: tuple[DataField, ...],
        options: ProfileOptions,
    ) -> ProfileComputationResult:
        """PostgreSQL üzerinde kaynakta toplulaştırılmış profil metriklerini döndürür."""


class DNSConnectionError(Exception):
    """Host adı çözülemedi."""


class NetworkConnectionError(Exception):
    """Ağ bağlantısı kurulamadı."""


class TimeoutConnectionError(Exception):
    """Bağlantı veya test sorgusu zaman aşımına uğradı."""


class AuthenticationConnectionError(Exception):
    """Kimlik doğrulama başarısız oldu."""


class TLSConnectionError(Exception):
    """TLS doğrulaması başarısız oldu."""


class PermissionConnectionError(Exception):
    """Salt-okunur yetki doğrulaması başarısız oldu."""


class DriverConnectionError(Exception):
    """PostgreSQL sürücüsü beklenen bağlantı testini tamamlayamadı."""


class MissingPostgreSQLDriver:
    def probe(
        self,
        *,
        config: Mapping[str, Any],
        credentials: Mapping[str, Any],
        test_query: str,
        connect_timeout_seconds: int,
        statement_timeout_ms: int,
    ) -> PostgreSQLProbeResult:
        raise DriverConnectionError("PostgreSQL driver is not configured.")

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
        raise DriverConnectionError("PostgreSQL driver is not configured.")

    def profile_dataset(
        self,
        *,
        config: Mapping[str, Any],
        credentials: Mapping[str, Any],
        dataset: Dataset,
        fields: tuple[DataField, ...],
        options: ProfileOptions,
    ) -> ProfileComputationResult:
        raise DriverConnectionError("PostgreSQL driver is not configured.")


class PostgreSQLConnector:
    source_type = SourceType.POSTGRESQL

    def __init__(self, driver: PostgreSQLDriver | None = None) -> None:
        self.driver = driver or MissingPostgreSQLDriver()

    def test_connection(
        self,
        data_source: DataSource,
        secret: Mapping[str, Any],
    ) -> ConnectionTestResult:
        started = perf_counter()
        config = data_source.connection_config
        test_query = str(config.get("test_query", DEFAULT_POSTGRESQL_TEST_QUERY))
        if not is_read_only_sql(test_query):
            return _failure(
                data_source,
                started,
                ErrorClass.PERMISSION,
                "PostgreSQL test query must be read-only.",
            )

        try:
            probe = self.driver.probe(
                config=config,
                credentials=dict(secret),
                test_query=test_query,
                connect_timeout_seconds=int(config.get("connect_timeout_seconds", 5)),
                statement_timeout_ms=int(config.get("statement_timeout_ms", 5000)),
            )
            if not probe.read_only:
                return _failure(
                    data_source,
                    started,
                    ErrorClass.PERMISSION,
                    "PostgreSQL account is not read-only.",
                )
            return ConnectionTestResult(
                data_source_id=data_source.data_source_id,
                succeeded=True,
                duration_ms=_elapsed_ms(started),
                message="PostgreSQL source is reachable with read-only access.",
                source_info={
                    "source_type": SourceType.POSTGRESQL.value,
                    "database_name": probe.database_name,
                    "user_name": probe.user_name,
                    "server_version": probe.server_version,
                    "ssl_mode": config["ssl_mode"],
                },
            )
        except DNSConnectionError:
            return _classified_failure(data_source, started, ErrorClass.DNS)
        except NetworkConnectionError:
            return _classified_failure(data_source, started, ErrorClass.NETWORK)
        except TimeoutConnectionError:
            return _classified_failure(data_source, started, ErrorClass.TIMEOUT)
        except AuthenticationConnectionError:
            return _classified_failure(data_source, started, ErrorClass.AUTHENTICATION)
        except TLSConnectionError:
            return _classified_failure(data_source, started, ErrorClass.TLS)
        except PermissionConnectionError:
            return _classified_failure(data_source, started, ErrorClass.PERMISSION)
        except DriverConnectionError:
            return _classified_failure(data_source, started, ErrorClass.DRIVER)

    def discover_metadata(
        self,
        data_source: DataSource,
        secret: Mapping[str, Any],
        options: MetadataDiscoveryOptions,
    ) -> tuple[MetadataDatasetCandidate, ...]:
        return self.driver.discover_metadata(
            config=data_source.connection_config,
            credentials=dict(secret),
            scope=options.scope,
            page_size=options.page_size,
            max_objects=options.max_objects,
            timeout_seconds=options.timeout_seconds,
        )

    def profile_dataset(
        self,
        data_source: DataSource,
        secret: Mapping[str, Any],
        dataset: Dataset,
        fields: tuple[DataField, ...],
        options: ProfileOptions,
    ) -> ProfileComputationResult:
        return self.driver.profile_dataset(
            config=data_source.connection_config,
            credentials=dict(secret),
            dataset=dataset,
            fields=fields,
            options=options,
        )


def is_read_only_sql(sql: str) -> bool:
    statement = _strip_sql_comments(sql).strip()
    if statement.endswith(";"):
        statement = statement[:-1].strip()
    if not statement or ";" in statement:
        return False

    first_keyword = statement.split(maxsplit=1)[0].lower()
    if first_keyword not in READ_ONLY_START_KEYWORDS:
        return False

    forbidden_pattern = r"\b(" + "|".join(sorted(FORBIDDEN_SQL_KEYWORDS)) + r")\b"
    return re.search(forbidden_pattern, statement, flags=re.IGNORECASE) is None


def _strip_sql_comments(sql: str) -> str:
    without_block_comments = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    lines = []
    for line in without_block_comments.splitlines():
        lines.append(line.split("--", maxsplit=1)[0])
    return "\n".join(lines)


def _classified_failure(
    data_source: DataSource,
    started: float,
    error_class: ErrorClass,
) -> ConnectionTestResult:
    return _failure(
        data_source,
        started,
        error_class,
        f"PostgreSQL connection test failed with {error_class.value}.",
    )
