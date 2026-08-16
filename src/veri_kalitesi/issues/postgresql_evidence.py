"""PostgreSQL-backed issue investigation evidence provider."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from veri_kalitesi.executions.models import RuleExecutionResult
from veri_kalitesi.issues.investigation import IssueEvidencePayload
from veri_kalitesi.issues.models import DataQualityIssue, IssueScopeType
from veri_kalitesi.rules.models import QualityRule, RuleVersion


class IssueReader(Protocol):
    """Provider'ın ihtiyaç duyduğu dar issue okuma yüzeyi."""

    def get(self, issue_id: str) -> DataQualityIssue: ...


class ExecutionResultReader(Protocol):
    def list_results(self, execution_id: str) -> list[RuleExecutionResult]: ...


class RuleReader(Protocol):
    def get_version(self, rule_version_id: str) -> RuleVersion: ...

    def get_rule(self, quality_rule_id: str) -> QualityRule: ...


class PostgreSQLIssueEvidenceProvider:
    """Issue'nun kaynak execution sonucundaki veri-minimum kanıtı okur."""

    def __init__(
        self,
        issue_reader: IssueReader,
        execution_reader: ExecutionResultReader,
        rule_reader: RuleReader,
    ) -> None:
        self._issue_reader = issue_reader
        self._execution_reader = execution_reader
        self._rule_reader = rule_reader

    def get_evidence_for_issue(
        self,
        issue_id: str,
        scope_type: IssueScopeType,
        scope_id: str,
    ) -> IssueEvidencePayload | None:
        issue = self._issue_reader.get(issue_id)
        if issue.scope_type is not scope_type or issue.scope_id != scope_id:
            return None
        if issue.source_execution_id is None or issue.source_rule_version_id is None:
            return None

        result = next(
            (
                item
                for item in self._execution_reader.list_results(issue.source_execution_id)
                if item.rule_version_id == issue.source_rule_version_id
            ),
            None,
        )
        if result is None or not result.evidence:
            return None

        evidence = result.evidence
        if not _has_evidence_contract(evidence):
            return None

        version = self._rule_reader.get_version(issue.source_rule_version_id)
        rule = self._rule_reader.get_rule(version.quality_rule_id)
        return IssueEvidencePayload(
            rule_version_id=version.rule_version_id,
            rule_description=rule.name,
            ir_version=version.ir_version,
            expected_summary=dict(evidence["expected_summary"]),
            actual_summary=dict(evidence["actual_summary"]),
            masked_samples=list(evidence["masked_samples"]),
            fingerprint=str(evidence["fingerprint"]),
            query_reference=str(evidence["query_reference"]),
            plan_reference=str(evidence["plan_reference"]),
        )


def _has_evidence_contract(evidence: Mapping[str, object]) -> bool:
    return (
        isinstance(evidence.get("expected_summary"), Mapping)
        and isinstance(evidence.get("actual_summary"), Mapping)
        and isinstance(evidence.get("masked_samples"), (list, tuple))
        and isinstance(evidence.get("fingerprint"), str)
        and isinstance(evidence.get("query_reference"), str)
        and isinstance(evidence.get("plan_reference"), str)
    )
