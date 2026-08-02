"""ENTERPRISE-LAB-02 application adapters for synthetic, non-production services."""

from __future__ import annotations

import hashlib
import json
import re
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import Request

from veri_kalitesi.api.errors import ApiAuthenticationError, ApiSessionUnavailableError
from veri_kalitesi.audit import AuditEvent, AuditEventInput, AuditWriteError
from veri_kalitesi.data_sources.errors import SecretResolutionError
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.servicenow import (
    ServiceNowAdapterError,
    ServiceNowAdapterErrorKind,
    ServiceNowTicketRequest,
    ServiceNowTicketResponse,
)
from veri_kalitesi.enterprise_lab.gate import (
    EnterpriseLabEvidence,
    verify_enterprise_lab_configuration,
)
from veri_kalitesi.environment_security import (
    LabAdapterGate,
    LabGateEvidence,
    LabGateStatus,
    StaticLabEnvironmentProvider,
)


ENTERPRISE_LAB_APPLICATION_POLICY_VERSION = "ENTERPRISE-LAB-02-v1"
_CLASSIFICATION = "PrototypeVerified"
_ALLOWED_ENVIRONMENTS = frozenset({"LOCAL", "ACCEPTANCE"})
_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}$")
_SECRET_REFERENCE_PATTERN = re.compile(
    r"^secret://(?P<environment>local|acceptance)/enterprise-lab/"
    r"(?P<name>[a-z0-9][a-z0-9-]{0,63})$"
)
_SECRET_NAMES = frozenset({"keycloak-admin", "postgres-app", "postgres-replication", "rabbitmq"})
_MAX_RESPONSE_BYTES = 64 * 1024


class EnterpriseLabAdapterError(Exception):
    """A lab adapter could not safely complete its operation."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


class HttpTransport(Protocol):
    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> HttpResponse: ...


class UrllibHttpTransport:
    """Small bounded HTTP transport; network details never escape adapter errors."""

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> HttpResponse:
        request = UrlRequest(url, data=body, headers=dict(headers), method=method)
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                payload = response.read(_MAX_RESPONSE_BYTES + 1)
                if len(payload) > _MAX_RESPONSE_BYTES:
                    raise EnterpriseLabAdapterError("LAB_RESPONSE_TOO_LARGE")
                return HttpResponse(
                    status=response.status,
                    headers=dict(response.headers.items()),
                    body=payload,
                )
        except HTTPError as exc:
            payload = exc.read(_MAX_RESPONSE_BYTES + 1)
            if len(payload) > _MAX_RESPONSE_BYTES:
                raise EnterpriseLabAdapterError("LAB_RESPONSE_TOO_LARGE") from exc
            return HttpResponse(
                status=exc.code,
                headers=dict(exc.headers.items()),
                body=payload,
            )
        except (OSError, TimeoutError, socket.timeout, URLError) as exc:
            raise EnterpriseLabAdapterError("LAB_ENDPOINT_UNAVAILABLE") from exc


@dataclass(frozen=True)
class SyntheticGroupAccess:
    roles: frozenset[str]
    permitted_source_ids: frozenset[str]
    permitted_dataset_ids: frozenset[str]
    can_view_enterprise: bool = False
    privileged: bool = False


@dataclass(frozen=True)
class SyntheticIdentityPolicy:
    version: str
    group_access: Mapping[str, SyntheticGroupAccess]
    required_mfa_value: str = "lab-mfa"
    context_lifetime_seconds: int = 300


@dataclass(frozen=True)
class EnterpriseLabApplicationAdapters:
    identity: KeycloakActorContextResolver
    secrets: LocalPrototypeSecretResolver
    servicenow: FakeServiceNowHttpAdapter
    siem: FailClosedSiemAuditAdapter
    classification: str = _CLASSIFICATION


def _derive_lab_gate_evidence(evidence: EnterpriseLabEvidence) -> LabGateEvidence:
    """Derives fail-closed lab gate evidence from the verified lab configuration evidence."""
    return LabGateEvidence(
        lab_id=evidence.lab_id,
        policy_version=evidence.policy_version,
        classification=evidence.classification,
        environment=evidence.environment,
        data_origin=evidence.data_origin,
        gate_status=LabGateStatus.OPEN,
        verified_at=datetime.now(timezone.utc),
        checks=evidence.checks,
    )


def build_enterprise_lab_application_adapters(
    configuration_path: Path,
    *,
    identity_policy: SyntheticIdentityPolicy,
    secret_manager_token_path: Path,
    transport: HttpTransport | None = None,
) -> EnterpriseLabApplicationAdapters:
    """Builds all application adapters only after the lab gate has passed."""

    evidence = verify_enterprise_lab_configuration(configuration_path)
    if evidence.environment not in _ALLOWED_ENVIRONMENTS:
        raise EnterpriseLabAdapterError("LAB_APPLICATION_ENVIRONMENT_FORBIDDEN")
    try:
        payload = _json_object(configuration_path.read_bytes(), "LAB_CONFIGURATION_UNAVAILABLE")
    except OSError as exc:
        raise EnterpriseLabAdapterError("LAB_CONFIGURATION_UNAVAILABLE") from exc
    endpoints = payload.get("endpoints")
    if not isinstance(endpoints, dict):
        raise EnterpriseLabAdapterError("LAB_ADAPTER_ENDPOINTS_INVALID")
    active_transport = transport or UrllibHttpTransport()
    gate = LabAdapterGate(StaticLabEnvironmentProvider(_derive_lab_gate_evidence(evidence)))
    return EnterpriseLabApplicationAdapters(
        identity=KeycloakActorContextResolver(
            _endpoint_value(endpoints, "identity"),
            identity_policy,
            transport=active_transport,
            gate=gate,
        ),
        secrets=LocalPrototypeSecretResolver(
            _endpoint_value(endpoints, "secret_manager"),
            environment=evidence.environment,
            authorization_token_path=secret_manager_token_path,
            transport=active_transport,
            gate=gate,
        ),
        servicenow=FakeServiceNowHttpAdapter(
            _endpoint_value(endpoints, "servicenow"),
            transport=active_transport,
            gate=gate,
        ),
        siem=FailClosedSiemAuditAdapter(
            _endpoint_value(endpoints, "siem"),
            transport=active_transport,
            gate=gate,
        ),
    )


class KeycloakActorContextResolver:
    """Validates bearer identity through the synthetic Keycloak userinfo endpoint."""

    def __init__(
        self,
        endpoint: str,
        policy: SyntheticIdentityPolicy,
        *,
        transport: HttpTransport | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        gate: LabAdapterGate | None = None,
    ) -> None:
        _validate_endpoint(endpoint, expected_host="keycloak")
        _validate_identity_policy(policy)
        self._userinfo_url = (
            endpoint.rstrip("/") + "/realms/enterprise-lab/protocol/openid-connect/userinfo"
        )
        self._policy = policy
        self._transport = transport or UrllibHttpTransport()
        self._clock = clock
        self._issuer = ActorContextIssuer()
        self._gate = gate

    def resolve(self, request: Request) -> ActorContext:
        if self._gate is not None:
            self._gate.guard("identity.resolve_actor_context")
        correlation_id = request.state.correlation_id
        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer ") or not authorization[7:].strip():
            raise ApiAuthenticationError("Authentication is required.", correlation_id)
        token = authorization[7:].strip()
        try:
            response = self._transport.request(
                method="GET",
                url=self._userinfo_url,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                body=None,
                timeout_seconds=3.0,
            )
        except EnterpriseLabAdapterError as exc:
            raise ApiSessionUnavailableError(
                "Synthetic identity provider is unavailable.",
                correlation_id,
            ) from exc
        if response.status in {401, 403}:
            raise ApiAuthenticationError("Identity assertion was rejected.", correlation_id)
        if response.status != 200:
            raise ApiSessionUnavailableError(
                "Synthetic identity provider is unavailable.",
                correlation_id,
            )

        try:
            claims = _json_object(response.body, "IDENTITY_RESPONSE_INVALID")
            actor_id = _required_code(claims, "sub", "IDENTITY_SUBJECT_INVALID")
        except EnterpriseLabAdapterError as exc:
            raise ApiAuthenticationError(
                "Identity assertion was rejected.", correlation_id
            ) from exc
        session_id = claims.get("sid")
        if session_id is None:
            session_id = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if not isinstance(session_id, str) or not _CODE_PATTERN.fullmatch(session_id):
            raise ApiAuthenticationError("Identity assertion was rejected.", correlation_id)
        if claims.get("mfa_evidence") != self._policy.required_mfa_value:
            raise ApiAuthenticationError("MFA evidence is required.", correlation_id)
        groups = claims.get("groups")
        if (
            not isinstance(groups, list)
            or not groups
            or any(not isinstance(group, str) for group in groups)
        ):
            raise ApiAuthenticationError("Identity scope mapping is required.", correlation_id)
        mapped = [
            self._policy.group_access[group]
            for group in groups
            if group in self._policy.group_access
        ]
        if not mapped:
            raise ApiAuthenticationError("Identity scope mapping is required.", correlation_id)

        now = self._clock().astimezone(timezone.utc)
        return self._issuer.issue(
            actor_id=actor_id,
            actor_type=ActorType.USER,
            authentication_source="synthetic-keycloak-oidc",
            session_id=session_id,
            roles=frozenset().union(*(access.roles for access in mapped)),
            permitted_source_ids=frozenset().union(
                *(access.permitted_source_ids for access in mapped)
            ),
            permitted_dataset_ids=frozenset().union(
                *(access.permitted_dataset_ids for access in mapped)
            ),
            can_view_enterprise=any(access.can_view_enterprise for access in mapped),
            privileged=any(access.privileged for access in mapped),
            issued_at=now,
            expires_at=now + timedelta(seconds=self._policy.context_lifetime_seconds),
            policy_version=self._policy.version,
            correlation_id=correlation_id,
        )


class LocalPrototypeSecretResolver:
    """Resolves only environment-scoped lab references using a file-backed token."""

    def __init__(
        self,
        endpoint: str,
        *,
        environment: str,
        authorization_token_path: Path,
        transport: HttpTransport | None = None,
        gate: LabAdapterGate | None = None,
    ) -> None:
        _validate_endpoint(endpoint, expected_host="local-secret-manager")
        if environment not in _ALLOWED_ENVIRONMENTS:
            raise EnterpriseLabAdapterError("LAB_APPLICATION_ENVIRONMENT_FORBIDDEN")
        self._endpoint = endpoint.rstrip("/") + "/v1/resolve"
        self._environment = environment.lower()
        self._authorization_token_path = authorization_token_path
        self._transport = transport or UrllibHttpTransport()
        self._gate = gate

    def resolve(self, secret_reference: str) -> Mapping[str, Any]:
        if self._gate is not None:
            self._gate.guard("secret.resolve")
        match = _SECRET_REFERENCE_PATTERN.fullmatch(secret_reference)
        if (
            match is None
            or match.group("environment") != self._environment
            or match.group("name") not in _SECRET_NAMES
        ):
            raise SecretResolutionError("Secret reference could not be resolved.")
        token = _read_token(self._authorization_token_path)
        body = _encode_json({"reference": match.group("name")})
        try:
            response = self._transport.request(
                method="POST",
                url=self._endpoint,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body=body,
                timeout_seconds=3.0,
            )
        except EnterpriseLabAdapterError as exc:
            raise SecretResolutionError("Secret reference could not be resolved.") from exc
        if response.status != 200:
            raise SecretResolutionError("Secret reference could not be resolved.")
        try:
            payload = _json_object(response.body, "SECRET_RESPONSE_INVALID")
        except EnterpriseLabAdapterError as exc:
            raise SecretResolutionError("Secret reference could not be resolved.") from exc
        if frozenset(payload) != {"reference", "value"} or payload["reference"] != match.group(
            "name"
        ):
            raise SecretResolutionError("Secret reference could not be resolved.")
        value = payload["value"]
        if not isinstance(value, str) or not value:
            raise SecretResolutionError("Secret reference could not be resolved.")
        return {"password": value}


class FakeServiceNowHttpAdapter:
    """Data-minimum adapter for the idempotent fake ServiceNow lab endpoint."""

    def __init__(
        self,
        endpoint: str,
        *,
        transport: HttpTransport | None = None,
        gate: LabAdapterGate | None = None,
    ) -> None:
        _validate_endpoint(endpoint, expected_host="fake-servicenow")
        self._endpoint = endpoint.rstrip("/") + "/api/now/table/incident"
        self._transport = transport or UrllibHttpTransport()
        self._gate = gate

    def create_ticket(self, request: ServiceNowTicketRequest) -> ServiceNowTicketResponse:
        if self._gate is not None:
            self._gate.guard("servicenow.create_ticket")
        payload = {
            "short_description": "SYNTHETIC_DATA_QUALITY_ISSUE",
            "correlation_id": request.correlation_id,
            "issue_id": request.issue_reference,
        }
        try:
            response = self._transport.request(
                method="POST",
                url=self._endpoint,
                headers={
                    "Idempotency-Key": request.client_request_id,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body=_encode_json(payload),
                timeout_seconds=3.0,
            )
        except EnterpriseLabAdapterError as exc:
            raise ServiceNowAdapterError(ServiceNowAdapterErrorKind.TEMPORARY) from exc
        if response.status in {401, 403}:
            raise ServiceNowAdapterError(ServiceNowAdapterErrorKind.AUTHENTICATION)
        if response.status == 429:
            raise ServiceNowAdapterError(
                ServiceNowAdapterErrorKind.RATE_LIMIT,
                retry_after_seconds=_retry_after(response.headers),
            )
        if response.status >= 500:
            raise ServiceNowAdapterError(ServiceNowAdapterErrorKind.TEMPORARY)
        if response.status not in {200, 201}:
            raise ServiceNowAdapterError(ServiceNowAdapterErrorKind.PERMANENT)
        try:
            payload = _json_object(response.body, "SERVICENOW_RESPONSE_INVALID")
        except EnterpriseLabAdapterError as exc:
            raise ServiceNowAdapterError(ServiceNowAdapterErrorKind.PERMANENT) from exc
        if frozenset(payload) != {"sys_id", "number"}:
            raise ServiceNowAdapterError(ServiceNowAdapterErrorKind.PERMANENT)
        try:
            return ServiceNowTicketResponse(
                external_ticket_id=_required_code(payload, "sys_id", "SERVICENOW_RESPONSE_INVALID"),
                ticket_number=_required_code(payload, "number", "SERVICENOW_RESPONSE_INVALID"),
            )
        except EnterpriseLabAdapterError as exc:
            raise ServiceNowAdapterError(ServiceNowAdapterErrorKind.PERMANENT) from exc


class FailClosedSiemAuditAdapter:
    """Projects audit events to an allowlisted SIEM envelope and fails closed."""

    def __init__(
        self,
        endpoint: str,
        *,
        transport: HttpTransport | None = None,
        gate: LabAdapterGate | None = None,
    ) -> None:
        _validate_endpoint(endpoint, expected_host="siem-collector")
        self._endpoint = endpoint.rstrip("/") + "/events"
        self._transport = transport or UrllibHttpTransport()
        self._gate = gate

    def append(self, event: AuditEventInput) -> None:
        if self._gate is not None:
            self._gate.guard("siem.append")
        event_id = _audit_input_id(event)
        self._publish(
            event_id=event_id,
            occurred_at=event.occurred_at,
            action=event.action,
            result=event.result.value,
            correlation_id=event.correlation_id,
        )

    def publish(self, event: AuditEvent) -> None:
        if self._gate is not None:
            self._gate.guard("siem.publish")
        self._publish(
            event_id=event.event_id,
            occurred_at=event.occurred_at,
            action=event.action,
            result=event.result.value,
            correlation_id=event.correlation_id,
        )

    def _publish(
        self,
        *,
        event_id: str,
        occurred_at: datetime,
        action: str,
        result: str,
        correlation_id: str,
    ) -> None:
        if (
            not _CODE_PATTERN.fullmatch(event_id)
            or not _CODE_PATTERN.fullmatch(action)
            or not _CODE_PATTERN.fullmatch(result)
            or not _CODE_PATTERN.fullmatch(correlation_id)
            or occurred_at.tzinfo is None
            or occurred_at.utcoffset() is None
        ):
            raise AuditWriteError("Audit event could not be transferred.")
        payload = {
            "event_id": event_id,
            "occurred_at_utc": occurred_at.astimezone(timezone.utc).isoformat(),
            "action": action,
            "result": result,
            "correlation_id": correlation_id,
        }
        try:
            response = self._transport.request(
                method="POST",
                url=self._endpoint,
                headers={
                    "Idempotency-Key": event_id,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body=_encode_json(payload),
                timeout_seconds=3.0,
            )
        except EnterpriseLabAdapterError as exc:
            raise AuditWriteError("Audit event could not be transferred.") from exc
        if response.status not in {200, 202}:
            raise AuditWriteError("Audit event could not be transferred.")
        try:
            response_payload = _json_object(response.body, "SIEM_RESPONSE_INVALID")
        except EnterpriseLabAdapterError as exc:
            raise AuditWriteError("Audit event could not be transferred.") from exc
        if response_payload != {"status": "ACCEPTED"}:
            raise AuditWriteError("Audit event could not be transferred.")


def _validate_identity_policy(policy: SyntheticIdentityPolicy) -> None:
    if (
        policy.version != ENTERPRISE_LAB_APPLICATION_POLICY_VERSION
        or not policy.group_access
        or not _CODE_PATTERN.fullmatch(policy.required_mfa_value)
        or not 1 <= policy.context_lifetime_seconds <= 900
    ):
        raise EnterpriseLabAdapterError("LAB_IDENTITY_POLICY_INVALID")
    for group, access in policy.group_access.items():
        if (
            not _CODE_PATTERN.fullmatch(group)
            or not access.roles
            or any(not _CODE_PATTERN.fullmatch(role) for role in access.roles)
            or any(not _CODE_PATTERN.fullmatch(item) for item in access.permitted_source_ids)
            or any(not _CODE_PATTERN.fullmatch(item) for item in access.permitted_dataset_ids)
        ):
            raise EnterpriseLabAdapterError("LAB_IDENTITY_POLICY_INVALID")


def _validate_endpoint(endpoint: str, *, expected_host: str) -> None:
    from urllib.parse import urlsplit

    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError as exc:
        raise EnterpriseLabAdapterError("LAB_ADAPTER_ENDPOINT_INVALID") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname != expected_host
        or port != 8080
        or parsed.path not in {"", "/"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise EnterpriseLabAdapterError("LAB_ADAPTER_ENDPOINT_INVALID")


def _read_token(path: Path) -> str:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
            raise OSError
        token = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise SecretResolutionError("Secret reference could not be resolved.") from exc
    if not token:
        raise SecretResolutionError("Secret reference could not be resolved.")
    return token


def _json_object(body: bytes, reason_code: str) -> dict[str, Any]:
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EnterpriseLabAdapterError(reason_code) from exc
    if not isinstance(payload, dict):
        raise EnterpriseLabAdapterError(reason_code)
    return payload


def _required_code(payload: Mapping[str, Any], field: str, reason_code: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not _CODE_PATTERN.fullmatch(value):
        raise EnterpriseLabAdapterError(reason_code)
    return value


def _endpoint_value(endpoints: Mapping[str, Any], name: str) -> str:
    value = endpoints.get(name)
    if not isinstance(value, str):
        raise EnterpriseLabAdapterError("LAB_ADAPTER_ENDPOINTS_INVALID")
    return value


def _encode_json(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")


def _retry_after(headers: Mapping[str, str]) -> int | None:
    value = next(
        (header_value for name, header_value in headers.items() if name.lower() == "retry-after"),
        None,
    )
    if value is None or not value.isdigit():
        return None
    seconds = int(value)
    return seconds if 0 <= seconds <= 3600 else None


def _audit_input_id(event: AuditEventInput) -> str:
    canonical = _encode_json(
        {
            "action": event.action,
            "actor_id": event.actor_id,
            "actor_type": event.actor_type,
            "correlation_id": event.correlation_id,
            "object_id": event.object_id,
            "object_type": event.object_type,
            "occurred_at_utc": event.occurred_at.astimezone(timezone.utc).isoformat(),
            "reason_code": event.reason_code,
            "result": event.result.value,
        }
    )
    return hashlib.sha256(canonical).hexdigest()
