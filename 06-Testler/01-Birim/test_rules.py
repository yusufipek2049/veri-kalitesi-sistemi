from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import pytest

from veri_kalitesi.audit import (
    AuditEvent,
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactor,
    AuditService,
    PreparedAuditEvent,
    SQLiteAuditRepository,
    SQLiteTransactionalAudit,
    build_default_redaction_policy,
)
from veri_kalitesi.data_sources import DataField, DataSource, DataSourceStatus, Dataset, SourceType
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.rules import (
    BusinessCalendar,
    RuleApprovalPolicy,
    RuleApprovalStatus,
    RuleAuthorizationError,
    RuleService,
    RuleStatus,
    RuleTestComputation,
    RuleTestOptions,
    RuleTestStatus,
    RuleTestTechnicalError,
    RuleType,
    RuleValidationError,
    SQLiteRuleRepository,
    build_rule_plan,
)


DATASET_ID = "dataset-main"
REFERENCE_DATASET_ID = "dataset-reference"
FIELD_ID = "field-main"
SECOND_FIELD_ID = "field-second"
REFERENCE_FIELD_ID = "field-reference"
NOW = datetime(2026, 7, 16, 15, 0, tzinfo=timezone.utc)
ACTOR_POLICY_VERSION = "BANK_ACTOR_POLICY_V1"


@dataclass
class FakeMetadataCatalog:
    source_status: DataSourceStatus = DataSourceStatus.TEST_SUCCEEDED
    datasets: dict[str, Dataset] = field(
        default_factory=lambda: {
            DATASET_ID: Dataset(
                dataset_id=DATASET_ID,
                data_source_id="source-main",
                namespace="public",
                name="customers",
            ),
            REFERENCE_DATASET_ID: Dataset(
                dataset_id=REFERENCE_DATASET_ID,
                data_source_id="source-main",
                namespace="public",
                name="countries",
            ),
        }
    )
    fields: dict[str, list[DataField]] = field(
        default_factory=lambda: {
            DATASET_ID: [
                DataField(
                    data_field_id=FIELD_ID,
                    dataset_id=DATASET_ID,
                    name="email",
                    native_data_type="TEXT",
                ),
                DataField(
                    data_field_id=SECOND_FIELD_ID,
                    dataset_id=DATASET_ID,
                    name="created_at",
                    native_data_type="TIMESTAMP",
                ),
            ],
            REFERENCE_DATASET_ID: [
                DataField(
                    data_field_id=REFERENCE_FIELD_ID,
                    dataset_id=REFERENCE_DATASET_ID,
                    name="country_code",
                    native_data_type="TEXT",
                )
            ],
        }
    )

    def get_dataset(self, dataset_id: str) -> Dataset:
        return self.datasets[dataset_id]

    def list_data_fields(self, dataset_id: str) -> list[DataField]:
        return self.fields.get(dataset_id, [])

    def get_data_source(self, data_source_id: str) -> DataSource:
        return DataSource(
            data_source_id=data_source_id,
            name="Test source",
            source_type=SourceType.CSV,
            connection_config={"file_path": "/not-read-by-rule-unit-test.csv"},
            secret_reference="secret://test/rules",
            status=self.source_status,
        )


class FakeRuleExecutor:
    def __init__(self, outcome: RuleTestComputation | Exception) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, Any]] = []

    def execute(self, **kwargs: Any) -> RuleTestComputation:
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@dataclass(frozen=True)
class FakeBusinessCalendar:
    version: str = "BANK_BUSINESS_CALENDAR_V1"
    holidays: frozenset[date] = frozenset()

    def add_business_days(self, start_at: datetime, business_days: int) -> datetime:
        current = start_at
        remaining = business_days
        while remaining:
            current += timedelta(days=1)
            if current.weekday() < 5 and current.date() not in self.holidays:
                remaining -= 1
        return current


@dataclass
class MutableClock:
    now: datetime

    def __call__(self) -> datetime:
        return self.now


def _rule_service(
    repository: SQLiteRuleRepository,
    catalog: FakeMetadataCatalog,
    executor: FakeRuleExecutor,
    *,
    approval_policy: RuleApprovalPolicy | None = None,
    approval_calendar: BusinessCalendar | None = None,
    clock: Callable[[], datetime] = lambda: NOW,
) -> RuleService:
    audit_repository = SQLiteAuditRepository()
    redactor = AuditRedactor(build_default_redaction_policy())
    return RuleService(
        repository,
        catalog,
        executor,
        audit_sink=AuditService(
            audit_repository,
            redactor,
            AuditFailurePolicy("AUDIT_FAILURE_TEST_V1", AuditFailureMode.FAIL_CLOSED),
        ),
        transactional_audit=SQLiteTransactionalAudit(
            repository.connection,
            redactor,
            audit_repository,
            policy_version="AUDIT_OUTBOX_TEST_V1",
        ),
        approval_policy=approval_policy,
        approval_calendar=approval_calendar,
        clock=clock,
    )


def _audit_events(service: RuleService) -> list[AuditEvent]:
    audit_service = service.audit_sink
    assert isinstance(audit_service, AuditService)
    repository = audit_service.repository
    assert isinstance(repository, SQLiteAuditRepository)
    return repository.list_events()


@pytest.mark.parametrize(
    ("rule_type", "parameters", "expected_operator"),
    [
        (RuleType.REQUIRED, {"field_id": FIELD_ID}, "IS_NOT_NULL"),
        (RuleType.UNIQUE, {"field_ids": [FIELD_ID, SECOND_FIELD_ID]}, "UNIQUE"),
        (
            RuleType.RANGE,
            {"field_id": FIELD_ID, "minimum": 1, "maximum": 10},
            "BETWEEN",
        ),
        (RuleType.REGEX, {"field_id": FIELD_ID, "pattern": r"^[^@]+@[^@]+$"}, "REGEX_MATCH"),
        (
            RuleType.FRESHNESS,
            {"field_id": SECOND_FIELD_ID, "max_age_minutes": 60, "timezone": "Europe/Istanbul"},
            "MAX_AGE",
        ),
        (
            RuleType.REFERENTIAL_INTEGRITY,
            {
                "source_field_ids": [FIELD_ID],
                "reference_dataset_id": REFERENCE_DATASET_ID,
                "reference_field_ids": [REFERENCE_FIELD_ID],
            },
            "REFERENCE_EXISTS",
        ),
        (
            RuleType.CROSS_TABLE_CONSISTENCY,
            {
                "source_field_ids": [FIELD_ID],
                "reference_dataset_id": REFERENCE_DATASET_ID,
                "reference_field_ids": [REFERENCE_FIELD_ID],
                "comparison": "EQUALS",
            },
            "CROSS_TABLE_EQUALS",
        ),
    ],
)
def test_fr_023_fr_032_fr_033_fr_034_uc_005_builds_mvp_template_plans(
    rule_type: RuleType,
    parameters: dict[str, Any],
    expected_operator: str,
) -> None:
    plan = build_rule_plan(rule_type, parameters)

    assert plan["operator"] == expected_operator


@pytest.mark.parametrize(
    ("rule_type", "parameters"),
    [
        (RuleType.REQUIRED, {}),
        (RuleType.UNIQUE, {"field_ids": []}),
        (RuleType.RANGE, {"field_id": FIELD_ID, "minimum": 10, "maximum": 1}),
        (RuleType.REGEX, {"field_id": FIELD_ID, "pattern": "["}),
        (
            RuleType.FRESHNESS,
            {"field_id": SECOND_FIELD_ID, "max_age_minutes": 0, "timezone": "Europe/Istanbul"},
        ),
        (
            RuleType.REFERENTIAL_INTEGRITY,
            {
                "source_field_ids": [FIELD_ID, SECOND_FIELD_ID],
                "reference_dataset_id": REFERENCE_DATASET_ID,
                "reference_field_ids": [REFERENCE_FIELD_ID],
            },
        ),
        (
            RuleType.CROSS_TABLE_CONSISTENCY,
            {
                "source_field_ids": [FIELD_ID],
                "reference_dataset_id": REFERENCE_DATASET_ID,
                "reference_field_ids": [REFERENCE_FIELD_ID],
                "comparison": "CONTAINS",
            },
        ),
    ],
)
def test_fr_023_uc_005_rejects_invalid_template_parameters(
    rule_type: RuleType,
    parameters: dict[str, Any],
) -> None:
    with pytest.raises(RuleValidationError):
        build_rule_plan(rule_type, parameters)


def test_fr_025_fr_027_uc_005_creates_draft_with_valid_scope_threshold_and_owner() -> None:
    executor = FakeRuleExecutor(RuleTestComputation(1, 1, 0))
    service = _rule_service(SQLiteRuleRepository(), FakeMetadataCatalog(), executor)

    rule, version = _create_required_rule(service, correlation_id="correlation-rule-create")
    audit = _audit_events(service)[-1]

    assert rule.code == "DQ_CUSTOMER_EMAIL_REQUIRED"
    assert rule.dataset_id == DATASET_ID
    assert rule.field_ids == (FIELD_ID,)
    assert rule.status.value == "DRAFT"
    assert version.version_no == 1
    assert version.threshold == 90.0
    assert version.weight == 1.0
    assert audit.action == "QUALITY_RULE_CREATED"
    assert audit.correlation_id == "correlation-rule-create"
    assert audit.new_value_summary["rule_version_id"] == version.rule_version_id
    assert audit.redaction_policy_version == "AUDIT_REDACTION_V3"


@pytest.mark.parametrize(
    ("threshold", "weight"),
    [(-1, 1), (101, 1), (90, 0), (90, -1)],
)
def test_fr_025_fr_027_uc_005_rejects_invalid_scope_threshold_or_weight(
    threshold: float,
    weight: float,
) -> None:
    service = _rule_service(
        SQLiteRuleRepository(),
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(1, 1, 0)),
    )

    with pytest.raises(RuleValidationError):
        _create_required_rule(service, threshold=threshold, weight=weight)

    assert service.repository.list_versions("missing") == []


def test_fr_025_uc_005_rejects_field_outside_dataset() -> None:
    service = _rule_service(
        SQLiteRuleRepository(),
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(1, 1, 0)),
    )

    with pytest.raises(RuleValidationError, match="invalid field reference"):
        _create_required_rule(service, parameters={"field_id": REFERENCE_FIELD_ID})


def test_fr_029_uc_005_creates_immutable_version_and_preserves_history() -> None:
    repository = SQLiteRuleRepository()
    service = _rule_service(
        repository,
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(1, 1, 0)),
    )
    rule, first = _create_required_rule(service)

    second = service.create_version(
        actor_id="user-1",
        quality_rule_id=rule.quality_rule_id,
        parameters={"field_id": SECOND_FIELD_ID},
        threshold=95,
        weight=2,
        criticality="HIGH",
    )

    with pytest.raises(TypeError):
        first.definition["field_id"] = SECOND_FIELD_ID
    versions = repository.list_versions(rule.quality_rule_id)
    assert [version.version_no for version in versions] == [1, 2]
    assert versions[0].definition["field_id"] == FIELD_ID
    assert second.definition["field_id"] == SECOND_FIELD_ID


def test_rule_007_legacy_rule_version_schema_preserves_history_with_unknown_preparer(
    tmp_path: Path,
) -> None:
    database = tmp_path / "legacy-rules.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE rule_versions (
            rule_version_id TEXT PRIMARY KEY,
            quality_rule_id TEXT NOT NULL,
            version_no INTEGER NOT NULL,
            rule_type TEXT NOT NULL,
            definition TEXT NOT NULL,
            threshold REAL NOT NULL,
            weight REAL NOT NULL,
            criticality TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (quality_rule_id, version_no)
        );
        INSERT INTO rule_versions VALUES (
            'version-legacy', 'rule-legacy', 1, 'REQUIRED',
            '{"field_id":"field-main","operator":"IS_NOT_NULL"}',
            90, 1, 'CRITICAL', '2026-07-16T12:00:00+00:00'
        );
        """
    )
    connection.close()

    repository = SQLiteRuleRepository(str(database))
    version = repository.get_version("version-legacy")

    assert version.prepared_by_actor_id == "LEGACY_UNKNOWN"
    columns = {
        row["name"]
        for row in repository.connection.execute("PRAGMA table_info(rule_versions)").fetchall()
    }
    assert "prepared_by_actor_id" in columns


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO customer(id) VALUES (1)",
        "UPDATE customer SET active = false",
        "DELETE FROM customer",
        "DROP TABLE customer",
        "TRUNCATE TABLE customer",
        "SELECT 1; DELETE FROM customer",
    ],
)
def test_nfr_sec_006_ac_006_uc_005_rejects_dml_ddl_before_rule_test_executor(sql: str) -> None:
    executor = FakeRuleExecutor(RuleTestComputation(1, 1, 0))
    service = _rule_service(SQLiteRuleRepository(), FakeMetadataCatalog(), executor)

    with pytest.raises(RuleValidationError, match="read-only"):
        service.create_rule(
            actor_id="user-1",
            code="DQ_CUSTOM_SQL",
            name="Salt okunur özel SQL",
            dataset_id=DATASET_ID,
            rule_type="CUSTOM_SQL",
            parameters={"sql": sql},
            primary_dimension="VALIDITY",
            threshold=90,
            weight=1,
            criticality="MEDIUM",
            owner_user_id="owner-1",
        )

    assert executor.calls == []


def test_fr_029_fr_031_uc_006_ac_009_persists_test_counts_and_preview_score() -> None:
    repository = SQLiteRuleRepository()
    executor = FakeRuleExecutor(RuleTestComputation(125, 100, 25))
    service = _rule_service(repository, FakeMetadataCatalog(), executor)
    _, version = _create_required_rule(service)

    result = service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)
    history = repository.list_test_results(version.rule_version_id)

    assert result.status is RuleTestStatus.SUCCESS
    assert result.record_limit == 10_000
    assert result.checked_count == 125
    assert result.passed_count == 100
    assert result.failed_count == 25
    assert result.success_rate == 80.0
    assert result.preview_score == 80.0
    assert result.official_score_included is False
    assert history == [result]
    assert executor.calls[0]["record_limit"] == 10_000
    assert executor.calls[0]["version"].rule_version_id == version.rule_version_id


def test_fr_031_uc_006_allows_reduced_limit_and_rejects_limit_above_policy() -> None:
    executor = FakeRuleExecutor(RuleTestComputation(100, 100, 0))
    service = _rule_service(SQLiteRuleRepository(), FakeMetadataCatalog(), executor)
    _, version = _create_required_rule(service)

    result = service.test_rule(
        actor_id="user-1",
        rule_version_id=version.rule_version_id,
        options=RuleTestOptions(limit=500),
    )

    assert result.record_limit == 500
    with pytest.raises(RuleValidationError, match="10000"):
        service.test_rule(
            actor_id="user-1",
            rule_version_id=version.rule_version_id,
            options=RuleTestOptions(limit=10_001),
        )
    assert len(executor.calls) == 1


def test_fr_031_uc_006_requires_successful_source_connection_test() -> None:
    executor = FakeRuleExecutor(RuleTestComputation(1, 1, 0))
    catalog = FakeMetadataCatalog(source_status=DataSourceStatus.TEST_PENDING)
    service = _rule_service(SQLiteRuleRepository(), catalog, executor)
    _, version = _create_required_rule(service)

    with pytest.raises(RuleValidationError, match="successful connection"):
        service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)

    assert executor.calls == []


def test_rule_003_fr_031_uc_006_persists_technical_error_without_numeric_score() -> None:
    repository = SQLiteRuleRepository()
    executor = FakeRuleExecutor(RuleTestTechnicalError("TIMEOUT"))
    service = _rule_service(repository, FakeMetadataCatalog(), executor)
    _, version = _create_required_rule(service)

    result = service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)

    assert result.status is RuleTestStatus.TECHNICAL_ERROR
    assert result.error_class == "TIMEOUT"
    assert result.success_rate is None
    assert result.preview_score is None
    assert result.failed_count == 0
    assert repository.list_test_results(version.rule_version_id) == [result]
    audit = _audit_events(service)[-1]
    assert audit.result.value == "FAILURE"
    assert audit.reason_code == "TIMEOUT"


def test_fr_030_uc_005_activates_only_after_successful_latest_version_test() -> None:
    repository = SQLiteRuleRepository()
    service = _rule_service(
        repository,
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(5, 5, 0)),
    )
    rule, version = _create_required_rule(service)

    service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)
    active = service.activate_rule(actor_id="user-1", quality_rule_id=rule.quality_rule_id)

    assert active.status is RuleStatus.ACTIVE
    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.ACTIVE
    audit = _audit_events(service)[-1]
    assert audit.old_value_summary == {"status": "DRAFT"}
    assert audit.new_value_summary["status"] == "ACTIVE"


def test_fr_030_uc_005_rejects_activation_without_successful_test() -> None:
    service = _rule_service(
        SQLiteRuleRepository(),
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(1, 1, 0)),
    )
    rule, _ = _create_required_rule(service)

    with pytest.raises(RuleValidationError, match="successful latest-version test"):
        service.activate_rule(actor_id="user-1", quality_rule_id=rule.quality_rule_id)


def test_passivate_rule_transitions_active_to_passive() -> None:
    repository = SQLiteRuleRepository()
    service = _rule_service(
        repository,
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(5, 5, 0)),
    )
    rule, version = _create_required_rule(service)
    service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)
    service.activate_rule(actor_id="user-1", quality_rule_id=rule.quality_rule_id)

    passive = service.passivate_rule(
        quality_rule_id=rule.quality_rule_id,
        actor_context=_actor_context("steward-1", {"DATA_STEWARD"}),
    )

    assert passive.status is RuleStatus.PASSIVE
    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.PASSIVE
    audit = _audit_events(service)[-1]
    assert audit.action == "QUALITY_RULE_PASSIVATED"
    assert audit.old_value_summary == {"status": "ACTIVE"}
    assert audit.new_value_summary["status"] == "PASSIVE"


def test_passivate_rule_rejects_non_active_rule() -> None:
    repository = SQLiteRuleRepository()
    service = _rule_service(
        repository,
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(5, 5, 0)),
    )
    rule, _ = _create_required_rule(service)

    with pytest.raises(RuleValidationError, match="Only an active rule"):
        service.passivate_rule(
            quality_rule_id=rule.quality_rule_id,
            actor_context=_actor_context("steward-1", {"DATA_STEWARD"}),
        )


def test_passivate_rule_rejects_unauthorized_actor() -> None:
    repository = SQLiteRuleRepository()
    service = _rule_service(
        repository,
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(5, 5, 0)),
    )
    rule, version = _create_required_rule(service)
    service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)
    service.activate_rule(actor_id="user-1", quality_rule_id=rule.quality_rule_id)

    with pytest.raises(RuleAuthorizationError):
        service.passivate_rule(
            quality_rule_id=rule.quality_rule_id,
            actor_context=_actor_context("viewer-1", {"DATA_VIEWER"}),
        )


def test_passivate_rule_rejects_missing_actor_context() -> None:
    repository = SQLiteRuleRepository()
    service = _rule_service(
        repository,
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(5, 5, 0)),
    )
    rule, version = _create_required_rule(service)
    service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)
    service.activate_rule(actor_id="user-1", quality_rule_id=rule.quality_rule_id)

    with pytest.raises(RuleAuthorizationError, match="Trusted actor context"):
        service.passivate_rule(
            quality_rule_id=rule.quality_rule_id,
            actor_context=None,
        )


def test_passivate_rule_rejects_out_of_scope_actor() -> None:
    repository = SQLiteRuleRepository()
    service = _rule_service(
        repository,
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(5, 5, 0)),
    )
    rule, version = _create_required_rule(service)
    service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)
    service.activate_rule(actor_id="user-1", quality_rule_id=rule.quality_rule_id)

    with pytest.raises(RuleAuthorizationError, match="outside the rule dataset scope"):
        service.passivate_rule(
            quality_rule_id=rule.quality_rule_id,
            actor_context=_actor_context(
                "steward-other",
                {"DATA_STEWARD"},
                dataset_ids={"dataset-other"},
            ),
        )


def test_passivate_rule_audit_outbox_failure_rolls_back() -> None:
    repository = SQLiteRuleRepository()
    service = _rule_service(
        repository,
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(5, 5, 0)),
    )
    rule, version = _create_required_rule(service)
    service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)
    service.activate_rule(actor_id="user-1", quality_rule_id=rule.quality_rule_id)
    _use_failing_stage(service)

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        service.passivate_rule(
            quality_rule_id=rule.quality_rule_id,
            actor_context=_actor_context("steward-1", {"DATA_STEWARD"}),
        )

    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.ACTIVE


class FailingAuditRepository:
    def append(self, prepared: PreparedAuditEvent) -> AuditEvent:
        raise sqlite3.OperationalError("synthetic audit outage")


class FailingStageAudit(SQLiteTransactionalAudit):
    def stage(self, prepared: PreparedAuditEvent) -> None:
        raise sqlite3.OperationalError("synthetic outbox write failure")


def _use_failing_stage(service: RuleService) -> None:
    current_audit = service.transactional_audit
    service.transactional_audit = FailingStageAudit(
        service.repository.connection,
        current_audit.redactor,
        current_audit.repository,
        policy_version="AUDIT_OUTBOX_TEST_V1",
    )


def test_fr_077_bfr_aud_004_rule_creation_is_durably_buffered_on_outage() -> None:
    repository = SQLiteRuleRepository()
    failing_repository = FailingAuditRepository()
    redactor = AuditRedactor(build_default_redaction_policy())
    transactional_audit = SQLiteTransactionalAudit(
        repository.connection,
        redactor,
        failing_repository,
        policy_version="AUDIT_OUTBOX_TEST_V1",
    )
    service = RuleService(
        repository,
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(1, 1, 0)),
        audit_sink=AuditService(
            failing_repository,
            redactor,
            AuditFailurePolicy("AUDIT_FAILURE_TEST_V1", AuditFailureMode.FAIL_CLOSED),
        ),
        transactional_audit=transactional_audit,
    )

    _create_required_rule(service, correlation_id="correlation-rule-audit-failure")

    stored_count = repository.connection.execute("SELECT COUNT(*) FROM quality_rules").fetchone()[0]
    assert stored_count == 1
    pending = transactional_audit.list_pending()
    assert len(pending) == 1
    assert pending[0].correlation_id == "correlation-rule-audit-failure"
    assert pending[0].action == "QUALITY_RULE_CREATED"


def test_bfr_aud_004_outbox_failure_rolls_back_rule_activation() -> None:
    repository = SQLiteRuleRepository()
    service = _rule_service(
        repository,
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(5, 5, 0)),
    )
    rule, version = _create_required_rule(service)
    service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)
    _use_failing_stage(service)

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        service.activate_rule(actor_id="user-1", quality_rule_id=rule.quality_rule_id)

    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.DRAFT


def test_fr_035_bfr_sod_001_002_separate_checker_activates_critical_rule() -> None:
    repository = SQLiteRuleRepository()
    service = _approval_rule_service(repository)
    rule, version = _create_required_rule(service, criticality="CRITICAL")
    service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)

    with pytest.raises(RuleValidationError, match="maker-checker approval"):
        service.activate_rule(actor_id="user-1", quality_rule_id=rule.quality_rule_id)

    request = service.request_rule_approval(
        actor_context=_actor_context("maker-1", {"RULE_MAKER"}),
        quality_rule_id=rule.quality_rule_id,
    )
    decided = service.decide_rule_approval(
        actor_context=_actor_context("checker-1", {"RULE_CHECKER"}),
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="RULE.TEST.PASSED",
    )

    assert request.status is RuleApprovalStatus.PENDING
    assert decided.status is RuleApprovalStatus.APPROVED
    assert decided.rule_version_id == version.rule_version_id
    assert decided.maker_actor_id == "maker-1"
    assert decided.checker_actor_id == "checker-1"
    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.ACTIVE
    approval_audits = [event for event in _audit_events(service) if "APPROVAL" in event.action]
    assert [event.action for event in approval_audits] == [
        "QUALITY_RULE_APPROVAL_REQUESTED",
        "QUALITY_RULE_APPROVAL_DECIDED",
    ]
    assert approval_audits[-1].new_value_summary == {
        "rule_version_id": version.rule_version_id,
        "approval_request_id": request.approval_request_id,
        "policy_version": "RULE_APPROVAL_POLICY_V1",
        "status": "APPROVED",
    }
    assert "RULE.TEST.PASSED" not in str(approval_audits)
    assert approval_audits[-1].session_id_digest is not None


def test_fr_035_bfr_sod_002_maker_cannot_decide_same_change() -> None:
    repository = SQLiteRuleRepository()
    service = _approval_rule_service(repository)
    maker = _actor_context("maker-checker-1", {"RULE_MAKER", "RULE_CHECKER"})
    rule, version = _create_required_rule(
        service,
        criticality="CRITICAL",
        actor_context=maker,
    )
    service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)
    request = service.request_rule_approval(
        actor_context=maker,
        quality_rule_id=rule.quality_rule_id,
    )

    with pytest.raises(RuleAuthorizationError, match="Maker cannot"):
        service.decide_rule_approval(
            actor_context=maker,
            approval_request_id=request.approval_request_id,
            decision="APPROVE",
            reason_code="SELF.APPROVAL",
        )

    assert repository.get_approval_request(request.approval_request_id).status is (
        RuleApprovalStatus.PENDING
    )
    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.DRAFT


def test_fr_035_critical_rule_creation_requires_matching_trusted_maker() -> None:
    service = _approval_rule_service(SQLiteRuleRepository())

    with pytest.raises(RuleAuthorizationError, match="Trusted actor context"):
        _create_required_rule(
            service,
            criticality="CRITICAL",
            actor_context=None,
            default_critical_context=False,
        )


@pytest.mark.parametrize(
    "actor_context",
    [
        None,
        pytest.param(
            lambda: _actor_context(
                "expired-maker",
                {"RULE_MAKER"},
                expires_at=NOW,
            ),
            id="expired",
        ),
        pytest.param(
            lambda: _actor_context("wrong-role", {"DATA_VIEWER"}),
            id="wrong-role",
        ),
        pytest.param(
            lambda: _actor_context(
                "wrong-scope",
                {"RULE_MAKER"},
                dataset_ids={"dataset-other"},
            ),
            id="wrong-scope",
        ),
    ],
)
def test_br_rule_001_bfr_iam_001_rule_approval_fails_closed_without_valid_context(
    actor_context: ActorContext | Any,
) -> None:
    service = _approval_rule_service(SQLiteRuleRepository())
    rule, version = _create_required_rule(service, criticality="CRITICAL")
    service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)
    resolved_context = actor_context() if callable(actor_context) else actor_context

    with pytest.raises(RuleAuthorizationError):
        service.request_rule_approval(
            actor_context=resolved_context,
            quality_rule_id=rule.quality_rule_id,
        )


def test_fr_035_bfr_sod_004_rejection_is_versioned_audited_and_keeps_draft() -> None:
    repository = SQLiteRuleRepository()
    service = _approval_rule_service(repository)
    rule, version = _create_required_rule(service, criticality="CRITICAL")
    service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)
    request = service.request_rule_approval(
        actor_context=_actor_context("maker-1", {"RULE_MAKER"}),
        quality_rule_id=rule.quality_rule_id,
    )

    rejected = service.decide_rule_approval(
        actor_context=_actor_context("checker-1", {"RULE_CHECKER"}),
        approval_request_id=request.approval_request_id,
        decision="REJECT",
        reason_code="OWNER.REVIEW.REQUIRED",
    )

    assert rejected.status is RuleApprovalStatus.REJECTED
    assert rejected.rule_version_id == version.rule_version_id
    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.DRAFT
    audit = _audit_events(service)[-1]
    assert audit.reason_code == "RULE_APPROVAL_REJECTED"
    assert audit.new_value_summary["status"] == "REJECTED"
    assert "OWNER.REVIEW.REQUIRED" not in str(audit)


def test_fr_035_bfr_sod_004_maker_withdraws_pending_rule_approval() -> None:
    repository = SQLiteRuleRepository()
    service = _approval_rule_service(repository)
    rule, version, request = _pending_critical_rule_approval(service)

    withdrawn = service.withdraw_rule_approval(
        actor_context=_actor_context("maker-1", {"RULE_MAKER"}),
        approval_request_id=request.approval_request_id,
        reason_code="RULE.CHANGE.REQUIRED",
    )

    assert withdrawn.status is RuleApprovalStatus.WITHDRAWN
    assert withdrawn.rule_version_id == version.rule_version_id
    assert withdrawn.maker_actor_id == "maker-1"
    assert withdrawn.checker_actor_id is None
    assert withdrawn.decision_reason_code == "RULE.CHANGE.REQUIRED"
    assert withdrawn.decided_at == NOW
    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.DRAFT
    audit = _audit_events(service)[-1]
    assert audit.action == "QUALITY_RULE_APPROVAL_WITHDRAWN"
    assert audit.reason_code == "RULE_APPROVAL_WITHDRAWN"
    assert audit.old_value_summary == {"status": "PENDING"}
    assert audit.new_value_summary == {
        "rule_version_id": version.rule_version_id,
        "approval_request_id": request.approval_request_id,
        "policy_version": "RULE_APPROVAL_POLICY_V1",
        "status": "WITHDRAWN",
    }
    assert "RULE.CHANGE.REQUIRED" not in str(audit)
    assert audit.session_id_digest is not None

    with pytest.raises(RuleValidationError, match="not pending"):
        service.withdraw_rule_approval(
            actor_context=_actor_context("maker-1", {"RULE_MAKER"}),
            approval_request_id=request.approval_request_id,
            reason_code="RULE.REPEATED.WITHDRAWAL",
        )


def test_bfr_sod_002_different_maker_cannot_withdraw_rule_approval() -> None:
    repository = SQLiteRuleRepository()
    service = _approval_rule_service(repository)
    rule, _, request = _pending_critical_rule_approval(service)

    with pytest.raises(RuleAuthorizationError, match="request maker"):
        service.withdraw_rule_approval(
            actor_context=_actor_context("maker-2", {"RULE_MAKER"}),
            approval_request_id=request.approval_request_id,
            reason_code="RULE.NOT.MINE",
        )

    assert repository.get_approval_request(request.approval_request_id).status is (
        RuleApprovalStatus.PENDING
    )
    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.DRAFT


@pytest.mark.parametrize(
    "actor_context",
    [
        None,
        pytest.param(
            lambda: _actor_context("maker-1", {"RULE_MAKER"}, expires_at=NOW),
            id="expired",
        ),
        pytest.param(
            lambda: _actor_context("maker-1", {"DATA_VIEWER"}),
            id="wrong-role",
        ),
        pytest.param(
            lambda: _actor_context("maker-1", {"RULE_MAKER"}, dataset_ids={"dataset-other"}),
            id="wrong-scope",
        ),
        pytest.param(
            lambda: _actor_context("maker-1", {"RULE_MAKER"}, actor_type=ActorType.SERVICE),
            id="service-account",
        ),
        pytest.param(
            lambda: _actor_context("maker-1", {"DATA_VIEWER"}, privileged=True),
            id="privileged-without-role",
        ),
    ],
)
def test_br_rule_001_bfr_sod_003_rule_withdrawal_rejects_unauthorized_actor(
    actor_context: ActorContext | Any,
) -> None:
    repository = SQLiteRuleRepository()
    service = _approval_rule_service(repository)
    rule, _, request = _pending_critical_rule_approval(service)
    resolved_context = actor_context() if callable(actor_context) else actor_context

    with pytest.raises(RuleAuthorizationError):
        service.withdraw_rule_approval(
            actor_context=resolved_context,
            approval_request_id=request.approval_request_id,
            reason_code="RULE.WITHDRAWAL.DENIED",
        )

    assert repository.get_approval_request(request.approval_request_id).status is (
        RuleApprovalStatus.PENDING
    )
    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.DRAFT


def test_fr_035_bfr_sod_004_rule_approval_uses_versioned_business_day_window() -> None:
    repository = SQLiteRuleRepository()
    calendar = FakeBusinessCalendar(holidays=frozenset({date(2026, 7, 17)}))
    service = _approval_rule_service(repository, calendar=calendar)

    _, _, request = _pending_critical_rule_approval(service)

    assert request.requested_at == NOW
    assert request.target_at == datetime(2026, 7, 22, 15, 0, tzinfo=timezone.utc)
    assert request.expires_at == datetime(2026, 7, 31, 15, 0, tzinfo=timezone.utc)
    assert request.business_calendar_version == "BANK_BUSINESS_CALENDAR_V1"
    stored = repository.get_approval_request(request.approval_request_id)
    assert stored == request


def test_fr_035_bfr_sod_004_expired_request_cannot_be_decided_and_can_be_recreated() -> None:
    repository = SQLiteRuleRepository()
    clock = MutableClock(NOW)
    service = _approval_rule_service(repository, clock=clock)
    rule, version, request = _pending_critical_rule_approval(service)
    assert request.expires_at is not None
    clock.now = request.expires_at

    with pytest.raises(RuleValidationError, match="expired and must be recreated"):
        service.decide_rule_approval(
            actor_context=_actor_context_at(clock.now, "checker-1", {"RULE_CHECKER"}),
            approval_request_id=request.approval_request_id,
            decision="APPROVE",
            reason_code="RULE.TEST.PASSED",
        )

    expired = service.expire_due_rule_approvals(
        actor_context=_actor_context_at(
            clock.now,
            "rule-expiry-worker",
            {"RULE_APPROVAL_EXPIRY_WORKER"},
            actor_type=ActorType.SERVICE,
        )
    )

    assert len(expired) == 1
    assert expired[0].status is RuleApprovalStatus.EXPIRED
    assert expired[0].decision_reason_code == "RULE.APPROVAL.EXPIRED"
    assert expired[0].decided_at == clock.now
    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.DRAFT
    audit = _audit_events(service)[-1]
    assert audit.action == "QUALITY_RULE_APPROVAL_EXPIRED"
    assert audit.reason_code == "RULE_APPROVAL_EXPIRED"
    assert audit.old_value_summary == {"status": "PENDING"}
    assert audit.new_value_summary["status"] == "EXPIRED"
    assert "maker-1" not in str(audit)

    recreated = service.request_rule_approval(
        actor_context=_actor_context_at(clock.now, "maker-1", {"RULE_MAKER"}),
        quality_rule_id=rule.quality_rule_id,
    )
    assert recreated.status is RuleApprovalStatus.PENDING
    assert recreated.rule_version_id == version.rule_version_id
    assert recreated.approval_request_id != request.approval_request_id


@pytest.mark.parametrize(
    "actor_context",
    [
        None,
        pytest.param(
            lambda now: _actor_context_at(now, "human", {"RULE_APPROVAL_EXPIRY_WORKER"}),
            id="human-account",
        ),
        pytest.param(
            lambda now: _actor_context_at(
                now, "service-wrong-role", {"RULE_CHECKER"}, actor_type=ActorType.SERVICE
            ),
            id="service-wrong-role",
        ),
        pytest.param(
            lambda now: _actor_context_at(
                now,
                "service-wrong-scope",
                {"RULE_APPROVAL_EXPIRY_WORKER"},
                dataset_ids={"dataset-other"},
                actor_type=ActorType.SERVICE,
            ),
            id="service-wrong-scope",
        ),
    ],
)
def test_br_rule_001_bfr_sod_003_expiry_rejects_unauthorized_actor(
    actor_context: ActorContext | Any,
) -> None:
    repository = SQLiteRuleRepository()
    clock = MutableClock(NOW)
    service = _approval_rule_service(repository, clock=clock)
    rule, _, request = _pending_critical_rule_approval(service)
    assert request.expires_at is not None
    clock.now = request.expires_at
    resolved_context = actor_context(clock.now) if callable(actor_context) else actor_context

    with pytest.raises(RuleAuthorizationError):
        service.expire_due_rule_approvals(actor_context=resolved_context)

    assert repository.get_approval_request(request.approval_request_id).status is (
        RuleApprovalStatus.PENDING
    )
    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.DRAFT


def test_bfr_aud_004_outbox_failure_rolls_back_rule_approval_expiry() -> None:
    repository = SQLiteRuleRepository()
    clock = MutableClock(NOW)
    service = _approval_rule_service(repository, clock=clock)
    _, _, request = _pending_critical_rule_approval(service)
    assert request.expires_at is not None
    clock.now = request.expires_at
    _use_failing_stage(service)

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        service.expire_due_rule_approvals(
            actor_context=_actor_context_at(
                clock.now,
                "rule-expiry-worker",
                {"RULE_APPROVAL_EXPIRY_WORKER"},
                actor_type=ActorType.SERVICE,
            )
        )

    assert repository.get_approval_request(request.approval_request_id).status is (
        RuleApprovalStatus.PENDING
    )


def test_bfr_sod_004_legacy_approval_schema_migrates_without_losing_history(
    tmp_path: Path,
) -> None:
    database = tmp_path / "legacy-rule-approval.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE rule_approval_requests (
            approval_request_id TEXT PRIMARY KEY,
            rule_version_id TEXT NOT NULL UNIQUE,
            maker_actor_id TEXT NOT NULL,
            checker_actor_id TEXT,
            policy_version TEXT NOT NULL,
            status TEXT NOT NULL,
            decision_reason_code TEXT,
            requested_at TEXT NOT NULL,
            decided_at TEXT
        );
        INSERT INTO rule_approval_requests (
            approval_request_id, rule_version_id, maker_actor_id,
            policy_version, status, requested_at
        ) VALUES (
            'approval-legacy', 'version-legacy', 'maker-legacy',
            'RULE_APPROVAL_POLICY_LEGACY', 'APPROVED', '2026-07-16T15:00:00+00:00'
        );
        """
    )
    connection.close()

    repository = SQLiteRuleRepository(str(database))

    stored = repository.get_approval_request("approval-legacy")
    assert stored.status is RuleApprovalStatus.APPROVED
    assert stored.target_at is None
    assert stored.expires_at is None
    columns = {
        row["name"]
        for row in repository.connection.execute(
            "PRAGMA table_info(rule_approval_requests)"
        ).fetchall()
    }
    assert {"target_at", "expires_at", "business_calendar_version"} <= columns
    indexes = repository.connection.execute("PRAGMA index_list(rule_approval_requests)").fetchall()
    assert any(row["name"] == "ux_rule_approval_pending_version" for row in indexes)


def test_rule_007_stale_rule_approval_can_be_withdrawn_without_affecting_new_version() -> None:
    repository = SQLiteRuleRepository()
    service = _approval_rule_service(repository)
    rule, version, request = _pending_critical_rule_approval(service)
    latest = service.create_version(
        actor_id="maker-2",
        quality_rule_id=rule.quality_rule_id,
        parameters={"field_id": SECOND_FIELD_ID},
        threshold=95,
        weight=2,
        criticality="CRITICAL",
        actor_context=_actor_context("maker-2", {"RULE_MAKER"}),
    )

    withdrawn = service.withdraw_rule_approval(
        actor_context=_actor_context("maker-1", {"RULE_MAKER"}),
        approval_request_id=request.approval_request_id,
        reason_code="RULE.SUPERSEDED",
    )

    assert withdrawn.status is RuleApprovalStatus.WITHDRAWN
    assert withdrawn.rule_version_id == version.rule_version_id
    assert latest.rule_version_id != withdrawn.rule_version_id
    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.DRAFT


def test_bfr_aud_004_outbox_failure_rolls_back_rule_approval_withdrawal() -> None:
    repository = SQLiteRuleRepository()
    service = _approval_rule_service(repository)
    rule, _, request = _pending_critical_rule_approval(service)
    _use_failing_stage(service)

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        service.withdraw_rule_approval(
            actor_context=_actor_context("maker-1", {"RULE_MAKER"}),
            approval_request_id=request.approval_request_id,
            reason_code="RULE.CHANGE.REQUIRED",
        )

    assert repository.get_approval_request(request.approval_request_id).status is (
        RuleApprovalStatus.PENDING
    )
    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.DRAFT


def test_rule_007_bfr_sod_004_approval_does_not_transfer_to_new_version() -> None:
    repository = SQLiteRuleRepository()
    service = _approval_rule_service(repository)
    rule, version = _create_required_rule(service, criticality="CRITICAL")
    service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)
    request = service.request_rule_approval(
        actor_context=_actor_context("maker-1", {"RULE_MAKER"}),
        quality_rule_id=rule.quality_rule_id,
    )
    service.create_version(
        actor_id="user-2",
        quality_rule_id=rule.quality_rule_id,
        parameters={"field_id": SECOND_FIELD_ID},
        threshold=95,
        weight=2,
        criticality="CRITICAL",
        actor_context=_actor_context("user-2", {"RULE_MAKER"}),
    )

    with pytest.raises(RuleValidationError, match="latest RuleVersion"):
        service.decide_rule_approval(
            actor_context=_actor_context("checker-1", {"RULE_CHECKER"}),
            approval_request_id=request.approval_request_id,
            decision="APPROVE",
            reason_code="STALE.VERSION",
        )

    assert repository.get_approval_request(request.approval_request_id).status is (
        RuleApprovalStatus.PENDING
    )
    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.DRAFT


def test_bfr_aud_004_outbox_failure_rolls_back_rule_approval_and_activation() -> None:
    repository = SQLiteRuleRepository()
    service = _approval_rule_service(repository)
    rule, version = _create_required_rule(service, criticality="CRITICAL")
    service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)
    request = service.request_rule_approval(
        actor_context=_actor_context("maker-1", {"RULE_MAKER"}),
        quality_rule_id=rule.quality_rule_id,
    )
    _use_failing_stage(service)

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        service.decide_rule_approval(
            actor_context=_actor_context("checker-1", {"RULE_CHECKER"}),
            approval_request_id=request.approval_request_id,
            decision="APPROVE",
            reason_code="RULE.TEST.PASSED",
        )

    assert repository.get_approval_request(request.approval_request_id).status is (
        RuleApprovalStatus.PENDING
    )
    assert repository.get_rule(rule.quality_rule_id).status is RuleStatus.DRAFT


def test_bfr_aud_004_outbox_failure_rolls_back_rule_version() -> None:
    repository = SQLiteRuleRepository()
    service = _rule_service(
        repository,
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(1, 1, 0)),
    )
    rule, _ = _create_required_rule(service)
    _use_failing_stage(service)

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        service.create_version(
            actor_id="user-1",
            quality_rule_id=rule.quality_rule_id,
            parameters={"field_id": SECOND_FIELD_ID},
            threshold=95,
            weight=2,
            criticality="HIGH",
        )

    assert [version.version_no for version in repository.list_versions(rule.quality_rule_id)] == [1]


def test_bfr_aud_004_outbox_failure_rolls_back_rule_test_result() -> None:
    repository = SQLiteRuleRepository()
    service = _rule_service(
        repository,
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(1, 1, 0)),
    )
    _, version = _create_required_rule(service)
    _use_failing_stage(service)

    with pytest.raises(sqlite3.OperationalError, match="outbox write failure"):
        service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)

    assert repository.list_test_results(version.rule_version_id) == []


def test_fr_077_bfr_aud_004_rule_version_is_durably_buffered_on_outage() -> None:
    repository = SQLiteRuleRepository()
    service = _rule_service(
        repository,
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(1, 1, 0)),
    )
    rule, _ = _create_required_rule(service)
    service.transactional_audit.repository = FailingAuditRepository()

    version = service.create_version(
        actor_id="user-1",
        quality_rule_id=rule.quality_rule_id,
        parameters={"field_id": SECOND_FIELD_ID},
        threshold=95,
        weight=2,
        criticality="HIGH",
        correlation_id="correlation-buffered-version",
    )

    pending = service.transactional_audit.list_pending()
    assert repository.get_version(version.rule_version_id) == version
    assert [event.action for event in pending] == ["QUALITY_RULE_VERSION_CREATED"]
    assert pending[0].correlation_id == "correlation-buffered-version"


def test_repository_lists_only_allowed_dataset_rules_with_latest_version() -> None:
    repository = SQLiteRuleRepository()
    service = _rule_service(
        repository,
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(5, 5, 0)),
    )
    main_rule, _ = _create_required_rule(service)
    latest = service.create_version(
        actor_id="user-2",
        quality_rule_id=main_rule.quality_rule_id,
        parameters={"field_id": FIELD_ID},
        threshold=97,
        weight=2,
        criticality="HIGH",
    )
    service.create_rule(
        actor_id="user-1",
        code="dq_reference_required",
        name="Referans alanı zorunlu",
        dataset_id=REFERENCE_DATASET_ID,
        rule_type="REQUIRED",
        parameters={"field_id": REFERENCE_FIELD_ID},
        primary_dimension="COMPLETENESS",
        threshold=90,
        weight=1,
        criticality="LOW",
        owner_user_id="owner-2",
    )

    listed = repository.list_rules_with_latest_version(frozenset({DATASET_ID}))

    assert [(rule.code, version.version_no) for rule, version in listed] == [
        ("DQ_CUSTOMER_EMAIL_REQUIRED", 2)
    ]
    assert listed[0][1].rule_version_id == latest.rule_version_id
    assert repository.list_rules_with_latest_version(frozenset()) == []


def _create_required_rule(
    service: RuleService,
    *,
    parameters: dict[str, Any] | None = None,
    threshold: float = 90,
    weight: float = 1,
    correlation_id: str | None = None,
    criticality: str = "HIGH",
    actor_context: ActorContext | None = None,
    default_critical_context: bool = True,
) -> tuple[Any, Any]:
    if criticality == "CRITICAL" and actor_context is None and default_critical_context:
        actor_context = _actor_context("maker-1", {"RULE_MAKER"})
    actor_id = actor_context.actor_id if actor_context is not None else "user-1"
    return service.create_rule(
        actor_id=actor_id,
        code="dq_customer_email_required",
        name="Müşteri e-postası zorunlu",
        dataset_id=DATASET_ID,
        rule_type="REQUIRED",
        parameters=parameters or {"field_id": FIELD_ID},
        primary_dimension="COMPLETENESS",
        threshold=threshold,
        weight=weight,
        criticality=criticality,
        owner_user_id="owner-1",
        correlation_id=correlation_id,
        actor_context=actor_context,
    )


def _approval_rule_service(
    repository: SQLiteRuleRepository,
    *,
    clock: Callable[[], datetime] = lambda: NOW,
    calendar: BusinessCalendar = FakeBusinessCalendar(),
) -> RuleService:
    return _rule_service(
        repository,
        FakeMetadataCatalog(),
        FakeRuleExecutor(RuleTestComputation(5, 5, 0)),
        approval_policy=RuleApprovalPolicy(
            version="RULE_APPROVAL_POLICY_V1",
            actor_policy_version=ACTOR_POLICY_VERSION,
            maker_roles=frozenset({"RULE_MAKER"}),
            checker_roles=frozenset({"RULE_CHECKER"}),
            target_business_days=3,
            expiration_business_days=10,
            business_calendar_version="BANK_BUSINESS_CALENDAR_V1",
            expiry_service_roles=frozenset({"RULE_APPROVAL_EXPIRY_WORKER"}),
        ),
        approval_calendar=calendar,
        clock=clock,
    )


def _pending_critical_rule_approval(service: RuleService) -> tuple[Any, Any, Any]:
    rule, version = _create_required_rule(service, criticality="CRITICAL")
    service.test_rule(actor_id="user-1", rule_version_id=version.rule_version_id)
    request = service.request_rule_approval(
        actor_context=_actor_context("maker-1", {"RULE_MAKER"}),
        quality_rule_id=rule.quality_rule_id,
    )
    return rule, version, request


def _actor_context(
    actor_id: str,
    roles: set[str],
    *,
    dataset_ids: set[str] | None = None,
    expires_at: datetime = NOW + timedelta(hours=1),
    actor_type: ActorType = ActorType.USER,
    privileged: bool = False,
) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=actor_type,
        authentication_source="synthetic-identity-adapter",
        session_id=f"session-{actor_id}",
        roles=frozenset(roles),
        permitted_source_ids=frozenset({"source-main"}),
        permitted_dataset_ids=frozenset(dataset_ids or {DATASET_ID}),
        can_view_enterprise=False,
        privileged=privileged,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=expires_at,
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id=f"correlation-{actor_id}",
    )


def _actor_context_at(
    now: datetime,
    actor_id: str,
    roles: set[str],
    *,
    dataset_ids: set[str] | None = None,
    actor_type: ActorType = ActorType.USER,
) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=actor_type,
        authentication_source="synthetic-identity-adapter",
        session_id=f"session-{actor_id}",
        roles=frozenset(roles),
        permitted_source_ids=frozenset({"source-main"}),
        permitted_dataset_ids=frozenset(dataset_ids or {DATASET_ID}),
        can_view_enterprise=False,
        privileged=False,
        issued_at=now - timedelta(minutes=5),
        expires_at=now + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id=f"correlation-{actor_id}",
    )
