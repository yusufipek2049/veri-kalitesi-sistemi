from __future__ import annotations

from types import SimpleNamespace

import pytest

from veri_kalitesi.executions.errors import ExecutionTechnicalError
from veri_kalitesi.executions.models import MeasurementStatus, RuleExecution
from veri_kalitesi.executions.postgresql_executor import (
    PostgreSQLRuleExecutionExecutor,
    _measurement_status,
)


def _execution(observation_date: object = "2026-08-01") -> RuleExecution:
    return RuleExecution(
        idempotency_key_hash="idempotency",
        payload_hash="payload",
        rule_version_ids=("version-1",),
        scope={"observation_date": observation_date},
        triggered_by="test",
        correlation_id="correlation",
    )


def test_observation_date_scopes_real_source_relation() -> None:
    dataset = SimpleNamespace(namespace="dq", name="accounts")

    relation = PostgreSQLRuleExecutionExecutor._scoped_relation(_execution(), dataset)

    assert relation == (
        '(SELECT * FROM "dq"."accounts" WHERE "observed_on" = DATE \'2026-08-01\') AS "scoped_data"'
    )
    assert PostgreSQLRuleExecutionExecutor._build_population_query(relation).startswith(
        "SELECT COUNT(*) FROM (SELECT *"
    )


@pytest.mark.parametrize("value", ["not-a-date", 123, "2026-02-30"])
def test_invalid_observation_date_fails_closed(value: object) -> None:
    dataset = SimpleNamespace(namespace="dq", name="accounts")

    with pytest.raises(ExecutionTechnicalError, match="Observation date is invalid"):
        PostgreSQLRuleExecutionExecutor._scoped_relation(_execution(value), dataset)


def test_measurement_threshold_uses_pass_ratio() -> None:
    assert _measurement_status(1, 1000, 0.999) is MeasurementStatus.PASSED
    assert _measurement_status(2, 1000, 0.999) is MeasurementStatus.FAILED
