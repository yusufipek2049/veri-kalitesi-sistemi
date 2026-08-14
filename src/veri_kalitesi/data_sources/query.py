"""Yetki kapsamlı, veri-minimum veri kaynağı okuma servisi."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from typing import Protocol

from sqlalchemy.exc import SQLAlchemyError

from veri_kalitesi.data_sources.errors import ValidationError
from veri_kalitesi.data_sources.models import (
    DataProfile,
    DataSource,
    DataSourceActivationRequest,
    DataSourceCommandPolicy,
    DataSourceStatus,
    ProfileComparison,
    ProfileComparisonStatus,
)
from veri_kalitesi.data_sources.profiling import compare_profile_snapshots, ProfilePolicyResolver
from veri_kalitesi.data_sources.service import DataSourceService
from veri_kalitesi.identity import (
    ActorContext,
    AuthorizationService,
    IdentityError,
    is_trusted_actor_context,
)


class DataSourceReader(Protocol):
    def get_data_source(self, data_source_id: str) -> DataSource: ...

    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]: ...

    def list_all_data_sources(self) -> list[DataSource]: ...

    def latest_pending_activation_request(
        self, data_source_id: str
    ) -> DataSourceActivationRequest | None: ...

    def latest_pending_deactivation_request(
        self, data_source_id: str
    ) -> DataSourceActivationRequest | None: ...


@dataclass(frozen=True)
class DataSourceView:
    source: DataSource
    available_actions: tuple[str, ...] = ()
    pending_activation_request: DataSourceActivationRequest | None = None
    pending_deactivation_request: DataSourceActivationRequest | None = None


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


class DataSourceNotFoundError(DataSourceQueryError):
    """Veri kaynağı kimliği mevcut değil."""


class DataSourceConflictError(DataSourceQueryError):
    """Veri kaynağı bu işlem için uygun durumda değil."""


class DataSourceQueryService:
    def __init__(
        self,
        reader: DataSourceReader,
        authorization_service: AuthorizationService,
        command_policy: DataSourceCommandPolicy | None = None,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.reader = reader
        self.authorization_service = authorization_service
        self.command_policy = command_policy
        self.clock = clock

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
            if decision.can_view_enterprise:
                return tuple(self.reader.list_all_data_sources())
            return tuple(self.reader.list_data_sources(decision.permitted_source_ids))
        except (sqlite3.Error, SQLAlchemyError, OSError) as exc:
            raise DataSourceQueryTechnicalError(
                "Data source query could not be completed.", correlation_id
            ) from exc

    def list_views_for_actor(
        self, actor_context: ActorContext | None
    ) -> tuple[DataSourceView, ...]:
        sources = self.list_for_actor(actor_context)
        try:
            return tuple(self._view(source, actor_context) for source in sources)
        except (sqlite3.Error, SQLAlchemyError, OSError) as exc:
            correlation_id = (
                actor_context.correlation_id
                if actor_context is not None
                else "authorization-denied"
            )
            raise DataSourceQueryTechnicalError(
                "Data source projection could not be completed.", correlation_id
            ) from exc

    def get_view_for_actor(
        self,
        data_source_id: str,
        actor_context: ActorContext | None,
    ) -> DataSourceView:
        for view in self.list_views_for_actor(actor_context):
            if view.source.data_source_id == data_source_id:
                return view
        correlation_id = (
            actor_context.correlation_id if actor_context is not None else "authorization-denied"
        )
        raise DataSourceNotFoundError("Data source not found.", correlation_id)

    def _view(
        self,
        source: DataSource,
        actor_context: ActorContext | None,
    ) -> DataSourceView:
        pending = self.reader.latest_pending_activation_request(source.data_source_id)
        deactivation_reader = getattr(self.reader, "latest_pending_deactivation_request", None)
        pending_deactivation = (
            deactivation_reader(source.data_source_id) if callable(deactivation_reader) else None
        )
        return DataSourceView(
            source=source,
            pending_activation_request=pending,
            pending_deactivation_request=pending_deactivation,
            available_actions=self._available_actions(
                source, pending, pending_deactivation, actor_context
            ),
        )

    def _available_actions(
        self,
        source: DataSource,
        pending: DataSourceActivationRequest | None,
        pending_deactivation: DataSourceActivationRequest | None,
        context: ActorContext | None,
    ) -> tuple[str, ...]:
        policy = self.command_policy
        now = self.clock()
        if (
            policy is None
            or not is_trusted_actor_context(context)
            or context is None
            or context.issued_at > now
            or context.expires_at <= now
            or context.policy_version != policy.actor_policy_version
            or context.privileged
            or source.data_source_id not in context.permitted_source_ids
        ):
            return ()
        actions: list[str] = []
        if (
            not context.roles.isdisjoint(policy.connection_tester_roles)
            and source.status is not DataSourceStatus.ARCHIVED
        ):
            actions.append("TEST_CONNECTION")
        if (
            not context.roles.isdisjoint(policy.maker_roles)
            and pending is None
            and source.status in {DataSourceStatus.TEST_SUCCEEDED, DataSourceStatus.INACTIVE}
        ):
            actions.append("REQUEST_ACTIVATION")
        if (
            pending is not None
            and pending.request_type == "ACTIVATION"
            and pending.maker_actor_id != context.actor_id
            and not context.roles.isdisjoint(policy.checker_roles)
        ):
            actions.extend(("APPROVE_ACTIVATION", "REJECT_ACTIVATION"))
        if (
            source.status is DataSourceStatus.ACTIVE
            and not context.roles.isdisjoint(policy.maker_roles)
            and pending_deactivation is None
        ):
            actions.append("REQUEST_DEACTIVATION")
        if (
            pending_deactivation is not None
            and pending_deactivation.maker_actor_id != context.actor_id
            and not context.roles.isdisjoint(policy.checker_roles)
        ):
            actions.extend(("APPROVE_DEACTIVATION", "REJECT_DEACTIVATION"))
        if source.status is DataSourceStatus.ACTIVE and not context.roles.isdisjoint(
            policy.deactivator_roles
        ):
            actions.append("PASSIVATE")
        if source.status is DataSourceStatus.ACTIVE and not context.roles.isdisjoint(
            policy.metadata_discovery_roles
        ):
            actions.append("DISCOVER_METADATA")
        return tuple(actions)


class ProfileSnapshotQueryService:
    """Salt okunur profil snapshot ve drift hüküm sorgu servisi."""

    MAX_SNAPSHOTS = 50

    def __init__(
        self,
        service: DataSourceService,
        authorization_service: AuthorizationService,
        profile_policy_resolver: ProfilePolicyResolver | None = None,
    ) -> None:
        self.service = service
        self.authorization_service = authorization_service
        self.profile_policy_resolver = profile_policy_resolver

    def _assert_dataset_scope(
        self,
        dataset_id: str,
        decision: object,
        correlation_id: str,
    ) -> None:
        permitted_dataset_ids: frozenset[str] = getattr(
            decision, "permitted_dataset_ids", frozenset()
        )
        permitted_source_ids: frozenset[str] = getattr(
            decision, "permitted_source_ids", frozenset()
        )
        dataset = self.service.repository.get_dataset(dataset_id)
        if (
            dataset_id not in permitted_dataset_ids
            and dataset.data_source_id not in permitted_source_ids
        ):
            raise DataSourceQueryAuthorizationError(
                "Profile snapshot scope is not available.",
                correlation_id,
            )

    def list_snapshots(
        self,
        *,
        actor_context: ActorContext | None,
        dataset_id: str,
        correlation_id: str,
    ) -> list[DataProfile]:
        """Yetkili kapsamdaki profil snapshot listesini bounded döner."""
        try:
            decision = self.authorization_service.authorize_dashboard(actor_context)
        except IdentityError as exc:
            raise DataSourceQueryAuthorizationError(
                "Profile snapshot scope is not available.",
                correlation_id,
            ) from exc
        try:
            self._assert_dataset_scope(dataset_id, decision, correlation_id)
            profiles = self.service.repository.list_data_profiles(dataset_id)
            profiles.sort(key=lambda p: p.finished_at, reverse=True)
            return profiles[: self.MAX_SNAPSHOTS]
        except DataSourceQueryAuthorizationError:
            raise
        except (sqlite3.Error, SQLAlchemyError, OSError) as exc:
            raise DataSourceQueryTechnicalError(
                "Profile snapshot query could not be completed.",
                correlation_id,
            ) from exc

    def get_snapshot(
        self,
        *,
        actor_context: ActorContext | None,
        profile_id: str,
        correlation_id: str,
    ) -> DataProfile:
        """Tek profil snapshot detayını döner."""
        try:
            decision = self.authorization_service.authorize_dashboard(actor_context)
        except IdentityError as exc:
            raise DataSourceQueryAuthorizationError(
                "Profile snapshot scope is not available.",
                correlation_id,
            ) from exc
        permitted_dataset_ids: frozenset[str] = getattr(
            decision, "permitted_dataset_ids", frozenset()
        )
        permitted_source_ids: frozenset[str] = getattr(
            decision, "permitted_source_ids", frozenset()
        )
        try:
            for ds_id in permitted_dataset_ids:
                for profile in self.service.repository.list_data_profiles(ds_id):
                    if profile.profile_id == profile_id:
                        return profile
            for source_id in permitted_source_ids:
                for dataset in self.service.repository.list_datasets(source_id):
                    for profile in self.service.repository.list_data_profiles(dataset.dataset_id):
                        if profile.profile_id == profile_id:
                            return profile
            raise DataSourceNotFoundError(
                "Profile snapshot not found.",
                correlation_id,
            )
        except DataSourceQueryAuthorizationError:
            raise
        except DataSourceNotFoundError:
            raise
        except (sqlite3.Error, SQLAlchemyError, OSError) as exc:
            raise DataSourceQueryTechnicalError(
                "Profile snapshot query could not be completed.",
                correlation_id,
            ) from exc

    def get_drift_judgments(
        self,
        *,
        actor_context: ActorContext | None,
        profile_id: str,
        baseline_profile_id: str | None = None,
        correlation_id: str,
    ) -> ProfileComparison:
        """Profil snapshot'a bağlı drift hükümlerini döner (fail-closed)."""
        try:
            decision = self.authorization_service.authorize_dashboard(actor_context)
        except IdentityError as exc:
            raise DataSourceQueryAuthorizationError(
                "Profile drift scope is not available.",
                correlation_id,
            ) from exc
        permitted_dataset_ids: frozenset[str] = getattr(
            decision, "permitted_dataset_ids", frozenset()
        )
        permitted_source_ids: frozenset[str] = getattr(
            decision, "permitted_source_ids", frozenset()
        )
        try:
            current_profile: DataProfile | None = None
            dataset_id: str | None = None
            for ds_id in permitted_dataset_ids:
                for profile in self.service.repository.list_data_profiles(ds_id):
                    if profile.profile_id == profile_id:
                        current_profile = profile
                        dataset_id = ds_id
                        break
                if current_profile:
                    break
            if current_profile is None:
                for source_id in permitted_source_ids:
                    for dataset in self.service.repository.list_datasets(source_id):
                        for profile in self.service.repository.list_data_profiles(
                            dataset.dataset_id
                        ):
                            if profile.profile_id == profile_id:
                                current_profile = profile
                                dataset_id = dataset.dataset_id
                                break
                        if current_profile:
                            break
                    if current_profile:
                        break
            if current_profile is None or dataset_id is None:
                raise DataSourceNotFoundError(
                    "Profile snapshot not found.",
                    correlation_id,
                )
            all_profiles = self.service.repository.list_data_profiles(dataset_id)
            if baseline_profile_id:
                baseline_profile = next(
                    (p for p in all_profiles if p.profile_id == baseline_profile_id),
                    None,
                )
                if baseline_profile is None:
                    raise DataSourceNotFoundError(
                        "Baseline profile snapshot not found.",
                        correlation_id,
                    )
            else:
                sorted_profiles = sorted(all_profiles, key=lambda p: p.finished_at)
                idx = next(
                    (i for i, p in enumerate(sorted_profiles) if p.profile_id == profile_id),
                    None,
                )
                if idx is None or idx == 0:
                    return ProfileComparison(
                        dataset_id=dataset_id,
                        baseline_profile_id="",
                        current_profile_id=profile_id,
                        status=ProfileComparisonStatus.INSUFFICIENT_HISTORY,
                        result={"signals": []},
                        message="No baseline available for drift comparison.",
                    )
                baseline_profile = sorted_profiles[idx - 1]
            policy = (
                self.profile_policy_resolver.resolve() if self.profile_policy_resolver else None
            )
            return compare_profile_snapshots(
                baseline=baseline_profile,
                current=current_profile,
                history=all_profiles,
                policy=policy,
            )
        except DataSourceQueryAuthorizationError:
            raise
        except DataSourceNotFoundError:
            raise
        except ValidationError as exc:
            raise DataSourceQueryValidationError(
                "Profile drift request could not be validated.",
                correlation_id,
            ) from exc
        except (sqlite3.Error, SQLAlchemyError, OSError) as exc:
            raise DataSourceQueryTechnicalError(
                "Profile drift query could not be completed.",
                correlation_id,
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
