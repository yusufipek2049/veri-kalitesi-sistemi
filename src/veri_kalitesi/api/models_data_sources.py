"""Veri kaynağı ve profil HTTP yanıt modelleri."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from veri_kalitesi.data_sources.models import (
    DataProfile,
    DataSource,
    ProfileComparison,
)
from veri_kalitesi.data_sources.query import DataSourceView


class DataSourceListItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_source_id: str
    name: str
    source_type: str
    status: str
    last_test_at: datetime | None
    available_actions: tuple[str, ...] = ()
    pending_activation_request_id: str | None = None
    pending_activation_maker_actor_id: str | None = None
    pending_activation_requested_at: datetime | None = None
    pending_activation_expires_at: datetime | None = None

    @classmethod
    def from_domain(cls, source: DataSource) -> "DataSourceListItemResponse":
        return cls(
            data_source_id=source.data_source_id,
            name=source.name,
            source_type=source.source_type.value,
            status=source.status.value,
            last_test_at=source.last_test_at,
        )

    @classmethod
    def from_view(cls, view: DataSourceView) -> "DataSourceListItemResponse":
        pending = view.pending_activation_request
        return cls(
            data_source_id=view.source.data_source_id,
            name=view.source.name,
            source_type=view.source.source_type.value,
            status=view.source.status.value,
            last_test_at=view.source.last_test_at,
            available_actions=view.available_actions,
            pending_activation_request_id=(
                pending.activation_request_id if pending is not None else None
            ),
            pending_activation_maker_actor_id=(
                pending.maker_actor_id if pending is not None else None
            ),
            pending_activation_requested_at=(pending.requested_at if pending is not None else None),
            pending_activation_expires_at=(pending.expires_at if pending is not None else None),
        )


class DataSourceListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    items: tuple[DataSourceListItemResponse, ...]


class ProfileComparisonRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_id: str = Field(min_length=1)
    baseline_profile_id: str = Field(min_length=1)
    current_profile_id: str = Field(min_length=1)
    policy_version: str | None = Field(default=None, min_length=1)


class ProfileComparisonItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    comparison_id: str
    dataset_id: str
    baseline_profile_id: str
    current_profile_id: str
    policy_version: str | None
    status: str
    anomaly_candidate: bool | None
    result: dict
    message: str
    created_at: datetime

    @classmethod
    def from_domain(cls, comparison: ProfileComparison) -> "ProfileComparisonItemResponse":
        return cls(
            comparison_id=comparison.comparison_id,
            dataset_id=comparison.dataset_id,
            baseline_profile_id=comparison.baseline_profile_id,
            current_profile_id=comparison.current_profile_id,
            policy_version=comparison.policy_version,
            status=comparison.status.value,
            anomaly_candidate=comparison.anomaly_candidate,
            result=comparison.result,
            message=comparison.message,
            created_at=comparison.created_at,
        )


class ProfileComparisonResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    item: ProfileComparisonItemResponse


class ProfileSnapshotListItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str
    dataset_id: str
    execution_id: str
    method: str
    status: str
    sample_ratio: float | None
    duration_ms: int
    started_at: datetime
    finished_at: datetime

    @classmethod
    def from_domain(cls, profile: DataProfile) -> "ProfileSnapshotListItemResponse":
        return cls(
            profile_id=profile.profile_id,
            dataset_id=profile.dataset_id,
            execution_id=profile.execution_id,
            method=profile.method.value,
            status=profile.status.value,
            sample_ratio=profile.sample_ratio,
            duration_ms=profile.duration_ms,
            started_at=profile.started_at,
            finished_at=profile.finished_at,
        )


class ProfileSnapshotListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    dataset_id: str
    limit: int
    items: tuple[ProfileSnapshotListItemResponse, ...]


class ProfileSnapshotDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    profile_id: str
    dataset_id: str
    execution_id: str
    method: str
    status: str
    sample_ratio: float | None
    duration_ms: int
    metrics: dict[str, Any]
    started_at: datetime
    finished_at: datetime

    @classmethod
    def from_domain(
        cls,
        profile: DataProfile,
        *,
        data_origin: str,
        correlation_id: str,
    ) -> "ProfileSnapshotDetailResponse":
        return cls(
            data_origin=data_origin,
            correlation_id=correlation_id,
            profile_id=profile.profile_id,
            dataset_id=profile.dataset_id,
            execution_id=profile.execution_id,
            method=profile.method.value,
            status=profile.status.value,
            sample_ratio=profile.sample_ratio,
            duration_ms=profile.duration_ms,
            metrics=profile.metrics,
            started_at=profile.started_at,
            finished_at=profile.finished_at,
        )


class DriftJudgmentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    item: ProfileComparisonItemResponse


class DataSourceCreateRequest(BaseModel):
    """Veri kaynağı oluşturma için girdi modeli."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    name: str = Field(min_length=1, max_length=250)
    source_type: str = Field(pattern=r"^POSTGRESQL$")
    host: str = Field(min_length=1, max_length=500)
    port: int = Field(default=5432, ge=1, le=65535)
    database: str = Field(min_length=1, max_length=250)
    schema_name: str = Field(alias="schema", min_length=1, max_length=120)
    secret_reference: str = Field(min_length=16, max_length=500, pattern=r"^secret://")
    ssl_mode: str = Field(default="verify-full", pattern=r"^(require|verify-ca|verify-full)$")
    connect_timeout_seconds: int = Field(default=5, ge=1, le=60)
    statement_timeout_ms: int = Field(default=5000, ge=100, le=120000)
    connection_parameters: dict[str, Any] = Field(default_factory=dict)


class DataSourceActivationDecisionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    decision: str = Field(pattern=r"^(APPROVE|REJECT)$")
    reason_code: str = Field(min_length=1, max_length=120)


class DataSourcePassivationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reason_code: str = Field(min_length=1, max_length=120)


class DataSourceMutationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    item: DataSourceListItemResponse
    activation_request_status: str | None = None
    replayed: bool = False


class DataSourceDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_source_id: str
    name: str
    source_type: str
    status: str
    owner_user_id: str | None
    last_test_at: datetime | None
    last_test_result: str | None
    revision: int

    @classmethod
    def from_domain(cls, source: DataSource) -> "DataSourceDetailResponse":
        return cls(
            data_source_id=source.data_source_id,
            name=source.name,
            source_type=source.source_type.value,
            status=source.status.value,
            owner_user_id=source.owner_user_id,
            last_test_at=source.last_test_at,
            last_test_result=source.last_test_result,
            revision=source.revision,
        )
