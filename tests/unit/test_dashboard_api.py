from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from veri_kalitesi.api.dashboard_router import register_dashboard_routes
from veri_kalitesi.dashboard import DashboardFilterParams


class _Resolver:
    def resolve(self, request: Request) -> None:
        return None


class _DashboardService:
    def __init__(self) -> None:
        self.filters: DashboardFilterParams | None = None
        self.trend_policy = SimpleNamespace(below_threshold_value=Decimal("64.5"))

    def get_overview(
        self,
        actor_context: object,
        filters: DashboardFilterParams | None = None,
    ) -> Any:
        self.filters = filters
        assert filters is not None
        return SimpleNamespace(
            trend=SimpleNamespace(
                as_of=datetime(2026, 8, 11, 12, tzinfo=timezone.utc),
                periods=(),
                has_data=False,
            ),
            operational_indicators=SimpleNamespace(
                measurement_qualification=SimpleNamespace(
                    status=SimpleNamespace(value="NO_DATA"),
                    evaluated_scope_count=0,
                    reason_codes=(),
                ),
                critical_controls=SimpleNamespace(
                    status=SimpleNamespace(value="NOT_AVAILABLE"),
                    reason_code="NOT_AVAILABLE",
                ),
                technical_errors=SimpleNamespace(
                    observation_count=0,
                    execution_count=0,
                    affected_source_count=0,
                    last_occurred_at=None,
                ),
            ),
            role_view="EXECUTIVE",
            applied_filters=SimpleNamespace(
                window_start=filters.start_date,
                window_end=filters.end_date,
                scope_type=filters.scope_type.value if filters.scope_type else None,
                scope_id=filters.scope_id,
                score_status=None,
                level=None,
            ),
        )


def test_overview_serializes_threshold_and_forwards_filter_query_params() -> None:
    app = FastAPI()
    service = _DashboardService()

    @app.middleware("http")
    async def correlation_id(request: Request, call_next: Any) -> Any:
        request.state.correlation_id = "dashboard-api-test"
        return await call_next(request)

    register_dashboard_routes(
        app,
        dashboard_query_service=service,  # type: ignore[arg-type]
        resolver=_Resolver(),
        data_origin="test",
    )

    response = TestClient(app).get(
        "/api/v1/dashboard/overview",
        params={
            "scope_type": "SOURCE",
            "scope_id": "source-a",
            "start_date": "2026-08-01",
            "end_date": "2026-08-11",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trend"]["threshold_value"] == 64.5
    assert payload["applied_filters"]["scope_id"] == "source-a"
    assert service.filters is not None
    assert service.filters.scope_id == "source-a"
    assert service.filters.scope_type is not None
    assert service.filters.scope_type.value == "SOURCE"
