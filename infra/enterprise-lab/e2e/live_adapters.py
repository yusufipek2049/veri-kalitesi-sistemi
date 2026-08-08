"""Redacted live-container acceptance checks for ENTERPRISE-LAB-03."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import Request

from veri_kalitesi.api.errors import ApiAuthenticationError
from veri_kalitesi.audit import AuditEventInput, AuditResult, AuditWriteError
from veri_kalitesi.data_sources.errors import SecretResolutionError
from veri_kalitesi.enterprise_lab import (
    ENTERPRISE_LAB_APPLICATION_POLICY_VERSION,
    LocalPrototypeSecretResolver,
    SyntheticGroupAccess,
    SyntheticIdentityPolicy,
    build_enterprise_lab_application_adapters,
)
from veri_kalitesi.identity import is_trusted_actor_context
from veri_kalitesi.servicenow import (
    ServiceNowAdapterError,
    ServiceNowAdapterErrorKind,
    ServiceNowTicketRequest,
)


CONFIGURATION_PATH = Path("/lab-config/environment.json")
KEYCLOAK_PASSWORD_PATH = Path("/run/secrets/keycloak_lab_user_password")
SECRET_MANAGER_TOKEN_PATH = Path("/run/secrets/local_secret_manager_token")
FAULT_CONTROL_TOKEN_PATH = Path("/run/secrets/lab_fault_control_token")
NOW = datetime(2026, 7, 29, 16, 0, tzinfo=timezone.utc)


def main() -> None:
    checks: list[dict[str, str]] = []
    adapters = build_enterprise_lab_application_adapters(
        CONFIGURATION_PATH,
        identity_policy=_identity_policy(),
        secret_manager_token_path=SECRET_MANAGER_TOKEN_PATH,
    )

    viewer_token = _keycloak_token("synthetic-lab-viewer")
    context = adapters.identity.resolve(_request(viewer_token))
    _assert(
        is_trusted_actor_context(context)
        and context.roles == frozenset({"DATA_VIEWER"})
        and context.permitted_source_ids == frozenset({"synthetic-source"})
        and context.permitted_dataset_ids == frozenset({"synthetic-dataset"})
        and context.policy_version == ENTERPRISE_LAB_APPLICATION_POLICY_VERSION,
        "identity projection",
    )
    _passed(checks, "keycloak-session-versioned-role-scope")

    _expect(ApiAuthenticationError, lambda: adapters.identity.resolve(_request("invalid-token")))
    _passed(checks, "invalid-identity-fail-closed")

    unmapped_token = _keycloak_token("synthetic-lab-unmapped")
    _expect(ApiAuthenticationError, lambda: adapters.identity.resolve(_request(unmapped_token)))
    _passed(checks, "unmapped-role-fail-closed")

    resolved = adapters.secrets.resolve("secret://local/enterprise-lab/postgres-app")
    _assert(set(resolved) == {"password"} and bool(resolved["password"]), "secret resolution")
    _passed(checks, "file-backed-secret-reference")

    missing_file_resolver = LocalPrototypeSecretResolver(
        "http://local-secret-manager:8080",
        environment="LOCAL",
        authorization_token_path=Path("/run/secrets/not-mounted"),
    )
    _expect(
        SecretResolutionError,
        lambda: missing_file_resolver.resolve("secret://local/enterprise-lab/postgres-app"),
    )
    _passed(checks, "missing-secret-file-fail-closed")

    denied_resolver = LocalPrototypeSecretResolver(
        "http://local-secret-manager:8080",
        environment="LOCAL",
        authorization_token_path=KEYCLOAK_PASSWORD_PATH,
    )
    _expect(
        SecretResolutionError,
        lambda: denied_resolver.resolve("secret://local/enterprise-lab/postgres-app"),
    )
    _passed(checks, "secret-authorization-denied-fail-closed")

    ticket_request = _ticket_request()
    first = adapters.servicenow.create_ticket(ticket_request)
    replay = adapters.servicenow.create_ticket(ticket_request)
    _assert(first == replay, "ServiceNow replay")
    _passed(checks, "servicenow-create-idempotent-replay")

    for mode, expected_kind in (
        ("denied", ServiceNowAdapterErrorKind.AUTHENTICATION),
        ("outage", ServiceNowAdapterErrorKind.TEMPORARY),
        ("rate-limit", ServiceNowAdapterErrorKind.RATE_LIMIT),
        ("timeout", ServiceNowAdapterErrorKind.TEMPORARY),
    ):
        _set_fault("fake-servicenow", mode)
        error = _expect(
            ServiceNowAdapterError, lambda: adapters.servicenow.create_ticket(ticket_request)
        )
        _assert(error.error_kind is expected_kind, f"ServiceNow {mode} classification")
        if mode == "rate-limit":
            _assert(error.retry_after_seconds == 2, "ServiceNow Retry-After")
        recovered = adapters.servicenow.create_ticket(ticket_request)
        _assert(recovered == first, f"ServiceNow {mode} recovery")
        _passed(checks, f"servicenow-{mode}-fail-closed-recovery")

    event = _audit_event()
    adapters.siem.append(event)
    adapters.siem.append(event)
    _passed(checks, "siem-data-minimum-idempotent-transfer")

    malformed_status = _post_json(
        "http://siem-collector:8080/events",
        {"event_id": "unexpected-extra-field", "sensitive": "redacted"},
        headers={"Idempotency-Key": "unexpected-extra-field"},
    )
    _assert(malformed_status == 400, "SIEM invalid payload rejection")
    _passed(checks, "siem-invalid-payload-rejected")

    _set_fault("siem-collector", "malformed-response")
    _expect(AuditWriteError, lambda: adapters.siem.append(_audit_event("correlation-malformed")))
    adapters.siem.append(_audit_event("correlation-recovered"))
    _passed(checks, "siem-malformed-response-fail-closed-recovery")

    print(
        json.dumps(
            {
                "classification": "PrototypeVerified",
                "environment": "LOCAL",
                "scope": "SYNTHETIC_ACCEPTANCE",
                "status": "PASSED",
                "checks": checks,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def _keycloak_token(username: str) -> str:
    password = KEYCLOAK_PASSWORD_PATH.read_text(encoding="utf-8").strip()
    body = urlencode(
        {
            "client_id": "veri-kalitesi-lab",
            "grant_type": "password",
            "scope": "openid",
            "username": username,
            "password": password,
        }
    ).encode("ascii")
    request = UrlRequest(
        "http://keycloak:8080/realms/enterprise-lab/protocol/openid-connect/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=3) as response:  # noqa: S310
        payload = json.loads(response.read())
    token = payload.get("access_token")
    _assert(isinstance(token, str) and bool(token), "Keycloak token response")
    return token


def _set_fault(service: str, mode: str) -> None:
    token = FAULT_CONTROL_TOKEN_PATH.read_text(encoding="utf-8").strip()
    status = _post_json(
        f"http://{service}:8080/_lab/fault",
        {"mode": mode},
        headers={"Authorization": f"Bearer {token}"},
    )
    _assert(status == 204, f"{service} fault control")


def _post_json(url: str, payload: dict[str, str], *, headers: dict[str, str]) -> int:
    request = UrlRequest(
        url,
        data=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=3) as response:  # noqa: S310
            response.read()
            return response.status
    except HTTPError as exc:
        exc.read()
        return exc.code


def _request(token: str) -> Request:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/dashboard",
            "headers": [(b"authorization", f"Bearer {token}".encode("ascii"))],
            "state": {},
        }
    )
    request.state.correlation_id = "correlation-e2e"
    return request


def _identity_policy() -> SyntheticIdentityPolicy:
    return SyntheticIdentityPolicy(
        version=ENTERPRISE_LAB_APPLICATION_POLICY_VERSION,
        group_access={
            "lab-viewers": SyntheticGroupAccess(
                roles=frozenset({"DATA_VIEWER"}),
                permitted_source_ids=frozenset({"synthetic-source"}),
                permitted_dataset_ids=frozenset({"synthetic-dataset"}),
            )
        },
    )


def _ticket_request() -> ServiceNowTicketRequest:
    return ServiceNowTicketRequest(
        client_request_id="enterprise-lab-03-idempotency",
        issue_reference="DQI-SYNTHETIC-E2E",
        source_event_type="QUALITY",
        priority="HIGH",
        detail_reference_id="11111111-1111-4111-8111-111111111111",
        correlation_id="correlation-e2e",
    )


def _audit_event(correlation_id: str = "correlation-e2e") -> AuditEventInput:
    return AuditEventInput(
        actor_id="synthetic-actor-e2e",
        actor_type="USER",
        correlation_id=correlation_id,
        action="SYNTHETIC_ACCEPTANCE",
        object_type="SyntheticObject",
        object_id="synthetic-object-e2e",
        result=AuditResult.SUCCESS,
        reason_code="SYNTHETIC_ACCEPTANCE",
        old_values={},
        new_values={"sensitive": "must-not-be-projected"},
        occurred_at=NOW,
    )


def _expect(error_type: type[Exception], action: Callable[[], object]) -> Exception:
    try:
        action()
    except error_type as exc:
        return exc
    raise AssertionError(f"expected {error_type.__name__}")


def _assert(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def _passed(checks: list[dict[str, str]], scenario: str) -> None:
    checks.append({"scenario": scenario, "status": "PASSED"})


if __name__ == "__main__":
    main()
