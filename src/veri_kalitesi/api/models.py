"""Dashboard HTTP yant modelleri."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from veri_kalitesi.audit.models import AuditEvent, AuditQueryPage, AuditSummary
from veri_kalitesi.data_sources.models import Criticality
from veri_kalitesi.executions.models import RuleExecution
from veri_kalitesi.governance.models import GovernanceApprovalItem
from veri_kalitesi.issues.models import DataQualityIssue, IssuePriority
from veri_kalitesi.rules.models import QualityDimension, QualityRule, RuleTestResult, RuleVersion
from veri_kalitesi.scoring.errors import ScoringValidationError
from veri_kalitesi.scoring.models import ScoringConfiguration, ScoringConfigurationApproval


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


class RuleDetailResponse(BaseModel):
    """Tek kural detay modeli — tanim (SQL dahil) icerir."""

    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    item: RuleListItemResponse
    definition: dict[str, Any] = {}


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


class ExecutionDatasetRef(BaseModel):
    """Calistirma kapsamindaki cozumlenmis dataset/kaynak referansi."""

    model_config = ConfigDict(frozen=True)

    dataset_id: str
    name: str
    namespace: str
    source_id: str
    source_name: str


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
    datasets: tuple[ExecutionDatasetRef, ...] = ()
    schedule_id: str | None = None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def from_domain(
        cls,
        execution: RuleExecution,
        *,
        datasets: tuple[ExecutionDatasetRef, ...] | list[ExecutionDatasetRef] = (),
        schedule_id: str | None = None,
    ) -> "ExecutionListItemResponse":
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
            datasets=tuple(datasets),
            schedule_id=schedule_id,
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
    title: str = ""
    source_event_type: str
    trigger_type: str
    scope_type: str
    scope_id: str
    scope_display_name: str | None = None
    scope_parent_name: str | None = None
    status: str
    priority: str
    occurrence_count: int
    version: int
    source_execution_id: str | None = None
    source_rule_version_id: str | None = None
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
            title=issue.title,
            source_event_type=issue.source_event_type.value,
            trigger_type=issue.trigger_type.value,
            scope_type=issue.scope_type.value,
            scope_id=issue.scope_id,
            status=issue.status.value,
            priority=issue.priority.value,
            occurrence_count=issue.occurrence_count,
            version=issue.version,
            source_execution_id=issue.source_execution_id,
            source_rule_version_id=issue.source_rule_version_id,
            available_actions=available_actions,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
            last_seen_at=issue.last_seen_at,
        )

    def with_scope_display(
        self,
        *,
        scope_display_name: str | None,
        scope_parent_name: str | None,
    ) -> "IssueListItemResponse":
        """Return a copy with resolved scope display names."""
        return self.model_copy(
            update={
                "scope_display_name": scope_display_name,
                "scope_parent_name": scope_parent_name,
            }
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

    user_id: str = Field(min_length=1, max_length=160)
    display_name: str = Field(min_length=1, max_length=160)


class IssueAssigneeOptionsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    items: tuple[IssueAssigneeOptionResponse, ...]


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
    old_value_summary: dict[str, Any] | None = None
    new_value_summary: dict[str, Any] | None = None
    redacted_fields: tuple[str, ...] = ()
    event_hash: str = ""
    previous_event_hash: str = ""

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
            old_value_summary=dict(event.old_value_summary) if event.old_value_summary else None,
            new_value_summary=dict(event.new_value_summary) if event.new_value_summary else None,
            redacted_fields=tuple(event.redacted_fields),
            event_hash=event.event_hash,
            previous_event_hash=event.previous_event_hash,
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
    first_invalid_event_id: str | None = None
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
            first_invalid_event_id=page.integrity.first_invalid_event_id,
            next_after_sequence_no=page.next_after_sequence_no,
            through_sequence_no=page.through_sequence_no,
            page_size=page_size,
            policy_version=page.policy_version,
            items=tuple(AuditEventListItemResponse.from_domain(event) for event in page.events),
        )


class AuditEventGroupedResponse(AuditEventListResponse):
    """Correlation kimliğine göre gruplanmış audit olayları yanıtı."""

    grouped_by: Literal["correlation_id"] = "correlation_id"


class AuditSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_count: int
    result_distribution: dict[str, int]
    action_distribution: dict[str, int]
    top_actors: list[dict[str, int | str]]
    period_start: datetime
    period_end: datetime

    @classmethod
    def from_domain(cls, summary: AuditSummary) -> "AuditSummaryResponse":
        return cls(
            total_count=summary.total_count,
            result_distribution=dict(summary.result_distribution),
            action_distribution=dict(summary.action_distribution),
            top_actors=[
                {"actor_id": actor.actor_id, "count": actor.count} for actor in summary.top_actors
            ],
            period_start=summary.period_start,
            period_end=summary.period_end,
        )


class ExecutionStartRequest(BaseModel):
    """Manuel çalıştırma başlatma için girdi modeli."""

    model_config = ConfigDict(frozen=True)

    rule_version_ids: tuple[str, ...] = Field(min_length=1)
    source_ids: tuple[str, ...] = Field(default_factory=tuple)
    idempotency_key: str = ""
    execution_mode: str = "OFFICIAL"


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
    actor_id: str = ""


class DevelopmentUserListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    correlation_id: str
    items: tuple[DevelopmentUserInfoResponse, ...]


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


class IssueEvidenceItemResponse(BaseModel):
    """Kayitli kanit. ``evidence_id`` cozum formunun referans hedefidir."""

    model_config = ConfigDict(frozen=True)

    evidence_id: str
    issue_id: str
    kind: str
    label: str
    execution_id: str
    rule_version_id: str | None = None
    evaluated_count: int | None = None
    failed_count: int | None = None
    measurement_status: str | None = None
    fingerprint: str | None = None
    query_reference: str | None = None
    plan_reference: str | None = None
    content_digest: str
    observed_at: datetime
    captured_at: datetime
    captured_by: str
    original_filename: str | None = None
    safe_filename: str | None = None
    detected_media_type: str | None = None
    byte_size: int | None = None
    sha256_digest: str | None = None
    scan_status: str | None = None
    scan_reason_code: str | None = None
    scan_completed_at: datetime | None = None
    classification: str | None = None
    uploaded_by: str | None = None
    uploaded_at: datetime | None = None

    @classmethod
    def from_domain(cls, record: object, file: object = None) -> "IssueEvidenceItemResponse":
        from veri_kalitesi.issues.evidence import IssueEvidenceRecord
        from veri_kalitesi.issues.evidence_files import IssueEvidenceFileRecord

        assert isinstance(record, IssueEvidenceRecord)
        upload = file if isinstance(file, IssueEvidenceFileRecord) else None
        return cls(
            evidence_id=record.evidence_id,
            issue_id=record.issue_id,
            kind=record.kind.value,
            label=record.label,
            execution_id=record.execution_id,
            rule_version_id=record.rule_version_id,
            evaluated_count=record.evaluated_count,
            failed_count=record.failed_count,
            measurement_status=record.measurement_status,
            fingerprint=record.fingerprint,
            query_reference=record.query_reference,
            plan_reference=record.plan_reference,
            content_digest=record.content_digest,
            observed_at=record.observed_at,
            captured_at=record.captured_at,
            captured_by=record.captured_by,
            original_filename=upload.original_filename if upload else None,
            safe_filename=upload.safe_filename if upload else None,
            detected_media_type=upload.detected_media_type if upload else None,
            byte_size=upload.byte_size if upload else None,
            sha256_digest=upload.sha256_digest if upload else None,
            scan_status=upload.scan_status.value if upload else None,
            scan_reason_code=upload.scan_reason_code if upload else None,
            scan_completed_at=upload.scan_completed_at if upload else None,
            classification=upload.classification.value if upload else None,
            uploaded_by=upload.uploaded_by if upload else None,
            uploaded_at=upload.uploaded_at if upload else None,
        )


class IssueEvidenceCandidateResponse(BaseModel):
    """Henuz kaydedilmemis kanit adayi (calistirma sonucu veya logu)."""

    model_config = ConfigDict(frozen=True)

    candidate_key: str
    kind: str
    label: str
    execution_id: str
    rule_version_id: str | None = None
    evaluated_count: int | None = None
    failed_count: int | None = None
    measurement_status: str | None = None
    observed_at: datetime

    @classmethod
    def from_domain(cls, candidate: object) -> "IssueEvidenceCandidateResponse":
        from veri_kalitesi.issues.evidence import IssueEvidenceCandidate

        assert isinstance(candidate, IssueEvidenceCandidate)
        return cls(
            candidate_key=candidate.candidate_key,
            kind=candidate.kind.value,
            label=candidate.label,
            execution_id=candidate.execution_id,
            rule_version_id=candidate.rule_version_id,
            evaluated_count=candidate.evaluated_count,
            failed_count=candidate.failed_count,
            measurement_status=candidate.measurement_status,
            observed_at=candidate.observed_at,
        )


class IssueEvidenceListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    issue_id: str
    items: tuple[IssueEvidenceItemResponse, ...] = ()
    candidates: tuple[IssueEvidenceCandidateResponse, ...] = ()


class IssueEvidenceCaptureRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_key: str = Field(min_length=1, max_length=200)


class IssueEvidenceCaptureResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    item: IssueEvidenceItemResponse


class IssueCreateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1, max_length=500)
    scope_type: str = Field(min_length=1)
    scope_id: str = Field(min_length=1)
    priority: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


class JobInfoRef(BaseModel):
    """Job kuyruğu lifecycle bilgisi (execution_id = job_id)."""

    model_config = ConfigDict(frozen=True)

    job_id: str
    status: str
    queue_position: int | None = None
    worker_id: str | None = None
    leased_until: datetime | None = None
    attempt_count: int = 0
    last_error_class: str | None = None
    completed_at: datetime | None = None
    completion_outcome: str | None = None


class ExecutionDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    execution: ExecutionListItemResponse
    rule_results: tuple[dict, ...] = ()
    rule_definitions: tuple[dict, ...] = ()
    job_info: JobInfoRef | None = None

    @classmethod
    def from_domain(
        cls,
        execution: RuleExecution,
        results: list | tuple,
        *,
        data_origin: str,
        correlation_id: str,
        rule_definitions: list | tuple = (),
        datasets: tuple[ExecutionDatasetRef, ...] | list[ExecutionDatasetRef] = (),
        schedule_id: str | None = None,
        job_info: JobInfoRef | None = None,
    ) -> "ExecutionDetailResponse":
        return cls(
            data_origin=data_origin,
            correlation_id=correlation_id,
            execution=ExecutionListItemResponse.from_domain(
                execution, datasets=datasets, schedule_id=schedule_id
            ),
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
            rule_definitions=tuple(rule_definitions),
            job_info=job_info,
        )


class ScoreItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    quality_score_id: str
    execution_id: str
    rule_version_id: str | None
    scope_type: str
    scope_id: str | None
    scope_display_name: str | None = None
    scope_parent_name: str | None = None
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

    def with_scope_display(
        self,
        *,
        scope_display_name: str | None,
        scope_parent_name: str | None,
    ) -> "ScoreItemResponse":
        """Return a copy with resolved scope display names."""
        return self.model_copy(
            update={
                "scope_display_name": scope_display_name,
                "scope_parent_name": scope_parent_name,
            }
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
    calculation_details: dict[str, Any] | None = None
    contribution_graph: dict[str, Any] | None = None


class ScoreTrendPointResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    score_value: float | None
    level: str | None
    change: float | None
    score_count: int = 0


class ScoreTrendResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    scope_type: str
    scope_id: str | None
    granularity: str
    items: tuple[ScoreTrendPointResponse, ...]


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


class GovernanceApprovalItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    approval_request_id: str
    domain: str
    request_type: str
    status: str
    object_type: str
    object_id: str
    object_name: str
    scope_type: str
    scope_id: str
    maker_actor_id: str
    checker_actor_id: str | None
    reason_code: str | None
    requested_at: datetime
    decided_at: datetime | None
    expires_at: datetime | None
    policy_version: str
    available_actions: tuple[str, ...] = ()
    change_summary: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, item: GovernanceApprovalItem) -> "GovernanceApprovalItemResponse":
        return cls(
            approval_request_id=item.approval_request_id,
            domain=item.domain.value,
            request_type=item.request_type.value,
            status=item.status.value,
            object_type=item.object_type,
            object_id=item.object_id,
            object_name=item.object_name,
            scope_type=item.scope_type,
            scope_id=item.scope_id,
            maker_actor_id=item.maker_actor_id,
            checker_actor_id=item.checker_actor_id,
            reason_code=item.reason_code,
            requested_at=item.requested_at,
            decided_at=item.decided_at,
            expires_at=item.expires_at,
            policy_version=item.policy_version,
            available_actions=item.available_actions,
            change_summary=dict(item.change_summary),
        )


class GovernanceApprovalListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    view: str
    items: tuple[GovernanceApprovalItemResponse, ...]


class GovernanceApprovalDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    item: GovernanceApprovalItemResponse


class GovernanceApprovalCreateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_type: str
    object_id: str
    reason_code: str
    new_owner_user_id: str | None = None
    proposed_changes: dict[str, Any] = Field(default_factory=dict)


class GovernanceApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: str
    reason_code: str


class GovernanceApprovalWithdrawRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    reason_code: str


class ScoringThresholdSetResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    critical_upper_exclusive: str
    risky_upper_exclusive: str
    acceptable_upper_exclusive: str


class ScoringConfigurationItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    configuration_id: str
    version: str
    is_active: bool
    activated_at: datetime | None
    created_by: str
    created_at: datetime
    threshold_set: ScoringThresholdSetResponse
    dimension_weights: dict[str, str]
    criticality_weights: dict[str, str]
    dataset_id: str | None = None

    @classmethod
    def from_domain(cls, configuration: ScoringConfiguration) -> "ScoringConfigurationItemResponse":
        return cls(
            configuration_id=configuration.configuration_id,
            version=configuration.version,
            is_active=configuration.is_active,
            activated_at=configuration.activated_at,
            created_by=configuration.created_by,
            created_at=configuration.created_at,
            threshold_set=ScoringThresholdSetResponse(
                version=configuration.threshold_set.version,
                critical_upper_exclusive=str(configuration.threshold_set.critical_upper_exclusive),
                risky_upper_exclusive=str(configuration.threshold_set.risky_upper_exclusive),
                acceptable_upper_exclusive=str(
                    configuration.threshold_set.acceptable_upper_exclusive
                ),
            ),
            dimension_weights={
                dimension.value: str(weight)
                for dimension, weight in configuration.dimension_weights.items()
            },
            criticality_weights={
                criticality.value: str(weight)
                for criticality, weight in configuration.criticality_weights.items()
            },
            dataset_id=configuration.dataset_id,
        )


class ScoringConfigurationApprovalItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    approval_id: str
    configuration_id: str
    status: str
    maker_actor_id: str
    checker_actor_id: str | None
    policy_version: str
    decision_reason_code: str | None
    requested_at: datetime
    decided_at: datetime | None

    @classmethod
    def from_domain(
        cls, approval: ScoringConfigurationApproval
    ) -> "ScoringConfigurationApprovalItemResponse":
        return cls(
            approval_id=approval.approval_id,
            configuration_id=approval.configuration_id,
            status=approval.status.value,
            maker_actor_id=approval.maker_actor_id,
            checker_actor_id=approval.checker_actor_id,
            policy_version=approval.policy_version,
            decision_reason_code=approval.decision_reason_code,
            requested_at=approval.requested_at,
            decided_at=approval.decided_at,
        )


class ScoringConfigurationEntryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    configuration: ScoringConfigurationItemResponse
    approval: ScoringConfigurationApprovalItemResponse | None


class ScoringConfigurationListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    active_configuration_id: str | None
    pending_approval: ScoringConfigurationApprovalItemResponse | None
    items: tuple[ScoringConfigurationEntryResponse, ...]


class ScoringConfigurationDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_version: str = "v1"
    data_origin: str
    correlation_id: str
    configuration: ScoringConfigurationItemResponse
    approval: ScoringConfigurationApprovalItemResponse


class ScoringConfigurationCreateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    threshold_version: str | None = None
    critical_upper_exclusive: str | None = None
    risky_upper_exclusive: str | None = None
    acceptable_upper_exclusive: str | None = None
    dimension_weights: dict[str, str] | None = None
    criticality_weights: dict[str, str] | None = None
    dataset_id: str | None = None

    def parse_dimension_weights(self) -> dict[QualityDimension, Decimal]:
        return {
            _parse_quality_dimension(key): _parse_decimal(weight)
            for key, weight in (self.dimension_weights or {}).items()
        }

    def parse_criticality_weights(self) -> dict[Criticality, Decimal]:
        return {
            _parse_criticality(key): _parse_decimal(weight)
            for key, weight in (self.criticality_weights or {}).items()
        }


class ScoringConfigurationDecisionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: str
    reason_code: str


def _parse_decimal(value: str) -> Decimal:
    try:
        return Decimal(value)
    except Exception as exc:
        raise ScoringValidationError(
            "Scoring configuration weight or threshold is invalid."
        ) from exc


def _parse_quality_dimension(value: str) -> QualityDimension:
    try:
        return QualityDimension(value.strip().upper())
    except ValueError as exc:
        raise ScoringValidationError("Scoring configuration dimension is invalid.") from exc


def _parse_criticality(value: str) -> Criticality:
    try:
        return Criticality(value.strip().upper())
    except ValueError as exc:
        raise ScoringValidationError("Scoring configuration criticality is invalid.") from exc
