"""Dashboard HTTP yant modelleri."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from veri_kalitesi.audit.models import AuditEvent, AuditQueryPage
from veri_kalitesi.executions.models import RuleExecution
from veri_kalitesi.issues.models import DataQualityIssue, IssuePriority
from veri_kalitesi.reporting.models import ReportPreview, ReportSummaryRow, Report
from veri_kalitesi.reporting.scheduling import ReportSchedule
from veri_kalitesi.rules.models import QualityRule, RuleTestResult, RuleVersion


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
    ir_version: str = "DQ_RULE_IR_V1"
    rule_source: str = "TEMPLATE"
    scope_type: str = "DATASET"
    criticality: str
    created_at: datetime
    available_actions: tuple[str, ...] = ()
    pending_approval_request_id: str | None = None

    @classmethod
    def from_domain(
        cls,
        rule: QualityRule,
        version: RuleVersion,
        *,
        available_actions: tuple[str, ...] = (),
        pending_approval_request_id: str | None = None,
    ) -> "RuleListItemResponse":
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
            ir_version=version.ir_version,
            rule_source=version.definition_source.value,
            scope_type=version.scope_type.value,
            criticality=version.criticality.value,
            created_at=version.created_at,
            available_actions=available_actions,
            pending_approval_request_id=pending_approval_request_id,
        )


class RuleListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    items: tuple[RuleListItemResponse, ...]


class RuleCreateRequest(BaseModel):
    """Kural oluşturma için girdi modeli."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=250)
    dataset_id: str = Field(min_length=1)
    rule_type: str = Field(min_length=1)
    primary_dimension: str = Field(min_length=1)
    threshold: float = Field(ge=0, le=100)
    weight: float = Field(gt=0)
    criticality: str = Field(min_length=1)
    owner_user_id: str = Field(min_length=1)
    parameters: dict = Field(default_factory=dict)


class RuleMutationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    item: RuleListItemResponse


class RuleVersionCreateRequest(BaseModel):
    """Kural sürümü oluşturma için girdi modeli."""

    model_config = ConfigDict(frozen=True)

    threshold: float = Field(ge=0, le=100)
    weight: float = Field(gt=0)
    criticality: str = Field(min_length=1)
    parameters: dict = Field(default_factory=dict)


class RuleTestRequest(BaseModel):
    """Kural testi çalıştırma için girdi modeli."""

    model_config = ConfigDict(frozen=True)

    rule_version_id: str = Field(min_length=1)
    limit: int = Field(default=10_000, ge=1, le=10_000)


class RuleTestResultResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_test_result_id: str
    rule_version_id: str
    status: str
    record_limit: int
    checked_count: int
    passed_count: int
    failed_count: int
    not_evaluated_count: int
    success_rate: float | None
    preview_score: float | None
    official_score_included: bool
    error_class: str | None
    message: str
    created_at: datetime

    @classmethod
    def from_domain(cls, result: RuleTestResult) -> "RuleTestResultResponse":
        return cls(
            rule_test_result_id=result.rule_test_result_id,
            rule_version_id=result.rule_version_id,
            status=result.status.value,
            record_limit=result.record_limit,
            checked_count=result.checked_count,
            passed_count=result.passed_count,
            failed_count=result.failed_count,
            not_evaluated_count=result.not_evaluated_count,
            success_rate=result.success_rate,
            preview_score=result.preview_score,
            official_score_included=result.official_score_included,
            error_class=result.error_class,
            message=result.message,
            created_at=result.created_at,
        )


class RuleActivationRequest(BaseModel):
    """Kural aktivasyonu için girdi modeli."""

    model_config = ConfigDict(frozen=True)

    quality_rule_id: str = Field(min_length=1)


class RuleApprovalRequestPayload(BaseModel):
    """Kural onay isteği için girdi modeli."""

    model_config = ConfigDict(frozen=True)

    quality_rule_id: str = Field(min_length=1)


class RuleApprovalDecisionRequest(BaseModel):
    """Kural onay kararı için girdi modeli."""

    model_config = ConfigDict(frozen=True)

    approval_request_id: str = Field(min_length=1)
    decision: str = Field(min_length=1, pattern=r"^(APPROVE|REJECT)$")
    reason_code: str = Field(min_length=1, max_length=120)


class RuleApprovalWithdrawRequest(BaseModel):
    """Kural onay geri çekme için girdi modeli."""

    model_config = ConfigDict(frozen=True)

    approval_request_id: str = Field(min_length=1)
    reason_code: str = Field(min_length=1, max_length=120)


class RulePassivationRequest(BaseModel):
    """Kural pasifleştirme için girdi modeli."""

    model_config = ConfigDict(frozen=True)

    quality_rule_id: str = Field(min_length=1)


class ExecutionListItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    execution_id: str
    execution_type: str
    execution_mode: str
    status: str
    workload_class: str
    rule_count: int
    source_count: int
    attempt_count: int
    error_class: str | None
    progress_percent: int = 0
    blocked_reason_code: str | None = None
    available_actions: list[str] = []
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def from_domain(cls, execution: RuleExecution) -> "ExecutionListItemResponse":
        status_value = execution.status.value
        if status_value in {"SUCCESS", "PARTIAL"}:
            progress_percent = 100
        elif status_value == "RUNNING":
            progress_percent = 0
        else:
            progress_percent = 0

        if status_value == "RUNNING":
            available_actions = ["REQUEST_CANCEL"]
        else:
            available_actions = []

        return cls(
            execution_id=execution.execution_id,
            execution_type=execution.execution_type.value,
            execution_mode=execution.execution_mode.value,
            status=status_value,
            workload_class=execution.workload_class.value,
            rule_count=len(execution.rule_version_ids),
            source_count=len(execution.source_ids),
            attempt_count=execution.attempt_count,
            error_class=execution.error_class,
            progress_percent=progress_percent,
            blocked_reason_code=None,
            available_actions=available_actions,
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
    version: int
    available_actions: tuple[str, ...] = ()
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime

    @classmethod
    def from_domain(
        cls,
        issue: DataQualityIssue,
        *,
        available_actions: tuple[str, ...] = (),
    ) -> "IssueListItemResponse":
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
            version=issue.version,
            available_actions=available_actions,
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


class IssueMutationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: int = Field(ge=1)


class IssueVerificationRequest(BaseModel):
    """Farklı aktörle doğrulama için girdi modeli."""

    model_config = ConfigDict(frozen=True)

    version: int = Field(ge=1)
    verification_reference_id: UUID


class IssueResolutionDraftRequest(BaseModel):
    """Korumalı çözüm kaydı için girdi modeli."""

    model_config = ConfigDict(frozen=True)

    version: int = Field(ge=1)
    root_cause: str = Field(min_length=1, max_length=4000)
    corrective_action: str = Field(min_length=1, max_length=4000)
    evidence_reference_id: UUID
    completed_at: datetime


class IssueMutationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    item: IssueListItemResponse


class IssueReassignmentRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: int = Field(ge=1)
    assignee_user_id: UUID
    priority: IssuePriority


class IssueAssigneeOptionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: UUID
    display_name: str = Field(min_length=1, max_length=160)


class IssueAssigneeOptionsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    items: tuple[IssueAssigneeOptionResponse, ...]


class ReportSummaryRowResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    score_value: Decimal | None
    score_status: str
    level: str | None
    calculated_at: datetime

    @classmethod
    def from_domain(cls, row: ReportSummaryRow) -> "ReportSummaryRowResponse":
        return cls(
            source_id=row.source_id,
            score_value=row.score_value,
            score_status=row.score_status.value,
            level=row.level.value if row.level is not None else None,
            calculated_at=row.calculated_at,
        )


class ReportSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    report_type: str
    created_at: datetime
    period_start: datetime
    period_end: datetime
    source_count: int
    calculated_source_count: int
    average_score: Decimal | None
    policy_version: str
    masking_mode: str
    rows: tuple[ReportSummaryRowResponse, ...]

    @classmethod
    def from_domain(
        cls,
        preview: ReportPreview,
        *,
        correlation_id: str,
        data_origin: str,
    ) -> "ReportSummaryResponse":
        return cls(
            data_origin=data_origin,
            correlation_id=correlation_id,
            report_type=preview.report_type.value,
            created_at=preview.created_at,
            period_start=preview.filters.start_at,
            period_end=preview.filters.end_at,
            source_count=preview.source_count,
            calculated_source_count=preview.calculated_source_count,
            average_score=preview.average_score,
            policy_version=preview.policy_version,
            masking_mode=preview.masking_mode,
            rows=tuple(ReportSummaryRowResponse.from_domain(row) for row in preview.rows),
        )


class AuditEventListItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence_no: int
    event_id: str
    occurred_at: datetime
    actor_id: str
    actor_type: str | None
    correlation_id: str
    action: str
    object_type: str
    object_id: str | None
    result: str
    reason_code: str
    redacted_field_count: int

    @classmethod
    def from_domain(cls, event: AuditEvent) -> "AuditEventListItemResponse":
        return cls(
            sequence_no=event.sequence_no,
            event_id=event.event_id,
            occurred_at=event.occurred_at,
            actor_id=event.actor_id,
            actor_type=event.actor_type,
            correlation_id=event.correlation_id,
            action=event.action,
            object_type=event.object_type,
            object_id=event.object_id,
            result=event.result.value,
            reason_code=event.reason_code,
            redacted_field_count=len(event.redacted_fields),
        )


class AuditEventListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    period_start: datetime
    period_end: datetime
    integrity_valid: bool
    integrity_checked_count: int
    next_after_sequence_no: int | None
    through_sequence_no: int
    page_size: int
    policy_version: str
    items: tuple[AuditEventListItemResponse, ...]

    @classmethod
    def from_domain(
        cls,
        page: AuditQueryPage,
        *,
        period_start: datetime,
        period_end: datetime,
        page_size: int,
        correlation_id: str,
        data_origin: str,
    ) -> "AuditEventListResponse":
        return cls(
            data_origin=data_origin,
            correlation_id=correlation_id,
            period_start=period_start,
            period_end=period_end,
            integrity_valid=page.integrity.valid,
            integrity_checked_count=page.integrity.checked_count,
            next_after_sequence_no=page.next_after_sequence_no,
            through_sequence_no=page.through_sequence_no,
            page_size=page_size,
            policy_version=page.policy_version,
            items=tuple(AuditEventListItemResponse.from_domain(event) for event in page.events),
        )


class ExecutionStartRequest(BaseModel):
    """Manuel çalıştırma başlatma için girdi modeli."""

    model_config = ConfigDict(frozen=True)

    rule_version_ids: tuple[str, ...] = Field(min_length=1)
    source_ids: tuple[str, ...] = Field(default_factory=tuple)


class ExecutionStartResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    item: ExecutionListItemResponse


class ExecutionCancelRequest(BaseModel):
    """Çalıştırma iptali için girdi modeli."""

    model_config = ConfigDict(frozen=True)

    reason: str = Field(min_length=1, max_length=500)


class DevelopmentUserInfoResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: str
    display_name: str
    roles: str


class DevelopmentUserListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    correlation_id: str
    items: tuple[DevelopmentUserInfoResponse, ...]


class ReportRequestResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: str
    report_type: str
    format: str
    status: str
    file_size: int | None
    expires_at: datetime | None
    created_at: datetime | None
    completed_at: datetime | None
    failure_reason: str | None

    @classmethod
    def from_domain(cls, report: Report) -> "ReportRequestResponse":
        return cls(
            report_id=report.report_id,
            report_type=report.report_type.value,
            format=report.format.value,
            status=report.status.value,
            file_size=report.file_size,
            expires_at=report.expires_at,
            created_at=report.created_at,
            completed_at=report.completed_at,
            failure_reason=report.failure_reason,
        )


class ReportListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    items: tuple[ReportRequestResponse, ...]


class ReportCreateRequest(BaseModel):
    report_type: str
    format: str
    parameters: dict = {}
    reason_code: str = ""
    sensitivity_level: str | None = None


class ReportCreateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    report: ReportRequestResponse


class ReportScheduleItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    schedule_id: str
    name: str
    report_type: str
    format: str
    schedule_type: str
    timezone_name: str
    is_active: bool
    next_run_at: datetime | None
    created_by: str
    created_at: datetime | None
    last_triggered_at: datetime | None

    @classmethod
    def from_domain(cls, schedule: ReportSchedule) -> "ReportScheduleItemResponse":
        return cls(
            schedule_id=schedule.schedule_id,
            name=schedule.name,
            report_type=schedule.report_type.value,
            format=schedule.format.value,
            schedule_type=schedule.schedule_type.value,
            timezone_name=schedule.timezone_name,
            is_active=schedule.is_active,
            next_run_at=schedule.next_run_at,
            created_by=schedule.created_by,
            created_at=schedule.created_at,
            last_triggered_at=schedule.last_triggered_at,
        )


class ReportScheduleListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    items: tuple[ReportScheduleItemResponse, ...]


class ReportScheduleCreateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    report_type: str
    format: str
    schedule_type: str
    timezone_name: str
    parameters: dict = {}
    sensitivity_level: str | None = None
    recipients: tuple[str, ...] = ()
    local_time: str | None = None
    once_at: datetime | None = None
    day_of_week: int | None = None
    day_of_month: int | None = None


class ReportScheduleCreateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    item: ReportScheduleItemResponse
    preview: tuple[str, ...]


class ReportScheduleTriggerResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    triggered_report_ids: tuple[str, ...]
    triggered_count: int


class ReportScheduleDeleteResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    deleted: bool = True


# ── Supplementary models for routes not yet extracted (Slice 2/3) ──


class _EvidenceComponentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    value: object | None = None
    references: tuple[str, ...] = ()

    @classmethod
    def from_domain(cls, component: object) -> "_EvidenceComponentResponse":
        from veri_kalitesi.issues.investigation import EvidenceComponent

        assert isinstance(component, EvidenceComponent)
        return cls(
            source=component.source.value,
            value=component.value,
            references=component.references,
        )


class InvestigationEvidenceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    issue_id: str
    rule_description: _EvidenceComponentResponse
    expected_summary: _EvidenceComponentResponse
    actual_summary: _EvidenceComponentResponse
    masked_samples: _EvidenceComponentResponse
    similar_history: _EvidenceComponentResponse
    recommendation: _EvidenceComponentResponse
    rule_version_id: str | None
    ir_version: str | None
    evidence_fingerprint: str | None
    evidence_query_reference: str | None
    evidence_plan_reference: str | None
    authorization_policy_version: str

    @classmethod
    def from_domain(
        cls,
        evidence: object,
        *,
        data_origin: str,
        correlation_id: str,
    ) -> "InvestigationEvidenceResponse":
        from veri_kalitesi.issues.investigation import InvestigationEvidence

        assert isinstance(evidence, InvestigationEvidence)
        return cls(
            data_origin=data_origin,
            correlation_id=correlation_id,
            issue_id=evidence.issue_id,
            rule_description=_EvidenceComponentResponse.from_domain(evidence.rule_description),
            expected_summary=_EvidenceComponentResponse.from_domain(evidence.expected_summary),
            actual_summary=_EvidenceComponentResponse.from_domain(evidence.actual_summary),
            masked_samples=_EvidenceComponentResponse.from_domain(evidence.masked_samples),
            similar_history=_EvidenceComponentResponse.from_domain(evidence.similar_history),
            recommendation=_EvidenceComponentResponse.from_domain(evidence.recommendation),
            rule_version_id=evidence.rule_version_id,
            ir_version=evidence.ir_version,
            evidence_fingerprint=evidence.evidence_fingerprint,
            evidence_query_reference=evidence.evidence_query_reference,
            evidence_plan_reference=evidence.evidence_plan_reference,
            authorization_policy_version=evidence.authorization_policy_version,
        )


class IssueCreateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1, max_length=500)
    scope_type: str = Field(min_length=1)
    scope_id: str = Field(min_length=1)
    priority: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


class ExecutionDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    execution: ExecutionListItemResponse
    rule_results: tuple[dict, ...] = ()

    @classmethod
    def from_domain(
        cls,
        execution: RuleExecution,
        results: list | tuple,
        *,
        data_origin: str,
        correlation_id: str,
    ) -> "ExecutionDetailResponse":
        return cls(
            data_origin=data_origin,
            correlation_id=correlation_id,
            execution=ExecutionListItemResponse.from_domain(execution),
            rule_results=tuple(
                {
                    "rule_version_id": r.rule_version_id,
                    "population_count": r.population_count,
                    "eligible_count": r.eligible_count,
                    "evaluated_count": r.evaluated_count,
                    "passed_count": r.passed_count,
                    "failed_count": r.failed_count,
                    "excluded_count": r.excluded_count,
                    "technical_error_count": r.technical_error_count,
                    "unknown_count": r.unknown_count,
                    "measurement_status": (
                        r.measurement_status.value if r.measurement_status else None
                    ),
                }
                for r in results
            ),
        )


class ScoreItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    quality_score_id: str
    execution_id: str
    rule_version_id: str | None
    scope_type: str
    scope_id: str | None
    score_value: float | None
    score_status: str
    level: str | None
    measurement_status: str | None
    calculated_at: datetime
    publication_id: str | None
    policy_version: str | None
    included_component_count: int | None
    excluded_component_count: int | None

    @classmethod
    def from_domain(cls, score: object) -> "ScoreItemResponse":
        from veri_kalitesi.scoring.models import QualityScore

        assert isinstance(score, QualityScore)
        return cls(
            quality_score_id=score.quality_score_id,
            execution_id=score.execution_id,
            rule_version_id=score.rule_version_id,
            scope_type=score.scope_type.value,
            scope_id=score.scope_id,
            score_value=float(score.score_value) if score.score_value is not None else None,
            score_status=score.score_status.value,
            level=score.level.value if score.level else None,
            measurement_status=(
                score.measurement_status.value if score.measurement_status else None
            ),
            calculated_at=score.calculated_at,
            publication_id=score.publication_id,
            policy_version=score.policy_version,
            included_component_count=score.included_component_count,
            excluded_component_count=score.excluded_component_count,
        )


class ScoreListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    items: tuple[ScoreItemResponse, ...]


class ScoreRuleHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    rule_version_id: str
    items: tuple[ScoreItemResponse, ...]


class ScorePublicationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    publication_id: str
    execution_id: str
    period: str
    status: str
    policy_version: str
    published_at: datetime
    superseded_at: datetime | None = None


class ScoreDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    score: ScoreItemResponse
    publication: ScorePublicationResponse | None = None
    available_actions: tuple[str, ...] = ()
    has_contribution_graph: bool = False


class ScoreComparisonResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    current_score_id: str
    previous_score_id: str
    comparison_status: str
    reason_codes: tuple[str, ...]
    delta_value: float | None = None


class ScoreReproductionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    original_score_id: str
    matches: bool
    delta_value: float | None = None
    delta_level: bool = False
    reason_codes: tuple[str, ...] = ()
    reproduced_value: float | None = None
    reproduced_level: str | None = None
