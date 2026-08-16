"""Unit tests for dashboard insights API routes — 503 when services unavailable."""

from fastapi.testclient import TestClient

from veri_kalitesi.api import create_dashboard_api


def test_rule_health_returns_503_when_unavailable() -> None:
    client = TestClient(create_dashboard_api())
    response = client.get("/api/v1/dashboard/rule-health")
    assert response.status_code == 503


def test_metadata_health_returns_503_when_unavailable() -> None:
    client = TestClient(create_dashboard_api())
    response = client.get("/api/v1/dashboard/metadata-health")
    assert response.status_code == 503


def test_issue_performance_returns_503_when_unavailable() -> None:
    client = TestClient(create_dashboard_api())
    response = client.get("/api/v1/dashboard/issue-performance")
    assert response.status_code == 503


def test_scoring_policy_impact_returns_503_when_unavailable() -> None:
    client = TestClient(create_dashboard_api())
    response = client.get("/api/v1/dashboard/scoring-policy-impact")
    assert response.status_code == 503


def test_rule_health_no_store_header() -> None:
    """Even 503 responses carry the correlation header."""
    client = TestClient(create_dashboard_api())
    response = client.get("/api/v1/dashboard/rule-health")
    assert "x-correlation-id" in response.headers
