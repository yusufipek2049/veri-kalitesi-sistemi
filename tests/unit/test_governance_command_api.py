"""Yönetişim komut endpoint'leri HTTP testleri.

Maker → checker → applier akışını, CSRF korumasını, kapsam filtrelemesini
ve merkezi listede DATA_OWNERSHIP projeksiyonunu doğrular.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.api.bff import CSRF_HEADER_NAME
from veri_kalitesi.api.errors import ApiCsrfError
from veri_kalitesi.api.identity import DevelopmentUser, DevelopmentUserRegistry
from veri_kalitesi.api.service_groups import ActorResolverIdentity, ApiOptions, GovernanceServices
from veri_kalitesi.audit.models import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactionPolicy,
)
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.audit.service import AuditService
from veri_kalitesi.data_sources.errors import ConflictError
from veri_kalitesi.data_sources.models import DataField, Dataset
from veri_kalitesi.governance import (
    GovernanceApprovalCommandService,
    GovernanceApprovalPolicy,
    GovernanceApprovalQueryService,
)
from veri_kalitesi.identity import (
    ActorContext,
    DashboardAuthorizationPolicy,
    PolicyAuthorizationService,
)

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
ACTOR_POLICY_VERSION = "GOVERNANCE_CMD_API_POLICY_V1"
DATASET_ID = "dataset-gov"
FIELD_ID = "field-gov"

CSRF_PROOF = "test-csrf-proof"


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

    def transition(
        self, request, *, expected_version, expected_status, audit_event, audit_outbox
    ):
        stored = self.requests[request.approval_request_id]
        updated = replace(stored, status=request.status, version=expected_version + 1,
                         checker_actor_id=request.checker_actor_id,
                         checker_role=request.checker_role,
                         reason_code=request.reason_code,
                         decided_at=request.decided_at,
                         applied_at=request.applied_at)
        self.requests[request.approval_request_id] = updated
        return updated

    def list_for_scope(self, *, dataset_ids, source_ids):
        return [
            request
            for request in self.requests.values()
            if request.scope_type == "DATASET" and request.scope_id in dataset_ids
        ]


class FakeCatalog:
    def __init__(self) -> None:
        self.datasets = {
            DATASET_ID: Dataset(
                data_source_id="source-1",
                namespace="core",
                name="Governance tablosu",
                owner_user_id="current-owner",
                dataset_id=DATASET_ID,
                version=2,
            )
        }
        self.fields = {
            FIELD_ID: DataField(
                dataset_id=DATASET_ID,
                name="tc_kimlik_no",
                native_data_type="varchar(11)",
                is_sensitive=False,
                data_field_id=FIELD_ID,
                version=1,
            )
        }

    def get_dataset(self, dataset_id: str) -> Dataset:
        return self.datasets[dataset_id]

    def get_data_field(self, field_id: str) -> DataField:
        return self.fields[field_id]


class FakeOwnershipWriter:
    def __init__(self, catalog: FakeCatalog) -> None:
        self.catalog = catalog

    def apply_dataset_owner(self, *, dataset_id, owner_user_id, expected_version) -> Dataset:
        dataset = self.catalog.datasets[dataset_id]
        if dataset.version != expected_version:
            raise ConflictError("version mismatch")
        updated = replace(dataset, owner_user_id=owner_user_id, version=dataset.version + 1)
        self.catalog.datasets[dataset_id] = updated
        return updated


class FakeMetadataWriter:
    def __init__(self, catalog: FakeCatalog) -> None:
        self.catalog = catalog

    def apply_dataset_metadata(self, *, dataset_id, updates, expected_version) -> Dataset:
        dataset = self.catalog.datasets[dataset_id]
        if dataset.version != expected_version:
            raise ConflictError("version mismatch")
        updated = replace(dataset, version=dataset.version + 1, **updates)
        self.catalog.datasets[dataset_id] = updated
        return updated

    def apply_field_sensitivity(self, *, field_id, updates, expected_version) -> DataField:
        data_field = self.catalog.fields[field_id]
        if data_field.version != expected_version:
            raise ConflictError("version mismatch")
        updated = replace(data_field, version=data_field.version + 1, **updates)
        self.catalog.fields[field_id] = updated
        return updated


class _GovernanceResolver(DevelopmentActorContextResolver):
    """CSRF kanıtını basitleştirilmiş biçimde denetleyen test resolver'ı."""

    def protect_state_changing(self, request) -> ActorContext:  # type: ignore[no-untyped-def]
        if request.headers.get(CSRF_HEADER_NAME) != CSRF_PROOF:
            raise ApiCsrfError("rejected", request.state.correlation_id)
        return self.resolve(request)


def _policy() -> GovernanceApprovalPolicy:
    return GovernanceApprovalPolicy(
        version="GOVERNANCE_APPROVAL_POLICY_V1",
        actor_policy_version=ACTOR_POLICY_VERSION,
        maker_roles=frozenset({"DATA_STEWARD"}),
        checker_roles=frozenset({"DATA_OWNER"}),
        applier_roles=frozenset({"DATA_GOVERNANCE_SPECIALIST"}),
    )


def _app():
    registry = DevelopmentUserRegistry(
        [
            DevelopmentUser(
                user_id="maker-user",
                display_name="Veri Uzmanı",
                roles=frozenset({"DATA_STEWARD"}),
                permitted_source_ids=frozenset(),
                permitted_dataset_ids=frozenset({DATASET_ID}),
            ),
            DevelopmentUser(
                user_id="owner-user",
                display_name="Tablo Sahibi",
                roles=frozenset({"DATA_OWNER"}),
                permitted_source_ids=frozenset(),
                permitted_dataset_ids=frozenset({DATASET_ID}),
            ),
            DevelopmentUser(
                user_id="applier-user",
                display_name="Uygulayıcı",
                roles=frozenset({"DATA_GOVERNANCE_SPECIALIST"}),
                permitted_source_ids=frozenset(),
                permitted_dataset_ids=frozenset({DATASET_ID}),
            ),
            DevelopmentUser(
                user_id="outsider-owner",
                display_name="Kapsam Dışı Sahip",
                roles=frozenset({"DATA_OWNER"}),
                permitted_source_ids=frozenset(),
                permitted_dataset_ids=frozenset({"dataset-other"}),
            ),
        ]
    )
    resolver = _GovernanceResolver(
        runtime_environment="development",
        policy_version=ACTOR_POLICY_VERSION,
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=False,
        user_registry=registry,
        clock=lambda: NOW,
    )
    audit_service = AuditService(
        SQLiteAuditRepository(),
        AuditRedactor(
            AuditRedactionPolicy(
                version="GOVERNANCE_CMD_REDACTION_V1",
                allowed_fields_by_action={
                    "DASHBOARD_SCOPE_AUTHORIZATION": frozenset(
                        {
                            "policy_version",
                            "permitted_source_count",
                            "can_view_enterprise",
                            "reason_code",
                        }
                    )
                },
            )
        ),
        AuditFailurePolicy("GOVERNANCE_CMD_AUDIT_V1", AuditFailureMode.FAIL_CLOSED),
    )
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=ACTOR_POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )
    repository = FakeGovernanceRepository()
    catalog = FakeCatalog()
    command_service = GovernanceApprovalCommandService(
        repository,
        catalog,
        FakeOwnershipWriter(catalog),
        audit_sink=FakeAuditSink(),
        transactional_audit=FakeTransactionalAudit(),
        policy=_policy(),
        metadata_writer=FakeMetadataWriter(catalog),
        clock=lambda: NOW,
    )
    query_service = GovernanceApprovalQueryService(
        None,
        None,
        authorization,
        center_reader=repository,
        center_policy=_policy(),
    )
    app = create_dashboard_api(
        identity=ActorResolverIdentity(resolver),
        options=ApiOptions(data_origin="synthetic-test"),
        governance=GovernanceServices(query=query_service, command=command_service),
    )
    return TestClient(app), repository, catalog


def _headers(user_id: str) -> dict[str, str]:
    return {CSRF_HEADER_NAME: CSRF_PROOF, "X-Development-User-Id": user_id}


def _submit(client: TestClient) -> str:
    response = client.post(
        "/api/v1/governance/approval-requests",
        json={
            "request_type": "DATASET_OWNER_CHANGE",
            "object_id": DATASET_ID,
            "new_owner_user_id": "new-owner",
            "reason_code": "OWNERSHIP.TRANSFER",
        },
        headers=_headers("maker-user"),
    )
    assert response.status_code == 201, response.text
    return response.json()["item"]["approval_request_id"]


def test_full_maker_checker_apply_flow_over_http() -> None:
    client, repository, catalog = _app()

    approval_id = _submit(client)

    # Maker karar veremez → 403
    denied = client.post(
        f"/api/v1/governance/approval-requests/{approval_id}/decision",
        json={"decision": "APPROVE", "reason_code": "OWNERSHIP.VERIFIED"},
        headers=_headers("maker-user"),
    )
    assert denied.status_code == 403

    # Kapsam dışı owner karar veremez → 403
    outsider = client.post(
        f"/api/v1/governance/approval-requests/{approval_id}/decision",
        json={"decision": "APPROVE", "reason_code": "OWNERSHIP.VERIFIED"},
        headers=_headers("outsider-owner"),
    )
    assert outsider.status_code == 403

    # Yetkili owner onaylar
    decided = client.post(
        f"/api/v1/governance/approval-requests/{approval_id}/decision",
        json={"decision": "APPROVE", "reason_code": "OWNERSHIP.VERIFIED"},
        headers=_headers("owner-user"),
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["item"]["status"] == "APPROVED"

    # Onaylanan karar uygulanır ve dataset sahibi değişir
    applied = client.post(
        f"/api/v1/governance/approval-requests/{approval_id}/apply",
        headers=_headers("applier-user"),
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["item"]["status"] == "APPLIED"
    assert catalog.datasets[DATASET_ID].owner_user_id == "new-owner"


def test_csrf_proof_is_required_for_governance_mutations() -> None:
    client, _repository, _catalog = _app()

    response = client.post(
        "/api/v1/governance/approval-requests",
        json={
            "request_type": "DATASET_OWNER_CHANGE",
            "object_id": DATASET_ID,
            "new_owner_user_id": "new-owner",
            "reason_code": "OWNERSHIP.TRANSFER",
        },
        headers={"X-Development-User-Id": "maker-user"},
    )
    assert response.status_code == 403


def test_withdraw_flow_and_central_listing_actions() -> None:
    client, _repository, _catalog = _app()
    approval_id = _submit(client)

    # Checker bekleyen talebi merkezi listede DECIDE_APPROVAL ile görür
    checker_list = client.get(
        "/api/v1/governance/approval-requests",
        params={"view": "PENDING"},
        headers={"X-Development-User-Id": "owner-user"},
    )
    assert checker_list.status_code == 200
    checker_items = checker_list.json()["items"]
    assert len(checker_items) == 1
    assert checker_items[0]["domain"] == "DATA_OWNERSHIP"
    assert checker_items[0]["available_actions"] == ["DECIDE_APPROVAL"]

    # Maker aynı talebi Gönderdiklerim'de WITHDRAW_APPROVAL ile görür
    maker_list = client.get(
        "/api/v1/governance/approval-requests",
        params={"view": "MINE"},
        headers={"X-Development-User-Id": "maker-user"},
    )
    assert maker_list.status_code == 200
    maker_items = maker_list.json()["items"]
    assert len(maker_items) == 1
    assert maker_items[0]["available_actions"] == ["WITHDRAW_APPROVAL"]

    # Owner geri çekemez
    denied = client.post(
        f"/api/v1/governance/approval-requests/{approval_id}/withdraw",
        json={"reason_code": "MAKER.WITHDRAWAL"},
        headers=_headers("owner-user"),
    )
    assert denied.status_code == 403

    withdrawn = client.post(
        f"/api/v1/governance/approval-requests/{approval_id}/withdraw",
        json={"reason_code": "MAKER.WITHDRAWAL"},
        headers=_headers("maker-user"),
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["item"]["status"] == "WITHDRAWN"


def test_detail_is_scope_filtered() -> None:
    client, _repository, _catalog = _app()
    approval_id = _submit(client)

    in_scope = client.get(
        f"/api/v1/governance/approval-requests/{approval_id}",
        headers={"X-Development-User-Id": "owner-user"},
    )
    assert in_scope.status_code == 200
    assert in_scope.json()["item"]["approval_request_id"] == approval_id
    assert in_scope.json()["item"]["change_summary"]["after"] == {
        "owner_user_id": "new-owner"
    }

    out_of_scope = client.get(
        f"/api/v1/governance/approval-requests/{approval_id}",
        headers={"X-Development-User-Id": "outsider-owner"},
    )
    assert out_of_scope.status_code == 404


def test_invalid_payloads_are_rejected() -> None:
    client, _repository, _catalog = _app()

    bad_reason = client.post(
        "/api/v1/governance/approval-requests",
        json={
            "request_type": "DATASET_OWNER_CHANGE",
            "object_id": DATASET_ID,
            "new_owner_user_id": "new-owner",
            "reason_code": "NOT.IN.DICTIONARY",
        },
        headers=_headers("maker-user"),
    )
    assert bad_reason.status_code == 422

    missing_dataset = client.post(
        "/api/v1/governance/approval-requests",
        json={
            "request_type": "DATASET_OWNER_CHANGE",
            "object_id": "dataset-missing",
            "new_owner_user_id": "new-owner",
            "reason_code": "OWNERSHIP.TRANSFER",
        },
        headers=_headers("maker-user"),
    )
    assert missing_dataset.status_code == 404


def test_metadata_critical_change_flow_over_http() -> None:
    client, _repository, catalog = _app()

    created = client.post(
        "/api/v1/governance/approval-requests",
        json={
            "request_type": "METADATA_CRITICAL_CHANGE",
            "object_id": DATASET_ID,
            "reason_code": "METADATA.CRITICALITY.CHANGE",
            "proposed_changes": {"criticality": "CRITICAL"},
        },
        headers=_headers("maker-user"),
    )
    assert created.status_code == 201, created.text
    item = created.json()["item"]
    approval_id = item["approval_request_id"]
    assert item["domain"] == "METADATA_AND_CLASSIFICATION"
    assert item["change_summary"]["after"] == {"criticality": "CRITICAL"}

    decided = client.post(
        f"/api/v1/governance/approval-requests/{approval_id}/decision",
        json={"decision": "APPROVE", "reason_code": "METADATA.VERIFIED"},
        headers=_headers("owner-user"),
    )
    assert decided.status_code == 200, decided.text

    applied = client.post(
        f"/api/v1/governance/approval-requests/{approval_id}/apply",
        headers=_headers("applier-user"),
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["item"]["status"] == "APPLIED"
    assert catalog.datasets[DATASET_ID].criticality == "CRITICAL"


def test_field_sensitivity_mark_flow_over_http() -> None:
    client, _repository, catalog = _app()

    created = client.post(
        "/api/v1/governance/approval-requests",
        json={
            "request_type": "FIELD_SENSITIVITY_MARK",
            "object_id": FIELD_ID,
            "reason_code": "METADATA.SENSITIVITY.MARK",
            "proposed_changes": {"is_sensitive": True, "classification": "PERSONAL_DATA"},
        },
        headers=_headers("maker-user"),
    )
    assert created.status_code == 201, created.text
    item = created.json()["item"]
    approval_id = item["approval_request_id"]
    assert item["object_type"] == "DataField"
    assert item["scope_type"] == "DATASET"
    assert item["scope_id"] == DATASET_ID

    decided = client.post(
        f"/api/v1/governance/approval-requests/{approval_id}/decision",
        json={"decision": "APPROVE", "reason_code": "METADATA.VERIFIED"},
        headers=_headers("owner-user"),
    )
    assert decided.status_code == 200, decided.text

    applied = client.post(
        f"/api/v1/governance/approval-requests/{approval_id}/apply",
        headers=_headers("applier-user"),
    )
    assert applied.status_code == 200, applied.text
    assert catalog.fields[FIELD_ID].is_sensitive is True
    assert catalog.fields[FIELD_ID].classification == "PERSONAL_DATA"


def test_metadata_submission_rejects_invalid_proposed_changes() -> None:
    client, _repository, _catalog = _app()

    non_governed = client.post(
        "/api/v1/governance/approval-requests",
        json={
            "request_type": "METADATA_CRITICAL_CHANGE",
            "object_id": DATASET_ID,
            "reason_code": "METADATA.CRITICALITY.CHANGE",
            "proposed_changes": {"name": "yeni-ad"},
        },
        headers=_headers("maker-user"),
    )
    assert non_governed.status_code == 422

    empty_changes = client.post(
        "/api/v1/governance/approval-requests",
        json={
            "request_type": "METADATA_CRITICAL_CHANGE",
            "object_id": DATASET_ID,
            "reason_code": "METADATA.CRITICALITY.CHANGE",
        },
        headers=_headers("maker-user"),
    )
    assert empty_changes.status_code == 422
