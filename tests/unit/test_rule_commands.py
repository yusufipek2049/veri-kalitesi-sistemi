"""DS-02 Faz A: RuleCommandAdapter sözleşme ve fail-closed testleri."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from veri_kalitesi.api.rule_commands import RuleCommandAdapter
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.rules import (
    QualityDimension,
    QualityRule,
    RuleApprovalRequest,
    RuleAuthorizationError,
    RuleCriticality,
    RuleStatus,
    RuleTestOptions,
    RuleTestResult,
    RuleTestStatus,
    RuleType,
    RuleVersion,
)

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
ACTOR_ID = "actor-ds02"
DATASET_ID = "dataset-ds02"


def test_ds02_ac_rule_actor_id_only_commands_fail_closed_without_context() -> None:
    service = _RuleServiceStub()
    adapter = RuleCommandAdapter(service)  # type: ignore[arg-type]

    with pytest.raises(RuleAuthorizationError):
        adapter.test_rule(
            actor_id=ACTOR_ID,
            rule_version_id=service.version.rule_version_id,
            options=RuleTestOptions(),
        )
    with pytest.raises(RuleAuthorizationError):
        adapter.activate_rule(
            actor_id=ACTOR_ID,
            quality_rule_id=service.rule.quality_rule_id,
        )

    assert service.calls == []


def test_ds02_ac_rule_adapter_handles_actor_id_and_context_signature_variants() -> None:
    service = _RuleServiceStub()
    adapter = RuleCommandAdapter(service)  # type: ignore[arg-type]
    context = _actor_context()

    result = adapter.test_rule(
        actor_id=ACTOR_ID,
        actor_context=context,
        rule_version_id=service.version.rule_version_id,
        options=RuleTestOptions(limit=100),
    )
    activated = adapter.activate_rule(
        actor_id=ACTOR_ID,
        actor_context=context,
        quality_rule_id=service.rule.quality_rule_id,
    )
    passivated = adapter.passivate_rule(
        actor_context=context,
        quality_rule_id=service.rule.quality_rule_id,
    )
    passivated_with_actor = adapter.passivate_rule(
        actor_id=ACTOR_ID,
        actor_context=context,
        quality_rule_id=service.rule.quality_rule_id,
    )

    assert result is service.test_result
    assert activated == (service.rule, service.version)
    assert passivated == (service.rule, service.version)
    assert passivated_with_actor == (service.rule, service.version)
    assert service.calls == ["test_rule", "activate_rule", "passivate_rule", "passivate_rule"]


def test_ds02_ac_rule_adapter_rejects_dataset_scope_escalation() -> None:
    service = _RuleServiceStub()
    adapter = RuleCommandAdapter(service)  # type: ignore[arg-type]

    with pytest.raises(RuleAuthorizationError):
        adapter.create_version(
            actor_id=ACTOR_ID,
            actor_context=_actor_context(dataset_ids=frozenset({"dataset-other"})),
            quality_rule_id=service.rule.quality_rule_id,
            parameters={},
            threshold=0.9,
            weight=1.0,
            criticality="HIGH",
        )

    assert service.calls == []


class _RuleRepositoryStub:
    def __init__(self, rule: QualityRule, version: RuleVersion) -> None:
        self.rule = rule
        self.version = version

    def get_rule(self, quality_rule_id: str) -> QualityRule:
        assert quality_rule_id == self.rule.quality_rule_id
        return self.rule

    def get_version(self, rule_version_id: str) -> RuleVersion:
        assert rule_version_id == self.version.rule_version_id
        return self.version

    def list_versions(self, quality_rule_id: str) -> list[RuleVersion]:
        assert quality_rule_id == self.rule.quality_rule_id
        return [self.version]


class _RuleServiceStub:
    def __init__(self) -> None:
        self.rule = QualityRule(
            quality_rule_id="rule-ds02",
            code="DS02_RULE",
            name="DS-02 rule",
            dataset_id=DATASET_ID,
            field_ids=(),
            primary_dimension=QualityDimension.COMPLETENESS,
            owner_user_id=ACTOR_ID,
            status=RuleStatus.DRAFT,
        )
        self.version = RuleVersion(
            rule_version_id="version-ds02",
            quality_rule_id=self.rule.quality_rule_id,
            version_no=1,
            rule_type=RuleType.REQUIRED,
            definition={"ir_version": "DQ_RULE_IR_V1"},
            threshold=0.9,
            weight=1.0,
            criticality=RuleCriticality.HIGH,
            prepared_by_actor_id=ACTOR_ID,
        )
        self.repository = _RuleRepositoryStub(self.rule, self.version)
        self.test_result = RuleTestResult(
            rule_version_id=self.version.rule_version_id,
            status=RuleTestStatus.SUCCESS,
            record_limit=100,
        )
        self.approval = RuleApprovalRequest(
            rule_version_id=self.version.rule_version_id,
            maker_actor_id=ACTOR_ID,
            policy_version="DS02_RULE_POLICY_V1",
        )
        self.calls: list[str] = []

    def test_rule(self, **values: Any) -> RuleTestResult:
        self.calls.append("test_rule")
        return self.test_result

    def activate_rule(self, **values: Any) -> QualityRule:
        self.calls.append("activate_rule")
        return self.rule

    def passivate_rule(self, **values: Any) -> QualityRule:
        self.calls.append("passivate_rule")
        return self.rule


def _actor_context(*, dataset_ids: frozenset[str] = frozenset({DATASET_ID})) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id=ACTOR_ID,
        actor_type=ActorType.USER,
        authentication_source="ds02-test",
        session_id="ds02-session",
        roles=frozenset({"DATA_STEWARD"}),
        permitted_source_ids=frozenset({"source-ds02"}),
        permitted_dataset_ids=dataset_ids,
        can_view_enterprise=False,
        privileged=False,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
        policy_version="DS02_ACTOR_POLICY_V1",
        correlation_id="ds02-rule-command-test",
    )
