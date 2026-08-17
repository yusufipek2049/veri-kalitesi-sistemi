"""Metadata diff uygulama governance akışı birim testleri.

Kapsam:
- METADATA_DIFF_APPLICATION submit doğrulamaları (PENDING olmayan diff,
  boş/geçersiz seçim, kapsam dışı maker)
- apply happy path, idempotent tekrar ve diff değişince INVALIDATED
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from veri_kalitesi.data_sources.errors import ConflictError as DataSourceConflictError
from veri_kalitesi.data_sources.errors import NotFoundError as DataSourceNotFoundError
from veri_kalitesi.data_sources.models import Dataset, MetadataDiff, MetadataDiffStatus
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

NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
ACTOR_POLICY_VERSION = "GOVERNANCE_UNIT_POLICY_V1"
GOVERNANCE_POLICY_VERSION = "GOVERNANCE_APPROVAL_POLICY_V1"
DIFF_ID = "diff-gov-1"
SOURCE_ID = "source-1"
DATASET_ID = "dataset-customers"


class FakeAuditSink:
    def __init__(self) -> None:
        self.events: list = []

    def append(self, event) -> None:
        self.events.append(event)


class FakeTransactionalAudit:
    def __init__(self) -> None:
        self.prepared_events: list = []
        self.published = 0

    def prepare(self, event):
        self.prepared_events.append(event)
        return object()

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
        updated = replace(request, version=expected_version + 1)
        self._requests[request.approval_request_id] = updated
        return updated


class FakeDiffWriter:
    def __init__(self) -> None:
        self.diffs: dict[str, MetadataDiff] = {}
        self.dataset_versions: dict[str, int] = {DATASET_ID: 5}
        self.apply_calls: list[dict] = []
        self.raise_conflict_on_apply = False

    def get_metadata_diff(self, metadata_diff_id: str) -> MetadataDiff:
        if metadata_diff_id not in self.diffs:
            raise DataSourceNotFoundError("diff missing")
        return self.diffs[metadata_diff_id]

    def dataset_versions_for_diff(
        self, data_source_id: str, dataset_keys: frozenset[tuple[str, str]]
    ) -> dict[str, int]:
        return dict(self.dataset_versions)

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
        if self.raise_conflict_on_apply:
            raise DataSourceConflictError("diff changed")
        diff = self.get_metadata_diff(metadata_diff_id)
        if diff.version != expected_version:
            raise DataSourceConflictError("diff changed")
        applied = replace(diff, status=MetadataDiffStatus.APPLIED, version=diff.version + 1)
        self.diffs[metadata_diff_id] = applied
        self.apply_calls.append(
            {
                "actor_id": actor_id,
                "metadata_diff_id": metadata_diff_id,
                "reason_code": reason_code,
                "expected_version": expected_version,
                "selected_objects": selected_objects,
            }
        )
        return applied


class FakeCatalog:
    def __init__(self) -> None:
        self.datasets: dict[str, Dataset] = {
            DATASET_ID: Dataset(
                data_source_id=SOURCE_ID,
                namespace="public",
                name="customers",
                dataset_id=DATASET_ID,
                version=5,
            )
        }

    def get_dataset(self, dataset_id: str) -> Dataset:
        if dataset_id not in self.datasets:
            raise GovernanceNotFoundError("dataset missing")
        return self.datasets[dataset_id]


def _pending_diff() -> MetadataDiff:
    return MetadataDiff(
        metadata_diff_id=DIFF_ID,
        discovery_id=1,
        data_source_id=SOURCE_ID,
        added_objects=(
            {
                "object_type": "DATA_FIELD",
                "namespace": "public",
                "dataset_name": "customers",
                "field_name": "email",
                "new_values": {"native_data_type": "text"},
            },
        ),
        changed_objects=(
            {
                "object_type": "DATA_FIELD",
                "namespace": "public",
                "dataset_name": "customers",
                "field_name": "amount",
                "new_values": {"native_data_type": "numeric"},
            },
        ),
        removed_objects=(),
        version=1,
    )


def _policy() -> GovernanceApprovalPolicy:
    return GovernanceApprovalPolicy(
        version=GOVERNANCE_POLICY_VERSION,
        actor_policy_version=ACTOR_POLICY_VERSION,
        maker_roles=frozenset({"DATA_STEWARD"}),
        checker_roles=frozenset({"DATA_OWNER"}),
        applier_roles=frozenset({"DATA_GOVERNANCE_SPECIALIST"}),
    )


def _service(writer: FakeDiffWriter | None = None):
    writer = writer or FakeDiffWriter()
    repository = FakeGovernanceRepository()
    catalog = FakeCatalog()
    service = GovernanceApprovalCommandService(
        repository,
        catalog,
        ownership_writer=object(),
        audit_sink=FakeAuditSink(),
        transactional_audit=FakeTransactionalAudit(),
        policy=_policy(),
        diff_writer=writer,
        clock=lambda: NOW,
    )
    return service, repository, writer


def _actor(
    actor_id: str,
    roles: set[str],
    *,
    dataset_ids: set[str] | None = None,
):
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=ActorType.USER,
        authentication_source="synthetic-identity-adapter",
        session_id=f"session-{actor_id}",
        roles=frozenset(roles),
        permitted_source_ids=frozenset({SOURCE_ID}),
        permitted_dataset_ids=frozenset(dataset_ids or {DATASET_ID}),
        can_view_enterprise=False,
        privileged=False,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id=f"correlation-{actor_id}",
    )


_SELECTION = [["ADDED", "DATA_FIELD", "public", "customers", "email"]]


def _submit(service: GovernanceApprovalCommandService, actor, selection=_SELECTION):
    return service.submit_request(
        actor_context=actor,
        request_type="METADATA_DIFF_APPLICATION",
        object_id=DIFF_ID,
        reason_code="METADATA.DIFF.APPLICATION",
        proposed_changes={"selected_objects": selection},
    )


def _approve(service: GovernanceApprovalCommandService, request) -> GovernanceApprovalRequest:
    return service.decide_request(
        actor_context=_actor("checker-1", {"DATA_OWNER"}),
        approval_request_id=request.approval_request_id,
        decision="APPROVE",
        reason_code="METADATA.VERIFIED",
    )


class TestDiffApplicationSubmit:
    def test_submit_builds_request_with_selection_summary(self) -> None:
        service, _repository, writer = _service()
        writer.diffs[DIFF_ID] = _pending_diff()

        request = _submit(service, _actor("maker-1", {"DATA_STEWARD"}))

        assert request.status is GovernanceApprovalStatus.SUBMITTED
        assert request.object_type == "MetadataDiff"
        assert request.scope_type == "DATA_SOURCE"
        assert request.scope_id == SOURCE_ID
        assert request.scope_version == 1
        assert request.change_summary["before"]["status"] == "PENDING"
        assert request.change_summary["before"]["dataset_versions"] == {DATASET_ID: 5}
        assert request.change_summary["selected"] == _SELECTION
        assert request.change_summary["counts"] == {"added": 1, "changed": 0, "removed": 0}

    def test_submit_requires_pending_diff(self) -> None:
        service, _repository, writer = _service()
        writer.diffs[DIFF_ID] = replace(_pending_diff(), status=MetadataDiffStatus.APPLIED)

        with pytest.raises(GovernanceValidationError, match="pending"):
            _submit(service, _actor("maker-1", {"DATA_STEWARD"}))

    def test_submit_requires_existing_diff(self) -> None:
        service, _repository, _writer = _service()

        with pytest.raises(GovernanceNotFoundError):
            _submit(service, _actor("maker-1", {"DATA_STEWARD"}))

    def test_submit_rejects_empty_selection(self) -> None:
        service, _repository, writer = _service()
        writer.diffs[DIFF_ID] = _pending_diff()

        with pytest.raises(GovernanceValidationError, match="selection"):
            _submit(service, _actor("maker-1", {"DATA_STEWARD"}), selection=[])

    def test_submit_rejects_unknown_selection_entry(self) -> None:
        service, _repository, writer = _service()
        writer.diffs[DIFF_ID] = _pending_diff()

        with pytest.raises(GovernanceValidationError, match="not part"):
            _submit(
                service,
                _actor("maker-1", {"DATA_STEWARD"}),
                selection=[["ADDED", "DATA_FIELD", "public", "customers", "missing"]],
            )

    def test_submit_rejects_out_of_scope_maker(self) -> None:
        service, _repository, writer = _service()
        writer.diffs[DIFF_ID] = _pending_diff()

        with pytest.raises(GovernanceAuthorizationError):
            _submit(service, _actor("maker-1", {"DATA_STEWARD"}, dataset_ids={"other-dataset"}))


class TestDiffApplicationApply:
    def test_apply_writes_selection_through_writer(self) -> None:
        service, _repository, writer = _service()
        writer.diffs[DIFF_ID] = _pending_diff()
        request = _submit(service, _actor("maker-1", {"DATA_STEWARD"}))
        approved = _approve(service, request)

        applied = service.apply_request(
            actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
            approval_request_id=approved.approval_request_id,
        )

        assert applied.status is GovernanceApprovalStatus.APPLIED
        assert writer.diffs[DIFF_ID].status is MetadataDiffStatus.APPLIED
        assert len(writer.apply_calls) == 1
        call = writer.apply_calls[0]
        assert call["actor_id"] == "applier-1"
        assert call["expected_version"] == 1
        assert call["selected_objects"] == frozenset(
            {("ADDED", "DATA_FIELD", "public", "customers", "email")}
        )

    def test_apply_is_idempotent_when_diff_already_applied(self) -> None:
        service, _repository, writer = _service()
        writer.diffs[DIFF_ID] = _pending_diff()
        request = _submit(service, _actor("maker-1", {"DATA_STEWARD"}))
        approved = _approve(service, request)
        writer.diffs[DIFF_ID] = replace(writer.diffs[DIFF_ID], status=MetadataDiffStatus.APPLIED)

        applied = service.apply_request(
            actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
            approval_request_id=approved.approval_request_id,
        )

        assert applied.status is GovernanceApprovalStatus.APPLIED
        assert writer.apply_calls == []

    def test_apply_invalidates_request_when_diff_changed(self) -> None:
        service, repository, writer = _service()
        writer.diffs[DIFF_ID] = _pending_diff()
        request = _submit(service, _actor("maker-1", {"DATA_STEWARD"}))
        approved = _approve(service, request)
        # Keşif yeni bir diff sürümü üretti: kapsam denetimi bozulur.
        writer.diffs[DIFF_ID] = replace(writer.diffs[DIFF_ID], version=2)

        with pytest.raises(GovernanceConflictError):
            service.apply_request(
                actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
                approval_request_id=approved.approval_request_id,
            )

        assert (
            repository.get(approved.approval_request_id).status
            is GovernanceApprovalStatus.INVALIDATED
        )
        assert writer.apply_calls == []

    def test_apply_invalidates_when_writer_reports_conflict(self) -> None:
        service, repository, writer = _service()
        writer.diffs[DIFF_ID] = _pending_diff()
        request = _submit(service, _actor("maker-1", {"DATA_STEWARD"}))
        approved = _approve(service, request)
        writer.raise_conflict_on_apply = True

        with pytest.raises(GovernanceConflictError):
            service.apply_request(
                actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
                approval_request_id=approved.approval_request_id,
            )

        assert (
            repository.get(approved.approval_request_id).status
            is GovernanceApprovalStatus.APPLICATION_FAILED
        )
