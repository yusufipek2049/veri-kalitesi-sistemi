"""Geliştirme ortamı kural (rule) bellek içi deposu ve okuyucusu."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from veri_kalitesi.api.development_fixtures import DEVELOPMENT_RULES
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.rules import (
    QualityDimension,
    QualityRule,
    RuleCriticality,
    RuleStatus,
    RuleType,
    RuleValidationError,
    RuleVersion,
)


class DevelopmentRuleReader:
    def __init__(self) -> None:
        self._rules: dict[str, tuple[QualityRule, RuleVersion]] = {
            rule.quality_rule_id: (rule, version) for rule, version in DEVELOPMENT_RULES
        }

    def list_rules_with_latest_version(
        self, allowed_dataset_ids: frozenset[str]
    ) -> list[tuple[QualityRule, RuleVersion]]:
        return sorted(
            (item for item in self._rules.values() if item[0].dataset_id in allowed_dataset_ids),
            key=lambda item: (item[0].code.casefold(), item[0].quality_rule_id),
        )

    def get_rule(self, quality_rule_id: str) -> QualityRule:
        entry = self._rules.get(quality_rule_id)
        if entry is None:
            raise KeyError(f"Rule not found: {quality_rule_id}")
        return entry[0]

    def get_version(self, rule_version_id: str) -> RuleVersion:
        for _rule, version in self._rules.values():
            if version.rule_version_id == rule_version_id:
                return version
        raise KeyError(f"Rule version not found: {rule_version_id}")

    def list_versions(self, quality_rule_id: str) -> list[RuleVersion]:
        entry = self._rules.get(quality_rule_id)
        if entry is None:
            return []
        return [entry[1]]


class DevelopmentRuleStore:
    def __init__(self) -> None:
        self._rules: dict[str, tuple[QualityRule, RuleVersion]] = {
            rule.quality_rule_id: (rule, version) for rule, version in DEVELOPMENT_RULES
        }
        self._lock = RLock()

    def create_rule(
        self,
        *,
        actor_id: str,
        code: str,
        name: str,
        dataset_id: str,
        rule_type: str,
        primary_dimension: str,
        threshold: float,
        weight: float,
        criticality: str,
        owner_user_id: str,
        parameters: dict,
        correlation_id: str | None = None,
        actor_context: ActorContext | None = None,
    ) -> tuple[QualityRule, RuleVersion]:
        if actor_context is None:
            raise RuleValidationError("Development actor is required.")
        with self._lock:
            quality_rule_id = f"rule-{uuid4().hex[:12]}"
            rule_version_id = f"rule-version-{uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)
            rule = QualityRule(
                quality_rule_id=quality_rule_id,
                code=code,
                name=name,
                dataset_id=dataset_id,
                field_ids=(),
                primary_dimension=QualityDimension(primary_dimension),
                owner_user_id=owner_user_id,
                status=RuleStatus.DRAFT,
            )
            version = RuleVersion(
                rule_version_id=rule_version_id,
                quality_rule_id=quality_rule_id,
                version_no=1,
                rule_type=RuleType(rule_type),
                definition=parameters,
                threshold=threshold,
                weight=weight,
                criticality=RuleCriticality(criticality),
                prepared_by_actor_id=actor_id,
                created_at=now,
            )
            self._rules[quality_rule_id] = (rule, version)
            return rule, version
