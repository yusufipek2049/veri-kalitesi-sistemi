"""Veri kaynağı uygulama servisi."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Callable, Protocol
from uuid import uuid4

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditResult,
    AuditSink,
    SQLiteTransactionalAudit,
)
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
    SecretResolutionError,
    TechnicalError,
    ValidationError,
)
from veri_kalitesi.data_sources.models import (
    ConnectionTestResult,
    DataField,
    DataProfile,
    DataSource,
    DataSourceActivationPolicy,
    DataSourceActivationRequest,
    DataSourceActivationStatus,
    DataSourceStatus,
    Dataset,
    ErrorClass,
    MetadataChange,
    MetadataChangeType,
    MetadataDiscoveryOptions,
    MetadataDiscoveryResult,
    ProfileMethod,
    ProfileOptions,
    ProfileStatus,
    SourceType,
    utc_now,
)
from veri_kalitesi.identity import ActorContext, ActorType, is_trusted_actor_context
from veri_kalitesi.data_sources.postgresql import is_read_only_sql
from veri_kalitesi.data_sources.repository import SQLiteDataSourceRepository
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

_FORBIDDEN_CONFIG_KEYS = {"password", "passwd", "token", "secret", "private_key", "api_key"}
_POSTGRESQL_SSL_MODES = {"require", "verify-ca", "verify-full"}


class BusinessCalendar(Protocol):
    @property
    def version(self) -> str: ...

    def add_business_days(self, start_at: datetime, business_days: int) -> datetime: ...


class DataSourceService:
    def __init__(
        self,
        repository: SQLiteDataSourceRepository,
        registry: ConnectorRegistry,
        secret_resolver: SecretResolver | None = None,
        *,
        audit_sink: AuditSink,
        transactional_audit: SQLiteTransactionalAudit,
        classification_policy: ClassificationPolicy | None = None,
        masking_policy: MaskingPolicy | None = None,
        activation_policy: DataSourceActivationPolicy | None = None,
        activation_calendar: BusinessCalendar | None = None,
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
        self.clock = clock
        if activation_policy is not None:
            _validate_activation_policy(activation_policy)
            _validate_activation_calendar(activation_policy, activation_calendar)

    def create_data_source(
        self,
        *,
        actor_id: str,
        name: str,
        source_type: str,
        connection_config: dict[str, Any],
        secret_reference: str,
        owner_user_id: str | None = None,
        correlation_id: str | None = None,
    ) -> DataSource:
        correlation_id = _resolve_correlation_id(correlation_id)
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
        self.transactional_audit.publish_pending()
        return created

    def test_connection(
        self,
        *,
        actor_id: str,
        data_source_id: str,
        correlation_id: str | None = None,
    ) -> ConnectionTestResult:
        correlation_id = _resolve_correlation_id(correlation_id)
        data_source = self.repository.get_data_source(data_source_id)
        connector = self.registry.get(data_source.source_type)
        if connector is None:
            result = ConnectionTestResult(
                data_source_id=data_source.data_source_id,
                succeeded=False,
                duration_ms=0,
                error_class=ErrorClass.UNSUPPORTED_SOURCE,
                message="No connector is registered for this source type.",
                source_info={"source_type": data_source.source_type.value},
            )
        else:
            try:
                secret = self.secret_resolver.resolve(data_source.secret_reference)
                result = connector.test_connection(data_source, secret)
            except SecretResolutionError:
                result = ConnectionTestResult(
                    data_source_id=data_source.data_source_id,
                    succeeded=False,
                    duration_ms=0,
                    error_class=ErrorClass.AUTHENTICATION,
                    message="Secret reference could not be resolved.",
                    source_info={"source_type": data_source.source_type.value},
                )
            except Exception as exc:
                raise TechnicalError("Unexpected connector failure.") from exc

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
        self.transactional_audit.publish_pending()
        return result

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
        if source.status is not DataSourceStatus.TEST_SUCCEEDED:
            raise ValidationError("Activation requires a successfully tested data source.")
        if not source.owner_user_id or not source.owner_user_id.strip():
            raise ValidationError("Activation requires a data owner.")
        latest_test = self.repository.latest_connection_test(data_source_id)
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
        self.transactional_audit.publish_pending()
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
        if request.status is not DataSourceActivationStatus.PENDING:
            raise ValidationError("Data source activation request is not pending.")
        if self._activation_request_expired(request):
            raise ValidationError(
                "Data source activation request has expired and must be recreated."
            )
        if request.policy_version != policy.version:
            raise ValidationError("Data source activation policy version changed.")
        if request.data_source_revision != source.revision:
            raise ValidationError("Data source activation request is for a stale revision.")
        if request.maker_actor_id == context.actor_id:
            raise AuthorizationError("Activation maker cannot approve the same change.")
        normalized_reason = reason_code.strip()
        if not normalized_reason:
            raise ValidationError("Activation decision reason code is required.")
        status = _parse_activation_decision(decision)
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
            else DataSourceStatus.TEST_SUCCEEDED
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
        self.transactional_audit.publish_pending()
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
            candidates = connector.discover_metadata(data_source, secret, options)
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
        result = MetadataDiscoveryResult(
            data_source_id=data_source.data_source_id,
            succeeded=True,
            duration_ms=_elapsed_ms(started),
            scanned_object_count=sum(len(fields) + 1 for fields in fields_by_dataset_id.values()),
            datasets=tuple(datasets),
            fields=tuple(field for fields in fields_by_dataset_id.values() for field in fields),
            changes=tuple(changes),
            message="Metadata discovery completed.",
        )
        self._persist_metadata_result(
            actor_id,
            correlation_id,
            result,
            datasets=datasets,
            fields_by_dataset_id=fields_by_dataset_id,
        )
        return result

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
        dataset = self.repository.get_dataset(dataset_id)
        fields = tuple(self.repository.list_data_fields(dataset_id))
        if not fields:
            raise ValidationError("Profile requires discovered DataField metadata.")
        _validate_profile_field_selection(options, fields)
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
            computation = connector.profile_dataset(data_source, secret, dataset, fields, options)
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
        profile = DataProfile(
            dataset_id=dataset_id,
            execution_id=str(uuid4()),
            method=options.method,
            sample_ratio=options.sample_ratio,
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
        policy = self._require_activation_policy()
        now = self.clock()
        _require_aware_time(now, "Data source activation clock")
        if not is_trusted_actor_context(context):
            raise AuthorizationError("Trusted actor context is required for source activation.")
        assert context is not None
        if context.issued_at > now or context.expires_at <= now:
            raise AuthorizationError("Actor context is not currently valid.")
        if context.policy_version != policy.actor_policy_version:
            raise AuthorizationError("Actor context policy version is not accepted.")
        if context.actor_type.value not in policy.allowed_actor_types:
            raise AuthorizationError("Actor type is not allowed for source activation.")
        if context.roles.isdisjoint(required_roles):
            raise AuthorizationError("Actor lacks the required source activation role.")
        if data_source_id not in context.permitted_source_ids:
            raise AuthorizationError("Actor is outside the data source scope.")
        return context


def _parse_source_type(source_type: str) -> SourceType:
    try:
        return SourceType(source_type.upper())
    except ValueError as exc:
        raise ValidationError("Unsupported source type.") from exc


def _resolve_correlation_id(correlation_id: str | None) -> str:
    if correlation_id is None:
        return str(uuid4())
    if not correlation_id.strip():
        raise ValidationError("correlation_id must not be blank.")
    return correlation_id


def _error_reason(error_class: ErrorClass | None) -> str:
    return error_class.value if error_class is not None else "UNKNOWN_TECHNICAL_ERROR"


def _parse_activation_decision(decision: str) -> DataSourceActivationStatus:
    normalized = decision.strip().upper()
    if normalized == "APPROVE":
        return DataSourceActivationStatus.APPROVED
    if normalized == "REJECT":
        return DataSourceActivationStatus.REJECTED
    raise ValidationError("Activation decision must be APPROVE or REJECT.")


def _validate_activation_policy(policy: DataSourceActivationPolicy) -> None:
    if not policy.version.strip() or not policy.actor_policy_version.strip():
        raise ValidationError("Data source activation policy versions are required.")
    if not policy.maker_roles or not policy.checker_roles:
        raise ValidationError("Data source activation maker and checker roles are required.")
    if any(not role.strip() for role in (*policy.maker_roles, *policy.checker_roles)):
        raise ValidationError("Data source activation roles must not be blank.")
    if not policy.allowed_actor_types or not policy.allowed_actor_types <= {"USER", "SERVICE"}:
        raise ValidationError("Data source activation actor types are invalid.")
    timing = (
        policy.target_business_days,
        policy.expiration_business_days,
        policy.business_calendar_version,
    )
    if any(value is not None for value in timing) and not all(
        value is not None for value in timing
    ):
        raise ValidationError("Data source activation timing policy must be complete.")
    if policy.expiration_business_days is not None:
        target = policy.target_business_days
        expiration = policy.expiration_business_days
        if (
            isinstance(target, bool)
            or isinstance(expiration, bool)
            or not isinstance(target, int)
            or not isinstance(expiration, int)
            or target < 1
            or expiration <= target
        ):
            raise ValidationError("Data source activation business-day limits are invalid.")
        if not policy.business_calendar_version or not policy.business_calendar_version.strip():
            raise ValidationError("Data source activation business calendar version is required.")
        if not policy.expiry_service_roles or any(
            not role.strip() for role in policy.expiry_service_roles
        ):
            raise ValidationError("Data source activation expiry service roles are required.")


def _validate_activation_calendar(
    policy: DataSourceActivationPolicy, calendar: BusinessCalendar | None
) -> None:
    if policy.expiration_business_days is None:
        return
    if calendar is None:
        raise ValidationError("Data source activation business calendar is required.")
    if calendar.version != policy.business_calendar_version:
        raise ValidationError(
            "Data source activation business calendar version does not match policy."
        )


def _require_aware_time(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(f"{label} must be timezone-aware.")


def _validate_name(name: str) -> None:
    if not name or not name.strip():
        raise ValidationError("DataSource name is required.")
    if len(name.strip()) > 200:
        raise ValidationError("DataSource name must be at most 200 characters.")


def _validate_secret_reference(secret_reference: str) -> None:
    if not secret_reference or not secret_reference.startswith("secret://"):
        raise ValidationError("Secret reference must use the secret:// scheme.")


def _validate_connection_config(source_type: SourceType, config: Mapping[str, Any]) -> None:
    if not isinstance(config, Mapping):
        raise ValidationError("Connection config must be an object.")
    _reject_raw_secrets(config)
    if source_type is SourceType.CSV:
        file_path = config.get("file_path")
        if not file_path or not isinstance(file_path, str):
            raise ValidationError("CSV file_path is required.")
        delimiter = config.get("delimiter", ",")
        if not isinstance(delimiter, str) or len(delimiter) != 1:
            raise ValidationError("CSV delimiter must be a single character.")
        encoding = config.get("encoding", "utf-8")
        if not isinstance(encoding, str) or not encoding:
            raise ValidationError("CSV encoding must be a non-empty string.")
    elif source_type is SourceType.POSTGRESQL:
        _validate_postgresql_config(config)


def _reject_raw_secrets(config: Mapping[str, Any]) -> None:
    for key, value in config.items():
        key_normalized = str(key).lower()
        if key_normalized in _FORBIDDEN_CONFIG_KEYS:
            raise ValidationError("Connection config must not contain raw secret fields.")
        if isinstance(value, Mapping):
            _reject_raw_secrets(value)


def _validate_postgresql_config(config: Mapping[str, Any]) -> None:
    host = config.get("host")
    if not host or not isinstance(host, str):
        raise ValidationError("PostgreSQL host is required.")

    port = config.get("port")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValidationError("PostgreSQL port must be an integer between 1 and 65535.")

    database = config.get("database")
    if not database or not isinstance(database, str):
        raise ValidationError("PostgreSQL database is required.")

    ssl_mode = config.get("ssl_mode")
    if ssl_mode not in _POSTGRESQL_SSL_MODES:
        raise ValidationError("PostgreSQL ssl_mode must require TLS verification.")

    connect_timeout_seconds = config.get("connect_timeout_seconds", 5)
    if (
        isinstance(connect_timeout_seconds, bool)
        or not isinstance(connect_timeout_seconds, int)
        or not 1 <= connect_timeout_seconds <= 60
    ):
        raise ValidationError("PostgreSQL connect_timeout_seconds must be between 1 and 60.")

    statement_timeout_ms = config.get("statement_timeout_ms", 5000)
    if (
        isinstance(statement_timeout_ms, bool)
        or not isinstance(statement_timeout_ms, int)
        or not 1 <= statement_timeout_ms <= 600_000
    ):
        raise ValidationError("PostgreSQL statement_timeout_ms must be between 1 and 600000.")

    test_query = config.get("test_query")
    if test_query is not None and (
        not isinstance(test_query, str) or not is_read_only_sql(test_query)
    ):
        raise ValidationError("PostgreSQL test_query must be a single read-only statement.")


def _validate_metadata_options(options: MetadataDiscoveryOptions) -> None:
    if options.page_size < 1 or options.page_size > 10_000:
        raise ValidationError("Metadata discovery page_size must be between 1 and 10000.")
    if options.max_objects < 1 or options.max_objects > 100_000:
        raise ValidationError("Metadata discovery max_objects must be between 1 and 100000.")
    if options.timeout_seconds < 1 or options.timeout_seconds > 3600:
        raise ValidationError("Metadata discovery timeout_seconds must be between 1 and 3600.")


def _validate_profile_options(options: ProfileOptions) -> None:
    if options.method is ProfileMethod.SAMPLE:
        if options.sample_ratio is None or not 0 < options.sample_ratio <= 1:
            raise ValidationError("Sample profile requires 0 < sample_ratio <= 1.")
    elif options.sample_ratio is not None and not 0 < options.sample_ratio <= 1:
        raise ValidationError("Profile sample_ratio must satisfy 0 < sample_ratio <= 1.")
    if options.method is not ProfileMethod.SAMPLE and options.sample_ratio is not None:
        raise ValidationError("sample_ratio is only valid for SAMPLE profile method.")


def _validate_profile_field_selection(
    options: ProfileOptions, fields: tuple[DataField, ...]
) -> None:
    field_names = {field.name for field in fields}
    missing_fields = set(options.field_names) - field_names
    if missing_fields:
        raise ValidationError("Profile selected fields must exist in metadata.")
    missing_key_fields = set(options.key_field_names) - field_names
    if missing_key_fields:
        raise ValidationError("Profile key fields must exist in metadata.")


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
