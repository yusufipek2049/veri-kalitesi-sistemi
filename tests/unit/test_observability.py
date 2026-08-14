from __future__ import annotations

from io import StringIO
import json
import logging

from fastapi.testclient import TestClient

from veri_kalitesi.api import create_dashboard_api
from veri_kalitesi.api.service_groups import ApiOptions
from veri_kalitesi.operational_logging import JsonFormatter


def test_liveness_stays_healthy_when_database_is_unavailable() -> None:
    def unavailable_database() -> None:
        raise ConnectionError("postgresql://user:password@db/internal_schema")

    client = TestClient(
        create_dashboard_api(options=ApiOptions(readiness_check=unavailable_database))
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_is_not_ready_without_leaking_internal_state() -> None:
    def unavailable_database() -> None:
        raise RuntimeError(
            "postgresql://dq_app:super-secret@postgres/data_quality schema=dq traceback"
        )

    client = TestClient(
        create_dashboard_api(options=ApiOptions(readiness_check=unavailable_database))
    )

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    for internal_value in (
        "dq_app",
        "super-secret",
        "postgres",
        "data_quality",
        "schema",
        "traceback",
        "version",
    ):
        assert internal_value not in response.text.lower()


def test_readiness_reports_ready_with_minimal_contract() -> None:
    client = TestClient(create_dashboard_api(options=ApiOptions(readiness_check=lambda: None)))

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_request_logs_are_json_and_share_response_correlation_id() -> None:
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    api_logger = logging.getLogger("veri_kalitesi.api.app")
    previous_level = api_logger.level
    api_logger.addHandler(handler)
    api_logger.setLevel(logging.INFO)
    try:
        response = TestClient(
            create_dashboard_api(options=ApiOptions(readiness_check=lambda: None))
        ).get("/health")
    finally:
        api_logger.removeHandler(handler)
        api_logger.setLevel(previous_level)

    documents = [json.loads(line) for line in stream.getvalue().splitlines()]
    request_documents = [
        item for item in documents if item.get("event", "").startswith("request_")
    ]
    assert [item["event"] for item in request_documents] == [
        "request_started",
        "request_completed",
    ]
    assert {item["correlation_id"] for item in request_documents} == {
        response.headers["X-Correlation-ID"]
    }


def test_json_logging_redacts_credentials_secrets_and_personal_data() -> None:
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("tests.observability.redaction")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        logger.info(
            "password=plain-password postgresql://user:uri-password@db/data_quality",
            extra={
                "event": "redaction_test",
                "credentials": {"username": "customer", "password": "nested-password"},
                "secret_ref": "resolved-secret-value",
                "customer_data_sample": {"email": "person@example.test"},
            },
        )
    finally:
        logger.removeHandler(handler)

    document = json.loads(stream.getvalue())
    serialized = json.dumps(document)
    for sensitive_value in (
        "plain-password",
        "uri-password",
        "nested-password",
        "resolved-secret-value",
        "person@example.test",
        '"customer"',
    ):
        assert sensitive_value not in serialized
    assert "[REDACTED]" in serialized
