"""BE-04: Salt okunur ihlal inceleme kaniti birim testleri.

AC-01: Tam kanit tek yanitta
AC-02: Maskeli ornekler bounded ve veri-minimum formatinda
AC-03: Her bilesen kaynak siniflandirmasi tasir
AC-04: Kaniti olmayan bilesen Unknown (fail-closed)
AC-05: Yetkisiz kapsam veri sizdirmayan hata
AC-06: Benzer gecmis deterministik (Unknown)
AC-07: Kural surumu, politika surumu ve kanit referanslari
AC-08: Bounded ornek
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from veri_kalitesi.api import (
    DevelopmentActorContextResolver,
    create_dashboard_api,
)
from veri_kalitesi.audit.models import (
    AuditFailureMode,
    AuditFailurePolicy,
    AuditRedactionPolicy,
)
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.audit.service import AuditService
from veri_kalitesi.dashboard import DashboardQueryService
from veri_kalitesi.identity import (
    ActorContext,
    ActorContextIssuer,
    ActorType,
    DashboardAuthorizationPolicy,
    PolicyAuthorizationService,
)
from veri_kalitesi.issues import (
    DataQualityIssue,
    IssueEvidencePayload,
    IssueInvestigationEvidenceService,
    IssuePriority,
    IssueScopeType,
    IssueSourceEventType,
    IssueStatus,
    IssueTriggerType,
)
from veri_kalitesi.scoring.repository import SQLiteScoreRepository

NOW = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "INVESTIGATION_EVIDENCE_TEST_V1"

SHA256_FINGERPRINT = "sha256:" + "a" * 64
MASKED_SAMPLE = (
    "hmac-sha256:key-id/abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
)


def _issue(
    issue_id: str,
    scope_type: IssueScopeType,
    scope_id: str,
) -> DataQualityIssue:
    return DataQualityIssue(
        issue_id=issue_id,
        issue_no=f"DQI-{issue_id}",
        source_event_id="source-event-001",
        source_event_type=IssueSourceEventType.QUALITY,
        trigger_type=IssueTriggerType.QUALITY_THRESHOLD,
        scope_type=scope_type,
        scope_id=scope_id,
        status=IssueStatus.INVESTIGATING,
        priority=IssuePriority.HIGH,
        assignee_user_id="assignee-001",
        deduplication_key_digest="sha256:dedup",
        occurrence_count=1,
        created_at=NOW,
        updated_at=NOW,
        last_seen_at=NOW,
    )


class FakeIssueInvestigationReader:
    def __init__(self, issues: dict[str, DataQualityIssue]) -> None:
        self._issues = issues

    def get(self, issue_id: str) -> DataQualityIssue:
        from veri_kalitesi.issues.errors import IssueNotFoundError

        if issue_id not in self._issues:
            raise IssueNotFoundError(f"Issue {issue_id} not found.")
        return self._issues[issue_id]


class FakeEvidenceProvider:
    def __init__(
        self,
        payload: IssueEvidencePayload | None = None,
    ) -> None:
        self._payload = payload
        self.calls: list[tuple[str, IssueScopeType, str]] = []

    def get_evidence_for_issue(
        self,
        issue_id: str,
        scope_type: IssueScopeType,
        scope_id: str,
    ) -> IssueEvidencePayload | None:
        self.calls.append((issue_id, scope_type, scope_id))
        return self._payload


class FakeAuthorizationService:
    def __init__(
        self,
        *,
        source_ids: frozenset[str] = frozenset(),
        dataset_ids: frozenset[str] = frozenset(),
    ) -> None:
        self._source_ids = source_ids
        self._dataset_ids = dataset_ids

    def authorize_dashboard(self, context: ActorContext | None):
        from veri_kalitesi.identity import DashboardAuthorizationDecision

        if context is None:
            return DashboardAuthorizationDecision(
                permitted_source_ids=frozenset(),
                permitted_dataset_ids=frozenset(),
                can_view_enterprise=False,
                policy_version=POLICY_VERSION,
            )
        return DashboardAuthorizationDecision(
            permitted_source_ids=self._source_ids & context.permitted_source_ids,
            permitted_dataset_ids=self._dataset_ids & context.permitted_dataset_ids,
            can_view_enterprise=context.can_view_enterprise,
            policy_version=POLICY_VERSION,
        )


def _actor_context(
    *,
    source_ids: frozenset[str] = frozenset({"source-a"}),
    dataset_ids: frozenset[str] = frozenset({"dataset-a"}),
) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id="actor-investigator",
        actor_type=ActorType.USER,
        authentication_source="test-idp",
        session_id="test-session",
        roles=frozenset({"DATA_STEWARD"}),
        permitted_source_ids=source_ids,
        permitted_dataset_ids=dataset_ids,
        can_view_enterprise=False,
        privileged=False,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
        policy_version=POLICY_VERSION,
        correlation_id="investigation-evidence-test",
    )


def _evidence_payload() -> IssueEvidencePayload:
    return IssueEvidencePayload(
        rule_version_id="rule-version-001",
        rule_description="Kolon NULL olmamali: musteri_id",
        ir_version="DQ_RULE_IR_V1",
        expected_summary={"failed_count": 0},
        actual_summary={"failed_count": 5},
        masked_samples=[MASKED_SAMPLE],
        fingerprint=SHA256_FINGERPRINT,
        query_reference="query-template://version-001",
        plan_reference="plan://version-001",
    )


def _app(
    reader: FakeIssueInvestigationReader,
    provider: FakeEvidenceProvider,
    auth_service: FakeAuthorizationService,
) -> TestClient:
    service = IssueInvestigationEvidenceService(
        reader=reader,
        authorization_service=auth_service,
        evidence_provider=provider,
    )
    audit_service = AuditService(
        SQLiteAuditRepository(),
        AuditRedactor(
            AuditRedactionPolicy(
                version="INVESTIGATION_EVIDENCE_REDACTION_V1",
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
        AuditFailurePolicy("INVESTIGATION_EVIDENCE_AUDIT_V1", AuditFailureMode.FAIL_CLOSED),
    )
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=POLICY_VERSION,
        permitted_source_ids=frozenset({"source-a"}),
        permitted_dataset_ids=frozenset({"dataset-a"}),
        can_view_enterprise=False,
        clock=lambda: NOW,
    )
    DashboardQueryService(
        SQLiteScoreRepository(),
        authorization,
        clock=lambda: NOW,
    )
    return TestClient(
        create_dashboard_api(
            actor_context_resolver=resolver,
            issue_investigation_evidence_service=service,
            data_origin="synthetic-test",
        )
    )


# AC-01: Tam kanit tek yanitta
def test_ac_01_full_evidence_returns_all_components() -> None:
    issue = _issue("issue-001", IssueScopeType.DATASET, "dataset-a")
    reader = FakeIssueInvestigationReader({"issue-001": issue})
    provider = FakeEvidenceProvider(_evidence_payload())
    auth = FakeAuthorizationService(dataset_ids=frozenset({"dataset-a"}))
    client = _app(reader, provider, auth)

    response = client.get("/api/v1/issues/issue-001/investigation/evidence")

    assert response.status_code == 200
    body = response.json()
    assert body["issue_id"] == "issue-001"
    # AC-03: Kaynak siniflandirmasi
    assert body["rule_description"]["source"] == "Observed"
    assert body["expected_summary"]["source"] == "Observed"
    assert body["actual_summary"]["source"] == "Observed"
    assert body["masked_samples"]["source"] == "Observed"
    # AC-04: Benzer gecmis ve oneri Unknown
    assert body["similar_history"]["source"] == "Unknown"
    assert body["recommendation"]["source"] == "Unknown"
    # AC-07: Kural surumu ve kanit referanslari
    assert body["rule_version_id"] == "rule-version-001"
    assert body["ir_version"] == "DQ_RULE_IR_V1"
    assert body["evidence_fingerprint"] == SHA256_FINGERPRINT
    assert body["evidence_query_reference"] == "query-template://version-001"
    assert body["evidence_plan_reference"] == "plan://version-001"
    assert body["authorization_policy_version"] == POLICY_VERSION


# AC-02: Maskeli ornekler bounded
def test_ac_02_masked_samples_bounded_to_ten() -> None:
    issue = _issue("issue-002", IssueScopeType.DATASET, "dataset-a")
    reader = FakeIssueInvestigationReader({"issue-002": issue})
    # 15 ornek sagla
    many_samples = IssueEvidencePayload(
        rule_version_id="rule-version-001",
        rule_description="Test kurali",
        ir_version="DQ_RULE_IR_V1",
        expected_summary={"failed_count": 0},
        actual_summary={"failed_count": 15},
        masked_samples=[MASKED_SAMPLE] * 15,
        fingerprint=SHA256_FINGERPRINT,
        query_reference="query-template://version-001",
        plan_reference="plan://version-001",
    )
    provider = FakeEvidenceProvider(many_samples)
    auth = FakeAuthorizationService(dataset_ids=frozenset({"dataset-a"}))
    client = _app(reader, provider, auth)

    response = client.get("/api/v1/issues/issue-002/investigation/evidence")

    assert response.status_code == 200
    samples = response.json()["masked_samples"]["value"]
    assert len(samples) == 10  # Bounded to 10


# AC-04: Kaniti olmayan bilesen Unknown (fail-closed)
def test_ac_04_no_evidence_returns_unknown() -> None:
    issue = _issue("issue-003", IssueScopeType.DATASET, "dataset-a")
    reader = FakeIssueInvestigationReader({"issue-003": issue})
    provider = FakeEvidenceProvider(payload=None)  # Kanit yok
    auth = FakeAuthorizationService(dataset_ids=frozenset({"dataset-a"}))
    client = _app(reader, provider, auth)

    response = client.get("/api/v1/issues/issue-003/investigation/evidence")

    assert response.status_code == 200
    body = response.json()
    # Tum bilesenler Unknown
    assert body["rule_description"]["source"] == "Unknown"
    assert body["expected_summary"]["source"] == "Unknown"
    assert body["actual_summary"]["source"] == "Unknown"
    assert body["masked_samples"]["source"] == "Unknown"
    assert body["similar_history"]["source"] == "Unknown"
    assert body["recommendation"]["source"] == "Unknown"
    # Referanslar None
    assert body["rule_version_id"] is None
    assert body["evidence_fingerprint"] is None


# AC-05: Yetkisiz kapsam veri sizdirmayan hata
def test_ac_05_unauthorized_scope_returns_404() -> None:
    issue = _issue("issue-004", IssueScopeType.DATASET, "dataset-secret")
    reader = FakeIssueInvestigationReader({"issue-004": issue})
    provider = FakeEvidenceProvider(_evidence_payload())
    # Yetkili sadece dataset-a, dataset-secret degil
    auth = FakeAuthorizationService(dataset_ids=frozenset({"dataset-a"}))
    client = _app(reader, provider, auth)

    response = client.get("/api/v1/issues/issue-004/investigation/evidence")

    assert response.status_code == 404
    # Veri sizdirmama: yanitta kanit detayi yok (Observed/Unknown degerleri yok)
    body = response.json()
    assert "rule_description" not in body
    assert "masked_samples" not in body


# AC-05: Yetkisiz erisim (null context)
def test_ac_05_null_actor_context_returns_empty_scope() -> None:
    issue = _issue("issue-005", IssueScopeType.DATASET, "dataset-a")
    reader = FakeIssueInvestigationReader({"issue-005": issue})
    provider = FakeEvidenceProvider(_evidence_payload())
    auth = FakeAuthorizationService(dataset_ids=frozenset())  # Bos yetki
    client = _app(reader, provider, auth)

    response = client.get("/api/v1/issues/issue-005/investigation/evidence")

    assert response.status_code == 404


# AC-05: Source scope yetki kontrolu
def test_ac_05_source_scope_authorization() -> None:
    issue = _issue("issue-006", IssueScopeType.SOURCE, "source-a")
    reader = FakeIssueInvestigationReader({"issue-006": issue})
    provider = FakeEvidenceProvider(_evidence_payload())
    auth = FakeAuthorizationService(source_ids=frozenset({"source-a"}))
    client = _app(reader, provider, auth)

    response = client.get("/api/v1/issues/issue-006/investigation/evidence")

    assert response.status_code == 200
    assert response.json()["issue_id"] == "issue-006"


# AC-07: Cache-Control no-store
def test_ac_07_cache_control_no_store() -> None:
    issue = _issue("issue-007", IssueScopeType.DATASET, "dataset-a")
    reader = FakeIssueInvestigationReader({"issue-007": issue})
    provider = FakeEvidenceProvider(_evidence_payload())
    auth = FakeAuthorizationService(dataset_ids=frozenset({"dataset-a"}))
    client = _app(reader, provider, auth)

    response = client.get("/api/v1/issues/issue-007/investigation/evidence")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"


# AC-01: Yazma yan etkisi yok
def test_ac_01_no_write_side_effects() -> None:
    issue = _issue("issue-008", IssueScopeType.DATASET, "dataset-a")
    reader = FakeIssueInvestigationReader({"issue-008": issue})
    provider = FakeEvidenceProvider(_evidence_payload())
    auth = FakeAuthorizationService(dataset_ids=frozenset({"dataset-a"}))
    client = _app(reader, provider, auth)

    # GET endpoint - yazma yan etkisi olmamali
    response1 = client.get("/api/v1/issues/issue-008/investigation/evidence")
    response2 = client.get("/api/v1/issues/issue-008/investigation/evidence")

    assert response1.status_code == 200
    assert response2.status_code == 200
    # Ayni kanit verilerini dondurmeli (correlation_id haric)
    body1 = response1.json()
    body2 = response2.json()
    assert body1["issue_id"] == body2["issue_id"]
    assert body1["rule_description"] == body2["rule_description"]
    assert body1["masked_samples"] == body2["masked_samples"]
    assert body1["evidence_fingerprint"] == body2["evidence_fingerprint"]


# AC-08: Evidence provider cagrildi
def test_ac_08_evidence_provider_called_with_correct_args() -> None:
    issue = _issue("issue-009", IssueScopeType.DATASET, "dataset-a")
    reader = FakeIssueInvestigationReader({"issue-009": issue})
    provider = FakeEvidenceProvider(_evidence_payload())
    auth = FakeAuthorizationService(dataset_ids=frozenset({"dataset-a"}))
    client = _app(reader, provider, auth)

    client.get("/api/v1/issues/issue-009/investigation/evidence")

    assert len(provider.calls) == 1
    assert provider.calls[0] == ("issue-009", IssueScopeType.DATASET, "dataset-a")


# Servis yoksa 503
def test_service_unavailable_returns_503() -> None:
    audit_service = AuditService(
        SQLiteAuditRepository(),
        AuditRedactor(
            AuditRedactionPolicy(
                version="INVESTIGATION_EVIDENCE_REDACTION_V1",
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
        AuditFailurePolicy("INVESTIGATION_EVIDENCE_AUDIT_V1", AuditFailureMode.FAIL_CLOSED),
    )
    authorization = PolicyAuthorizationService(
        DashboardAuthorizationPolicy(version=POLICY_VERSION),
        audit_service,
        clock=lambda: NOW,
    )
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version=POLICY_VERSION,
        permitted_source_ids=frozenset({"source-a"}),
        permitted_dataset_ids=frozenset({"dataset-a"}),
        can_view_enterprise=False,
        clock=lambda: NOW,
    )
    DashboardQueryService(
        SQLiteScoreRepository(),
        authorization,
        clock=lambda: NOW,
    )
    # issue_investigation_evidence_service=None (fail-closed)
    app = create_dashboard_api(
        actor_context_resolver=resolver,
        data_origin="synthetic-test",
    )
    client = TestClient(app)

    response = client.get("/api/v1/issues/any-issue/investigation/evidence")

    assert response.status_code == 503


# Issue bulunamadi
def test_issue_not_found_returns_404() -> None:
    reader = FakeIssueInvestigationReader({})  # Bos
    provider = FakeEvidenceProvider(_evidence_payload())
    auth = FakeAuthorizationService(dataset_ids=frozenset({"dataset-a"}))
    client = _app(reader, provider, auth)

    response = client.get("/api/v1/issues/nonexistent/investigation/evidence")

    assert response.status_code == 404
