from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from time import perf_counter

import pytest

from veri_kalitesi.audit import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactor,
    AuditService,
    SQLiteAuditRepository,
    build_default_redaction_policy,
)
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.reporting import (
    ReportAuthorizationError,
    ReportPreviewAccessPolicy,
    ReportPreviewRequest,
    ReportPreviewService,
    ReportScoreObservation,
    ReportTechnicalError,
    ReportValidationError,
    SQLiteReportPreviewReader,
)
from veri_kalitesi.scoring import (
    QualityScore,
    ScoreLevel,
    ScoreScopeType,
    ScoreStatus,
    SQLiteScoreRepository,
)


NOW = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
ACTOR_POLICY_VERSION = "BANK_ACTOR_V1"
REPORT_POLICY_VERSION = "REPORT_PREVIEW_V1"
SOURCE_A = "source-a"
SOURCE_B = "source-b"


def test_fr_072_uc_015_summary_preview_uses_latest_authorized_aggregate() -> None:
    fixture = _fixture(source_ids={SOURCE_A})
    fixture.score_repository.add_or_get(
        _score(SOURCE_A, "70.00", NOW - timedelta(days=2), execution_id="execution-a-old")
    )
    latest = _score(
        SOURCE_A,
        "90.00",
        NOW - timedelta(days=1),
        execution_id="execution-a-latest",
    )
    fixture.score_repository.add_or_get(latest)
    fixture.score_repository.add_or_get(
        _score(SOURCE_B, "99.00", NOW, execution_id="execution-b-forbidden")
    )

    preview = fixture.service.preview_summary(_request(), fixture.context)

    assert preview.filters.start_at == NOW - timedelta(days=30)
    assert preview.filters.end_at == NOW
    assert preview.filters.source_ids == (SOURCE_A,)
    assert preview.source_count == 1
    assert preview.calculated_source_count == 1
    assert preview.average_score == Decimal("90.00")
    assert preview.rows[0].source_id == SOURCE_A
    assert preview.rows[0].score_value == Decimal("90.00")
    assert preview.rows[0].calculated_at == latest.calculated_at
    assert set(asdict(preview.rows[0])) == {
        "source_id",
        "score_value",
        "score_status",
        "level",
        "calculated_at",
    }
    assert SOURCE_B not in repr(preview)


def test_fr_048_fr_072_provisional_partial_does_not_replace_latest_official_score() -> None:
    fixture = _fixture(source_ids={SOURCE_A})
    official = _score(
        SOURCE_A,
        "80.00",
        NOW - timedelta(days=1),
        execution_id="execution-official-old",
    )
    fixture.score_repository.add_or_get(official)
    fixture.score_repository.add_or_get(
        _score(
            SOURCE_A,
            None,
            NOW,
            execution_id="execution-provisional-new",
            status=ScoreStatus.PARTIAL,
            level=None,
            official=False,
        )
    )

    preview = fixture.service.preview_summary(_request(), fixture.context)

    assert preview.source_count == 1
    assert preview.rows[0].score_value == Decimal("80.00")
    assert preview.rows[0].calculated_at == official.calculated_at


def test_fr_048_fr_072_official_partial_is_included_in_report_summary() -> None:
    fixture = _fixture(source_ids={SOURCE_A})
    fixture.score_repository.add_or_get(
        _score(
            SOURCE_A,
            "85.00",
            NOW,
            execution_id="execution-official-partial",
            status=ScoreStatus.PARTIAL,
            level=ScoreLevel.ACCEPTABLE,
            official=True,
        )
    )

    preview = fixture.service.preview_summary(_request(), fixture.context)

    assert preview.rows[0].score_status is ScoreStatus.PARTIAL
    assert preview.calculated_source_count == 1
    assert preview.average_score == Decimal("85.00")


def test_fr_072_bfr_aud_005_preview_audit_is_data_minimum() -> None:
    fixture = _fixture(source_ids={SOURCE_A})
    fixture.score_repository.add_or_get(_score(SOURCE_A, "80.00", NOW, execution_id="execution-a"))

    fixture.service.preview_summary(_request(), fixture.context)

    event = fixture.audit_repository.list_events()[-1]
    assert event.action == "REPORT_PREVIEW_VIEWED"
    assert event.new_value_summary == {
        "calculated_source_count": 1,
        "masking_mode": "AGGREGATED_ONLY",
        "policy_version": REPORT_POLICY_VERSION,
        "query_reason_code": "QUALITY_REVIEW",
        "report_type": "SUMMARY",
        "requested_source_count": 1,
        "returned_source_count": 1,
        "window_days": 30,
    }
    serialized = repr(event)
    assert SOURCE_A not in serialized
    assert "execution-a" not in serialized


def test_ac_021_scope_expansion_is_rejected_before_reader_query() -> None:
    reader = CountingReader()
    fixture = _fixture(source_ids={SOURCE_A}, reader=reader)

    with pytest.raises(ReportAuthorizationError) as exc_info:
        fixture.service.preview_summary(
            _request(requested_source_ids={SOURCE_A, SOURCE_B}),
            fixture.context,
        )

    assert exc_info.value.reason_code == "SOURCE_SCOPE_DENIED"
    assert reader.calls == 0
    denied = fixture.audit_repository.list_events()[-1]
    assert denied.result.value == "DENIED"
    assert SOURCE_A not in repr(denied)
    assert SOURCE_B not in repr(denied)


@pytest.mark.parametrize(
    ("context_kind", "reason_code"),
    [
        ("missing", "UNTRUSTED_CONTEXT"),
        ("forged", "UNTRUSTED_CONTEXT"),
        ("roles-missing", "REPORT_ROLE_REQUIRED"),
        ("privileged", "PRIVILEGED_CONTEXT_NOT_ALLOWED"),
        ("service", "ACTOR_TYPE_NOT_ALLOWED"),
    ],
)
def test_nfr_sec_001_brule_001_untrusted_report_access_is_denied_and_audited(
    context_kind: str,
    reason_code: str,
) -> None:
    fixture = _fixture(source_ids={SOURCE_A})
    contexts = {
        "missing": None,
        "forged": replace(fixture.context, _trust_marker=object()),
        "roles-missing": _context({SOURCE_A}, roles=frozenset()),
        "privileged": _context({SOURCE_A}, privileged=True),
        "service": _context({SOURCE_A}, actor_type=ActorType.SERVICE),
    }

    with pytest.raises(ReportAuthorizationError) as exc_info:
        fixture.service.preview_summary(_request(), contexts[context_kind])

    assert exc_info.value.reason_code == reason_code
    denied = fixture.audit_repository.list_events()[-1]
    assert denied.action == "REPORT_PREVIEW_AUTHORIZATION"
    assert denied.reason_code == reason_code
    assert denied.new_value_summary == {
        "policy_version": REPORT_POLICY_VERSION,
        "reason_code": reason_code,
    }


@pytest.mark.parametrize(
    "invalid_kind",
    ["window", "order", "reason", "source"],
)
def test_fr_072_uc_015_invalid_preview_filter_is_rejected(invalid_kind: str) -> None:
    fixture = _fixture(source_ids={SOURCE_A})
    requests = {
        "window": _request(start_at=NOW - timedelta(days=32)),
        "order": _request(start_at=NOW, end_at=NOW - timedelta(days=1)),
        "reason": _request(reason_code="free text reason"),
        "source": _request(requested_source_ids={" "}),
    }

    with pytest.raises(ReportValidationError):
        fixture.service.preview_summary(requests[invalid_kind], fixture.context)


def test_nfr_prv_002_no_data_and_technical_statuses_are_never_zero_filled() -> None:
    fixture = _fixture(source_ids={SOURCE_A, SOURCE_B})
    fixture.score_repository.add_or_get(
        _score(
            SOURCE_A,
            None,
            NOW,
            execution_id="execution-no-data",
            status=ScoreStatus.NO_DATA,
            level=None,
        )
    )
    fixture.score_repository.add_or_get(
        _score(
            SOURCE_B,
            None,
            NOW,
            execution_id="execution-technical",
            status=ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR,
            level=None,
        )
    )

    preview = fixture.service.preview_summary(_request(), fixture.context)

    assert preview.source_count == 2
    assert preview.calculated_source_count == 0
    assert preview.average_score is None
    assert all(row.score_value is None for row in preview.rows)


def test_nfr_prv_003_score_preview_reader_executes_only_read_statements() -> None:
    fixture = _fixture(source_ids={SOURCE_A})
    fixture.score_repository.add_or_get(
        _score(SOURCE_A, "80.00", NOW, execution_id="execution-read-only")
    )
    statements: list[str] = []
    fixture.score_repository.connection.set_trace_callback(statements.append)

    fixture.service.preview_summary(_request(), fixture.context)

    assert statements
    assert all(
        statement.lstrip().upper().startswith(("SELECT", "WITH")) for statement in statements
    )


def test_uc_015_reader_failure_is_redacted_technical_error() -> None:
    fixture = _fixture(source_ids={SOURCE_A}, reader=FailingReader())

    with pytest.raises(ReportTechnicalError) as exc_info:
        fixture.service.preview_summary(_request(), fixture.context)

    assert exc_info.value.correlation_id == "correlation-report"
    assert "customer secret" not in str(exc_info.value)


def test_nfr_sec_001_reader_scope_leak_fails_closed() -> None:
    fixture = _fixture(source_ids={SOURCE_A}, reader=LeakingReader())

    with pytest.raises(ReportTechnicalError):
        fixture.service.preview_summary(_request(), fixture.context)


def test_bfr_aud_005_preview_audit_failure_returns_no_result() -> None:
    score_repository = SQLiteScoreRepository()
    service = ReportPreviewService(
        SQLiteReportPreviewReader(score_repository.connection),
        FailingAuditSink(),
        _policy(),
        clock=lambda: NOW,
    )

    with pytest.raises(ReportTechnicalError):
        service.preview_summary(_request(), _context({SOURCE_A}))


def test_nfr_perf_002_summary_preview_p95_is_under_one_second_for_500_sources() -> None:
    """Local guard: 500 latest SOURCE scores, in-memory SQLite, no sampling."""
    source_ids = {f"source-{index:03d}" for index in range(500)}
    fixture = _fixture(source_ids=source_ids)
    for index, source_id in enumerate(sorted(source_ids)):
        fixture.score_repository.add_or_get(
            _score(
                source_id,
                "90.00",
                NOW,
                execution_id=f"execution-{index:03d}",
            )
        )

    durations = []
    for _ in range(20):
        started_at = perf_counter()
        preview = fixture.service.preview_summary(_request(), fixture.context)
        durations.append(perf_counter() - started_at)

    assert len(preview.rows) == 500
    assert sorted(durations)[18] < 1.0


class ReportingFixture:
    def __init__(
        self,
        service: ReportPreviewService,
        score_repository: SQLiteScoreRepository,
        audit_repository: SQLiteAuditRepository,
        context: ActorContext,
    ) -> None:
        self.service = service
        self.score_repository = score_repository
        self.audit_repository = audit_repository
        self.context = context


class CountingReader:
    def __init__(self) -> None:
        self.calls = 0

    def latest_source_scores(
        self,
        start_at: datetime,
        end_at: datetime,
        allowed_source_ids: frozenset[str],
    ) -> tuple[ReportScoreObservation, ...]:
        self.calls += 1
        return ()


class FailingReader:
    def latest_source_scores(
        self,
        start_at: datetime,
        end_at: datetime,
        allowed_source_ids: frozenset[str],
    ) -> tuple[ReportScoreObservation, ...]:
        raise OSError("customer secret")


class LeakingReader:
    def latest_source_scores(
        self,
        start_at: datetime,
        end_at: datetime,
        allowed_source_ids: frozenset[str],
    ) -> tuple[ReportScoreObservation, ...]:
        return (
            ReportScoreObservation(
                source_id=SOURCE_B,
                score_value=Decimal("99.00"),
                score_status=ScoreStatus.CALCULATED,
                level=ScoreLevel.GOOD,
                calculated_at=NOW,
            ),
        )


class FailingAuditSink:
    def append(self, event: object) -> None:
        raise OSError("synthetic audit outage")


def _fixture(
    *,
    source_ids: set[str],
    reader: CountingReader | FailingReader | LeakingReader | None = None,
) -> ReportingFixture:
    score_repository = SQLiteScoreRepository()
    audit_repository = SQLiteAuditRepository()
    audit_service = AuditService(
        audit_repository,
        AuditRedactor(build_default_redaction_policy()),
        AuditFailurePolicy(
            version="AUDIT_FAILURE_V1",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )
    service = ReportPreviewService(
        reader or SQLiteReportPreviewReader(score_repository.connection),
        audit_service,
        _policy(),
        clock=lambda: NOW,
    )
    return ReportingFixture(
        service,
        score_repository,
        audit_repository,
        _context(source_ids),
    )


def _policy() -> ReportPreviewAccessPolicy:
    return ReportPreviewAccessPolicy(
        version=REPORT_POLICY_VERSION,
        actor_policy_version=ACTOR_POLICY_VERSION,
    )


def _request(
    *,
    start_at: datetime = NOW - timedelta(days=30),
    end_at: datetime = NOW,
    reason_code: str = "QUALITY_REVIEW",
    requested_source_ids: set[str] | None = None,
) -> ReportPreviewRequest:
    return ReportPreviewRequest(
        start_at=start_at,
        end_at=end_at,
        reason_code=reason_code,
        requested_source_ids=(
            frozenset(requested_source_ids) if requested_source_ids is not None else None
        ),
    )


def _context(
    source_ids: set[str],
    *,
    roles: frozenset[str] = frozenset({"DATA_OWNER"}),
    privileged: bool = False,
    actor_type: ActorType = ActorType.USER,
) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id="report-user",
        actor_type=actor_type,
        authentication_source="synthetic-identity-adapter",
        session_id="synthetic-report-session",
        roles=roles,
        permitted_source_ids=frozenset(source_ids),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=False,
        privileged=privileged,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id="correlation-report",
    )


def _score(
    source_id: str,
    value: str | None,
    calculated_at: datetime,
    *,
    execution_id: str,
    status: ScoreStatus = ScoreStatus.CALCULATED,
    level: ScoreLevel | None = ScoreLevel.GOOD,
    official: bool | None = None,
) -> QualityScore:
    details: dict[str, object] = {"aggregate": True}
    if official is not None:
        details["included_in_official_aggregation"] = official
    return QualityScore(
        execution_id=execution_id,
        rule_version_id=None,
        scope_id=source_id,
        score_status=status,
        calculation_details=details,
        score_value=Decimal(value) if value is not None else None,
        level=level,
        scope_type=ScoreScopeType.SOURCE,
        calculated_at=calculated_at,
    )
