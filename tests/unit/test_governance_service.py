"""Ortak yönetişim komut servisi birim testleri.

Maker-checker görevler ayrılığı, kapsam denetimi, geçersizleştirme,
idempotent uygulama ve audit davranışlarını doğrular.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from veri_kalitesi.data_protection.policy import ClassificationCode
from veri_kalitesi.data_sources.models import CatalogItemStatus, Criticality, DataField, Dataset
from veri_kalitesi.executions.models import ExecutionMode, ExecutionStatus, ExecutionType, RuleExecution
from veri_kalitesi.governance.errors import (
    GovernanceAuthorizationError,
    GovernanceConflictError,
    GovernanceNotFoundError,
    GovernanceValidationError,
)
from veri_kalitesi.governance.models import (
    GovernanceApprovalPolicy,
    GovernanceApprovalRequest,
    GovernanceApprovalStatus,
)
from veri_kalitesi.governance.service import GovernanceApprovalCommandService
from veri_kalitesi.identity import ActorContextIssuer, ActorType
from veri_kalitesi.jobs.models import DeadLetterRecord, DeadLetterStatus
from veri_kalitesi.rules.models import (
    QualityDimension,
    QualityRule,
    RuleCriticality,
    RuleStatus,
    RuleType,
    RuleVersion,
)

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
ACTOR_POLICY_VERSION = "GOVERNANCE_UNIT_POLICY_V1"
GOVERNANCE_POLICY_VERSION = "GOVERNANCE_APPROVAL_POLICY_V1"
DATASET_ID = "dataset-ownership"
FIELD_ID = "field-sensitive"
RULE_ID = "rule-exec-1"
RULE_VERSION_ID = "rv-exec-1"
EXECUTION_ID = "exec-gov-1"
DEAD_LETTER_ID = "dl-gov-1"


class FakeAuditSink:
    def __init__(self) -> None:
        self.events: list = []

    def append(self, event) -> None:
        self.events.append(event)


class FakePreparedAudit:
    pass


class FakeTransactionalAudit:
    def __init__(self) -> None:
        self.staged: list = []
        self.published = 0
        self.prepared_events: list = []

    def prepare(self, event):
        self.prepared_events.append(event)
        return FakePreparedAudit()

    def publish_pending(self, *, limit: int = 100):
        self.published += 1


class FakeGovernanceRepository:
    def __init__(self) -> None:
        self._requests: dict[str, GovernanceApprovalRequest] = {}

    def add(self, request, *, audit_event, audit_outbox) -> GovernanceApprovalRequest:
        for existing in self._requests.values():
            if (
                existing.object_id == request.object_id
                and existing.request_type is request.request_type
                and existing.status is GovernanceApprovalStatus.SUBMITTED
            ):
                raise GovernanceConflictError("pending exists")
        self._requests[request.approval_request_id] = request
        return request

    def get(self, approval_request_id: str) -> GovernanceApprovalRequest:
        if approval_request_id not in self._requests:
            raise GovernanceNotFoundError("missing")
        return self._requests[approval_request_id]

    def transition(
        self, request, *, expected_version, expected_status, audit_event, audit_outbox
    ) -> GovernanceApprovalRequest:
        stored = self._requests[request.approval_request_id]
        if stored.status is not expected_status or stored.version != expected_version:
            raise GovernanceConflictError("concurrent decision")
        updated = GovernanceApprovalRequest(
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
            status=request.status,
            checker_actor_id=request.checker_actor_id,
            checker_role=request.checker_role,
            reason_code=request.reason_code,
            requested_at=request.requested_at,
            expires_at=request.expires_at,
            decided_at=request.decided_at,
            applied_at=request.applied_at,
            version=expected_version + 1,
        )
        self._requests[request.approval_request_id] = updated
        return updated


class FakeCatalog:
    def __init__(self) -> None:
        self.datasets: dict[str, Dataset] = {
            DATASET_ID: Dataset(
                data_source_id="source-1",
                namespace="core",
                name="Müşteri tablosu",
                owner_user_id="current-owner",
                dataset_id=DATASET_ID,
                version=3,
            )
        }
        self.fields: dict[str, DataField] = {
            FIELD_ID: DataField(
                dataset_id=DATASET_ID,
                name="tc_kimlik_no",
                native_data_type="varchar(11)",
                is_sensitive=False,
                data_field_id=FIELD_ID,
                version=2,
            )
        }
        self.rules: dict[str, QualityRule] = {
            RULE_ID: QualityRule(
                code="RQ-001",
                name="Test kuralı",
                dataset_id=DATASET_ID,
                field_ids=(FIELD_ID,),
                primary_dimension=QualityDimension.COMPLETENESS,
                owner_user_id="rule-owner",
                status=RuleStatus.ACTIVE,
                quality_rule_id=RULE_ID,
            ),
        }
        self.rule_versions: dict[str, RuleVersion] = {
            RULE_VERSION_ID: RuleVersion(
                quality_rule_id=RULE_ID,
                version_no=1,
                rule_type=RuleType.REQUIRED,
                definition={"field_id": FIELD_ID, "operator": "IS_NOT_NULL"},
                threshold=0.95,
                weight=1.0,
                criticality=RuleCriticality.HIGH,
                rule_version_id=RULE_VERSION_ID,
            ),
        }
        self.executions: dict[str, RuleExecution] = {}
        self.dead_letters: dict[str, DeadLetterRecord] = {}

    def get_dataset(self, dataset_id: str) -> Dataset:
        if dataset_id not in self.datasets:
            raise KeyError(dataset_id)
        return self.datasets[dataset_id]

    def get_data_field(self, field_id: str) -> DataField:
        if field_id not in self.fields:
            raise KeyError(field_id)
        return self.fields[field_id]

    def get_rule(self, quality_rule_id: str) -> QualityRule:
        if quality_rule_id not in self.rules:
            raise KeyError(quality_rule_id)
        return self.rules[quality_rule_id]

    def get_rule_version(self, rule_version_id: str) -> RuleVersion:
        if rule_version_id not in self.rule_versions:
            raise KeyError(rule_version_id)
        return self.rule_versions[rule_version_id]

    def get_execution(self, execution_id: str) -> RuleExecution:
        if execution_id not in self.executions:
            raise KeyError(execution_id)
        return self.executions[execution_id]

    def get_dead_letter(self, dead_letter_id: str) -> DeadLetterRecord:
        if dead_letter_id not in self.dead_letters:
            raise KeyError(dead_letter_id)
        return self.dead_letters[dead_letter_id]


class FakeOwnershipWriter:
    def __init__(self, catalog: FakeCatalog) -> None:
        self.catalog = catalog

    def apply_dataset_owner(self, *, dataset_id, owner_user_id, expected_version) -> Dataset:
        dataset = self.catalog.datasets[dataset_id]
        if dataset.version != expected_version:
            from veri_kalitesi.data_sources.errors import ConflictError

            raise ConflictError("version mismatch")
        updated = replace(
            dataset, owner_user_id=owner_user_id, version=dataset.version + 1
        )
        self.catalog.datasets[dataset_id] = updated
        return updated


class FakeMetadataWriter:
    _DATASET_ENUMS = {"criticality": Criticality, "status": CatalogItemStatus}
    _FIELD_ENUMS = {"classification": ClassificationCode}

    def __init__(self, catalog: FakeCatalog) -> None:
        self.catalog = catalog

    def apply_dataset_metadata(self, *, dataset_id, updates, expected_version) -> Dataset:
        from veri_kalitesi.data_sources.errors import ConflictError

        dataset = self.catalog.datasets[dataset_id]
        if dataset.version != expected_version:
            raise ConflictError("version mismatch")
        normalized = {
            key: self._DATASET_ENUMS[key](value) if key in self._DATASET_ENUMS else value
            for key, value in updates.items()
        }
        updated = replace(dataset, version=dataset.version + 1, **normalized)
        self.catalog.datasets[dataset_id] = updated
        return updated

    def apply_field_sensitivity(self, *, field_id, updates, expected_version) -> DataField:
        from veri_kalitesi.data_sources.errors import ConflictError

        data_field = self.catalog.fields[field_id]
        if data_field.version != expected_version:
            raise ConflictError("version mismatch")
        normalized = {
            key: self._FIELD_ENUMS[key](value) if key in self._FIELD_ENUMS else value
            for key, value in updates.items()
        }
        updated = replace(data_field, version=data_field.version + 1, **normalized)
        self.catalog.fields[field_id] = updated
        return updated


class FakeExecutionWriter:
    def __init__(self, catalog: FakeCatalog) -> None:
        self.catalog = catalog
        self.started: list = []
        self.cancelled: list = []
        self.reprocessed: list = []

    def apply_manual_start(self, *, request, actor_context) -> RuleExecution:
        from veri_kalitesi.executions.errors import ExecutionConflictError
        after = request.change_summary.get("after", {})
        rule_version_ids = tuple(after.get("rule_version_ids", ()))
        execution = RuleExecution(
            idempotency_key_hash="test",
            payload_hash="test",
            rule_version_ids=rule_version_ids,
            scope={},
            triggered_by=actor_context.actor_id,
            correlation_id=actor_context.correlation_id,
            execution_id=request.object_id,
            execution_type=ExecutionType.MANUAL,
            execution_mode=ExecutionMode(after.get("execution_mode", "OFFICIAL")),
            status=ExecutionStatus.QUEUED,
        )
        self.catalog.executions[execution.execution_id] = execution
        self.started.append(execution)
        return execution

    def apply_cancel(self, *, request, actor_context) -> RuleExecution:
        from veri_kalitesi.executions.errors import ExecutionNotFoundError
        execution = self.catalog.executions.get(request.object_id)
        if execution is None:
            raise ExecutionNotFoundError("execution missing")
        cancelled = replace(
            execution,
            status=ExecutionStatus.CANCELLED,
            cancel_reason=request.change_summary.get("after", {}).get("reason", ""),
        )
        self.catalog.executions[request.object_id] = cancelled
        self.cancelled.append(cancelled)
        return cancelled

    def apply_dead_letter_reprocess(self, *, request, actor_context) -> object:
        self.reprocessed.append(request.object_id)
        return object()


def _policy() -> GovernanceApprovalPolicy:
    return GovernanceApprovalPolicy(
        version=GOVERNANCE_POLICY_VERSION,
        actor_policy_version=ACTOR_POLICY_VERSION,
        maker_roles=frozenset({"DATA_STEWARD"}),
        checker_roles=frozenset({"DATA_OWNER"}),
        applier_roles=frozenset({"DATA_GOVERNANCE_SPECIALIST"}),
    )


def _service(
    *,
    repository: FakeGovernanceRepository | None = None,
    catalog: FakeCatalog | None = None,
    sink: FakeAuditSink | None = None,
):
    repository = repository or FakeGovernanceRepository()
    catalog = catalog or FakeCatalog()
    audit = FakeTransactionalAudit()
    service_sink = sink or FakeAuditSink()
    execution_writer = FakeExecutionWriter(catalog)
    service = GovernanceApprovalCommandService(
        repository,
        catalog,
        FakeOwnershipWriter(catalog),
        audit_sink=service_sink,
        transactional_audit=audit,
        policy=_policy(),
        metadata_writer=FakeMetadataWriter(catalog),
        execution_writer=execution_writer,
        clock=lambda: NOW,
    )
    return service, repository, catalog, service_sink, audit, execution_writer


def _actor(
    actor_id: str,
    roles: set[str],
    *,
    dataset_ids: set[str] | None = None,
    privileged: bool = False,
    actor_type: ActorType = ActorType.USER,
):
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=actor_type,
        authentication_source="synthetic-identity-adapter",
        session_id=f"session-{actor_id}",
        roles=frozenset(roles),
        permitted_source_ids=frozenset({"source-1"}),
        permitted_dataset_ids=frozenset(dataset_ids or {DATASET_ID}),
        can_view_enterprise=False,
        privileged=privileged,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id=f"correlation-{actor_id}",
    )


def test_maker_submits_owner_change_request() -> None:
    service, repository, _catalog, _sink, _audit, _exec = _service()

    request = service.submit_request(
        actor_context=_actor("maker-1", {"DATA_STEWARD"}),
        request_type="DATASET_OWNER_CHANGE",
        object_id=DATASET_ID,
        new_owner_user_id="new-owner",
        reason_code="OWNERSHIP.TRANSFER",
    )

    assert request.status is GovernanceApprovalStatus.SUBMITTED
    assert request.scope_version == 3
    assert request.change_summary["before"] == {"owner_user_id": "current-owner"}
    assert request.change_summary["after"] == {"owner_user_id": "new-owner"}
    assert repository.get(request.approval_request_id) is request


def test_assign_requires_ownerless_dataset() -> None:
    service, _repository, _catalog, _sink, _audit, _exec = _service()

    with pytest.raises(GovernanceValidationError, match="already has an owner"):
        service.submit_request(
            actor_context=_actor("maker-1", {"DATA_STEWARD"}),
            request_type="DATASET_OWNER_ASSIGN",
            object_id=DATASET_ID,
            new_owner_user_id="new-owner",
            reason_code="OWNERSHIP.ASSIGN",
        )


def test_change_requires_different_owner_and_known_dataset() -> None:
    service, _repository, _catalog, _sink, _audit, _exec = _service()

    with pytest.raises(GovernanceValidationError, match="differ"):
        service.submit_request(
            actor_context=_actor("maker-1", {"DATA_STEWARD"}),
            request_type="DATASET_OWNER_CHANGE",
            object_id=DATASET_ID,
            new_owner_user_id="current-owner",
            reason_code="OWNERSHIP.TRANSFER",
        )
    with pytest.raises(GovernanceNotFoundError):
        service.submit_request(
            actor_context=_actor("maker-1", {"DATA_STEWARD"}),
            request_type="DATASET_OWNER_CHANGE",
            object_id="dataset-missing",
            new_owner_user_id="new-owner",
            reason_code="OWNERSHIP.TRANSFER",
        )


def test_maker_outside_scope_cannot_submit() -> None:
    service, _repository, _catalog, _sink, _audit, _exec = _service()

    with pytest.raises(GovernanceAuthorizationError, match="scope"):
        service.submit_request(
            actor_context=_actor("maker-1", {"DATA_STEWARD"}, dataset_ids={"other"}),
            request_type="DATASET_OWNER_CHANGE",
            object_id=DATASET_ID,
            new_owner_user_id="new-owner",
            reason_code="OWNERSHIP.TRANSFER",
        )


def test_privileged_actor_cannot_bypass_governance() -> None:
    service, _repository, _catalog, _sink, _audit, _exec = _service()

    with pytest.raises(GovernanceAuthorizationError, match="Privileged"):
        service.submit_request(
            actor_context=_actor("admin-1", {"DATA_STEWARD"}, privileged=True),
            request_type="DATASET_OWNER_CHANGE",
            object_id=DATASET_ID,
            new_owner_user_id="new-owner",
            reason_code="OWNERSHIP.TRANSFER",
        )


def test_reason_code_must_be_from_controlled_dictionary() -> None:
    service, _repository, _catalog, _sink, _audit, _exec = _service()

    with pytest.raises(GovernanceValidationError, match="reason code"):
        service.submit_request(
            actor_context=_actor("maker-1", {"DATA_STEWARD"}),
            request_type="DATASET_OWNER_CHANGE",
            object_id=DATASET_ID,
            new_owner_user_id="new-owner",
            reason_code="FREE.TEXT.REASON",
        )


def _submit(service) -> GovernanceApprovalRequest:
    return service.submit_request(
        actor_context=_actor("maker-1", {"DATA_STEWARD"}),
        request_type="DATASET_OWNER_CHANGE",
        object_id=DATASET_ID,
        new_owner_user_id="new-owner",
        reason_code="OWNERSHIP.TRANSFER",
    )


def test_maker_cannot_decide_own_request_and_violation_is_audited() -> None:
    service, _repository, _catalog, sink, _audit, _exec = _service()
    request = _submit(service)
    maker_checker = _actor("maker-1", {"DATA_STEWARD", "DATA_OWNER"})

    with pytest.raises(GovernanceAuthorizationError, match="Maker cannot"):
        service.decide_request(
            actor_context=maker_checker,
            approval_request_id=request.approval_request_id,
            decision="APPROVE",
            reason_code="OWNERSHIP.VERIFIED",
        )

    assert any(
        event.action == "GOVERNANCE_MAKER_CHECKER_VIOLATION" for event in sink.events
    )


def test_scoped_owner_approves_request() -> None:
    service, repository, _catalog, _sink, _audit, _exec = _service()
    request = _submit(service)

    decided = service.decide_request(
        actor_context=_actor("checker-1", {"DATA_OWNER"}),
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="OWNERSHIP.VERIFIED",
    )

    assert decided.status is GovernanceApprovalStatus.APPROVED
    assert decided.checker_actor_id == "checker-1"
    assert decided.checker_role == "DATA_OWNER"
    assert repository.get(request.approval_request_id).status is (
        GovernanceApprovalStatus.APPROVED
    )
    decided_events = [
        event
        for event in _audit.prepared_events
        if event.action == "GOVERNANCE_APPROVAL_DECIDED"
    ]
    assert decided_events and decided_events[-1].actor_id == "checker-1"


def test_checker_without_role_or_scope_is_rejected() -> None:
    service, _repository, _catalog, _sink, _audit, _exec = _service()
    request = _submit(service)

    with pytest.raises(GovernanceAuthorizationError, match="role"):
        service.decide_request(
            actor_context=_actor("viewer-1", {"DATA_VIEWER"}),
            approval_request_id=request.approval_request_id,
            decision="APPROVE",
            reason_code="OWNERSHIP.VERIFIED",
        )
    with pytest.raises(GovernanceAuthorizationError, match="scope"):
        service.decide_request(
            actor_context=_actor("owner-2", {"DATA_OWNER"}, dataset_ids={"other"}),
            approval_request_id=request.approval_request_id,
            decision="APPROVE",
            reason_code="OWNERSHIP.VERIFIED",
        )


def test_object_change_invalidates_pending_request() -> None:
    service, repository, catalog, _sink, audit, _exec = _service()
    request = _submit(service)
    catalog.datasets[DATASET_ID] = replace(
        catalog.datasets[DATASET_ID], version=4, owner_user_id="someone-else"
    )

    with pytest.raises(GovernanceConflictError, match="invalidated"):
        service.decide_request(
            actor_context=_actor("checker-1", {"DATA_OWNER"}),
            approval_request_id=request.approval_request_id,
            decision="APPROVE",
            reason_code="OWNERSHIP.VERIFIED",
        )

    assert repository.get(request.approval_request_id).status is (
        GovernanceApprovalStatus.INVALIDATED
    )


def test_only_maker_can_withdraw() -> None:
    service, repository, _catalog, _sink, _audit, _exec = _service()
    request = _submit(service)

    with pytest.raises(GovernanceAuthorizationError, match="maker"):
        service.withdraw_request(
            actor_context=_actor("checker-1", {"DATA_OWNER", "DATA_STEWARD"}),
            approval_request_id=request.approval_request_id,
            reason_code="MAKER.WITHDRAWAL",
        )

    withdrawn = service.withdraw_request(
        actor_context=_actor("maker-1", {"DATA_STEWARD"}),
        approval_request_id=request.approval_request_id,
        reason_code="MAKER.WITHDRAWAL",
    )
    assert withdrawn.status is GovernanceApprovalStatus.WITHDRAWN
    assert repository.get(request.approval_request_id).status is (
        GovernanceApprovalStatus.WITHDRAWN
    )


def test_apply_updates_owner_and_is_idempotent() -> None:
    service, repository, catalog, _sink, audit, _exec = _service()
    request = _submit(service)
    service.decide_request(
        actor_context=_actor("checker-1", {"DATA_OWNER"}),
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="OWNERSHIP.VERIFIED",
    )

    applied = service.apply_request(
        actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
        approval_request_id=request.approval_request_id,
    )

    assert applied.status is GovernanceApprovalStatus.APPLIED
    assert catalog.datasets[DATASET_ID].owner_user_id == "new-owner"
    applied_events = [
        event for event in audit.prepared_events if event.action == "GOVERNANCE_APPROVAL_APPLIED"
    ]
    assert applied_events and applied_events[-1].actor_id == "applier-1"

    replayed = service.apply_request(
        actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
        approval_request_id=request.approval_request_id,
    )
    assert replayed.status is GovernanceApprovalStatus.APPLIED
    assert repository.get(request.approval_request_id).status is (
        GovernanceApprovalStatus.APPLIED
    )


def test_apply_requires_approved_request_and_applier_role() -> None:
    service, _repository, _catalog, _sink, _audit, _exec = _service()
    request = _submit(service)

    with pytest.raises(GovernanceValidationError, match="approved"):
        service.apply_request(
            actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
            approval_request_id=request.approval_request_id,
        )


def test_apply_after_object_change_marks_application_failed() -> None:
    service, repository, catalog, _sink, audit, _exec = _service()
    request = _submit(service)
    service.decide_request(
        actor_context=_actor("checker-1", {"DATA_OWNER"}),
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="OWNERSHIP.VERIFIED",
    )
    # Sürüm değişti ama sahiplik henüz değişmedi: uygulama fail-closed olmalı.
    catalog.datasets[DATASET_ID] = replace(catalog.datasets[DATASET_ID], version=9)

    with pytest.raises(GovernanceConflictError, match="could not be applied"):
        service.apply_request(
            actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
            approval_request_id=request.approval_request_id,
        )

    assert repository.get(request.approval_request_id).status is (
        GovernanceApprovalStatus.APPLICATION_FAILED
    )


# ----------------------------------------------------------------------
# Execution domain (manuel start / cancel / dead-letter)
# ----------------------------------------------------------------------


def _seed_execution(catalog: FakeCatalog, *, status: ExecutionStatus = ExecutionStatus.QUEUED) -> RuleExecution:
    execution = RuleExecution(
        idempotency_key_hash="seed",
        payload_hash="seed",
        rule_version_ids=(RULE_VERSION_ID,),
        scope={},
        triggered_by="scheduler",
        correlation_id="seed-corr",
        source_ids=("source-1",),
        execution_id=EXECUTION_ID,
        execution_type=ExecutionType.SCHEDULED,
        status=status,
    )
    catalog.executions[EXECUTION_ID] = execution
    return execution


def _seed_dead_letter(
    catalog: FakeCatalog, *, status: DeadLetterStatus = DeadLetterStatus.OPEN
) -> DeadLetterRecord:
    _seed_execution(catalog)
    letter = DeadLetterRecord(
        dead_letter_id=DEAD_LETTER_ID,
        job_id=EXECUTION_ID,
        error_class="CONNECTOR_TIMEOUT",
        attempt_count=3,
        status=status,
        created_at=NOW,
    )
    catalog.dead_letters[DEAD_LETTER_ID] = letter
    return letter


def _submit_execution_start(service):
    return service.submit_request(
        actor_context=_actor("maker-1", {"DATA_STEWARD"}),
        request_type="EXECUTION_MANUAL_START",
        object_id="new-exec-id",
        reason_code="EXECUTION.MANUAL.START",
        proposed_changes={"rule_version_ids": [RULE_VERSION_ID], "execution_mode": "OFFICIAL"},
    )


def _submit_execution_cancel(service, catalog):
    _seed_execution(catalog)
    return service.submit_request(
        actor_context=_actor("maker-1", {"DATA_STEWARD"}),
        request_type="EXECUTION_CANCEL",
        object_id=EXECUTION_ID,
        reason_code="EXECUTION.CANCEL",
        proposed_changes={"reason": "Operator requested cancellation"},
    )


def _submit_dead_letter_reprocess(service, catalog):
    _seed_dead_letter(catalog)
    return service.submit_request(
        actor_context=_actor("maker-1", {"DATA_STEWARD"}),
        request_type="DEAD_LETTER_REPROCESS",
        object_id=DEAD_LETTER_ID,
        reason_code="EXECUTION.DEAD.LETTER.REPROCESS",
    )


def test_maker_submits_execution_manual_start() -> None:
    service, repository, _catalog, _sink, _audit, _exec = _service()

    request = _submit_execution_start(service)

    assert request.status is GovernanceApprovalStatus.SUBMITTED
    assert request.object_type == "RuleExecution"
    assert request.scope_version == 0
    assert request.change_summary["after"]["rule_version_ids"] == [RULE_VERSION_ID]
    assert request.change_summary["after"]["execution_mode"] == "OFFICIAL"
    assert "dataset_versions" in request.change_summary["before"]
    assert repository.get(request.approval_request_id) is request


def test_execution_start_requires_rule_version_ids() -> None:
    service, _repository, _catalog, _sink, _audit, _exec = _service()

    with pytest.raises(GovernanceValidationError, match="rule_version_ids"):
        service.submit_request(
            actor_context=_actor("maker-1", {"DATA_STEWARD"}),
            request_type="EXECUTION_MANUAL_START",
            object_id="new-exec-id",
            reason_code="EXECUTION.MANUAL.START",
            proposed_changes=None,
        )
    with pytest.raises(GovernanceValidationError, match="At least one"):
        service.submit_request(
            actor_context=_actor("maker-1", {"DATA_STEWARD"}),
            request_type="EXECUTION_MANUAL_START",
            object_id="new-exec-id",
            reason_code="EXECUTION.MANUAL.START",
            proposed_changes={"rule_version_ids": []},
        )


def test_execution_start_validates_execution_mode() -> None:
    service, _repository, _catalog, _sink, _audit, _exec = _service()

    with pytest.raises(GovernanceValidationError, match="execution mode"):
        service.submit_request(
            actor_context=_actor("maker-1", {"DATA_STEWARD"}),
            request_type="EXECUTION_MANUAL_START",
            object_id="new-exec-id",
            reason_code="EXECUTION.MANUAL.START",
            proposed_changes={"rule_version_ids": [RULE_VERSION_ID], "execution_mode": "INVALID"},
        )


def test_execution_start_maker_outside_scope_cannot_submit() -> None:
    service, _repository, _catalog, _sink, _audit, _exec = _service()

    with pytest.raises(GovernanceAuthorizationError, match="scope"):
        service.submit_request(
            actor_context=_actor("maker-1", {"DATA_STEWARD"}, dataset_ids={"other"}),
            request_type="EXECUTION_MANUAL_START",
            object_id="new-exec-id",
            reason_code="EXECUTION.MANUAL.START",
            proposed_changes={"rule_version_ids": [RULE_VERSION_ID]},
        )


def test_maker_submits_execution_cancel() -> None:
    service, repository, catalog, _sink, _audit, _exec = _service()

    request = _submit_execution_cancel(service, catalog)

    assert request.status is GovernanceApprovalStatus.SUBMITTED
    assert request.object_type == "RuleExecution"
    assert request.object_id == EXECUTION_ID
    assert request.change_summary["after"]["status"] == "CANCELLED"
    assert request.change_summary["before"]["status"] == "QUEUED"


def test_cancel_rejects_terminal_execution() -> None:
    service, _repository, catalog, _sink, _audit, _exec = _service()
    _seed_execution(catalog, status=ExecutionStatus.SUCCESS)

    with pytest.raises(GovernanceValidationError, match="terminal"):
        service.submit_request(
            actor_context=_actor("maker-1", {"DATA_STEWARD"}),
            request_type="EXECUTION_CANCEL",
            object_id=EXECUTION_ID,
            reason_code="EXECUTION.CANCEL",
            proposed_changes={"reason": "cancel attempt"},
        )


def test_maker_submits_dead_letter_reprocess() -> None:
    service, repository, catalog, _sink, _audit, _exec = _service()

    request = _submit_dead_letter_reprocess(service, catalog)

    assert request.status is GovernanceApprovalStatus.SUBMITTED
    assert request.object_type == "DeadLetterRecord"
    assert request.object_id == DEAD_LETTER_ID
    assert request.change_summary["after"]["status"] == "REPROCESSED"


def test_dead_letter_reprocess_rejects_already_reprocessed() -> None:
    service, _repository, catalog, _sink, _audit, _exec = _service()
    _seed_dead_letter(catalog, status=DeadLetterStatus.REPROCESSED)

    with pytest.raises(GovernanceValidationError, match="already been reprocessed"):
        service.submit_request(
            actor_context=_actor("maker-1", {"DATA_STEWARD"}),
            request_type="DEAD_LETTER_REPROCESS",
            object_id=DEAD_LETTER_ID,
            reason_code="EXECUTION.DEAD.LETTER.REPROCESS",
        )


def test_execution_start_full_approve_apply_flow() -> None:
    service, repository, _catalog, _sink, audit, exec_writer = _service()
    request = _submit_execution_start(service)

    decided = service.decide_request(
        actor_context=_actor("checker-1", {"DATA_OWNER"}),
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="EXECUTION.VERIFIED",
    )
    assert decided.status is GovernanceApprovalStatus.APPROVED

    applied = service.apply_request(
        actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
        approval_request_id=request.approval_request_id,
    )
    assert applied.status is GovernanceApprovalStatus.APPLIED
    assert len(exec_writer.started) == 1
    applied_events = [
        event for event in audit.prepared_events if event.action == "GOVERNANCE_APPROVAL_APPLIED"
    ]
    assert applied_events and applied_events[-1].actor_id == "applier-1"

    # Idempotent replay
    replayed = service.apply_request(
        actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
        approval_request_id=request.approval_request_id,
    )
    assert replayed.status is GovernanceApprovalStatus.APPLIED


def test_execution_cancel_full_approve_apply_flow() -> None:
    service, _repository, catalog, _sink, audit, exec_writer = _service()
    request = _submit_execution_cancel(service, catalog)

    service.decide_request(
        actor_context=_actor("checker-1", {"DATA_OWNER"}),
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="EXECUTION.VERIFIED",
    )

    applied = service.apply_request(
        actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
        approval_request_id=request.approval_request_id,
    )
    assert applied.status is GovernanceApprovalStatus.APPLIED
    assert len(exec_writer.cancelled) == 1
    assert exec_writer.cancelled[0].status is ExecutionStatus.CANCELLED


def test_dead_letter_full_approve_apply_flow() -> None:
    service, _repository, catalog, _sink, audit, exec_writer = _service()
    request = _submit_dead_letter_reprocess(service, catalog)

    service.decide_request(
        actor_context=_actor("checker-1", {"DATA_OWNER"}),
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="EXECUTION.VERIFIED",
    )

    applied = service.apply_request(
        actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
        approval_request_id=request.approval_request_id,
    )
    assert applied.status is GovernanceApprovalStatus.APPLIED
    assert len(exec_writer.reprocessed) == 1
    assert exec_writer.reprocessed[0] == DEAD_LETTER_ID


def test_execution_apply_without_writer_raises() -> None:
    repository = FakeGovernanceRepository()
    catalog = FakeCatalog()
    audit = FakeTransactionalAudit()
    service = GovernanceApprovalCommandService(
        repository,
        catalog,
        FakeOwnershipWriter(catalog),
        audit_sink=FakeAuditSink(),
        transactional_audit=audit,
        policy=_policy(),
        metadata_writer=FakeMetadataWriter(catalog),
        execution_writer=None,
        clock=lambda: NOW,
    )
    request = _submit_execution_start(service)
    service.decide_request(
        actor_context=_actor("checker-1", {"DATA_OWNER"}),
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="EXECUTION.VERIFIED",
    )

    with pytest.raises(GovernanceValidationError, match="not configured"):
        service.apply_request(
            actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
            approval_request_id=request.approval_request_id,
        )


def test_execution_dataset_version_change_invalidates_pending() -> None:
    service, repository, catalog, _sink, _audit, _exec = _service()
    request = _submit_execution_start(service)

    # Dataset version changes between submit and decide
    catalog.datasets[DATASET_ID] = replace(catalog.datasets[DATASET_ID], version=99)

    with pytest.raises(GovernanceConflictError, match="invalidated"):
        service.decide_request(
            actor_context=_actor("checker-1", {"DATA_OWNER"}),
            approval_request_id=request.approval_request_id,
            decision="APPROVE",
            reason_code="EXECUTION.VERIFIED",
        )

    assert repository.get(request.approval_request_id).status is (
        GovernanceApprovalStatus.INVALIDATED
    )


def test_expired_request_cannot_be_decided() -> None:
    service, repository, _catalog, _sink, _audit, _exec = _service()
    request = _submit(service)
    expired_request = GovernanceApprovalRequest(
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
        requested_at=request.requested_at,
        expires_at=NOW - timedelta(hours=1),
    )
    repository._requests[request.approval_request_id] = expired_request

    with pytest.raises(GovernanceValidationError, match="expired"):
        service.decide_request(
            actor_context=_actor("checker-1", {"DATA_OWNER"}),
            approval_request_id=request.approval_request_id,
            decision="APPROVE",
            reason_code="OWNERSHIP.VERIFIED",
        )

    assert repository.get(request.approval_request_id).status is (
        GovernanceApprovalStatus.EXPIRED
    )


# ----------------------------------------------------------------------
# Metadata ve sınıflandırma domain'i
# ----------------------------------------------------------------------


def _submit_metadata(service, *, proposed_changes=None, reason="METADATA.CRITICALITY.CHANGE"):
    return service.submit_request(
        actor_context=_actor("maker-1", {"DATA_STEWARD"}),
        request_type="METADATA_CRITICAL_CHANGE",
        object_id=DATASET_ID,
        reason_code=reason,
        proposed_changes=(
            {"criticality": "CRITICAL"} if proposed_changes is None else proposed_changes
        ),
    )


def _submit_field_sensitivity(service, *, proposed_changes=None):
    return service.submit_request(
        actor_context=_actor("maker-1", {"DATA_STEWARD"}),
        request_type="FIELD_SENSITIVITY_MARK",
        object_id=FIELD_ID,
        reason_code="METADATA.SENSITIVITY.MARK",
        proposed_changes={"is_sensitive": True} if proposed_changes is None else proposed_changes,
    )


def test_maker_submits_metadata_critical_change() -> None:
    service, repository, _catalog, _sink, _audit, _exec = _service()

    request = _submit_metadata(
        service, proposed_changes={"criticality": "CRITICAL", "status": "INACTIVE"}
    )

    assert request.status is GovernanceApprovalStatus.SUBMITTED
    assert request.object_type == "Dataset"
    assert request.scope_version == 3
    assert request.change_summary["before"] == {"criticality": "MEDIUM", "status": "ACTIVE"}
    assert request.change_summary["after"] == {"criticality": "CRITICAL", "status": "INACTIVE"}
    assert repository.get(request.approval_request_id) is request


def test_maker_submits_field_sensitivity_mark() -> None:
    service, repository, _catalog, _sink, _audit, _exec = _service()

    request = _submit_field_sensitivity(
        service, proposed_changes={"is_sensitive": True, "classification": "PERSONAL_DATA"}
    )

    assert request.status is GovernanceApprovalStatus.SUBMITTED
    assert request.object_type == "DataField"
    assert request.object_id == FIELD_ID
    assert request.scope_type == "DATASET"
    assert request.scope_id == DATASET_ID
    assert request.scope_version == 2
    assert request.change_summary["before"] == {
        "is_sensitive": False,
        "classification": "UNCLASSIFIED",
    }
    assert request.change_summary["after"] == {
        "is_sensitive": True,
        "classification": "PERSONAL_DATA",
    }


def test_metadata_submission_rejects_non_governed_or_empty_changes() -> None:
    service, _repository, _catalog, _sink, _audit, _exec = _service()

    with pytest.raises(GovernanceValidationError, match="non-governed"):
        _submit_metadata(service, proposed_changes={"name": "yeni-ad"})
    with pytest.raises(GovernanceValidationError, match="proposed changes"):
        _submit_metadata(service, proposed_changes={})


def test_metadata_submission_validates_values_and_noop_changes() -> None:
    service, _repository, _catalog, _sink, _audit, _exec = _service()

    with pytest.raises(GovernanceValidationError, match="criticality"):
        _submit_metadata(service, proposed_changes={"criticality": "ULTRA"})
    with pytest.raises(GovernanceValidationError, match="modify"):
        _submit_metadata(service, proposed_changes={"criticality": "MEDIUM"})
    with pytest.raises(GovernanceValidationError, match="boolean"):
        _submit_field_sensitivity(service, proposed_changes={"is_sensitive": "yes"})
    with pytest.raises(GovernanceValidationError, match="classification"):
        _submit_field_sensitivity(service, proposed_changes={"classification": "TOP_SECRET"})
    with pytest.raises(GovernanceNotFoundError):
        service.submit_request(
            actor_context=_actor("maker-1", {"DATA_STEWARD"}),
            request_type="FIELD_SENSITIVITY_MARK",
            object_id="field-missing",
            reason_code="METADATA.SENSITIVITY.MARK",
            proposed_changes={"is_sensitive": True},
        )


def test_metadata_maker_outside_scope_cannot_submit() -> None:
    service, _repository, _catalog, _sink, _audit, _exec = _service()

    with pytest.raises(GovernanceAuthorizationError, match="scope"):
        service.submit_request(
            actor_context=_actor("maker-1", {"DATA_STEWARD"}, dataset_ids={"other"}),
            request_type="FIELD_SENSITIVITY_MARK",
            object_id=FIELD_ID,
            reason_code="METADATA.SENSITIVITY.MARK",
            proposed_changes={"is_sensitive": True},
        )


def test_metadata_apply_updates_dataset_and_is_idempotent() -> None:
    service, repository, catalog, _sink, audit, _exec = _service()
    request = _submit_metadata(service)
    service.decide_request(
        actor_context=_actor("checker-1", {"DATA_OWNER"}),
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="METADATA.VERIFIED",
    )

    applied = service.apply_request(
        actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
        approval_request_id=request.approval_request_id,
    )

    assert applied.status is GovernanceApprovalStatus.APPLIED
    assert catalog.datasets[DATASET_ID].criticality is Criticality.CRITICAL
    applied_events = [
        event for event in audit.prepared_events if event.action == "GOVERNANCE_APPROVAL_APPLIED"
    ]
    assert applied_events and applied_events[-1].actor_id == "applier-1"
    assert applied_events[-1].object_type == "Dataset"

    replayed = service.apply_request(
        actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
        approval_request_id=request.approval_request_id,
    )
    assert replayed.status is GovernanceApprovalStatus.APPLIED
    assert repository.get(request.approval_request_id).status is (
        GovernanceApprovalStatus.APPLIED
    )


def test_field_sensitivity_apply_updates_field() -> None:
    service, _repository, catalog, _sink, audit, _exec = _service()
    request = _submit_field_sensitivity(
        service, proposed_changes={"is_sensitive": True, "classification": "PERSONAL_DATA"}
    )
    service.decide_request(
        actor_context=_actor("checker-1", {"DATA_OWNER"}),
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="METADATA.VERIFIED",
    )

    applied = service.apply_request(
        actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
        approval_request_id=request.approval_request_id,
    )

    assert applied.status is GovernanceApprovalStatus.APPLIED
    updated = catalog.fields[FIELD_ID]
    assert updated.is_sensitive is True
    assert updated.classification is ClassificationCode.PERSONAL_DATA
    applied_events = [
        event for event in audit.prepared_events if event.action == "GOVERNANCE_APPROVAL_APPLIED"
    ]
    assert applied_events and applied_events[-1].object_type == "DataField"


def test_metadata_object_change_invalidates_pending_request() -> None:
    service, repository, catalog, _sink, _audit, _exec = _service()
    request = _submit_metadata(service)
    catalog.datasets[DATASET_ID] = replace(
        catalog.datasets[DATASET_ID], criticality=Criticality.HIGH, version=4
    )

    with pytest.raises(GovernanceConflictError, match="invalidated"):
        service.decide_request(
            actor_context=_actor("checker-1", {"DATA_OWNER"}),
            approval_request_id=request.approval_request_id,
            decision="APPROVE",
            reason_code="METADATA.VERIFIED",
        )

    assert repository.get(request.approval_request_id).status is (
        GovernanceApprovalStatus.INVALIDATED
    )


def test_metadata_apply_after_version_change_marks_application_failed() -> None:
    service, repository, catalog, _sink, _audit, _exec = _service()
    request = _submit_field_sensitivity(service)
    service.decide_request(
        actor_context=_actor("checker-1", {"DATA_OWNER"}),
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="METADATA.VERIFIED",
    )
    catalog.fields[FIELD_ID] = replace(catalog.fields[FIELD_ID], version=9)

    with pytest.raises(GovernanceConflictError, match="could not be applied"):
        service.apply_request(
            actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
            approval_request_id=request.approval_request_id,
        )

    assert repository.get(request.approval_request_id).status is (
        GovernanceApprovalStatus.APPLICATION_FAILED
    )
