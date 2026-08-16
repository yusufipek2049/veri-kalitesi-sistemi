from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from veri_kalitesi.api.development import create_synthetic_development_app


def test_audit_events_custom_period_is_applied_across_http_and_repository() -> None:
    app = create_synthetic_development_app()
    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=4)

    response = TestClient(app).get(
        "/api/v1/audit/events",
        params={
            "days": 1,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        },
    )

    assert response.status_code == 200
    correlation_ids = {item["correlation_id"] for item in response.json()["items"]}
    assert "synthetic-audit-4" in correlation_ids
    assert "synthetic-audit-6" not in correlation_ids
