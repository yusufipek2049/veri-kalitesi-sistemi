"""Dashboard HTTP yanıt modelleri."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from veri_kalitesi.dashboard import DashboardOverview
from veri_kalitesi.data_sources import DataSource
from veri_kalitesi.executions import RuleExecution
from veri_kalitesi.issues import DataQualityIssue
from veri_kalitesi.rules import QualityRule, RuleVersion


class DataSourceListItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_source_id: str
    name: str
    source_type: str
    status: str
    last_test_at: datetime | None

    @classmethod
    def from_domain(cls, source: DataSource) -> "DataSourceListItemResponse":
        return cls(
            data_source_id=source.data_source_id,
            name=source.name,
            source_type=source.source_type.value,
            status=source.status.value,
            last_test_at=source.last_test_at,
        )


class DataSourceListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    items: tuple[DataSourceListItemResponse, ...]


class RuleListItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    quality_rule_id: str
    code: str
    name: str
    dataset_id: str
    primary_dimension: str
    status: str
    rule_version_id: str
    version_no: int
    rule_type: str
    criticality: str
    created_at: datetime

    @classmethod
    def from_domain(cls, rule: QualityRule, version: RuleVersion) -> "RuleListItemResponse":
        return cls(
            quality_rule_id=rule.quality_rule_id,
            code=rule.code,
            name=rule.name,
            dataset_id=rule.dataset_id,
            primary_dimension=rule.primary_dimension.value,
            status=rule.status.value,
            rule_version_id=version.rule_version_id,
            version_no=version.version_no,
            rule_type=version.rule_type.value,
            criticality=version.criticality.value,
            created_at=version.created_at,
        )


class RuleListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    items: tuple[RuleListItemResponse, ...]


class ExecutionListItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    execution_id: str
    execution_type: str
    status: str
    workload_class: str
    rule_count: int
    source_count: int
    attempt_count: int
    error_class: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def from_domain(cls, execution: RuleExecution) -> "ExecutionListItemResponse":
        return cls(
            execution_id=execution.execution_id,
            execution_type=execution.execution_type.value,
            status=execution.status.value,
            workload_class=execution.workload_class.value,
            rule_count=len(execution.rule_version_ids),
            source_count=len(execution.source_ids),
            attempt_count=execution.attempt_count,
            error_class=execution.error_class,
            created_at=execution.created_at,
            started_at=execution.started_at,
            finished_at=execution.finished_at,
        )


class ExecutionListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    limit: int
    items: tuple[ExecutionListItemResponse, ...]


class IssueListItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    issue_id: str
    issue_no: str
    source_event_type: str
    trigger_type: str
    scope_type: str
    scope_id: str
    status: str
    priority: str
    occurrence_count: int
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime

    @classmethod
    def from_domain(cls, issue: DataQualityIssue) -> "IssueListItemResponse":
        return cls(
            issue_id=issue.issue_id,
            issue_no=issue.issue_no,
            source_event_type=issue.source_event_type.value,
            trigger_type=issue.trigger_type.value,
            scope_type=issue.scope_type.value,
            scope_id=issue.scope_id,
            status=issue.status.value,
            priority=issue.priority.value,
            occurrence_count=issue.occurrence_count,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
            last_seen_at=issue.last_seen_at,
        )


class IssueListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    limit: int
    items: tuple[IssueListItemResponse, ...]


class DashboardObservationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    quality_score_id: str
    scope_type: str
    scope_id: str | None
    score_value: Decimal | None
    score_status: str
    level: str | None
    calculated_at: datetime


class DashboardTrendPeriodResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    period_start: datetime
    period_end: datetime
    observations: tuple[DashboardObservationResponse, ...]


class DashboardMeasurementQualificationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    evaluated_scope_count: int
    reason_codes: tuple[str, ...]
    policy_version: str | None


class DashboardCriticalControlResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    reason_code: str
    passed_count: int | None
    failed_count: int | None
    not_evaluated_count: int | None


class DashboardTechnicalErrorResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    observation_count: int
    execution_count: int
    affected_source_count: int
    last_occurred_at: datetime | None


class DashboardOperationalIndicatorsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    measurement_qualification: DashboardMeasurementQualificationResponse
    critical_controls: DashboardCriticalControlResponse
    technical_errors: DashboardTechnicalErrorResponse


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    as_of: datetime
    has_data: bool
    periods: tuple[DashboardTrendPeriodResponse, ...]
    operational_indicators: DashboardOperationalIndicatorsResponse

    @classmethod
    def from_domain(
        cls,
        overview: DashboardOverview,
        *,
        correlation_id: str,
        data_origin: str,
    ) -> "DashboardSummaryResponse":
        return cls(
            data_origin=data_origin,
            correlation_id=correlation_id,
            as_of=overview.trend.as_of,
            has_data=overview.trend.has_data,
            periods=tuple(
                DashboardTrendPeriodResponse(
                    period_start=period.period_start,
                    period_end=period.period_end,
                    observations=tuple(
                        DashboardObservationResponse(
                            quality_score_id=item.quality_score_id,
                            scope_type=item.scope_type.value,
                            scope_id=item.scope_id,
                            score_value=item.score_value,
                            score_status=item.score_status.value,
                            level=item.level.value if item.level is not None else None,
                            calculated_at=item.calculated_at,
                        )
                        for item in period.observations
                    ),
                )
                for period in overview.trend.periods
            ),
            operational_indicators=DashboardOperationalIndicatorsResponse(
                measurement_qualification=DashboardMeasurementQualificationResponse(
                    status=(overview.operational_indicators.measurement_qualification.status.value),
                    evaluated_scope_count=(
                        overview.operational_indicators.measurement_qualification.evaluated_scope_count
                    ),
                    reason_codes=(
                        overview.operational_indicators.measurement_qualification.reason_codes
                    ),
                    policy_version=(
                        overview.operational_indicators.measurement_qualification.policy_version
                    ),
                ),
                critical_controls=DashboardCriticalControlResponse(
                    status=overview.operational_indicators.critical_controls.status.value,
                    reason_code=overview.operational_indicators.critical_controls.reason_code,
                    passed_count=overview.operational_indicators.critical_controls.passed_count,
                    failed_count=overview.operational_indicators.critical_controls.failed_count,
                    not_evaluated_count=(
                        overview.operational_indicators.critical_controls.not_evaluated_count
                    ),
                ),
                technical_errors=DashboardTechnicalErrorResponse(
                    observation_count=(
                        overview.operational_indicators.technical_errors.observation_count
                    ),
                    execution_count=(
                        overview.operational_indicators.technical_errors.execution_count
                    ),
                    affected_source_count=(
                        overview.operational_indicators.technical_errors.affected_source_count
                    ),
                    last_occurred_at=(
                        overview.operational_indicators.technical_errors.last_occurred_at
                    ),
                ),
            ),
        )
