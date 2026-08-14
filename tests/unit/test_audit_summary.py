from __future__ import annotations

from datetime import datetime, timedelta, timezone

from veri_kalitesi.audit.models import (
    AuditEventInput,
    AuditFailureMode,
    AuditFailurePolicy,
    AuditQuery,
    AuditResult,
)
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.audit.service import AuditService


NOW = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)


def test_query_summary_groups_results_actions_and_top_five_actors() -> None:
    repository = SQLiteAuditRepository()
    service = AuditService(
        repository,
        AuditRedactor(build_default_redaction_policy()),
        AuditFailurePolicy(
            version="AUDIT_SUMMARY_FAILURE_V1",
            default_mode=AuditFailureMode.FAIL_CLOSED,
        ),
    )
    events = (
        ("actor-a", "RULE_ACTIVATION", AuditResult.SUCCESS, 1),
        ("actor-a", "RULE_ACTIVATION", AuditResult.FAILURE, 2),
        ("actor-b", "LDAP_AUTHENTICATION", AuditResult.SUCCESS, 3),
        ("actor-c", "LDAP_AUTHENTICATION", AuditResult.DENIED, 4),
        ("actor-d", "IDENTITY_SESSION", AuditResult.SUCCESS, 5),
        ("actor-e", "IDENTITY_SESSION", AuditResult.SUCCESS, 6),
        ("actor-f", "IDENTITY_SESSION", AuditResult.SUCCESS, 7),
    )
    for actor_id, action, result, hours_ago in events:
        service.append(_event(actor_id, action, result, hours_ago))
    service.append(_event("actor-hidden", "RULE_ACTIVATION", AuditResult.FAILURE, 72))

    summary = repository.query_summary(
        AuditQuery(
            start_at=NOW - timedelta(days=1),
            end_at=NOW,
            reason_code="AUDIT_SUMMARY_TEST",
        )
    )

    assert summary.total_count == 7
    assert dict(summary.result_distribution) == {
        "SUCCESS": 5,
        "FAILURE": 1,
        "DENIED": 1,
    }
    assert dict(summary.action_distribution) == {
        "IDENTITY_SESSION": 3,
        "LDAP_AUTHENTICATION": 2,
        "RULE_ACTIVATION": 2,
    }
    assert [(actor.actor_id, actor.count) for actor in summary.top_actors] == [
        ("actor-a", 2),
        ("actor-b", 1),
        ("actor-c", 1),
        ("actor-d", 1),
        ("actor-e", 1),
    ]
    assert summary.period_start == NOW - timedelta(days=1)
    assert summary.period_end == NOW


def _event(
    actor_id: str,
    action: str,
    result: AuditResult,
    hours_ago: int,
) -> AuditEventInput:
    return AuditEventInput(
        actor_id=actor_id,
        actor_type="USER",
        correlation_id=f"correlation-{actor_id}-{hours_ago}",
        action=action,
        object_type="AuditTestObject",
        object_id=None,
        result=result,
        reason_code="SUMMARY_FIXTURE",
        old_values={},
        new_values={},
        occurred_at=NOW - timedelta(hours=hours_ago),
    )
