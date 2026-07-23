"""Yalnız yerel geliştirmede kullanılabilen sentetik dashboard API fabrikası."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from veri_kalitesi.api.app import create_dashboard_api
from veri_kalitesi.api.identity import DevelopmentActorContextResolver
from veri_kalitesi.audit import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactionPolicy,
    AuditRedactor,
    AuditService,
    SQLiteAuditRepository,
)
from veri_kalitesi.dashboard import DashboardQueryService
from veri_kalitesi.data_sources import (
    DataSource,
    DataSourceQueryService,
    DataSourceStatus,
    SourceType,
)
from veri_kalitesi.identity import DashboardAuthorizationPolicy, PolicyAuthorizationService
from veri_kalitesi.issues import (
    DataQualityIssue,
    IssuePriority,
    IssueQueryService,
    IssueScopeType,
    IssueSourceEventType,
    IssueStatus,
    IssueTriggerType,
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
)
from veri_kalitesi.scoring import (
    QualityScore,
    ScoreLevel,
    ScoreScopeType,
    ScoreStatus,
    SQLiteScoreRepository,
)

POLICY_VERSION = "DEVELOPMENT_DASHBOARD_POLICY_V1"
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
        assignee_user_id="development-assignee",
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
        assignee_user_id="development-assignee",
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
        assignee_user_id="development-assignee",
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


class DevelopmentIssueReader:
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
                for issue in DEVELOPMENT_ISSUES
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


def create_development_app():  # type: ignore[no-untyped-def]
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
    audit_repository = SQLiteAuditRepository()
    audit_service = AuditService(
        audit_repository,
        AuditRedactor(
            AuditRedactionPolicy(
                version="DEVELOPMENT_API_REDACTION_V1",
                allowed_fields_by_action={
                    "DASHBOARD_SCOPE_AUTHORIZATION": frozenset(
                        {
                            "policy_version",
                            "permitted_source_count",
                            "can_view_enterprise",
                            "reason_code",
                        }
                    )
                },
            )
        ),
        AuditFailurePolicy(
            version="DEVELOPMENT_API_AUDIT_FAILURE_V1",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
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
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=POLICY_VERSION,
        permitted_source_ids=frozenset(source.data_source_id for source in DEVELOPMENT_SOURCES),
        permitted_dataset_ids=frozenset(rule.dataset_id for rule, _ in DEVELOPMENT_RULES),
        can_view_enterprise=True,
    )
    return create_dashboard_api(
        service,
        actor_context_resolver=resolver,
        allowed_origins=("http://127.0.0.1:5173", "http://localhost:5173"),
        data_origin="synthetic-development",
        data_source_query_service=DataSourceQueryService(
            DevelopmentDataSourceReader(), authorization
        ),
        rule_query_service=RuleQueryService(DevelopmentRuleReader(), authorization),
        execution_query_service=ExecutionQueryService(DevelopmentExecutionReader(), authorization),
        issue_query_service=IssueQueryService(DevelopmentIssueReader(), authorization),
    )
