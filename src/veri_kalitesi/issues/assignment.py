"""Rule/dataset/source ownership zinciri üzerinden issue assignment resolver.

DS-05: Otomatik ve manuel issue üretimi için trusted ownership assignment.
- Kalite trigger'ında rule-version → quality-rule owner;
- Teknik trigger'da source owner;
- Manuel dataset trigger'ında dataset owner, yoksa parent source owner;
- Manuel source trigger'ında source owner.

ID, aktiflik ve hedef scope IssueAssigneeDirectory ile doğrulanır.
Sahip bulunamazsa fail-closed IssueAssignmentError üretir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from veri_kalitesi.data_sources.models import DataSource, Dataset
from veri_kalitesi.issues.errors import IssueAssignmentError
from veri_kalitesi.issues.models import (
    IssueAssignment,
    IssueAssigneeProfile,
    IssuePriority,
    IssueScopeType,
    IssueTrigger,
    IssueTriggerType,
)
from veri_kalitesi.issues.service import IssueAssigneeDirectory
from veri_kalitesi.rules.models import QualityRule, RuleCriticality, RuleVersion


class RuleVersionLookup(Protocol):
    def get_version(self, rule_version_id: str) -> RuleVersion: ...


class RuleLookup(Protocol):
    def get_rule(self, quality_rule_id: str) -> QualityRule: ...


class DatasetLookup(Protocol):
    def get_dataset(self, dataset_id: str) -> Dataset: ...


class DataSourceLookup(Protocol):
    def get_data_source(self, data_source_id: str) -> DataSource: ...


_CRITICALITY_TO_PRIORITY: dict[RuleCriticality, IssuePriority] = {
    RuleCriticality.LOW: IssuePriority.LOW,
    RuleCriticality.MEDIUM: IssuePriority.MEDIUM,
    RuleCriticality.HIGH: IssuePriority.HIGH,
    RuleCriticality.CRITICAL: IssuePriority.CRITICAL,
}


@dataclass(frozen=True)
class OwnershipIssueAssignmentResolver:
    """Rule/dataset/source ownership zinciri üzerinden assignment çözer."""

    rule_version_lookup: RuleVersionLookup
    rule_lookup: RuleLookup
    dataset_lookup: DatasetLookup
    data_source_lookup: DataSourceLookup
    assignee_directory: IssueAssigneeDirectory

    def resolve_assignment(self, trigger: IssueTrigger) -> IssueAssignment:
        if trigger.trigger_type in (
            IssueTriggerType.QUALITY_THRESHOLD,
            IssueTriggerType.CRITICAL_RULE_FAILURE,
        ):
            return self._resolve_quality(trigger)
        if trigger.trigger_type is IssueTriggerType.TECHNICAL_ERROR:
            return self._resolve_technical(trigger)
        if trigger.trigger_type is IssueTriggerType.MANUAL:
            return self._resolve_manual(trigger)
        raise IssueAssignmentError(
            f"Unsupported trigger type for assignment: {trigger.trigger_type}"
        )

    def _resolve_quality(self, trigger: IssueTrigger) -> IssueAssignment:
        if trigger.rule_version_id is None:
            raise IssueAssignmentError(
                "Quality trigger requires rule_version_id for ownership resolution."
            )
        version = self._get_version(trigger.rule_version_id)
        rule = self._get_rule(version.quality_rule_id)
        priority = _CRITICALITY_TO_PRIORITY.get(version.criticality, IssuePriority.MEDIUM)
        return self._validated_assignment(rule.owner_user_id, priority, trigger)

    def _resolve_technical(self, trigger: IssueTrigger) -> IssueAssignment:
        if trigger.scope_type is IssueScopeType.DATASET:
            dataset = self._get_dataset(trigger.scope_id)
            owner_id = dataset.owner_user_id
            if owner_id is None:
                source = self._get_data_source(dataset.data_source_id)
                owner_id = source.owner_user_id
        elif trigger.scope_type is IssueScopeType.SOURCE:
            source = self._get_data_source(trigger.scope_id)
            owner_id = source.owner_user_id
        else:
            raise IssueAssignmentError(
                f"Technical trigger has unsupported scope: {trigger.scope_type}"
            )
        return self._validated_assignment(owner_id, IssuePriority.HIGH, trigger)

    def _resolve_manual(self, trigger: IssueTrigger) -> IssueAssignment:
        if trigger.scope_type is IssueScopeType.DATASET:
            dataset = self._get_dataset(trigger.scope_id)
            owner_id = dataset.owner_user_id
            if owner_id is None:
                source = self._get_data_source(dataset.data_source_id)
                owner_id = source.owner_user_id
        elif trigger.scope_type is IssueScopeType.SOURCE:
            source = self._get_data_source(trigger.scope_id)
            owner_id = source.owner_user_id
        else:
            raise IssueAssignmentError(
                f"Manual trigger has unsupported scope: {trigger.scope_type}"
            )
        return self._validated_assignment(owner_id, IssuePriority.MEDIUM, trigger)

    def _validated_assignment(
        self,
        owner_user_id: str | None,
        priority: IssuePriority,
        trigger: IssueTrigger,
    ) -> IssueAssignment:
        if not owner_user_id:
            raise IssueAssignmentError(
                "No owner found in the ownership chain for issue assignment."
            )
        profile = self._get_assignee_profile(owner_user_id)
        if profile is None:
            raise IssueAssignmentError(
                f"Owner '{owner_user_id}' is not registered in the assignee directory."
            )
        if not profile.active:
            raise IssueAssignmentError(
                f"Owner '{owner_user_id}' is not active for issue assignment."
            )
        if not self._scope_permitted(profile, trigger):
            raise IssueAssignmentError(
                f"Owner '{owner_user_id}' is not permitted for trigger scope."
            )
        return IssueAssignment(assignee_user_id=owner_user_id, priority=priority)

    def _scope_permitted(self, profile: IssueAssigneeProfile, trigger: IssueTrigger) -> bool:
        if trigger.scope_type is IssueScopeType.DATASET:
            return trigger.scope_id in profile.permitted_dataset_ids
        if trigger.scope_type is IssueScopeType.SOURCE:
            return trigger.scope_id in profile.permitted_source_ids
        return False

    def _get_version(self, rule_version_id: str) -> RuleVersion:
        try:
            return self.rule_version_lookup.get_version(rule_version_id)
        except Exception as exc:
            raise IssueAssignmentError(
                f"Rule version '{rule_version_id}' not found for ownership resolution."
            ) from exc

    def _get_rule(self, quality_rule_id: str) -> QualityRule:
        try:
            return self.rule_lookup.get_rule(quality_rule_id)
        except Exception as exc:
            raise IssueAssignmentError(
                f"Quality rule '{quality_rule_id}' not found for ownership resolution."
            ) from exc

    def _get_dataset(self, dataset_id: str) -> Dataset:
        try:
            return self.dataset_lookup.get_dataset(dataset_id)
        except Exception as exc:
            raise IssueAssignmentError(
                f"Dataset '{dataset_id}' not found for ownership resolution."
            ) from exc

    def _get_data_source(self, data_source_id: str) -> DataSource:
        try:
            return self.data_source_lookup.get_data_source(data_source_id)
        except Exception as exc:
            raise IssueAssignmentError(
                f"Data source '{data_source_id}' not found for ownership resolution."
            ) from exc

    def _get_assignee_profile(self, user_id: str) -> IssueAssigneeProfile | None:
        return self.assignee_directory.get_assignee_profile(user_id)
