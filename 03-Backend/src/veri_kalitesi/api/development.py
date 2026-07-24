"""Yalnız yerel geliştirmede kullanılabilen sentetik dashboard API fabrikası."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import RLock
from uuid import UUID, uuid4

from veri_kalitesi.api.app import create_dashboard_api
from veri_kalitesi.api.identity import (
    DevelopmentActorContextResolver,
    DevelopmentUserRegistry,
    build_default_development_users,
)
from veri_kalitesi.api.models import IssueAssigneeOptionResponse
from veri_kalitesi.audit import (
    AuditAccessPolicy,
    AuditEventInput,
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactor,
    AuditQueryService,
    AuditResult,
    AuditService,
    SQLiteAuditRepository,
    build_default_redaction_policy,
)
from veri_kalitesi.executions import (
    ExecutionConflictError,
    ExecutionNotFoundError,
    ExecutionStatus,
    ExecutionType,
    RuleExecution,
    WorkloadClass,
)
from veri_kalitesi.dashboard import DashboardQueryService
from veri_kalitesi.data_sources import (
    DataSource,
    DataSourceQueryService,
    DataSourceStatus,
    SourceType,
)
from veri_kalitesi.identity import (
    ActorContext,
    DashboardAuthorizationPolicy,
    PolicyAuthorizationService,
)
from veri_kalitesi.issues import (
    DataQualityIssue,
    IssueAssignment,
    IssueAuthorizationError,
    IssueConflictError,
    IssuePriority,
    IssueQueryService,
    IssueResolutionDraft,
    IssueScopeType,
    IssueSourceEventType,
    IssueStatus,
    IssueTriggerType,
    IssueValidationError,
)
from veri_kalitesi.executions import (
    ExecutionQueryService,
    ExecutionStatus,
    ExecutionType,
    RuleExecution,
    WorkloadClass,
)
from veri_kalitesi.rules import (
    QualityDimension,
    QualityRule,
    RuleCriticality,
    RuleQueryService,
    RuleStatus,
    RuleType,
    RuleVersion,
    RuleValidationError,
)
from veri_kalitesi.reporting import (
    ReportPreviewAccessPolicy,
    ReportPreviewService,
    SQLiteReportPreviewReader,
)
from veri_kalitesi.scoring import (
    QualityScore,
    ScoreLevel,
    ScoreScopeType,
    ScoreStatus,
    SQLiteScoreRepository,
)

POLICY_VERSION = "DEVELOPMENT_DASHBOARD_POLICY_V1"
DEVELOPMENT_ASSIGNEE_OPTIONS = (
    IssueAssigneeOptionResponse(
        user_id=UUID("4ec96cb4-d150-45d2-9565-c1879d135f08"),
        display_name="Veri Sorumlusu A",
    ),
    IssueAssigneeOptionResponse(
        user_id=UUID("d6b099c7-0b6d-4ae5-8f58-6978050c434f"),
        display_name="Veri Sorumlusu B",
    ),
    IssueAssigneeOptionResponse(
        user_id=UUID("257c5792-b9ad-4678-aa8e-f44759d4752e"),
        display_name="Teknik Sorumlu",
    ),
)
DEVELOPMENT_SOURCES = (
    DataSource(
        data_source_id="source-core-banking",
        name="Temel Bankacılık",
        source_type=SourceType.POSTGRESQL,
        connection_config={},
        secret_reference="development-reference-only",
        status=DataSourceStatus.ACTIVE,
    ),
    DataSource(
        data_source_id="source-customer-file",
        name="Müşteri Dosyaları",
        source_type=SourceType.CSV,
        connection_config={},
        secret_reference="development-reference-only",
        status=DataSourceStatus.TEST_SUCCEEDED,
    ),
    DataSource(
        data_source_id="source-risk-mart",
        name="Risk Veri Martı",
        source_type=SourceType.MSSQL,
        connection_config={},
        secret_reference="development-reference-only",
        status=DataSourceStatus.INACTIVE,
    ),
    DataSource(
        data_source_id="source-regulatory-api",
        name="Düzenleyici Veri Servisi",
        source_type=SourceType.REST,
        connection_config={},
        secret_reference="development-reference-only",
        status=DataSourceStatus.TEST_FAILED,
    ),
)
DEVELOPMENT_RULES = (
    (
        QualityRule(
            quality_rule_id="rule-customer-id-required",
            code="DQ_CUSTOMER_ID_REQUIRED",
            name="Müşteri kimliği zorunluluğu",
            dataset_id="dataset-customer",
            field_ids=("field-customer-id",),
            primary_dimension=QualityDimension.COMPLETENESS,
            owner_user_id="development-owner",
            status=RuleStatus.ACTIVE,
        ),
        RuleVersion(
            rule_version_id="rule-version-customer-id-3",
            quality_rule_id="rule-customer-id-required",
            version_no=3,
            rule_type=RuleType.REQUIRED,
            definition={},
            threshold=100,
            weight=1,
            criticality=RuleCriticality.CRITICAL,
            prepared_by_actor_id="development-maker",
            created_at=datetime(2026, 7, 19, 8, 30, tzinfo=timezone.utc),
        ),
    ),
    (
        QualityRule(
            quality_rule_id="rule-account-iban-unique",
            code="DQ_ACCOUNT_IBAN_UNIQUE",
            name="IBAN tekillik kontrolü",
            dataset_id="dataset-account",
            field_ids=("field-account-iban",),
            primary_dimension=QualityDimension.UNIQUENESS,
            owner_user_id="development-owner",
            status=RuleStatus.ACTIVE,
        ),
        RuleVersion(
            rule_version_id="rule-version-account-iban-2",
            quality_rule_id="rule-account-iban-unique",
            version_no=2,
            rule_type=RuleType.UNIQUE,
            definition={},
            threshold=99.5,
            weight=1,
            criticality=RuleCriticality.HIGH,
            prepared_by_actor_id="development-maker",
            created_at=datetime(2026, 7, 18, 10, 15, tzinfo=timezone.utc),
        ),
    ),
    (
        QualityRule(
            quality_rule_id="rule-risk-score-range",
            code="DQ_RISK_SCORE_RANGE",
            name="Risk skoru geçerlilik aralığı",
            dataset_id="dataset-risk",
            field_ids=("field-risk-score",),
            primary_dimension=QualityDimension.VALIDITY,
            owner_user_id="development-owner",
            status=RuleStatus.REVIEW_REQUIRED,
        ),
        RuleVersion(
            rule_version_id="rule-version-risk-score-4",
            quality_rule_id="rule-risk-score-range",
            version_no=4,
            rule_type=RuleType.RANGE,
            definition={},
            threshold=98,
            weight=1,
            criticality=RuleCriticality.CRITICAL,
            prepared_by_actor_id="development-maker",
            created_at=datetime(2026, 7, 21, 13, 45, tzinfo=timezone.utc),
        ),
    ),
    (
        QualityRule(
            quality_rule_id="rule-transaction-freshness",
            code="DQ_TRANSACTION_FRESHNESS",
            name="İşlem verisi güncelliği",
            dataset_id="dataset-transaction",
            field_ids=("field-transaction-created-at",),
            primary_dimension=QualityDimension.TIMELINESS,
            owner_user_id="development-owner",
            status=RuleStatus.DRAFT,
        ),
        RuleVersion(
            rule_version_id="rule-version-transaction-freshness-1",
            quality_rule_id="rule-transaction-freshness",
            version_no=1,
            rule_type=RuleType.FRESHNESS,
            definition={},
            threshold=95,
            weight=1,
            criticality=RuleCriticality.MEDIUM,
            prepared_by_actor_id="development-maker",
            created_at=datetime(2026, 7, 22, 7, 5, tzinfo=timezone.utc),
        ),
    ),
    (
        QualityRule(
            quality_rule_id="rule-branch-code-reference",
            code="DQ_BRANCH_CODE_REFERENCE",
            name="Şube kodu referans bütünlüğü",
            dataset_id="dataset-account",
            field_ids=("field-branch-code",),
            primary_dimension=QualityDimension.INTEGRITY,
            owner_user_id="development-owner",
            status=RuleStatus.PASSIVE,
        ),
        RuleVersion(
            rule_version_id="rule-version-branch-code-2",
            quality_rule_id="rule-branch-code-reference",
            version_no=2,
            rule_type=RuleType.REFERENTIAL_INTEGRITY,
            definition={},
            threshold=99,
            weight=1,
            criticality=RuleCriticality.LOW,
            prepared_by_actor_id="development-maker",
            created_at=datetime(2026, 7, 17, 9, 0, tzinfo=timezone.utc),
        ),
    ),
)
DEVELOPMENT_EXECUTIONS = (
    RuleExecution(
        execution_id="execution-running",
        idempotency_key_hash="synthetic-running",
        payload_hash="synthetic-running-payload",
        rule_version_ids=("rule-version-customer-id-3", "rule-version-account-iban-2"),
        scope={},
        triggered_by="development-user",
        correlation_id="development-running",
        source_ids=("source-core-banking",),
        workload_class=WorkloadClass.HEAVY,
        execution_type=ExecutionType.MANUAL,
        status=ExecutionStatus.RUNNING,
        attempt_count=1,
        created_at=datetime(2026, 7, 23, 8, 40, tzinfo=timezone.utc),
        started_at=datetime(2026, 7, 23, 8, 41, tzinfo=timezone.utc),
    ),
    RuleExecution(
        execution_id="execution-queued",
        idempotency_key_hash="synthetic-queued",
        payload_hash="synthetic-queued-payload",
        rule_version_ids=("rule-version-risk-score-4",),
        scope={},
        triggered_by="development-user",
        correlation_id="development-queued",
        source_ids=("source-risk-mart",),
        execution_type=ExecutionType.SCHEDULED,
        status=ExecutionStatus.QUEUED,
        created_at=datetime(2026, 7, 23, 8, 35, tzinfo=timezone.utc),
    ),
    RuleExecution(
        execution_id="execution-success",
        idempotency_key_hash="synthetic-success",
        payload_hash="synthetic-success-payload",
        rule_version_ids=("rule-version-customer-id-3",),
        scope={},
        triggered_by="development-user",
        correlation_id="development-success",
        source_ids=("source-core-banking",),
        execution_type=ExecutionType.SCHEDULED,
        status=ExecutionStatus.SUCCESS,
        attempt_count=1,
        created_at=datetime(2026, 7, 23, 7, 15, tzinfo=timezone.utc),
        started_at=datetime(2026, 7, 23, 7, 16, tzinfo=timezone.utc),
        finished_at=datetime(2026, 7, 23, 7, 24, tzinfo=timezone.utc),
    ),
    RuleExecution(
        execution_id="execution-partial",
        idempotency_key_hash="synthetic-partial",
        payload_hash="synthetic-partial-payload",
        rule_version_ids=("rule-version-transaction-freshness-1",),
        scope={},
        triggered_by="development-user",
        correlation_id="development-partial",
        source_ids=("source-customer-file",),
        workload_class=WorkloadClass.HEAVY,
        status=ExecutionStatus.PARTIAL,
        error_class="QUERY_TIMEOUT",
        attempt_count=1,
        created_at=datetime(2026, 7, 22, 18, 0, tzinfo=timezone.utc),
        started_at=datetime(2026, 7, 22, 18, 1, tzinfo=timezone.utc),
        finished_at=datetime(2026, 7, 22, 18, 31, tzinfo=timezone.utc),
    ),
    RuleExecution(
        execution_id="execution-technical-error",
        idempotency_key_hash="synthetic-technical-error",
        payload_hash="synthetic-technical-error-payload",
        rule_version_ids=("rule-version-risk-score-4",),
        scope={},
        triggered_by="development-user",
        correlation_id="development-technical-error",
        source_ids=("source-risk-mart",),
        status=ExecutionStatus.TECHNICAL_ERROR,
        error_class="CONNECTION_UNAVAILABLE",
        attempt_count=3,
        created_at=datetime(2026, 7, 22, 14, 20, tzinfo=timezone.utc),
        started_at=datetime(2026, 7, 22, 14, 21, tzinfo=timezone.utc),
        finished_at=datetime(2026, 7, 22, 14, 24, tzinfo=timezone.utc),
    ),
    RuleExecution(
        execution_id="execution-timeout",
        idempotency_key_hash="synthetic-timeout",
        payload_hash="synthetic-timeout-payload",
        rule_version_ids=("rule-version-branch-code-2",),
        scope={},
        triggered_by="development-user",
        correlation_id="development-timeout",
        source_ids=("source-core-banking",),
        status=ExecutionStatus.TIMEOUT,
        error_class="TOTAL_TIMEOUT",
        attempt_count=1,
        created_at=datetime(2026, 7, 21, 11, 0, tzinfo=timezone.utc),
        started_at=datetime(2026, 7, 21, 11, 1, tzinfo=timezone.utc),
        finished_at=datetime(2026, 7, 21, 12, 1, tzinfo=timezone.utc),
    ),
    RuleExecution(
        execution_id="execution-cancel-requested",
        idempotency_key_hash="synthetic-cancel-requested",
        payload_hash="synthetic-cancel-requested-payload",
        rule_version_ids=("rule-version-account-iban-2",),
        scope={},
        triggered_by="development-user",
        correlation_id="development-cancel-requested",
        source_ids=("source-core-banking",),
        status=ExecutionStatus.CANCEL_REQUESTED,
        attempt_count=1,
        created_at=datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc),
        started_at=datetime(2026, 7, 20, 9, 1, tzinfo=timezone.utc),
        cancel_requested_at=datetime(2026, 7, 20, 9, 4, tzinfo=timezone.utc),
        cancel_requested_by="development-user",
        cancel_reason="development-reason",
    ),
    RuleExecution(
        execution_id="execution-cancelled",
        idempotency_key_hash="synthetic-cancelled",
        payload_hash="synthetic-cancelled-payload",
        rule_version_ids=("rule-version-customer-id-3",),
        scope={},
        triggered_by="development-user",
        correlation_id="development-cancelled",
        source_ids=("source-customer-file",),
        status=ExecutionStatus.CANCELLED,
        created_at=datetime(2026, 7, 19, 16, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 7, 19, 16, 2, tzinfo=timezone.utc),
        cancelled_at=datetime(2026, 7, 19, 16, 2, tzinfo=timezone.utc),
    ),
)
DEVELOPMENT_ISSUES = (
    DataQualityIssue(
        issue_id="issue-critical-customer",
        issue_no="DQI-2026-0018",
        source_event_id="development-event-18",
        source_event_type=IssueSourceEventType.QUALITY,
        trigger_type=IssueTriggerType.CRITICAL_RULE_FAILURE,
        scope_type=IssueScopeType.DATASET,
        scope_id="dataset-customer",
        status=IssueStatus.NEW,
        priority=IssuePriority.CRITICAL,
        assignee_user_id="development-dashboard-user",
        deduplication_key_digest="development-digest-18",
        occurrence_count=1,
        created_at=datetime(2026, 7, 23, 8, 10, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 23, 8, 10, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 7, 23, 8, 10, tzinfo=timezone.utc),
    ),
    DataQualityIssue(
        issue_id="issue-technical-risk",
        issue_no="DQI-2026-0017",
        source_event_id="development-event-17",
        source_event_type=IssueSourceEventType.TECHNICAL,
        trigger_type=IssueTriggerType.TECHNICAL_ERROR,
        scope_type=IssueScopeType.SOURCE,
        scope_id="source-risk-mart",
        status=IssueStatus.ASSIGNED,
        priority=IssuePriority.HIGH,
        assignee_user_id="development-dashboard-user",
        deduplication_key_digest="development-digest-17",
        occurrence_count=3,
        created_at=datetime(2026, 7, 22, 15, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 23, 7, 40, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 7, 23, 7, 40, tzinfo=timezone.utc),
    ),
    DataQualityIssue(
        issue_id="issue-account-investigation",
        issue_no="DQI-2026-0016",
        source_event_id="development-event-16",
        source_event_type=IssueSourceEventType.QUALITY,
        trigger_type=IssueTriggerType.QUALITY_THRESHOLD,
        scope_type=IssueScopeType.DATASET,
        scope_id="dataset-account",
        status=IssueStatus.INVESTIGATING,
        priority=IssuePriority.HIGH,
        assignee_user_id="development-dashboard-user",
        deduplication_key_digest="development-digest-16",
        occurrence_count=2,
        created_at=datetime(2026, 7, 21, 10, 30, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 22, 16, 20, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 7, 22, 16, 20, tzinfo=timezone.utc),
    ),
    DataQualityIssue(
        issue_id="issue-transaction-waiting",
        issue_no="DQI-2026-0015",
        source_event_id="development-event-15",
        source_event_type=IssueSourceEventType.QUALITY,
        trigger_type=IssueTriggerType.QUALITY_THRESHOLD,
        scope_type=IssueScopeType.DATASET,
        scope_id="dataset-transaction",
        status=IssueStatus.WAITING_FOR_RESOLUTION,
        priority=IssuePriority.MEDIUM,
        assignee_user_id="development-assignee",
        deduplication_key_digest="development-digest-15",
        occurrence_count=4,
        created_at=datetime(2026, 7, 19, 9, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 22, 11, 45, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 7, 22, 11, 45, tzinfo=timezone.utc),
    ),
    DataQualityIssue(
        issue_id="issue-risk-resolved",
        issue_no="DQI-2026-0014",
        source_event_id="development-event-14",
        source_event_type=IssueSourceEventType.QUALITY,
        trigger_type=IssueTriggerType.CRITICAL_RULE_FAILURE,
        scope_type=IssueScopeType.DATASET,
        scope_id="dataset-risk",
        status=IssueStatus.RESOLVED,
        priority=IssuePriority.CRITICAL,
        assignee_user_id="development-assignee",
        deduplication_key_digest="development-digest-14",
        occurrence_count=1,
        created_at=datetime(2026, 7, 18, 13, 15, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 21, 14, 10, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 7, 18, 13, 15, tzinfo=timezone.utc),
    ),
    DataQualityIssue(
        issue_id="issue-customer-verified",
        issue_no="DQI-2026-0013",
        source_event_id="development-event-13",
        source_event_type=IssueSourceEventType.QUALITY,
        trigger_type=IssueTriggerType.QUALITY_THRESHOLD,
        scope_type=IssueScopeType.DATASET,
        scope_id="dataset-customer",
        status=IssueStatus.VERIFIED,
        priority=IssuePriority.MEDIUM,
        assignee_user_id="development-assignee",
        deduplication_key_digest="development-digest-13",
        occurrence_count=1,
        created_at=datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 20, 15, 30, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc),
    ),
    DataQualityIssue(
        issue_id="issue-account-closed",
        issue_no="DQI-2026-0012",
        source_event_id="development-event-12",
        source_event_type=IssueSourceEventType.QUALITY,
        trigger_type=IssueTriggerType.QUALITY_THRESHOLD,
        scope_type=IssueScopeType.DATASET,
        scope_id="dataset-account",
        status=IssueStatus.CLOSED,
        priority=IssuePriority.LOW,
        assignee_user_id="development-assignee",
        deduplication_key_digest="development-digest-12",
        occurrence_count=1,
        created_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 19, 10, 0, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
    ),
    DataQualityIssue(
        issue_id="issue-source-cancelled",
        issue_no="DQI-2026-0011",
        source_event_id="development-event-11",
        source_event_type=IssueSourceEventType.TECHNICAL,
        trigger_type=IssueTriggerType.TECHNICAL_ERROR,
        scope_type=IssueScopeType.SOURCE,
        scope_id="source-customer-file",
        status=IssueStatus.CANCELLED,
        priority=IssuePriority.LOW,
        assignee_user_id="development-assignee",
        deduplication_key_digest="development-digest-11",
        occurrence_count=1,
        created_at=datetime(2026, 7, 14, 9, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 7, 14, 9, 0, tzinfo=timezone.utc),
    ),
)


class DevelopmentDataSourceReader:
    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]:
        return [
            source for source in DEVELOPMENT_SOURCES if source.data_source_id in allowed_source_ids
        ]


class DevelopmentRuleReader:
    def list_rules_with_latest_version(
        self, allowed_dataset_ids: frozenset[str]
    ) -> list[tuple[QualityRule, RuleVersion]]:
        return sorted(
            (item for item in DEVELOPMENT_RULES if item[0].dataset_id in allowed_dataset_ids),
            key=lambda item: (item[0].code.casefold(), item[0].quality_rule_id),
        )


class DevelopmentExecutionReader:
    def list_executions_for_sources(
        self,
        allowed_source_ids: frozenset[str],
        *,
        limit: int = 100,
    ) -> list[RuleExecution]:
        return sorted(
            (
                execution
                for execution in DEVELOPMENT_EXECUTIONS
                if execution.source_ids and set(execution.source_ids).issubset(allowed_source_ids)
            ),
            key=lambda execution: (execution.created_at, execution.execution_id),
            reverse=True,
        )[:limit]


class DevelopmentIssueStore:
    def __init__(self) -> None:
        self._issues = {issue.issue_id: issue for issue in DEVELOPMENT_ISSUES}
        self._lock = RLock()

    def list_issues_for_scopes(
        self,
        allowed_source_ids: frozenset[str],
        allowed_dataset_ids: frozenset[str],
        *,
        limit: int = 100,
    ) -> list[DataQualityIssue]:
        return sorted(
            (
                issue
                for issue in self._issues.values()
                if (
                    issue.scope_type is IssueScopeType.SOURCE
                    and issue.scope_id in allowed_source_ids
                )
                or (
                    issue.scope_type is IssueScopeType.DATASET
                    and issue.scope_id in allowed_dataset_ids
                )
            ),
            key=lambda issue: (issue.updated_at, issue.issue_id),
            reverse=True,
        )[:limit]

    def start_investigation(
        self,
        issue_id: str,
        expected_version: int,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        if actor_context is None:
            raise IssueAuthorizationError("Development actor is required.")
        with self._lock:
            issue = self._issues.get(issue_id)
            if issue is None:
                raise IssueValidationError("Development issue was not found.")
            has_scope = (
                issue.scope_id in actor_context.permitted_source_ids
                if issue.scope_type is IssueScopeType.SOURCE
                else issue.scope_id in actor_context.permitted_dataset_ids
            )
            if issue.assignee_user_id != actor_context.actor_id or not has_scope:
                raise IssueAuthorizationError("Development actor cannot investigate issue.")
            if issue.version != expected_version:
                raise IssueConflictError("Development issue version changed.")
            if issue.status is not IssueStatus.ASSIGNED:
                raise IssueValidationError("Development issue is not assigned.")
            updated = replace(
                issue,
                status=IssueStatus.INVESTIGATING,
                updated_at=datetime.now(timezone.utc),
                version=issue.version + 1,
            )
            self._issues[issue_id] = updated
            return updated

    def list_assignment_options(
        self,
        issue_id: str,
        actor_context: ActorContext | None,
    ) -> tuple[IssueAssigneeOptionResponse, ...]:
        if actor_context is None:
            raise IssueAuthorizationError("Development actor is required.")
        with self._lock:
            issue = self._issues.get(issue_id)
            if issue is None:
                raise IssueValidationError("Development issue was not found.")
            self._authorize_assignment(issue, actor_context)
            return DEVELOPMENT_ASSIGNEE_OPTIONS

    def reassign(
        self,
        issue_id: str,
        assignment: IssueAssignment,
        expected_version: int,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        if actor_context is None:
            raise IssueAuthorizationError("Development actor is required.")
        with self._lock:
            issue = self._issues.get(issue_id)
            if issue is None:
                raise IssueValidationError("Development issue was not found.")
            self._authorize_assignment(issue, actor_context)
            if issue.version != expected_version:
                raise IssueConflictError("Development issue version changed.")
            allowed_ids = {str(option.user_id) for option in DEVELOPMENT_ASSIGNEE_OPTIONS}
            if assignment.assignee_user_id not in allowed_ids:
                raise IssueAuthorizationError("Development assignee is not available.")
            if (
                issue.assignee_user_id == assignment.assignee_user_id
                and issue.priority is assignment.priority
            ):
                raise IssueValidationError("Development assignment must change.")
            updated = replace(
                issue,
                assignee_user_id=assignment.assignee_user_id,
                priority=assignment.priority,
                status=IssueStatus.ASSIGNED,
                updated_at=datetime.now(timezone.utc),
                version=issue.version + 1,
            )
            self._issues[issue_id] = updated
            return updated

    def resolve(
        self,
        issue_id: str,
        draft: IssueResolutionDraft,
        expected_version: int,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        if actor_context is None:
            raise IssueAuthorizationError("Development actor is required.")
        with self._lock:
            issue = self._issues.get(issue_id)
            if issue is None:
                raise IssueValidationError("Development issue was not found.")
            if issue.version != expected_version:
                raise IssueConflictError("Development issue version changed.")
            has_scope = (
                issue.scope_id in actor_context.permitted_source_ids
                if issue.scope_type is IssueScopeType.SOURCE
                else issue.scope_id in actor_context.permitted_dataset_ids
            )
            if issue.assignee_user_id != actor_context.actor_id or not has_scope:
                raise IssueAuthorizationError("Development actor cannot resolve issue.")
            if issue.status not in {IssueStatus.INVESTIGATING, IssueStatus.WAITING_FOR_RESOLUTION}:
                raise IssueValidationError("Development issue is not in a resolvable state.")
            if draft.completed_at > datetime.now(timezone.utc):
                raise IssueValidationError("Development resolution completed_at is in the future.")
            updated = replace(
                issue,
                status=IssueStatus.RESOLVED,
                updated_at=datetime.now(timezone.utc),
                version=issue.version + 1,
            )
            self._issues[issue_id] = updated
            return updated

    def record_verification_result(
        self,
        issue_id: str,
        verification_reference_id: str,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        if actor_context is None:
            raise IssueAuthorizationError("Development actor is required.")
        with self._lock:
            issue = self._issues.get(issue_id)
            if issue is None:
                raise IssueValidationError("Development issue was not found.")
            has_scope = (
                issue.scope_id in actor_context.permitted_source_ids
                if issue.scope_type is IssueScopeType.SOURCE
                else issue.scope_id in actor_context.permitted_dataset_ids
            )
            if issue.assignee_user_id == actor_context.actor_id or not has_scope:
                raise IssueAuthorizationError("Development actor cannot verify this issue.")
            if not actor_context.roles.intersection({"DATA_STEWARD", "DATA_GOVERNANCE_SPECIALIST"}):
                raise IssueAuthorizationError("Development actor cannot verify issues.")
            if issue.status is not IssueStatus.RESOLVED:
                raise IssueValidationError("Development issue is not resolved.")
            updated = replace(
                issue,
                status=IssueStatus.VERIFIED,
                updated_at=datetime.now(timezone.utc),
                version=issue.version + 1,
            )
            self._issues[issue_id] = updated
            return updated

    def close(
        self,
        issue_id: str,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        if actor_context is None:
            raise IssueAuthorizationError("Development actor is required.")
        with self._lock:
            issue = self._issues.get(issue_id)
            if issue is None:
                raise IssueValidationError("Development issue was not found.")
            has_scope = (
                issue.scope_id in actor_context.permitted_source_ids
                if issue.scope_type is IssueScopeType.SOURCE
                else issue.scope_id in actor_context.permitted_dataset_ids
            )
            if not has_scope:
                raise IssueAuthorizationError("Development actor cannot close this issue.")
            if not actor_context.roles.intersection({"DATA_OWNER", "DATA_STEWARD"}):
                raise IssueAuthorizationError("Development actor cannot close issues.")
            if issue.status is not IssueStatus.VERIFIED:
                raise IssueValidationError("Development issue is not verified.")
            updated = replace(
                issue,
                status=IssueStatus.CLOSED,
                updated_at=datetime.now(timezone.utc),
                version=issue.version + 1,
            )
            self._issues[issue_id] = updated
            return updated

    def _authorize_assignment(
        self,
        issue: DataQualityIssue,
        actor_context: ActorContext,
    ) -> None:
        has_scope = (
            issue.scope_id in actor_context.permitted_source_ids
            if issue.scope_type is IssueScopeType.SOURCE
            else issue.scope_id in actor_context.permitted_dataset_ids
        )
        if (
            actor_context.privileged
            or not actor_context.roles.intersection({"DATA_STEWARD", "DATA_GOVERNANCE_SPECIALIST"})
            or not has_scope
            or issue.status not in {IssueStatus.ASSIGNED, IssueStatus.INVESTIGATING}
        ):
            raise IssueAuthorizationError("Development actor cannot assign issue.")


class DevelopmentRuleStore:
    def __init__(self) -> None:
        self._rules: dict[str, tuple[QualityRule, RuleVersion]] = {
            rule.quality_rule_id: (rule, version) for rule, version in DEVELOPMENT_RULES
        }
        self._lock = RLock()

    def create_rule(
        self,
        *,
        actor_id: str,
        code: str,
        name: str,
        dataset_id: str,
        rule_type: str,
        primary_dimension: str,
        threshold: float,
        weight: float,
        criticality: str,
        owner_user_id: str,
        parameters: dict,
        actor_context: ActorContext | None = None,
    ) -> tuple[QualityRule, RuleVersion]:
        if actor_context is None:
            raise RuleValidationError("Development actor is required.")
        with self._lock:
            quality_rule_id = f"rule-{uuid4().hex[:12]}"
            rule_version_id = f"rule-version-{uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)
            rule = QualityRule(
                quality_rule_id=quality_rule_id,
                code=code,
                name=name,
                dataset_id=dataset_id,
                field_ids=(),
                primary_dimension=QualityDimension(primary_dimension),
                owner_user_id=owner_user_id,
                status=RuleStatus.DRAFT,
            )
            version = RuleVersion(
                rule_version_id=rule_version_id,
                quality_rule_id=quality_rule_id,
                version_no=1,
                rule_type=RuleType(rule_type),
                definition=parameters,
                threshold=threshold,
                weight=weight,
                criticality=RuleCriticality(criticality),
                prepared_by_actor_id=actor_id,
                created_at=now,
            )
            self._rules[quality_rule_id] = (rule, version)
            return rule, version


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
                raise ValueError(f"Development data source {data_source_id} not found.")
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
                raise ValueError(f"Development data source {data_source_id} not found.")
            if source.status is not DataSourceStatus.TEST_SUCCEEDED:
                raise ValueError(f"Cannot activate source in status {source.status.value}.")
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
                raise ValueError(f"Development data source {data_source_id} not found.")
            if source.status is not DataSourceStatus.ACTIVE:
                raise ValueError(f"Cannot passivate source in status {source.status.value}.")
            updated = replace(
                source,
                status=DataSourceStatus.INACTIVE,
                revision=source.revision + 1,
            )
            self._sources[data_source_id] = updated
            return updated


class DevelopmentExecutionStore:
    """Geliştirme ortamında çalıştırma işlemleri için bellek içi depo."""

    def __init__(self) -> None:
        self._executions = {execution.execution_id: execution for execution in DEVELOPMENT_EXECUTIONS}
        self._lock = RLock()

    def start_manual(
        self,
        *,
        rule_version_ids: tuple[str, ...],
        source_ids: tuple[str, ...],
        triggered_by: str,
    ) -> RuleExecution:
        with self._lock:
            execution_id = f"execution-{uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)
            execution = RuleExecution(
                execution_id=execution_id,
                idempotency_key_hash=f"dev-manual-{execution_id}",
                payload_hash=f"dev-manual-payload-{execution_id}",
                rule_version_ids=rule_version_ids,
                scope={},
                triggered_by=triggered_by,
                correlation_id=execution_id,
                source_ids=source_ids,
                workload_class=WorkloadClass.LIGHT,
                execution_type=ExecutionType.MANUAL,
                status=ExecutionStatus.QUEUED,
                created_at=now,
            )
            self._executions[execution_id] = execution
            return execution

    def cancel(self, execution_id: str, *, reason: str, requested_by: str) -> RuleExecution:
        with self._lock:
            execution = self._executions.get(execution_id)
            if execution is None:
                raise ExecutionNotFoundError(f"Execution {execution_id} not found.")
            if execution.status in {ExecutionStatus.SUCCESS, ExecutionStatus.FAILED,
                                     ExecutionStatus.TECHNICAL_ERROR, ExecutionStatus.CANCELLED,
                                     ExecutionStatus.TIMEOUT}:
                raise ExecutionConflictError(
                    f"Cannot cancel execution in {execution.status.value} status."
                )
            now = datetime.now(timezone.utc)
            if execution.status is ExecutionStatus.QUEUED:
                updated = replace(
                    execution,
                    status=ExecutionStatus.CANCELLED,
                    cancelled_at=now,
                    cancel_reason=reason,
                    finished_at=now,
                    cancel_requested_by=requested_by,
                )
            else:
                updated = replace(
                    execution,
                    status=ExecutionStatus.CANCEL_REQUESTED,
                    cancel_requested_at=now,
                    cancel_reason=reason,
                    cancel_requested_by=requested_by,
                )
            self._executions[execution_id] = updated
            return updated


DEVELOPMENT_USER_REGISTRY = DevelopmentUserRegistry(build_default_development_users())


def create_development_app(  # type: ignore[no-untyped-def]
    user_registry: DevelopmentUserRegistry | None = None,
):
    """Sentetik skorlarla yerel gösterim uygulaması üretir; üretimde kullanılmaz."""

    now = datetime.now(timezone.utc)
    repository = SQLiteScoreRepository()
    for index, (days_ago, score_value) in enumerate(
        (
            (28, "72.10"),
            (24, "76.80"),
            (20, "78.20"),
            (12, "82.40"),
            (8, "84.60"),
            (4, "86.20"),
            (0, "87.40"),
        )
    ):
        repository.add_or_get(
            QualityScore(
                execution_id=f"development-dashboard-{index}",
                rule_version_id=None,
                scope_type=ScoreScopeType.ENTERPRISE,
                scope_id=None,
                score_value=Decimal(score_value),
                score_status=ScoreStatus.CALCULATED,
                level=ScoreLevel.ACCEPTABLE,
                calculation_details={"included_in_official_aggregation": True},
                calculated_at=now - timedelta(days=days_ago),
            )
        )
    source_observations = (
        (
            "source-core-banking",
            "91.80",
            ScoreStatus.CALCULATED,
            ScoreLevel.GOOD,
            True,
        ),
        (
            "source-customer-file",
            "82.40",
            ScoreStatus.PARTIAL,
            ScoreLevel.ACCEPTABLE,
            True,
        ),
        ("source-risk-mart", None, ScoreStatus.NO_DATA, None, None),
        (
            "source-regulatory-api",
            None,
            ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR,
            None,
            None,
        ),
    )
    for index, (source_id, score_value, status, level, official) in enumerate(source_observations):
        calculation_details: dict[str, object] = {"aggregate": True}
        if official is not None:
            calculation_details["included_in_official_aggregation"] = official
        repository.add_or_get(
            QualityScore(
                execution_id=f"development-report-{index}",
                rule_version_id=None,
                scope_type=ScoreScopeType.SOURCE,
                scope_id=source_id,
                score_value=Decimal(score_value) if score_value is not None else None,
                score_status=status,
                level=level,
                calculation_details=calculation_details,
                calculated_at=now - timedelta(hours=index + 1),
            )
        )
    audit_repository = SQLiteAuditRepository()
    audit_service = AuditService(
        audit_repository,
        AuditRedactor(build_default_redaction_policy()),
        AuditFailurePolicy(
            version="DEVELOPMENT_API_AUDIT_FAILURE_V1",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )
    for index, (actor_id, action, object_type, object_id, result, reason_code) in enumerate(
        (
            (
                "synthetic-iam-user",
                "LDAP_AUTHENTICATION",
                "UserSession",
                "synthetic-session",
                AuditResult.SUCCESS,
                "AUTHENTICATED",
            ),
            (
                "synthetic-data-steward",
                "DATA_SOURCE_CONNECTION_TEST",
                "DataSource",
                "source-core-banking",
                AuditResult.SUCCESS,
                "TEST_SUCCEEDED",
            ),
            (
                "synthetic-rule-checker",
                "RULE_ACTIVATION",
                "QualityRule",
                "rule-customer-id-required",
                AuditResult.SUCCESS,
                "APPROVED",
            ),
            (
                "synthetic-score-checker",
                "SCORING_CONFIGURATION_ACTIVATION",
                "ScoringConfiguration",
                "scoring-policy-v2",
                AuditResult.DENIED,
                "MAKER_CHECKER_REQUIRED",
            ),
            (
                "synthetic-report-viewer",
                "REPORT_PREVIEW_VIEWED",
                "ReportPreview",
                None,
                AuditResult.SUCCESS,
                "QUERY_COMPLETED",
            ),
            (
                "synthetic-session-user",
                "IDENTITY_SESSION",
                "UserSession",
                "synthetic-expired-session",
                AuditResult.FAILURE,
                "ABSOLUTE_TIMEOUT",
            ),
        )
    ):
        audit_service.append(
            AuditEventInput(
                actor_id=actor_id,
                actor_type="USER",
                correlation_id=f"synthetic-audit-{index + 1}",
                action=action,
                object_type=object_type,
                object_id=object_id,
                result=result,
                reason_code=reason_code,
                old_values={},
                new_values={},
                occurred_at=now - timedelta(days=index, hours=1),
                session_id=None,
            )
        )
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: datetime.now(timezone.utc),
    )
    service = DashboardQueryService(
        repository,
        authorization,
        clock=lambda: datetime.now(timezone.utc),
    )
    development_origins = frozenset({"http://127.0.0.1:5173", "http://localhost:5173"})
    effective_registry = user_registry or DEVELOPMENT_USER_REGISTRY
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=POLICY_VERSION,
        permitted_source_ids=frozenset(source.data_source_id for source in DEVELOPMENT_SOURCES),
        permitted_dataset_ids=frozenset(rule.dataset_id for rule, _ in DEVELOPMENT_RULES),
        roles=frozenset({"DATA_VIEWER", "DATA_STEWARD", "AUDIT_VIEWER"}),
        allowed_origins=development_origins,
        can_view_enterprise=True,
        user_registry=effective_registry,
    )
    issue_store = DevelopmentIssueStore()
    rule_store = DevelopmentRuleStore()
    data_source_store = DevelopmentDataSourceStore()
    execution_store = DevelopmentExecutionStore()
    return create_dashboard_api(
        service,
        rule_creator_service=rule_store,
        actor_context_resolver=resolver,
        allowed_origins=tuple(development_origins),
        data_origin="synthetic-development",
        data_source_query_service=DataSourceQueryService(
            DevelopmentDataSourceReader(), authorization
        ),
        rule_query_service=RuleQueryService(DevelopmentRuleReader(), authorization),
        execution_query_service=ExecutionQueryService(DevelopmentExecutionReader(), authorization),
        issue_query_service=IssueQueryService(issue_store, authorization),
        issue_investigation_service=issue_store,
        issue_assignment_service=issue_store,
        issue_assignee_option_provider=issue_store,
        issue_resolution_service=issue_store,
        issue_verification_service=issue_store,
        issue_closure_service=issue_store,
        data_source_mutation_service=data_source_store,
        execution_start_service=execution_store,
        execution_cancel_service=execution_store,
        development_user_registry=effective_registry,
        report_preview_service=ReportPreviewService(
            SQLiteReportPreviewReader(repository.connection),
            audit_service,
            ReportPreviewAccessPolicy(
                version="DEVELOPMENT_REPORT_POLICY_V1",
                actor_policy_version=POLICY_VERSION,
            ),
            clock=lambda: datetime.now(timezone.utc),
        ),
        audit_query_service=AuditQueryService(
            audit_repository,
            audit_service,
            AuditAccessPolicy(
                version="DEVELOPMENT_AUDIT_ACCESS_V1",
                context_policy_version=POLICY_VERSION,
            ),
            clock=lambda: datetime.now(timezone.utc),
        ),
        clock=lambda: datetime.now(timezone.utc),
    )
