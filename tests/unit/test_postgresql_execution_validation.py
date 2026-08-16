"""PostgreSQLExecutionStartService kural-kaynak ilişki doğrulaması birim testleri.

Çalıştırma başlatma isteğindeki kaynakların seçili kuralların ilişkili
kaynaklarıyla birebir eşleşmesi gerekir; ilişkisiz kaynak içeren istekler
reddedilir ve DB'ye çalıştırma kaydı yazılmaz.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import pytest

from veri_kalitesi.api.postgresql_execution import PostgreSQLExecutionStartService
from veri_kalitesi.executions.errors import ExecutionValidationError
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType


@dataclass(frozen=True)
class _FakeStatus:
    value: str


@dataclass(frozen=True)
class FakeRuleVersion:
    rule_version_id: str
    quality_rule_id: str
    version_no: int = 1


@dataclass(frozen=True)
class FakeQualityRule:
    quality_rule_id: str
    dataset_id: str
    status_value: str = "ACTIVE"

    @property
    def status(self) -> _FakeStatus:
        return _FakeStatus(self.status_value)


@dataclass(frozen=True)
class FakeDataset:
    dataset_id: str
    data_source_id: str


class FakeRuleCatalog:
    def __init__(
        self,
        versions: tuple[FakeRuleVersion, ...],
        rules: tuple[FakeQualityRule, ...],
    ) -> None:
        self._versions = {item.rule_version_id: item for item in versions}
        self._rules = {item.quality_rule_id: item for item in rules}

    def get_version(self, rule_version_id: str) -> FakeRuleVersion:
        version = self._versions.get(rule_version_id)
        if version is None:
            raise KeyError(rule_version_id)
        return version

    def get_rule(self, quality_rule_id: str) -> FakeQualityRule | None:
        return self._rules.get(quality_rule_id)

    def list_versions(self, quality_rule_id: str) -> list[FakeRuleVersion]:
        return [item for item in self._versions.values() if item.quality_rule_id == quality_rule_id]


class FakeSourceCatalog:
    def __init__(
        self,
        datasets: tuple[FakeDataset, ...],
        *,
        failing: bool = False,
    ) -> None:
        self._datasets = {item.dataset_id: item for item in datasets}
        self._failing = failing

    def get_dataset(self, dataset_id: str) -> FakeDataset | None:
        if self._failing:
            raise RuntimeError("synthetic catalog outage")
        return self._datasets.get(dataset_id)


def _operator_context(source_ids: frozenset[str]) -> ActorContext:
    from datetime import datetime, timezone

    issued_at = datetime.now(timezone.utc)
    return ActorContextIssuer().issue(
        actor_id="operator-a",
        actor_type=ActorType.USER,
        authentication_source="test-execution-validation",
        session_id="test-session",
        roles=frozenset({"DATA_STEWARD"}),
        permitted_source_ids=source_ids,
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=True,
        privileged=False,
        issued_at=issued_at,
        expires_at=issued_at + timedelta(minutes=5),
        policy_version="TEST_VALIDATION_POLICY",
        correlation_id="test-validation-correlation",
    )


def _service(
    rule_catalog: FakeRuleCatalog,
    source_catalog: FakeSourceCatalog,
) -> PostgreSQLExecutionStartService:
    return PostgreSQLExecutionStartService(
        object(),  # repository doğrulama aşamasında kullanılmaz
        job_queue=object(),  # type: ignore[arg-type]
        transactional_audit=object(),  # type: ignore[arg-type]
        rule_catalog=rule_catalog,  # type: ignore[arg-type]
        source_catalog=source_catalog,  # type: ignore[arg-type]
    )


def _standard_catalogs() -> tuple[FakeRuleCatalog, FakeSourceCatalog]:
    rule_catalog = FakeRuleCatalog(
        versions=(FakeRuleVersion("version-1", "rule-1"),),
        rules=(FakeQualityRule("rule-1", "dataset-1"),),
    )
    source_catalog = FakeSourceCatalog(
        datasets=(FakeDataset("dataset-1", "source-a"),),
    )
    return rule_catalog, source_catalog


def test_unrelated_source_is_rejected() -> None:
    rule_catalog, source_catalog = _standard_catalogs()
    service = _service(rule_catalog, source_catalog)

    with pytest.raises(ExecutionValidationError, match="not associated"):
        service._validate_execution_request(
            rule_version_ids=("version-1",),
            source_ids=("source-a", "source-b"),
            actor_context=_operator_context(frozenset({"source-a", "source-b"})),
        )


def test_missing_required_source_is_rejected() -> None:
    rule_catalog, source_catalog = _standard_catalogs()
    service = _service(rule_catalog, source_catalog)

    # Tek kural senaryosunda ilişkisiz kaynak kontrolü önce tetiklenir
    with pytest.raises(ExecutionValidationError, match="not associated"):
        service._validate_execution_request(
            rule_version_ids=("version-1",),
            source_ids=("source-b",),
            actor_context=_operator_context(frozenset({"source-a", "source-b"})),
        )


def test_exact_related_source_passes() -> None:
    rule_catalog, source_catalog = _standard_catalogs()
    service = _service(rule_catalog, source_catalog)

    service._validate_execution_request(
        rule_version_ids=("version-1",),
        source_ids=("source-a",),
        actor_context=_operator_context(frozenset({"source-a"})),
    )


def test_unresolvable_dataset_is_rejected_fail_closed() -> None:
    rule_catalog = FakeRuleCatalog(
        versions=(FakeRuleVersion("version-1", "rule-1"),),
        rules=(FakeQualityRule("rule-1", "dataset-missing"),),
    )
    source_catalog = FakeSourceCatalog(datasets=())
    service = _service(rule_catalog, source_catalog)

    with pytest.raises(ExecutionValidationError, match="could not be resolved"):
        service._validate_execution_request(
            rule_version_ids=("version-1",),
            source_ids=("source-a",),
            actor_context=_operator_context(frozenset({"source-a"})),
        )


def test_catalog_outage_is_rejected_fail_closed() -> None:
    rule_catalog, _ = _standard_catalogs()
    source_catalog = FakeSourceCatalog(datasets=(), failing=True)
    service = _service(rule_catalog, source_catalog)

    with pytest.raises(ExecutionValidationError, match="could not be resolved"):
        service._validate_execution_request(
            rule_version_ids=("version-1",),
            source_ids=("source-a",),
            actor_context=_operator_context(frozenset({"source-a"})),
        )


def test_multiple_rules_require_all_related_sources() -> None:
    rule_catalog = FakeRuleCatalog(
        versions=(
            FakeRuleVersion("version-1", "rule-1"),
            FakeRuleVersion("version-2", "rule-2"),
        ),
        rules=(
            FakeQualityRule("rule-1", "dataset-1"),
            FakeQualityRule("rule-2", "dataset-2"),
        ),
    )
    source_catalog = FakeSourceCatalog(
        datasets=(
            FakeDataset("dataset-1", "source-a"),
            FakeDataset("dataset-2", "source-b"),
        ),
    )
    service = _service(rule_catalog, source_catalog)
    actor_context = _operator_context(frozenset({"source-a", "source-b"}))

    service._validate_execution_request(
        rule_version_ids=("version-1", "version-2"),
        source_ids=("source-a", "source-b"),
        actor_context=actor_context,
    )

    with pytest.raises(ExecutionValidationError, match="require sources"):
        service._validate_execution_request(
            rule_version_ids=("version-1", "version-2"),
            source_ids=("source-a",),
            actor_context=actor_context,
        )
