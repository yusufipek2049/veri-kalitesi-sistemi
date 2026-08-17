"""Ortak yönetişim talepleri için maker-checker komut servisi.

Güvenlik kuralları backend tarafında fail-closed uygulanır:
- Maker kendi talebini onaylayamaz veya reddedemez.
- Checker, talebin nesne kapsamı (dataset/source) için yetkili olmalıdır.
- Hedef nesnenin onaya esas sürümü değişirse talep INVALIDATED olur.
- Karar ile uygulama ayrı işlem ve ayrı audit olaylarıdır.
- Tekrarlanan uygulama komutları idempotenttir.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Generic, Mapping, Protocol, TypeVar
from uuid import uuid4

logger = logging.getLogger(__name__)

from veri_kalitesi.audit.models import AuditEventInput, AuditResult
from veri_kalitesi.audit.service import AuditSink
from veri_kalitesi.data_protection.policy import ClassificationCode
from veri_kalitesi.data_sources.errors import (
    ConflictError as DataSourceConflictError,
)
from veri_kalitesi.data_sources.errors import (
    NotFoundError as DataSourceNotFoundError,
)
from veri_kalitesi.data_sources.models import (
    CatalogItemStatus,
    Criticality,
    DataField,
    Dataset,
    MetadataDiff,
    MetadataDiffStatus,
    TimelinessNature,
)
from veri_kalitesi.data_sources.service_helpers import diff_object_key
from veri_kalitesi.executions.errors import (
    ExecutionConflictError as ExecutionConflictErr,
    ExecutionNotFoundError as ExecutionNotFoundErr,
    ExecutionValidationError as ExecutionValidationErr,
)
from veri_kalitesi.executions.models import (
    ExecutionMode,
    ExecutionStatus,
    RuleExecution,
)
from veri_kalitesi.executions.schedule_policy import is_within_band
from veri_kalitesi.executions.scheduling import Schedule, ScheduleType, SchedulingService
from veri_kalitesi.governance.errors import (
    GovernanceAuthorizationError,
    GovernanceConflictError,
    GovernanceNotFoundError,
    GovernanceValidationError,
)
from veri_kalitesi.governance.models import (
    GOVERNANCE_REASON_CODES,
    GovernanceApprovalPolicy,
    GovernanceApprovalRequest,
    GovernanceApprovalStatus,
    GovernanceRequestType,
    utc_now,
)
from veri_kalitesi.governance.repository import PostgreSQLGovernanceApprovalRepository
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.identity import ActorContext, is_trusted_actor_context
from veri_kalitesi.jobs.models import DeadLetterRecord, DeadLetterStatus
from veri_kalitesi.rules.models import QualityRule, RuleVersion

AuditT = TypeVar("AuditT", bound=PostgreSQLTransactionalAudit)


class GovernanceCatalog(Protocol):
    def get_dataset(self, dataset_id: str) -> Dataset: ...

    def get_data_field(self, field_id: str) -> DataField: ...

    def get_rule_version(self, rule_version_id: str) -> RuleVersion: ...

    def get_rule(self, quality_rule_id: str) -> QualityRule: ...

    def get_execution(self, execution_id: str) -> RuleExecution: ...

    def get_dead_letter(self, dead_letter_id: str) -> DeadLetterRecord: ...


class GovernanceOwnershipWriter(Protocol):
    """Onaylanan sahiplik kararını hedef nesneye uygulayan adaptör."""

    def apply_dataset_owner(
        self,
        *,
        dataset_id: str,
        owner_user_id: str,
        expected_version: int,
    ) -> Dataset: ...


class GovernanceMetadataWriter(Protocol):
    """Onaylanan metadata/sınıflandırma kararını hedef nesneye uygulayan adaptör."""

    def apply_dataset_metadata(
        self,
        *,
        dataset_id: str,
        updates: Mapping[str, Any],
        expected_version: int,
    ) -> Dataset: ...

    def apply_field_sensitivity(
        self,
        *,
        field_id: str,
        updates: Mapping[str, Any],
        expected_version: int,
    ) -> DataField: ...


class GovernanceDiffWriter(Protocol):
    """Onaylanan metadata diff seçimini kataloğa uygulayan adaptör."""

    def get_metadata_diff(self, metadata_diff_id: str) -> MetadataDiff: ...

    def dataset_versions_for_diff(
        self, data_source_id: str, dataset_keys: frozenset[tuple[str, str]]
    ) -> dict[str, int]: ...

    def apply_metadata_diff(
        self,
        *,
        actor_id: str,
        metadata_diff_id: str,
        reason_code: str,
        expected_version: int,
        selected_objects: frozenset[tuple[str, str, str, str, str | None]],
        correlation_id: str,
    ) -> MetadataDiff: ...


class GovernanceExecutionWriter(Protocol):
    """Onaylanan çalıştırma kararlarını hedef nesneye uygulayan adaptör."""

    def apply_manual_start(
        self,
        *,
        request: GovernanceApprovalRequest,
        actor_context: ActorContext,
    ) -> RuleExecution: ...

    def apply_cancel(
        self,
        *,
        request: GovernanceApprovalRequest,
        actor_context: ActorContext,
    ) -> RuleExecution: ...

    def apply_dead_letter_reprocess(
        self,
        *,
        request: GovernanceApprovalRequest,
        actor_context: ActorContext,
    ) -> object: ...


class GovernanceScheduleWriter(Protocol):
    """Onaylanan bant dışı zamanlayıcı kararını hedef nesneye uygulayan adaptör."""

    def apply_schedule_interval(
        self,
        *,
        request: GovernanceApprovalRequest,
        actor_context: ActorContext,
    ) -> Schedule: ...


class GovernanceNotificationSink(Protocol):
    """Yönetişim onay olaylarını bildirim kanalına yayınlayan adaptör."""

    def publish_governance_approval_event(
        self,
        *,
        event_type: str,
        approval_request_id: str,
        request_type: str,
        object_type: str,
        object_id: str,
        object_name: str,
        scope_type: str,
        scope_id: str,
        maker_actor_id: str,
        recipient_user_id: str,
        actor_context: ActorContext | None,
        correlation_id: str,
        payload: dict[str, Any],
    ) -> None: ...


class DatasetUpdater(Protocol):
    """OCC ile dataset alanı güncelleyen depo yüzeyi."""

    def update_dataset(
        self,
        *,
        dataset_id: str,
        updates: dict,
        expected_version: int,
    ) -> Dataset: ...


class GovernanceMetadataRepository(Protocol):
    """OCC ile dataset ve alan güncelleyen depo yüzeyi."""

    def update_dataset(
        self,
        *,
        dataset_id: str,
        updates: dict,
        expected_version: int,
    ) -> Dataset: ...

    def update_field(
        self,
        *,
        field_id: str,
        updates: dict,
        expected_version: int,
    ) -> DataField: ...


_OWNERSHIP_REQUEST_TYPES = frozenset(
    {
        GovernanceRequestType.DATASET_OWNER_ASSIGN,
        GovernanceRequestType.DATASET_OWNER_CHANGE,
    }
)

_EXECUTION_REQUEST_TYPES = frozenset(
    {
        GovernanceRequestType.EXECUTION_MANUAL_START,
        GovernanceRequestType.EXECUTION_CANCEL,
        GovernanceRequestType.DEAD_LETTER_REPROCESS,
    }
)

#: Kritik metadata alanları: doğrudan düzenlenemez, onaydan geçmelidir.
_CRITICAL_DATASET_ATTRIBUTES = frozenset({"criticality", "status", "timeliness_nature"})
_SENSITIVE_FIELD_ATTRIBUTES = frozenset({"is_sensitive", "classification"})


class GovernanceApprovalCommandService(Generic[AuditT]):
    def __init__(
        self,
        repository: PostgreSQLGovernanceApprovalRepository,
        catalog: GovernanceCatalog,
        ownership_writer: GovernanceOwnershipWriter,
        *,
        audit_sink: AuditSink,
        transactional_audit: AuditT,
        policy: GovernanceApprovalPolicy,
        metadata_writer: GovernanceMetadataWriter | None = None,
        diff_writer: GovernanceDiffWriter | None = None,
        execution_writer: GovernanceExecutionWriter | None = None,
        schedule_writer: GovernanceScheduleWriter | None = None,
        notification_sink: GovernanceNotificationSink | None = None,
        notification_recipient_provider: (
            Callable[[GovernanceApprovalRequest, str], list[str]] | None
        ) = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.repository = repository
        self.catalog = catalog
        self.ownership_writer = ownership_writer
        self.metadata_writer = metadata_writer
        self.diff_writer = diff_writer
        self.execution_writer = execution_writer
        self.schedule_writer = schedule_writer
        self.notification_sink = notification_sink
        self.notification_recipient_provider = notification_recipient_provider
        self.audit_sink = audit_sink
        self.transactional_audit = transactional_audit
        self.policy = policy
        self.clock = clock
        _validate_policy(policy)

    # ------------------------------------------------------------------
    # Maker: talep oluşturma
    # ------------------------------------------------------------------

    def submit_request(
        self,
        *,
        actor_context: ActorContext | None,
        request_type: str,
        object_id: str,
        reason_code: str,
        new_owner_user_id: str | None = None,
        proposed_changes: Mapping[str, Any] | None = None,
    ) -> GovernanceApprovalRequest:
        policy = self.policy
        parsed_type = _parse_request_type(request_type)
        context = self._authorize_actor(
            actor_context, required_roles=policy.maker_roles, dataset_ids=None
        )
        normalized_reason = _validate_reason_code(reason_code)
        requested_at = self.clock()
        if not _is_aware(requested_at):
            raise GovernanceValidationError("Governance clock must be timezone-aware.")
        if parsed_type in _OWNERSHIP_REQUEST_TYPES:
            request = self._prepare_ownership_request(
                context, parsed_type, object_id, new_owner_user_id, normalized_reason, requested_at
            )
        elif parsed_type is GovernanceRequestType.METADATA_CRITICAL_CHANGE:
            request = self._prepare_dataset_metadata_request(
                context, object_id, proposed_changes, normalized_reason, requested_at
            )
        elif parsed_type is GovernanceRequestType.FIELD_SENSITIVITY_MARK:
            request = self._prepare_field_sensitivity_request(
                context, object_id, proposed_changes, normalized_reason, requested_at
            )
        elif parsed_type is GovernanceRequestType.METADATA_DIFF_APPLICATION:
            request = self._prepare_diff_application_request(
                context, object_id, proposed_changes, normalized_reason, requested_at
            )
        elif parsed_type is GovernanceRequestType.EXECUTION_MANUAL_START:
            request = self._prepare_execution_start_request(
                context, object_id, proposed_changes, normalized_reason, requested_at
            )
        elif parsed_type is GovernanceRequestType.EXECUTION_CANCEL:
            request = self._prepare_execution_cancel_request(
                context, object_id, proposed_changes, normalized_reason, requested_at
            )
        elif parsed_type is GovernanceRequestType.DEAD_LETTER_REPROCESS:
            request = self._prepare_execution_dead_letter_request(
                context, object_id, normalized_reason, requested_at
            )
        elif parsed_type is GovernanceRequestType.SCHEDULE_INTERVAL_EXCEPTION:
            request = self._prepare_schedule_interval_request(
                context, object_id, proposed_changes, normalized_reason, requested_at
            )
        else:
            raise GovernanceValidationError("Governance request type is not governed.")
        audit_event = self._build_audit_event(
            context.actor_id,
            context.correlation_id,
            "GOVERNANCE_APPROVAL_REQUESTED",
            request.object_id,
            AuditResult.SUCCESS,
            "GOVERNANCE_APPROVAL_REQUESTED",
            {
                "approval_request_id": request.approval_request_id,
                "request_type": parsed_type.value,
                "policy_version": policy.version,
                "status": request.status.value,
            },
            actor_type=context.actor_type.value,
            session_id=context.session_id,
            object_type=request.object_type,
        )
        stored = self.repository.add(
            request,
            audit_event=self.transactional_audit.prepare(audit_event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        self._publish_governance_notification(
            event_type="GOVERNANCE_APPROVAL_REQUESTED",
            request=stored,
            recipient_user_id=self._resolve_checker_recipient(stored),
            actor_context=actor_context,
            correlation_id=context.correlation_id,
            payload={
                "request_type": parsed_type.value,
                "maker_actor_id": context.actor_id,
                "object_type": stored.object_type,
                "object_id": stored.object_id,
                "approval_request_id": stored.approval_request_id,
                "reason_code": normalized_reason,
            },
        )
        return stored

    def _prepare_ownership_request(
        self,
        context: ActorContext,
        parsed_type: GovernanceRequestType,
        object_id: str,
        new_owner_user_id: str | None,
        reason_code: str,
        requested_at: datetime,
    ) -> GovernanceApprovalRequest:
        if new_owner_user_id is None:
            raise GovernanceValidationError(
                "Owner user identifier is required for ownership requests."
            )
        dataset = self._get_dataset(object_id)
        if dataset.dataset_id not in context.permitted_dataset_ids:
            raise GovernanceAuthorizationError(
                "Maker is outside the dataset scope for governance submission."
            )
        normalized_owner = _validate_owner(new_owner_user_id)
        if parsed_type is GovernanceRequestType.DATASET_OWNER_ASSIGN:
            if dataset.owner_user_id and dataset.owner_user_id.strip():
                raise GovernanceValidationError(
                    "Dataset already has an owner; use DATASET_OWNER_CHANGE."
                )
        else:
            if not dataset.owner_user_id or not dataset.owner_user_id.strip():
                raise GovernanceValidationError("Dataset has no owner; use DATASET_OWNER_ASSIGN.")
            if dataset.owner_user_id == normalized_owner:
                raise GovernanceValidationError("New owner must differ from the current owner.")
        return GovernanceApprovalRequest(
            request_type=parsed_type,
            object_type="Dataset",
            object_id=dataset.dataset_id,
            scope_type="DATASET",
            scope_id=dataset.dataset_id,
            scope_version=dataset.version,
            maker_actor_id=context.actor_id,
            maker_roles=tuple(sorted(context.roles)),
            policy_version=self.policy.version,
            correlation_id=context.correlation_id,
            change_summary={
                "before": {"owner_user_id": dataset.owner_user_id},
                "after": {"owner_user_id": normalized_owner},
            },
            status=GovernanceApprovalStatus.SUBMITTED,
            reason_code=reason_code,
            requested_at=requested_at,
        )

    def _prepare_dataset_metadata_request(
        self,
        context: ActorContext,
        object_id: str,
        proposed_changes: Mapping[str, Any] | None,
        reason_code: str,
        requested_at: datetime,
    ) -> GovernanceApprovalRequest:
        dataset = self._get_dataset(object_id)
        if dataset.dataset_id not in context.permitted_dataset_ids:
            raise GovernanceAuthorizationError(
                "Maker is outside the dataset scope for governance submission."
            )
        updates = _validate_proposed_changes(
            proposed_changes, _CRITICAL_DATASET_ATTRIBUTES, object_label="dataset"
        )
        _normalize_enum_attribute(updates, "criticality", Criticality, label="criticality")
        _normalize_enum_attribute(updates, "status", CatalogItemStatus, label="status")
        _normalize_enum_attribute(
            updates, "timeliness_nature", TimelinessNature, label="timeliness_nature"
        )
        for attribute, value in updates.items():
            if _attribute_value(dataset, attribute) == value:
                raise GovernanceValidationError("Proposed metadata change must modify the dataset.")
        return GovernanceApprovalRequest(
            request_type=GovernanceRequestType.METADATA_CRITICAL_CHANGE,
            object_type="Dataset",
            object_id=dataset.dataset_id,
            scope_type="DATASET",
            scope_id=dataset.dataset_id,
            scope_version=dataset.version,
            maker_actor_id=context.actor_id,
            maker_roles=tuple(sorted(context.roles)),
            policy_version=self.policy.version,
            correlation_id=context.correlation_id,
            change_summary={
                "before": {
                    attribute: _attribute_value(dataset, attribute) for attribute in updates
                },
                "after": updates,
            },
            status=GovernanceApprovalStatus.SUBMITTED,
            reason_code=reason_code,
            requested_at=requested_at,
        )

    def _prepare_field_sensitivity_request(
        self,
        context: ActorContext,
        object_id: str,
        proposed_changes: Mapping[str, Any] | None,
        reason_code: str,
        requested_at: datetime,
    ) -> GovernanceApprovalRequest:
        data_field = self._get_data_field(object_id)
        if data_field.dataset_id not in context.permitted_dataset_ids:
            raise GovernanceAuthorizationError(
                "Maker is outside the dataset scope for governance submission."
            )
        updates = _validate_proposed_changes(
            proposed_changes, _SENSITIVE_FIELD_ATTRIBUTES, object_label="field"
        )
        if "is_sensitive" in updates and not isinstance(updates["is_sensitive"], bool):
            raise GovernanceValidationError("Field sensitivity mark must be a boolean.")
        _normalize_enum_attribute(
            updates, "classification", ClassificationCode, label="classification"
        )
        for attribute, value in updates.items():
            if _attribute_value(data_field, attribute) == value:
                raise GovernanceValidationError(
                    "Proposed sensitivity change must modify the field."
                )
        return GovernanceApprovalRequest(
            request_type=GovernanceRequestType.FIELD_SENSITIVITY_MARK,
            object_type="DataField",
            object_id=data_field.data_field_id,
            scope_type="DATASET",
            scope_id=data_field.dataset_id,
            scope_version=data_field.version,
            maker_actor_id=context.actor_id,
            maker_roles=tuple(sorted(context.roles)),
            policy_version=self.policy.version,
            correlation_id=context.correlation_id,
            change_summary={
                "before": {
                    attribute: _attribute_value(data_field, attribute) for attribute in updates
                },
                "after": updates,
            },
            status=GovernanceApprovalStatus.SUBMITTED,
            reason_code=reason_code,
            requested_at=requested_at,
        )

    def _prepare_diff_application_request(
        self,
        context: ActorContext,
        object_id: str,
        proposed_changes: Mapping[str, Any] | None,
        reason_code: str,
        requested_at: datetime,
    ) -> GovernanceApprovalRequest:
        writer = self._require_diff_writer()
        diff = self._get_metadata_diff(object_id)
        if diff.status is not MetadataDiffStatus.PENDING:
            raise GovernanceValidationError("Metadata diff must be pending to request application.")
        selected = _validate_diff_selection(diff, proposed_changes)
        dataset_keys = frozenset((entry[2], entry[3]) for entry in selected)
        dataset_versions = writer.dataset_versions_for_diff(diff.data_source_id, dataset_keys)
        _assert_full_dataset_scope(context, frozenset(dataset_versions.keys()))
        return GovernanceApprovalRequest(
            request_type=GovernanceRequestType.METADATA_DIFF_APPLICATION,
            object_type="MetadataDiff",
            object_id=diff.metadata_diff_id,
            scope_type="DATA_SOURCE",
            scope_id=diff.data_source_id,
            scope_version=diff.version,
            maker_actor_id=context.actor_id,
            maker_roles=tuple(sorted(context.roles)),
            policy_version=self.policy.version,
            correlation_id=context.correlation_id,
            change_summary={
                "before": {"status": "PENDING", "dataset_versions": dataset_versions},
                "after": {"status": "APPLIED"},
                "selected": [
                    list(entry)
                    for entry in sorted(
                        selected, key=lambda entry: tuple(part or "" for part in entry)
                    )
                ],
                "counts": {
                    "added": sum(1 for entry in selected if entry[0] == "ADDED"),
                    "changed": sum(1 for entry in selected if entry[0] == "CHANGED"),
                    "removed": sum(1 for entry in selected if entry[0] == "REMOVED"),
                },
            },
            status=GovernanceApprovalStatus.SUBMITTED,
            reason_code=reason_code,
            requested_at=requested_at,
        )

    # ------------------------------------------------------------------
    # Execution prepare methods
    # ------------------------------------------------------------------

    def _prepare_execution_start_request(
        self,
        context: ActorContext,
        object_id: str,
        proposed_changes: Mapping[str, Any] | None,
        reason_code: str,
        requested_at: datetime,
    ) -> GovernanceApprovalRequest:
        if not proposed_changes or "rule_version_ids" not in proposed_changes:
            raise GovernanceValidationError(
                "Execution start request requires proposed rule_version_ids."
            )
        rule_version_ids = tuple(proposed_changes["rule_version_ids"])
        if not rule_version_ids:
            raise GovernanceValidationError("At least one rule_version_id is required.")
        execution_mode_raw = proposed_changes.get("execution_mode", "OFFICIAL")
        try:
            execution_mode = ExecutionMode(execution_mode_raw)
        except (ValueError, TypeError) as exc:
            raise GovernanceValidationError("Invalid execution mode.") from exc
        dataset_ids = self._resolve_execution_dataset_ids(rule_version_ids)
        if not dataset_ids:
            raise GovernanceNotFoundError(
                "Could not resolve any dataset for the given rule versions."
            )
        _assert_full_dataset_scope(context, dataset_ids)
        dataset_versions = self._build_dataset_versions(dataset_ids)
        primary_dataset_id = sorted(dataset_ids)[0]
        return GovernanceApprovalRequest(
            request_type=GovernanceRequestType.EXECUTION_MANUAL_START,
            object_type="RuleExecution",
            object_id=object_id,
            scope_type="DATASET",
            scope_id=primary_dataset_id,
            scope_version=0,
            maker_actor_id=context.actor_id,
            maker_roles=tuple(sorted(context.roles)),
            policy_version=self.policy.version,
            correlation_id=context.correlation_id,
            change_summary={
                "before": {"status": None, "dataset_versions": dataset_versions},
                "after": {
                    "rule_version_ids": list(rule_version_ids),
                    "execution_mode": execution_mode.value,
                },
            },
            status=GovernanceApprovalStatus.SUBMITTED,
            reason_code=reason_code,
            requested_at=requested_at,
        )

    def _prepare_execution_cancel_request(
        self,
        context: ActorContext,
        object_id: str,
        proposed_changes: Mapping[str, Any] | None,
        reason_code: str,
        requested_at: datetime,
    ) -> GovernanceApprovalRequest:
        execution = self._get_execution(object_id)
        if execution.status in {
            ExecutionStatus.SUCCESS,
            ExecutionStatus.TECHNICAL_ERROR,
            ExecutionStatus.TIMEOUT,
            ExecutionStatus.CANCELLED,
        }:
            raise GovernanceValidationError("Cannot request cancellation of a terminal execution.")
        dataset_ids = self._resolve_execution_dataset_ids(execution.rule_version_ids)
        _assert_full_dataset_scope(context, dataset_ids)
        cancel_reason = ""
        if proposed_changes and "reason" in proposed_changes:
            cancel_reason = str(proposed_changes["reason"])
        dataset_versions = self._build_dataset_versions(dataset_ids)
        primary_dataset_id = sorted(dataset_ids)[0]
        return GovernanceApprovalRequest(
            request_type=GovernanceRequestType.EXECUTION_CANCEL,
            object_type="RuleExecution",
            object_id=execution.execution_id,
            scope_type="DATASET",
            scope_id=primary_dataset_id,
            scope_version=0,
            maker_actor_id=context.actor_id,
            maker_roles=tuple(sorted(context.roles)),
            policy_version=self.policy.version,
            correlation_id=context.correlation_id,
            change_summary={
                "before": {
                    "status": execution.status.value,
                    "dataset_versions": dataset_versions,
                },
                "after": {
                    "status": "CANCELLED",
                    "reason": cancel_reason,
                },
            },
            status=GovernanceApprovalStatus.SUBMITTED,
            reason_code=reason_code,
            requested_at=requested_at,
        )

    def _prepare_execution_dead_letter_request(
        self,
        context: ActorContext,
        object_id: str,
        reason_code: str,
        requested_at: datetime,
    ) -> GovernanceApprovalRequest:
        letter = self._get_dead_letter(object_id)
        if letter.status is DeadLetterStatus.REPROCESSED:
            raise GovernanceValidationError("Dead letter has already been reprocessed.")
        execution = self._get_execution(letter.job_id)
        dataset_ids = self._resolve_execution_dataset_ids(execution.rule_version_ids)
        _assert_full_dataset_scope(context, dataset_ids)
        dataset_versions = self._build_dataset_versions(dataset_ids)
        primary_dataset_id = sorted(dataset_ids)[0]
        return GovernanceApprovalRequest(
            request_type=GovernanceRequestType.DEAD_LETTER_REPROCESS,
            object_type="DeadLetterRecord",
            object_id=letter.dead_letter_id,
            scope_type="DATASET",
            scope_id=primary_dataset_id,
            scope_version=0,
            maker_actor_id=context.actor_id,
            maker_roles=tuple(sorted(context.roles)),
            policy_version=self.policy.version,
            correlation_id=context.correlation_id,
            change_summary={
                "before": {
                    "status": letter.status.value,
                    "dataset_versions": dataset_versions,
                },
                "after": {"status": "REPROCESSED"},
            },
            status=GovernanceApprovalStatus.SUBMITTED,
            reason_code=reason_code,
            requested_at=requested_at,
        )

    def _prepare_schedule_interval_request(
        self,
        context: ActorContext,
        object_id: str,
        proposed_changes: Mapping[str, Any] | None,
        reason_code: str,
        requested_at: datetime,
    ) -> GovernanceApprovalRequest:
        dataset = self._get_dataset(object_id)
        if dataset.dataset_id not in context.permitted_dataset_ids:
            raise GovernanceAuthorizationError(
                "Maker is outside the dataset scope for governance submission."
            )
        if dataset.timeliness_nature is None:
            raise GovernanceValidationError(
                "Dataset timeliness nature must be assigned before a schedule exception request."
            )
        if not proposed_changes or not isinstance(proposed_changes.get("schedule"), Mapping):
            raise GovernanceValidationError(
                "Schedule exception request requires a proposed schedule definition."
            )
        proposal = proposed_changes["schedule"]
        raw_type = str(proposal.get("schedule_type", "")).strip().upper()
        try:
            schedule_type = ScheduleType(raw_type)
        except ValueError as exc:
            raise GovernanceValidationError("Proposed schedule type is invalid.") from exc
        interval_minutes = proposal.get("interval_minutes")
        if interval_minutes is not None and (
            isinstance(interval_minutes, bool) or not isinstance(interval_minutes, int)
        ):
            raise GovernanceValidationError("Proposed interval_minutes must be an integer.")
        if is_within_band(dataset.timeliness_nature, schedule_type, interval_minutes):
            raise GovernanceValidationError(
                "Proposed schedule is within the recommended band; no governance request needed."
            )
        raw_rule_ids = proposal.get("rule_version_ids")
        if not isinstance(raw_rule_ids, (list, tuple)) or not raw_rule_ids:
            raise GovernanceValidationError("Proposed schedule requires rule_version_ids.")
        rule_version_ids = tuple(str(value) for value in raw_rule_ids)
        _assert_full_dataset_scope(context, self._resolve_execution_dataset_ids(rule_version_ids))
        name = str(proposal.get("name", "")).strip()
        timezone_name = str(proposal.get("timezone_name", "")).strip()
        if not name or not timezone_name:
            raise GovernanceValidationError("Proposed schedule requires name and timezone_name.")
        schedule_proposal = {
            "schedule_id": str(uuid4()),
            "name": name,
            "schedule_type": schedule_type.value,
            "timezone_name": timezone_name,
            "rule_version_ids": list(rule_version_ids),
            "interval_minutes": interval_minutes,
            "local_time": proposal.get("local_time"),
            "day_of_week": proposal.get("day_of_week"),
            "day_of_month": proposal.get("day_of_month"),
        }
        return GovernanceApprovalRequest(
            request_type=GovernanceRequestType.SCHEDULE_INTERVAL_EXCEPTION,
            object_type="Dataset",
            object_id=dataset.dataset_id,
            scope_type="DATASET",
            scope_id=dataset.dataset_id,
            scope_version=dataset.version,
            maker_actor_id=context.actor_id,
            maker_roles=tuple(sorted(context.roles)),
            policy_version=self.policy.version,
            correlation_id=context.correlation_id,
            change_summary={
                "before": {"timeliness_nature": dataset.timeliness_nature.value},
                "after": {"schedule": schedule_proposal},
            },
            status=GovernanceApprovalStatus.SUBMITTED,
            reason_code=reason_code,
            requested_at=requested_at,
        )

    def _resolve_execution_dataset_ids(self, rule_version_ids: tuple[str, ...]) -> frozenset[str]:
        dataset_ids: set[str] = set()
        for vid in rule_version_ids:
            try:
                version = self.catalog.get_rule_version(vid)
                rule = self.catalog.get_rule(version.quality_rule_id)
                dataset_ids.add(rule.dataset_id)
            except (DataSourceNotFoundError, KeyError, AttributeError):
                continue
        return frozenset(dataset_ids)

    def _build_dataset_versions(self, dataset_ids: frozenset[str]) -> dict[str, int]:
        result: dict[str, int] = {}
        for dataset_id in sorted(dataset_ids):
            try:
                dataset = self._get_dataset(dataset_id)
                result[dataset_id] = dataset.version
            except GovernanceNotFoundError:
                result[dataset_id] = 0
        return result

    def _get_execution(self, execution_id: str) -> RuleExecution:
        try:
            return self.catalog.get_execution(execution_id)
        except (ExecutionNotFoundErr, KeyError) as exc:
            raise GovernanceNotFoundError("Governance target execution not found.") from exc

    def _get_dead_letter(self, dead_letter_id: str) -> DeadLetterRecord:
        try:
            return self.catalog.get_dead_letter(dead_letter_id)
        except (KeyError, Exception) as exc:
            raise GovernanceNotFoundError("Governance target dead letter not found.") from exc

    # ------------------------------------------------------------------
    # Checker: karar verme
    # ------------------------------------------------------------------

    def decide_request(
        self,
        *,
        actor_context: ActorContext | None,
        approval_request_id: str,
        decision: str,
        reason_code: str,
    ) -> GovernanceApprovalRequest:
        policy = self.policy
        request = self.repository.get(approval_request_id)
        context = self._authorize_actor(
            actor_context,
            required_roles=policy.checker_roles,
            dataset_ids=_request_scope_dataset_ids(request),
        )
        if request.status is not GovernanceApprovalStatus.SUBMITTED:
            raise GovernanceValidationError("Governance approval request is not pending.")
        if request.maker_actor_id == context.actor_id:
            self._record_violation(context, request, "MAKER_SELF_DECISION")
            raise GovernanceAuthorizationError("Maker cannot approve or reject the same change.")
        if self._request_expired(request):
            expired = _replace_status(
                request,
                GovernanceApprovalStatus.EXPIRED,
                decided_at=self.clock(),
                reason_code="GOVERNANCE.APPROVAL.EXPIRED",
            )
            self._transition(
                request, expired, action="GOVERNANCE_APPROVAL_EXPIRED", actor_id=context.actor_id
            )
            raise GovernanceValidationError(
                "Governance approval request has expired and must be recreated."
            )
        self._assert_object_unchanged(
            request, action="GOVERNANCE_APPROVAL_INVALIDATED", actor_id=context.actor_id
        )
        status = _parse_decision(decision)
        normalized_reason = _validate_reason_code(reason_code)
        decided = _replace_status(
            request,
            status,
            checker_actor_id=context.actor_id,
            checker_role=_first_matching_role(context.roles, policy.checker_roles),
            reason_code=normalized_reason,
            decided_at=self.clock(),
        )
        stored = self._transition(
            request, decided, action="GOVERNANCE_APPROVAL_DECIDED", actor_id=context.actor_id
        )
        self._publish_governance_notification(
            event_type="GOVERNANCE_APPROVAL_DECIDED",
            request=stored,
            recipient_user_id=request.maker_actor_id,
            actor_context=actor_context,
            correlation_id=context.correlation_id,
            payload={
                "request_type": request.request_type.value,
                "maker_actor_id": request.maker_actor_id,
                "object_type": request.object_type,
                "object_id": request.object_id,
                "approval_request_id": request.approval_request_id,
                "decision": status.value,
                "reason_code": normalized_reason,
                "checker_actor_id": context.actor_id,
            },
        )
        if status is GovernanceApprovalStatus.REJECTED:
            self._publish_governance_notification(
                event_type="GOVERNANCE_APPROVAL_REJECTED",
                request=stored,
                recipient_user_id=context.actor_id,
                actor_context=actor_context,
                correlation_id=context.correlation_id,
                payload={
                    "request_type": request.request_type.value,
                    "maker_actor_id": request.maker_actor_id,
                    "object_type": request.object_type,
                    "object_id": request.object_id,
                    "approval_request_id": request.approval_request_id,
                    "decision": status.value,
                    "reason_code": normalized_reason,
                    "checker_actor_id": context.actor_id,
                },
            )
        return stored

    # ------------------------------------------------------------------
    # Maker: geri çekme
    # ------------------------------------------------------------------

    def withdraw_request(
        self,
        *,
        actor_context: ActorContext | None,
        approval_request_id: str,
        reason_code: str,
    ) -> GovernanceApprovalRequest:
        policy = self.policy
        request = self.repository.get(approval_request_id)
        context = self._authorize_actor(
            actor_context,
            required_roles=policy.maker_roles,
            dataset_ids=_request_scope_dataset_ids(request),
        )
        if request.status is not GovernanceApprovalStatus.SUBMITTED:
            raise GovernanceValidationError("Governance approval request is not pending.")
        if request.maker_actor_id != context.actor_id:
            raise GovernanceAuthorizationError("Only the approval request maker can withdraw it.")
        normalized_reason = _validate_reason_code(reason_code)
        withdrawn = _replace_status(
            request,
            GovernanceApprovalStatus.WITHDRAWN,
            reason_code=normalized_reason,
            decided_at=self.clock(),
        )
        stored = self._transition(
            request, withdrawn, action="GOVERNANCE_APPROVAL_WITHDRAWN", actor_id=context.actor_id
        )
        self._publish_governance_notification(
            event_type="GOVERNANCE_APPROVAL_WITHDRAWN",
            request=stored,
            recipient_user_id=request.maker_actor_id,
            actor_context=actor_context,
            correlation_id=context.correlation_id,
            payload={
                "request_type": request.request_type.value,
                "maker_actor_id": request.maker_actor_id,
                "object_type": request.object_type,
                "object_id": request.object_id,
                "approval_request_id": request.approval_request_id,
                "reason_code": normalized_reason,
            },
        )
        return stored

    # ------------------------------------------------------------------
    # Applier: kararı uygulama (idempotent)
    # ------------------------------------------------------------------

    def apply_request(
        self,
        *,
        actor_context: ActorContext | None,
        approval_request_id: str,
    ) -> GovernanceApprovalRequest:
        policy = self.policy
        request = self.repository.get(approval_request_id)
        context = self._authorize_actor(
            actor_context,
            required_roles=policy.applier_roles,
            dataset_ids=_request_scope_dataset_ids(request),
        )
        if request.status is GovernanceApprovalStatus.APPLIED:
            return request
        if request.status is not GovernanceApprovalStatus.APPROVED:
            raise GovernanceValidationError("Only an approved governance request can be applied.")
        if request.request_type in _OWNERSHIP_REQUEST_TYPES:
            return self._apply_ownership(request, context)
        if request.request_type is GovernanceRequestType.METADATA_CRITICAL_CHANGE:
            return self._apply_dataset_metadata(request, context)
        if request.request_type is GovernanceRequestType.FIELD_SENSITIVITY_MARK:
            return self._apply_field_sensitivity(request, context)
        if request.request_type is GovernanceRequestType.METADATA_DIFF_APPLICATION:
            return self._apply_diff_application(request, context)
        if request.request_type in _EXECUTION_REQUEST_TYPES:
            return self._apply_execution(request, context)
        if request.request_type is GovernanceRequestType.SCHEDULE_INTERVAL_EXCEPTION:
            return self._apply_schedule_interval(request, context)
        raise GovernanceValidationError("Governance request type cannot be applied.")

    def _apply_ownership(
        self, request: GovernanceApprovalRequest, context: ActorContext
    ) -> GovernanceApprovalRequest:
        dataset = self._get_dataset(request.object_id)
        expected_owner = str(request.change_summary.get("after", {}).get("owner_user_id", ""))
        if dataset.owner_user_id == expected_owner and dataset.version > request.scope_version:
            applied = _replace_status(
                request,
                GovernanceApprovalStatus.APPLIED,
                applied_at=self.clock(),
            )
            return self._transition(
                request, applied, action="GOVERNANCE_APPROVAL_APPLIED", actor_id=context.actor_id
            )
        try:
            self.ownership_writer.apply_dataset_owner(
                dataset_id=request.object_id,
                owner_user_id=expected_owner,
                expected_version=request.scope_version,
            )
        except DataSourceConflictError:
            self._fail_application(request, context)
            raise GovernanceConflictError(
                "Governance decision could not be applied; object version changed."
            ) from None
        applied = _replace_status(
            request,
            GovernanceApprovalStatus.APPLIED,
            applied_at=self.clock(),
        )
        return self._transition(
            request, applied, action="GOVERNANCE_APPROVAL_APPLIED", actor_id=context.actor_id
        )

    def _apply_dataset_metadata(
        self, request: GovernanceApprovalRequest, context: ActorContext
    ) -> GovernanceApprovalRequest:
        writer = self._require_metadata_writer()
        dataset = self._get_dataset(request.object_id)
        after = dict(request.change_summary.get("after", {}))
        if self._already_applied(dataset, after, request.scope_version):
            applied = _replace_status(
                request,
                GovernanceApprovalStatus.APPLIED,
                applied_at=self.clock(),
            )
            return self._transition(
                request, applied, action="GOVERNANCE_APPROVAL_APPLIED", actor_id=context.actor_id
            )
        try:
            writer.apply_dataset_metadata(
                dataset_id=request.object_id,
                updates=after,
                expected_version=request.scope_version,
            )
        except DataSourceConflictError:
            self._fail_application(request, context)
            raise GovernanceConflictError(
                "Governance decision could not be applied; object version changed."
            ) from None
        applied = _replace_status(
            request,
            GovernanceApprovalStatus.APPLIED,
            applied_at=self.clock(),
        )
        return self._transition(
            request, applied, action="GOVERNANCE_APPROVAL_APPLIED", actor_id=context.actor_id
        )

    def _apply_field_sensitivity(
        self, request: GovernanceApprovalRequest, context: ActorContext
    ) -> GovernanceApprovalRequest:
        writer = self._require_metadata_writer()
        data_field = self._get_data_field(request.object_id)
        after = dict(request.change_summary.get("after", {}))
        if self._already_applied(data_field, after, request.scope_version):
            applied = _replace_status(
                request,
                GovernanceApprovalStatus.APPLIED,
                applied_at=self.clock(),
            )
            return self._transition(
                request, applied, action="GOVERNANCE_APPROVAL_APPLIED", actor_id=context.actor_id
            )
        try:
            writer.apply_field_sensitivity(
                field_id=request.object_id,
                updates=after,
                expected_version=request.scope_version,
            )
        except DataSourceConflictError:
            self._fail_application(request, context)
            raise GovernanceConflictError(
                "Governance decision could not be applied; object version changed."
            ) from None
        applied = _replace_status(
            request,
            GovernanceApprovalStatus.APPLIED,
            applied_at=self.clock(),
        )
        return self._transition(
            request, applied, action="GOVERNANCE_APPROVAL_APPLIED", actor_id=context.actor_id
        )

    def _apply_diff_application(
        self, request: GovernanceApprovalRequest, context: ActorContext
    ) -> GovernanceApprovalRequest:
        writer = self._require_diff_writer()
        diff = self._get_metadata_diff(request.object_id)
        if diff.status is MetadataDiffStatus.APPLIED:
            # Idempotent tekrar uygulama: diff zaten kapatılmış.
            applied = _replace_status(
                request,
                GovernanceApprovalStatus.APPLIED,
                applied_at=self.clock(),
            )
            return self._transition(
                request, applied, action="GOVERNANCE_APPROVAL_APPLIED", actor_id=context.actor_id
            )
        if diff.status is not MetadataDiffStatus.PENDING or diff.version != request.scope_version:
            # Diff değiştiyse talep geçersizleşir; yeni keşif yeni bir talep gerektirir.
            invalidated = _replace_status(
                request,
                GovernanceApprovalStatus.INVALIDATED,
                reason_code="GOVERNANCE.OBJECT.CHANGED",
                decided_at=self.clock(),
            )
            self._transition(
                request,
                invalidated,
                action="GOVERNANCE_APPROVAL_INVALIDATED",
                actor_id=context.actor_id,
            )
            raise GovernanceConflictError("Metadata diff changed; the approval was invalidated.")
        selected_raw = request.change_summary.get("selected", ())
        selected_objects: frozenset[tuple[str, str, str, str, str | None]] = frozenset(
            (str(entry[0]), str(entry[1]), str(entry[2]), str(entry[3]), entry[4] or None)
            for entry in selected_raw
            if isinstance(entry, (list, tuple)) and len(entry) == 5
        )
        if not selected_objects:
            raise GovernanceValidationError("Governance diff request has no selected objects.")
        try:
            writer.apply_metadata_diff(
                actor_id=context.actor_id,
                metadata_diff_id=request.object_id,
                reason_code=request.reason_code or "METADATA.DIFF.APPLICATION",
                expected_version=request.scope_version,
                selected_objects=selected_objects,
                correlation_id=request.correlation_id,
            )
        except DataSourceConflictError:
            self._fail_application(request, context)
            raise GovernanceConflictError(
                "Governance decision could not be applied; metadata diff changed."
            ) from None
        applied = _replace_status(
            request,
            GovernanceApprovalStatus.APPLIED,
            applied_at=self.clock(),
        )
        return self._transition(
            request, applied, action="GOVERNANCE_APPROVAL_APPLIED", actor_id=context.actor_id
        )

    def _require_metadata_writer(self) -> GovernanceMetadataWriter:
        if self.metadata_writer is None:
            raise GovernanceValidationError("Metadata governance writer is not configured.")
        return self.metadata_writer

    def _require_diff_writer(self) -> GovernanceDiffWriter:
        if self.diff_writer is None:
            raise GovernanceValidationError("Metadata diff governance writer is not configured.")
        return self.diff_writer

    def _require_execution_writer(self) -> GovernanceExecutionWriter:
        if self.execution_writer is None:
            raise GovernanceValidationError("Execution governance writer is not configured.")
        return self.execution_writer

    def _require_schedule_writer(self) -> GovernanceScheduleWriter:
        if self.schedule_writer is None:
            raise GovernanceValidationError("Schedule governance writer is not configured.")
        return self.schedule_writer

    def _apply_execution(
        self, request: GovernanceApprovalRequest, context: ActorContext
    ) -> GovernanceApprovalRequest:
        writer = self._require_execution_writer()
        try:
            if request.request_type is GovernanceRequestType.EXECUTION_MANUAL_START:
                writer.apply_manual_start(request=request, actor_context=context)
            elif request.request_type is GovernanceRequestType.EXECUTION_CANCEL:
                writer.apply_cancel(request=request, actor_context=context)
            elif request.request_type is GovernanceRequestType.DEAD_LETTER_REPROCESS:
                writer.apply_dead_letter_reprocess(request=request, actor_context=context)
            else:
                raise GovernanceValidationError("Unknown execution request type.")
        except (ExecutionConflictErr, ExecutionNotFoundErr) as exc:
            self._fail_application(request, context)
            raise GovernanceConflictError(
                "Governance decision could not be applied; execution state changed."
            ) from exc
        except ExecutionValidationErr as exc:
            self._fail_application(request, context)
            raise GovernanceValidationError(
                "Governance decision application failed validation."
            ) from exc
        applied = _replace_status(
            request,
            GovernanceApprovalStatus.APPLIED,
            applied_at=self.clock(),
        )
        return self._transition(
            request, applied, action="GOVERNANCE_APPROVAL_APPLIED", actor_id=context.actor_id
        )

    def _apply_schedule_interval(
        self, request: GovernanceApprovalRequest, context: ActorContext
    ) -> GovernanceApprovalRequest:
        writer = self._require_schedule_writer()
        try:
            writer.apply_schedule_interval(request=request, actor_context=context)
        except (ExecutionConflictErr, ExecutionNotFoundErr) as exc:
            self._fail_application(request, context)
            raise GovernanceConflictError(
                "Governance decision could not be applied; schedule state changed."
            ) from exc
        except ExecutionValidationErr as exc:
            self._fail_application(request, context)
            raise GovernanceValidationError(
                "Governance decision application failed validation."
            ) from exc
        applied = _replace_status(
            request,
            GovernanceApprovalStatus.APPLIED,
            applied_at=self.clock(),
        )
        return self._transition(
            request, applied, action="GOVERNANCE_APPROVAL_APPLIED", actor_id=context.actor_id
        )

    def _already_applied(
        self, target: Dataset | DataField, after: Mapping[str, Any], scope_version: int
    ) -> bool:
        if not after or target.version <= scope_version:
            return False
        return all(_attribute_value(target, key) == value for key, value in after.items())

    def _fail_application(self, request: GovernanceApprovalRequest, context: ActorContext) -> None:
        failed = _replace_status(
            request,
            GovernanceApprovalStatus.APPLICATION_FAILED,
            reason_code="GOVERNANCE.OBJECT.CHANGED",
        )
        self._transition(
            request,
            failed,
            action="GOVERNANCE_APPROVAL_APPLICATION_FAILED",
            actor_id=context.actor_id,
            result=AuditResult.FAILURE,
        )

    # ------------------------------------------------------------------
    # İç yardımcılar
    # ------------------------------------------------------------------

    def _get_dataset(self, dataset_id: str) -> Dataset:
        try:
            return self.catalog.get_dataset(dataset_id)
        except (DataSourceNotFoundError, KeyError) as exc:
            raise GovernanceNotFoundError("Governance target dataset not found.") from exc

    def _get_data_field(self, field_id: str) -> DataField:
        try:
            return self.catalog.get_data_field(field_id)
        except (DataSourceNotFoundError, KeyError) as exc:
            raise GovernanceNotFoundError("Governance target field not found.") from exc

    def _get_metadata_diff(self, metadata_diff_id: str) -> MetadataDiff:
        writer = self._require_diff_writer()
        try:
            return writer.get_metadata_diff(metadata_diff_id)
        except (DataSourceNotFoundError, KeyError) as exc:
            raise GovernanceNotFoundError("Governance target metadata diff not found.") from exc

    def _load_object(
        self, request: GovernanceApprovalRequest
    ) -> Dataset | DataField | RuleExecution | DeadLetterRecord | MetadataDiff:
        if request.object_type == "DataField":
            return self._get_data_field(request.object_id)
        if request.object_type == "RuleExecution":
            return self._get_execution(request.object_id)
        if request.object_type == "DeadLetterRecord":
            return self._get_dead_letter(request.object_id)
        if request.object_type == "MetadataDiff":
            return self._get_metadata_diff(request.object_id)
        return self._get_dataset(request.object_id)

    def _request_expired(self, request: GovernanceApprovalRequest) -> bool:
        if request.expires_at is None:
            return False
        now = self.clock()
        if not _is_aware(now):
            raise GovernanceValidationError("Governance clock must be timezone-aware.")
        return now >= request.expires_at

    def _assert_object_unchanged(
        self, request: GovernanceApprovalRequest, *, action: str, actor_id: str
    ) -> None:
        before = dict(request.change_summary.get("before", {}))
        dataset_versions = before.pop("dataset_versions", None)
        is_creation = before.get("status") is None and request.scope_version == 0
        try:
            current = self._load_object(request)
        except GovernanceNotFoundError:
            if is_creation:
                current = None
            else:
                invalidated = _replace_status(
                    request,
                    GovernanceApprovalStatus.INVALIDATED,
                    reason_code="GOVERNANCE.OBJECT.CHANGED",
                    decided_at=self.clock(),
                )
                self._transition(request, invalidated, action=action, actor_id=actor_id)
                raise GovernanceConflictError(
                    "Governance target object not found; the approval was invalidated."
                ) from None
        if current is not None:
            current_version = _object_version(current)
            attributes_changed = any(
                _attribute_value(current, attribute) != value for attribute, value in before.items()
            )
            version_changed = request.scope_version > 0 and current_version != request.scope_version
        else:
            attributes_changed = False
            version_changed = False
        datasets_changed = False
        if isinstance(dataset_versions, dict):
            for dataset_id, expected_version in dataset_versions.items():
                try:
                    dataset = self._get_dataset(dataset_id)
                    if dataset.version != expected_version:
                        datasets_changed = True
                        break
                except GovernanceNotFoundError:
                    datasets_changed = True
                    break
        if version_changed or attributes_changed or datasets_changed:
            invalidated = _replace_status(
                request,
                GovernanceApprovalStatus.INVALIDATED,
                reason_code="GOVERNANCE.OBJECT.CHANGED",
                decided_at=self.clock(),
            )
            self._transition(request, invalidated, action=action, actor_id=actor_id)
            raise GovernanceConflictError(
                "Governance target object changed; the approval was invalidated."
            )

    # ------------------------------------------------------------------
    # Notification helper methods
    # ------------------------------------------------------------------

    def _resolve_checker_recipient(self, request: GovernanceApprovalRequest) -> str:
        """Resolve the notification recipient for a governance checker.

        For dataset-scoped requests, the dataset owner is the natural checker.
        Falls back to the maker actor id when no better recipient is found.
        """
        if request.scope_type == "DATASET" and request.scope_id:
            try:
                dataset = self._get_dataset(request.scope_id)
                if dataset.owner_user_id and dataset.owner_user_id.strip():
                    return dataset.owner_user_id
            except (GovernanceNotFoundError, Exception):
                pass
        return request.maker_actor_id

    def _publish_governance_notification(
        self,
        *,
        event_type: str,
        request: GovernanceApprovalRequest,
        recipient_user_id: str,
        actor_context: ActorContext | None,
        correlation_id: str,
        payload: dict[str, Any],
    ) -> None:
        """Publish governance notifications to all relevant recipients.

        The explicit *recipient_user_id* is always included.  When a
        ``notification_recipient_provider`` is configured its results (e.g.
        governance specialists) are merged in as well.
        """
        if self.notification_sink is None:
            return
        recipients: set[str] = {recipient_user_id}
        if self.notification_recipient_provider is not None:
            try:
                extra = self.notification_recipient_provider(request, event_type)
                recipients.update(extra)
            except Exception:
                logger.warning(
                    "Governance notification recipient resolution failed for %s",
                    request.approval_request_id,
                    exc_info=True,
                )
        for user_id in sorted(recipients):
            try:
                self.notification_sink.publish_governance_approval_event(
                    event_type=event_type,
                    approval_request_id=request.approval_request_id,
                    request_type=request.request_type.value,
                    object_type=request.object_type,
                    object_id=request.object_id,
                    object_name=request.object_id,
                    scope_type=request.scope_type,
                    scope_id=request.scope_id,
                    maker_actor_id=request.maker_actor_id,
                    recipient_user_id=user_id,
                    actor_context=actor_context,
                    correlation_id=correlation_id,
                    payload=payload,
                )
            except Exception:
                # Notification failures must not break the governance workflow.
                logger.warning(
                    "Governance notification publish failed for %s (recipient=%s)",
                    request.approval_request_id,
                    user_id,
                    exc_info=True,
                )

    def _transition(
        self,
        original: GovernanceApprovalRequest,
        updated: GovernanceApprovalRequest,
        *,
        action: str,
        actor_id: str,
        result: AuditResult = AuditResult.SUCCESS,
    ) -> GovernanceApprovalRequest:
        audit_event = self._build_audit_event(
            actor_id,
            original.correlation_id,
            action,
            original.object_id,
            result,
            action,
            {
                "approval_request_id": original.approval_request_id,
                "request_type": original.request_type.value,
                "policy_version": original.policy_version,
                "status": updated.status.value,
            },
            old_values={"status": original.status.value},
            object_type=original.object_type,
        )
        stored = self.repository.transition(
            updated,
            expected_version=original.version,
            expected_status=original.status,
            audit_event=self.transactional_audit.prepare(audit_event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return stored

    def _record_violation(
        self,
        context: ActorContext,
        request: GovernanceApprovalRequest,
        violation_code: str,
    ) -> None:
        audit_event = self._build_audit_event(
            context.actor_id,
            context.correlation_id,
            "GOVERNANCE_MAKER_CHECKER_VIOLATION",
            request.object_id,
            AuditResult.FAILURE,
            violation_code,
            {
                "approval_request_id": request.approval_request_id,
                "request_type": request.request_type.value,
                "status": request.status.value,
            },
            actor_type=context.actor_type.value,
            session_id=context.session_id,
        )
        self.audit_sink.append(audit_event)

    def _authorize_actor(
        self,
        context: ActorContext | None,
        *,
        required_roles: frozenset[str],
        dataset_ids: frozenset[str] | None,
    ) -> ActorContext:
        policy = self.policy
        now = self.clock()
        if not _is_aware(now):
            raise GovernanceValidationError("Governance clock must be timezone-aware.")
        if not is_trusted_actor_context(context):
            raise GovernanceAuthorizationError("Trusted actor context is required.")
        assert context is not None
        if context.issued_at > now or context.expires_at <= now:
            raise GovernanceAuthorizationError("Actor context is not currently valid.")
        if context.policy_version != policy.actor_policy_version:
            raise GovernanceAuthorizationError("Actor context policy version is not accepted.")
        if context.actor_type not in policy.allowed_actor_types:
            raise GovernanceAuthorizationError("Actor type is not allowed for governance approval.")
        if context.privileged:
            raise GovernanceAuthorizationError(
                "Privileged actors cannot bypass governance approval."
            )
        if not required_roles:
            raise GovernanceAuthorizationError(
                "Governance policy does not define the required roles."
            )
        if context.roles.isdisjoint(required_roles):
            raise GovernanceAuthorizationError("Actor does not have the required approval role.")
        if dataset_ids is not None and not dataset_ids <= context.permitted_dataset_ids:
            raise GovernanceAuthorizationError("Actor is outside the governance object scope.")
        return context

    def _build_audit_event(
        self,
        actor_id: str,
        correlation_id: str,
        action: str,
        object_id: str,
        result: AuditResult,
        reason_code: str,
        new_values: dict,
        *,
        old_values: dict | None = None,
        actor_type: str = "USER",
        session_id: str | None = None,
        object_type: str = "Dataset",
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


class PostgreSQLDatasetOwnershipWriter:
    """Dataset sahipliğini OCC ile güncelleyen uygulama adaptörü."""

    def __init__(self, repository: DatasetUpdater) -> None:
        self.repository = repository

    def apply_dataset_owner(
        self,
        *,
        dataset_id: str,
        owner_user_id: str,
        expected_version: int,
    ) -> Dataset:
        return self.repository.update_dataset(
            dataset_id=dataset_id,
            updates={"owner_user_id": owner_user_id},
            expected_version=expected_version,
        )


class PostgreSQLMetadataGovernanceWriter:
    """Onaylanan kritik metadata kararlarını OCC ile uygulayan adaptör."""

    def __init__(self, repository: GovernanceMetadataRepository) -> None:
        self.repository = repository

    def apply_dataset_metadata(
        self,
        *,
        dataset_id: str,
        updates: Mapping[str, Any],
        expected_version: int,
    ) -> Dataset:
        return self.repository.update_dataset(
            dataset_id=dataset_id,
            updates=dict(updates),
            expected_version=expected_version,
        )

    def apply_field_sensitivity(
        self,
        *,
        field_id: str,
        updates: Mapping[str, Any],
        expected_version: int,
    ) -> DataField:
        return self.repository.update_field(
            field_id=field_id,
            updates=dict(updates),
            expected_version=expected_version,
        )


class PostgreSQLDiffGovernanceRepository(Protocol):
    """Metadata diff okuma ve katalog dataset envanteri yüzeyi."""

    def get_metadata_diff(self, metadata_diff_id: str) -> MetadataDiff: ...

    def list_datasets(self, data_source_id: str) -> list[Dataset]: ...


class GovernanceDiffApplicationService(Protocol):
    """Seçim filtreli metadata diff uygulama yüzeyi."""

    def apply_discovery_diff(
        self,
        *,
        actor_id: str,
        metadata_diff_id: str,
        reason_code: str,
        expected_version: int,
        correlation_id: str | None = None,
        selected_objects: frozenset[tuple[str, str, str, str, str | None]] | None = None,
    ) -> MetadataDiff: ...


class PostgreSQLDiffGovernanceWriter:
    """Onaylanan metadata diff seçimini DataSourceService ile uygulayan adaptör."""

    def __init__(
        self,
        service: GovernanceDiffApplicationService,
        repository: PostgreSQLDiffGovernanceRepository,
    ) -> None:
        self.service = service
        self.repository = repository

    def get_metadata_diff(self, metadata_diff_id: str) -> MetadataDiff:
        return self.repository.get_metadata_diff(metadata_diff_id)

    def dataset_versions_for_diff(
        self, data_source_id: str, dataset_keys: frozenset[tuple[str, str]]
    ) -> dict[str, int]:
        versions: dict[str, int] = {}
        for dataset in self.repository.list_datasets(data_source_id):
            if (dataset.namespace, dataset.name) in dataset_keys:
                versions[dataset.dataset_id] = dataset.version
        return versions

    def apply_metadata_diff(
        self,
        *,
        actor_id: str,
        metadata_diff_id: str,
        reason_code: str,
        expected_version: int,
        selected_objects: frozenset[tuple[str, str, str, str, str | None]],
        correlation_id: str,
    ) -> MetadataDiff:
        return self.service.apply_discovery_diff(
            actor_id=actor_id,
            metadata_diff_id=metadata_diff_id,
            reason_code=reason_code,
            expected_version=expected_version,
            correlation_id=correlation_id,
            selected_objects=selected_objects,
        )


class PostgreSQLScheduleGovernanceWriter:
    """Onaylanan bant dışı zamanlayıcı önerisini SchedulingService ile oluşturur."""

    def __init__(self, scheduling_service: SchedulingService) -> None:
        self.scheduling_service = scheduling_service

    def apply_schedule_interval(
        self,
        *,
        request: GovernanceApprovalRequest,
        actor_context: ActorContext,
    ) -> Schedule:
        schedule_proposal = request.change_summary.get("after", {}).get("schedule", {})
        schedule_id = str(schedule_proposal.get("schedule_id", ""))
        if schedule_id:
            try:
                # Idempotent tekrar uygulama: önerilen schedule zaten mevcut.
                return self.scheduling_service.repository.get(schedule_id)
            except ExecutionValidationErr:
                pass
        schedule, _preview = self.scheduling_service.create_schedule(
            actor_id=actor_context.actor_id,
            name=str(schedule_proposal.get("name", "")),
            schedule_type=str(schedule_proposal.get("schedule_type", "")),
            timezone_name=str(schedule_proposal.get("timezone_name", "")),
            rule_version_ids=tuple(schedule_proposal.get("rule_version_ids", ())),
            local_time=schedule_proposal.get("local_time"),
            interval_minutes=schedule_proposal.get("interval_minutes"),
            day_of_week=schedule_proposal.get("day_of_week"),
            day_of_month=schedule_proposal.get("day_of_month"),
            schedule_id=schedule_id or None,
            correlation_id=request.correlation_id,
        )
        return schedule


def _validate_policy(policy: GovernanceApprovalPolicy) -> None:
    if not policy.version.strip() or not policy.actor_policy_version.strip():
        raise GovernanceValidationError("Governance policy versions are required.")
    if not policy.maker_roles or not policy.checker_roles:
        raise GovernanceValidationError("Governance policy roles are required.")
    if policy.maker_roles & policy.checker_roles:
        raise GovernanceValidationError(
            "Maker and checker role sets must be disjoint for segregation of duties."
        )


def _parse_request_type(value: str) -> GovernanceRequestType:
    try:
        return GovernanceRequestType(value.strip().upper())
    except (AttributeError, ValueError) as exc:
        raise GovernanceValidationError("Governance request type is invalid.") from exc


def _parse_decision(decision: str) -> GovernanceApprovalStatus:
    try:
        return {
            "APPROVE": GovernanceApprovalStatus.APPROVED,
            "REJECT": GovernanceApprovalStatus.REJECTED,
        }[decision.strip().upper()]
    except (AttributeError, KeyError) as exc:
        raise GovernanceValidationError("Governance approval decision is invalid.") from exc


def _validate_reason_code(reason_code: str) -> str:
    normalized = reason_code.strip().upper()
    if normalized not in GOVERNANCE_REASON_CODES:
        raise GovernanceValidationError(
            "Governance reason code is not in the controlled dictionary."
        )
    return normalized


def _validate_owner(owner_user_id: str) -> str:
    normalized = owner_user_id.strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,120}", normalized):
        raise GovernanceValidationError("Owner user identifier format is invalid.")
    return normalized


def _validate_proposed_changes(
    proposed_changes: Mapping[str, Any] | None,
    allowed_attributes: frozenset[str],
    *,
    object_label: str,
) -> dict[str, Any]:
    if not proposed_changes:
        raise GovernanceValidationError(
            f"Governance {object_label} request requires proposed changes."
        )
    if set(proposed_changes) - allowed_attributes:
        raise GovernanceValidationError(
            f"Proposed changes include non-governed {object_label} attributes."
        )
    return dict(proposed_changes)


def _validate_diff_selection(
    diff: MetadataDiff, proposed_changes: Mapping[str, Any] | None
) -> frozenset[tuple[str, str, str, str, str | None]]:
    """Diff uygulaması için gönderilen obje seçimini doğrular."""
    if not proposed_changes or "selected_objects" not in proposed_changes:
        raise GovernanceValidationError("Metadata diff application requires an object selection.")
    raw_selection = proposed_changes["selected_objects"]
    if not isinstance(raw_selection, (list, tuple)) or not raw_selection:
        raise GovernanceValidationError("Metadata diff selection must be a non-empty object list.")
    known = {
        diff_object_key(change_type, obj)
        for change_type, bucket in (
            ("ADDED", diff.added_objects),
            ("CHANGED", diff.changed_objects),
            ("REMOVED", diff.removed_objects),
        )
        for obj in bucket
    }
    selected: set[tuple[str, str, str, str, str | None]] = set()
    for entry in raw_selection:
        if not isinstance(entry, (list, tuple)) or len(entry) != 5:
            raise GovernanceValidationError("Metadata diff selection entry is malformed.")
        key = (
            str(entry[0]).strip().upper(),
            str(entry[1]),
            str(entry[2]),
            str(entry[3]),
            str(entry[4]) if entry[4] else None,
        )
        if key not in known:
            raise GovernanceValidationError(
                "Selected object is not part of the pending metadata diff."
            )
        selected.add(key)
    return frozenset(selected)


def _normalize_enum_attribute(
    updates: dict[str, Any], attribute: str, enum_type: type[Enum], *, label: str
) -> None:
    if attribute not in updates:
        return
    value = updates[attribute]
    if isinstance(value, enum_type):
        updates[attribute] = value.value
        return
    if not isinstance(value, str):
        raise GovernanceValidationError(f"Proposed {label} value is invalid.")
    try:
        updates[attribute] = enum_type(value.strip().upper()).value
    except ValueError as exc:
        raise GovernanceValidationError(f"Proposed {label} value is invalid.") from exc


def _attribute_value(target: object, attribute: str) -> Any:
    value = getattr(target, attribute)
    if isinstance(value, Enum):
        return value.value
    return value


def _object_version(target: object) -> int:
    """OCC version of a governance target; 0 for objects without version."""
    return getattr(target, "version", 0)


def _assert_full_dataset_scope(context: ActorContext, dataset_ids: frozenset[str]) -> None:
    """Maker, talebin dokunduğu dataset'lerin tamamına yetkili olmalıdır.

    F-03: Eskiden yalnız bir kesişim aranıyordu; D1'e yetkili bir maker,
    talebe D2 kurallarını da ekleyerek kapsam dışına taşabiliyordu.
    """

    outside = dataset_ids - context.permitted_dataset_ids
    if outside:
        raise GovernanceAuthorizationError(
            "Maker is outside the dataset scope for execution governance: "
            + ", ".join(sorted(outside))
        )


def _request_scope_dataset_ids(request: GovernanceApprovalRequest) -> frozenset[str]:
    """Talebin dokunduğu dataset kapsamının tamamı.

    F-03: ``scope_id`` çok dataset'e dokunan execution taleplerinde yalnız
    birincil (alfabetik ilk) dataset'tir. Tam kapsam maker aşamasında
    ``change_summary.before.dataset_versions`` içine yazılır; checker, maker
    geri çekmesi ve applier yetkilendirmesi bu kümenin tamamı üzerinden
    yapılmalıdır, aksi halde aktör kapsam dışı bir dataset üzerinde karar
    verebilir.
    """

    scope: set[str] = set()
    if request.scope_type == "DATASET" and request.scope_id:
        scope.add(request.scope_id)
    before = request.change_summary.get("before")
    if isinstance(before, Mapping):
        dataset_versions = before.get("dataset_versions")
        if isinstance(dataset_versions, Mapping):
            scope.update(str(dataset_id) for dataset_id in dataset_versions)
    return frozenset(scope)


def _first_matching_role(actor_roles: frozenset[str], policy_roles: frozenset[str]) -> str:
    return sorted(actor_roles & policy_roles)[0]


def _replace_status(
    request: GovernanceApprovalRequest,
    status: GovernanceApprovalStatus,
    *,
    checker_actor_id: str | None = None,
    checker_role: str | None = None,
    reason_code: str | None = None,
    decided_at: datetime | None = None,
    applied_at: datetime | None = None,
) -> GovernanceApprovalRequest:
    return GovernanceApprovalRequest(
        approval_request_id=request.approval_request_id,
        request_type=request.request_type,
        object_type=request.object_type,
        object_id=request.object_id,
        scope_type=request.scope_type,
        scope_id=request.scope_id,
        scope_version=request.scope_version,
        maker_actor_id=request.maker_actor_id,
        maker_roles=request.maker_roles,
        policy_version=request.policy_version,
        correlation_id=request.correlation_id,
        change_summary=request.change_summary,
        status=status,
        checker_actor_id=checker_actor_id,
        checker_role=checker_role,
        reason_code=reason_code,
        before_snapshot_reference=request.before_snapshot_reference,
        after_snapshot_reference=request.after_snapshot_reference,
        evidence_references=request.evidence_references,
        requested_at=request.requested_at,
        expires_at=request.expires_at,
        decided_at=decided_at,
        applied_at=applied_at,
        version=request.version,
    )


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
