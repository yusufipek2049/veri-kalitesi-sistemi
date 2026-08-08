"""Concrete production ExecutionExecutor against active PostgreSQL sources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from veri_kalitesi.data_sources.postgresql import PostgreSQLConnector
from veri_kalitesi.data_sources.secrets import SecretResolver
from veri_kalitesi.data_sources.models import DataSourceStatus
from veri_kalitesi.data_sources.postgresql_repository import PostgreSQLDataSourceRepository
from veri_kalitesi.executions.errors import ExecutionTechnicalError
from veri_kalitesi.executions.models import (
    ExecutionTimeouts,
    MeasurementStatus,
    RuleExecution,
    RuleResultComputation,
)
from veri_kalitesi.rules.models import RuleStatus, RuleType, RuleVersion
from veri_kalitesi.rules.postgresql_repository import PostgreSQLRuleRepository


@dataclass(frozen=True)
class PostgreSQLRuleExecutionExecutor:
    """ExecutionExecutor protocol'ünün somut production uygulaması.

    Rule/source repository, SecretResolver ve PostgreSQLConnector bağımlılıklarını
    kullanarak DQ_RULE_IR_V1 planlarını aktif PostgreSQL kaynağında salt okunur
    yürütür. Desteklenmeyen IR version/operator fail-closed davranışı sergiler.
    """

    rule_repository: PostgreSQLRuleRepository
    source_repository: PostgreSQLDataSourceRepository
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
        results: list[RuleResultComputation] = []
        for version in versions:
            result = self._execute_version(execution, version, timeouts)
            results.append(result)
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
        source_id = self._resolve_source_id(version)
        source = self.source_repository.get_data_source(source_id)
        if source is None or source.status is not DataSourceStatus.ACTIVE:
            raise ExecutionTechnicalError(
                f"Data source {source_id} is not active.",
                retryable=False,
            )
        secret = self.secret_resolver.resolve(source.secret_reference)
        definition = dict(version.definition)
        custom_sql = definition.get("sql") or definition.get("count_query")
        try:
            if custom_sql is not None:
                population = self.connector.execute_count_query(
                    source,
                    secret,
                    custom_sql,
                    connection_timeout_seconds=timeouts.connection_seconds,
                    query_timeout_seconds=timeouts.query_seconds,
                )
                failed_count = 0
            else:
                violation_sql = self._build_violation_query(version, definition)
                population_sql = self._build_population_query(definition)
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
            evidence={},
        )

    def _resolve_source_id(self, version: RuleVersion) -> str:
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
        return dataset.data_source_id

    @staticmethod
    def _build_violation_query(version: RuleVersion, definition: dict[str, Any]) -> str:
        table, field = _require_table_field(definition)
        rule_type = version.rule_type
        if rule_type is RuleType.REQUIRED:
            return f'SELECT COUNT(*) FROM "{table}" WHERE "{field}" IS NULL'
        if rule_type is RuleType.UNIQUE:
            return (
                f'SELECT COUNT(*) - COUNT(DISTINCT "{field}") '
                f'FROM "{table}" WHERE "{field}" IS NOT NULL'
            )
        if rule_type is RuleType.RANGE:
            low = definition.get("min")
            high = definition.get("max")
            conditions: list[str] = []
            if low is not None:
                conditions.append(f'"{field}" < {low}')
            if high is not None:
                conditions.append(f'"{field}" > {high}')
            where = " OR ".join(conditions) if conditions else "FALSE"
            return f'SELECT COUNT(*) FROM "{table}" WHERE "{field}" IS NOT NULL AND ({where})'
        if rule_type is RuleType.REGEX:
            pattern = definition.get("pattern", "")
            return (
                f'SELECT COUNT(*) FROM "{table}" '
                f'WHERE "{field}" IS NOT NULL AND "{field}" !~ \'{pattern}\''
            )
        if rule_type is RuleType.FRESHNESS:
            max_age = definition.get("max_age_seconds", 86400)
            ts_field = definition.get("timestamp_field", field)
            return (
                f'SELECT COUNT(*) FROM "{table}" '
                f'WHERE "{ts_field}" IS NOT NULL '
                f"AND \"{ts_field}\" < NOW() - INTERVAL '{max_age} seconds'"
            )
        raise ExecutionTechnicalError(
            f"Unsupported template rule type: {rule_type.value}",
            retryable=False,
        )

    @staticmethod
    def _build_population_query(definition: dict[str, Any]) -> str:
        table, field = _require_table_field(definition)
        return f'SELECT COUNT(*) FROM "{table}" WHERE "{field}" IS NOT NULL'


def _require_table_field(definition: dict[str, Any]) -> tuple[str, str]:
    table = definition.get("table", "")
    field = definition.get("field", "")
    if not table or not field:
        raise ExecutionTechnicalError(
            "Rule definition lacks table/field for template query.",
            retryable=False,
        )
    return table, field


def _measurement_status(failed_count: int, population: int, threshold: float) -> MeasurementStatus:
    if population == 0:
        return MeasurementStatus.NO_DATA
    fail_ratio = failed_count / population
    if failed_count == 0:
        return MeasurementStatus.PASSED
    if threshold <= 0 or fail_ratio > threshold:
        return MeasurementStatus.FAILED
    return MeasurementStatus.WARNING
