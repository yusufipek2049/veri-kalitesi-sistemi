"""Rule domain servisini mevcut HTTP command portlarına uyarlayan ince katman."""

from __future__ import annotations

from typing import Any

from veri_kalitesi.identity import ActorContext
from veri_kalitesi.rules import (
    QualityRule,
    RuleAuthorizationError,
    RuleApprovalRequest,
    RuleService,
    RuleTestOptions,
    RuleTestResult,
    RuleValidationError,
    RuleVersion,
)


class RuleCommandAdapter:
    """HTTP dönüş şeklini üretir; domain state-machine kurallarını kopyalamaz.

    Faz A'da write endpoint'lerine bağlanmaz. Mevcut porttaki ``actor_id``-only
    test/activation imzalarını fail-closed karşılar; Faz B güvenilir
    ``ActorContext`` taşıdığında aynı adapter kullanılabilir.
    """

    def __init__(self, service: RuleService[Any]) -> None:
        self.service = service

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
        parameters: dict[str, Any],
        correlation_id: str | None = None,
        actor_context: ActorContext | None = None,
    ) -> tuple[QualityRule, RuleVersion]:
        self._require_dataset_actor(actor_id, actor_context, dataset_id)
        return self.service.create_rule(
            actor_id=actor_id,
            code=code,
            name=name,
            dataset_id=dataset_id,
            rule_type=rule_type,
            primary_dimension=primary_dimension,
            threshold=threshold,
            weight=weight,
            criticality=criticality,
            owner_user_id=owner_user_id,
            parameters=parameters,
            correlation_id=correlation_id,
            actor_context=actor_context,
        )

    def create_version(
        self,
        *,
        actor_id: str,
        quality_rule_id: str,
        parameters: dict[str, Any],
        threshold: float,
        weight: float,
        criticality: str,
        correlation_id: str | None = None,
        actor_context: ActorContext | None = None,
    ) -> tuple[QualityRule, RuleVersion]:
        rule = self.service.repository.get_rule(quality_rule_id)
        self._require_dataset_actor(actor_id, actor_context, rule.dataset_id)
        version = self.service.create_version(
            actor_id=actor_id,
            quality_rule_id=quality_rule_id,
            parameters=parameters,
            threshold=threshold,
            weight=weight,
            criticality=criticality,
            correlation_id=correlation_id,
            actor_context=actor_context,
        )
        return self.service.repository.get_rule(quality_rule_id), version

    def test_rule(
        self,
        *,
        actor_id: str,
        rule_version_id: str,
        options: RuleTestOptions | None = None,
        correlation_id: str | None = None,
        actor_context: ActorContext | None = None,
    ) -> RuleTestResult:
        version = self.service.repository.get_version(rule_version_id)
        rule = self.service.repository.get_rule(version.quality_rule_id)
        self._require_dataset_actor(actor_id, actor_context, rule.dataset_id)
        return self.service.test_rule(
            actor_id=actor_id,
            rule_version_id=rule_version_id,
            options=options,
            correlation_id=correlation_id,
            actor_context=actor_context,
        )

    def activate_rule(
        self,
        *,
        actor_id: str,
        quality_rule_id: str,
        correlation_id: str | None = None,
        actor_context: ActorContext | None = None,
    ) -> tuple[QualityRule, RuleVersion]:
        rule = self.service.repository.get_rule(quality_rule_id)
        self._require_dataset_actor(actor_id, actor_context, rule.dataset_id)
        self.service.activate_rule(
            actor_id=actor_id,
            quality_rule_id=quality_rule_id,
            correlation_id=correlation_id,
            actor_context=actor_context,
        )
        return self._current(quality_rule_id)

    def request_rule_approval(
        self,
        *,
        actor_context: ActorContext | None,
        quality_rule_id: str,
    ) -> tuple[QualityRule, RuleVersion, RuleApprovalRequest]:
        request = self.service.request_rule_approval(
            actor_context=actor_context,
            quality_rule_id=quality_rule_id,
        )
        rule, version = self._for_version(request.rule_version_id)
        return rule, version, request

    def decide_rule_approval(
        self,
        *,
        actor_context: ActorContext | None,
        approval_request_id: str,
        decision: str,
        reason_code: str,
    ) -> tuple[QualityRule, RuleVersion]:
        request = self.service.decide_rule_approval(
            actor_context=actor_context,
            approval_request_id=approval_request_id,
            decision=decision,
            reason_code=reason_code,
        )
        return self._for_version(request.rule_version_id)

    def withdraw_rule_approval(
        self,
        *,
        actor_context: ActorContext | None,
        approval_request_id: str,
        reason_code: str,
    ) -> tuple[QualityRule, RuleVersion]:
        request = self.service.withdraw_rule_approval(
            actor_context=actor_context,
            approval_request_id=approval_request_id,
            reason_code=reason_code,
        )
        return self._for_version(request.rule_version_id)

    def passivate_rule(
        self,
        *,
        quality_rule_id: str,
        correlation_id: str | None = None,
        actor_id: str | None = None,
        actor_context: ActorContext | None = None,
    ) -> tuple[QualityRule, RuleVersion]:
        if actor_id is not None:
            rule = self.service.repository.get_rule(quality_rule_id)
            self._require_dataset_actor(actor_id, actor_context, rule.dataset_id)
        self.service.passivate_rule(
            quality_rule_id=quality_rule_id,
            correlation_id=correlation_id,
            actor_context=actor_context,
        )
        return self._current(quality_rule_id)

    def _for_version(self, rule_version_id: str) -> tuple[QualityRule, RuleVersion]:
        version = self.service.repository.get_version(rule_version_id)
        return self.service.repository.get_rule(version.quality_rule_id), version

    def _current(self, quality_rule_id: str) -> tuple[QualityRule, RuleVersion]:
        rule = self.service.repository.get_rule(quality_rule_id)
        versions = self.service.repository.list_versions(quality_rule_id)
        if not versions:
            raise RuleValidationError("QualityRule must have an existing version.")
        return rule, versions[-1]

    @staticmethod
    def _require_dataset_actor(
        actor_id: str,
        actor_context: ActorContext | None,
        dataset_id: str,
    ) -> ActorContext:
        if actor_context is None or actor_context.actor_id != actor_id:
            raise RuleAuthorizationError("Trusted rule actor context is required.")
        if dataset_id not in actor_context.permitted_dataset_ids:
            raise RuleAuthorizationError("Actor is outside the rule dataset scope.")
        return actor_context
