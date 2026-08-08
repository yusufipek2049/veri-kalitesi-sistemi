"""FR-007/FR-008/FR-010: S1 veri kaynağı komut authorization sınırı."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from starlette.requests import Request

from veri_kalitesi.audit.models import (
    AuditEventInput,
    AuditFailureMode,
    AuditFailurePolicy,
)
from veri_kalitesi.audit.outbox import SQLiteTransactionalAudit
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.audit.service import AuditService
from veri_kalitesi.api.data_source_commands import (
    DataSourceCommandAdapter,
    DataSourceCommandError,
)
from veri_kalitesi.api.identity import (
    DevelopmentActorContextResolver,
    DevelopmentUser,
    DevelopmentUserRegistry,
)
from veri_kalitesi.data_sources.connectors import ConnectorRegistry
from veri_kalitesi.data_sources.models import (
    DataSource,
    DataSourceActivationRequest,
    DataSourceCommandPolicy,
    DataSourceStatus,
    SourceType,
)
from veri_kalitesi.data_sources.query import (
    DataSourceQueryService,
    DataSourceView,
)
from veri_kalitesi.data_sources.repository import SQLiteDataSourceRepository
from veri_kalitesi.data_sources.service import DataSourceService
from veri_kalitesi.data_sources.errors import AuthorizationError
from veri_kalitesi.data_sources.query import DataSourceQueryTechnicalError
from veri_kalitesi.identity import (
    ActorContextIssuer,
    ActorType,
    DashboardAuthorizationPolicy,
    PolicyAuthorizationService,
)

NOW = datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc)
ACTOR_POLICY = "S1_ACTOR_POLICY_V1"


def _service() -> DataSourceService:
    repository = SQLiteDataSourceRepository()
    ledger = SQLiteAuditRepository()
    redactor = AuditRedactor(build_default_redaction_policy())
    audit = AuditService(
        ledger,
        redactor,
        AuditFailurePolicy("S1_AUDIT_FAILURE_V1", AuditFailureMode.FAIL_CLOSED),
    )
    outbox = SQLiteTransactionalAudit(
        repository.connection,
        redactor,
        ledger,
        policy_version="S1_OUTBOX_V1",
    )
    return DataSourceService(
        repository,
        ConnectorRegistry([]),
        audit_sink=audit,
        transactional_audit=outbox,
        activation_policy=DataSourceCommandPolicy(
            version="S1_COMMAND_POLICY_V1",
            actor_policy_version=ACTOR_POLICY,
            creator_roles=frozenset({"DATA_STEWARD", "DATA_OWNER"}),
            connection_tester_roles=frozenset({"DATA_STEWARD"}),
            maker_roles=frozenset({"DATA_STEWARD"}),
            checker_roles=frozenset({"DATA_OWNER"}),
            deactivator_roles=frozenset({"DATA_OWNER"}),
        ),
        enforce_command_authorization=True,
        clock=lambda: NOW,
    )


def _context(
    actor_id: str,
    roles: set[str],
    *,
    sources: set[str] | None = None,
    enterprise: bool = False,
    policy_version: str = ACTOR_POLICY,
):
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=ActorType.USER,
        authentication_source="test-issuer",
        session_id=f"session-{actor_id}",
        roles=frozenset(roles),
        permitted_source_ids=frozenset(sources or set()),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=enterprise,
        privileged=False,
        issued_at=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(minutes=10),
        policy_version=policy_version,
        correlation_id=f"correlation-{actor_id}",
    )


def test_fr_007_create_requires_trusted_role_and_enterprise_scope() -> None:
    service = _service()
    with pytest.raises(AuthorizationError):
        service.create_data_source(
            actor_context=_context("steward-a", {"DATA_STEWARD"}),
            name="Source A",
            source_type="POSTGRESQL",
            connection_config={
                "host": "db.internal",
                "port": 5432,
                "database": "analytics",
                "schema": "public",
                "ssl_mode": "verify-full",
            },
            secret_reference="secret://local/source-a",
        )


def test_fr_007_create_derives_owner_from_trusted_actor() -> None:
    service = _service()
    source = service.create_data_source(
        actor_context=_context("steward-a", {"DATA_STEWARD"}, enterprise=True),
        name="Source A",
        source_type="POSTGRESQL",
        connection_config={
            "host": "db.internal",
            "port": 5432,
            "database": "analytics",
            "schema": "public",
            "ssl_mode": "verify-full",
        },
        secret_reference="secret://local/source-a",
        owner_user_id="untrusted-client-owner",
    )
    assert source.owner_user_id == "steward-a"


def test_fr_008_connection_test_denies_out_of_scope_before_connector() -> None:
    service = _service()
    source = service.create_data_source(
        actor_context=_context("steward-a", {"DATA_STEWARD"}, enterprise=True),
        name="Source A",
        source_type="POSTGRESQL",
        connection_config={
            "host": "db.internal",
            "port": 5432,
            "database": "analytics",
            "schema": "public",
            "ssl_mode": "verify-full",
        },
        secret_reference="secret://local/source-a",
    )
    with pytest.raises(AuthorizationError, match="outside"):
        service.test_connection(
            actor_context=_context("steward-b", {"DATA_STEWARD"}),
            data_source_id=source.data_source_id,
        )


def test_fr_007_command_policy_version_mismatch_fails_closed() -> None:
    service = _service()
    with pytest.raises(AuthorizationError, match="policy version"):
        service.create_data_source(
            actor_context=_context(
                "steward-a",
                {"DATA_STEWARD"},
                enterprise=True,
                policy_version="STALE_POLICY",
            ),
            name="Source A",
            source_type="POSTGRESQL",
            connection_config={
                "host": "db.internal",
                "port": 5432,
                "database": "analytics",
                "schema": "public",
                "ssl_mode": "verify-full",
            },
            secret_reference="secret://local/source-a",
        )


class _DeniedDecisionService:
    class _Repository:
        @staticmethod
        def get_activation_request(activation_request_id: str) -> DataSourceActivationRequest:
            return DataSourceActivationRequest(
                activation_request_id=activation_request_id,
                data_source_id="source-a",
                data_source_revision=1,
                maker_actor_id="maker-a",
                policy_version="S1_COMMAND_POLICY_V1",
            )

    repository = _Repository()

    def decide_activation(self, **values):  # type: ignore[no-untyped-def]
        del values
        raise AuthorizationError(
            "maker checker denied",
            code="DATA_SOURCE_MAKER_CHECKER_VIOLATION",
        )


class _CollectingAuditSink:
    def __init__(self) -> None:
        self.events: list[AuditEventInput] = []

    def append(self, event: AuditEventInput):  # type: ignore[no-untyped-def]
        self.events.append(event)
        return None


def test_fr_010_maker_checker_denial_writes_separate_security_audit() -> None:
    audit = _CollectingAuditSink()
    adapter = DataSourceCommandAdapter(
        _DeniedDecisionService(),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        audit,
    )
    with pytest.raises(DataSourceCommandError) as error:
        adapter.decide_activation(
            activation_request_id="request-a",
            decision="APPROVE",
            reason_code="VALIDATED",
            actor_context=_context(
                "maker-a",
                {"DATA_STEWARD", "DATA_OWNER"},
                sources={"source-a"},
            ),
        )
    assert error.value.code == "DATA_SOURCE_MAKER_CHECKER_VIOLATION"
    assert len(audit.events) == 1
    assert audit.events[0].action == "DATA_SOURCE_ACTIVATION_DECISION_DENIED"
    assert audit.events[0].reason_code == "MAKER_CHECKER_VIOLATION"
    assert audit.events[0].object_id == "request-a"


class _CapturingCreateService:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def create_data_source(self, **values):  # type: ignore[no-untyped-def]
        self.values = values
        return DataSource(
            data_source_id="source-created",
            name=str(values["name"]),
            source_type=SourceType.POSTGRESQL,
            connection_config=dict(values["connection_config"]),
            secret_reference=str(values["secret_reference"]),
            owner_user_id="steward-a",
        )


class _CreatedSourceQuery:
    @staticmethod
    def get_view_for_actor(data_source_id, context):  # type: ignore[no-untyped-def]
        del context
        return DataSourceView(
            DataSource(
                data_source_id=data_source_id,
                name="Created Source",
                source_type=SourceType.POSTGRESQL,
                connection_config={},
                secret_reference="secret://local/source-a",
            )
        )


def test_command_adapter_shapes_create_payload_without_allowing_reserved_overrides() -> None:
    service = _CapturingCreateService()
    adapter = DataSourceCommandAdapter(
        service,  # type: ignore[arg-type]
        _CreatedSourceQuery(),  # type: ignore[arg-type]
        _CollectingAuditSink(),
    )
    context = _context("steward-a", {"DATA_STEWARD"}, enterprise=True)

    result = adapter.create(
        payload=SimpleNamespace(
            name="Created Source",
            source_type="POSTGRESQL",
            host="db.internal",
            port=5432,
            database="analytics",
            schema_name="dq",
            secret_reference="secret://local/source-a",
            ssl_mode="verify-full",
            connect_timeout_seconds=5,
            statement_timeout_ms=5000,
            connection_parameters={
                "host": "attacker.invalid",
                "ssl_mode": "disable",
                "ssl_root_cert": "/run/certs/root.crt",
            },
        ),
        actor_context=context,
    )

    config = service.values["connection_config"]
    assert isinstance(config, dict)
    assert config["host"] == "db.internal"
    assert config["ssl_mode"] == "verify-full"
    assert config["ssl_root_cert"] == "/run/certs/root.crt"
    assert service.values["secret_reference"] == "secret://local/source-a"
    assert service.values["actor_context"] is context
    assert result.view.source.data_source_id == "source-created"


def test_command_adapter_maps_mutation_reread_failure_to_structured_503_code() -> None:
    class _UnavailableQuery:
        @staticmethod
        def get_view_for_actor(data_source_id, context):  # type: ignore[no-untyped-def]
            del data_source_id
            raise DataSourceQueryTechnicalError("query unavailable", context.correlation_id)

    adapter = DataSourceCommandAdapter(
        _CapturingCreateService(),  # type: ignore[arg-type]
        _UnavailableQuery(),  # type: ignore[arg-type]
        _CollectingAuditSink(),
    )

    with pytest.raises(DataSourceCommandError) as error:
        adapter.create(
            payload=SimpleNamespace(
                name="Created Source",
                source_type="POSTGRESQL",
                host="db.internal",
                port=5432,
                database="analytics",
                schema_name="dq",
                secret_reference="secret://local/source-a",
                ssl_mode="verify-full",
                connect_timeout_seconds=5,
                statement_timeout_ms=5000,
                connection_parameters={},
            ),
            actor_context=_context("steward-a", {"DATA_STEWARD"}, enterprise=True),
        )

    assert error.value.category == "technical"
    assert error.value.code == "DATA_SOURCE_PERSISTENCE_UNAVAILABLE"


def test_development_enterprise_identity_refreshes_explicit_source_scope() -> None:
    registry = DevelopmentUserRegistry(
        [
            DevelopmentUser(
                user_id="enterprise-steward",
                display_name="Enterprise Steward",
                roles=frozenset({"DATA_STEWARD"}),
                permitted_source_ids=frozenset({"source-existing"}),
                permitted_dataset_ids=frozenset(),
                can_view_enterprise=True,
            ),
            DevelopmentUser(
                user_id="limited-steward",
                display_name="Limited Steward",
                roles=frozenset({"DATA_STEWARD"}),
                permitted_source_ids=frozenset({"source-existing"}),
                permitted_dataset_ids=frozenset(),
                can_view_enterprise=False,
            ),
        ]
    )
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=ACTOR_POLICY,
        permitted_source_ids=frozenset(),
        can_view_enterprise=False,
        user_registry=registry,
        clock=lambda: NOW,
    )
    resolver.bind_enterprise_source_scope_provider(
        lambda: frozenset({"source-existing", "source-new"})
    )

    enterprise_request = Request(
        {
            "type": "http",
            "headers": [(b"x-development-user-id", b"enterprise-steward")],
        }
    )
    enterprise_request.state.correlation_id = "correlation-enterprise"
    limited_request = Request(
        {
            "type": "http",
            "headers": [(b"x-development-user-id", b"limited-steward")],
        }
    )
    limited_request.state.correlation_id = "correlation-limited"

    assert resolver.resolve(enterprise_request).permitted_source_ids == frozenset(
        {"source-existing", "source-new"}
    )
    assert resolver.resolve(limited_request).permitted_source_ids == frozenset({"source-existing"})


class _ProjectionReader:
    def __init__(
        self,
        sources: tuple[DataSource, ...],
        pending: DataSourceActivationRequest | None = None,
    ) -> None:
        self.sources = sources
        self.pending = pending

    def get_data_source(self, data_source_id: str) -> DataSource:
        return next(source for source in self.sources if source.data_source_id == data_source_id)

    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]:
        return [source for source in self.sources if source.data_source_id in allowed_source_ids]

    def list_all_data_sources(self) -> list[DataSource]:
        return list(self.sources)

    def latest_pending_activation_request(
        self, data_source_id: str
    ) -> DataSourceActivationRequest | None:
        if self.pending is not None and self.pending.data_source_id == data_source_id:
            return self.pending
        return None


def _projection_service(
    source: DataSource,
    pending: DataSourceActivationRequest | None = None,
) -> DataSourceQueryService:
    domain_service = _service()
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=ACTOR_POLICY),
        domain_service.audit_sink,
        clock=lambda: NOW,
    )
    return DataSourceQueryService(
        _ProjectionReader((source,), pending),
        authorization,
        domain_service.activation_policy,
        clock=lambda: NOW,
    )


def test_backend_projection_hides_checker_actions_from_request_maker() -> None:
    source = DataSource(
        data_source_id="source-a",
        name="Source A",
        source_type=SourceType.POSTGRESQL,
        connection_config={},
        secret_reference="secret://local/source-a",
        status=DataSourceStatus.TEST_SUCCEEDED,
    )
    pending = DataSourceActivationRequest(
        activation_request_id="request-a",
        data_source_id=source.data_source_id,
        data_source_revision=source.revision,
        maker_actor_id="maker-a",
        policy_version="S1_COMMAND_POLICY_V1",
    )
    query = _projection_service(source, pending)

    maker_view = query.get_view_for_actor(
        source.data_source_id,
        _context(
            "maker-a",
            {"DATA_STEWARD", "DATA_OWNER"},
            sources={source.data_source_id},
        ),
    )
    checker_view = query.get_view_for_actor(
        source.data_source_id,
        _context("owner-b", {"DATA_OWNER"}, sources={source.data_source_id}),
    )

    assert maker_view.available_actions == ("TEST_CONNECTION",)
    assert checker_view.available_actions == (
        "APPROVE_ACTIVATION",
        "REJECT_ACTIVATION",
    )
    assert checker_view.pending_activation_request is pending


def test_backend_projection_requires_role_scope_and_active_state_for_passivation() -> None:
    source = DataSource(
        data_source_id="source-active",
        name="Active Source",
        source_type=SourceType.POSTGRESQL,
        connection_config={},
        secret_reference="secret://local/source-active",
        status=DataSourceStatus.ACTIVE,
    )
    query = _projection_service(source)

    owner_view = query.get_view_for_actor(
        source.data_source_id,
        _context("owner-a", {"DATA_OWNER"}, sources={source.data_source_id}),
    )
    enterprise_without_explicit_scope = query.get_view_for_actor(
        source.data_source_id,
        _context("owner-b", {"DATA_OWNER"}, enterprise=True),
    )

    assert owner_view.available_actions == ("PASSIVATE",)
    assert enterprise_without_explicit_scope.available_actions == ()
