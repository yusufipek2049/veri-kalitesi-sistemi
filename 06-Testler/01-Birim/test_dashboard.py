from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from time import perf_counter
from typing import Callable, overload
import sqlite3

import pytest

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactionPolicy,
    AuditRedactor,
    AuditResult,
    AuditService,
    SQLiteAuditRepository,
)
from veri_kalitesi.dashboard import (
    DashboardAuthorizationError,
    DashboardQueryError,
    DashboardQueryService,
    DashboardValidationError,
)
from veri_kalitesi.dashboard._legacy import LegacyDashboardQueryAdapter
from veri_kalitesi.dashboard.models import DashboardAccessScope
from veri_kalitesi.identity import (
    ActorContext,
    ActorContextIssuer,
    ActorType,
    DashboardAuthorizationPolicy,
    PolicyAuthorizationService,
)
from veri_kalitesi.scoring import (
    QualityScore,
    ScoreLevel,
    ScoreScopeType,
    ScoreStatus,
    SQLiteScoreRepository,
)


NOW = datetime(2026, 7, 16, 14, 30, tzinfo=timezone.utc)
POLICY_VERSION = "BANK_DASHBOARD_POLICY_V1"


def test_fr_002_bfr_iam_001_valid_context_returns_only_authorized_sources() -> None:
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.ENTERPRISE, None, "88.00"))
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "80.00"))
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-b", "96.00"))
    service, context, audit = _secure_service(repository, source_ids={"source-a"})

    tree = service.get_score_tree("execution-dashboard", context)

    assert tree.enterprise is None
    assert [source.scope_id for source in tree.sources] == ["source-a"]
    assert tree.sources[0].score_value == Decimal("80.00")
    assert tree.has_data is True
    assert audit.list_events()[-1].result is AuditResult.SUCCESS


def test_bfr_iam_002_caller_scope_cannot_elevate_trusted_context() -> None:
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "80.00"))
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-forged", "99.00"))
    service, context, _ = _secure_service(repository, source_ids={"source-a"})
    caller_supplied_scope = DashboardAccessScope(
        allowed_source_ids=frozenset({"source-a", "source-forged"}),
        can_view_enterprise=True,
    )

    tree = service.get_score_tree("execution-dashboard", context)

    assert caller_supplied_scope.allowed_source_ids == frozenset({"source-a", "source-forged"})
    assert [source.scope_id for source in tree.sources] == ["source-a"]
    assert tree.enterprise is None


def test_fr_054_enterprise_permission_and_technical_status_are_preserved() -> None:
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.ENTERPRISE, None, "88.00"))
    repository.add_or_get(
        _score(
            ScoreScopeType.SOURCE,
            "source-technical",
            None,
            status=ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR,
            level=None,
        )
    )
    service, context, _ = _secure_service(
        repository,
        source_ids={"source-technical"},
        can_view_enterprise=True,
    )

    tree = service.get_score_tree("execution-dashboard", context)

    assert tree.enterprise is not None
    assert tree.enterprise.score_value == Decimal("88.00")
    assert tree.sources[0].score_value is None
    assert tree.sources[0].score_status is (ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR)


def test_br_rule_001_context_absence_denies_before_repository_query() -> None:
    reader = CountingReader()
    service, _, audit = _secure_service(reader, source_ids={"source-a"})

    with pytest.raises(DashboardAuthorizationError) as error:
        service.get_score_tree("execution-dashboard", None)

    assert error.value.correlation_id == "authorization-denied"
    assert reader.calls == 0
    assert audit.list_events()[-1].reason_code == "UNTRUSTED_CONTEXT"


def test_bfr_iam_001_directly_constructed_context_is_not_trusted() -> None:
    reader = CountingReader()
    service, valid_context, audit = _secure_service(reader, source_ids={"source-a"})
    forged_context = ActorContext(
        actor_id=valid_context.actor_id,
        actor_type=valid_context.actor_type,
        authentication_source=valid_context.authentication_source,
        session_id=valid_context.session_id,
        roles=valid_context.roles,
        permitted_source_ids=frozenset({"source-forged"}),
        permitted_dataset_ids=valid_context.permitted_dataset_ids,
        can_view_enterprise=True,
        privileged=True,
        issued_at=valid_context.issued_at,
        expires_at=valid_context.expires_at,
        policy_version=valid_context.policy_version,
        correlation_id=valid_context.correlation_id,
        _trust_marker=object(),
    )

    with pytest.raises(DashboardAuthorizationError):
        service.get_score_tree("execution-dashboard", forged_context)

    assert reader.calls == 0
    event = audit.list_events()[-1]
    assert event.actor_id == "UNKNOWN"
    assert event.new_value_summary["permitted_source_count"] == 0


@pytest.mark.parametrize(
    ("expires_at", "policy_version", "reason_code"),
    [
        (NOW, POLICY_VERSION, "CONTEXT_EXPIRED"),
        (NOW + timedelta(hours=1), "STALE_POLICY", "POLICY_VERSION_MISMATCH"),
    ],
)
def test_bfr_iam_004_expired_or_stale_context_fails_closed(
    expires_at: datetime,
    policy_version: str,
    reason_code: str,
) -> None:
    reader = CountingReader()
    service, context, audit = _secure_service(
        reader,
        source_ids={"source-a"},
        expires_at=expires_at,
        context_policy_version=policy_version,
    )

    with pytest.raises(DashboardAuthorizationError):
        service.get_score_tree("execution-dashboard", context)

    assert reader.calls == 0
    assert audit.list_events()[-1].reason_code == reason_code


def test_bfr_iam_006_service_account_is_denied_by_user_dashboard_policy() -> None:
    reader = CountingReader()
    service, context, audit = _secure_service(
        reader,
        source_ids={"source-a"},
        actor_type=ActorType.SERVICE,
    )

    with pytest.raises(DashboardAuthorizationError):
        service.get_score_tree("execution-dashboard", context)

    assert reader.calls == 0
    assert audit.list_events()[-1].reason_code == "ACTOR_TYPE_NOT_ALLOWED"


def test_rule_009_privileged_flag_does_not_grant_enterprise_visibility() -> None:
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.ENTERPRISE, None, "88.00"))
    service, context, _ = _secure_service(
        repository,
        source_ids=set(),
        privileged=True,
        can_view_enterprise=False,
    )

    tree = service.get_score_tree("execution-dashboard", context)

    assert tree.enterprise is None
    assert tree.has_data is False


def test_bfr_aud_002_authorization_audit_is_redacted_and_context_is_immutable() -> None:
    service, context, audit = _secure_service(
        CountingReader(),
        source_ids={"source-sensitive-name"},
    )

    service.get_score_tree("execution-dashboard", context)

    event = audit.list_events()[-1]
    assert event.new_value_summary["permitted_source_count"] == 1
    assert "source-sensitive-name" not in repr(event)
    assert "synthetic-session" not in repr(event)
    assert "new_values.roles" in event.redacted_fields
    assert "new_values.permitted_source_ids" in event.redacted_fields
    with pytest.raises(FrozenInstanceError):
        context.can_view_enterprise = True  # type: ignore[misc]


def test_bfr_iam_004_authorization_audit_failure_is_fail_closed() -> None:
    reader = CountingReader()
    service, context, _ = _secure_service(
        reader,
        source_ids={"source-a"},
        audit_sink=FailingAuditSink(),
    )

    with pytest.raises(DashboardAuthorizationError) as error:
        service.get_score_tree("execution-dashboard", context)

    assert error.value.correlation_id == "correlation-dashboard"
    assert reader.calls == 0


def test_fr_054_empty_dashboard_does_not_create_zero_score() -> None:
    service, context, _ = _secure_service(
        SQLiteScoreRepository(),
        source_ids={"source-a"},
        can_view_enterprise=True,
    )

    tree = service.get_score_tree("execution-without-scores", context)

    assert tree.enterprise is None
    assert tree.sources == ()
    assert tree.has_data is False


def test_fr_057_direct_drill_down_rejects_unauthorized_source() -> None:
    reader = CountingReader()
    service, context, _ = _secure_service(reader, source_ids={"source-a"})

    with pytest.raises(DashboardAuthorizationError) as error:
        service.get_source_detail(
            "execution-dashboard",
            "source-outside-scope",
            context,
        )

    assert error.value.correlation_id == "correlation-dashboard"
    assert reader.calls == 0


def test_fr_057_direct_drill_down_returns_authorized_source() -> None:
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "80.00"))
    service, context, _ = _secure_service(repository, source_ids={"source-a"})

    source = service.get_source_detail("execution-dashboard", "source-a", context)

    assert source.scope_id == "source-a"
    assert source.score_value == Decimal("80.00")


def test_uc_010_storage_failure_is_a_technical_error_with_correlation_id() -> None:
    service, context, _ = _secure_service(FailingReader(), source_ids={"source-a"})

    with pytest.raises(DashboardQueryError) as error:
        service.get_score_tree("execution-dashboard", context)

    assert error.value.correlation_id == "correlation-dashboard"
    assert "database unavailable" not in str(error.value)


def test_fr_054_request_validation_precedes_repository_query() -> None:
    reader = CountingReader()
    service, context, _ = _secure_service(reader, source_ids=set())

    with pytest.raises(DashboardValidationError, match="execution_id"):
        service.get_score_tree(" ", context)

    assert reader.calls == 0


def test_nfr_perf_002_secure_query_p95_is_under_one_second_for_500_sources() -> None:
    """Local guard: 500 source scores, in-memory SQLite, no sampling."""
    repository = SQLiteScoreRepository()
    source_ids = {f"source-{index:03d}" for index in range(500)}
    for source_id in source_ids:
        repository.add_or_get(_score(ScoreScopeType.SOURCE, source_id, "90.00"))
    service, context, _ = _secure_service(repository, source_ids=source_ids)

    durations = []
    for _ in range(20):
        started_at = perf_counter()
        tree = service.get_score_tree("execution-dashboard", context)
        durations.append(perf_counter() - started_at)

    p95 = sorted(durations)[18]
    assert len(tree.sources) == 500
    assert p95 < 1.0


def test_fr_054_fr_055_uc_010_trend_returns_only_authorized_observations() -> None:
    repository = SQLiteScoreRepository()
    repository.add_or_get(
        _score(
            ScoreScopeType.SOURCE,
            "source-a",
            "80.00",
            execution_id="trend-authorized",
            calculated_at=NOW - timedelta(days=2),
        )
    )
    repository.add_or_get(
        _score(
            ScoreScopeType.SOURCE,
            "source-b",
            "99.00",
            execution_id="trend-forbidden",
            calculated_at=NOW - timedelta(days=1),
        )
    )
    repository.add_or_get(
        _score(
            ScoreScopeType.ENTERPRISE,
            None,
            "91.00",
            execution_id="trend-enterprise",
            calculated_at=NOW,
        )
    )
    service, context, _ = _secure_service(repository, source_ids={"source-a"})

    trend = service.get_score_trend(context)

    observations = [item for period in trend.periods for item in period.observations]
    assert len(trend.periods) == 30
    assert [item.scope_id for item in observations] == ["source-a"]
    assert observations[0].score_value == Decimal("80.00")
    assert trend.periods[-1].has_data is False


def test_fr_055_enterprise_trend_requires_explicit_permission() -> None:
    repository = SQLiteScoreRepository()
    repository.add_or_get(
        _score(
            ScoreScopeType.ENTERPRISE,
            None,
            "91.00",
            execution_id="trend-enterprise",
            calculated_at=NOW,
        )
    )
    service, context, _ = _secure_service(repository, source_ids=set(), can_view_enterprise=True)

    trend = service.get_score_trend(context)

    assert trend.periods[-1].observations[0].scope_type is ScoreScopeType.ENTERPRISE
    assert trend.periods[-1].observations[0].score_value == Decimal("91.00")


def test_fr_048_fr_055_provisional_partial_is_excluded_from_official_trend() -> None:
    repository = SQLiteScoreRepository()
    repository.add_or_get(
        _score(
            ScoreScopeType.SOURCE,
            "source-a",
            "80.00",
            execution_id="trend-official-old",
            calculated_at=NOW - timedelta(days=1),
        )
    )
    repository.add_or_get(
        _score(
            ScoreScopeType.SOURCE,
            "source-a",
            None,
            status=ScoreStatus.PARTIAL,
            level=None,
            official=False,
            execution_id="trend-provisional-new",
            calculated_at=NOW,
        )
    )
    service, context, _ = _secure_service(repository, source_ids={"source-a"})

    trend = service.get_score_trend(context)

    observations = [item for period in trend.periods for item in period.observations]
    assert [item.score_value for item in observations] == [Decimal("80.00")]


def test_fr_048_fr_055_official_partial_is_visible_in_official_trend() -> None:
    repository = SQLiteScoreRepository()
    repository.add_or_get(
        _score(
            ScoreScopeType.SOURCE,
            "source-a",
            "85.00",
            status=ScoreStatus.PARTIAL,
            official=True,
            execution_id="trend-official-partial",
            calculated_at=NOW,
        )
    )
    service, context, _ = _secure_service(repository, source_ids={"source-a"})

    trend = service.get_score_trend(context)

    observation = trend.periods[-1].observations[0]
    assert observation.score_status is ScoreStatus.PARTIAL
    assert observation.score_value == Decimal("85.00")


def test_fr_055_missing_and_no_data_periods_are_never_zero_filled() -> None:
    repository = SQLiteScoreRepository()
    repository.add_or_get(
        _score(
            ScoreScopeType.SOURCE,
            "source-a",
            None,
            status=ScoreStatus.NO_DATA,
            level=None,
            execution_id="trend-no-data",
            calculated_at=NOW - timedelta(days=3),
        )
    )
    service, context, _ = _secure_service(repository, source_ids={"source-a"})

    trend = service.get_score_trend(context)

    empty_periods = [period for period in trend.periods if not period.has_data]
    observations = [item for period in trend.periods for item in period.observations]
    assert len(empty_periods) == 29
    assert empty_periods[0].observations == ()
    assert observations[0].score_status is ScoreStatus.NO_DATA
    assert observations[0].score_value is None


def test_fr_057_trend_authorization_precedes_repository_query() -> None:
    reader = CountingReader()
    service, _, audit = _secure_service(reader, source_ids={"source-a"})

    with pytest.raises(DashboardAuthorizationError):
        service.get_score_trend(None)

    assert reader.trend_calls == 0
    assert audit.list_events()[-1].reason_code == "UNTRUSTED_CONTEXT"


def test_fr_057_trend_defensively_filters_reader_output() -> None:
    reader = CountingReader(
        trend_scores=[
            _score(
                ScoreScopeType.SOURCE,
                "source-a",
                "80.00",
                execution_id="authorized-observation",
                calculated_at=NOW,
            ),
            _score(
                ScoreScopeType.SOURCE,
                "source-forbidden",
                "99.00",
                execution_id="forbidden-observation",
                calculated_at=NOW,
            ),
            _score(
                ScoreScopeType.ENTERPRISE,
                None,
                "95.00",
                execution_id="forbidden-enterprise",
                calculated_at=NOW,
            ),
        ]
    )
    service, context, _ = _secure_service(reader, source_ids={"source-a"})

    trend = service.get_score_trend(context)

    observations = trend.periods[-1].observations
    assert [item.scope_id for item in observations] == ["source-a"]
    assert reader.last_trend_source_ids == frozenset({"source-a"})
    assert reader.last_include_enterprise is False


def test_fr_055_trend_uses_exact_thirty_day_utc_window() -> None:
    repository = SQLiteScoreRepository()
    window_start = datetime(2026, 6, 17, tzinfo=timezone.utc)
    samples = [
        ("before-window", window_start - timedelta(microseconds=1)),
        ("window-start", window_start),
        ("as-of", NOW),
        ("future", NOW + timedelta(microseconds=1)),
    ]
    for execution_id, calculated_at in samples:
        repository.add_or_get(
            _score(
                ScoreScopeType.SOURCE,
                "source-a",
                "80.00",
                execution_id=execution_id,
                calculated_at=calculated_at,
            )
        )
    service, context, _ = _secure_service(repository, source_ids={"source-a"})

    trend = service.get_score_trend(context)

    observations = [item for period in trend.periods for item in period.observations]
    assert [item.calculated_at for item in observations] == [window_start, NOW]
    assert trend.periods[0].period_start == window_start
    assert trend.as_of == NOW


def test_fr_055_trend_compares_non_utc_offset_as_the_same_instant() -> None:
    repository = SQLiteScoreRepository()
    same_instant = NOW.astimezone(timezone(timedelta(hours=3)))
    repository.add_or_get(
        _score(
            ScoreScopeType.SOURCE,
            "source-a",
            "80.00",
            execution_id="trend-offset",
            calculated_at=same_instant,
        )
    )
    service, context, _ = _secure_service(repository, source_ids={"source-a"})

    trend = service.get_score_trend(context)

    assert trend.periods[-1].observations[0].calculated_at == NOW


def test_uc_010_trend_storage_failure_is_technical_and_redacted() -> None:
    service, context, _ = _secure_service(FailingReader(), source_ids={"source-a"})

    with pytest.raises(DashboardQueryError) as error:
        service.get_score_trend(context)

    assert error.value.correlation_id == "correlation-dashboard"
    assert "database unavailable" not in str(error.value)


def test_fr_055_trend_rejects_naive_clock() -> None:
    repository = SQLiteScoreRepository()
    service, context, _ = _secure_service(
        repository,
        source_ids={"source-a"},
        clock=lambda: datetime(2026, 7, 16, 14, 30),
    )

    with pytest.raises(DashboardValidationError, match="timezone-aware"):
        service.get_score_trend(context)


def test_fr_055_trend_rejects_naive_observation_timestamp() -> None:
    reader = CountingReader(
        trend_scores=[
            _score(
                ScoreScopeType.SOURCE,
                "source-a",
                "80.00",
                calculated_at=datetime(2026, 7, 16, 14, 0),
            )
        ]
    )
    service, context, _ = _secure_service(reader, source_ids={"source-a"})

    with pytest.raises(DashboardValidationError, match="calculated_at"):
        service.get_score_trend(context)


def test_nfr_perf_001_thirty_day_trend_p95_is_under_three_seconds() -> None:
    """Local guard: 500 pre-aggregated source observations over 30 UTC days."""
    repository = SQLiteScoreRepository()
    source_ids = {f"source-{index:03d}" for index in range(500)}
    for index, source_id in enumerate(sorted(source_ids)):
        repository.add_or_get(
            _score(
                ScoreScopeType.SOURCE,
                source_id,
                "90.00",
                execution_id=f"trend-performance-{index}",
                calculated_at=NOW - timedelta(days=index % 30),
            )
        )
    service, context, _ = _secure_service(repository, source_ids=source_ids)

    durations = []
    for _ in range(20):
        started_at = perf_counter()
        trend = service.get_score_trend(context)
        durations.append(perf_counter() - started_at)

    assert sum(len(period.observations) for period in trend.periods) == 500
    assert sorted(durations)[18] < 3.0


def test_legacy_scope_adapter_is_internal_deprecated_and_still_operational() -> None:
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "80.00"))
    adapter = LegacyDashboardQueryAdapter(repository)

    tree = adapter.get_score_tree(
        "execution-dashboard",
        DashboardAccessScope(allowed_source_ids=frozenset({"source-a"})),
        correlation_id="correlation-legacy",
    )

    assert adapter.__deprecated__ is True
    assert tree.sources[0].scope_id == "source-a"


class FailingAuditSink:
    def append(self, event: AuditEventInput) -> None:
        raise OSError("audit storage unavailable")


class CountingReader:
    def __init__(self, trend_scores: list[QualityScore] | None = None) -> None:
        self.calls = 0
        self.trend_calls = 0
        self.trend_scores = trend_scores or []
        self.last_trend_source_ids: frozenset[str] | None = None
        self.last_include_enterprise: bool | None = None

    def list_for_execution(self, execution_id: str) -> list[QualityScore]:
        self.calls += 1
        return []

    def list_for_dashboard_trend(
        self,
        start_at: datetime,
        end_at: datetime,
        allowed_source_ids: frozenset[str],
        include_enterprise: bool,
    ) -> list[QualityScore]:
        self.trend_calls += 1
        self.last_trend_source_ids = allowed_source_ids
        self.last_include_enterprise = include_enterprise
        return self.trend_scores


class FailingReader:
    def list_for_execution(self, execution_id: str) -> list[QualityScore]:
        raise sqlite3.OperationalError("database unavailable")

    def list_for_dashboard_trend(
        self,
        start_at: datetime,
        end_at: datetime,
        allowed_source_ids: frozenset[str],
        include_enterprise: bool,
    ) -> list[QualityScore]:
        raise sqlite3.OperationalError("database unavailable")


@overload
def _secure_service(
    reader: SQLiteScoreRepository | CountingReader | FailingReader,
    *,
    source_ids: set[str],
    actor_type: ActorType = ActorType.USER,
    can_view_enterprise: bool = False,
    privileged: bool = False,
    expires_at: datetime = NOW + timedelta(hours=1),
    context_policy_version: str = POLICY_VERSION,
    audit_sink: None = None,
    clock: Callable[[], datetime] = lambda: NOW,
) -> tuple[DashboardQueryService, ActorContext, SQLiteAuditRepository]: ...


@overload
def _secure_service(
    reader: SQLiteScoreRepository | CountingReader | FailingReader,
    *,
    source_ids: set[str],
    actor_type: ActorType = ActorType.USER,
    can_view_enterprise: bool = False,
    privileged: bool = False,
    expires_at: datetime = NOW + timedelta(hours=1),
    context_policy_version: str = POLICY_VERSION,
    audit_sink: FailingAuditSink,
    clock: Callable[[], datetime] = lambda: NOW,
) -> tuple[DashboardQueryService, ActorContext, FailingAuditSink]: ...


def _secure_service(
    reader: SQLiteScoreRepository | CountingReader | FailingReader,
    *,
    source_ids: set[str],
    actor_type: ActorType = ActorType.USER,
    can_view_enterprise: bool = False,
    privileged: bool = False,
    expires_at: datetime = NOW + timedelta(hours=1),
    context_policy_version: str = POLICY_VERSION,
    audit_sink: FailingAuditSink | None = None,
    clock: Callable[[], datetime] = lambda: NOW,
) -> tuple[
    DashboardQueryService,
    ActorContext,
    SQLiteAuditRepository | FailingAuditSink,
]:
    if audit_sink is None:
        audit_store = SQLiteAuditRepository()
        sink: AuditService | FailingAuditSink = AuditService(
            audit_store,
            AuditRedactor(
                AuditRedactionPolicy(
                    version="AUTHORIZATION_REDACTION_V1",
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
                version="AUTHORIZATION_AUDIT_FAILURE_V1",
                default_mode=AuditFailureMode.FAIL_CLOSED,
            ),
        )
        audit_result: SQLiteAuditRepository | FailingAuditSink = audit_store
    else:
        sink = audit_sink
        audit_result = audit_sink
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        sink,
        clock=lambda: NOW,
    )
    context = ActorContextIssuer().issue(
        actor_id="synthetic-user",
        actor_type=actor_type,
        authentication_source="synthetic-adapter",
        session_id="synthetic-session",
        roles=frozenset({"DATA_VIEWER"}),
        permitted_source_ids=frozenset(source_ids),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=can_view_enterprise,
        privileged=privileged,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=expires_at,
        policy_version=context_policy_version,
        correlation_id="correlation-dashboard",
    )
    return DashboardQueryService(reader, authorization, clock=clock), context, audit_result


def _score(
    scope_type: ScoreScopeType,
    scope_id: str | None,
    score_value: str | None,
    *,
    status: ScoreStatus = ScoreStatus.CALCULATED,
    level: ScoreLevel | None = ScoreLevel.ACCEPTABLE,
    execution_id: str = "execution-dashboard",
    calculated_at: datetime = datetime(2026, 7, 16, 14, 0, tzinfo=timezone.utc),
    official: bool | None = None,
) -> QualityScore:
    details: dict[str, object] = {"formula_version": "TEST_ONLY"}
    if official is not None:
        details["included_in_official_aggregation"] = official
    return QualityScore(
        execution_id=execution_id,
        rule_version_id=None,
        scope_type=scope_type,
        scope_id=scope_id,
        score_value=Decimal(score_value) if score_value is not None else None,
        score_status=status,
        level=level,
        calculation_details=details,
        calculated_at=calculated_at,
    )
