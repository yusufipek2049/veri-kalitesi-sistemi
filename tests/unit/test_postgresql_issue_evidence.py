"""PostgreSQL issue investigation evidence adapter tests."""

from types import SimpleNamespace

from veri_kalitesi.issues import IssueScopeType, PostgreSQLIssueEvidenceProvider


class _IssueReader:
    def __init__(self, issue) -> None:  # type: ignore[no-untyped-def]
        self.issue = issue

    def get(self, issue_id: str):  # type: ignore[no-untyped-def]
        assert issue_id == self.issue.issue_id
        return self.issue


class _ExecutionReader:
    def __init__(self, results: list[object]) -> None:
        self.results = results

    def list_results(self, execution_id: str):  # type: ignore[no-untyped-def]
        assert execution_id == "execution-1"
        return self.results


class _RuleReader:
    def get_version(self, rule_version_id: str):  # type: ignore[no-untyped-def]
        assert rule_version_id == "rule-version-1"
        return SimpleNamespace(
            rule_version_id=rule_version_id,
            quality_rule_id="rule-1",
            ir_version="DQ_RULE_IR_V1",
        )

    def get_rule(self, quality_rule_id: str):  # type: ignore[no-untyped-def]
        assert quality_rule_id == "rule-1"
        return SimpleNamespace(name="Müşteri kimliği boş olmamalı")


def _issue():  # type: ignore[no-untyped-def]
    return SimpleNamespace(
        issue_id="issue-1",
        scope_type=IssueScopeType.DATASET,
        scope_id="dataset-1",
        source_execution_id="execution-1",
        source_rule_version_id="rule-version-1",
    )


def test_provider_maps_source_execution_evidence_to_investigation_payload() -> None:
    evidence = {
        "fingerprint": "sha256:" + "a" * 64,
        "masked_samples": ["hmac-sha256://key/" + "b" * 64],
        "expected_summary": {"failed_count": 0},
        "actual_summary": {"failed_count": 4},
        "query_reference": "query-template://rules/version-1",
        "plan_reference": "plan://executions/version-1",
    }
    provider = PostgreSQLIssueEvidenceProvider(
        _IssueReader(_issue()),
        _ExecutionReader([SimpleNamespace(rule_version_id="rule-version-1", evidence=evidence)]),
        _RuleReader(),
    )

    payload = provider.get_evidence_for_issue("issue-1", IssueScopeType.DATASET, "dataset-1")

    assert payload is not None
    assert payload.rule_description == "Müşteri kimliği boş olmamalı"
    assert payload.actual_summary == {"failed_count": 4}
    assert payload.masked_samples == ["hmac-sha256://key/" + "b" * 64]


def test_provider_fails_closed_when_issue_has_no_execution_evidence() -> None:
    provider = PostgreSQLIssueEvidenceProvider(
        _IssueReader(_issue()),
        _ExecutionReader([]),
        _RuleReader(),
    )

    assert provider.get_evidence_for_issue("issue-1", IssueScopeType.DATASET, "dataset-1") is None
