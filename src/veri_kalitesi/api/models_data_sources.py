"""Veri kaynağı ve profil HTTP yanıt modelleri."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from veri_kalitesi.data_sources.models import DataSource
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
    pending_deactivation_request_id: str | None = None
    pending_deactivation_maker_actor_id: str | None = None
    pending_deactivation_requested_at: datetime | None = None

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
        pending_deact = view.pending_deactivation_request
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
            pending_deactivation_request_id=(
                pending_deact.activation_request_id if pending_deact is not None else None
            ),
            pending_deactivation_maker_actor_id=(
                pending_deact.maker_actor_id if pending_deact is not None else None
            ),
            pending_deactivation_requested_at=(
                pending_deact.requested_at if pending_deact is not None else None
            ),
        )


class DataSourceListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    items: tuple[DataSourceListItemResponse, ...]


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
