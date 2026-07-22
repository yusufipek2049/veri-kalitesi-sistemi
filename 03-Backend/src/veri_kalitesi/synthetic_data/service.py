"""Fail-closed sentetik üretim çalışması talep servisi."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Callable

from veri_kalitesi.audit import AuditEventInput, AuditResult, SQLiteTransactionalAudit
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.synthetic_data.authorization import (
    authorize_synthetic_actor,
    validate_synthetic_access_policy,
)
from veri_kalitesi.synthetic_data.errors import SyntheticDataValidationError
from veri_kalitesi.synthetic_data.models import (
    SyntheticDatasetPolicy,
    SyntheticGenerationRun,
    SyntheticRunAccessPolicy,
    SyntheticScenario,
    utc_now,
)
from veri_kalitesi.synthetic_data.repository import SQLiteSyntheticDataRepository


class SyntheticGenerationRegistryService:
    def __init__(
        self,
        repository: SQLiteSyntheticDataRepository,
        *,
        transactional_audit: SQLiteTransactionalAudit,
        access_policy: SyntheticRunAccessPolicy,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.repository = repository
        self.transactional_audit = transactional_audit
        self.access_policy = access_policy
        self.clock = clock
        validate_synthetic_access_policy(access_policy)

    def request_run(
        self,
        *,
        actor_context: ActorContext | None,
        dataset_id: str,
        scenario_id: str,
        scenario_version: str,
        generator_version: str,
        configuration_version: str,
        random_seed: int,
        requested_record_count: int,
    ) -> SyntheticGenerationRun:
        now = self.clock()
        _validate_aware_time(now, "Synthetic run request time")
        context = authorize_synthetic_actor(
            actor_context,
            dataset_id=dataset_id,
            at=now,
            access_policy=self.access_policy,
            operation="run requests",
        )
        policy = self.repository.resolve_effective_policy(dataset_id, at=now)
        if policy is None:
            raise SyntheticDataValidationError(
                "Active approved synthetic dataset policy is required."
            )
        _validate_effective_policy(policy)
        scenario = self.repository.get_scenario(scenario_id, scenario_version)
        _validate_policy_scenario_match(
            policy,
            scenario,
            dataset_id=dataset_id,
            configuration_version=configuration_version,
        )
        run = SyntheticGenerationRun(
            dataset_id=dataset_id,
            scenario_id=scenario.scenario_id,
            scenario_version=scenario.scenario_version,
            generator_version=generator_version,
            configuration_version=configuration_version,
            schema_version=scenario.schema_version,
            policy_version=policy.policy_version,
            random_seed=random_seed,
            requested_record_count=requested_record_count,
            requested_by=context.actor_id,
            audit_reference="pending",
            created_at=now,
        )
        event = AuditEventInput(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            correlation_id=context.correlation_id,
            action="SYNTHETIC_GENERATION_RUN_REQUESTED",
            object_type="SyntheticGenerationRun",
            object_id=run.generation_run_id,
            result=AuditResult.SUCCESS,
            reason_code="SYNTHETIC_GENERATION_RUN_REQUESTED",
            old_values={},
            new_values={
                "dataset_id": dataset_id,
                "policy_version": policy.policy_version,
                "scenario_version": scenario.scenario_version,
                "schema_version": scenario.schema_version,
                "generator_version": generator_version,
                "configuration_version": configuration_version,
                "requested_record_count": requested_record_count,
                "seed_present": True,
                "status": run.status.value,
                "synthetic_origin": True,
                "access_policy_version": self.access_policy.version,
            },
            occurred_at=now,
            session_id=context.session_id,
        )
        prepared = self.transactional_audit.prepare(event)
        stored = self.repository.add_run_with_audit(
            replace(run, audit_reference=prepared.event_id),
            audit_event=prepared,
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return stored


def _validate_effective_policy(policy: SyntheticDatasetPolicy) -> None:
    if not policy.synthetic_generation_allowed:
        raise SyntheticDataValidationError("Synthetic generation is disabled by policy.")
    if not policy.ground_truth_enabled:
        raise SyntheticDataValidationError("Independent ground truth is required by policy.")


def _validate_policy_scenario_match(
    policy: SyntheticDatasetPolicy,
    scenario: SyntheticScenario,
    *,
    dataset_id: str,
    configuration_version: str,
) -> None:
    if scenario.dataset_id != dataset_id:
        raise SyntheticDataValidationError("Synthetic scenario dataset does not match request.")
    expected = (
        policy.schema_version,
        policy.synthetic_profile,
        policy.volume_profile,
        policy.distribution_profile,
        policy.missingness_profile,
        policy.defect_injection_profile,
        policy.privacy_profile,
    )
    actual = (
        scenario.schema_version,
        scenario.synthetic_profile,
        scenario.volume_profile,
        scenario.distribution_profile,
        scenario.missingness_profile,
        scenario.defect_injection_profile,
        scenario.privacy_profile,
    )
    if actual != expected:
        raise SyntheticDataValidationError(
            "Synthetic scenario does not match the effective dataset policy."
        )
    if scenario.configuration_version != configuration_version:
        raise SyntheticDataValidationError(
            "Synthetic scenario configuration version does not match request."
        )


def _validate_aware_time(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SyntheticDataValidationError(f"{name} must be timezone-aware.")
