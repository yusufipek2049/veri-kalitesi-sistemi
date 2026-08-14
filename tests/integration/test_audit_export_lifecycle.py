from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from veri_kalitesi.api import DevelopmentActorContextResolver, create_dashboard_api
from veri_kalitesi.audit.models import (
    AuditAccessPolicy,
    AuditEventInput,
    AuditFailureMode,
    AuditFailurePolicy,
    AuditResult,
)
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.audit.service import AuditQueryService, AuditService


def test_audit_export_download_is_followed_by_a_chained_completion_event() -> None:
    now = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
    repository = SQLiteAuditRepository()
    audit_service = AuditService(
        repository,
        AuditRedactor(build_default_redaction_policy()),
        AuditFailurePolicy(
            version="AUDIT_EXPORT_LIFECYCLE_FAILURE_V1",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )
    audit_service.append(
        AuditEventInput(
            actor_id="rule-owner",
            actor_type="USER",
            correlation_id="rule-lifecycle",
            action="RULE_ACTIVATION",
            object_type="QualityRule",
            object_id="rule-lifecycle-1",
            result=AuditResult.SUCCESS,
            reason_code="APPROVED",
            old_values={},
            new_values={},
            occurred_at=now - timedelta(hours=1),
        )
    )
    resolver = DevelopmentActorContextResolver(
        runtime_environment="development",
        policy_version="AUDIT_EXPORT_LIFECYCLE_CONTEXT_V1",
        permitted_source_ids=frozenset(),
        can_view_enterprise=False,
        roles=frozenset({"AUDIT_VIEWER"}),
        clock=lambda: now,
    )
    app = create_dashboard_api(
        actor_context_resolver=resolver,
        audit_query_service=AuditQueryService(
            repository,
            audit_service,
            AuditAccessPolicy(
                version="AUDIT_EXPORT_LIFECYCLE_ACCESS_V1",
                context_policy_version="AUDIT_EXPORT_LIFECYCLE_CONTEXT_V1",
            ),
            clock=lambda: now,
        ),
        clock=lambda: now,
    )

    export_response = TestClient(app).get(
        "/api/v1/audit/events/export",
        params={"format": "csv", "action": "RULE_ACTIVATION"},
    )

    assert export_response.status_code == 200
    assert "RULE_ACTIVATION" in export_response.text
    assert "must-not-leak" not in export_response.text
    events = repository.list_events()
    assert [event.action for event in events] == [
        "RULE_ACTIVATION",
        "AUDIT_EXPORT_COMPLETED",
    ]
    assert events[-1].previous_event_hash == events[0].event_hash
