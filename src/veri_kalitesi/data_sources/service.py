"""Veri kaynağı uygulama servisi."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar
from uuid import uuid4

from veri_kalitesi.audit.models import (
    AuditEventInput,
    AuditResult,
)
from veri_kalitesi.audit.service import AuditSink
from veri_kalitesi.data_protection import (
    ClassificationValidationError,
    ClassificationPolicy,
    ClassificationCode,
    DataProcessingInventory,
    DefaultClassificationPolicy,
    DefaultMaskingPolicy,
    InventoryCoverageReport,
    InventoryCoverageStatus,
    MaskingPolicy,
    InventoryValidationError,
    validate_inventory,
)
from veri_kalitesi.data_sources.connectors import ConnectorRegistry
from veri_kalitesi.data_sources.errors import (
    AuthorizationError,
    ConflictError,
    SecretResolutionError,
    TechnicalError,
    ValidationError,
)
from veri_kalitesi.data_sources.models import (
    ConnectionTestResult,
    ConnectionRevisionStatus,
    DataField,
    DataProfile,
    DataSource,
    DataSourceActivationPolicy,
    DataSourceActivationRequest,
    DataSourceActivationStatus,
    DataSourceConnectionRevision,
    DataSourceStatus,
    Dataset,
    DatasetType,
    DiscoveryScope,
    DiscoveryStatus,
    ErrorClass,
    MetadataChange,
    MetadataChangeType,
    MetadataDiff,
    MetadataDiffStatus,
    MetadataDiscoveryOptions,
    MetadataDiscoveryResult,
    ProfileMethod,
    ProfileComparison,
    ProfileComparisonStatus,
    ProfileOptions,
    ProfileStatus,
    utc_now,
)
from veri_kalitesi.data_sources.profiling import (
    ProfilePolicyResolver,
    build_profile_contract,
    compare_profile_snapshots,
    validate_freshness_field_scope,
)
from veri_kalitesi.identity import ActorContext, ActorType, is_trusted_actor_context
from veri_kalitesi.data_sources.contracts import DataSourceRepository, DataSourceTransactionalAudit
from veri_kalitesi.data_sources.secrets import EmptySecretResolver, SecretResolver
from veri_kalitesi.data_sources.postgresql import (
    AuthenticationConnectionError,
    DNSConnectionError,
    DriverConnectionError,
    NetworkConnectionError,
    PermissionConnectionError,
    TLSConnectionError,
    TimeoutConnectionError,
)

from veri_kalitesi.data_sources.validation import (
    BusinessCalendar,
    validate_discovery_pattern,
    _error_reason,
    _parse_activation_decision,
    _parse_source_type,
    _require_aware_time,
    _resolve_correlation_id,
    _validate_activation_calendar,
    _validate_activation_policy,
    _validate_connection_config,
    _validate_metadata_options,
    _validate_name,
    _validate_profile_field_selection,
    _validate_profile_options,
    _validate_secret_reference,
)

_RepoT = TypeVar("_RepoT", bound=DataSourceTransactionalAudit)


class DataSourceService:
    def __init__(
        self,
        repository: DataSourceRepository[_RepoT],
        registry: ConnectorRegistry,
        secret_resolver: SecretResolver | None = None,
        *,
        audit_sink: AuditSink,
        transactional_audit: _RepoT,
        classification_policy: ClassificationPolicy | None = None,
        masking_policy: MaskingPolicy | None = None,
        activation_policy: DataSourceActivationPolicy | None = None,
        activation_calendar: BusinessCalendar | None = None,
        profile_policy_resolver: ProfilePolicyResolver | None = None,
        enforce_command_authorization: bool = False,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.repository = repository
        self.registry = registry
        self.secret_resolver = secret_resolver or EmptySecretResolver()
        self.audit_sink = audit_sink
        self.transactional_audit = transactional_audit
        self.classification_policy = classification_policy or DefaultClassificationPolicy()
        self.masking_policy = masking_policy or DefaultMaskingPolicy(self.classification_policy)
        self.activation_policy = activation_policy
        self.activation_calendar = activation_calendar
        self.profile_policy_resolver = profile_policy_resolver
        self.enforce_command_authorization = enforce_command_authorization
        self.clock = clock
        if activation_policy is not None:
            _validate_activation_policy(activation_policy)
            _validate_activation_calendar(activation_policy, activation_calendar)

    def create_data_source(
        self,
        *,
        actor_context: ActorContext | None = None,
        actor_id: str | None = None,
        name: str,
        source_type: str,
        connection_config: dict[str, Any],
        secret_reference: str,
        owner_user_id: str | None = None,
        correlation_id: str | None = None,
    ) -> DataSource:
        correlation_id = _resolve_correlation_id(correlation_id)
        if actor_context is not None or self.enforce_command_authorization:
            context = self._authorize_command_actor(
                actor_context,
                required_roles=self._require_activation_policy().creator_roles,
                require_enterprise_scope=True,
            )
            actor_id = context.actor_id
            owner_user_id = context.actor_id
            correlation_id = context.correlation_id
        elif actor_id is None:
            raise AuthorizationError("Trusted actor context is required for source creation.")
        normalized_type = _parse_source_type(source_type)
        _validate_name(name)
        _validate_secret_reference(secret_reference)
        _validate_connection_config(normalized_type, connection_config)

        data_source = DataSource(
            name=name.strip(),
            source_type=normalized_type,
            connection_config=dict(connection_config),
            secret_reference=secret_reference,
            owner_user_id=owner_user_id,
        )
        audit_event = self._build_audit_event(
            actor_id=actor_id,
            correlation_id=correlation_id,
            action="DATA_SOURCE_CREATED",
            object_type="DataSource",
            object_id=data_source.data_source_id,
            result=AuditResult.SUCCESS,
            reason_code="DATA_SOURCE_CREATED",
            new_values={
                "source_type": data_source.source_type.value,
                "status": data_source.status.value,
            },
        )
        prepared = self.transactional_audit.prepare(audit_event)
        created = self.repository.add_data_source(
            data_source,
            audit_event=prepared,
            audit_outbox=self.transactional_audit,
        )
        self._publish_transactional_audit()
        return created

    def test_connection(
        self,
        *,
        actor_context: ActorContext | None = None,
        actor_id: str | None = None,
        data_source_id: str,
        correlation_id: str | None = None,
    ) -> ConnectionTestResult:
        correlation_id = _resolve_correlation_id(correlation_id)
        if actor_context is not None or self.enforce_command_authorization:
            context = self._authorize_command_actor(
                actor_context,
                required_roles=self._require_activation_policy().connection_tester_roles,
                data_source_id=data_source_id,
            )
            actor_id = context.actor_id
            correlation_id = context.correlation_id
        elif actor_id is None:
            raise AuthorizationError("Trusted actor context is required for connection test.")
        data_source = self.repository.get_data_source(data_source_id)
        result = replace(
            self._execute_connection_test(data_source),
            data_source_revision=data_source.revision,
        )

        audit_event = self._build_audit_event(
            actor_id=actor_id,
            correlation_id=correlation_id,
            action="DATA_SOURCE_CONNECTION_TESTED",
            object_type="DataSource",
            object_id=data_source.data_source_id,
            result=AuditResult.SUCCESS if result.succeeded else AuditResult.FAILURE,
            reason_code=(
                "CONNECTION_TEST_SUCCEEDED"
                if result.succeeded
                else _error_reason(result.error_class)
            ),
            new_values={
                "succeeded": result.succeeded,
                "duration_ms": result.duration_ms,
                "error_class": result.error_class.value if result.error_class else None,
            },
        )
        self.repository.update_connection_test(
            result,
            audit_event=self.transactional_audit.prepare(audit_event),
            audit_outbox=self.transactional_audit,
        )
        self._publish_transactional_audit()
        return result

    def create_connection_revision(
        self,
        *,
        actor_context: ActorContext | None,
        data_source_id: str,
        connection_config: dict[str, Any],
        secret_reference: str,
        reason_code: str,
    ) -> DataSourceConnectionRevision:
        policy = self._require_activation_policy()
        context = self._authorize_activation_actor(
            actor_context,
            required_roles=policy.maker_roles,
            data_source_id=data_source_id,
        )
        source = self.repository.get_data_source(data_source_id)
        if source.status is DataSourceStatus.ARCHIVED:
            raise ValidationError("Archived data source connection cannot be updated.")
        if self.repository.latest_pending_connection_revision(data_source_id) is not None:
            raise ValidationError("A connection revision is already pending test.")
        _validate_connection_config(source.source_type, connection_config)
        _validate_secret_reference(secret_reference)
        normalized_reason = reason_code.strip()
        if not normalized_reason:
            raise ValidationError("Connection revision reason code is required.")
        created_at = self.clock()
        _require_aware_time(created_at, "Data source connection revision clock")
        revision = DataSourceConnectionRevision(
            data_source_id=data_source_id,
            revision=self.repository.next_connection_revision(data_source_id),
            base_revision=source.revision,
            connection_config=dict(connection_config),
            secret_reference=secret_reference,
            prepared_by_actor_id=context.actor_id,
            policy_version=policy.version,
            reason_code=normalized_reason,
            created_at=created_at,
        )
        event = self._build_audit_event(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            session_id=context.session_id,
            correlation_id=context.correlation_id,
            action="DATA_SOURCE_CONNECTION_REVISION_CREATED",
            object_type="DataSource",
            object_id=data_source_id,
            result=AuditResult.SUCCESS,
            reason_code="DATA_SOURCE_CONNECTION_REVISION_CREATED",
            old_values={"data_source_revision": source.revision},
            new_values={
                "base_revision": revision.base_revision,
                "candidate_revision": revision.revision,
                "policy_version": revision.policy_version,
                "status": revision.status.value,
            },
        )
        stored = self.repository.add_connection_revision(
            revision,
            audit_event=self.transactional_audit.prepare(event),
            audit_outbox=self.transactional_audit,
        )
        self._publish_transactional_audit()
        return stored

    def test_connection_revision(
        self,
        *,
        actor_context: ActorContext | None,
        connection_revision_id: str,
    ) -> ConnectionTestResult:
        policy = self._require_activation_policy()
        candidate = self.repository.get_connection_revision(connection_revision_id)
        context = self._authorize_activation_actor(
            actor_context,
            required_roles=policy.maker_roles,
            data_source_id=candidate.data_source_id,
        )
        if candidate.status not in {
            ConnectionRevisionStatus.PENDING_TEST,
            ConnectionRevisionStatus.TEST_FAILED,
        }:
            raise ValidationError("Connection revision is not testable.")
        source = self.repository.get_data_source(candidate.data_source_id)
        if source.revision != candidate.base_revision:
            raise ValidationError("Connection revision base is stale.")
        candidate_source = DataSource(
            data_source_id=source.data_source_id,
            name=source.name,
            source_type=source.source_type,
            connection_config=candidate.connection_config,
            secret_reference=candidate.secret_reference,
            owner_user_id=source.owner_user_id,
            status=source.status,
            revision=candidate.revision,
            last_test_at=None,
            created_at=source.created_at,
        )
        result = replace(
            self._execute_connection_test(candidate_source),
            data_source_revision=candidate.revision,
        )
        next_status = (
            ConnectionRevisionStatus.PROMOTED
            if result.succeeded
            else ConnectionRevisionStatus.TEST_FAILED
        )
        tested = replace(candidate, status=next_status, tested_at=result.tested_at)
        invalidated_count = (
            self.repository.count_pending_activation_requests_except(
                source.data_source_id, candidate.revision
            )
            if result.succeeded
            else 0
        )
        source_status = DataSourceStatus.TEST_SUCCEEDED if result.succeeded else source.status
        event = self._build_audit_event(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            session_id=context.session_id,
            correlation_id=context.correlation_id,
            action="DATA_SOURCE_CONNECTION_REVISION_TESTED",
            object_type="DataSource",
            object_id=source.data_source_id,
            result=AuditResult.SUCCESS if result.succeeded else AuditResult.FAILURE,
            reason_code=(
                "DATA_SOURCE_CONNECTION_REVISION_PROMOTED"
                if result.succeeded
                else _error_reason(result.error_class)
            ),
            old_values={
                "data_source_revision": source.revision,
                "source_status": source.status.value,
            },
            new_values={
                "candidate_revision": candidate.revision,
                "revision_status": next_status.value,
                "source_status": source_status.value,
                "succeeded": result.succeeded,
                "duration_ms": result.duration_ms,
                "error_class": result.error_class.value if result.error_class else None,
                "invalidated_activation_count": invalidated_count,
            },
        )
        self.repository.record_connection_revision_test(
            tested,
            result,
            audit_event=self.transactional_audit.prepare(event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return result

    def _execute_connection_test(self, data_source: DataSource) -> ConnectionTestResult:
        connector = self.registry.get(data_source.source_type)
        if connector is None:
            return ConnectionTestResult(
                data_source_id=data_source.data_source_id,
                succeeded=False,
                duration_ms=0,
                error_class=ErrorClass.UNSUPPORTED_SOURCE,
                message="No connector is registered for this source type.",
                source_info={"source_type": data_source.source_type.value},
            )
        try:
            secret = self.secret_resolver.resolve(data_source.secret_reference)
            return connector.test_connection(data_source, secret)
        except SecretResolutionError:
            # Secret-store erişimi/çözümlemesi bir bağlantı sonucu değildir. Komutu
            # fail-closed sonlandırarak API'nin güvenli bir 503 üretmesini sağla;
            # yalnızca connector tarafından doğrulanan hatalı kimlik bilgileri
            # AUTHENTICATION test sonucu olarak kalır.
            raise
        except Exception as exc:
            raise TechnicalError("Unexpected connector failure.") from exc

    def request_activation(
        self,
        *,
        actor_context: ActorContext | None,
        data_source_id: str,
    ) -> DataSourceActivationRequest:
        policy = self._require_activation_policy()
        context = self._authorize_activation_actor(
            actor_context,
            required_roles=policy.maker_roles,
            data_source_id=data_source_id,
        )
        source = self.repository.get_data_source(data_source_id)
        if source.status not in {
            DataSourceStatus.TEST_SUCCEEDED,
            DataSourceStatus.INACTIVE,
        }:
            raise ConflictError("Activation requires a successfully tested data source.")
        if not source.owner_user_id or not source.owner_user_id.strip():
            raise ValidationError("Activation requires a data owner.")
        latest_test = self.repository.latest_connection_test(
            data_source_id, data_source_revision=source.revision
        )
        if (
            latest_test is None
            or not latest_test.succeeded
            or source.last_test_at is None
            or latest_test.tested_at != source.last_test_at
        ):
            raise ValidationError("Activation requires the current revision's successful test.")
        requested_at = self.clock()
        _require_aware_time(requested_at, "Data source activation clock")
        target_at, expires_at, calendar_version = self._activation_timing(requested_at)
        request = DataSourceActivationRequest(
            data_source_id=data_source_id,
            data_source_revision=source.revision,
            maker_actor_id=context.actor_id,
            policy_version=policy.version,
            requested_at=requested_at,
            target_at=target_at,
            expires_at=expires_at,
            business_calendar_version=calendar_version,
        )
        event = self._build_audit_event(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            session_id=context.session_id,
            correlation_id=context.correlation_id,
            action="DATA_SOURCE_ACTIVATION_REQUESTED",
            object_type="DataSource",
            object_id=data_source_id,
            result=AuditResult.SUCCESS,
            reason_code="DATA_SOURCE_ACTIVATION_REQUESTED",
            new_values={
                "activation_request_id": request.activation_request_id,
                "data_source_revision": source.revision,
                "policy_version": policy.version,
                "status": request.status.value,
                "target_at": target_at.isoformat() if target_at else None,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "business_calendar_version": calendar_version,
            },
        )
        stored = self.repository.add_activation_request(
            request,
            audit_event=self.transactional_audit.prepare(event),
            audit_outbox=self.transactional_audit,
        )
        self._publish_transactional_audit()
        return stored

    def decide_activation(
        self,
        *,
        actor_context: ActorContext | None,
        activation_request_id: str,
        decision: str,
        reason_code: str,
    ) -> DataSourceActivationRequest:
        policy = self._require_activation_policy()
        request = self.repository.get_activation_request(activation_request_id)
        source = self.repository.get_data_source(request.data_source_id)
        context = self._authorize_activation_actor(
            actor_context,
            required_roles=policy.checker_roles,
            data_source_id=source.data_source_id,
        )
        normalized_reason = reason_code.strip()
        if not normalized_reason:
            raise ValidationError("Activation decision reason code is required.")
        status = _parse_activation_decision(decision)
        if request.status is not DataSourceActivationStatus.PENDING:
            if (
                request.checker_actor_id == context.actor_id
                and request.status is status
                and request.decision_reason_code == normalized_reason
            ):
                return request
            raise ConflictError(
                "Data source activation decision conflicts with the terminal request.",
                code="DATA_SOURCE_DECISION_CONFLICT",
            )
        if self._activation_request_expired(request):
            raise ConflictError(
                "Data source activation request has expired and must be recreated.",
                code="DATA_SOURCE_ACTIVATION_EXPIRED",
            )
        if request.policy_version != policy.version:
            raise ConflictError(
                "Data source activation policy version changed.",
                code="DATA_SOURCE_POLICY_CONFLICT",
            )
        if request.data_source_revision != source.revision:
            raise ConflictError(
                "Data source activation request is for a stale revision.",
                code="DATA_SOURCE_REVISION_CONFLICT",
            )
        if request.maker_actor_id == context.actor_id:
            raise AuthorizationError(
                "Activation maker cannot approve the same change.",
                code="DATA_SOURCE_MAKER_CHECKER_VIOLATION",
            )
        decided_at = self.clock()
        _require_aware_time(decided_at, "Data source activation clock")
        decided = DataSourceActivationRequest(
            activation_request_id=request.activation_request_id,
            data_source_id=request.data_source_id,
            data_source_revision=request.data_source_revision,
            maker_actor_id=request.maker_actor_id,
            checker_actor_id=context.actor_id,
            policy_version=request.policy_version,
            status=status,
            decision_reason_code=normalized_reason,
            requested_at=request.requested_at,
            target_at=request.target_at,
            expires_at=request.expires_at,
            business_calendar_version=request.business_calendar_version,
            decided_at=decided_at,
        )
        source_status = (
            DataSourceStatus.ACTIVE
            if status is DataSourceActivationStatus.APPROVED
            else source.status
        )
        event = self._build_audit_event(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            session_id=context.session_id,
            correlation_id=context.correlation_id,
            action="DATA_SOURCE_ACTIVATION_DECIDED",
            object_type="DataSource",
            object_id=source.data_source_id,
            result=AuditResult.SUCCESS,
            reason_code=f"DATA_SOURCE_ACTIVATION_{status.value}",
            old_values={"status": source.status.value},
            new_values={
                "activation_request_id": request.activation_request_id,
                "data_source_revision": request.data_source_revision,
                "policy_version": request.policy_version,
                "status": status.value,
                "source_status": source_status.value,
            },
        )
        stored = self.repository.decide_activation_request(
            decided,
            activate_source=status is DataSourceActivationStatus.APPROVED,
            audit_event=self.transactional_audit.prepare(event),
            audit_outbox=self.transactional_audit,
        )
        self._publish_transactional_audit()
        return stored

    def deactivate_data_source(
        self,
        *,
        actor_context: ActorContext | None,
        data_source_id: str,
        reason_code: str,
    ) -> DataSource:
        policy = self._require_activation_policy()
        context = self._authorize_activation_actor(
            actor_context,
            required_roles=policy.deactivator_roles,
            data_source_id=data_source_id,
        )
        source = self.repository.get_data_source(data_source_id)
        if source.status is not DataSourceStatus.ACTIVE:
            raise ConflictError("Only an active data source can be deactivated.")
        normalized_reason = reason_code.strip()
        if not normalized_reason:
            raise ValidationError("Data source deactivation reason code is required.")
        event = self._build_audit_event(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            session_id=context.session_id,
            correlation_id=context.correlation_id,
            action="DATA_SOURCE_DEACTIVATED",
            object_type="DataSource",
            object_id=data_source_id,
            result=AuditResult.SUCCESS,
            reason_code="DATA_SOURCE_DEACTIVATED",
            old_values={"status": source.status.value},
            new_values={
                "data_source_revision": source.revision,
                "policy_version": policy.version,
                "status": DataSourceStatus.INACTIVE.value,
            },
        )
        stored = self.repository.deactivate_data_source(
            data_source_id,
            expected_revision=source.revision,
            audit_event=self.transactional_audit.prepare(event),
            audit_outbox=self.transactional_audit,
        )
        self._publish_transactional_audit()
        return stored

    def request_deactivation(
        self,
        *,
        actor_context: ActorContext | None,
        data_source_id: str,
    ) -> DataSourceActivationRequest:
        policy = self._require_activation_policy()
        context = self._authorize_activation_actor(
            actor_context,
            required_roles=policy.maker_roles,
            data_source_id=data_source_id,
        )
        source = self.repository.get_data_source(data_source_id)
        if source.status is not DataSourceStatus.ACTIVE:
            raise ConflictError("Only an active data source can be requested for deactivation.")
        requested_at = self.clock()
        _require_aware_time(requested_at, "Data source deactivation clock")
        request = DataSourceActivationRequest(
            data_source_id=data_source_id,
            data_source_revision=source.revision,
            maker_actor_id=context.actor_id,
            policy_version=policy.version,
            request_type="DEACTIVATION",
        )
        event = self._build_audit_event(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            session_id=context.session_id,
            correlation_id=context.correlation_id,
            action="DATA_SOURCE_DEACTIVATION_REQUESTED",
            object_type="DataSource",
            object_id=data_source_id,
            result=AuditResult.SUCCESS,
            reason_code="DATA_SOURCE_DEACTIVATION_REQUESTED",
            new_values={
                "deactivation_request_id": request.activation_request_id,
                "data_source_revision": source.revision,
                "policy_version": policy.version,
                "status": request.status.value,
            },
        )
        stored = self.repository.add_deactivation_request(
            request,
            audit_event=self.transactional_audit.prepare(event),
            audit_outbox=self.transactional_audit,
        )
        self._publish_transactional_audit()
        return stored

    def decide_deactivation(
        self,
        *,
        actor_context: ActorContext | None,
        deactivation_request_id: str,
        decision: str,
        reason_code: str,
    ) -> DataSourceActivationRequest:
        policy = self._require_activation_policy()
        request = self.repository.get_activation_request(deactivation_request_id)
        source = self.repository.get_data_source(request.data_source_id)
        context = self._authorize_activation_actor(
            actor_context,
            required_roles=policy.checker_roles,
            data_source_id=source.data_source_id,
        )
        normalized_reason = reason_code.strip()
        if not normalized_reason:
            raise ValidationError("Deactivation decision reason code is required.")
        status = _parse_activation_decision(decision)
        if request.status is not DataSourceActivationStatus.PENDING:
            if (
                request.checker_actor_id == context.actor_id
                and request.status is status
                and request.decision_reason_code == normalized_reason
            ):
                return request
            raise ConflictError(
                "Data source deactivation decision conflicts with the terminal request.",
                code="DATA_SOURCE_DECISION_CONFLICT",
            )
        if request.policy_version != policy.version:
            raise ConflictError(
                "Data source deactivation policy version changed.",
                code="DATA_SOURCE_POLICY_CONFLICT",
            )
        if request.data_source_revision != source.revision:
            raise ConflictError(
                "Data source deactivation request is for a stale revision.",
                code="DATA_SOURCE_REVISION_CONFLICT",
            )
        if request.maker_actor_id == context.actor_id:
            raise AuthorizationError(
                "Deactivation maker cannot approve the same change.",
                code="DATA_SOURCE_MAKER_CHECKER_VIOLATION",
            )
        decided_at = self.clock()
        _require_aware_time(decided_at, "Data source deactivation clock")
        decided = DataSourceActivationRequest(
            activation_request_id=request.activation_request_id,
            data_source_id=request.data_source_id,
            data_source_revision=request.data_source_revision,
            maker_actor_id=request.maker_actor_id,
            checker_actor_id=context.actor_id,
            policy_version=request.policy_version,
            status=status,
            decision_reason_code=normalized_reason,
            requested_at=request.requested_at,
            target_at=request.target_at,
            expires_at=request.expires_at,
            business_calendar_version=request.business_calendar_version,
            decided_at=decided_at,
            request_type="DEACTIVATION",
        )
        source_status = (
            DataSourceStatus.INACTIVE
            if status is DataSourceActivationStatus.APPROVED
            else source.status
        )
        event = self._build_audit_event(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            session_id=context.session_id,
            correlation_id=context.correlation_id,
            action="DATA_SOURCE_DEACTIVATION_DECIDED",
            object_type="DataSource",
            object_id=source.data_source_id,
            result=AuditResult.SUCCESS,
            reason_code=f"DATA_SOURCE_DEACTIVATION_{status.value}",
            old_values={"status": source.status.value},
            new_values={
                "deactivation_request_id": request.activation_request_id,
                "data_source_revision": request.data_source_revision,
                "policy_version": request.policy_version,
                "status": status.value,
                "source_status": source_status.value,
            },
        )
        stored = self.repository.decide_deactivation_request(
            decided,
            deactivate_source=status is DataSourceActivationStatus.APPROVED,
            audit_event=self.transactional_audit.prepare(event),
            audit_outbox=self.transactional_audit,
        )
        self._publish_transactional_audit()
        return stored

    def withdraw_activation(
        self,
        *,
        actor_context: ActorContext | None,
        activation_request_id: str,
        reason_code: str,
    ) -> DataSourceActivationRequest:
        policy = self._require_activation_policy()
        request = self.repository.get_activation_request(activation_request_id)
        source = self.repository.get_data_source(request.data_source_id)
        context = self._authorize_activation_actor(
            actor_context,
            required_roles=policy.maker_roles,
            data_source_id=source.data_source_id,
        )
        if request.status is not DataSourceActivationStatus.PENDING:
            raise ValidationError("Data source activation request is not pending.")
        if self._activation_request_expired(request):
            raise ValidationError(
                "Data source activation request has expired and must be recreated."
            )
        if request.data_source_revision != source.revision:
            raise ValidationError("Data source activation request is for a stale revision.")
        if request.maker_actor_id != context.actor_id:
            raise AuthorizationError("Only the activation request maker can withdraw it.")
        normalized_reason = reason_code.strip()
        if not normalized_reason:
            raise ValidationError("Activation withdrawal reason code is required.")
        withdrawn_at = self.clock()
        _require_aware_time(withdrawn_at, "Data source activation clock")
        withdrawn = DataSourceActivationRequest(
            activation_request_id=request.activation_request_id,
            data_source_id=request.data_source_id,
            data_source_revision=request.data_source_revision,
            maker_actor_id=request.maker_actor_id,
            policy_version=request.policy_version,
            status=DataSourceActivationStatus.WITHDRAWN,
            decision_reason_code=normalized_reason,
            requested_at=request.requested_at,
            target_at=request.target_at,
            expires_at=request.expires_at,
            business_calendar_version=request.business_calendar_version,
            decided_at=withdrawn_at,
        )
        event = self._build_audit_event(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            session_id=context.session_id,
            correlation_id=context.correlation_id,
            action="DATA_SOURCE_ACTIVATION_WITHDRAWN",
            object_type="DataSource",
            object_id=source.data_source_id,
            result=AuditResult.SUCCESS,
            reason_code="DATA_SOURCE_ACTIVATION_WITHDRAWN",
            old_values={"status": DataSourceActivationStatus.PENDING.value},
            new_values={
                "activation_request_id": request.activation_request_id,
                "data_source_revision": request.data_source_revision,
                "policy_version": request.policy_version,
                "status": DataSourceActivationStatus.WITHDRAWN.value,
                "source_status": source.status.value,
            },
        )
        stored = self.repository.withdraw_activation_request(
            withdrawn,
            audit_event=self.transactional_audit.prepare(event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return stored

    def expire_due_activations(
        self, *, actor_context: ActorContext | None
    ) -> tuple[DataSourceActivationRequest, ...]:
        context = self._authorize_activation_expiry_actor(actor_context)
        expired_at = self.clock()
        _require_aware_time(expired_at, "Data source activation clock")
        due = self.repository.list_due_activation_requests(expired_at)
        for request in due:
            if request.data_source_id not in context.permitted_source_ids:
                raise AuthorizationError("Expiry worker is outside the data source scope.")

        expired_requests = []
        for request in due:
            source = self.repository.get_data_source(request.data_source_id)
            expired = DataSourceActivationRequest(
                activation_request_id=request.activation_request_id,
                data_source_id=request.data_source_id,
                data_source_revision=request.data_source_revision,
                maker_actor_id=request.maker_actor_id,
                policy_version=request.policy_version,
                status=DataSourceActivationStatus.EXPIRED,
                decision_reason_code="DATA_SOURCE.ACTIVATION.EXPIRED",
                requested_at=request.requested_at,
                target_at=request.target_at,
                expires_at=request.expires_at,
                business_calendar_version=request.business_calendar_version,
                decided_at=expired_at,
            )
            event = self._build_audit_event(
                actor_id=context.actor_id,
                actor_type=context.actor_type.value,
                session_id=context.session_id,
                correlation_id=context.correlation_id,
                action="DATA_SOURCE_ACTIVATION_EXPIRED",
                object_type="DataSource",
                object_id=request.data_source_id,
                result=AuditResult.SUCCESS,
                reason_code="DATA_SOURCE_ACTIVATION_EXPIRED",
                old_values={"status": DataSourceActivationStatus.PENDING.value},
                new_values={
                    "activation_request_id": request.activation_request_id,
                    "data_source_revision": request.data_source_revision,
                    "policy_version": request.policy_version,
                    "business_calendar_version": request.business_calendar_version,
                    "status": DataSourceActivationStatus.EXPIRED.value,
                    "source_status": source.status.value,
                },
            )
            stored = self.repository.expire_activation_request(
                expired,
                audit_event=self.transactional_audit.prepare(event),
                audit_outbox=self.transactional_audit,
            )
            self.transactional_audit.publish_pending()
            expired_requests.append(stored)
        return tuple(expired_requests)

    def _activation_timing(
        self, requested_at: datetime
    ) -> tuple[datetime | None, datetime | None, str | None]:
        policy = self._require_activation_policy()
        if policy.expiration_business_days is None:
            return None, None, None
        assert policy.target_business_days is not None
        assert policy.business_calendar_version is not None
        assert self.activation_calendar is not None
        target_at = self.activation_calendar.add_business_days(
            requested_at, policy.target_business_days
        )
        expires_at = self.activation_calendar.add_business_days(
            requested_at, policy.expiration_business_days
        )
        _require_aware_time(target_at, "Data source activation calendar")
        _require_aware_time(expires_at, "Data source activation calendar")
        if not requested_at < target_at < expires_at:
            raise ValidationError(
                "Data source activation calendar returned an invalid time window."
            )
        return target_at, expires_at, policy.business_calendar_version

    def _activation_request_expired(self, request: DataSourceActivationRequest) -> bool:
        if request.expires_at is None:
            return False
        now = self.clock()
        _require_aware_time(now, "Data source activation clock")
        return now >= request.expires_at

    def _authorize_activation_expiry_actor(self, context: ActorContext | None) -> ActorContext:
        policy = self._require_activation_policy()
        now = self.clock()
        _require_aware_time(now, "Data source activation clock")
        if not is_trusted_actor_context(context):
            raise AuthorizationError("Trusted activation expiry service context is required.")
        assert context is not None
        if context.issued_at > now or context.expires_at <= now:
            raise AuthorizationError("Activation expiry service context is not currently valid.")
        if context.policy_version != policy.actor_policy_version:
            raise AuthorizationError("Activation expiry service policy version is not accepted.")
        if context.actor_type is not ActorType.SERVICE:
            raise AuthorizationError("Activation expiry requires a service account.")
        if not policy.expiry_service_roles or context.roles.isdisjoint(policy.expiry_service_roles):
            raise AuthorizationError("Service account cannot expire activation requests.")
        return context

    def discover_metadata(
        self,
        *,
        actor_id: str,
        data_source_id: str,
        options: MetadataDiscoveryOptions | None = None,
        correlation_id: str | None = None,
    ) -> MetadataDiscoveryResult:
        correlation_id = _resolve_correlation_id(correlation_id)
        options = options or MetadataDiscoveryOptions()
        _validate_metadata_options(options)
        data_source = self.repository.get_data_source(data_source_id)
        if data_source.status not in {
            DataSourceStatus.TEST_SUCCEEDED,
            DataSourceStatus.ACTIVE,
        }:
            raise ValidationError("Metadata discovery requires a successful connection test.")

        connector = self.registry.get(data_source.source_type)
        if connector is None:
            result = MetadataDiscoveryResult(
                data_source_id=data_source.data_source_id,
                succeeded=False,
                duration_ms=0,
                error_class=ErrorClass.UNSUPPORTED_SOURCE,
                message="No connector is registered for this source type.",
            )
            self._persist_metadata_result(actor_id, correlation_id, result)
            return result

        from time import perf_counter

        started = perf_counter()
        try:
            secret = self.secret_resolver.resolve(data_source.secret_reference)
            outcome = connector.discover_metadata(data_source, secret, options)
            candidates = outcome.candidates
        except SecretResolutionError:
            result = MetadataDiscoveryResult(
                data_source_id=data_source.data_source_id,
                succeeded=False,
                duration_ms=0,
                error_class=ErrorClass.AUTHENTICATION,
                message="Secret reference could not be resolved.",
            )
            self._persist_metadata_result(actor_id, correlation_id, result)
            return result
        except (
            DNSConnectionError,
            NetworkConnectionError,
            TimeoutConnectionError,
            AuthenticationConnectionError,
            TLSConnectionError,
            PermissionConnectionError,
            DriverConnectionError,
        ) as exc:
            result = MetadataDiscoveryResult(
                data_source_id=data_source.data_source_id,
                succeeded=False,
                duration_ms=_elapsed_ms(started),
                error_class=_error_class_for_exception(exc),
                message="Metadata discovery failed with a classified technical error.",
            )
            self._persist_metadata_result(actor_id, correlation_id, result)
            return result
        except Exception as exc:
            raise TechnicalError("Unexpected metadata discovery failure.") from exc

        previous = self.repository.list_metadata_snapshot(data_source.data_source_id)
        previous_datasets = {
            (dataset.namespace, dataset.name): dataset
            for dataset in self.repository.list_datasets(data_source.data_source_id)
        }
        datasets: list[Dataset] = []
        fields_by_dataset_id: dict[str, list[DataField]] = {}
        for candidate in candidates:
            previous_dataset = previous_datasets.get((candidate.namespace, candidate.name))
            dataset = Dataset(
                data_source_id=data_source.data_source_id,
                namespace=candidate.namespace,
                name=candidate.name,
                dataset_type=candidate.dataset_type,
                estimated_row_count=candidate.estimated_row_count,
                dataset_id=(previous_dataset.dataset_id if previous_dataset else str(uuid4())),
            )
            datasets.append(dataset)
            normalized_fields: list[DataField] = []
            previous_fields = {
                field.name: field
                for field in previous.get((candidate.namespace, candidate.name), [])
            }
            for field in candidate.fields:
                previous_field = previous_fields.get(field.name)
                try:
                    classification = (
                        previous_field.classification
                        if field.classification is None and previous_field is not None
                        else self.classification_policy.normalize(field.classification)
                    )
                except ClassificationValidationError as exc:
                    raise ValidationError(
                        "Metadata classification must use an approved policy code."
                    ) from exc
                normalized_fields.append(
                    DataField(
                        dataset_id=dataset.dataset_id,
                        name=field.name,
                        native_data_type=field.native_data_type,
                        is_nullable=field.is_nullable,
                        is_sensitive=field.is_sensitive,
                        classification=classification,
                        classification_policy_version=self.classification_policy.version,
                        data_field_id=(
                            previous_field.data_field_id if previous_field else str(uuid4())
                        ),
                    )
                )
            fields_by_dataset_id[dataset.dataset_id] = normalized_fields

        changes = _diff_metadata(previous, datasets, fields_by_dataset_id)
        if not outcome.is_complete:
            changes = [
                change for change in changes if change.change_type is not MetadataChangeType.REMOVED
            ]
        discovery_status = (
            DiscoveryStatus.SUCCESS if outcome.is_complete else DiscoveryStatus.PARTIAL
        )
        result = MetadataDiscoveryResult(
            data_source_id=data_source.data_source_id,
            succeeded=True,
            duration_ms=_elapsed_ms(started),
            scanned_object_count=outcome.scanned_object_count,
            datasets=tuple(datasets),
            fields=tuple(field for fields in fields_by_dataset_id.values() for field in fields),
            changes=tuple(changes),
            status=discovery_status,
            completed_scope=outcome.completed_scope,
            partial_reason_code=outcome.partial_reason_code,
            message=(
                "Metadata discovery completed."
                if outcome.is_complete
                else f"Metadata discovery partial: {outcome.partial_reason_code}"
            ),
        )
        self._persist_metadata_result(
            actor_id,
            correlation_id,
            result,
            datasets=datasets,
            fields_by_dataset_id=fields_by_dataset_id,
        )
        return result

    # ------------------------------------------------------------------
    # DS-04: async discovery lifecycle
    # ------------------------------------------------------------------

    def request_discovery(
        self,
        *,
        actor_id: str,
        data_source_id: str,
        correlation_id: str | None = None,
    ) -> MetadataDiscoveryResult:
        """Create a QUEUED discovery record. Caller enqueues the background job."""
        correlation_id = _resolve_correlation_id(correlation_id)
        data_source = self.repository.get_data_source(data_source_id)
        if data_source.status is not DataSourceStatus.ACTIVE:
            raise ValidationError("Metadata discovery request requires an ACTIVE data source.")
        now = self.clock()
        result = MetadataDiscoveryResult(
            data_source_id=data_source.data_source_id,
            succeeded=False,
            duration_ms=0,
            status=DiscoveryStatus.QUEUED,
            requested_by_actor_id=actor_id,
            correlation_id=correlation_id,
            discovered_at=now,
        )
        audit_event = self._build_audit_event(
            actor_id=actor_id,
            correlation_id=correlation_id,
            action="DATA_SOURCE_METADATA_DISCOVERY_REQUESTED",
            object_type="DataSource",
            object_id=data_source.data_source_id,
            result=AuditResult.SUCCESS,
            reason_code="METADATA_DISCOVERY_REQUESTED",
            new_values={"status": DiscoveryStatus.QUEUED.value},
        )
        prepared = self.transactional_audit.prepare(audit_event)
        stored = self.repository.record_discovery_request(
            result,
            audit_event=prepared,
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return stored

    def execute_discovery_for_worker(
        self,
        discovery_id: int,
        *,
        actor_id: str,
        correlation_id: str,
        cancellation_event: object | None = None,
    ) -> MetadataDiscoveryResult:
        """Run connector, compute diff, persist terminal state + diff."""
        existing = self.repository.get_discovery_result(discovery_id)
        if existing.status is not DiscoveryStatus.QUEUED:
            raise ConflictError("Discovery is not in QUEUED state.")

        _started_at = utc_now()
        start_transition = self._build_audit_event(
            actor_id=actor_id,
            correlation_id=correlation_id,
            action="DATA_SOURCE_METADATA_DISCOVERY_STARTED",
            object_type="DataSource",
            object_id=existing.data_source_id,
            result=AuditResult.SUCCESS,
            reason_code="METADATA_DISCOVERY_STARTED",
            new_values={},
        )
        self.repository.update_discovery_status(
            discovery_id,
            status=DiscoveryStatus.RUNNING.value,
            expected_version=existing.version,
            audit_event=self.transactional_audit.prepare(start_transition),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()

        data_source = self.repository.get_data_source(existing.data_source_id)
        connector = self.registry.get(data_source.source_type)
        if connector is None:
            failure = self._build_audit_event(
                actor_id=actor_id,
                correlation_id=correlation_id,
                action="DATA_SOURCE_METADATA_DISCOVERY_FAILED",
                object_type="DataSource",
                object_id=data_source.data_source_id,
                result=AuditResult.FAILURE,
                reason_code="UNSUPPORTED_SOURCE",
                new_values={},
            )
            self.repository.update_discovery_status(
                discovery_id,
                status=DiscoveryStatus.TECHNICAL_ERROR.value,
                expected_version=existing.version + 1,
                error_class=ErrorClass.UNSUPPORTED_SOURCE.value,
                message="No connector is registered for this source type.",
                audit_event=self.transactional_audit.prepare(failure),
                audit_outbox=self.transactional_audit,
            )
            self.transactional_audit.publish_pending()
            return self.repository.get_discovery_result(discovery_id)

        from time import perf_counter

        started = perf_counter()
        try:
            secret = self.secret_resolver.resolve(data_source.secret_reference)
            scope = self.repository.get_discovery_scope(data_source.data_source_id)
            options = MetadataDiscoveryOptions(
                scope={
                    "include_patterns": list(scope.include_patterns) if scope else [],
                    "exclude_patterns": list(scope.exclude_patterns) if scope else [],
                },
                page_size=scope.page_size if scope else 1000,
                max_objects=scope.max_objects if scope else 100_000,
                timeout_seconds=scope.timeout_seconds if scope else 60,
            )
            outcome = connector.discover_metadata(data_source, secret, options)
        except SecretResolutionError:
            failure = self._build_audit_event(
                actor_id=actor_id,
                correlation_id=correlation_id,
                action="DATA_SOURCE_METADATA_DISCOVERY_FAILED",
                object_type="DataSource",
                object_id=data_source.data_source_id,
                result=AuditResult.FAILURE,
                reason_code="SECRET_RESOLUTION_FAILED",
                new_values={},
            )
            self.repository.update_discovery_status(
                discovery_id,
                status=DiscoveryStatus.TECHNICAL_ERROR.value,
                expected_version=existing.version + 1,
                error_class=ErrorClass.AUTHENTICATION.value,
                message="Secret reference could not be resolved.",
                finished_at=utc_now(),
                audit_event=self.transactional_audit.prepare(failure),
                audit_outbox=self.transactional_audit,
            )
            self.transactional_audit.publish_pending()
            return self.repository.get_discovery_result(discovery_id)
        except (
            DNSConnectionError,
            NetworkConnectionError,
            TimeoutConnectionError,
            AuthenticationConnectionError,
            TLSConnectionError,
            PermissionConnectionError,
            DriverConnectionError,
        ) as exc:
            failure = self._build_audit_event(
                actor_id=actor_id,
                correlation_id=correlation_id,
                action="DATA_SOURCE_METADATA_DISCOVERY_FAILED",
                object_type="DataSource",
                object_id=data_source.data_source_id,
                result=AuditResult.FAILURE,
                reason_code=_error_reason(_error_class_for_exception(exc)),
                new_values={},
            )
            self.repository.update_discovery_status(
                discovery_id,
                status=DiscoveryStatus.TECHNICAL_ERROR.value,
                expected_version=existing.version + 1,
                error_class=_error_class_for_exception(exc).value,
                message="Metadata discovery failed with a classified technical error.",
                finished_at=utc_now(),
                audit_event=self.transactional_audit.prepare(failure),
                audit_outbox=self.transactional_audit,
            )
            self.transactional_audit.publish_pending()
            return self.repository.get_discovery_result(discovery_id)
        except Exception as exc:
            raise TechnicalError("Unexpected metadata discovery failure.") from exc

        candidates = outcome.candidates
        previous = self.repository.list_metadata_snapshot(data_source.data_source_id)
        previous_datasets = {
            (ds.namespace, ds.name): ds
            for ds in self.repository.list_datasets(data_source.data_source_id)
        }
        datasets: list[Dataset] = []
        fields_by_dataset_id: dict[str, list[DataField]] = {}
        for candidate in candidates:
            previous_dataset = previous_datasets.get((candidate.namespace, candidate.name))
            dataset = Dataset(
                data_source_id=data_source.data_source_id,
                namespace=candidate.namespace,
                name=candidate.name,
                dataset_type=candidate.dataset_type,
                estimated_row_count=candidate.estimated_row_count,
                dataset_id=(previous_dataset.dataset_id if previous_dataset else str(uuid4())),
            )
            datasets.append(dataset)
            normalized_fields: list[DataField] = []
            previous_fields = {
                f.name: f for f in previous.get((candidate.namespace, candidate.name), [])
            }
            for field in candidate.fields:
                previous_field = previous_fields.get(field.name)
                try:
                    classification = (
                        previous_field.classification
                        if field.classification is None and previous_field is not None
                        else self.classification_policy.normalize(field.classification)
                    )
                except ClassificationValidationError as exc:
                    raise ValidationError(
                        "Metadata classification must use an approved policy code."
                    ) from exc
                normalized_fields.append(
                    DataField(
                        dataset_id=dataset.dataset_id,
                        name=field.name,
                        native_data_type=field.native_data_type,
                        is_nullable=field.is_nullable,
                        is_sensitive=field.is_sensitive,
                        classification=classification,
                        classification_policy_version=self.classification_policy.version,
                        data_field_id=(
                            previous_field.data_field_id if previous_field else str(uuid4())
                        ),
                    )
                )
            fields_by_dataset_id[dataset.dataset_id] = normalized_fields

        changes = _diff_metadata(previous, datasets, fields_by_dataset_id)
        if not outcome.is_complete:
            changes = [c for c in changes if c.change_type is not MetadataChangeType.REMOVED]

        terminal_status = (
            DiscoveryStatus.SUCCESS if outcome.is_complete else DiscoveryStatus.PARTIAL
        )
        finished_at = utc_now()
        duration_ms = _elapsed_ms(started)

        diff = MetadataDiff(
            metadata_diff_id=str(uuid4()),
            discovery_id=discovery_id,
            data_source_id=data_source.data_source_id,
            added_objects=tuple(
                {
                    "object_type": c.object_type,
                    "namespace": c.namespace,
                    "dataset_name": c.dataset_name,
                    "field_name": c.field_name,
                    "new_values": c.new_values,
                }
                for c in changes
                if c.change_type is MetadataChangeType.ADDED
            ),
            changed_objects=tuple(
                {
                    "object_type": c.object_type,
                    "namespace": c.namespace,
                    "dataset_name": c.dataset_name,
                    "field_name": c.field_name,
                    "old_values": c.old_values,
                    "new_values": c.new_values,
                    "requires_rule_review": c.requires_rule_review,
                }
                for c in changes
                if c.change_type is MetadataChangeType.CHANGED
            ),
            removed_objects=tuple(
                {
                    "object_type": c.object_type,
                    "namespace": c.namespace,
                    "dataset_name": c.dataset_name,
                    "field_name": c.field_name,
                    "old_values": c.old_values,
                    "requires_rule_review": c.requires_rule_review,
                }
                for c in changes
                if c.change_type is MetadataChangeType.REMOVED
            ),
            status=MetadataDiffStatus.PENDING,
            requires_rule_review=any(c.requires_rule_review for c in changes),
        )

        discovered_event = self._build_audit_event(
            actor_id=actor_id,
            correlation_id=correlation_id,
            action="DATA_SOURCE_METADATA_DISCOVERED",
            object_type="DataSource",
            object_id=data_source.data_source_id,
            result=AuditResult.SUCCESS,
            reason_code="METADATA_DISCOVERY_SUCCEEDED",
            new_values={
                "status": terminal_status.value,
                "duration_ms": duration_ms,
                "scanned_object_count": outcome.scanned_object_count,
            },
        )
        diff_computed_event = self._build_audit_event(
            actor_id=actor_id,
            correlation_id=correlation_id,
            action="DATA_SOURCE_METADATA_DIFF_COMPUTED",
            object_type="DataSource",
            object_id=data_source.data_source_id,
            result=AuditResult.SUCCESS,
            reason_code="METADATA_DIFF_COMPUTED",
            new_values={
                "metadata_diff_id": diff.metadata_diff_id,
                "added_count": len(diff.added_objects),
                "changed_count": len(diff.changed_objects),
                "removed_count": len(diff.removed_objects),
                "requires_rule_review": diff.requires_rule_review,
            },
        )
        prepared_discovered = self.transactional_audit.prepare(discovered_event)
        prepared_diff = self.transactional_audit.prepare(diff_computed_event)
        self.repository.update_discovery_status(
            discovery_id,
            status=terminal_status.value,
            expected_version=existing.version + 1,
            finished_at=finished_at,
            completed_scope=outcome.completed_scope,
            partial_reason_code=outcome.partial_reason_code,
            scanned_object_count=outcome.scanned_object_count,
            message=(
                "Metadata discovery completed."
                if outcome.is_complete
                else f"Metadata discovery partial: {outcome.partial_reason_code}"
            ),
            audit_event=prepared_discovered,
            audit_outbox=self.transactional_audit,
        )
        self.repository.persist_metadata_diff(
            diff,
            audit_event=prepared_diff,
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return self.repository.get_discovery_result(discovery_id)

    def apply_discovery_diff(
        self,
        *,
        actor_id: str,
        metadata_diff_id: str,
        reason_code: str,
        expected_version: int,
        correlation_id: str | None = None,
    ) -> MetadataDiff:
        """Apply a pending metadata diff to reconcile the catalog."""
        correlation_id = _resolve_correlation_id(correlation_id)
        diff = self.repository.get_metadata_diff(metadata_diff_id)
        if diff.status is not MetadataDiffStatus.PENDING:
            raise ConflictError("Metadata diff is not in PENDING state.")
        data_source = self.repository.get_data_source(diff.data_source_id)
        _discovery = self.repository.get_discovery_result(diff.discovery_id)

        datasets: list[Dataset] = []
        fields_by_dataset_id: dict[str, list[DataField]] = {}
        passivated_dataset_ids: list[str] = []
        passivated_field_ids: list[str] = []

        existing_datasets = {
            (ds.namespace, ds.name): ds
            for ds in self.repository.list_datasets(data_source.data_source_id)
        }
        existing_fields_map: dict[str, dict[str, DataField]] = {}
        for ds in self.repository.list_datasets(data_source.data_source_id):
            existing_fields_map[ds.dataset_id] = {
                f.name: f for f in self.repository.list_data_fields(ds.dataset_id)
            }

        for added in diff.added_objects:
            if added["object_type"] == "DATASET":
                ds_key = (added["namespace"], added["dataset_name"])
                previous = existing_datasets.get(ds_key)
                datasets.append(
                    Dataset(
                        data_source_id=data_source.data_source_id,
                        namespace=added["namespace"],
                        name=added["dataset_name"],
                        dataset_type=DatasetType(added["new_values"].get("dataset_type", "TABLE")),
                        dataset_id=(previous.dataset_id if previous else str(uuid4())),
                    )
                )
            elif added["object_type"] == "DATA_FIELD":
                ds_key = (added["namespace"], added["dataset_name"])
                ds_candidate = next((d for d in datasets if (d.namespace, d.name) == ds_key), None)
                if ds_candidate is None:
                    ds_candidate = existing_datasets.get(ds_key)
                if ds_candidate is not None:
                    nv = added.get("new_values", {})
                    previous_fields = existing_fields_map.get(ds_candidate.dataset_id, {})
                    previous_field = previous_fields.get(added["field_name"])
                    fields_by_dataset_id.setdefault(ds_candidate.dataset_id, []).append(
                        DataField(
                            dataset_id=ds_candidate.dataset_id,
                            name=added["field_name"],
                            native_data_type=nv.get("native_data_type", "TEXT"),
                            is_nullable=nv.get("is_nullable", True),
                            is_sensitive=nv.get("is_sensitive", False),
                            data_field_id=(
                                previous_field.data_field_id if previous_field else str(uuid4())
                            ),
                        )
                    )

        for removed in diff.removed_objects:
            if removed["object_type"] == "DATASET":
                ds_key = (removed["namespace"], removed["dataset_name"])
                ds_removed = existing_datasets.get(ds_key)
                if ds_removed is not None:
                    passivated_dataset_ids.append(ds_removed.dataset_id)
            elif removed["object_type"] == "DATA_FIELD":
                ds_key = (removed["namespace"], removed["dataset_name"])
                ds_field = existing_datasets.get(ds_key)
                if ds_field is not None:
                    field = existing_fields_map.get(ds_field.dataset_id, {}).get(
                        removed["field_name"]
                    )
                    if field is not None:
                        passivated_field_ids.append(field.data_field_id)

        audit_event = self._build_audit_event(
            actor_id=actor_id,
            correlation_id=correlation_id,
            action="DATA_SOURCE_METADATA_DIFF_APPLIED",
            object_type="DataSource",
            object_id=data_source.data_source_id,
            result=AuditResult.SUCCESS,
            reason_code=reason_code,
            new_values={
                "metadata_diff_id": metadata_diff_id,
                "passivated_datasets": len(passivated_dataset_ids),
                "passivated_fields": len(passivated_field_ids),
            },
        )
        prepared = self.transactional_audit.prepare(audit_event)
        applied = self.repository.apply_metadata_diff(
            metadata_diff_id,
            applied_by_actor_id=actor_id,
            reason_code=reason_code,
            expected_version=expected_version,
            datasets=datasets,
            fields_by_dataset_id=fields_by_dataset_id,
            passivated_dataset_ids=passivated_dataset_ids,
            passivated_field_ids=passivated_field_ids,
            audit_event=prepared,
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return applied

    def update_discovery_scope(
        self,
        *,
        actor_id: str,
        data_source_id: str,
        include_patterns: tuple[str, ...],
        exclude_patterns: tuple[str, ...],
        page_size: int,
        max_objects: int,
        timeout_seconds: int,
        expected_version: int,
        policy_version: str,
        correlation_id: str | None = None,
    ) -> DiscoveryScope:
        """Update the discovery scope for a data source."""
        correlation_id = _resolve_correlation_id(correlation_id)
        data_source = self.repository.get_data_source(data_source_id)
        if data_source.status is not DataSourceStatus.ACTIVE:
            raise ValidationError("Discovery scope requires an ACTIVE data source.")

        canonical_include = tuple(validate_discovery_pattern(p) for p in include_patterns)
        canonical_exclude = tuple(validate_discovery_pattern(p) for p in exclude_patterns)
        deduped_include = tuple(dict.fromkeys(canonical_include))
        deduped_exclude = tuple(dict.fromkeys(canonical_exclude))

        now = self.clock()
        scope = DiscoveryScope(
            data_source_id=data_source.data_source_id,
            include_patterns=deduped_include,
            exclude_patterns=deduped_exclude,
            page_size=page_size,
            max_objects=max_objects,
            timeout_seconds=timeout_seconds,
            policy_version=policy_version,
            updated_by_actor_id=actor_id,
            updated_at=now,
        )
        audit_event = self._build_audit_event(
            actor_id=actor_id,
            correlation_id=correlation_id,
            action="DATA_SOURCE_DISCOVERY_SCOPE_CHANGED",
            object_type="DataSource",
            object_id=data_source.data_source_id,
            result=AuditResult.SUCCESS,
            reason_code="DISCOVERY_SCOPE_CHANGED",
            new_values={
                "include_pattern_count": len(deduped_include),
                "exclude_pattern_count": len(deduped_exclude),
                "page_size": page_size,
                "max_objects": max_objects,
                "timeout_seconds": timeout_seconds,
            },
        )
        prepared = self.transactional_audit.prepare(audit_event)
        stored = self.repository.update_discovery_scope(
            scope,
            expected_version=expected_version,
            audit_event=prepared,
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return stored

    def run_profile(
        self,
        *,
        actor_id: str,
        dataset_id: str,
        options: ProfileOptions | None = None,
        correlation_id: str | None = None,
    ) -> DataProfile:
        correlation_id = _resolve_correlation_id(correlation_id)
        options = options or ProfileOptions()
        _validate_profile_options(options)
        policy = (
            self.profile_policy_resolver.resolve(options.policy_version)
            if self.profile_policy_resolver is not None
            else None
        )
        if options.policy_version is not None and policy is None:
            raise ValidationError("Requested profile policy version could not be resolved.")
        execution_options = replace(options, analysis_policy=policy)
        dataset = self.repository.get_dataset(dataset_id)
        fields = tuple(self.repository.list_data_fields(dataset_id))
        if not fields:
            raise ValidationError("Profile requires discovered DataField metadata.")
        _validate_profile_field_selection(options, fields)
        validate_freshness_field_scope(
            policy,
            fields,
            selected_field_names=options.field_names,
        )
        data_source = self.repository.get_data_source(dataset.data_source_id)
        if data_source.status not in {
            DataSourceStatus.TEST_SUCCEEDED,
            DataSourceStatus.ACTIVE,
        }:
            raise ValidationError("Profile requires a successful connection test.")
        connector = self.registry.get(data_source.source_type)
        if connector is None:
            profile = _profile_from_failure(
                dataset_id,
                options,
                ErrorClass.UNSUPPORTED_SOURCE,
                "No connector is registered for this source type.",
            )
            self._persist_profile(actor_id, correlation_id, profile)
            return profile

        started_at = utc_now()
        started = _perf_counter()
        try:
            secret = self.secret_resolver.resolve(data_source.secret_reference)
            computation = connector.profile_dataset(
                data_source,
                secret,
                dataset,
                fields,
                execution_options,
            )
        except ValidationError:
            raise
        except SecretResolutionError:
            profile = _profile_from_failure(
                dataset_id,
                options,
                ErrorClass.AUTHENTICATION,
                "Secret reference could not be resolved.",
                started_at=started_at,
                duration_ms=_elapsed_ms(started),
            )
            self._persist_profile(actor_id, correlation_id, profile)
            return profile
        except (
            DNSConnectionError,
            NetworkConnectionError,
            TimeoutConnectionError,
            AuthenticationConnectionError,
            TLSConnectionError,
            PermissionConnectionError,
            DriverConnectionError,
        ) as exc:
            profile = _profile_from_failure(
                dataset_id,
                options,
                _error_class_for_exception(exc),
                "Profile failed with a classified technical error.",
                started_at=started_at,
                duration_ms=_elapsed_ms(started),
            )
            self._persist_profile(actor_id, correlation_id, profile)
            return profile
        except Exception as exc:
            raise TechnicalError("Unexpected profile failure.") from exc

        protected_metrics = self.masking_policy.protect_profile_metrics(
            computation.metrics,
            {field.name: field.classification for field in fields},
        )
        try:
            effective_method = ProfileMethod(
                str(protected_metrics.get("method", options.method.value))
            )
        except ValueError as exc:
            raise TechnicalError("Connector returned an invalid profile method.") from exc
        effective_sample_ratio = protected_metrics.get("sample_ratio")
        if effective_sample_ratio is not None and not isinstance(
            effective_sample_ratio, (int, float)
        ):
            raise TechnicalError("Connector returned an invalid profile sample ratio.")
        data_observed_at = _latest_profile_observation(protected_metrics)
        protected_metrics["profile_contract"] = build_profile_contract(
            fields=fields,
            method=effective_method,
            sample_ratio=effective_sample_ratio,
            scope=options.scope,
            query_version=options.query_version,
            connector_version=options.connector_version,
            policy=policy,
            data_observed_at=data_observed_at,
            category_fingerprint_algorithm=protected_metrics.get("category_fingerprint_algorithm"),
            category_fingerprint_key_id=protected_metrics.get("category_fingerprint_key_id"),
            analysis_execution=protected_metrics.get("analysis_execution"),
        )
        profile = DataProfile(
            dataset_id=dataset_id,
            execution_id=str(uuid4()),
            method=effective_method,
            sample_ratio=effective_sample_ratio,
            metrics=protected_metrics,
            status=computation.status,
            duration_ms=_elapsed_ms(started),
            error_class=computation.error_class,
            message=computation.message,
            started_at=started_at,
            finished_at=utc_now(),
        )
        self._persist_profile(actor_id, correlation_id, profile)
        return profile

    def compare_profiles(
        self,
        *,
        actor_id: str,
        dataset_id: str,
        baseline_profile_id: str,
        current_profile_id: str,
        policy_version: str | None = None,
        correlation_id: str | None = None,
    ) -> ProfileComparison:
        correlation_id = _resolve_correlation_id(correlation_id)
        profiles = self.repository.list_data_profiles(dataset_id)
        by_id = {profile.profile_id: profile for profile in profiles}
        try:
            baseline = by_id[baseline_profile_id]
            current = by_id[current_profile_id]
        except KeyError as exc:
            raise ValidationError("Profile comparison references an unknown profile.") from exc
        policy = (
            self.profile_policy_resolver.resolve(policy_version)
            if self.profile_policy_resolver is not None
            else None
        )
        if policy_version is not None and policy is not None and policy.version != policy_version:
            raise ValidationError("Resolved profile policy version does not match request.")
        comparison = compare_profile_snapshots(
            baseline=baseline,
            current=current,
            history=profiles,
            policy=policy,
        )
        audit_event = self._build_audit_event(
            actor_id=actor_id,
            correlation_id=correlation_id,
            action="DATASET_PROFILES_COMPARED",
            object_type="Dataset",
            object_id=dataset_id,
            result=(
                AuditResult.SUCCESS
                if comparison.status is ProfileComparisonStatus.COMPLETED
                else AuditResult.FAILURE
            ),
            reason_code=f"PROFILE_COMPARISON_{comparison.status.value}",
            new_values={
                "comparison_id": comparison.comparison_id,
                "baseline_profile_id": comparison.baseline_profile_id,
                "current_profile_id": comparison.current_profile_id,
                "status": comparison.status.value,
                "policy_version": comparison.policy_version,
                "anomaly_candidate": comparison.anomaly_candidate,
                "signal_count": len(comparison.result.get("signals", [])),
            },
        )
        stored = self.repository.add_profile_comparison(
            comparison,
            audit_event=self.transactional_audit.prepare(audit_event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return stored

    def record_processing_inventory(
        self,
        *,
        actor_id: str,
        data_field_id: str,
        processing_purpose: str,
        legal_basis_reference: str,
        data_owner_id: str,
        retention_policy_id: str,
        access_role_codes: tuple[str, ...],
        cross_border_transfer: bool,
        recipient_groups: tuple[str, ...] = (),
        correlation_id: str | None = None,
    ) -> DataProcessingInventory:
        correlation_id = _resolve_correlation_id(correlation_id)
        data_field = self.repository.get_data_field(data_field_id)
        if data_field.classification is ClassificationCode.UNCLASSIFIED:
            raise ValidationError(
                "Processing inventory requires an explicitly classified DataField."
            )
        inventory = DataProcessingInventory(
            data_field_id=data_field_id,
            version_number=self.repository.next_processing_inventory_version(data_field_id),
            processing_purpose=processing_purpose,
            legal_basis_reference=legal_basis_reference,
            data_owner_id=data_owner_id,
            retention_policy_id=retention_policy_id,
            access_role_codes=access_role_codes,
            cross_border_transfer=cross_border_transfer,
            recipient_groups=recipient_groups,
        )
        try:
            validate_inventory(inventory)
        except InventoryValidationError as exc:
            raise ValidationError("Processing inventory references are invalid.") from exc

        audit_event = self._build_audit_event(
            actor_id=actor_id,
            correlation_id=correlation_id,
            action="DATA_PROCESSING_INVENTORY_RECORDED",
            object_type="DataField",
            object_id=data_field_id,
            result=AuditResult.SUCCESS,
            reason_code="PROCESSING_INVENTORY_RECORDED",
            new_values={
                "inventory_version": inventory.version_number,
                "classification": data_field.classification.value,
                "cross_border_transfer": inventory.cross_border_transfer,
                "access_role_count": len(inventory.access_role_codes),
                "recipient_group_count": len(inventory.recipient_groups),
            },
        )
        stored = self.repository.add_processing_inventory(
            inventory,
            audit_event=self.transactional_audit.prepare(audit_event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return stored

    def get_processing_inventory_coverage(
        self, *, data_source_id: str | None = None
    ) -> InventoryCoverageReport:
        items = self.repository.list_processing_inventory_coverage(data_source_id)
        missing_count = sum(item.inventory_version is None for item in items)
        if not items:
            status = InventoryCoverageStatus.NO_REQUIRED_FIELDS
        elif missing_count:
            status = InventoryCoverageStatus.INCOMPLETE
        else:
            status = InventoryCoverageStatus.COMPLETE
        return InventoryCoverageReport(
            status=status,
            total_required_count=len(items),
            complete_count=len(items) - missing_count,
            missing_count=missing_count,
            items=items,
        )

    def _persist_metadata_result(
        self,
        actor_id: str,
        correlation_id: str,
        result: MetadataDiscoveryResult,
        *,
        datasets: list[Dataset] | None = None,
        fields_by_dataset_id: dict[str, list[DataField]] | None = None,
    ) -> None:
        audit_event = self._build_audit_event(
            actor_id=actor_id,
            correlation_id=correlation_id,
            action="DATA_SOURCE_METADATA_DISCOVERED",
            object_type="DataSource",
            object_id=result.data_source_id,
            result=AuditResult.SUCCESS if result.succeeded else AuditResult.FAILURE,
            reason_code=(
                "METADATA_DISCOVERY_SUCCEEDED"
                if result.succeeded
                else _error_reason(result.error_class)
            ),
            new_values={
                "succeeded": result.succeeded,
                "duration_ms": result.duration_ms,
                "scanned_object_count": result.scanned_object_count,
                "error_class": result.error_class.value if result.error_class else None,
                "added_count": sum(
                    1 for change in result.changes if change.change_type is MetadataChangeType.ADDED
                ),
                "changed_count": sum(
                    1
                    for change in result.changes
                    if change.change_type is MetadataChangeType.CHANGED
                ),
                "removed_count": sum(
                    1
                    for change in result.changes
                    if change.change_type is MetadataChangeType.REMOVED
                ),
                "requires_rule_review": any(
                    change.requires_rule_review for change in result.changes
                ),
            },
        )
        prepared = self.transactional_audit.prepare(audit_event)
        if result.succeeded:
            if datasets is None or fields_by_dataset_id is None:
                raise ValidationError("Successful metadata discovery requires metadata values.")
            self.repository.replace_metadata(
                result.data_source_id,
                datasets,
                fields_by_dataset_id,
                result,
                audit_event=prepared,
                audit_outbox=self.transactional_audit,
            )
        else:
            self.repository.record_metadata_discovery_failure(
                result,
                audit_event=prepared,
                audit_outbox=self.transactional_audit,
            )
        self.transactional_audit.publish_pending()

    def _persist_profile(
        self,
        actor_id: str,
        correlation_id: str,
        profile: DataProfile,
    ) -> None:
        succeeded = profile.status in {ProfileStatus.COMPLETED, ProfileStatus.NO_DATA}
        audit_event = self._build_audit_event(
            actor_id=actor_id,
            correlation_id=correlation_id,
            action="DATASET_PROFILE_CREATED",
            object_type="Dataset",
            object_id=profile.dataset_id,
            result=AuditResult.SUCCESS if succeeded else AuditResult.FAILURE,
            reason_code=("PROFILE_COMPLETED" if succeeded else _error_reason(profile.error_class)),
            new_values={
                "profile_id": profile.profile_id,
                "method": profile.method.value,
                "sample_ratio": profile.sample_ratio,
                "status": profile.status.value,
                "duration_ms": profile.duration_ms,
                "error_class": profile.error_class.value if profile.error_class else None,
                "record_count": profile.metrics.get("record_count"),
                "sampled_count": profile.metrics.get("sampled_count"),
            },
        )
        self.repository.add_data_profile(
            profile,
            audit_event=self.transactional_audit.prepare(audit_event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()

    def _build_audit_event(
        self,
        *,
        actor_id: str,
        correlation_id: str,
        action: str,
        object_type: str,
        object_id: str,
        result: AuditResult,
        reason_code: str,
        new_values: dict[str, Any],
        old_values: dict[str, Any] | None = None,
        actor_type: str = "USER",
        session_id: str | None = None,
    ) -> AuditEventInput:
        return AuditEventInput(
            actor_id=actor_id,
            actor_type=actor_type,
            correlation_id=correlation_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            result=result,
            reason_code=reason_code,
            old_values=old_values or {},
            new_values=new_values,
            occurred_at=utc_now(),
            session_id=session_id,
        )

    def _publish_transactional_audit(self) -> None:
        status = self.transactional_audit.publish_pending()
        if status.failed_count:
            raise TechnicalError(
                "Transactional audit publication is pending.",
                code="DATA_SOURCE_AUDIT_UNAVAILABLE",
            )

    def _require_activation_policy(self) -> DataSourceActivationPolicy:
        if self.activation_policy is None:
            raise AuthorizationError("Data source activation policy is not configured.")
        return self.activation_policy

    def _authorize_activation_actor(
        self,
        context: ActorContext | None,
        *,
        required_roles: frozenset[str],
        data_source_id: str,
    ) -> ActorContext:
        return self._authorize_command_actor(
            context,
            required_roles=required_roles,
            data_source_id=data_source_id,
        )

    def _authorize_command_actor(
        self,
        context: ActorContext | None,
        *,
        required_roles: frozenset[str],
        data_source_id: str | None = None,
        require_enterprise_scope: bool = False,
    ) -> ActorContext:
        policy = self._require_activation_policy()
        now = self.clock()
        _require_aware_time(now, "Data source command clock")
        if not is_trusted_actor_context(context):
            raise AuthorizationError("Trusted actor context is required for data source command.")
        assert context is not None
        if context.issued_at > now or context.expires_at <= now:
            raise AuthorizationError("Actor context is not currently valid.")
        if context.policy_version != policy.actor_policy_version:
            raise AuthorizationError("Actor context policy version is not accepted.")
        if context.actor_type.value not in policy.allowed_actor_types:
            raise AuthorizationError("Actor type is not allowed for data source command.")
        if context.privileged:
            raise AuthorizationError("Privileged actor requires a separate approved workflow.")
        if not required_roles or context.roles.isdisjoint(required_roles):
            raise AuthorizationError("Actor lacks the required data source command role.")
        if require_enterprise_scope and not context.can_view_enterprise:
            raise AuthorizationError("Actor lacks enterprise scope for source creation.")
        if data_source_id is not None and data_source_id not in context.permitted_source_ids:
            raise AuthorizationError("Actor is outside the data source scope.")
        return context


def _elapsed_ms(started: float) -> int:
    return max(0, round((_perf_counter() - started) * 1000))


def _perf_counter() -> float:
    from time import perf_counter

    return perf_counter()


def _error_class_for_exception(exc: Exception) -> ErrorClass:
    if isinstance(exc, DNSConnectionError):
        return ErrorClass.DNS
    if isinstance(exc, NetworkConnectionError):
        return ErrorClass.NETWORK
    if isinstance(exc, TimeoutConnectionError):
        return ErrorClass.TIMEOUT
    if isinstance(exc, AuthenticationConnectionError):
        return ErrorClass.AUTHENTICATION
    if isinstance(exc, TLSConnectionError):
        return ErrorClass.TLS
    if isinstance(exc, PermissionConnectionError):
        return ErrorClass.PERMISSION
    return ErrorClass.DRIVER


def _diff_metadata(
    previous: dict[tuple[str, str], list[DataField]],
    datasets: list[Dataset],
    fields_by_dataset_id: dict[str, list[DataField]],
) -> list[MetadataChange]:
    changes: list[MetadataChange] = []
    current_keys = {(dataset.namespace, dataset.name): dataset for dataset in datasets}

    for dataset_key, dataset in current_keys.items():
        if dataset_key not in previous:
            changes.append(
                MetadataChange(
                    change_type=MetadataChangeType.ADDED,
                    object_type="DATASET",
                    namespace=dataset.namespace,
                    dataset_name=dataset.name,
                    new_values={"dataset_type": dataset.dataset_type.value},
                )
            )

        previous_fields = {field.name: field for field in previous.get(dataset_key, [])}
        current_fields = {
            field.name: field for field in fields_by_dataset_id.get(dataset.dataset_id, [])
        }
        for field_name, field in current_fields.items():
            previous_field = previous_fields.get(field_name)
            if previous_field is None:
                changes.append(
                    MetadataChange(
                        change_type=MetadataChangeType.ADDED,
                        object_type="DATA_FIELD",
                        namespace=dataset.namespace,
                        dataset_name=dataset.name,
                        field_name=field.name,
                        new_values=_field_signature(field),
                    )
                )
            elif _field_signature(previous_field) != _field_signature(field):
                changes.append(
                    MetadataChange(
                        change_type=MetadataChangeType.CHANGED,
                        object_type="DATA_FIELD",
                        namespace=dataset.namespace,
                        dataset_name=dataset.name,
                        field_name=field.name,
                        old_values=_field_signature(previous_field),
                        new_values=_field_signature(field),
                        requires_rule_review=True,
                    )
                )
        for field_name, previous_field in previous_fields.items():
            if field_name not in current_fields:
                changes.append(
                    MetadataChange(
                        change_type=MetadataChangeType.REMOVED,
                        object_type="DATA_FIELD",
                        namespace=dataset.namespace,
                        dataset_name=dataset.name,
                        field_name=previous_field.name,
                        old_values=_field_signature(previous_field),
                        requires_rule_review=True,
                    )
                )

    for namespace, dataset_name in previous:
        if (namespace, dataset_name) not in current_keys:
            changes.append(
                MetadataChange(
                    change_type=MetadataChangeType.REMOVED,
                    object_type="DATASET",
                    namespace=namespace,
                    dataset_name=dataset_name,
                    requires_rule_review=True,
                )
            )
    return changes


def _field_signature(field: DataField) -> dict[str, Any]:
    return {
        "native_data_type": field.native_data_type,
        "is_nullable": field.is_nullable,
        "is_sensitive": field.is_sensitive,
        "classification": field.classification.value,
        "classification_policy_version": field.classification_policy_version,
    }


def _profile_from_failure(
    dataset_id: str,
    options: ProfileOptions,
    error_class: ErrorClass,
    message: str,
    started_at: Any | None = None,
    duration_ms: int = 0,
) -> DataProfile:
    started_at = started_at or utc_now()
    return DataProfile(
        dataset_id=dataset_id,
        execution_id=str(uuid4()),
        method=options.method,
        sample_ratio=options.sample_ratio,
        metrics={},
        status=ProfileStatus.TECHNICAL_ERROR,
        duration_ms=duration_ms,
        error_class=error_class,
        message=message,
        started_at=started_at,
        finished_at=utc_now(),
    )


def _latest_profile_observation(metrics: Mapping[str, Any]) -> datetime | None:
    latest: datetime | None = None
    fields = metrics.get("fields")
    if not isinstance(fields, Mapping):
        return None
    for field_metrics in fields.values():
        if not isinstance(field_metrics, Mapping):
            continue
        value = field_metrics.get("freshness_max")
        if not isinstance(value, str):
            continue
        try:
            observed_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            continue
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            continue
        observed_at = observed_at.astimezone(timezone.utc)
        if latest is None or observed_at > latest:
            latest = observed_at
    return latest
