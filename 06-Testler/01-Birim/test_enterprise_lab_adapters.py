from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

import pytest
from fastapi import Request

from veri_kalitesi.api.errors import ApiAuthenticationError, ApiSessionUnavailableError
from veri_kalitesi.audit import AuditEventInput, AuditResult, AuditWriteError
from veri_kalitesi.data_sources.errors import SecretResolutionError
from veri_kalitesi.enterprise_lab import (
    ENTERPRISE_LAB_APPLICATION_POLICY_VERSION,
    EnterpriseLabAdapterError,
    FailClosedSiemAuditAdapter,
    FakeServiceNowHttpAdapter,
    HttpResponse,
    KeycloakActorContextResolver,
    LocalPrototypeSecretResolver,
    SyntheticGroupAccess,
    SyntheticIdentityPolicy,
    build_enterprise_lab_application_adapters,
)
from veri_kalitesi.environment_security import (
    EnvironmentPolicyBlockedError,
    LabAdapterGate,
    LabGateEvidence,
    LabGateStatus,
    StaticLabEnvironmentProvider,
)
from veri_kalitesi.identity import is_trusted_actor_context
from veri_kalitesi.servicenow import (
    ServiceNowAdapterError,
    ServiceNowAdapterErrorKind,
    ServiceNowTicketRequest,
)


NOW = datetime(2026, 7, 29, 16, 0, tzinfo=timezone.utc)
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONFIGURATION_PATH = (
    REPOSITORY_ROOT / "infrastructure" / "enterprise-lab" / "config" / "environment.json"
)


def _json_response(status: int, payload: Mapping[str, object]) -> HttpResponse:
    return HttpResponse(
        status=status,
        headers={},
        body=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii"),
    )


class StubHttpTransport:
    def __init__(
        self,
        responses: list[HttpResponse | Exception],
    ) -> None:
        self.responses = list(responses)
        self.calls: list[RecordedHttpCall] = []

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> HttpResponse:
        self.calls.append(
            RecordedHttpCall(
                method=method,
                url=url,
                headers=dict(headers),
                body=body,
                timeout_seconds=timeout_seconds,
            )
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@dataclass(frozen=True)
class RecordedHttpCall:
    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes | None
    timeout_seconds: float


def test_enterprise_lab_02_composes_only_prototype_adapters_after_environment_gate(
    tmp_path: Path,
) -> None:
    token_path = tmp_path / "secret-manager-token"
    token_path.write_text("synthetic-token", encoding="utf-8")

    adapters = build_enterprise_lab_application_adapters(
        CONFIGURATION_PATH,
        identity_policy=_identity_policy(),
        secret_manager_token_path=token_path,
        transport=StubHttpTransport([]),
    )

    assert adapters.classification == "PrototypeVerified"
    assert isinstance(adapters.identity, KeycloakActorContextResolver)
    assert isinstance(adapters.secrets, LocalPrototypeSecretResolver)
    assert isinstance(adapters.servicenow, FakeServiceNowHttpAdapter)
    assert isinstance(adapters.siem, FailClosedSiemAuditAdapter)
    assert "ApprovedByBank" not in repr(adapters)


def test_synthetic_keycloak_realm_projects_versioned_group_and_mfa_claims_without_secret() -> None:
    realm_path = (
        REPOSITORY_ROOT / "infrastructure" / "enterprise-lab" / "config" / "keycloak-realm.json"
    )
    payload = json.loads(realm_path.read_text(encoding="utf-8"))
    client = payload["clients"][0]
    mapper_claims = {mapper["config"]["claim.name"] for mapper in client["protocolMappers"]}
    users = {user["username"]: user for user in payload["users"]}
    viewer = users["synthetic-lab-viewer"]
    unmapped = users["synthetic-lab-unmapped"]

    assert mapper_claims == {"groups", "mfa_evidence"}
    assert client["directAccessGrantsEnabled"] is True
    assert viewer["groups"] == ["/lab-viewers"]
    assert viewer["attributes"] == {"mfa_evidence": ["lab-mfa"]}
    assert unmapped["groups"] == ["/lab-unmapped"]
    assert viewer["credentials"][0]["value"] == "${LAB_USER_PASSWORD}"
    assert unmapped["credentials"][0]["value"] == "${LAB_USER_PASSWORD}"
    assert "synthetic-token" not in realm_path.read_text(encoding="utf-8")


def test_enterprise_lab_02_rejects_application_binding_outside_local_or_acceptance(
    tmp_path: Path,
) -> None:
    payload = json.loads(CONFIGURATION_PATH.read_text(encoding="utf-8"))
    payload["environment"] = "TEST"
    payload["secret_reference"] = "secret://test/enterprise-lab"
    candidate = tmp_path / "environment.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        EnterpriseLabAdapterError,
        match="LAB_APPLICATION_ENVIRONMENT_FORBIDDEN",
    ):
        build_enterprise_lab_application_adapters(
            candidate,
            identity_policy=_identity_policy(),
            secret_manager_token_path=tmp_path / "unused",
            transport=StubHttpTransport([]),
        )


def test_keycloak_resolver_issues_trusted_context_from_verified_synthetic_claims() -> None:
    transport = StubHttpTransport(
        [
            _json_response(
                200,
                {
                    "sub": "synthetic-user-1",
                    "sid": "synthetic-session-1",
                    "mfa_evidence": "lab-mfa",
                    "groups": ["lab-viewers"],
                    "roles": ["CALLER_SUPPLIED_ROLE_IS_IGNORED"],
                },
            )
        ]
    )
    resolver = KeycloakActorContextResolver(
        "http://keycloak:8080",
        _identity_policy(),
        transport=transport,
        clock=lambda: NOW,
    )

    context = resolver.resolve(_request("Bearer synthetic-access-token"))

    assert is_trusted_actor_context(context)
    assert context.actor_id == "synthetic-user-1"
    assert context.authentication_source == "synthetic-keycloak-oidc"
    assert context.roles == frozenset({"DATA_VIEWER"})
    assert context.permitted_source_ids == frozenset({"synthetic-source"})
    assert context.permitted_dataset_ids == frozenset({"synthetic-dataset"})
    assert context.policy_version == ENTERPRISE_LAB_APPLICATION_POLICY_VERSION
    assert context.correlation_id == "correlation-1"
    assert transport.calls[0].url == (
        "http://keycloak:8080/realms/enterprise-lab/protocol/openid-connect/userinfo"
    )


@pytest.mark.parametrize(
    ("responses", "expected_error"),
    [
        ([_json_response(403, {"code": "DENIED"})], ApiAuthenticationError),
        ([EnterpriseLabAdapterError("LAB_ENDPOINT_UNAVAILABLE")], ApiSessionUnavailableError),
    ],
)
def test_keycloak_resolver_fails_closed_for_denial_or_connection_loss(
    responses: list[HttpResponse | Exception],
    expected_error: type[Exception],
) -> None:
    resolver = KeycloakActorContextResolver(
        "http://keycloak:8080",
        _identity_policy(),
        transport=StubHttpTransport(responses),
        clock=lambda: NOW,
    )

    with pytest.raises(expected_error):
        resolver.resolve(_request("Bearer synthetic-access-token"))


def test_keycloak_resolver_rejects_missing_mfa_or_known_group_mapping() -> None:
    transport = StubHttpTransport(
        [
            _json_response(
                200,
                {
                    "sub": "synthetic-user-1",
                    "mfa_evidence": "not-verified",
                    "groups": ["unmapped-group"],
                },
            )
        ]
    )
    resolver = KeycloakActorContextResolver(
        "http://keycloak:8080",
        _identity_policy(),
        transport=transport,
        clock=lambda: NOW,
    )

    with pytest.raises(ApiAuthenticationError):
        resolver.resolve(_request("Bearer synthetic-access-token"))


def test_local_secret_resolver_uses_reference_and_returns_no_transport_metadata(
    tmp_path: Path,
) -> None:
    token_path = tmp_path / "token"
    token_path.write_text("synthetic-manager-token", encoding="utf-8")
    transport = StubHttpTransport(
        [
            _json_response(
                200,
                {"reference": "postgres-app", "value": "synthetic-database-password"},
            )
        ]
    )
    resolver = LocalPrototypeSecretResolver(
        "http://local-secret-manager:8080",
        environment="LOCAL",
        authorization_token_path=token_path,
        transport=transport,
    )

    resolved = resolver.resolve("secret://local/enterprise-lab/postgres-app")

    assert resolved == {"password": "synthetic-database-password"}
    assert transport.calls[0].body is not None
    assert json.loads(transport.calls[0].body) == {"reference": "postgres-app"}
    assert transport.calls[0].headers == {
        "Authorization": "Bearer synthetic-manager-token",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


@pytest.mark.parametrize(
    "response",
    [
        _json_response(404, {"code": "REFERENCE_NOT_FOUND"}),
        EnterpriseLabAdapterError("LAB_ENDPOINT_UNAVAILABLE"),
    ],
)
def test_local_secret_resolver_fails_closed_without_disclosing_reference_or_value(
    tmp_path: Path,
    response: HttpResponse | Exception,
) -> None:
    token_path = tmp_path / "token"
    token_path.write_text("synthetic-manager-token", encoding="utf-8")
    resolver = LocalPrototypeSecretResolver(
        "http://local-secret-manager:8080",
        environment="LOCAL",
        authorization_token_path=token_path,
        transport=StubHttpTransport([response]),
    )

    with pytest.raises(SecretResolutionError) as error:
        resolver.resolve("secret://local/enterprise-lab/postgres-app")

    assert "postgres-app" not in str(error.value)
    assert "synthetic-manager-token" not in str(error.value)


def test_fake_servicenow_adapter_sends_data_minimum_idempotent_payload() -> None:
    transport = StubHttpTransport(
        [
            _json_response(201, {"sys_id": "synthetic-sys-1", "number": "LAB0001"}),
            _json_response(200, {"sys_id": "synthetic-sys-1", "number": "LAB0001"}),
        ]
    )
    adapter = FakeServiceNowHttpAdapter(
        "http://fake-servicenow:8080",
        transport=transport,
    )
    request = _servicenow_request()

    first = adapter.create_ticket(request)
    replay = adapter.create_ticket(request)

    assert first == replay
    assert transport.calls[0].headers["Idempotency-Key"] == request.client_request_id
    assert transport.calls[0].body is not None
    assert json.loads(transport.calls[0].body) == {
        "short_description": "SYNTHETIC_DATA_QUALITY_ISSUE",
        "correlation_id": "correlation-1",
        "issue_id": "DQI-SYNTHETIC-1",
    }


@pytest.mark.parametrize(
    ("response", "error_kind"),
    [
        (_json_response(403, {"code": "DENIED"}), ServiceNowAdapterErrorKind.AUTHENTICATION),
        (_json_response(503, {"code": "DOWN"}), ServiceNowAdapterErrorKind.TEMPORARY),
        (
            EnterpriseLabAdapterError("LAB_ENDPOINT_UNAVAILABLE"),
            ServiceNowAdapterErrorKind.TEMPORARY,
        ),
    ],
)
def test_fake_servicenow_adapter_classifies_failures_without_remote_detail(
    response: HttpResponse | Exception,
    error_kind: ServiceNowAdapterErrorKind,
) -> None:
    adapter = FakeServiceNowHttpAdapter(
        "http://fake-servicenow:8080",
        transport=StubHttpTransport([response]),
    )

    with pytest.raises(ServiceNowAdapterError) as error:
        adapter.create_ticket(_servicenow_request())

    assert error.value.error_kind is error_kind
    assert "DOWN" not in str(error.value)


def test_siem_audit_adapter_is_data_minimum_and_reuses_deterministic_event_key() -> None:
    transport = StubHttpTransport(
        [
            _json_response(202, {"status": "ACCEPTED"}),
            _json_response(200, {"status": "ACCEPTED"}),
        ]
    )
    adapter = FailClosedSiemAuditAdapter(
        "http://siem-collector:8080",
        transport=transport,
    )
    event = _audit_event()

    adapter.append(event)
    adapter.append(event)

    assert transport.calls[0].body is not None
    assert transport.calls[1].body is not None
    first_payload = json.loads(transport.calls[0].body)
    assert first_payload == json.loads(transport.calls[1].body)
    assert transport.calls[0].headers["Idempotency-Key"] == first_payload["event_id"]
    assert set(first_payload) == {
        "event_id",
        "occurred_at_utc",
        "action",
        "result",
        "correlation_id",
    }
    assert event.actor_id not in repr(first_payload)
    assert event.object_id not in repr(first_payload)


@pytest.mark.parametrize(
    "response",
    [
        _json_response(503, {"code": "DOWN"}),
        EnterpriseLabAdapterError("LAB_ENDPOINT_UNAVAILABLE"),
    ],
)
def test_siem_audit_transfer_failure_is_fail_closed(
    response: HttpResponse | Exception,
) -> None:
    adapter = FailClosedSiemAuditAdapter(
        "http://siem-collector:8080",
        transport=StubHttpTransport([response]),
    )

    with pytest.raises(AuditWriteError, match="could not be transferred"):
        adapter.append(_audit_event())


def test_closed_lab_gate_blocks_synthetic_adapter_operation() -> None:
    gate = LabAdapterGate(
        StaticLabEnvironmentProvider(_lab_gate_evidence(gate_status=LabGateStatus.CLOSED)),
        clock=lambda: NOW,
    )
    adapter = FakeServiceNowHttpAdapter(
        "http://fake-servicenow:8080",
        transport=StubHttpTransport([]),
        gate=gate,
    )

    with pytest.raises(EnvironmentPolicyBlockedError, match="LAB_GATE_CLOSED"):
        adapter.create_ticket(_servicenow_request())


def test_missing_lab_evidence_blocks_synthetic_adapter_operation() -> None:
    gate = LabAdapterGate(StaticLabEnvironmentProvider(None), clock=lambda: NOW)
    adapter = FailClosedSiemAuditAdapter(
        "http://siem-collector:8080",
        transport=StubHttpTransport([]),
        gate=gate,
    )

    with pytest.raises(EnvironmentPolicyBlockedError, match="LAB_EVIDENCE_MISSING"):
        adapter.append(_audit_event())


def test_build_wires_open_lab_gate_so_synthetic_operations_pass(tmp_path: Path) -> None:
    token_path = tmp_path / "secret-manager-token"
    token_path.write_text("synthetic-token", encoding="utf-8")
    transport = StubHttpTransport(
        [_json_response(201, {"sys_id": "synthetic-sys-1", "number": "LAB0001"})]
    )

    adapters = build_enterprise_lab_application_adapters(
        CONFIGURATION_PATH,
        identity_policy=_identity_policy(),
        secret_manager_token_path=token_path,
        transport=transport,
    )

    response = adapters.servicenow.create_ticket(_servicenow_request())

    assert response.ticket_number == "LAB0001"


def _lab_gate_evidence(*, gate_status: LabGateStatus) -> LabGateEvidence:
    return LabGateEvidence(
        lab_id="ENTERPRISE-LAB",
        policy_version="ENTERPRISE-LAB-01-v1",
        classification="PrototypeVerified",
        environment="LOCAL",
        data_origin="SYNTHETIC",
        gate_status=gate_status,
        verified_at=NOW,
        checks=("PINNED_CONFIGURATION_VERIFIED",),
    )


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


def _request(authorization: str) -> Request:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/dashboard",
            "headers": [(b"authorization", authorization.encode("ascii"))],
            "state": {},
        }
    )
    request.state.correlation_id = "correlation-1"
    return request


def _servicenow_request() -> ServiceNowTicketRequest:
    return ServiceNowTicketRequest(
        client_request_id="idempotency-digest-1",
        issue_reference="DQI-SYNTHETIC-1",
        source_event_type="QUALITY",
        priority="HIGH",
        detail_reference_id="11111111-1111-4111-8111-111111111111",
        correlation_id="correlation-1",
    )


def _audit_event() -> AuditEventInput:
    return AuditEventInput(
        actor_id="synthetic-actor-1",
        actor_type="USER",
        correlation_id="correlation-1",
        action="SYNTHETIC_ACTION",
        object_type="SyntheticObject",
        object_id="synthetic-object-1",
        result=AuditResult.SUCCESS,
        reason_code="SYNTHETIC_REASON",
        old_values={},
        new_values={"secret": "must-not-be-projected"},
        occurred_at=NOW,
    )
