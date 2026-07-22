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


class DevelopmentDataSourceReader:
    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]:
        return [
            source for source in DEVELOPMENT_SOURCES if source.data_source_id in allowed_source_ids
        ]


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
    )
