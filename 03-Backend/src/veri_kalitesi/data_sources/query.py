"""Yetki kapsamlı, veri-minimum veri kaynağı okuma servisi."""

from __future__ import annotations

import sqlite3
from typing import Protocol

from sqlalchemy.exc import SQLAlchemyError

from veri_kalitesi.data_sources.errors import ValidationError
from veri_kalitesi.data_sources.models import DataSource, ProfileComparison
from veri_kalitesi.data_sources.service import DataSourceService
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


class DataSourceQueryValidationError(DataSourceQueryError):
    """Profil karşılaştırma istemci girdisi domain doğrulamasını geçemedi."""


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
        except (sqlite3.Error, SQLAlchemyError, OSError) as exc:
            raise DataSourceQueryTechnicalError(
                "Data source query could not be completed.", correlation_id
            ) from exc


class ProfileComparisonCommandService:
    """HTTP sınırı için trusted-context ve dataset scope zorlaması."""

    def __init__(
        self,
        service: DataSourceService,
        authorization_service: AuthorizationService,
    ) -> None:
        self.service = service
        self.authorization_service = authorization_service

    def compare(
        self,
        *,
        actor_context: ActorContext | None,
        dataset_id: str,
        baseline_profile_id: str,
        current_profile_id: str,
        policy_version: str | None,
        correlation_id: str,
    ) -> ProfileComparison:
        try:
            decision = self.authorization_service.authorize_dashboard(actor_context)
        except IdentityError as exc:
            raise DataSourceQueryAuthorizationError(
                "Profile comparison scope is not available.",
                correlation_id,
            ) from exc
        assert actor_context is not None
        try:
            dataset = self.service.repository.get_dataset(dataset_id)
            if (
                dataset_id not in decision.permitted_dataset_ids
                and dataset.data_source_id not in decision.permitted_source_ids
            ):
                raise DataSourceQueryAuthorizationError(
                    "Profile comparison scope is not available.",
                    correlation_id,
                )
            return self.service.compare_profiles(
                actor_id=actor_context.actor_id,
                dataset_id=dataset_id,
                baseline_profile_id=baseline_profile_id,
                current_profile_id=current_profile_id,
                policy_version=policy_version,
                correlation_id=correlation_id,
            )
        except DataSourceQueryAuthorizationError:
            raise
        except ValidationError as exc:
            raise DataSourceQueryValidationError(
                "Profile comparison request could not be validated.",
                correlation_id,
            ) from exc
        except (sqlite3.Error, SQLAlchemyError, OSError) as exc:
            raise DataSourceQueryTechnicalError(
                "Profile comparison could not be completed.",
                correlation_id,
            ) from exc
