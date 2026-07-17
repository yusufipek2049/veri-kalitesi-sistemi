from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import pytest

from veri_kalitesi.audit import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactor,
    AuditResult,
    AuditService,
    SQLiteAuditRepository,
    build_default_redaction_policy,
)
from veri_kalitesi.identity import (
    ActorContextValidationError,
    ActorContextIssuer,
    ActorType,
    AuthenticationDeniedError,
    AuthenticationThrottleKeys,
    AuthenticationThrottlePolicy,
    AuthenticationThrottleService,
    AuthenticationUnavailableError,
    DashboardAuthorizationPolicy,
    LdapAdapterTechnicalError,
    LdapAuthenticationService,
    LdapCredentialsRejectedError,
    LdapGroupGrant,
    LdapGroupRoleScopePolicy,
    LdapIdentityAssertion,
    PolicyAuthorizationService,
    SessionDeniedError,
    SessionPolicy,
    SessionService,
    SessionStatus,
    SessionUnavailableError,
    SQLiteAuthenticationThrottleRepository,
    SQLiteSessionRepository,
    is_trusted_actor_context,
)


NOW = datetime(2026, 7, 17, 9, 0, tzinfo=timezone.utc)
POLICY_VERSION = "LDAP_MAPPING_POLICY_V1"
CORRELATION_ID = "correlation-ldap-authentication"
SESSION_ID = "session-ldap-authentication"
CREDENTIAL = bytes((11, 22, 33, 44))
CLIENT_REFERENCE = "synthetic-client-reference"
THROTTLE_POLICY_VERSION = "LOGIN_THROTTLE_POLICY_V1"
THROTTLE_KEY_POLICY_VERSION = "LOGIN_THROTTLE_KEYS_V1"
SESSION_POLICY_VERSION = "SESSION_POLICY_V1"


@dataclass
class FakeLdapAdapter:
    outcome: LdapIdentityAssertion | Exception
    adapter_id: str = "synthetic-directory"

    def __post_init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def authenticate(self, *, principal: str, credential: bytes) -> LdapIdentityAssertion:
        self.calls.append((principal, len(credential)))
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class FailingAuditSink:
    def append(self, event: Any) -> None:
        raise RuntimeError("synthetic audit outage")


@dataclass
class FakeThrottleKeyProvider:
    version: str = THROTTLE_KEY_POLICY_VERSION

    def derive(self, *, principal: str, client_reference: str) -> AuthenticationThrottleKeys:
        return AuthenticationThrottleKeys(
            user_key=f"opaque-user-{len(principal)}",
            client_key=f"opaque-client-{len(client_reference)}",
        )


def test_fr_001_fr_003_bfr_iam_003_ldap_groups_issue_trusted_context() -> None:
    adapter = FakeLdapAdapter(_assertion(groups={"group-readers", "group-unmapped"}))
    service, audit = _service(adapter)

    context = _authenticate(service)

    assert is_trusted_actor_context(context)
    assert context.actor_id == "actor-subject-001"
    assert context.actor_type is ActorType.USER
    assert context.authentication_source == "LDAP:synthetic-directory"
    assert context.roles == frozenset({"DATA_VIEWER"})
    assert context.permitted_source_ids == frozenset({"source-a"})
    assert context.permitted_dataset_ids == frozenset({"dataset-a"})
    assert context.can_view_enterprise is False
    assert context.privileged is False
    assert context.policy_version == POLICY_VERSION
    assert adapter.calls == [("synthetic-principal", len(CREDENTIAL))]
    event = [event for event in audit.list_events() if event.action == "LDAP_AUTHENTICATION"][-1]
    assert event.result is AuditResult.SUCCESS
    assert event.reason_code == "LDAP_AUTHENTICATED"
    assert event.new_value_summary == {
        "mapping_policy_version": POLICY_VERSION,
        "mapped_role_count": 1,
        "mapped_source_count": 1,
        "mapped_dataset_count": 1,
        "can_view_enterprise": False,
        "throttle_policy_version": THROTTLE_POLICY_VERSION,
        "throttle_key_policy_version": THROTTLE_KEY_POLICY_VERSION,
        "failure_count": 0,
        "blocked": False,
        "blocked_scope_count": 0,
        "reason_code": "LDAP_AUTHENTICATED",
    }
    serialized = repr(event)
    assert "synthetic-principal" not in serialized
    assert "group-readers" not in serialized
    assert repr(CREDENTIAL) not in serialized
    assert SESSION_ID not in serialized
    with pytest.raises(FrozenInstanceError):
        context.roles = frozenset({"ADMIN"})  # type: ignore[misc]


def test_uc_001_bfr_iam_003_unmapped_group_produces_no_authority() -> None:
    adapter = FakeLdapAdapter(_assertion(groups={"group-unmapped"}))
    service, audit = _service(adapter)

    with pytest.raises(AuthenticationDeniedError) as error:
        _authenticate(service)

    assert error.value.reason_code == "LDAP_GROUP_NOT_MAPPED"
    assert audit.list_events()[-1].result is AuditResult.DENIED
    assert audit.list_events()[-1].actor_id == "actor-subject-001"


@pytest.mark.parametrize(
    ("adapter_error", "expected_error", "audit_result", "reason_code"),
    [
        (
            LdapCredentialsRejectedError(),
            AuthenticationDeniedError,
            AuditResult.DENIED,
            "CREDENTIALS_REJECTED",
        ),
        (
            LdapAdapterTechnicalError(),
            AuthenticationUnavailableError,
            AuditResult.FAILURE,
            "LDAP_TECHNICAL_ERROR",
        ),
        (
            RuntimeError("synthetic unexpected adapter error"),
            AuthenticationUnavailableError,
            AuditResult.FAILURE,
            "LDAP_UNEXPECTED_ERROR",
        ),
    ],
    ids=("credential-rejection", "technical-error", "unexpected-error"),
)
def test_fr_001_uc_001_bfr_iam_004_authentication_errors_fail_closed(
    adapter_error: Exception,
    expected_error: type[Exception],
    audit_result: AuditResult,
    reason_code: str,
) -> None:
    service, audit = _service(FakeLdapAdapter(adapter_error))

    with pytest.raises(expected_error):
        _authenticate(service)

    event = audit.list_events()[-1]
    assert event.result is audit_result
    assert event.reason_code == reason_code
    assert event.object_id is None


def test_uc_001_inactive_ldap_identity_is_denied_without_context() -> None:
    service, audit = _service(FakeLdapAdapter(_assertion(active=False)))

    with pytest.raises(AuthenticationDeniedError) as error:
        _authenticate(service)

    assert error.value.reason_code == "LDAP_IDENTITY_INACTIVE"
    assert audit.list_events()[-1].result is AuditResult.DENIED


def test_bfr_iam_006_service_account_is_separate_from_user_ldap_flow() -> None:
    service, audit = _service(FakeLdapAdapter(_assertion(actor_type=ActorType.SERVICE)))

    with pytest.raises(AuthenticationDeniedError) as error:
        _authenticate(service)

    assert error.value.reason_code == "LDAP_ACTOR_TYPE_NOT_ALLOWED"
    assert audit.list_events()[-1].actor_type == "SERVICE"


def test_bfr_iam_004_invalid_adapter_assertion_is_technical_failure() -> None:
    service, audit = _service(FakeLdapAdapter(_assertion(subject_id="")))

    with pytest.raises(AuthenticationUnavailableError):
        _authenticate(service)

    event = audit.list_events()[-1]
    assert event.result is AuditResult.FAILURE
    assert event.reason_code == "LDAP_INVALID_ASSERTION"


def test_br_rule_001_invalid_credential_input_does_not_call_adapter() -> None:
    adapter = FakeLdapAdapter(_assertion())
    service, audit = _service(adapter)

    with pytest.raises(AuthenticationDeniedError) as error:
        service.authenticate(
            principal="",
            credential=b"",
            client_reference="",
            correlation_id=CORRELATION_ID,
        )

    assert error.value.reason_code == "INVALID_CREDENTIAL_INPUT"
    assert adapter.calls == []
    assert audit.list_events()[-1].actor_id == "UNKNOWN"


def test_bfr_iam_004_authentication_audit_failure_returns_no_context() -> None:
    service = LdapAuthenticationService(
        FakeLdapAdapter(_assertion()),
        _policy(),
        FailingAuditSink(),
        _throttle(),
        FakeThrottleKeyProvider(),
        _sessions(FailingAuditSink()),
        clock=lambda: NOW,
    )

    with pytest.raises(AuthenticationUnavailableError) as error:
        _authenticate(service)

    assert error.value.correlation_id == CORRELATION_ID


def test_fr_002_ldap_context_connects_to_dashboard_authorization() -> None:
    service, audit = _service(FakeLdapAdapter(_assertion()))
    context = _authenticate(service)
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        _audit_service(audit),
        clock=lambda: NOW,
    )

    decision = authorization.authorize_dashboard(context)

    assert decision.permitted_source_ids == frozenset({"source-a"})
    assert decision.can_view_enterprise is False
    assert decision.policy_version == POLICY_VERSION


def test_bfr_iam_003_mapping_policy_is_immutable_and_validated() -> None:
    policy = _policy()

    with pytest.raises(TypeError):
        policy.group_grants["group-admin"] = LdapGroupGrant(  # type: ignore[index]
            roles=frozenset({"ADMIN"})
        )
    with pytest.raises(ActorContextValidationError, match="valid roles"):
        LdapAuthenticationService(
            FakeLdapAdapter(_assertion()),
            LdapGroupRoleScopePolicy(
                version=POLICY_VERSION,
                group_grants={"group-empty": LdapGroupGrant(roles=frozenset())},
            ),
            FailingAuditSink(),
            _throttle(),
            FakeThrottleKeyProvider(),
            _sessions(FailingAuditSink()),
            clock=lambda: NOW,
        )


def test_fr_006_nfr_sec_010_fifth_rejection_blocks_user_and_client() -> None:
    adapter = FakeLdapAdapter(LdapCredentialsRejectedError())
    service, audit = _service(adapter)

    for attempt in range(5):
        with pytest.raises(AuthenticationDeniedError) as error:
            _authenticate(service, correlation_id=f"rejection-{attempt}")
        assert error.value.reason_code == "CREDENTIALS_REJECTED"

    blocked_event = audit.list_events()[-1]
    assert blocked_event.new_value_summary["failure_count"] == 5
    assert blocked_event.new_value_summary["blocked"] is True
    assert blocked_event.new_value_summary["blocked_scope_count"] == 2

    with pytest.raises(AuthenticationDeniedError) as error:
        _authenticate(service, correlation_id="blocked-attempt")

    assert error.value.reason_code == "AUTHENTICATION_THROTTLED"
    assert len(adapter.calls) == 5
    assert audit.list_events()[-1].reason_code == "AUTHENTICATION_THROTTLED"


def test_fr_006_user_scope_blocks_same_user_from_a_different_client() -> None:
    adapter = FakeLdapAdapter(LdapCredentialsRejectedError())
    service, _ = _service(adapter)

    for attempt in range(5):
        with pytest.raises(AuthenticationDeniedError):
            _authenticate(service, correlation_id=f"user-scope-{attempt}")

    with pytest.raises(AuthenticationDeniedError) as error:
        _authenticate(
            service,
            client_reference="another-synthetic-client",
            correlation_id="user-scope-blocked",
        )

    assert error.value.reason_code == "AUTHENTICATION_THROTTLED"
    assert len(adapter.calls) == 5


def test_fr_006_client_scope_blocks_a_different_user_on_same_client() -> None:
    adapter = FakeLdapAdapter(LdapCredentialsRejectedError())
    service, _ = _service(adapter)

    for attempt in range(5):
        with pytest.raises(AuthenticationDeniedError):
            _authenticate(service, correlation_id=f"client-scope-{attempt}")

    with pytest.raises(AuthenticationDeniedError) as error:
        _authenticate(
            service,
            principal="another-synthetic-principal",
            correlation_id="client-scope-blocked",
        )

    assert error.value.reason_code == "AUTHENTICATION_THROTTLED"
    assert len(adapter.calls) == 5


def test_fr_006_success_resets_failure_counters() -> None:
    adapter = FakeLdapAdapter(LdapCredentialsRejectedError())
    service, _ = _service(adapter)
    for attempt in range(4):
        with pytest.raises(AuthenticationDeniedError):
            _authenticate(service, correlation_id=f"before-success-{attempt}")

    adapter.outcome = _assertion()
    _authenticate(service, correlation_id="successful-reset")
    adapter.outcome = LdapCredentialsRejectedError()

    with pytest.raises(AuthenticationDeniedError) as error:
        _authenticate(service, correlation_id="after-success")

    assert error.value.reason_code == "CREDENTIALS_REJECTED"


def test_fr_006_block_expires_after_configured_duration() -> None:
    current = [NOW]
    adapter = FakeLdapAdapter(LdapCredentialsRejectedError())
    service, _ = _service(adapter, clock=lambda: current[0])
    for attempt in range(5):
        with pytest.raises(AuthenticationDeniedError):
            _authenticate(service, correlation_id=f"expiry-{attempt}", now=current[0])

    current[0] += timedelta(minutes=15, seconds=1)
    adapter.outcome = _assertion(authenticated_at=current[0] - timedelta(seconds=1))

    context = _authenticate(service, correlation_id="after-expiry", now=current[0])

    assert context.actor_id == "actor-subject-001"


@pytest.mark.parametrize(
    "adapter_error",
    [LdapAdapterTechnicalError(), RuntimeError("synthetic LDAP outage")],
    ids=("ldap-technical", "ldap-unexpected"),
)
def test_fr_006_ldap_technical_failures_do_not_increment_counter(
    adapter_error: Exception,
) -> None:
    adapter = FakeLdapAdapter(adapter_error)
    service, audit = _service(adapter)

    for attempt in range(6):
        with pytest.raises(AuthenticationUnavailableError):
            _authenticate(service, correlation_id=f"technical-{attempt}")

    assert len(adapter.calls) == 6
    assert all(event.new_value_summary["failure_count"] == 0 for event in audit.list_events())


def test_fr_006_throttle_state_survives_repository_reopen(tmp_path: Path) -> None:
    database = str(tmp_path / "synthetic-throttle.sqlite")
    keys = AuthenticationThrottleKeys("opaque-user-key", "opaque-client-key")
    first = SQLiteAuthenticationThrottleRepository(database)
    service = AuthenticationThrottleService(first, _throttle_policy())
    for _ in range(5):
        decision = service.record_failure(keys, NOW)
    first.connection.close()

    reopened = AuthenticationThrottleService(
        SQLiteAuthenticationThrottleRepository(database), _throttle_policy()
    )

    assert decision.blocked is True
    assert reopened.evaluate(keys, NOW).blocked is True


def test_fr_006_configured_stricter_threshold_is_applied() -> None:
    policy = AuthenticationThrottlePolicy(
        version="stricter-synthetic-policy",
        max_failures=3,
        failure_window=timedelta(minutes=10),
        block_duration=timedelta(minutes=20),
    )
    service = AuthenticationThrottleService(SQLiteAuthenticationThrottleRepository(), policy)
    keys = AuthenticationThrottleKeys("opaque-user-key", "opaque-client-key")

    assert service.record_failure(keys, NOW).blocked is False
    assert service.record_failure(keys, NOW).blocked is False
    assert service.record_failure(keys, NOW).blocked is True


def test_fr_006_unblocked_failure_window_expires_before_next_attempt() -> None:
    service = _throttle()
    keys = AuthenticationThrottleKeys("opaque-user-key", "opaque-client-key")
    for _ in range(4):
        assert service.record_failure(keys, NOW).blocked is False

    later = NOW + timedelta(minutes=15)
    assert service.evaluate(keys, later).failure_count == 0
    assert service.record_failure(keys, later).failure_count == 1


def test_fr_006_throttle_storage_contains_only_opaque_keys() -> None:
    repository = SQLiteAuthenticationThrottleRepository()
    adapter = FakeLdapAdapter(LdapCredentialsRejectedError())
    service, audit = _service(adapter, throttle_repository=repository)

    with pytest.raises(AuthenticationDeniedError):
        _authenticate(service)

    stored = repr(
        repository.connection.execute("SELECT * FROM authentication_throttle_states").fetchall()
    )
    serialized_audit = repr(audit.list_events())
    for sensitive in ("synthetic-principal", CLIENT_REFERENCE, repr(CREDENTIAL)):
        assert sensitive not in stored
        assert sensitive not in serialized_audit


def test_fr_006_throttle_repository_failure_denies_before_ldap() -> None:
    repository = SQLiteAuthenticationThrottleRepository()
    repository.connection.close()
    adapter = FakeLdapAdapter(_assertion())
    service, audit = _service(adapter, throttle_repository=repository)

    with pytest.raises(AuthenticationUnavailableError):
        _authenticate(service)

    assert adapter.calls == []
    event = audit.list_events()[-1]
    assert event.result is AuditResult.FAILURE
    assert event.reason_code == "THROTTLE_TECHNICAL_ERROR"


def test_nfr_sec_010_policy_rejects_weaker_threshold_or_duration() -> None:
    with pytest.raises(ActorContextValidationError, match="between one and five"):
        AuthenticationThrottlePolicy(
            version="invalid-threshold",
            max_failures=6,
            failure_window=timedelta(minutes=15),
            block_duration=timedelta(minutes=15),
        )
    with pytest.raises(ActorContextValidationError, match="at least fifteen"):
        AuthenticationThrottlePolicy(
            version="invalid-duration",
            max_failures=5,
            failure_window=timedelta(minutes=15),
            block_duration=timedelta(minutes=14),
        )


def test_fr_001_fr_005_ac_001_ldap_login_creates_data_minimum_session() -> None:
    service, audit = _service(FakeLdapAdapter(_assertion()))

    started_at = perf_counter()
    grant = service.authenticate(
        principal="synthetic-principal",
        credential=CREDENTIAL,
        client_reference=CLIENT_REFERENCE,
        correlation_id="session-login",
    )

    assert perf_counter() - started_at < 5
    assert len(grant.credential) >= 32
    assert is_trusted_actor_context(grant.context)
    assert grant.context.expires_at == NOW + timedelta(hours=8)
    assert [event.action for event in audit.list_events()[-2:]] == [
        "LDAP_AUTHENTICATION",
        "IDENTITY_SESSION",
    ]
    serialized = repr(audit.list_events())
    assert repr(grant.credential) not in serialized
    assert grant.context.session_id not in serialized


def test_fr_005_session_validation_refreshes_last_activity() -> None:
    current = [NOW]
    audit = SQLiteAuditRepository()
    service = _sessions(_audit_service(audit), clock=lambda: current[0])
    grant = _open_session(service)
    current[0] += timedelta(minutes=20)

    context = service.validate(grant.credential, "session-validation")

    assert is_trusted_actor_context(context)
    assert context.correlation_id == "session-validation"
    current[0] += timedelta(minutes=20)
    assert service.validate(grant.credential, "session-refreshed").session_id == context.session_id


def test_fr_005_nfr_sec_009_idle_timeout_denies_at_thirty_minutes() -> None:
    current = [NOW]
    audit = SQLiteAuditRepository()
    repository = SQLiteSessionRepository()
    service = _sessions(_audit_service(audit), repository=repository, clock=lambda: current[0])
    grant = _open_session(service)
    current[0] += timedelta(minutes=30)

    with pytest.raises(SessionDeniedError) as error:
        service.validate(grant.credential, "idle-timeout")

    assert error.value.reason_code == "SESSION_IDLE_TIMEOUT"
    row = repository.connection.execute("SELECT status FROM identity_sessions").fetchone()
    assert row["status"] == SessionStatus.EXPIRED.value
    assert audit.list_events()[-1].reason_code == "SESSION_IDLE_TIMEOUT"


def test_fr_005_configured_stricter_idle_timeout_is_applied() -> None:
    current = [NOW]
    policy = SessionPolicy(
        version="stricter-session-policy",
        idle_timeout=timedelta(minutes=10),
        absolute_timeout=timedelta(hours=2),
    )
    service = SessionService(
        SQLiteSessionRepository(),
        policy,
        _audit_service(SQLiteAuditRepository()),
        clock=lambda: current[0],
    )
    grant = _open_session(service)
    current[0] += timedelta(minutes=10)

    with pytest.raises(SessionDeniedError, match="Session denied"):
        service.validate(grant.credential, "stricter-idle-timeout")


def test_fr_005_absolute_timeout_cannot_be_extended_by_activity() -> None:
    current = [NOW]
    policy = SessionPolicy(
        version="short-absolute-session-policy",
        idle_timeout=timedelta(minutes=10),
        absolute_timeout=timedelta(minutes=25),
    )
    service = SessionService(
        SQLiteSessionRepository(),
        policy,
        _audit_service(SQLiteAuditRepository()),
        clock=lambda: current[0],
    )
    grant = _open_session(service)
    current[0] += timedelta(minutes=9)
    service.validate(grant.credential, "activity-one")
    current[0] += timedelta(minutes=9)
    service.validate(grant.credential, "activity-two")
    current[0] = NOW + timedelta(minutes=25)

    with pytest.raises(SessionDeniedError) as error:
        service.validate(grant.credential, "absolute-timeout")

    assert error.value.reason_code == "SESSION_ABSOLUTE_TIMEOUT"


def test_fr_005_logout_revokes_credential_and_is_idempotent() -> None:
    audit = SQLiteAuditRepository()
    service = _sessions(_audit_service(audit))
    grant = _open_session(service)

    service.logout(grant.credential, "first-logout")
    service.logout(grant.credential, "second-logout")

    with pytest.raises(SessionDeniedError) as error:
        service.validate(grant.credential, "reuse-after-logout")
    assert error.value.reason_code == "SESSION_NOT_ACTIVE"
    assert [event.reason_code for event in audit.list_events()[-3:]] == [
        "SESSION_REVOKED",
        "SESSION_ALREADY_INACTIVE",
        "SESSION_NOT_ACTIVE",
    ]


def test_fr_005_changed_or_unknown_credential_is_generically_denied() -> None:
    audit = SQLiteAuditRepository()
    service = _sessions(_audit_service(audit))
    grant = _open_session(service)
    changed = bytes(value ^ 1 for value in grant.credential)

    with pytest.raises(SessionDeniedError) as error:
        service.validate(changed, "changed-session-credential")

    assert str(error.value) == "Session denied."
    assert error.value.reason_code == "SESSION_NOT_FOUND"
    assert audit.list_events()[-1].actor_id == "UNKNOWN"
    assert repr(changed) not in repr(audit.list_events())


def test_fr_005_session_state_survives_repository_reopen(tmp_path: Path) -> None:
    database = str(tmp_path / "synthetic-sessions.sqlite")
    first_repository = SQLiteSessionRepository(database)
    first = _sessions(_audit_service(SQLiteAuditRepository()), repository=first_repository)
    grant = _open_session(first)
    first_repository.connection.close()

    reopened = _sessions(
        _audit_service(SQLiteAuditRepository()),
        repository=SQLiteSessionRepository(database),
    )

    assert (
        reopened.validate(grant.credential, "reopened-session").actor_id == grant.context.actor_id
    )


def test_fr_005_session_repository_failure_is_audited_and_fail_closed() -> None:
    audit = SQLiteAuditRepository()
    repository = SQLiteSessionRepository()
    repository.connection.close()
    service = _sessions(_audit_service(audit), repository=repository)

    with pytest.raises(SessionUnavailableError):
        service.validate(bytes(range(32)), "session-store-failure")

    event = audit.list_events()[-1]
    assert event.result is AuditResult.FAILURE
    assert event.reason_code == "SESSION_TECHNICAL_ERROR"


def test_fr_001_fr_005_ldap_returns_no_grant_when_session_store_fails() -> None:
    repository = SQLiteSessionRepository()
    repository.connection.close()
    adapter = FakeLdapAdapter(_assertion())
    service, audit = _service(adapter, session_repository=repository)

    with pytest.raises(AuthenticationUnavailableError):
        _authenticate(service, correlation_id="ldap-session-store-failure")

    assert len(adapter.calls) == 1
    event = audit.list_events()[-1]
    assert event.result is AuditResult.FAILURE
    assert event.reason_code == "SESSION_TECHNICAL_ERROR"


def test_fr_005_session_creation_audit_failure_revokes_persisted_session() -> None:
    repository = SQLiteSessionRepository()
    service = _sessions(FailingAuditSink(), repository=repository)

    with pytest.raises(SessionUnavailableError):
        _open_session(service)

    row = repository.connection.execute(
        "SELECT status, revocation_reason FROM identity_sessions"
    ).fetchone()
    assert row["status"] == SessionStatus.REVOKED.value
    assert row["revocation_reason"] == "SESSION_CREATION_AUDIT_FAILED"


@pytest.mark.parametrize(
    ("actor_type", "privileged"),
    [(ActorType.SERVICE, False), (ActorType.USER, True)],
    ids=("service-account", "privileged-user"),
)
def test_fr_005_user_session_rejects_service_or_privileged_context(
    actor_type: ActorType, privileged: bool
) -> None:
    service = _sessions(_audit_service(SQLiteAuditRepository()))

    with pytest.raises(ActorContextValidationError, match="non-privileged user"):
        _open_session(service, actor_type=actor_type, privileged=privileged)


def test_fr_005_session_rejects_untrusted_authentication_context() -> None:
    service = _sessions(_audit_service(SQLiteAuditRepository()))

    with pytest.raises(ActorContextValidationError, match="Trusted authentication"):
        service.open_authenticated_session(  # type: ignore[arg-type]
            authenticated_context=None,
            correlation_id="untrusted-session-open",
        )


def test_fr_005_session_rejects_expired_trusted_authentication_context() -> None:
    service = _sessions(_audit_service(SQLiteAuditRepository()))
    expired = ActorContextIssuer().issue(
        actor_id="actor-subject-001",
        actor_type=ActorType.USER,
        authentication_source="LDAP:synthetic-directory",
        session_id="expired-pre-session",
        roles=frozenset({"DATA_VIEWER"}),
        permitted_source_ids=frozenset({"source-a"}),
        permitted_dataset_ids=frozenset({"dataset-a"}),
        can_view_enterprise=False,
        privileged=False,
        issued_at=NOW - timedelta(minutes=2),
        expires_at=NOW - timedelta(minutes=1),
        policy_version=POLICY_VERSION,
        correlation_id="expired-session-open",
    )

    with pytest.raises(ActorContextValidationError, match="not currently valid"):
        service.open_authenticated_session(
            authenticated_context=expired,
            correlation_id="expired-session-open",
        )


def test_nfr_sec_005_session_repository_never_stores_raw_credential() -> None:
    repository = SQLiteSessionRepository()
    service = _sessions(_audit_service(SQLiteAuditRepository()), repository=repository)

    grant = _open_session(service)

    row = repository.connection.execute(
        "SELECT credential_digest FROM identity_sessions"
    ).fetchone()
    assert len(row["credential_digest"]) == 64
    assert row["credential_digest"] != grant.credential.hex()
    assert repr(grant.credential) not in repr(grant)


def test_nfr_sec_009_session_policy_rejects_weak_or_incoherent_timeouts() -> None:
    with pytest.raises(ActorContextValidationError, match="at most thirty"):
        SessionPolicy(
            version="weak-idle-policy",
            idle_timeout=timedelta(minutes=31),
            absolute_timeout=timedelta(hours=8),
        )
    with pytest.raises(ActorContextValidationError, match="must exceed"):
        SessionPolicy(
            version="invalid-absolute-policy",
            idle_timeout=timedelta(minutes=30),
            absolute_timeout=timedelta(minutes=30),
        )


def _assertion(
    *,
    subject_id: str = "actor-subject-001",
    groups: set[str] | None = None,
    actor_type: ActorType = ActorType.USER,
    active: bool = True,
    authenticated_at: datetime = NOW - timedelta(seconds=1),
) -> LdapIdentityAssertion:
    return LdapIdentityAssertion(
        subject_id=subject_id,
        group_ids=frozenset(groups or {"group-readers"}),
        actor_type=actor_type,
        active=active,
        authenticated_at=authenticated_at,
    )


def _policy() -> LdapGroupRoleScopePolicy:
    return LdapGroupRoleScopePolicy(
        version=POLICY_VERSION,
        group_grants={
            "group-readers": LdapGroupGrant(
                roles=frozenset({"DATA_VIEWER"}),
                permitted_source_ids=frozenset({"source-a"}),
                permitted_dataset_ids=frozenset({"dataset-a"}),
            )
        },
    )


def _service(
    adapter: FakeLdapAdapter,
    *,
    clock: Any = lambda: NOW,
    throttle_repository: SQLiteAuthenticationThrottleRepository | None = None,
    session_repository: SQLiteSessionRepository | None = None,
) -> tuple[LdapAuthenticationService, SQLiteAuditRepository]:
    audit = SQLiteAuditRepository()
    audit_service = _audit_service(audit)
    return (
        LdapAuthenticationService(
            adapter,
            _policy(),
            audit_service,
            _throttle(throttle_repository),
            FakeThrottleKeyProvider(),
            _sessions(audit_service, repository=session_repository, clock=clock),
            clock=clock,
        ),
        audit,
    )


def _throttle_policy() -> AuthenticationThrottlePolicy:
    return AuthenticationThrottlePolicy(
        version=THROTTLE_POLICY_VERSION,
        max_failures=5,
        failure_window=timedelta(minutes=15),
        block_duration=timedelta(minutes=15),
    )


def _throttle(
    repository: SQLiteAuthenticationThrottleRepository | None = None,
) -> AuthenticationThrottleService:
    return AuthenticationThrottleService(
        repository or SQLiteAuthenticationThrottleRepository(),
        _throttle_policy(),
    )


def _session_policy() -> SessionPolicy:
    return SessionPolicy(
        version=SESSION_POLICY_VERSION,
        idle_timeout=timedelta(minutes=30),
        absolute_timeout=timedelta(hours=8),
    )


def _sessions(
    audit_sink: Any,
    *,
    repository: SQLiteSessionRepository | None = None,
    clock: Any = lambda: NOW,
) -> SessionService:
    return SessionService(
        repository or SQLiteSessionRepository(),
        _session_policy(),
        audit_sink,
        clock=clock,
    )


def _open_session(
    service: SessionService,
    *,
    actor_type: ActorType = ActorType.USER,
    privileged: bool = False,
) -> Any:
    context = ActorContextIssuer().issue(
        actor_id="actor-subject-001",
        actor_type=actor_type,
        authentication_source="LDAP:synthetic-directory",
        session_id="pre-session-authentication",
        roles=frozenset({"DATA_VIEWER"}),
        permitted_source_ids=frozenset({"source-a"}),
        permitted_dataset_ids=frozenset({"dataset-a"}),
        can_view_enterprise=False,
        privileged=privileged,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=1),
        policy_version=POLICY_VERSION,
        correlation_id="session-open",
    )
    return service.open_authenticated_session(
        authenticated_context=context,
        correlation_id="session-open",
    )


def _audit_service(repository: SQLiteAuditRepository) -> AuditService:
    return AuditService(
        repository,
        AuditRedactor(build_default_redaction_policy()),
        AuditFailurePolicy(
            version="LDAP_AUDIT_FAILURE_POLICY_V1",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )


def _authenticate(
    service: LdapAuthenticationService,
    *,
    principal: str = "synthetic-principal",
    client_reference: str = CLIENT_REFERENCE,
    correlation_id: str = CORRELATION_ID,
    now: datetime = NOW,
) -> Any:
    grant = service.authenticate(
        principal=principal,
        credential=CREDENTIAL,
        client_reference=client_reference,
        correlation_id=correlation_id,
    )
    return grant.context
