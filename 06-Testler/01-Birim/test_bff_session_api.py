from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from http.cookies import SimpleCookie

import pytest
from fastapi import Response
from fastapi.testclient import TestClient

from veri_kalitesi.api import (
    BffSessionBoundary,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    create_dashboard_api,
)
from veri_kalitesi.audit import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactor,
    AuditService,
    SQLiteAuditRepository,
    build_default_redaction_policy,
)
from veri_kalitesi.dashboard import DashboardQueryService
from veri_kalitesi.identity import (
    ActorContextIssuer,
    ActorType,
    DashboardAuthorizationPolicy,
    PolicyAuthorizationService,
    SessionDeniedError,
    SessionPolicy,
    SessionService,
    SQLiteSessionRepository,
)
from veri_kalitesi.scoring import (
    QualityScore,
    ScoreLevel,
    ScoreScopeType,
    ScoreStatus,
    SQLiteScoreRepository,
)

NOW = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
ORIGIN = "https://quality.example"
POLICY_VERSION = "BFF_SESSION_POLICY_V1"
DASHBOARD_POLICY_VERSION = "BFF_DASHBOARD_POLICY_V1"


def test_fr_005_nfr_sec_009_session_grant_uses_exact_secure_cookie_contract() -> None:
    setup = _setup()

    set_cookie = setup.transport_response.headers["set-cookie"]
    csrf_value = setup.transport_response.headers[CSRF_HEADER_NAME]

    assert set_cookie.startswith(f"{SESSION_COOKIE_NAME}=")
    assert "Secure" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie
    assert "Domain=" not in set_cookie
    assert setup.transport_response.headers["cache-control"] == "no-store"
    assert csrf_value not in set_cookie
    assert repr(setup.grant.credential) not in set_cookie
    assert repr(setup.grant.csrf_token) not in set_cookie

    row = setup.session_repository.connection.execute(
        "SELECT credential_digest, csrf_token_digest FROM identity_sessions"
    ).fetchone()
    assert len(row["credential_digest"]) == 64
    assert len(row["csrf_token_digest"]) == 64
    assert row["credential_digest"] != setup.grant.credential.hex()
    assert row["csrf_token_digest"] != setup.grant.csrf_token.hex()


def test_fr_005_fr_081_bff_cookie_resolves_authorized_dashboard_context() -> None:
    setup = _setup()

    response = setup.client.get(
        "/api/v1/dashboard/summary",
        headers={
            "Cookie": setup.cookie_header,
            "X-Actor-ID": "forged-user",
            "X-Roles": "ADMIN",
            "X-Source-IDs": "source-forbidden",
        },
    )

    assert response.status_code == 200
    observations = [
        observation
        for period in response.json()["periods"]
        for observation in period["observations"]
    ]
    assert [observation["scope_id"] for observation in observations] == ["source-a"]


@pytest.mark.parametrize(
    "cookie_header",
    [None, f"{SESSION_COOKIE_NAME}=not-valid-base64!"],
    ids=("missing", "malformed"),
)
def test_fr_081_missing_or_malformed_bff_cookie_fails_closed(
    cookie_header: str | None,
) -> None:
    setup = _setup()
    headers = {"Cookie": cookie_header} if cookie_header else {}

    response = setup.client.get("/api/v1/dashboard/summary", headers=headers)

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "A trusted user session is required."
    assert "not-valid-base64" not in response.text


def test_fr_005_nfr_sec_007_valid_csrf_logout_revokes_and_clears_session() -> None:
    setup = _setup()

    response = setup.client.post(
        "/api/v1/session/logout",
        headers=setup.state_changing_headers(),
    )

    assert response.status_code == 204
    assert response.headers["cache-control"] == "no-store"
    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f'{SESSION_COOKIE_NAME}=""')
    assert "Max-Age=0" in set_cookie
    assert "Secure" in set_cookie
    assert "HttpOnly" in set_cookie
    row = setup.session_repository.connection.execute(
        "SELECT credential_digest, csrf_token_digest, status FROM identity_sessions"
    ).fetchone()
    assert row["credential_digest"] is None
    assert row["csrf_token_digest"] is None
    assert row["status"] == "REVOKED"

    reused = setup.client.get(
        "/api/v1/dashboard/summary",
        headers={"Cookie": setup.cookie_header},
    )
    assert reused.status_code == 401


@pytest.mark.parametrize(
    "csrf_value",
    [None, "invalid-csrf-value"],
    ids=("missing", "changed"),
)
def test_nfr_sec_007_missing_or_changed_csrf_is_denied_without_logout(
    csrf_value: str | None,
) -> None:
    setup = _setup()
    headers = setup.state_changing_headers()
    if csrf_value is None:
        headers.pop(CSRF_HEADER_NAME)
    else:
        headers[CSRF_HEADER_NAME] = csrf_value

    response = setup.client.post("/api/v1/session/logout", headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "The state-changing request could not be verified."
    assert "invalid-csrf-value" not in response.text
    assert (
        setup.client.get(
            "/api/v1/dashboard/summary",
            headers={"Cookie": setup.cookie_header},
        ).status_code
        == 200
    )


@pytest.mark.parametrize(
    ("header_name", "header_value"),
    [
        ("Origin", "https://untrusted.example"),
        ("Referer", "https://untrusted.example/page"),
        ("Sec-Fetch-Site", "cross-site"),
    ],
    ids=("origin", "referer", "fetch-metadata"),
)
def test_nfr_sec_007_untrusted_request_metadata_is_denied(
    header_name: str,
    header_value: str,
) -> None:
    setup = _setup()
    headers = setup.state_changing_headers()
    headers[header_name] = header_value

    response = setup.client.post("/api/v1/session/logout", headers=headers)

    assert response.status_code == 403
    assert response.json()["title"] == "Request rejected"


def test_nfr_sec_007_get_cannot_perform_logout() -> None:
    setup = _setup()

    response = setup.client.get(
        "/api/v1/session/logout",
        headers={"Cookie": setup.cookie_header},
    )

    assert response.status_code == 405
    assert (
        setup.client.get(
            "/api/v1/dashboard/summary",
            headers={"Cookie": setup.cookie_header},
        ).status_code
        == 200
    )


def test_nfr_sec_007_cors_preflight_allows_only_configured_origin_and_csrf_header() -> None:
    setup = _setup()

    allowed = setup.client.options(
        "/api/v1/session/logout",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": CSRF_HEADER_NAME,
        },
    )
    denied = setup.client.options(
        "/api/v1/session/logout",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": CSRF_HEADER_NAME,
        },
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == ORIGIN
    assert "POST" in allowed.headers["access-control-allow-methods"]
    assert CSRF_HEADER_NAME.lower() in allowed.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-origin" not in denied.headers


def test_fr_005_session_store_failure_returns_safe_503() -> None:
    setup = _setup()
    setup.session_repository.connection.close()

    response = setup.client.get(
        "/api/v1/dashboard/summary",
        headers={"Cookie": setup.cookie_header},
    )

    assert response.status_code == 503
    assert response.json()["title"] == "Session temporarily unavailable"
    assert "database" not in response.text.lower()


def test_fr_005_csrf_validation_audit_contains_no_session_secret() -> None:
    setup = _setup()

    with pytest.raises(SessionDeniedError) as error:
        setup.session_service.validate_csrf(
            setup.grant.credential,
            bytes(reversed(setup.grant.csrf_token)),
            "csrf-audit-denied",
        )

    assert error.value.reason_code == "CSRF_VALIDATION_FAILED"
    event = setup.audit_repository.list_events()[-1]
    serialized = repr(event)
    assert event.reason_code == "CSRF_VALIDATION_FAILED"
    assert repr(setup.grant.credential) not in serialized
    assert repr(setup.grant.csrf_token) not in serialized
    assert setup.cookie_value not in serialized
    assert setup.csrf_value not in serialized


class BffSetup:
    def __init__(self) -> None:
        self.audit_repository = SQLiteAuditRepository()
        audit_service = AuditService(
            self.audit_repository,
            AuditRedactor(build_default_redaction_policy()),
            AuditFailurePolicy(
                version="BFF_AUDIT_FAILURE_POLICY_V1",
                default_mode=AuditFailureMode.FAIL_CLOSED,
            ),
        )
        self.session_repository = SQLiteSessionRepository()
        self.session_service = SessionService(
            self.session_repository,
            SessionPolicy(
                version=POLICY_VERSION,
                idle_timeout=timedelta(minutes=60),
                absolute_timeout=timedelta(hours=10),
            ),
            audit_service,
            clock=lambda: NOW,
        )
        authenticated_context = ActorContextIssuer().issue(
            actor_id="actor-bff-user",
            actor_type=ActorType.USER,
            authentication_source="synthetic-idp-adapter",
            session_id="pre-session-authentication",
            roles=frozenset({"DATA_VIEWER"}),
            permitted_source_ids=frozenset({"source-a"}),
            permitted_dataset_ids=frozenset(),
            can_view_enterprise=False,
            privileged=False,
            issued_at=NOW - timedelta(seconds=1),
            expires_at=NOW + timedelta(minutes=1),
            policy_version=DASHBOARD_POLICY_VERSION,
            correlation_id="session-open",
        )
        self.grant = self.session_service.open_authenticated_session(
            authenticated_context=authenticated_context,
            correlation_id="session-open",
        )
        boundary = BffSessionBoundary(
            self.session_service,
            allowed_origins=(ORIGIN,),
        )
        self.transport_response = Response(status_code=204)
        boundary.attach_session(self.transport_response, self.grant)
        cookie = SimpleCookie()
        cookie.load(self.transport_response.headers["set-cookie"])
        self.cookie_value = cookie[SESSION_COOKIE_NAME].value
        self.csrf_value = self.transport_response.headers[CSRF_HEADER_NAME]
        self.cookie_header = f"{SESSION_COOKIE_NAME}={self.cookie_value}"

        scores = SQLiteScoreRepository()
        scores.add_or_get(_score("authorized", "source-a", "84.20"))
        scores.add_or_get(_score("forbidden", "source-forbidden", "99.90"))
        authorization = PolicyAuthorizationService(
            DashboardAuthorizationPolicy(version=DASHBOARD_POLICY_VERSION),
            audit_service,
            clock=lambda: NOW,
        )
        app = create_dashboard_api(
            DashboardQueryService(scores, authorization, clock=lambda: NOW),
            bff_session_boundary=boundary,
            allowed_origins=(ORIGIN,),
            data_origin="test",
        )
        self.client = TestClient(app, base_url=ORIGIN)

    def state_changing_headers(self) -> dict[str, str]:
        return {
            "Cookie": self.cookie_header,
            CSRF_HEADER_NAME: self.csrf_value,
            "Origin": ORIGIN,
            "Referer": f"{ORIGIN}/dashboard",
            "Sec-Fetch-Site": "same-origin",
        }


def _setup() -> BffSetup:
    return BffSetup()


def _score(execution_id: str, source_id: str, value: str) -> QualityScore:
    return QualityScore(
        execution_id=execution_id,
        rule_version_id=None,
        scope_type=ScoreScopeType.SOURCE,
        scope_id=source_id,
        score_value=Decimal(value),
        score_status=ScoreStatus.CALCULATED,
        level=ScoreLevel.ACCEPTABLE,
        calculation_details={"included_in_official_aggregation": True},
        calculated_at=NOW - timedelta(days=1),
    )
