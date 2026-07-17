from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import sqlite3

import pytest

from veri_kalitesi.audit import (
    GENESIS_HASH,
    AuditAccessPolicy,
    AuditEvent,
    AuditEventInput,
    AuditFailureMode,
    AuditFailurePolicy,
    AuditMigrationTechnicalError,
    AuditQuery,
    AuditQueryAuthorizationError,
    AuditQueryService,
    AuditQueryTechnicalError,
    AuditQueryValidationError,
    AuditRedactionPolicy,
    AuditRedactor,
    AuditResult,
    AuditService,
    AuditValidationError,
    AuditWriteError,
    LegacyAuditMigrator,
    PreparedAuditEvent,
    SQLiteAuditRepository,
    build_default_redaction_policy,
)
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType


NOW = datetime(2026, 7, 16, 15, 0, tzinfo=timezone.utc)
ACTION = "DASHBOARD_SCOPE_AUTHORIZATION"
ALLOWED_FIELDS = frozenset(
    {"policy_version", "permitted_source_count", "can_view_enterprise", "reason_code"}
)
ACTOR_POLICY_VERSION = "BANK_ACTOR_V1"
AUDIT_ACCESS_POLICY_VERSION = "AUDIT_ACCESS_V1"


def test_fr_077_bfr_aud_001_common_versioned_envelope_is_append_only() -> None:
    repository = SQLiteAuditRepository()
    service = _service(repository)

    first = service.append(_event("correlation-1"))
    second = service.append(_event("correlation-2"))

    assert first is not None
    assert second is not None
    assert first.event_version == "AUDIT_EVENT_V1"
    assert first.previous_event_hash == GENESIS_HASH
    assert second.previous_event_hash == first.event_hash
    assert len(first.event_hash) == 64
    assert repository.list_events() == [first, second]
    assert not hasattr(repository, "update")
    assert not hasattr(repository, "delete")


def test_bfr_aud_003_idempotent_event_rejects_content_collision() -> None:
    repository = SQLiteAuditRepository()
    redactor = AuditRedactor(
        AuditRedactionPolicy(
            version="AUDIT_REDACTION_TEST_V1",
            allowed_fields_by_action={ACTION: ALLOWED_FIELDS},
        )
    )
    prepared = redactor.prepare(_event("correlation-original"))
    repository.append(prepared)

    with pytest.raises(AuditValidationError, match="event_id"):
        repository.append(replace(prepared, correlation_id="correlation-collision"))

    assert len(repository.list_events()) == 1


def test_br_rule_005_redactor_blocks_secret_structures_and_unlisted_fields() -> None:
    repository = SQLiteAuditRepository()
    service = _service(repository)
    raw_secret = "secret://synthetic/not-a-real-secret"
    event = _event(
        "correlation-redaction",
        new_values={
            "policy_version": "POLICY_V1",
            "password": "synthetic-password",
            "reason_code": raw_secret,
            "roles": ["ROLE_A"],
            "unlisted": "must-not-persist",
        },
    )

    stored = service.append(event)

    assert stored is not None
    assert stored.new_value_summary == {"policy_version": "POLICY_V1"}
    assert set(stored.redacted_fields) == {
        "new_values.password",
        "new_values.reason_code",
        "new_values.roles",
        "new_values.unlisted",
    }
    raw_row = repository.connection.execute(
        "SELECT * FROM audit_events WHERE event_id = ?", (stored.event_id,)
    ).fetchone()
    assert raw_secret not in repr(dict(raw_row))
    assert "synthetic-password" not in repr(dict(raw_row))
    assert "must-not-persist" not in repr(dict(raw_row))


def test_br_rule_005_rejects_sensitive_text_in_persisted_envelope() -> None:
    repository = SQLiteAuditRepository()
    service = _service(repository)

    with pytest.raises(AuditValidationError):
        service.append(
            replace(
                _event("correlation-envelope-redaction"),
                reason_code="secret://synthetic/not-a-real-secret",
            )
        )

    assert repository.list_events() == []


def test_fr_079_bfr_aud_003_hash_chain_detects_tampered_event() -> None:
    repository = SQLiteAuditRepository()
    service = _service(repository)
    first = service.append(_event("correlation-1"))
    service.append(_event("correlation-2"))
    assert first is not None
    assert repository.verify_integrity().valid is True

    repository.connection.execute(
        "UPDATE audit_events SET reason_code = 'TAMPERED' WHERE event_id = ?",
        (first.event_id,),
    )
    repository.connection.commit()

    result = repository.verify_integrity()
    assert result.valid is False
    assert result.first_invalid_event_id == first.event_id
    assert result.checked_count == 1


def test_fr_077_bfr_aud_004_critical_audit_failure_is_fail_closed() -> None:
    service = _service(FailingRepository())

    with pytest.raises(AuditWriteError, match="could not be written"):
        service.append(_event("correlation-fail-closed"))


def test_bfr_aud_004_durable_mode_buffers_prepared_redacted_event() -> None:
    buffer = InMemoryDurableBuffer()
    service = _service(
        FailingRepository(),
        mode=AuditFailureMode.DURABLE_BUFFER,
        buffer=buffer,
    )

    result = service.append(
        _event(
            "correlation-buffered",
            new_values={
                "policy_version": "POLICY_V1",
                "password": "must-not-reach-buffer",
            },
        )
    )

    assert result is None
    assert len(buffer.events) == 1
    assert buffer.events[0].new_value_summary == {"policy_version": "POLICY_V1"}
    assert "must-not-reach-buffer" not in repr(buffer.events[0])


def test_bfr_aud_004_durable_mode_without_buffer_is_rejected() -> None:
    repository = SQLiteAuditRepository()
    redactor = AuditRedactor(_redaction_policy())

    with pytest.raises(AuditValidationError, match="durable buffer"):
        AuditService(
            repository,
            redactor,
            AuditFailurePolicy(
                version="AUDIT_FAILURE_V1",
                default_mode=AuditFailureMode.DURABLE_BUFFER,
            ),
        )


def test_fr_077_event_time_must_be_timezone_aware() -> None:
    service = _service(SQLiteAuditRepository())
    event = _event("correlation-naive")
    invalid = AuditEventInput(
        actor_id=event.actor_id,
        actor_type=event.actor_type,
        correlation_id=event.correlation_id,
        action=event.action,
        object_type=event.object_type,
        object_id=event.object_id,
        result=event.result,
        reason_code=event.reason_code,
        old_values=event.old_values,
        new_values=event.new_values,
        occurred_at=NOW.replace(tzinfo=None),
        session_id=event.session_id,
    )

    with pytest.raises(AuditValidationError, match="timezone-aware"):
        service.append(invalid)


def test_fr_078_uc_016_authorized_auditor_filters_records_and_audits_view() -> None:
    repository, query_service, audit_service = _query_fixture()
    first = audit_service.append(_event("correlation-first"))
    audit_service.append(
        replace(
            _event("correlation-second"),
            actor_id="other-synthetic-user",
            result=AuditResult.DENIED,
        )
    )
    assert first is not None

    page = query_service.query(
        _query(
            actor_id="synthetic-user",
            action=ACTION,
            object_type="AuthorizationDecision",
            object_id="synthetic-user",
            result=AuditResult.SUCCESS,
            correlation_id="correlation-first",
        ),
        _audit_viewer_context(),
    )

    assert page.events == (first,)
    assert page.integrity.valid is True
    assert page.integrity.checked_count == 2
    assert page.next_after_sequence_no is None
    assert page.policy_version == AUDIT_ACCESS_POLICY_VERSION
    view_event = repository.list_events()[-1]
    assert view_event.action == "AUDIT_RECORDS_VIEWED"
    assert view_event.new_value_summary == {
        "filter_count": 6,
        "integrity_valid": True,
        "page_size": 50,
        "policy_version": AUDIT_ACCESS_POLICY_VERSION,
        "query_reason_code": "CONTROL_REVIEW",
        "returned_count": 1,
    }
    assert "synthetic-user" not in repr(view_event.new_value_summary)


def test_fr_078_uc_016_cursor_pagination_uses_stable_snapshot() -> None:
    repository, query_service, audit_service = _query_fixture()
    for index in range(3):
        audit_service.append(_event(f"correlation-page-{index}"))

    first = query_service.query(_query(page_size=2), _audit_viewer_context())
    second = query_service.query(
        _query(
            page_size=2,
            after_sequence_no=first.next_after_sequence_no or 0,
            through_sequence_no=first.through_sequence_no,
        ),
        _audit_viewer_context(),
    )

    assert [event.correlation_id for event in first.events] == [
        "correlation-page-0",
        "correlation-page-1",
    ]
    assert [event.correlation_id for event in second.events] == ["correlation-page-2"]
    assert second.next_after_sequence_no is None
    assert second.through_sequence_no == first.through_sequence_no == 3
    assert len(repository.list_events()) == 5


@pytest.mark.parametrize(
    ("context_kind", "reason_code"),
    [
        ("missing", "UNTRUSTED_CONTEXT"),
        ("forged", "UNTRUSTED_CONTEXT"),
        ("roles-missing", "AUDIT_ROLE_REQUIRED"),
        ("privileged", "PRIVILEGED_CONTEXT_NOT_ALLOWED"),
        ("service", "ACTOR_TYPE_NOT_ALLOWED"),
    ],
)
def test_fr_078_nfr_sec_001_unauthorized_audit_queries_are_denied_and_audited(
    context_kind: str,
    reason_code: str,
) -> None:
    repository, query_service, _ = _query_fixture()
    contexts = {
        "missing": None,
        "forged": replace(_audit_viewer_context(), _trust_marker=object()),
        "roles-missing": _audit_viewer_context(roles=frozenset()),
        "privileged": _audit_viewer_context(privileged=True),
        "service": _audit_viewer_context(actor_type=ActorType.SERVICE),
    }

    with pytest.raises(AuditQueryAuthorizationError) as exc_info:
        query_service.query(_query(), contexts[context_kind])

    assert exc_info.value.reason_code == reason_code
    denied = repository.list_events()[-1]
    assert denied.action == "AUDIT_RECORDS_VIEW_AUTHORIZATION"
    assert denied.result is AuditResult.DENIED
    assert denied.reason_code == reason_code
    assert denied.new_value_summary == {
        "policy_version": AUDIT_ACCESS_POLICY_VERSION,
        "reason_code": reason_code,
    }


@pytest.mark.parametrize(
    "invalid_kind",
    [
        "window",
        "page-size",
        "reason",
        "action",
    ],
)
def test_fr_078_uc_016_invalid_or_overbroad_query_is_rejected(invalid_kind: str) -> None:
    _, query_service, _ = _query_fixture()
    queries = {
        "window": _query(start_at=NOW - timedelta(days=32)),
        "page-size": _query(page_size=101),
        "reason": _query(reason_code="free text reason"),
        "action": _query(action="INVALID ACTION"),
    }

    with pytest.raises(AuditQueryValidationError):
        query_service.query(queries[invalid_kind], _audit_viewer_context())


def test_fr_079_uc_016_query_reports_integrity_failure_without_changing_record() -> None:
    repository, query_service, audit_service = _query_fixture()
    stored = audit_service.append(_event("correlation-tamper-query"))
    assert stored is not None
    repository.connection.execute(
        "UPDATE audit_events SET reason_code = 'TAMPERED' WHERE event_id = ?",
        (stored.event_id,),
    )
    repository.connection.commit()

    page = query_service.query(_query(), _audit_viewer_context())

    assert page.integrity.valid is False
    assert page.integrity.first_invalid_event_id == stored.event_id
    assert page.events[0].reason_code == "TAMPERED"
    unchanged = repository.find_event(stored.event_id)
    assert unchanged is not None
    assert unchanged.reason_code == "TAMPERED"
    assert repository.list_events()[-1].new_value_summary["integrity_valid"] is False


def test_fr_078_uc_016_repository_failure_is_separate_technical_error() -> None:
    repository, query_service, _ = _query_fixture()
    repository.connection.close()

    with pytest.raises(AuditQueryTechnicalError) as exc_info:
        query_service.query(_query(), _audit_viewer_context())

    assert exc_info.value.correlation_id == "correlation-audit-viewer"


def test_bfr_aud_005_view_audit_failure_is_fail_closed() -> None:
    repository = SQLiteAuditRepository()
    query_service = AuditQueryService(
        repository,
        FailingAuditSink(),
        _audit_access_policy(),
        clock=lambda: NOW,
    )

    with pytest.raises(AuditQueryTechnicalError):
        query_service.query(_query(), _audit_viewer_context())

    assert repository.list_events() == []


def test_fr_077_fr_079_uc_016_legacy_audit_migration_is_read_only_and_idempotent() -> None:
    source = _legacy_audit_connection()
    _insert_legacy_audit(
        source,
        audit_id="legacy-source-created-1",
        action="DATA_SOURCE_CREATED",
        new_values={
            "source_type": "CSV",
            "status": "TEST_PENDING",
            "name": "must-not-migrate",
            "password": "must-not-migrate",
        },
    )
    original = tuple(source.execute("SELECT * FROM audit_records").fetchone())
    statements: list[str] = []
    source.set_trace_callback(statements.append)
    repository = SQLiteAuditRepository()
    migrator = LegacyAuditMigrator(
        source,
        repository,
        AuditRedactor(build_default_redaction_policy()),
        source_id="synthetic-data-source-metadata-v1",
    )

    inventory = migrator.inventory()
    first = migrator.migrate()
    repeated = migrator.migrate()

    event = repository.list_events()[0]
    assert inventory.table_exists is True
    assert inventory.record_count == 1
    assert first.migrated_count == 1
    assert first.duplicate_count == 0
    assert first.skipped_count == 0
    assert repeated.migrated_count == 0
    assert repeated.duplicate_count == 1
    assert event.action == "DATA_SOURCE_CREATED"
    assert event.reason_code == "LEGACY_AUDIT_MIGRATED"
    assert event.new_value_summary == {"source_type": "CSV", "status": "TEST_PENDING"}
    assert "must-not-migrate" not in repr(event)
    assert repository.verify_integrity().valid is True
    assert tuple(source.execute("SELECT * FROM audit_records").fetchone()) == original
    assert all(
        statement.lstrip().upper().startswith(("PRAGMA", "SELECT")) for statement in statements
    )


def test_fr_077_legacy_migration_reports_data_quality_issues_without_stopping() -> None:
    source = _legacy_audit_connection()
    _insert_legacy_audit(
        source,
        audit_id="legacy-invalid-json",
        action="DATA_SOURCE_CREATED",
        old_values="not-json",
    )
    _insert_legacy_audit(
        source,
        audit_id="legacy-unsupported-action",
        action="UNSUPPORTED_LEGACY_ACTION",
    )
    _insert_legacy_audit(
        source,
        audit_id="legacy-naive-time",
        action="DATA_SOURCE_CREATED",
        created_at="2026-07-16T10:00:00",
    )
    repository = SQLiteAuditRepository()
    migrator = LegacyAuditMigrator(
        source,
        repository,
        AuditRedactor(build_default_redaction_policy()),
        source_id="synthetic-data-quality-source",
    )

    report = migrator.migrate()

    assert report.total_count == 3
    assert report.migrated_count == 0
    assert report.skipped_count == 3
    assert {issue.code for issue in report.issues} == {
        "INVALID_LEGACY_VALUE",
        "NAIVE_EVENT_TIME",
        "UNSUPPORTED_ACTION",
    }
    assert all(issue.record_id_digest is not None for issue in report.issues)
    assert repository.list_events() == []


def test_bfr_aud_004_legacy_migration_separates_central_repository_technical_error() -> None:
    source = _legacy_audit_connection()
    _insert_legacy_audit(
        source,
        audit_id="legacy-technical-failure",
        action="DATA_SOURCE_CREATED",
    )
    repository = FailingMigrationRepository()
    migrator = LegacyAuditMigrator(
        source,
        repository,
        AuditRedactor(build_default_redaction_policy()),
        source_id="synthetic-technical-source",
    )

    with pytest.raises(AuditMigrationTechnicalError, match="could not accept"):
        migrator.migrate()

    assert source.execute("SELECT COUNT(*) FROM audit_records").fetchone()[0] == 1


class FailingRepository:
    def append(self, prepared: PreparedAuditEvent) -> AuditEvent:
        raise sqlite3.OperationalError("audit database unavailable")


class FailingMigrationRepository(SQLiteAuditRepository):
    def append(self, prepared: PreparedAuditEvent) -> AuditEvent:
        raise sqlite3.OperationalError("synthetic central audit outage")


class FailingAuditSink:
    def append(self, event: AuditEventInput) -> None:
        raise sqlite3.OperationalError("synthetic audit sink outage")


class InMemoryDurableBuffer:
    def __init__(self) -> None:
        self.events: list[PreparedAuditEvent] = []

    def append(self, prepared: PreparedAuditEvent) -> None:
        self.events.append(prepared)


def _service(
    repository: SQLiteAuditRepository | FailingRepository,
    *,
    mode: AuditFailureMode = AuditFailureMode.FAIL_CLOSED,
    buffer: InMemoryDurableBuffer | None = None,
) -> AuditService:
    return AuditService(
        repository,
        AuditRedactor(_redaction_policy()),
        AuditFailurePolicy(
            version="AUDIT_FAILURE_V1",
            default_mode=mode,
        ),
        durable_buffer=buffer,
    )


def _redaction_policy() -> AuditRedactionPolicy:
    return AuditRedactionPolicy(
        version="AUDIT_REDACTION_V1",
        allowed_fields_by_action={ACTION: ALLOWED_FIELDS},
    )


def _event(
    correlation_id: str,
    *,
    new_values: dict[str, object] | None = None,
) -> AuditEventInput:
    return AuditEventInput(
        actor_id="synthetic-user",
        actor_type=ActorType.USER.value,
        session_id="synthetic-session",
        correlation_id=correlation_id,
        action=ACTION,
        object_type="AuthorizationDecision",
        object_id="synthetic-user",
        result=AuditResult.SUCCESS,
        reason_code="POLICY_MATCH",
        old_values={},
        new_values=(
            new_values
            if new_values is not None
            else {
                "policy_version": "POLICY_V1",
                "permitted_source_count": 1,
                "can_view_enterprise": False,
                "reason_code": "POLICY_MATCH",
            }
        ),
        occurred_at=NOW,
    )


def _query_fixture() -> tuple[SQLiteAuditRepository, AuditQueryService, AuditService]:
    repository = SQLiteAuditRepository()
    audit_service = AuditService(
        repository,
        AuditRedactor(build_default_redaction_policy()),
        AuditFailurePolicy(
            version="AUDIT_FAILURE_V1",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )
    return (
        repository,
        AuditQueryService(
            repository,
            audit_service,
            _audit_access_policy(),
            clock=lambda: NOW,
        ),
        audit_service,
    )


def _audit_access_policy() -> AuditAccessPolicy:
    return AuditAccessPolicy(
        version=AUDIT_ACCESS_POLICY_VERSION,
        context_policy_version=ACTOR_POLICY_VERSION,
    )


def _query(
    *,
    start_at: datetime = NOW - timedelta(days=1),
    end_at: datetime = NOW + timedelta(days=1),
    reason_code: str = "CONTROL_REVIEW",
    actor_id: str | None = None,
    action: str | None = None,
    object_type: str | None = None,
    object_id: str | None = None,
    result: AuditResult | None = None,
    correlation_id: str | None = None,
    after_sequence_no: int = 0,
    through_sequence_no: int | None = None,
    page_size: int = 50,
) -> AuditQuery:
    return AuditQuery(
        start_at=start_at,
        end_at=end_at,
        reason_code=reason_code,
        actor_id=actor_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        result=result,
        correlation_id=correlation_id,
        after_sequence_no=after_sequence_no,
        through_sequence_no=through_sequence_no,
        page_size=page_size,
    )


def _audit_viewer_context(
    *,
    roles: frozenset[str] = frozenset({"AUDIT_VIEWER"}),
    privileged: bool = False,
    actor_type: ActorType = ActorType.USER,
) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id="audit-viewer-user",
        actor_type=actor_type,
        authentication_source="synthetic-identity-adapter",
        session_id="synthetic-audit-session",
        roles=roles,
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=False,
        privileged=privileged,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id="correlation-audit-viewer",
    )


def _legacy_audit_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE audit_records (
            audit_id TEXT PRIMARY KEY,
            actor_id TEXT NOT NULL,
            action TEXT NOT NULL,
            object_type TEXT NOT NULL,
            object_id TEXT NOT NULL,
            result TEXT NOT NULL,
            old_values TEXT NOT NULL,
            new_values TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    return connection


def _insert_legacy_audit(
    connection: sqlite3.Connection,
    *,
    audit_id: str,
    action: str,
    old_values: dict[str, object] | str | None = None,
    new_values: dict[str, object] | str | None = None,
    created_at: str = "2026-07-16T10:00:00+00:00",
) -> None:
    def payload(value: dict[str, object] | str | None) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value or {}, sort_keys=True)

    connection.execute(
        """
        INSERT INTO audit_records (
            audit_id, actor_id, action, object_type, object_id, result,
            old_values, new_values, created_at
        ) VALUES (?, 'synthetic-user', ?, 'DataSource', 'source-1', 'SUCCESS', ?, ?, ?)
        """,
        (audit_id, action, payload(old_values), payload(new_values), created_at),
    )
    connection.commit()
