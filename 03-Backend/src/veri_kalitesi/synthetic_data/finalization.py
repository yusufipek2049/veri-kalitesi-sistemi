"""Doğrulanmış Golden çıktıyı append-only run tamamlama kanıtına bağlar."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import hashlib
import hmac
from typing import Callable

from veri_kalitesi.audit import AuditEventInput, AuditResult, SQLiteTransactionalAudit
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.synthetic_data.authorization import (
    authorize_synthetic_actor,
    validate_synthetic_access_policy,
)
from veri_kalitesi.synthetic_data.canonical import build_golden_canonical_payload
from veri_kalitesi.synthetic_data.errors import SyntheticDataValidationError
from veri_kalitesi.synthetic_data.models import (
    GoldenRelationalDataset,
    SyntheticGenerationRun,
    SyntheticRunAccessPolicy,
    SyntheticRunCompletion,
    SyntheticRunStatus,
    SyntheticScenario,
    SyntheticValidationResult,
    SyntheticValidationStatus,
    utc_now,
)
from veri_kalitesi.synthetic_data.repository import SQLiteSyntheticDataRepository


class SyntheticRunFinalizationService:
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

    def finalize(
        self,
        *,
        actor_context: ActorContext | None,
        output: GoldenRelationalDataset,
        validation_result_id: str,
    ) -> SyntheticRunCompletion:
        if not isinstance(output, GoldenRelationalDataset):
            raise SyntheticDataValidationError("Golden relational output is required.")
        now = self.clock()
        _validate_aware_time(now)
        context = authorize_synthetic_actor(
            actor_context,
            dataset_id=output.dataset_id,
            at=now,
            access_policy=self.access_policy,
            operation="run finalization",
        )
        run = self.repository.get_run(output.generation_run_id)
        context = authorize_synthetic_actor(
            context,
            dataset_id=run.dataset_id,
            at=now,
            access_policy=self.access_policy,
            operation="run finalization",
        )
        scenario = self.repository.get_scenario(run.scenario_id, run.scenario_version)
        validation = self.repository.get_validation_result_by_id(validation_result_id)
        policy = self.repository.get_policy(run.dataset_id, run.policy_version)

        _validate_lineage(run, scenario, output)
        digest = _validate_canonical_integrity(run, scenario, output)
        _validate_validation_link(output, validation)
        completion = SyntheticRunCompletion(
            generation_run_id=run.generation_run_id,
            status=_terminal_status(validation.status),
            output_reference=output.output_reference,
            canonical_sha256=digest,
            payload_byte_count=len(output.canonical_payload),
            subject_count=len(output.subjects),
            observation_count=len(output.observations),
            validation_result_id=validation.validation_result_id,
            validation_status=validation.status,
            retention_policy_id=policy.retention_policy_id,
            audit_reference="pending",
            created_at=now,
        )
        event = AuditEventInput(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            correlation_id=context.correlation_id,
            action="SYNTHETIC_RUN_FINALIZED",
            object_type="SyntheticGenerationRun",
            object_id=run.generation_run_id,
            result=AuditResult.SUCCESS,
            reason_code="SYNTHETIC_RUN_FINALIZED",
            old_values={},
            new_values={
                "dataset_id": run.dataset_id,
                "generation_run_id": run.generation_run_id,
                "status": completion.status.value,
                "validation_status": completion.validation_status.value,
                "subject_count": completion.subject_count,
                "observation_count": completion.observation_count,
                "payload_byte_count": completion.payload_byte_count,
                "output_digest_present": True,
                "validation_reference_present": True,
                "retention_policy_id": completion.retention_policy_id,
                "synthetic_origin": True,
                "access_policy_version": self.access_policy.version,
            },
            occurred_at=now,
            session_id=context.session_id,
        )
        prepared = self.transactional_audit.prepare(event)
        stored, created = self.repository.add_run_completion_with_audit(
            replace(completion, audit_reference=prepared.event_id),
            audit_event=prepared,
            audit_outbox=self.transactional_audit,
        )
        if created:
            self.transactional_audit.publish_pending()
        return stored


def _validate_lineage(
    run: SyntheticGenerationRun,
    scenario: SyntheticScenario,
    output: GoldenRelationalDataset,
) -> None:
    expected = (
        run.generation_run_id,
        run.dataset_id,
        run.scenario_id,
        run.scenario_version,
        run.generator_version,
        run.configuration_version,
        run.schema_version,
        run.policy_version,
        run.random_seed,
        run.requested_record_count,
        scenario.scenario_id,
        scenario.scenario_version,
        True,
    )
    actual = (
        output.generation_run_id,
        output.dataset_id,
        output.scenario_id,
        output.scenario_version,
        output.generator_version,
        output.configuration_version,
        output.schema_version,
        output.policy_version,
        output.random_seed,
        output.requested_record_count,
        output.scenario_id,
        output.scenario_version,
        output.synthetic_origin,
    )
    if actual != expected:
        raise SyntheticDataValidationError("Synthetic output lineage does not match the run.")


def _validate_canonical_integrity(
    run: SyntheticGenerationRun,
    scenario: SyntheticScenario,
    output: GoldenRelationalDataset,
) -> str:
    expected_payload = build_golden_canonical_payload(
        run,
        scenario,
        output.subjects,
        output.observations,
    )
    if not hmac.compare_digest(expected_payload, output.canonical_payload):
        raise SyntheticDataValidationError(
            "Synthetic canonical payload does not match the validated records."
        )
    digest = hashlib.sha256(expected_payload).hexdigest()
    if not hmac.compare_digest(digest, output.canonical_sha256) or not hmac.compare_digest(
        f"sha256:{digest}", output.output_reference
    ):
        raise SyntheticDataValidationError("Synthetic output digest integrity check failed.")
    return digest


def _validate_validation_link(
    output: GoldenRelationalDataset,
    validation: SyntheticValidationResult,
) -> None:
    if validation.generation_run_id != output.generation_run_id:
        raise SyntheticDataValidationError("Synthetic validation does not belong to the run.")
    if validation.actual_output_reference != output.output_reference:
        raise SyntheticDataValidationError(
            "Synthetic validation does not reference the canonical output."
        )
    if validation.actual_subject_count != len(
        output.subjects
    ) or validation.actual_observation_count != len(output.observations):
        raise SyntheticDataValidationError(
            "Synthetic validation counts do not match the canonical output."
        )


def _terminal_status(validation_status: SyntheticValidationStatus) -> SyntheticRunStatus:
    return {
        SyntheticValidationStatus.PASS: SyntheticRunStatus.COMPLETED,
        SyntheticValidationStatus.BLOCKED: SyntheticRunStatus.BLOCKED,
        SyntheticValidationStatus.TECHNICAL_ERROR: SyntheticRunStatus.TECHNICAL_ERROR,
    }[validation_status]


def _validate_aware_time(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SyntheticDataValidationError("Synthetic finalization time must be timezone-aware.")
