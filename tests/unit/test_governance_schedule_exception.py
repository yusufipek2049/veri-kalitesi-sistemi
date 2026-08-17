"""SCHEDULE_INTERVAL_EXCEPTION maker-checker akış testleri.

Bant dışı zamanlayıcı talebinin submit/decide/apply yaşam döngüsünü,
OCC invalidation'ını ve idempotent uygulamayı doğrular.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from veri_kalitesi.data_sources.models import DataField, Dataset, TimelinessNature
from veri_kalitesi.governance import (
    GovernanceApprovalCommandService,
    GovernanceApprovalPolicy,
    GovernanceApprovalStatus,
)
from veri_kalitesi.governance.errors import (
    GovernanceConflictError,
    GovernanceValidationError,
)
from veri_kalitesi.identity import ActorContextIssuer, ActorType
from veri_kalitesi.rules.models import (
    QualityDimension,
    QualityRule,
    RuleCriticality,
    RuleStatus,
    RuleType,
    RuleVersion,
)

NOW = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
ACTOR_POLICY_VERSION = "GOVERNANCE_SCHEDULE_POLICY_V1"
DATASET_ID = "dataset-schedule"
RULE_ID = "rule-schedule-1"
RULE_VERSION_ID = "rv-schedule-1"


class FakeAuditSink:
    def __init__(self) -> None:
        self.events: list = []

    def append(self, event) -> None:
        self.events.append(event)


class FakeTransactionalAudit:
    def prepare(self, event):
        return object()

    def publish_pending(self, *, limit: int = 100):
        return None


class FakeGovernanceRepository:
    def __init__(self) -> None:
        self.requests: dict = {}

    def add(self, request, *, audit_event, audit_outbox):
        self.requests[request.approval_request_id] = request
        return request

    def get(self, approval_request_id: str):
        from veri_kalitesi.governance.errors import GovernanceNotFoundError

        if approval_request_id not in self.requests:
            raise GovernanceNotFoundError("missing")
        return self.requests[approval_request_id]

    def transition(self, request, *, expected_version, expected_status, audit_event, audit_outbox):
        stored = self.requests[request.approval_request_id]
        updated = replace(
            stored,
            status=request.status,
            version=expected_version + 1,
            checker_actor_id=request.checker_actor_id,
            checker_role=request.checker_role,
            reason_code=request.reason_code,
            decided_at=request.decided_at,
            applied_at=request.applied_at,
        )
        self.requests[request.approval_request_id] = updated
        return updated

    def list_for_scope(self, *, dataset_ids, source_ids):
        return list(self.requests.values())


class FakeCatalog:
    def __init__(self, *, nature: TimelinessNature | None) -> None:
        self.datasets: dict[str, Dataset] = {
            DATASET_ID: Dataset(
                data_source_id="source-1",
                namespace="core",
                name="Yakın zamanlı tablo",
                owner_user_id="owner-1",
                timeliness_nature=nature,
                dataset_id=DATASET_ID,
                version=3,
            )
        }
        self.rules: dict[str, QualityRule] = {
            RULE_ID: QualityRule(
                code="RQ-S01",
                name="Zamanlayıcı kuralı",
                dataset_id=DATASET_ID,
                field_ids=(),
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
                definition={"operator": "IS_NOT_NULL"},
                threshold=0.95,
                weight=1.0,
                criticality=RuleCriticality.HIGH,
                rule_version_id=RULE_VERSION_ID,
            ),
        }

    def get_dataset(self, dataset_id: str) -> Dataset:
        if dataset_id not in self.datasets:
            raise KeyError(dataset_id)
        return self.datasets[dataset_id]

    def get_data_field(self, field_id: str) -> DataField:
        raise KeyError(field_id)

    def get_rule(self, quality_rule_id: str) -> QualityRule:
        return self.rules[quality_rule_id]

    def get_rule_version(self, rule_version_id: str) -> RuleVersion:
        return self.rule_versions[rule_version_id]

    def get_execution(self, execution_id: str):
        raise KeyError(execution_id)

    def get_dead_letter(self, dead_letter_id: str):
        raise KeyError(dead_letter_id)


class FakeScheduleWriter:
    def __init__(self) -> None:
        self.calls: list = []

    def apply_schedule_interval(self, *, request, actor_context):
        self.calls.append(request)
        return object()


def _policy() -> GovernanceApprovalPolicy:
    return GovernanceApprovalPolicy(
        version="GOVERNANCE_APPROVAL_POLICY_V1",
        actor_policy_version=ACTOR_POLICY_VERSION,
        maker_roles=frozenset({"DATA_STEWARD"}),
        checker_roles=frozenset({"DATA_OWNER"}),
        applier_roles=frozenset({"DATA_GOVERNANCE_SPECIALIST"}),
    )


def _service(*, nature: TimelinessNature | None = TimelinessNature.NEAR_TIME):
    repository = FakeGovernanceRepository()
    catalog = FakeCatalog(nature=nature)
    writer = FakeScheduleWriter()
    service = GovernanceApprovalCommandService(
        repository,
        catalog,
        None,  # type: ignore[arg-type]
        audit_sink=FakeAuditSink(),
        transactional_audit=FakeTransactionalAudit(),
        policy=_policy(),
        schedule_writer=writer,
        clock=lambda: NOW,
    )
    return service, repository, catalog, writer


def _actor(actor_id: str, roles: set[str]):
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=ActorType.USER,
        authentication_source="synthetic-identity-adapter",
        session_id=f"session-{actor_id}",
        roles=frozenset(roles),
        permitted_source_ids=frozenset({"source-1"}),
        permitted_dataset_ids=frozenset({DATASET_ID}),
        can_view_enterprise=False,
        privileged=False,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=ACTOR_POLICY_VERSION,
        correlation_id=f"correlation-{actor_id}",
    )


def _proposal(**overrides):
    payload = {
        "name": "Bant dışı yakın zamanlı job",
        "schedule_type": "INTERVAL",
        "timezone_name": "Europe/Istanbul",
        "rule_version_ids": [RULE_VERSION_ID],
        "interval_minutes": 30,
    }
    payload.update(overrides)
    return payload


def _submit(service) -> str:
    request = service.submit_request(
        actor_context=_actor("maker-1", {"DATA_STEWARD"}),
        request_type="SCHEDULE_INTERVAL_EXCEPTION",
        object_id=DATASET_ID,
        reason_code="SCHEDULE.OUT_OF_BAND.REQUEST",
        proposed_changes={"schedule": _proposal()},
    )
    return request.approval_request_id


def test_out_of_band_submission_stores_schedule_proposal() -> None:
    service, _repository, _catalog, _writer = _service()

    request = service.submit_request(
        actor_context=_actor("maker-1", {"DATA_STEWARD"}),
        request_type="SCHEDULE_INTERVAL_EXCEPTION",
        object_id=DATASET_ID,
        reason_code="SCHEDULE.OUT_OF_BAND.REQUEST",
        proposed_changes={"schedule": _proposal()},
    )

    assert request.status is GovernanceApprovalStatus.SUBMITTED
    assert request.object_type == "Dataset"
    assert request.object_id == DATASET_ID
    assert request.scope_version == 3
    assert request.change_summary["before"] == {"timeliness_nature": "NEAR_TIME"}
    schedule = request.change_summary["after"]["schedule"]
    assert schedule["interval_minutes"] == 30
    assert schedule["schedule_id"]
    assert schedule["rule_version_ids"] == [RULE_VERSION_ID]


def test_within_band_schedule_does_not_require_governance() -> None:
    service, _repository, _catalog, _writer = _service()

    with pytest.raises(GovernanceValidationError, match="recommended band"):
        service.submit_request(
            actor_context=_actor("maker-1", {"DATA_STEWARD"}),
            request_type="SCHEDULE_INTERVAL_EXCEPTION",
            object_id=DATASET_ID,
            reason_code="SCHEDULE.OUT_OF_BAND.REQUEST",
            proposed_changes={"schedule": _proposal(interval_minutes=10)},
        )


def test_missing_nature_blocks_schedule_exception_submission() -> None:
    service, _repository, _catalog, _writer = _service(nature=None)

    with pytest.raises(GovernanceValidationError, match="timeliness nature"):
        _submit(service)


def test_invalid_reason_code_is_rejected() -> None:
    service, _repository, _catalog, _writer = _service()

    with pytest.raises(GovernanceValidationError, match="reason code"):
        service.submit_request(
            actor_context=_actor("maker-1", {"DATA_STEWARD"}),
            request_type="SCHEDULE_INTERVAL_EXCEPTION",
            object_id=DATASET_ID,
            reason_code="TOTALLY.UNKNOWN.CODE",
            proposed_changes={"schedule": _proposal()},
        )


def test_maker_cannot_decide_own_schedule_request() -> None:
    service, _repository, _catalog, _writer = _service()
    approval_id = _submit(service)

    with pytest.raises(Exception, match="Maker cannot"):
        service.decide_request(
            actor_context=_actor("maker-1", {"DATA_OWNER"}),
            approval_request_id=approval_id,
            decision="APPROVE",
            reason_code="SCHEDULE.OUT_OF_BAND.VERIFIED",
        )


def test_approve_and_apply_creates_schedule_idempotently() -> None:
    service, repository, _catalog, writer = _service()
    approval_id = _submit(service)

    service.decide_request(
        actor_context=_actor("owner-1", {"DATA_OWNER"}),
        approval_request_id=approval_id,
        decision="APPROVE",
        reason_code="SCHEDULE.OUT_OF_BAND.VERIFIED",
    )
    applied = service.apply_request(
        actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
        approval_request_id=approval_id,
    )
    assert applied.status is GovernanceApprovalStatus.APPLIED
    assert len(writer.calls) == 1

    replayed = service.apply_request(
        actor_context=_actor("applier-1", {"DATA_GOVERNANCE_SPECIALIST"}),
        approval_request_id=approval_id,
    )
    assert replayed.status is GovernanceApprovalStatus.APPLIED
    assert len(writer.calls) == 1
    assert repository.requests[approval_id].status is GovernanceApprovalStatus.APPLIED


def test_nature_change_invalidates_pending_schedule_request() -> None:
    service, repository, catalog, _writer = _service()
    approval_id = _submit(service)

    dataset = catalog.datasets[DATASET_ID]
    catalog.datasets[DATASET_ID] = replace(
        dataset, timeliness_nature=TimelinessNature.BATCH_TIME, version=dataset.version + 1
    )

    with pytest.raises(GovernanceConflictError, match="invalidated"):
        service.decide_request(
            actor_context=_actor("owner-1", {"DATA_OWNER"}),
            approval_request_id=approval_id,
            decision="APPROVE",
            reason_code="SCHEDULE.OUT_OF_BAND.VERIFIED",
        )
    assert repository.requests[approval_id].status is GovernanceApprovalStatus.INVALIDATED
