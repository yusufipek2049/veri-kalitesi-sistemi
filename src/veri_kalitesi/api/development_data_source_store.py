"""Geliştirme ortamı veri kaynağı (data source) bellek içi deposu ve okuyucusu."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from veri_kalitesi.api.development_fixtures import DEVELOPMENT_SOURCES
from veri_kalitesi.data_sources.models import (
    DataSource,
    DataSourceStatus,
    SourceType,
)
from veri_kalitesi.data_sources.query import (
    DataSourceConflictError,
    DataSourceNotFoundError,
)


class DevelopmentDataSourceReader:
    def get_data_source(self, data_source_id: str) -> DataSource:
        for source in DEVELOPMENT_SOURCES:
            if source.data_source_id == data_source_id:
                return source
        raise DataSourceNotFoundError("Data source not found.", "development")

    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]:
        return [
            source for source in DEVELOPMENT_SOURCES if source.data_source_id in allowed_source_ids
        ]

    def list_all_data_sources(self) -> list[DataSource]:
        return list(DEVELOPMENT_SOURCES)

    def latest_pending_activation_request(self, data_source_id: str):  # type: ignore[no-untyped-def]
        return None


class DevelopmentDataSourceStore:
    """Geliştirme ortamında veri kaynağı mutasyonları için bellek içi depo."""

    def __init__(self) -> None:
        self._sources = {source.data_source_id: source for source in DEVELOPMENT_SOURCES}
        self._lock = RLock()

    def create(
        self,
        *,
        name: str,
        source_type: str,
        owner_user_id: str,
        host: str = "",
        port: int = 0,
        database_name: str = "",
        username: str = "",
        file_path: str = "",
        connection_parameters: dict | None = None,
    ) -> DataSource:
        with self._lock:
            data_source_id = f"source-{uuid4().hex[:12]}"
            st = SourceType(source_type) if source_type else SourceType.POSTGRESQL
            conn_config: dict[str, object] = {}
            if host:
                conn_config["host"] = host
            if port:
                conn_config["port"] = port
            if database_name:
                conn_config["database"] = database_name
            if username:
                conn_config["username"] = username
            if file_path:
                conn_config["file_path"] = file_path
            if connection_parameters:
                conn_config.update(connection_parameters)
            source = DataSource(
                data_source_id=data_source_id,
                name=name,
                source_type=st,
                connection_config=conn_config,
                secret_reference="development-reference-only",
                status=DataSourceStatus.TEST_PENDING,
                owner_user_id=owner_user_id,
                revision=1,
            )
            self._sources[data_source_id] = source
            return source

    def test_connection(self, data_source_id: str) -> DataSource:
        with self._lock:
            source = self._sources.get(data_source_id)
            if source is None:
                raise DataSourceNotFoundError(
                    f"Development data source {data_source_id} not found.", "development"
                )
            updated = replace(
                source,
                status=DataSourceStatus.TEST_SUCCEEDED,
                last_test_at=datetime.now(timezone.utc),
                last_test_result="SUCCESS",
                revision=source.revision + 1,
            )
            self._sources[data_source_id] = updated
            return updated

    def activate(self, data_source_id: str) -> DataSource:
        with self._lock:
            source = self._sources.get(data_source_id)
            if source is None:
                raise DataSourceNotFoundError(
                    f"Development data source {data_source_id} not found.", "development"
                )
            if source.status is not DataSourceStatus.TEST_SUCCEEDED:
                raise DataSourceConflictError(
                    f"Cannot activate source in status {source.status.value}.", "development"
                )
            updated = replace(
                source,
                status=DataSourceStatus.ACTIVE,
                revision=source.revision + 1,
            )
            self._sources[data_source_id] = updated
            return updated

    def passivate(self, data_source_id: str) -> DataSource:
        with self._lock:
            source = self._sources.get(data_source_id)
            if source is None:
                raise DataSourceNotFoundError(
                    f"Development data source {data_source_id} not found.", "development"
                )
            if source.status is not DataSourceStatus.ACTIVE:
                raise DataSourceConflictError(
                    f"Cannot passivate source in status {source.status.value}.", "development"
                )
            updated = replace(
                source,
                status=DataSourceStatus.INACTIVE,
                revision=source.revision + 1,
            )
            self._sources[data_source_id] = updated
            return updated
