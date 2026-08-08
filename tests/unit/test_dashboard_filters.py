"""BE-01: FR-057 dashboard filtre birim testleri.

Her filtre kombinasyonu, yetki dışı kapsam, geçersiz parametre ve
parametresiz geriye dönük davranış için AC-01…AC-10 doğrulaması.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from veri_kalitesi.audit.models import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactionPolicy,
)
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.audit.service import AuditService
from veri_kalitesi.dashboard import (
    DashboardAuthorizationError,
    DashboardQueryService,
    DashboardValidationError,
)
from veri_kalitesi.dashboard.models import (
    AppliedDashboardFilters,
    DashboardFilterLevel,
    DashboardFilterParams,
    DashboardFilterScoreStatus,
    DashboardFilterScopeType,
)
from veri_kalitesi.identity import (
    ActorContext,
    ActorContextIssuer,
    ActorType,
    DashboardAuthorizationPolicy,
    PolicyAuthorizationService,
)
from veri_kalitesi.scoring.models import (
    QualityScore,
    ScoreLevel,
    ScoreScopeType,
    ScoreStatus,
)
from veri_kalitesi.scoring.repository import SQLiteScoreRepository

NOW = datetime(2026, 7, 16, 14, 30, tzinfo=timezone.utc)
POLICY_VERSION = "BE01_FILTER_POLICY_V1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _score(
    scope_type: ScoreScopeType,
    scope_id: str | None,
    score_value: str | None,
    *,
    status: ScoreStatus = ScoreStatus.CALCULATED,
    level: ScoreLevel | None = ScoreLevel.ACCEPTABLE,
    execution_id: str = "exec-filter",
    calculated_at: datetime = NOW - timedelta(days=1),
) -> QualityScore:
    return QualityScore(
        execution_id=execution_id,
        rule_version_id=None,
        scope_type=scope_type,
        scope_id=scope_id,
        score_value=Decimal(score_value) if score_value is not None else None,
        score_status=status,
        level=level,
        calculation_details={"included_in_official_aggregation": score_value is not None},
        calculated_at=calculated_at,
    )


def _service(
    repository: SQLiteScoreRepository,
    *,
    source_ids: set[str] | None = None,
    can_view_enterprise: bool = False,
    clock: datetime = NOW,
) -> tuple[DashboardQueryService, ActorContext]:
    audit_store = SQLiteAuditRepository()
    audit_service = AuditService(
        audit_store,
        AuditRedactor(
            AuditRedactionPolicy(
                version="FILTER_REDACTION_V1",
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
            version="FILTER_AUDIT_FAILURE_V1",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )
    context = ActorContextIssuer().issue(
        actor_id="filter-test-user",
        actor_type=ActorType.USER,
        authentication_source="synthetic-adapter",
        session_id="filter-session",
        roles=frozenset({"DATA_VIEWER"}),
        permitted_source_ids=frozenset(source_ids or {"source-a", "source-b"}),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=can_view_enterprise,
        privileged=False,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=POLICY_VERSION,
        correlation_id="correlation-filter-test",
    )
    service = DashboardQueryService(
        repository,
        authorization,
        clock=lambda: clock,
    )
    return service, context


# ---------------------------------------------------------------------------
# AC-05: Parametresiz geriye dönük davranış
# ---------------------------------------------------------------------------


def test_ac_05_no_filters_preserves_default_30_day_window() -> None:
    """Filtre yoksa varsayılan 30 gün penceresi ve aktör kapsamı korunur."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "80.00"))
    service, context = _service(repository, source_ids={"source-a"})

    overview = service.get_overview(context)

    assert overview.applied_filters is not None
    assert len(overview.trend.periods) == 30
    assert overview.applied_filters.scope_type is None
    assert overview.applied_filters.scope_id is None
    assert overview.applied_filters.score_status is None
    assert overview.applied_filters.level is None


# ---------------------------------------------------------------------------
# AC-01: Tarih aralığı filtresi
# ---------------------------------------------------------------------------


def test_ac_01_date_range_filter_restricts_periods() -> None:
    """Belirtilen tarih aralığı period sayısını değiştirir."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "80.00"))
    service, context = _service(repository, source_ids={"source-a"})

    start = NOW - timedelta(days=4)
    end = NOW
    filters = DashboardFilterParams(start_date=start, end_date=end)

    overview = service.get_overview(context, filters=filters)

    day_count = max(
        (
            end.replace(hour=0, minute=0, second=0, microsecond=0)
            - (start.replace(hour=0, minute=0, second=0, microsecond=0))
        ).days
        + 1,
        1,
    )
    assert len(overview.trend.periods) == day_count
    assert overview.applied_filters is not None
    assert overview.applied_filters.window_start == start.astimezone(timezone.utc)


def test_ac_01_only_start_date_uses_default_end() -> None:
    """Yalnız başlangıç verilirse bitiş mevcut zamandır."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "80.00"))
    service, context = _service(repository, source_ids={"source-a"})

    start = NOW - timedelta(days=9)
    filters = DashboardFilterParams(start_date=start)

    overview = service.get_overview(context, filters=filters)

    assert overview.applied_filters is not None
    assert overview.applied_filters.window_end == NOW.astimezone(timezone.utc)


def test_ac_01_only_end_date_uses_default_start() -> None:
    """Yalnız bitiş verilirse başlangıç varsayılan 30 gün öncedir."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "80.00"))
    service, context = _service(repository, source_ids={"source-a"})

    end = NOW - timedelta(days=5)
    filters = DashboardFilterParams(end_date=end)

    overview = service.get_overview(context, filters=filters)

    assert overview.applied_filters is not None
    default_start = (NOW - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
    assert overview.applied_filters.window_start == default_start


# ---------------------------------------------------------------------------
# AC-04: Geçersiz tarih aralığı (ters aralık) fail-closed
# ---------------------------------------------------------------------------


def test_ac_04_reversed_date_range_raises_validation_error() -> None:
    """start >= end durumunda DashboardValidationError fırlatılır."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "80.00"))
    service, context = _service(repository, source_ids={"source-a"})

    filters = DashboardFilterParams(
        start_date=NOW,
        end_date=NOW - timedelta(days=5),
    )

    with pytest.raises(DashboardValidationError, match="date range is invalid"):
        service.get_overview(context, filters=filters)


def test_ac_04_equal_start_end_raises_validation_error() -> None:
    """start == end durumunda da hata fırlatılır."""
    repository = SQLiteScoreRepository()
    service, context = _service(repository, source_ids={"source-a"})

    same_time = NOW - timedelta(days=2)
    filters = DashboardFilterParams(start_date=same_time, end_date=same_time)

    with pytest.raises(DashboardValidationError, match="date range is invalid"):
        service.get_overview(context, filters=filters)


# ---------------------------------------------------------------------------
# AC-01: Kapsam filtresi (scope_type / scope_id)
# ---------------------------------------------------------------------------


def test_ac_01_scope_source_filter_restricts_to_single_source() -> None:
    """scope_type=SOURCE ve scope_id ile tek kaynağa daraltılır."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "80.00"))
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-b", "90.00"))
    service, context = _service(repository, source_ids={"source-a", "source-b"})

    filters = DashboardFilterParams(
        scope_type=DashboardFilterScopeType.SOURCE,
        scope_id="source-a",
    )

    overview = service.get_overview(context, filters=filters)

    all_scope_ids = [
        obs.scope_id
        for period in overview.trend.periods
        for obs in period.observations
        if obs.scope_id is not None
    ]
    assert set(all_scope_ids) == {"source-a"}
    assert overview.applied_filters is not None
    assert overview.applied_filters.scope_type == "SOURCE"
    assert overview.applied_filters.scope_id == "source-a"


# ---------------------------------------------------------------------------
# AC-03: Yetki dışı kapsam sızdırmaz
# ---------------------------------------------------------------------------


def test_ac_03_unauthorized_scope_id_raises_authorization_error() -> None:
    """Aktörün izin vermediği scope_id için veri sızdırmadan hata döner."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "80.00"))
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-forbidden", "99.00"))
    service, context = _service(repository, source_ids={"source-a"})

    filters = DashboardFilterParams(
        scope_type=DashboardFilterScopeType.SOURCE,
        scope_id="source-forbidden",
    )

    with pytest.raises(DashboardAuthorizationError):
        service.get_overview(context, filters=filters)


def test_ac_03_enterprise_scope_without_permission_raises_error() -> None:
    """Enterprise scope izni olmayan aktör için yetki hatası."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.ENTERPRISE, None, "88.00"))
    service, context = _service(repository, source_ids={"source-a"}, can_view_enterprise=False)

    filters = DashboardFilterParams(
        scope_type=DashboardFilterScopeType.ENTERPRISE,
        scope_id="enterprise",
    )

    with pytest.raises(DashboardAuthorizationError):
        service.get_overview(context, filters=filters)


def test_ac_03_enterprise_scope_with_permission_succeeds() -> None:
    """Enterprise izni olan aktör enterprise scope filtreleyebilir."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.ENTERPRISE, None, "88.00"))
    service, context = _service(repository, source_ids={"source-a"}, can_view_enterprise=True)

    filters = DashboardFilterParams(
        scope_type=DashboardFilterScopeType.ENTERPRISE,
        scope_id="enterprise",
    )

    overview = service.get_overview(context, filters=filters)

    assert overview.applied_filters is not None
    assert overview.applied_filters.scope_type == "ENTERPRISE"


# ---------------------------------------------------------------------------
# AC-01: Skor durumu filtresi
# ---------------------------------------------------------------------------


def test_ac_01_score_status_filter_calculated_only() -> None:
    """CALCULATED filtresi yalnız hesaplanmış skorları döndürür."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(
        _score(ScoreScopeType.SOURCE, "source-a", "80.00", status=ScoreStatus.CALCULATED)
    )
    repository.add_or_get(
        _score(
            ScoreScopeType.SOURCE,
            "source-b",
            None,
            status=ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR,
            level=None,
            calculated_at=NOW - timedelta(hours=1),
        )
    )
    service, context = _service(repository, source_ids={"source-a", "source-b"})

    filters = DashboardFilterParams(score_status=DashboardFilterScoreStatus.CALCULATED)

    overview = service.get_overview(context, filters=filters)

    all_statuses = [
        obs.score_status for period in overview.trend.periods for obs in period.observations
    ]
    assert all(s == "CALCULATED" for s in all_statuses)
    assert overview.applied_filters is not None
    assert overview.applied_filters.score_status == "CALCULATED"


def test_ac_01_score_status_filter_technical_error() -> None:
    """NOT_CALCULATED_TECHNICAL_ERROR filtresi yalnız teknik hataları döndürür."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(
        _score(ScoreScopeType.SOURCE, "source-a", "80.00", status=ScoreStatus.CALCULATED)
    )
    repository.add_or_get(
        _score(
            ScoreScopeType.SOURCE,
            "source-b",
            None,
            status=ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR,
            level=None,
            calculated_at=NOW - timedelta(hours=1),
        )
    )
    service, context = _service(repository, source_ids={"source-a", "source-b"})

    filters = DashboardFilterParams(
        score_status=DashboardFilterScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR,
    )

    overview = service.get_overview(context, filters=filters)

    all_statuses = [
        obs.score_status for period in overview.trend.periods for obs in period.observations
    ]
    assert all(s == "NOT_CALCULATED_TECHNICAL_ERROR" for s in all_statuses)


# ---------------------------------------------------------------------------
# AC-01: Kalite seviyesi filtresi
# ---------------------------------------------------------------------------


def test_ac_01_level_filter_good_only() -> None:
    """GOOD seviyesi filtresi yalnız GOOD skorları döndürür."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "95.00", level=ScoreLevel.GOOD))
    repository.add_or_get(
        _score(ScoreScopeType.SOURCE, "source-b", "60.00", level=ScoreLevel.RISKY)
    )
    service, context = _service(repository, source_ids={"source-a", "source-b"})

    filters = DashboardFilterParams(level=DashboardFilterLevel.GOOD)

    overview = service.get_overview(context, filters=filters)

    all_levels = [obs.level for period in overview.trend.periods for obs in period.observations]
    assert all(lev == "GOOD" for lev in all_levels)
    assert overview.applied_filters is not None
    assert overview.applied_filters.level == "GOOD"


def test_ac_01_level_filter_risky_only() -> None:
    """RISKY seviyesi filtresi yalnız RISKY skorları döndürür."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "95.00", level=ScoreLevel.GOOD))
    repository.add_or_get(
        _score(ScoreScopeType.SOURCE, "source-b", "55.00", level=ScoreLevel.RISKY)
    )
    service, context = _service(repository, source_ids={"source-a", "source-b"})

    filters = DashboardFilterParams(level=DashboardFilterLevel.RISKY)

    overview = service.get_overview(context, filters=filters)

    all_levels = [obs.level for period in overview.trend.periods for obs in period.observations]
    assert all(lev == "RISKY" for lev in all_levels)


# ---------------------------------------------------------------------------
# AC-06: Filtreleme Unknown/provisional ayrımını bozmaz
# ---------------------------------------------------------------------------


def test_ac_06_score_status_filter_preserves_unknown_distinction() -> None:
    """NOT_CALCULATED_TECHNICAL_ERROR filtresi teknik hata ayrımını korur."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(
        _score(
            ScoreScopeType.SOURCE,
            "source-a",
            None,
            status=ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR,
            level=None,
            calculated_at=NOW - timedelta(hours=1),
        )
    )
    service, context = _service(repository, source_ids={"source-a"})

    filters = DashboardFilterParams(
        score_status=DashboardFilterScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR,
    )

    overview = service.get_overview(context, filters=filters)

    observations = [obs for period in overview.trend.periods for obs in period.observations]
    assert len(observations) == 1
    assert observations[0].score_status is ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR
    assert observations[0].score_value is None
    assert observations[0].level is None


# ---------------------------------------------------------------------------
# AC-07: Yanıt sözleşmesi uygulanmış filtreleri taşır
# ---------------------------------------------------------------------------


def test_ac_07_applied_filters_echo_all_parameters() -> None:
    """Yanıt tüm filtre parametrelerini yansıtır."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "80.00"))
    service, context = _service(repository, source_ids={"source-a"})

    start = NOW - timedelta(days=7)
    end = NOW
    filters = DashboardFilterParams(
        start_date=start,
        end_date=end,
        scope_type=DashboardFilterScopeType.SOURCE,
        scope_id="source-a",
        score_status=DashboardFilterScoreStatus.CALCULATED,
        level=DashboardFilterLevel.ACCEPTABLE,
    )

    overview = service.get_overview(context, filters=filters)

    af = overview.applied_filters
    assert af is not None
    assert isinstance(af, AppliedDashboardFilters)
    assert af.scope_type == "SOURCE"
    assert af.scope_id == "source-a"
    assert af.score_status == "CALCULATED"
    assert af.level == "ACCEPTABLE"


def test_ac_07_no_filters_still_echoes_defaults() -> None:
    """Filtre yok bile olsa applied_filters varsayılan pencereyi taşır."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "80.00"))
    service, context = _service(repository, source_ids={"source-a"})

    overview = service.get_overview(context)

    af = overview.applied_filters
    assert af is not None
    assert af.scope_type is None
    assert af.scope_id is None
    assert af.score_status is None
    assert af.level is None


# ---------------------------------------------------------------------------
# AC-01: Kombine filtreler
# ---------------------------------------------------------------------------


def test_ac_01_combined_scope_and_level_filters() -> None:
    """Kapsam ve seviye filtreleri birlikte çalışır."""
    repository = SQLiteScoreRepository()
    repository.add_or_get(_score(ScoreScopeType.SOURCE, "source-a", "95.00", level=ScoreLevel.GOOD))
    repository.add_or_get(
        _score(ScoreScopeType.SOURCE, "source-b", "55.00", level=ScoreLevel.RISKY)
    )
    service, context = _service(repository, source_ids={"source-a", "source-b"})

    filters = DashboardFilterParams(
        scope_type=DashboardFilterScopeType.SOURCE,
        scope_id="source-a",
        level=DashboardFilterLevel.GOOD,
    )

    overview = service.get_overview(context, filters=filters)

    observations = [obs for period in overview.trend.periods for obs in period.observations]
    assert len(observations) == 1
    assert observations[0].scope_id == "source-a"
    assert observations[0].level == ScoreLevel.GOOD


def test_ac_01_combined_date_and_status_filters() -> None:
    """Tarih ve skor durumu filtreleri birlikte çalışır."""
    repository = SQLiteScoreRepository()
    # source-a: CALCULATED, 2 gün önce
    repository.add_or_get(
        _score(ScoreScopeType.SOURCE, "source-a", "80.00", calculated_at=NOW - timedelta(days=2))
    )
    # source-b: TECHNICAL_ERROR, 3 gün önce
    repository.add_or_get(
        _score(
            ScoreScopeType.SOURCE,
            "source-b",
            None,
            status=ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR,
            level=None,
            calculated_at=NOW - timedelta(days=3),
        )
    )
    service, context = _service(repository, source_ids={"source-a", "source-b"})

    # Son 5 günü filtrele ve yalnız CALCULATED
    filters = DashboardFilterParams(
        start_date=NOW - timedelta(days=5),
        end_date=NOW,
        score_status=DashboardFilterScoreStatus.CALCULATED,
    )

    overview = service.get_overview(context, filters=filters)

    all_statuses = [
        obs.score_status for period in overview.trend.periods for obs in period.observations
    ]
    assert all(s == "CALCULATED" for s in all_statuses)
    # TECHNICAL_ERROR olan source-b filtrelenmiş olmalı
    all_scope_ids = [
        obs.scope_id for period in overview.trend.periods for obs in period.observations
    ]
    assert "source-b" not in all_scope_ids
