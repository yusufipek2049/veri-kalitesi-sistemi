"""Execution kritiklik kapısı — yönetişim onay gerekliliğini çözümler.

Bir çalıştırma, iptal veya dead-letter yeniden işleme talebinin
yönetişim onayından geçip geçmeyeceğini belirler. Kritiklik,
hedef dataset'lerin ``Criticality.CRITICAL`` değerine sahip
olmasına bakılarak fail-closed şekilde çözülür.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from veri_kalitesi.data_sources.models import Criticality
from veri_kalitesi.executions.models import RuleExecution
from veri_kalitesi.jobs.models import DeadLetterRecord
from veri_kalitesi.rules.models import QualityRule, RuleVersion

logger = logging.getLogger(__name__)


class GovernanceRuleLookup(Protocol):
    """Kural sürümünden kurala çözümleme yüzeyi."""

    def get_version(self, rule_version_id: str) -> RuleVersion: ...

    def get_rule(self, quality_rule_id: str) -> QualityRule: ...


class GovernanceDatasetLookup(Protocol):
    """Dataset kritiklik çözümleme yüzeyi."""

    def get_dataset(self, dataset_id: str) -> Any: ...


class GovernanceExecutionLookup(Protocol):
    """Execution okuma yüzeyi."""

    def get(self, execution_id: str) -> RuleExecution: ...


class ExecutionCriticalityGuard:
    """Manuel çalıştırma/iptal/dead-letter için kritiklik kapısı.

    Çözümleme zinciri: rule_version → quality_rule → dataset → criticality.
    Herhangi bir dataset ``Criticality.CRITICAL`` ise kapı ``True`` döner.
    Çözümleme hatasında fail-closed: ``True`` döner.
    """

    def __init__(
        self,
        rule_lookup: GovernanceRuleLookup,
        dataset_lookup: GovernanceDatasetLookup,
        execution_lookup: GovernanceExecutionLookup | None = None,
    ) -> None:
        self._rule_lookup = rule_lookup
        self._dataset_lookup = dataset_lookup
        self._execution_lookup = execution_lookup

    def requires_approval_for_start(
        self, rule_version_ids: tuple[str, ...]
    ) -> bool:
        """Manuel çalıştırma talebinin onay gerektirip gerektirmediğini döner."""
        return self._any_critical_dataset(rule_version_ids)

    def requires_approval_for_cancel(self, execution_id: str) -> bool:
        """İptal talebinin onay gerektirip gerektirmediğini döner."""
        if self._execution_lookup is None:
            return True
        execution = self._safe_get_execution(execution_id)
        if execution is None:
            return True
        return self.requires_approval_for_execution(execution)

    def requires_approval_for_execution(self, execution: RuleExecution) -> bool:
        """Mevcut execution nesnesi için onay gerekliliğini döner."""
        return self._any_critical_dataset(execution.rule_version_ids)

    def requires_approval_for_dead_letter(self, letter: DeadLetterRecord) -> bool:
        """Dead-letter yeniden işleme için onay gerekliliğini döner."""
        if self._execution_lookup is None:
            return True
        execution = self._safe_get_execution(letter.job_id)
        if execution is None:
            return True
        return self.requires_approval_for_execution(execution)

    def resolve_dataset_ids(self, rule_version_ids: tuple[str, ...]) -> frozenset[str]:
        """Kural sürümlerinin hedef dataset ID'lerini döner."""
        dataset_ids: set[str] = set()
        for vid in rule_version_ids:
            try:
                version = self._rule_lookup.get_version(vid)
                rule = self._rule_lookup.get_rule(version.quality_rule_id)
                dataset_ids.add(rule.dataset_id)
            except Exception:
                logger.warning(
                    "Execution governance guard could not resolve rule version",
                    extra={
                        "event": "governance_guard_resolution_failed",
                        "rule_version_id": vid,
                    },
                )
        return frozenset(dataset_ids)

    def _any_critical_dataset(self, rule_version_ids: tuple[str, ...]) -> bool:
        """Kural sürümlerinin herhangi bir dataset'inin CRITICAL olup olmadığını döner."""
        if not rule_version_ids:
            return False
        for vid in rule_version_ids:
            try:
                version = self._rule_lookup.get_version(vid)
                rule = self._rule_lookup.get_rule(version.quality_rule_id)
                dataset = self._dataset_lookup.get_dataset(rule.dataset_id)
                criticality = getattr(dataset, "criticality", None)
                if criticality is not None and (
                    criticality is Criticality.CRITICAL
                    or getattr(criticality, "value", criticality) == "CRITICAL"
                ):
                    return True
            except Exception:
                logger.warning(
                    "Execution governance guard failed; defaulting to approval required",
                    extra={
                        "event": "governance_guard_resolution_failed",
                        "rule_version_id": vid,
                    },
                    exc_info=True,
                )
                return True
        return False

    def _safe_get_execution(self, execution_id: str) -> RuleExecution | None:
        if self._execution_lookup is None:
            return None
        try:
            return self._execution_lookup.get(execution_id)
        except Exception:
            logger.warning(
                "Execution governance guard could not load execution",
                extra={
                    "event": "governance_guard_execution_load_failed",
                    "execution_id": execution_id,
                },
            )
            return None
