from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from veri_kalitesi.audit import (
    AuditRedactionPolicy,
    AuditRedactor,
    AuditValidationError,
    SQLiteAuditRepository,
    SQLiteTransactionalAudit,
)
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.issues import IssuePriority, IssueSourceEventType, IssueStatus
from veri_kalitesi.servicenow import (
    SQLiteServiceNowRepository,
    ServiceNowAdapterError,
    ServiceNowAdapterErrorKind,
    ServiceNowAuthorizationError,
    ServiceNowConflictError,
    ServiceNowExportPolicy,
    ServiceNowIssueProjection,
    ServiceNowPolicyError,
    ServiceNowService,
    ServiceNowTechnicalError,
    ServiceNowTicketCommand,
    ServiceNowTicketRequest,
    ServiceNowTicketResponse,
    ServiceNowTicketStatus,
    ServiceNowValidationError,
)


NOW = datetime(2026, 7, 17, 16, 0, tzinfo=timezone.utc)
ACTOR_POLICY_VERSION = "BANK_SERVICENOW_ACTOR_V1"
SERVICE_ID = "11111111-1111-4111-8111-111111111111"
USER_ID = "22222222-2222-4222-8222-222222222222"
ISSUE_ID = "33333333-3333-4333-8333-333333333333"
OTHER_ISSUE_ID = "44444444-4444-4444-8444-444444444444"
DETAIL_REFERENCE_ID = "55555555-5555-4555-8555-555555555555"
OTHER_DETAIL_REFERENCE_ID = "66666666-6666-4666-8666-666666666666"


class StaticIssueResolver:
    def __init__(
        self,
        projection: ServiceNowIssueProjection | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.projection = projection or _projection()
        self.error = error
        self.calls = 0

    def resolve_issue(self, issue_id: str) -> ServiceNowIssueProjection | None:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.projection


class IdempotentFakeServiceNowAdapter:
    def __init__(
        self,
        *,
        error: Exception | None = None,
        response: ServiceNowTicketResponse | None = None,
    ) -> None:
        self.error = error
        self.response = response or ServiceNowTicketResponse("SYS0000001", "INC0000001")
        self.calls = 0
        self.requests: list[ServiceNowTicketRequest] = []
        self.created_by_request_id: dict[str, ServiceNowTicketResponse] = {}

    def create_ticket(self, request: ServiceNowTicketRequest) -> ServiceNowTicketResponse:
        self.calls += 1
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.created_by_request_id.setdefault(request.client_request_id, self.response)


class ServiceNowFixture:
    def __init__(
        self,
        service: ServiceNowService,
        repository: SQLiteServiceNowRepository,
        resolver: StaticIssueResolver,
        adapter: IdempotentFakeServiceNowAdapter,
        audit_repository: SQLiteAuditRepository,
    ) -> None:
        self.service = service
        self.repository = repository
        self.resolver = resolver
        self.adapter = adapter
        self.audit_repository = audit_repository


def test_fr_071_fr_087_creates_allowlisted_ticket_link_and_history() -> None:
    fixture = _fixture()
    command = _command()

    link = fixture.service.create_ticket(command, _service_context())

    assert link.issue_id == ISSUE_ID
    assert link.external_ticket_id == "SYS0000001"
    assert link.ticket_number == "INC0000001"
    assert link.status is ServiceNowTicketStatus.CREATED
    assert link.idempotency_key_digest != command.idempotency_key
    assert fixture.repository.count() == 1
    assert fixture.resolver.calls == 1
    assert fixture.adapter.calls == 1
    request = fixture.adapter.requests[0]
    assert set(asdict(request)) == {
        "client_request_id",
        "issue_reference",
        "source_event_type",
        "priority",
        "detail_reference_id",
        "correlation_id",
    }
    assert request.client_request_id != command.idempotency_key
    assert request.issue_reference == "DQI-2026-000001"
    assert request.detail_reference_id == DETAIL_REFERENCE_ID
    serialized_request = repr(request).lower()
    for forbidden in (
        "customer",
        "tckn",
        "account",
        "card",
        "sql",
        "password",
        "secret",
        "token",
    ):
        assert forbidden not in serialized_request
    history = fixture.repository.list_history(link.link_id)
    assert len(history) == 1
    assert history[0].action == "SERVICENOW_TICKET_CREATED"
    assert history[0].old_status is None
    assert history[0].new_status is ServiceNowTicketStatus.CREATED
    audit = fixture.audit_repository.list_events()[-1]
    assert audit.action == "SERVICENOW_TICKET_CREATED"
    assert audit.reason_code == "ALLOWLIST_PAYLOAD_ACCEPTED"
    assert audit.new_value_summary == {
        "adapter_result": "CREATED",
        "priority": "CRITICAL",
        "source_event_type": "QUALITY",
        "status": "CREATED",
    }
    serialized_audit = repr(audit)
    assert ISSUE_ID not in serialized_audit
    assert DETAIL_REFERENCE_ID not in serialized_audit
    assert "INC0000001" not in serialized_audit


def test_rule_011_technical_issue_remains_distinct_in_outbound_contract() -> None:
    fixture = _fixture(
        projection=replace(
            _projection(),
            source_event_type=IssueSourceEventType.TECHNICAL,
        )
    )

    fixture.service.create_ticket(_command(), _service_context())

    assert fixture.adapter.requests[0].source_event_type == "TECHNICAL"
    audit = fixture.audit_repository.list_events()[-1]
    assert audit.new_value_summary["source_event_type"] == "TECHNICAL"


@pytest.mark.parametrize("context_kind", ["missing", "user", "privileged", "roles-missing"])
def test_bfr_ext_001_ticket_creation_requires_standard_trusted_service_context(
    context_kind: str,
) -> None:
    fixture = _fixture()
    contexts = {
        "missing": None,
        "user": _user_context(),
        "privileged": _service_context(privileged=True),
        "roles-missing": _service_context(roles=frozenset()),
    }

    with pytest.raises(ServiceNowAuthorizationError):
        fixture.service.create_ticket(_command(), contexts[context_kind])

    assert fixture.resolver.calls == 0
    assert fixture.adapter.calls == 0
    assert fixture.repository.count() == 0


@pytest.mark.parametrize(
    ("status", "priority"),
    [
        (IssueStatus.CLOSED, IssuePriority.CRITICAL),
        (IssueStatus.ASSIGNED, IssuePriority.LOW),
    ],
)
def test_fr_071_export_policy_rejects_ineligible_issue_before_adapter(
    status: IssueStatus,
    priority: IssuePriority,
) -> None:
    fixture = _fixture(projection=_projection(status=status, priority=priority))

    with pytest.raises(ServiceNowPolicyError, match="not eligible"):
        fixture.service.create_ticket(_command(), _service_context())

    assert fixture.adapter.calls == 0
    assert fixture.repository.count() == 0


def test_ac_019_nfr_rel_005_one_hundred_replays_create_one_ticket() -> None:
    fixture = _fixture()
    command = _command()

    links = [fixture.service.create_ticket(command, _service_context()) for _ in range(100)]

    assert len({link.link_id for link in links}) == 1
    assert fixture.adapter.calls == 1
    assert len(fixture.adapter.created_by_request_id) == 1
    assert fixture.repository.count() == 1
    assert len(fixture.repository.list_history(links[0].link_id)) == 1
    assert len(fixture.audit_repository.list_events()) == 1


def test_fr_071_same_issue_with_new_key_returns_existing_ticket() -> None:
    fixture = _fixture()
    first = fixture.service.create_ticket(_command(), _service_context())

    repeated = fixture.service.create_ticket(
        _command(idempotency_key="SERVICENOW.ISSUE.1.SECOND.REQUEST"),
        _service_context(),
    )

    assert repeated.link_id == first.link_id
    assert fixture.adapter.calls == 1
    assert fixture.repository.count() == 1


def test_fr_084_rule_011_same_key_with_different_payload_is_conflict() -> None:
    fixture = _fixture()
    fixture.service.create_ticket(_command(), _service_context())
    fixture.resolver.projection = replace(
        _projection(),
        priority=IssuePriority.HIGH,
        detail_reference_id=OTHER_DETAIL_REFERENCE_ID,
    )

    with pytest.raises(ServiceNowConflictError):
        fixture.service.create_ticket(_command(), _service_context())

    assert fixture.adapter.calls == 1
    assert fixture.repository.count() == 1


def test_bfr_ext_002_untrusted_projection_is_rejected_before_adapter() -> None:
    fixture = _fixture(
        projection=replace(_projection(), issue_reference="CUSTOMER.SECRET.REFERENCE")
    )

    with pytest.raises(ServiceNowValidationError, match="forbidden"):
        fixture.service.create_ticket(_command(), _service_context())

    assert fixture.adapter.calls == 0
    assert fixture.repository.count() == 0


@pytest.mark.parametrize(
    "error_kind",
    [ServiceNowAdapterErrorKind.AUTHENTICATION, ServiceNowAdapterErrorKind.RATE_LIMIT],
)
def test_fr_087_adapter_error_is_classified_without_sensitive_detail(
    error_kind: ServiceNowAdapterErrorKind,
) -> None:
    fixture = _fixture(adapter_error=ServiceNowAdapterError(error_kind))

    with pytest.raises(ServiceNowTechnicalError) as exc_info:
        fixture.service.create_ticket(_command(), _service_context())

    assert exc_info.value.error_kind is error_kind
    assert "credential" not in str(exc_info.value).lower()
    assert fixture.repository.count() == 0


def test_fr_087_invalid_adapter_response_is_permanent_technical_error() -> None:
    fixture = _fixture(adapter_response=ServiceNowTicketResponse("SYS0000001", "SECRET.TICKET"))

    with pytest.raises(ServiceNowTechnicalError) as exc_info:
        fixture.service.create_ticket(_command(), _service_context())

    assert exc_info.value.error_kind is ServiceNowAdapterErrorKind.PERMANENT
    assert "SECRET.TICKET" not in str(exc_info.value)
    assert fixture.repository.count() == 0


def test_fr_071_resolver_failure_is_redacted_technical_error() -> None:
    fixture = _fixture(resolver_error=RuntimeError("customer secret"))

    with pytest.raises(ServiceNowTechnicalError) as exc_info:
        fixture.service.create_ticket(_command(), _service_context())

    assert "customer secret" not in str(exc_info.value)
    assert fixture.adapter.calls == 0
    assert fixture.repository.count() == 0


def test_bfr_ext_002_audit_policy_failure_prevents_external_ticket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture()

    def fail_prepare(event: object) -> object:
        raise AuditValidationError("redaction policy unavailable")

    monkeypatch.setattr(fixture.service.transactional_audit, "prepare", fail_prepare)

    with pytest.raises(ServiceNowTechnicalError):
        fixture.service.create_ticket(_command(), _service_context())

    assert fixture.adapter.calls == 0
    assert fixture.repository.count() == 0


def test_nfr_rel_006_audit_failure_rolls_back_and_adapter_retry_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture()
    original_stage = fixture.service.transactional_audit.stage

    def fail_stage(event: object) -> None:
        raise sqlite3.OperationalError("audit outbox unavailable")

    monkeypatch.setattr(fixture.service.transactional_audit, "stage", fail_stage)

    with pytest.raises(ServiceNowTechnicalError):
        fixture.service.create_ticket(_command(), _service_context())

    assert fixture.repository.count() == 0
    assert fixture.adapter.calls == 1
    assert len(fixture.adapter.created_by_request_id) == 1

    monkeypatch.setattr(fixture.service.transactional_audit, "stage", original_stage)
    link = fixture.service.create_ticket(_command(), _service_context())

    assert link.ticket_number == "INC0000001"
    assert fixture.adapter.calls == 2
    assert len(fixture.adapter.created_by_request_id) == 1
    assert fixture.repository.count() == 1


def _fixture(
    *,
    projection: ServiceNowIssueProjection | None = None,
    resolver_error: Exception | None = None,
    adapter_error: Exception | None = None,
    adapter_response: ServiceNowTicketResponse | None = None,
) -> ServiceNowFixture:
    repository = SQLiteServiceNowRepository()
    audit_repository = SQLiteAuditRepository()
    audit_outbox = SQLiteTransactionalAudit(
        repository.connection,
        AuditRedactor(
            AuditRedactionPolicy(
                version="SERVICENOW_REDACTION_V1",
                allowed_fields_by_action={
                    "SERVICENOW_TICKET_CREATED": frozenset(
                        {"status", "source_event_type", "priority", "adapter_result"}
                    )
                },
            )
        ),
        audit_repository,
        policy_version="SERVICENOW_OUTBOX_V1",
    )
    resolver = StaticIssueResolver(projection, error=resolver_error)
    adapter = IdempotentFakeServiceNowAdapter(
        error=adapter_error,
        response=adapter_response,
    )
    service = ServiceNowService(
        repository,
        resolver,
        adapter,
        audit_outbox,
        ServiceNowExportPolicy(
            version="SERVICENOW_EXPORT_V1",
            actor_policy_version=ACTOR_POLICY_VERSION,
            eligible_statuses=frozenset(
                {
                    IssueStatus.ASSIGNED,
                    IssueStatus.INVESTIGATING,
                    IssueStatus.WAITING_FOR_RESOLUTION,
                }
            ),
            eligible_priorities=frozenset({IssuePriority.HIGH, IssuePriority.CRITICAL}),
        ),
        clock=lambda: NOW,
    )
    return ServiceNowFixture(service, repository, resolver, adapter, audit_repository)


def _projection(
    *,
    issue_id: str = ISSUE_ID,
    status: IssueStatus = IssueStatus.ASSIGNED,
    priority: IssuePriority = IssuePriority.CRITICAL,
) -> ServiceNowIssueProjection:
    return ServiceNowIssueProjection(
        issue_id=issue_id,
        issue_reference="DQI-2026-000001",
        source_event_type=IssueSourceEventType.QUALITY,
        status=status,
        priority=priority,
        detail_reference_id=DETAIL_REFERENCE_ID,
    )


def _command(
    *,
    issue_id: str = ISSUE_ID,
    idempotency_key: str = "SERVICENOW.ISSUE.1",
) -> ServiceNowTicketCommand:
    return ServiceNowTicketCommand(
        issue_id=issue_id,
        idempotency_key=idempotency_key,
        correlation_id="correlation-servicenow",
    )


def _service_context(
    *,
    privileged: bool = False,
    roles: frozenset[str] = frozenset({"SERVICENOW_TICKET_PRODUCER"}),
) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id=SERVICE_ID,
        actor_type=ActorType.SERVICE,
        authentication_source="synthetic-service-adapter",
        session_id="synthetic-servicenow-session",
        roles=roles,
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=False,
        privileged=privileged,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id="correlation-servicenow-producer",
    )


def _user_context() -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id=USER_ID,
        actor_type=ActorType.USER,
        authentication_source="synthetic-user-adapter",
        session_id="synthetic-user-session",
        roles=frozenset({"SERVICENOW_TICKET_PRODUCER"}),
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=False,
        privileged=False,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id="correlation-servicenow-user",
    )
