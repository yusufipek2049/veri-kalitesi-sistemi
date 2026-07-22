"""Yetki kapsamlı, veri-minimum veri kaynağı okuma servisi."""

from __future__ import annotations

import sqlite3
from typing import Protocol

from veri_kalitesi.data_sources.models import DataSource
from veri_kalitesi.identity import ActorContext, AuthorizationService, IdentityError


class DataSourceReader(Protocol):
    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]: ...


class DataSourceQueryError(Exception):
    def __init__(self, message: str, correlation_id: str) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id


class DataSourceQueryAuthorizationError(DataSourceQueryError):
    """Güvenilir yetkilendirme kararı üretilemedi."""


class DataSourceQueryTechnicalError(DataSourceQueryError):
    """Depo sorgusu teknik nedenle tamamlanamadı."""


class DataSourceQueryService:
    def __init__(
        self,
        reader: DataSourceReader,
        authorization_service: AuthorizationService,
    ) -> None:
        self.reader = reader
        self.authorization_service = authorization_service

    def list_for_actor(self, actor_context: ActorContext | None) -> tuple[DataSource, ...]:
        correlation_id = (
            actor_context.correlation_id if actor_context is not None else "authorization-denied"
        )
        try:
            decision = self.authorization_service.authorize_dashboard(actor_context)
        except IdentityError as exc:
            raise DataSourceQueryAuthorizationError(
                "Data source scope is not available.", correlation_id
            ) from exc
        try:
            return tuple(self.reader.list_data_sources(decision.permitted_source_ids))
        except (sqlite3.Error, OSError) as exc:
            raise DataSourceQueryTechnicalError(
                "Data source query could not be completed.", correlation_id
            ) from exc
