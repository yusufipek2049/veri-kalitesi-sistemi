"""Kural calistirmasindan kanit adayi turetme.

Issue'nun kaynak calistirmasinin (a) kural sonuclari ve (b) deneme kayitlari
(log) otomatik olarak kanit adayi kabul edilir. Kullanici cozum formunda bu
adaylardan birini secer; secim kalici bir kanit kaydina donusur.
"""

from __future__ import annotations

import logging
from typing import Protocol, Sequence

from veri_kalitesi.executions.errors import ExecutionNotFoundError
from veri_kalitesi.executions.models import ExecutionAttempt, RuleExecution, RuleExecutionResult
from veri_kalitesi.issues.evidence import IssueEvidenceCandidate, IssueEvidenceKind
from veri_kalitesi.issues.models import DataQualityIssue
from veri_kalitesi.operational_logging import current_correlation_id
from veri_kalitesi.rules.models import QualityRule, RuleVersion

logger = logging.getLogger(__name__)

RESULT_CANDIDATE_PREFIX = "RESULT"
LOG_CANDIDATE_PREFIX = "LOG"

#: Silinmiş veya erişilemeyen kayıt: meşru biçimde "kanıt yok" demektir.
#: Bağlantı/serialization gibi teknik arızalar bu kümeye girmez ve loglanır.
_MISSING_RECORD_ERRORS = (ExecutionNotFoundError, KeyError, LookupError)


class ExecutionEvidenceReader(Protocol):
    def get(self, execution_id: str) -> RuleExecution: ...

    def list_results(self, execution_id: str) -> list[RuleExecutionResult]: ...

    def list_attempts(self, execution_id: str) -> list[ExecutionAttempt]: ...


class RuleNameReader(Protocol):
    def get_version(self, rule_version_id: str) -> RuleVersion: ...

    def get_rule(self, quality_rule_id: str) -> QualityRule: ...


class ExecutionIssueEvidenceCandidateProvider:
    """Issue'nun kaynak calistirmasindan kanit adaylarini uretir."""

    def __init__(
        self,
        execution_reader: ExecutionEvidenceReader,
        rule_reader: RuleNameReader | None = None,
    ) -> None:
        self._execution_reader = execution_reader
        self._rule_reader = rule_reader

    def list_candidates(self, issue: DataQualityIssue) -> Sequence[IssueEvidenceCandidate]:
        execution_id = issue.source_execution_id
        if not execution_id:
            return ()
        try:
            execution = self._execution_reader.get(execution_id)
        except _MISSING_RECORD_ERRORS:
            # Calistirma silinmis: issue icin gercekten kanit adayi yok.
            return ()
        except Exception as exc:  # noqa: BLE001 - altyapi arizasi yutulmadan raporlanir
            _log_degraded("execution", execution_id, exc)
            return ()

        observed_at = execution.finished_at or execution.started_at or execution.created_at
        candidates: list[IssueEvidenceCandidate] = []

        for result in self._safe_results(execution_id):
            candidates.append(
                IssueEvidenceCandidate(
                    candidate_key=f"{RESULT_CANDIDATE_PREFIX}:{execution_id}:{result.rule_version_id}",
                    kind=IssueEvidenceKind.EXECUTION_RESULT,
                    label=self._result_label(result),
                    execution_id=execution_id,
                    observed_at=observed_at,
                    rule_version_id=result.rule_version_id,
                    evaluated_count=result.evaluated_count,
                    failed_count=result.failed_count,
                    measurement_status=(
                        result.measurement_status.value
                        if result.measurement_status is not None
                        else None
                    ),
                    fingerprint=_evidence_text(result, "fingerprint"),
                    query_reference=_evidence_text(result, "query_reference"),
                    plan_reference=_evidence_text(result, "plan_reference"),
                )
            )

        for attempt in self._safe_attempts(execution_id):
            candidates.append(
                IssueEvidenceCandidate(
                    candidate_key=f"{LOG_CANDIDATE_PREFIX}:{execution_id}:{attempt.attempt_no}",
                    kind=IssueEvidenceKind.EXECUTION_LOG,
                    label=_attempt_label(attempt),
                    execution_id=execution_id,
                    observed_at=attempt.created_at,
                    measurement_status=attempt.status.value,
                )
            )
        return tuple(candidates)

    def _safe_results(self, execution_id: str) -> Sequence[RuleExecutionResult]:
        try:
            return tuple(self._execution_reader.list_results(execution_id))
        except _MISSING_RECORD_ERRORS:
            return ()
        except Exception as exc:  # noqa: BLE001
            _log_degraded("results", execution_id, exc)
            return ()

    def _safe_attempts(self, execution_id: str) -> Sequence[ExecutionAttempt]:
        try:
            return tuple(self._execution_reader.list_attempts(execution_id))
        except _MISSING_RECORD_ERRORS:
            return ()
        except Exception as exc:  # noqa: BLE001
            _log_degraded("attempts", execution_id, exc)
            return ()

    def _result_label(self, result: RuleExecutionResult) -> str:
        rule_name = self._rule_name(result.rule_version_id)
        failed = result.failed_count
        evaluated = result.evaluated_count
        counts = (
            f"{failed}/{evaluated} başarısız"
            if failed is not None and evaluated is not None
            else "sayım yok"
        )
        return f"Kural sonucu — {rule_name} ({counts})"[:200]

    def _rule_name(self, rule_version_id: str) -> str:
        if self._rule_reader is None:
            return rule_version_id
        try:
            version = self._rule_reader.get_version(rule_version_id)
            rule = self._rule_reader.get_rule(version.quality_rule_id)
        except _MISSING_RECORD_ERRORS:
            return rule_version_id
        except Exception as exc:  # noqa: BLE001
            _log_degraded("rule_name", rule_version_id, exc)
            return rule_version_id
        return rule.name


def _log_degraded(stage: str, object_id: str, exc: Exception) -> None:
    """Teknik arizayi correlation ID ile raporlar.

    F-07: Bu hatalar kullaniciya mesru bir "kanit yok" sonucu gibi
    gorunuyordu; artik bos liste donmeye devam ediyoruz ama ariza sessiz
    kalmiyor.
    """

    logger.warning(
        "Issue evidence candidates degraded",
        extra={
            "event": "issue_evidence_candidates_degraded",
            "stage": stage,
            "object_id": object_id,
            "error_class": type(exc).__name__,
            "correlation_id": current_correlation_id(),
        },
        exc_info=exc,
    )


def _attempt_label(attempt: ExecutionAttempt) -> str:
    suffix = f" — {attempt.error_class}" if attempt.error_class else ""
    return f"Çalıştırma logu — deneme #{attempt.attempt_no} ({attempt.status.value}){suffix}"[:200]


def _evidence_text(result: RuleExecutionResult, key: str) -> str | None:
    value = result.evidence.get(key)
    return str(value) if isinstance(value, str) and value else None
