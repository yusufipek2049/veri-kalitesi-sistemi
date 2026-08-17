"""Concrete production ExecutionExecutor against active PostgreSQL sources."""

from __future__ import annotations

import logging
import hashlib
from dataclasses import dataclass
from datetime import date
from time import perf_counter
from typing import Any, Protocol

from veri_kalitesi.data_sources.postgresql import PostgreSQLConnector
from veri_kalitesi.data_sources.secrets import SecretResolver
from veri_kalitesi.data_sources.models import DataSource, Dataset, DataSourceStatus
from veri_kalitesi.executions.errors import ExecutionTechnicalError
from veri_kalitesi.executions.models import (
    ExecutionTimeouts,
    MeasurementStatus,
    RuleExecution,
    RuleResultComputation,
)
from veri_kalitesi.executions.violation_sql import (
    SQL_IDENTIFIER,
    build_violation_query,
    quote_identifier,
    requires_reference,
)
from veri_kalitesi.rules.models import QualityRule, RuleStatus, RuleVersion


logger = logging.getLogger(__name__)


class RuleExecutionCatalog(Protocol):
    """PostgreSQL kural yürütücüsünün ihtiyaç duyduğu kural kataloğu yüzeyi."""

    def get_rule(self, quality_rule_id: str) -> QualityRule: ...


class SourceExecutionCatalog(Protocol):
    """PostgreSQL kural yürütücüsünün ihtiyaç duyduğu kaynak kataloğu yüzeyi."""

    def get_data_source(self, data_source_id: str) -> DataSource: ...

    def get_dataset(self, dataset_id: str) -> Dataset: ...


@dataclass(frozen=True)
class PostgreSQLRuleExecutionExecutor:
    """ExecutionExecutor protocol'ünün somut production uygulaması.

    Rule/source repository, SecretResolver ve PostgreSQLConnector bağımlılıklarını
    kullanarak DQ_RULE_IR_V1 planlarını aktif PostgreSQL kaynağında salt okunur
    yürütür. Desteklenmeyen IR version/operator fail-closed davranışı sergiler.
    """

    rule_repository: RuleExecutionCatalog
    source_repository: SourceExecutionCatalog
    secret_resolver: SecretResolver
    connector: PostgreSQLConnector

    def execute(
        self,
        *,
        execution: RuleExecution,
        versions: tuple[RuleVersion, ...],
        timeouts: ExecutionTimeouts,
    ) -> tuple[RuleResultComputation, ...]:
        if not versions:
            raise ExecutionTechnicalError("EXECUTION_NO_VERSIONS", retryable=False)
        started = perf_counter()
        logger.info(
            "Rule execution started",
            extra={
                "event": "rule_execution_started",
                "execution_id": execution.execution_id,
                "rule_count": len(versions),
            },
        )
        results: list[RuleResultComputation] = []
        try:
            for version in versions:
                result = self._execute_version(execution, version, timeouts)
                results.append(result)
        except Exception as exc:
            logger.error(
                "Rule execution failed",
                extra={
                    "event": "rule_execution_failed",
                    "execution_id": execution.execution_id,
                    "duration_ms": round((perf_counter() - started) * 1000),
                    "error_class": type(exc).__name__,
                },
            )
            raise
        logger.info(
            "Rule execution completed",
            extra={
                "event": "rule_execution_completed",
                "execution_id": execution.execution_id,
                "duration_ms": round((perf_counter() - started) * 1000),
                "result_count": len(results),
                "passed_count": sum(item.passed_count or 0 for item in results),
                "failed_count": sum(item.failed_count or 0 for item in results),
                "technical_error_count": sum(item.technical_error_count or 0 for item in results),
            },
        )
        return tuple(results)

    def _execute_version(
        self,
        execution: RuleExecution,
        version: RuleVersion,
        timeouts: ExecutionTimeouts,
    ) -> RuleResultComputation:
        if version.ir_version != "DQ_RULE_IR_V1":
            raise ExecutionTechnicalError(
                f"Unsupported IR version: {version.ir_version}",
                retryable=False,
            )
        source_id, dataset = self._resolve_source_and_dataset(version)
        source = self.source_repository.get_data_source(source_id)
        if source is None or source.status is not DataSourceStatus.ACTIVE:
            raise ExecutionTechnicalError(
                f"Data source {source_id} is not active.",
                retryable=False,
            )
        secret = self.secret_resolver.resolve(source.secret_reference)
        definition = dict(version.definition)
        table = self._scoped_relation(execution, dataset)
        custom_sql = definition.get("sql") or definition.get("count_query")
        try:
            if custom_sql is not None:
                failed_count = self.connector.execute_count_query(
                    source,
                    secret,
                    custom_sql,
                    connection_timeout_seconds=timeouts.connection_seconds,
                    query_timeout_seconds=timeouts.query_seconds,
                )
                population_sql = self._build_population_query(table)
                population = self.connector.execute_count_query(
                    source,
                    secret,
                    population_sql,
                    connection_timeout_seconds=timeouts.connection_seconds,
                    query_timeout_seconds=timeouts.query_seconds,
                )
            else:
                violation_sql = self._violation_query(version, definition, table, dataset)
                population_sql = self._build_population_query(table)
                violation_count = self.connector.execute_count_query(
                    source,
                    secret,
                    violation_sql,
                    connection_timeout_seconds=timeouts.connection_seconds,
                    query_timeout_seconds=timeouts.query_seconds,
                )
                population = self.connector.execute_count_query(
                    source,
                    secret,
                    population_sql,
                    connection_timeout_seconds=timeouts.connection_seconds,
                    query_timeout_seconds=timeouts.query_seconds,
                )
                failed_count = min(violation_count, population)
        except ExecutionTechnicalError:
            raise
        except Exception as exc:
            raise ExecutionTechnicalError(
                f"EXECUTION_SOURCE_ERROR:{type(exc).__name__}",
                retryable=True,
            ) from exc
        passed_count = max(population - failed_count, 0)
        status = _measurement_status(failed_count, population, version.threshold)
        return RuleResultComputation(
            rule_version_id=version.rule_version_id,
            population_count=population,
            eligible_count=population,
            evaluated_count=population,
            passed_count=passed_count,
            failed_count=failed_count,
            excluded_count=0,
            technical_error_count=0,
            unknown_count=0,
            measurement_status=status,
            completed_partitions=(),
            evidence=(
                {
                    "fingerprint": "sha256:"
                    + hashlib.sha256(
                        f"{version.rule_version_id}:{population}:{failed_count}".encode()
                    ).hexdigest(),
                    "masked_samples": [],
                    "expected_summary": {
                        "population_count": population,
                        "evaluated_count": population,
                    },
                    "actual_summary": {
                        "passed_count": passed_count,
                        "failed_count": failed_count,
                    },
                    "query_reference": (f"query-template://execution/{version.rule_version_id}"),
                    "plan_reference": f"plan://execution/{version.rule_version_id}",
                }
                if failed_count
                else {}
            ),
        )

    @staticmethod
    def _scoped_relation(execution: RuleExecution, dataset: Dataset) -> str:
        if not SQL_IDENTIFIER.fullmatch(dataset.namespace) or not SQL_IDENTIFIER.fullmatch(
            dataset.name
        ):
            raise ExecutionTechnicalError("Dataset identifier is invalid.", retryable=False)
        table = f'"{dataset.namespace}"."{dataset.name}"'
        observation_date = execution.scope.get("observation_date")
        if observation_date is None:
            return table
        if not isinstance(observation_date, str):
            raise ExecutionTechnicalError("Observation date is invalid.", retryable=False)
        try:
            normalized_date = date.fromisoformat(observation_date).isoformat()
        except ValueError as exc:
            raise ExecutionTechnicalError("Observation date is invalid.", retryable=False) from exc
        return (
            f"(SELECT * FROM {table} WHERE \"observed_on\" = DATE '{normalized_date}') "
            'AS "scoped_data"'
        )

    def _resolve_source_and_dataset(self, version: RuleVersion) -> tuple[str, Dataset]:
        rule = self.rule_repository.get_rule(version.quality_rule_id)
        if rule is None:
            raise ExecutionTechnicalError(
                f"Rule {version.quality_rule_id} not found.",
                retryable=False,
            )
        if rule.status is not RuleStatus.ACTIVE:
            raise ExecutionTechnicalError(
                f"Rule {version.quality_rule_id} is not active.",
                retryable=False,
            )
        dataset = self.source_repository.get_dataset(rule.dataset_id)
        if dataset is None:
            raise ExecutionTechnicalError(
                f"Dataset {rule.dataset_id} not found.",
                retryable=False,
            )
        return dataset.data_source_id, dataset

    def _violation_query(
        self,
        version: RuleVersion,
        definition: dict[str, Any],
        table: str,
        dataset: Dataset,
    ) -> str:
        reference_table = (
            self._reference_relation(definition, dataset)
            if requires_reference(version.rule_type)
            else None
        )
        return build_violation_query(
            rule_type=version.rule_type,
            definition=definition,
            table=table,
            reference_table=reference_table,
        )

    def _reference_relation(self, definition: dict[str, Any], dataset: Dataset) -> str:
        reference_dataset_id = definition.get("reference_dataset_id")
        if not isinstance(reference_dataset_id, str) or not reference_dataset_id:
            raise ExecutionTechnicalError(
                "Rule definition lacks reference_dataset_id.",
                retryable=False,
            )
        reference = self.source_repository.get_dataset(reference_dataset_id)
        if reference is None:
            raise ExecutionTechnicalError(
                f"Reference dataset {reference_dataset_id} not found.",
                retryable=False,
            )
        if reference.data_source_id != dataset.data_source_id:
            raise ExecutionTechnicalError(
                "Reference dataset must belong to the same data source.",
                retryable=False,
            )
        return f"{quote_identifier(reference.namespace)}.{quote_identifier(reference.name)}"

    @staticmethod
    def _build_population_query(table: str) -> str:
        return f"SELECT COUNT(*) FROM {table}"


def _measurement_status(failed_count: int, population: int, threshold: float) -> MeasurementStatus:
    if population == 0:
        return MeasurementStatus.NO_DATA
    if failed_count == 0:
        return MeasurementStatus.PASSED
    pass_ratio = (population - failed_count) / population
    return (
        MeasurementStatus.PASSED
        if threshold > 0 and pass_ratio >= threshold
        else MeasurementStatus.FAILED
    )
