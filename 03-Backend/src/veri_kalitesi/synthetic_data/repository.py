"""Sentetik veri kayıt çekirdeği için append-only SQLite deposu."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal
import json
from threading import RLock

from veri_kalitesi.audit import PreparedAuditEvent, SQLiteTransactionalAudit
from veri_kalitesi.synthetic_data.errors import (
    SyntheticDataConflictError,
    SyntheticDataTechnicalError,
    SyntheticDataValidationError,
)
from veri_kalitesi.synthetic_data.models import (
    SyntheticDatasetPolicy,
    SyntheticGenerationRun,
    SyntheticGroundTruth,
    SyntheticPolicyStatus,
    SyntheticProfile,
    SyntheticRunCompletion,
    SyntheticRunStatus,
    SyntheticScenario,
    SyntheticTemporalProfile,
    SyntheticValidationResult,
    SyntheticValidationStatus,
)


class SQLiteSyntheticDataRepository:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        try:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS synthetic_dataset_policies (
                    policy_id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL,
                    synthetic_generation_allowed INTEGER NOT NULL,
                    synthetic_profile TEXT NOT NULL,
                    volume_profile TEXT NOT NULL,
                    distribution_profile TEXT NOT NULL,
                    missingness_profile TEXT NOT NULL,
                    defect_injection_profile TEXT NOT NULL,
                    privacy_profile TEXT NOT NULL,
                    retention_policy_id TEXT NOT NULL,
                    ground_truth_enabled INTEGER NOT NULL,
                    seed_strategy TEXT NOT NULL,
                    expected_score_tolerance TEXT,
                    criticality_profile_id TEXT NOT NULL,
                    notification_test_enabled INTEGER NOT NULL,
                    schema_version TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    effective_from TEXT NOT NULL,
                    effective_to TEXT,
                    approved_by TEXT,
                    approval_status TEXT NOT NULL,
                    audit_reference TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE (dataset_id, policy_version)
                );

                CREATE TABLE IF NOT EXISTS synthetic_scenarios (
                    scenario_record_id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL,
                    dataset_id TEXT NOT NULL,
                    scenario_version TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    configuration_version TEXT NOT NULL,
                    synthetic_profile TEXT NOT NULL,
                    volume_profile TEXT NOT NULL,
                    distribution_profile TEXT NOT NULL,
                    missingness_profile TEXT NOT NULL,
                    defect_injection_profile TEXT NOT NULL,
                    privacy_profile TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (scenario_id, scenario_version)
                );

                CREATE TABLE IF NOT EXISTS synthetic_generation_runs (
                    generation_run_id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL,
                    scenario_id TEXT NOT NULL,
                    scenario_version TEXT NOT NULL,
                    generator_version TEXT NOT NULL,
                    configuration_version TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    random_seed TEXT NOT NULL,
                    requested_record_count INTEGER NOT NULL,
                    requested_by TEXT NOT NULL,
                    audit_reference TEXT NOT NULL,
                    status TEXT NOT NULL,
                    output_reference TEXT,
                    validation_reference TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS synthetic_temporal_profiles (
                    profile_version TEXT PRIMARY KEY,
                    base_time TEXT NOT NULL,
                    period_count INTEGER NOT NULL,
                    period_duration_seconds INTEGER NOT NULL,
                    source_created_delay_seconds INTEGER NOT NULL,
                    source_updated_delay_seconds INTEGER NOT NULL,
                    ingestion_delay_seconds INTEGER NOT NULL,
                    processing_delay_seconds INTEGER NOT NULL,
                    quality_check_delay_seconds INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS synthetic_ground_truth (
                    synthetic_record_id TEXT PRIMARY KEY,
                    generation_run_id TEXT NOT NULL,
                    dataset_id TEXT NOT NULL,
                    scenario_id TEXT NOT NULL,
                    scenario_version TEXT NOT NULL,
                    generator_version TEXT NOT NULL,
                    random_seed TEXT NOT NULL,
                    source_system TEXT NOT NULL,
                    expected_subject_count INTEGER NOT NULL,
                    expected_observation_count INTEGER NOT NULL,
                    expected_primary_keys_unique INTEGER NOT NULL,
                    expected_foreign_keys_valid INTEGER NOT NULL,
                    expected_status_transitions_valid INTEGER NOT NULL,
                    expected_reference_codes_valid INTEGER NOT NULL,
                    expected_temporal_order_valid INTEGER NOT NULL,
                    expected_rule_result TEXT NOT NULL,
                    expected_severity TEXT NOT NULL,
                    expected_dataset_score TEXT,
                    expected_notification INTEGER NOT NULL,
                    expected_escalation INTEGER NOT NULL,
                    ground_truth_version TEXT NOT NULL,
                    audit_reference TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (generation_run_id, ground_truth_version)
                );

                CREATE TABLE IF NOT EXISTS synthetic_validation_results (
                    validation_result_id TEXT PRIMARY KEY,
                    generation_run_id TEXT NOT NULL,
                    synthetic_record_id TEXT NOT NULL,
                    ground_truth_version TEXT NOT NULL,
                    validation_class TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason_codes TEXT NOT NULL,
                    actual_subject_count INTEGER NOT NULL,
                    actual_observation_count INTEGER NOT NULL,
                    actual_primary_keys_unique INTEGER NOT NULL,
                    actual_foreign_keys_valid INTEGER NOT NULL,
                    actual_status_transitions_valid INTEGER NOT NULL,
                    actual_reference_codes_valid INTEGER NOT NULL,
                    actual_temporal_order_valid INTEGER NOT NULL,
                    actual_output_reference TEXT NOT NULL,
                    audit_reference TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (generation_run_id, ground_truth_version),
                    FOREIGN KEY (synthetic_record_id)
                        REFERENCES synthetic_ground_truth(synthetic_record_id)
                );

                CREATE TABLE IF NOT EXISTS synthetic_run_completions (
                    completion_id TEXT PRIMARY KEY,
                    generation_run_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    output_reference TEXT NOT NULL,
                    canonical_sha256 TEXT NOT NULL,
                    payload_byte_count INTEGER NOT NULL,
                    subject_count INTEGER NOT NULL,
                    observation_count INTEGER NOT NULL,
                    validation_result_id TEXT NOT NULL,
                    validation_status TEXT NOT NULL,
                    retention_policy_id TEXT NOT NULL,
                    audit_reference TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_synthetic_policy_effective
                ON synthetic_dataset_policies(
                    dataset_id, approval_status, effective_from, effective_to
                );

                CREATE INDEX IF NOT EXISTS idx_synthetic_runs_dataset
                ON synthetic_generation_runs(dataset_id, created_at, generation_run_id);

                CREATE TRIGGER IF NOT EXISTS synthetic_policies_no_update
                BEFORE UPDATE ON synthetic_dataset_policies
                BEGIN
                    SELECT RAISE(ABORT, 'synthetic policy history is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS synthetic_policies_no_delete
                BEFORE DELETE ON synthetic_dataset_policies
                BEGIN
                    SELECT RAISE(ABORT, 'synthetic policy history is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS synthetic_scenarios_no_update
                BEFORE UPDATE ON synthetic_scenarios
                BEGIN
                    SELECT RAISE(ABORT, 'synthetic scenario history is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS synthetic_scenarios_no_delete
                BEFORE DELETE ON synthetic_scenarios
                BEGIN
                    SELECT RAISE(ABORT, 'synthetic scenario history is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS synthetic_runs_no_update
                BEFORE UPDATE ON synthetic_generation_runs
                BEGIN
                    SELECT RAISE(ABORT, 'synthetic run history is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS synthetic_runs_no_delete
                BEFORE DELETE ON synthetic_generation_runs
                BEGIN
                    SELECT RAISE(ABORT, 'synthetic run history is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS synthetic_temporal_profiles_no_update
                BEFORE UPDATE ON synthetic_temporal_profiles
                BEGIN
                    SELECT RAISE(ABORT, 'synthetic temporal profile is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS synthetic_temporal_profiles_no_delete
                BEFORE DELETE ON synthetic_temporal_profiles
                BEGIN
                    SELECT RAISE(ABORT, 'synthetic temporal profile is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS synthetic_ground_truth_no_update
                BEFORE UPDATE ON synthetic_ground_truth
                BEGIN
                    SELECT RAISE(ABORT, 'synthetic ground truth is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS synthetic_ground_truth_no_delete
                BEFORE DELETE ON synthetic_ground_truth
                BEGIN
                    SELECT RAISE(ABORT, 'synthetic ground truth is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS synthetic_validation_results_no_update
                BEFORE UPDATE ON synthetic_validation_results
                BEGIN
                    SELECT RAISE(ABORT, 'synthetic validation result is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS synthetic_validation_results_no_delete
                BEFORE DELETE ON synthetic_validation_results
                BEGIN
                    SELECT RAISE(ABORT, 'synthetic validation result is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS synthetic_run_completions_no_update
                BEFORE UPDATE ON synthetic_run_completions
                BEGIN
                    SELECT RAISE(ABORT, 'synthetic run completion is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS synthetic_run_completions_no_delete
                BEFORE DELETE ON synthetic_run_completions
                BEGIN
                    SELECT RAISE(ABORT, 'synthetic run completion is append-only');
                END;
                """
            )
            self.connection.commit()
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError(
                "Synthetic data registry schema could not be initialized."
            ) from exc

    def add_policy(self, policy: SyntheticDatasetPolicy) -> SyntheticDatasetPolicy:
        _validate_policy(policy)
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """
                    INSERT INTO synthetic_dataset_policies (
                        policy_id, dataset_id, synthetic_generation_allowed,
                        synthetic_profile, volume_profile, distribution_profile,
                        missingness_profile, defect_injection_profile, privacy_profile,
                        retention_policy_id, ground_truth_enabled, seed_strategy,
                        expected_score_tolerance, criticality_profile_id,
                        notification_test_enabled, schema_version, policy_version,
                        effective_from, effective_to, approved_by, approval_status,
                        audit_reference, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _policy_values(policy),
                )
        except sqlite3.IntegrityError as exc:
            raise SyntheticDataConflictError(
                "Synthetic dataset policy identity or version conflicts."
            ) from exc
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError(
                "Synthetic dataset policy could not be persisted."
            ) from exc
        return policy

    def add_scenario(self, scenario: SyntheticScenario) -> SyntheticScenario:
        _validate_scenario(scenario)
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """
                    INSERT INTO synthetic_scenarios (
                        scenario_record_id, scenario_id, dataset_id, scenario_version,
                        schema_version, configuration_version, synthetic_profile,
                        volume_profile, distribution_profile, missingness_profile,
                        defect_injection_profile, privacy_profile, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _scenario_values(scenario),
                )
        except sqlite3.IntegrityError as exc:
            raise SyntheticDataConflictError(
                "Synthetic scenario identity or version conflicts."
            ) from exc
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError("Synthetic scenario could not be persisted.") from exc
        return scenario

    def add_temporal_profile(
        self,
        profile: SyntheticTemporalProfile,
    ) -> SyntheticTemporalProfile:
        _validate_temporal_profile(profile)
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """
                    INSERT INTO synthetic_temporal_profiles (
                        profile_version, base_time, period_count,
                        period_duration_seconds, source_created_delay_seconds,
                        source_updated_delay_seconds, ingestion_delay_seconds,
                        processing_delay_seconds, quality_check_delay_seconds,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _temporal_profile_values(profile),
                )
        except sqlite3.IntegrityError as exc:
            raise SyntheticDataConflictError(
                "Synthetic temporal profile version conflicts."
            ) from exc
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError(
                "Synthetic temporal profile could not be persisted."
            ) from exc
        return profile

    def get_temporal_profile(self, profile_version: str) -> SyntheticTemporalProfile:
        if not profile_version.strip():
            raise SyntheticDataValidationError("Temporal profile version is required.")
        try:
            row = self.connection.execute(
                """
                SELECT * FROM synthetic_temporal_profiles
                WHERE profile_version = ?
                """,
                (profile_version,),
            ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError(
                "Synthetic temporal profile could not be read."
            ) from exc
        if row is None:
            raise SyntheticDataValidationError("Synthetic temporal profile was not found.")
        return _row_to_temporal_profile(row)

    def resolve_effective_policy(
        self,
        dataset_id: str,
        *,
        at: datetime,
    ) -> SyntheticDatasetPolicy | None:
        if not dataset_id.strip():
            raise SyntheticDataValidationError("dataset_id is required.")
        _validate_aware_time(at, "Policy resolution time")
        try:
            rows = self.connection.execute(
                """
                SELECT * FROM synthetic_dataset_policies
                WHERE dataset_id = ?
                  AND approval_status = ?
                  AND effective_from <= ?
                  AND (effective_to IS NULL OR effective_to > ?)
                ORDER BY effective_from DESC, created_at DESC, policy_version DESC
                LIMIT 2
                """,
                (
                    dataset_id,
                    SyntheticPolicyStatus.APPROVED.value,
                    at.isoformat(),
                    at.isoformat(),
                ),
            ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError(
                "Effective synthetic dataset policy could not be read."
            ) from exc
        if len(rows) > 1:
            raise SyntheticDataConflictError(
                "Multiple effective synthetic dataset policies were found."
            )
        return _row_to_policy(rows[0]) if rows else None

    def get_policy(self, dataset_id: str, policy_version: str) -> SyntheticDatasetPolicy:
        _validate_ids((dataset_id, policy_version), "Synthetic policy identity fields")
        try:
            row = self.connection.execute(
                """
                SELECT * FROM synthetic_dataset_policies
                WHERE dataset_id = ? AND policy_version = ?
                """,
                (dataset_id, policy_version),
            ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError(
                "Synthetic dataset policy could not be read."
            ) from exc
        if row is None:
            raise SyntheticDataValidationError("Synthetic dataset policy was not found.")
        return _row_to_policy(row)

    def get_scenario(self, scenario_id: str, scenario_version: str) -> SyntheticScenario:
        if not scenario_id.strip() or not scenario_version.strip():
            raise SyntheticDataValidationError("Scenario identity and version are required.")
        try:
            row = self.connection.execute(
                """
                SELECT * FROM synthetic_scenarios
                WHERE scenario_id = ? AND scenario_version = ?
                """,
                (scenario_id, scenario_version),
            ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError("Synthetic scenario could not be read.") from exc
        if row is None:
            raise SyntheticDataValidationError("Synthetic scenario was not found.")
        return _row_to_scenario(row)

    def add_run_with_audit(
        self,
        run: SyntheticGenerationRun,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> SyntheticGenerationRun:
        if audit_outbox.connection is not self.connection:
            raise SyntheticDataValidationError(
                "Audit outbox must share the synthetic run transaction."
            )
        _validate_run(run)
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """
                    INSERT INTO synthetic_generation_runs (
                        generation_run_id, dataset_id, scenario_id, scenario_version,
                        generator_version, configuration_version, schema_version,
                        policy_version, random_seed, requested_record_count,
                        requested_by, audit_reference, status, output_reference,
                        validation_reference, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _run_values(run),
                )
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise SyntheticDataConflictError("Synthetic generation run conflicts.") from exc
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError(
                "Synthetic generation run and audit could not be persisted."
            ) from exc
        return self.get_run(run.generation_run_id)

    def get_run(self, generation_run_id: str) -> SyntheticGenerationRun:
        if not generation_run_id.strip():
            raise SyntheticDataValidationError("generation_run_id is required.")
        try:
            row = self.connection.execute(
                "SELECT * FROM synthetic_generation_runs WHERE generation_run_id = ?",
                (generation_run_id,),
            ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError(
                "Synthetic generation run could not be read."
            ) from exc
        if row is None:
            raise SyntheticDataValidationError("Synthetic generation run was not found.")
        return _row_to_run(row)

    def list_runs(self, dataset_id: str) -> list[SyntheticGenerationRun]:
        if not dataset_id.strip():
            raise SyntheticDataValidationError("dataset_id is required.")
        try:
            rows = self.connection.execute(
                """
                SELECT * FROM synthetic_generation_runs
                WHERE dataset_id = ?
                ORDER BY created_at, generation_run_id
                """,
                (dataset_id,),
            ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError(
                "Synthetic generation runs could not be read."
            ) from exc
        return [_row_to_run(row) for row in rows]

    def add_ground_truth_and_validation_with_audit(
        self,
        ground_truth: SyntheticGroundTruth,
        validation: SyntheticValidationResult,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> tuple[SyntheticGroundTruth, SyntheticValidationResult]:
        if audit_outbox.connection is not self.connection:
            raise SyntheticDataValidationError(
                "Audit outbox must share the synthetic validation transaction."
            )
        _validate_ground_truth(ground_truth)
        _validate_validation_result(validation, ground_truth)
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """
                    INSERT INTO synthetic_ground_truth (
                        synthetic_record_id, generation_run_id, dataset_id,
                        scenario_id, scenario_version, generator_version,
                        random_seed, source_system, expected_subject_count,
                        expected_observation_count, expected_primary_keys_unique,
                        expected_foreign_keys_valid, expected_status_transitions_valid,
                        expected_reference_codes_valid, expected_temporal_order_valid,
                        expected_rule_result, expected_severity, expected_dataset_score,
                        expected_notification, expected_escalation, ground_truth_version,
                        audit_reference, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _ground_truth_values(ground_truth),
                )
                self.connection.execute(
                    """
                    INSERT INTO synthetic_validation_results (
                        validation_result_id, generation_run_id, synthetic_record_id,
                        ground_truth_version, validation_class, status, reason_codes,
                        actual_subject_count, actual_observation_count,
                        actual_primary_keys_unique, actual_foreign_keys_valid,
                        actual_status_transitions_valid, actual_reference_codes_valid,
                        actual_temporal_order_valid, actual_output_reference,
                        audit_reference, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _validation_result_values(validation),
                )
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise SyntheticDataConflictError(
                "Synthetic ground truth or validation result conflicts."
            ) from exc
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError(
                "Synthetic ground truth, validation result and audit could not be persisted."
            ) from exc
        return (
            self.get_ground_truth(
                ground_truth.generation_run_id,
                ground_truth.ground_truth_version,
            ),
            self.get_validation_result(
                validation.generation_run_id,
                validation.ground_truth_version,
            ),
        )

    def get_ground_truth(
        self,
        generation_run_id: str,
        ground_truth_version: str,
    ) -> SyntheticGroundTruth:
        _validate_ids(
            (generation_run_id, ground_truth_version),
            "Synthetic ground truth identity fields",
        )
        try:
            row = self.connection.execute(
                """
                SELECT * FROM synthetic_ground_truth
                WHERE generation_run_id = ? AND ground_truth_version = ?
                """,
                (generation_run_id, ground_truth_version),
            ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError("Synthetic ground truth could not be read.") from exc
        if row is None:
            raise SyntheticDataValidationError("Synthetic ground truth was not found.")
        return _row_to_ground_truth(row)

    def get_validation_result(
        self,
        generation_run_id: str,
        ground_truth_version: str,
    ) -> SyntheticValidationResult:
        _validate_ids(
            (generation_run_id, ground_truth_version),
            "Synthetic validation identity fields",
        )
        try:
            row = self.connection.execute(
                """
                SELECT * FROM synthetic_validation_results
                WHERE generation_run_id = ? AND ground_truth_version = ?
                """,
                (generation_run_id, ground_truth_version),
            ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError(
                "Synthetic validation result could not be read."
            ) from exc
        if row is None:
            raise SyntheticDataValidationError("Synthetic validation result was not found.")
        return _row_to_validation_result(row)

    def get_validation_result_by_id(
        self,
        validation_result_id: str,
    ) -> SyntheticValidationResult:
        _validate_ids((validation_result_id,), "Synthetic validation result identity")
        try:
            row = self.connection.execute(
                """
                SELECT * FROM synthetic_validation_results
                WHERE validation_result_id = ?
                """,
                (validation_result_id,),
            ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError(
                "Synthetic validation result could not be read."
            ) from exc
        if row is None:
            raise SyntheticDataValidationError("Synthetic validation result was not found.")
        return _row_to_validation_result(row)

    def add_run_completion_with_audit(
        self,
        completion: SyntheticRunCompletion,
        *,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> tuple[SyntheticRunCompletion, bool]:
        if audit_outbox.connection is not self.connection:
            raise SyntheticDataValidationError(
                "Audit outbox must share the synthetic completion transaction."
            )
        _validate_run_completion(completion)
        try:
            with self._lock, self.connection:
                existing_row = self.connection.execute(
                    """
                    SELECT * FROM synthetic_run_completions
                    WHERE generation_run_id = ?
                    """,
                    (completion.generation_run_id,),
                ).fetchone()
                if existing_row is not None:
                    existing = _row_to_run_completion(existing_row)
                    if _same_completion_evidence(existing, completion):
                        return existing, False
                    raise SyntheticDataConflictError(
                        "Synthetic run already has different completion evidence."
                    )
                self.connection.execute(
                    """
                    INSERT INTO synthetic_run_completions (
                        completion_id, generation_run_id, status, output_reference,
                        canonical_sha256, payload_byte_count, subject_count,
                        observation_count, validation_result_id, validation_status,
                        retention_policy_id, audit_reference, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _run_completion_values(completion),
                )
                audit_outbox.stage(audit_event)
        except SyntheticDataConflictError:
            raise
        except sqlite3.IntegrityError as exc:
            raise SyntheticDataConflictError("Synthetic run completion conflicts.") from exc
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError(
                "Synthetic run completion and audit could not be persisted."
            ) from exc
        return self.get_run_completion(completion.generation_run_id), True

    def find_run_completion(
        self,
        generation_run_id: str,
    ) -> SyntheticRunCompletion | None:
        _validate_ids((generation_run_id,), "Synthetic run completion identity")
        try:
            row = self.connection.execute(
                """
                SELECT * FROM synthetic_run_completions
                WHERE generation_run_id = ?
                """,
                (generation_run_id,),
            ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise SyntheticDataTechnicalError(
                "Synthetic run completion could not be read."
            ) from exc
        return _row_to_run_completion(row) if row is not None else None

    def get_run_completion(self, generation_run_id: str) -> SyntheticRunCompletion:
        completion = self.find_run_completion(generation_run_id)
        if completion is None:
            raise SyntheticDataValidationError("Synthetic run completion was not found.")
        return completion

    def get_run_snapshot(self, generation_run_id: str) -> SyntheticGenerationRun:
        run = self.get_run(generation_run_id)
        completion = self.find_run_completion(generation_run_id)
        if completion is None:
            return run
        return SyntheticGenerationRun(
            generation_run_id=run.generation_run_id,
            dataset_id=run.dataset_id,
            scenario_id=run.scenario_id,
            scenario_version=run.scenario_version,
            generator_version=run.generator_version,
            configuration_version=run.configuration_version,
            schema_version=run.schema_version,
            policy_version=run.policy_version,
            random_seed=run.random_seed,
            requested_record_count=run.requested_record_count,
            requested_by=run.requested_by,
            audit_reference=run.audit_reference,
            status=completion.status,
            output_reference=completion.output_reference,
            validation_reference=completion.validation_result_id,
            created_at=run.created_at,
        )


def _validate_policy(policy: SyntheticDatasetPolicy) -> None:
    _validate_ids(
        (
            policy.policy_id,
            policy.dataset_id,
            policy.volume_profile,
            policy.distribution_profile,
            policy.missingness_profile,
            policy.defect_injection_profile,
            policy.privacy_profile,
            policy.retention_policy_id,
            policy.seed_strategy,
            policy.criticality_profile_id,
            policy.schema_version,
            policy.policy_version,
        ),
        "Synthetic dataset policy fields",
    )
    if not isinstance(policy.synthetic_generation_allowed, bool):
        raise SyntheticDataValidationError("Synthetic generation flag must be boolean.")
    if not isinstance(policy.ground_truth_enabled, bool):
        raise SyntheticDataValidationError("Ground truth flag must be boolean.")
    if not isinstance(policy.notification_test_enabled, bool):
        raise SyntheticDataValidationError("Notification test flag must be boolean.")
    if not isinstance(policy.synthetic_profile, SyntheticProfile):
        raise SyntheticDataValidationError("Synthetic profile is invalid.")
    if not isinstance(policy.approval_status, SyntheticPolicyStatus):
        raise SyntheticDataValidationError("Synthetic policy status is invalid.")
    if policy.expected_score_tolerance is not None and (
        not isinstance(policy.expected_score_tolerance, Decimal)
        or not policy.expected_score_tolerance.is_finite()
        or policy.expected_score_tolerance < 0
    ):
        raise SyntheticDataValidationError("Expected score tolerance is invalid.")
    _validate_aware_time(policy.effective_from, "Policy effective time")
    _validate_aware_time(policy.created_at, "Policy creation time")
    if policy.effective_to is not None:
        _validate_aware_time(policy.effective_to, "Policy expiry time")
        if policy.effective_to <= policy.effective_from:
            raise SyntheticDataValidationError("Policy expiry must follow effective time.")
    if policy.approval_status is SyntheticPolicyStatus.APPROVED and (
        not policy.approved_by
        or not policy.approved_by.strip()
        or not policy.audit_reference
        or not policy.audit_reference.strip()
    ):
        raise SyntheticDataValidationError(
            "Approved synthetic policy requires approver and audit reference."
        )


def _validate_scenario(scenario: SyntheticScenario) -> None:
    _validate_ids(
        (
            scenario.scenario_record_id,
            scenario.scenario_id,
            scenario.dataset_id,
            scenario.scenario_version,
            scenario.schema_version,
            scenario.configuration_version,
            scenario.volume_profile,
            scenario.distribution_profile,
            scenario.missingness_profile,
            scenario.defect_injection_profile,
            scenario.privacy_profile,
        ),
        "Synthetic scenario fields",
    )
    if not isinstance(scenario.synthetic_profile, SyntheticProfile):
        raise SyntheticDataValidationError("Synthetic scenario profile is invalid.")
    _validate_aware_time(scenario.created_at, "Scenario creation time")


def _validate_temporal_profile(profile: SyntheticTemporalProfile) -> None:
    _validate_ids((profile.profile_version,), "Synthetic temporal profile version")
    _validate_aware_time(profile.base_time, "Temporal profile base time")
    _validate_aware_time(profile.created_at, "Temporal profile creation time")
    if profile.base_time.utcoffset() != timedelta(0):
        raise SyntheticDataValidationError("Temporal profile base time must be UTC.")
    if (
        isinstance(profile.period_count, bool)
        or not isinstance(profile.period_count, int)
        or profile.period_count < 2
    ):
        raise SyntheticDataValidationError("Temporal profile requires multiple periods.")
    if (
        isinstance(profile.period_duration_seconds, bool)
        or not isinstance(profile.period_duration_seconds, int)
        or profile.period_duration_seconds <= 0
    ):
        raise SyntheticDataValidationError("Temporal period duration must be positive.")
    delays = (
        profile.source_created_delay_seconds,
        profile.source_updated_delay_seconds,
        profile.ingestion_delay_seconds,
        profile.processing_delay_seconds,
        profile.quality_check_delay_seconds,
    )
    if any(isinstance(value, bool) or not isinstance(value, int) for value in delays):
        raise SyntheticDataValidationError("Temporal profile delays must be integers.")
    if delays[0] < 0 or any(current < previous for previous, current in zip(delays, delays[1:])):
        raise SyntheticDataValidationError(
            "Temporal profile delays must preserve event processing order."
        )


def _validate_run(run: SyntheticGenerationRun) -> None:
    _validate_ids(
        (
            run.generation_run_id,
            run.dataset_id,
            run.scenario_id,
            run.scenario_version,
            run.generator_version,
            run.configuration_version,
            run.schema_version,
            run.policy_version,
            run.requested_by,
            run.audit_reference,
        ),
        "Synthetic generation run fields",
    )
    if isinstance(run.random_seed, bool) or not isinstance(run.random_seed, int):
        raise SyntheticDataValidationError("Random seed must be an integer.")
    if (
        isinstance(run.requested_record_count, bool)
        or not isinstance(run.requested_record_count, int)
        or run.requested_record_count <= 0
    ):
        raise SyntheticDataValidationError("Requested record count must be positive.")
    if run.status is not SyntheticRunStatus.REQUESTED:
        raise SyntheticDataValidationError("Initial synthetic run status is invalid.")
    if run.output_reference is not None or run.validation_reference is not None:
        raise SyntheticDataValidationError(
            "Requested synthetic run cannot contain output or validation references."
        )
    _validate_aware_time(run.created_at, "Run creation time")


def _validate_ground_truth(ground_truth: SyntheticGroundTruth) -> None:
    _validate_ids(
        (
            ground_truth.synthetic_record_id,
            ground_truth.generation_run_id,
            ground_truth.dataset_id,
            ground_truth.scenario_id,
            ground_truth.scenario_version,
            ground_truth.generator_version,
            ground_truth.source_system,
            ground_truth.expected_rule_result,
            ground_truth.expected_severity,
            ground_truth.ground_truth_version,
            ground_truth.audit_reference,
        ),
        "Synthetic ground truth fields",
    )
    if isinstance(ground_truth.random_seed, bool) or not isinstance(ground_truth.random_seed, int):
        raise SyntheticDataValidationError("Ground truth random seed must be an integer.")
    if ground_truth.expected_subject_count <= 0 or ground_truth.expected_observation_count <= 0:
        raise SyntheticDataValidationError("Ground truth record counts must be positive.")
    if ground_truth.expected_dataset_score is not None:
        raise SyntheticDataValidationError(
            "Golden structural ground truth cannot define a dataset score."
        )
    if ground_truth.expected_notification or ground_truth.expected_escalation:
        raise SyntheticDataValidationError(
            "Golden structural ground truth cannot expect operational events."
        )
    _validate_aware_time(ground_truth.created_at, "Ground truth creation time")


def _validate_validation_result(
    validation: SyntheticValidationResult,
    ground_truth: SyntheticGroundTruth,
) -> None:
    _validate_ids(
        (
            validation.validation_result_id,
            validation.generation_run_id,
            validation.synthetic_record_id,
            validation.ground_truth_version,
            validation.validation_class,
            validation.actual_output_reference,
            validation.audit_reference,
        ),
        "Synthetic validation result fields",
    )
    if (
        validation.generation_run_id != ground_truth.generation_run_id
        or validation.synthetic_record_id != ground_truth.synthetic_record_id
        or validation.ground_truth_version != ground_truth.ground_truth_version
    ):
        raise SyntheticDataValidationError(
            "Synthetic validation result does not match ground truth lineage."
        )
    if not isinstance(validation.status, SyntheticValidationStatus):
        raise SyntheticDataValidationError("Synthetic validation status is invalid.")
    if any(not code.strip() for code in validation.reason_codes):
        raise SyntheticDataValidationError("Synthetic validation reason codes are invalid.")
    if validation.status is SyntheticValidationStatus.PASS and validation.reason_codes:
        raise SyntheticDataValidationError("Passing validation cannot contain reason codes.")
    if validation.status is not SyntheticValidationStatus.PASS and not validation.reason_codes:
        raise SyntheticDataValidationError("Non-passing validation requires reason codes.")
    if validation.actual_subject_count < 0 or validation.actual_observation_count < 0:
        raise SyntheticDataValidationError("Actual record counts cannot be negative.")
    _validate_aware_time(validation.created_at, "Validation result creation time")


def _validate_run_completion(completion: SyntheticRunCompletion) -> None:
    _validate_ids(
        (
            completion.completion_id,
            completion.generation_run_id,
            completion.output_reference,
            completion.canonical_sha256,
            completion.validation_result_id,
            completion.retention_policy_id,
            completion.audit_reference,
        ),
        "Synthetic run completion fields",
    )
    if completion.status not in {
        SyntheticRunStatus.COMPLETED,
        SyntheticRunStatus.BLOCKED,
        SyntheticRunStatus.TECHNICAL_ERROR,
    }:
        raise SyntheticDataValidationError("Synthetic run completion status is invalid.")
    if not isinstance(completion.validation_status, SyntheticValidationStatus):
        raise SyntheticDataValidationError("Synthetic completion validation status is invalid.")
    expected_status = {
        SyntheticValidationStatus.PASS: SyntheticRunStatus.COMPLETED,
        SyntheticValidationStatus.BLOCKED: SyntheticRunStatus.BLOCKED,
        SyntheticValidationStatus.TECHNICAL_ERROR: SyntheticRunStatus.TECHNICAL_ERROR,
    }[completion.validation_status]
    if completion.status is not expected_status:
        raise SyntheticDataValidationError(
            "Synthetic run and validation terminal statuses do not match."
        )
    if (
        len(completion.canonical_sha256) != 64
        or any(character not in "0123456789abcdef" for character in completion.canonical_sha256)
        or completion.output_reference != f"sha256:{completion.canonical_sha256}"
    ):
        raise SyntheticDataValidationError("Synthetic output digest reference is invalid.")
    if completion.payload_byte_count <= 0:
        raise SyntheticDataValidationError("Synthetic output payload size must be positive.")
    if completion.subject_count < 0 or completion.observation_count < 0:
        raise SyntheticDataValidationError("Synthetic output record counts cannot be negative.")
    _validate_aware_time(completion.created_at, "Run completion time")


def _same_completion_evidence(
    existing: SyntheticRunCompletion,
    candidate: SyntheticRunCompletion,
) -> bool:
    return (
        existing.generation_run_id,
        existing.status,
        existing.output_reference,
        existing.canonical_sha256,
        existing.payload_byte_count,
        existing.subject_count,
        existing.observation_count,
        existing.validation_result_id,
        existing.validation_status,
        existing.retention_policy_id,
    ) == (
        candidate.generation_run_id,
        candidate.status,
        candidate.output_reference,
        candidate.canonical_sha256,
        candidate.payload_byte_count,
        candidate.subject_count,
        candidate.observation_count,
        candidate.validation_result_id,
        candidate.validation_status,
        candidate.retention_policy_id,
    )


def _validate_ids(values: tuple[str, ...], name: str) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise SyntheticDataValidationError(f"{name} are required.")


def _validate_aware_time(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SyntheticDataValidationError(f"{name} must be timezone-aware.")


def _policy_values(policy: SyntheticDatasetPolicy) -> tuple[object, ...]:
    return (
        policy.policy_id,
        policy.dataset_id,
        1 if policy.synthetic_generation_allowed else 0,
        policy.synthetic_profile.value,
        policy.volume_profile,
        policy.distribution_profile,
        policy.missingness_profile,
        policy.defect_injection_profile,
        policy.privacy_profile,
        policy.retention_policy_id,
        1 if policy.ground_truth_enabled else 0,
        policy.seed_strategy,
        str(policy.expected_score_tolerance)
        if policy.expected_score_tolerance is not None
        else None,
        policy.criticality_profile_id,
        1 if policy.notification_test_enabled else 0,
        policy.schema_version,
        policy.policy_version,
        policy.effective_from.isoformat(),
        policy.effective_to.isoformat() if policy.effective_to else None,
        policy.approved_by,
        policy.approval_status.value,
        policy.audit_reference,
        policy.created_at.isoformat(),
    )


def _scenario_values(scenario: SyntheticScenario) -> tuple[object, ...]:
    return (
        scenario.scenario_record_id,
        scenario.scenario_id,
        scenario.dataset_id,
        scenario.scenario_version,
        scenario.schema_version,
        scenario.configuration_version,
        scenario.synthetic_profile.value,
        scenario.volume_profile,
        scenario.distribution_profile,
        scenario.missingness_profile,
        scenario.defect_injection_profile,
        scenario.privacy_profile,
        scenario.created_at.isoformat(),
    )


def _temporal_profile_values(profile: SyntheticTemporalProfile) -> tuple[object, ...]:
    return (
        profile.profile_version,
        profile.base_time.isoformat(),
        profile.period_count,
        profile.period_duration_seconds,
        profile.source_created_delay_seconds,
        profile.source_updated_delay_seconds,
        profile.ingestion_delay_seconds,
        profile.processing_delay_seconds,
        profile.quality_check_delay_seconds,
        profile.created_at.isoformat(),
    )


def _run_values(run: SyntheticGenerationRun) -> tuple[object, ...]:
    return (
        run.generation_run_id,
        run.dataset_id,
        run.scenario_id,
        run.scenario_version,
        run.generator_version,
        run.configuration_version,
        run.schema_version,
        run.policy_version,
        str(run.random_seed),
        run.requested_record_count,
        run.requested_by,
        run.audit_reference,
        run.status.value,
        run.output_reference,
        run.validation_reference,
        run.created_at.isoformat(),
    )


def _ground_truth_values(ground_truth: SyntheticGroundTruth) -> tuple[object, ...]:
    return (
        ground_truth.synthetic_record_id,
        ground_truth.generation_run_id,
        ground_truth.dataset_id,
        ground_truth.scenario_id,
        ground_truth.scenario_version,
        ground_truth.generator_version,
        str(ground_truth.random_seed),
        ground_truth.source_system,
        ground_truth.expected_subject_count,
        ground_truth.expected_observation_count,
        int(ground_truth.expected_primary_keys_unique),
        int(ground_truth.expected_foreign_keys_valid),
        int(ground_truth.expected_status_transitions_valid),
        int(ground_truth.expected_reference_codes_valid),
        int(ground_truth.expected_temporal_order_valid),
        ground_truth.expected_rule_result,
        ground_truth.expected_severity,
        None,
        int(ground_truth.expected_notification),
        int(ground_truth.expected_escalation),
        ground_truth.ground_truth_version,
        ground_truth.audit_reference,
        ground_truth.created_at.isoformat(),
    )


def _validation_result_values(validation: SyntheticValidationResult) -> tuple[object, ...]:
    return (
        validation.validation_result_id,
        validation.generation_run_id,
        validation.synthetic_record_id,
        validation.ground_truth_version,
        validation.validation_class,
        validation.status.value,
        json.dumps(validation.reason_codes, separators=(",", ":")),
        validation.actual_subject_count,
        validation.actual_observation_count,
        int(validation.actual_primary_keys_unique),
        int(validation.actual_foreign_keys_valid),
        int(validation.actual_status_transitions_valid),
        int(validation.actual_reference_codes_valid),
        int(validation.actual_temporal_order_valid),
        validation.actual_output_reference,
        validation.audit_reference,
        validation.created_at.isoformat(),
    )


def _run_completion_values(completion: SyntheticRunCompletion) -> tuple[object, ...]:
    return (
        completion.completion_id,
        completion.generation_run_id,
        completion.status.value,
        completion.output_reference,
        completion.canonical_sha256,
        completion.payload_byte_count,
        completion.subject_count,
        completion.observation_count,
        completion.validation_result_id,
        completion.validation_status.value,
        completion.retention_policy_id,
        completion.audit_reference,
        completion.created_at.isoformat(),
    )


def _row_to_policy(row: sqlite3.Row) -> SyntheticDatasetPolicy:
    return SyntheticDatasetPolicy(
        policy_id=row["policy_id"],
        dataset_id=row["dataset_id"],
        synthetic_generation_allowed=bool(row["synthetic_generation_allowed"]),
        synthetic_profile=SyntheticProfile(row["synthetic_profile"]),
        volume_profile=row["volume_profile"],
        distribution_profile=row["distribution_profile"],
        missingness_profile=row["missingness_profile"],
        defect_injection_profile=row["defect_injection_profile"],
        privacy_profile=row["privacy_profile"],
        retention_policy_id=row["retention_policy_id"],
        ground_truth_enabled=bool(row["ground_truth_enabled"]),
        seed_strategy=row["seed_strategy"],
        expected_score_tolerance=(
            Decimal(row["expected_score_tolerance"])
            if row["expected_score_tolerance"] is not None
            else None
        ),
        criticality_profile_id=row["criticality_profile_id"],
        notification_test_enabled=bool(row["notification_test_enabled"]),
        schema_version=row["schema_version"],
        policy_version=row["policy_version"],
        effective_from=datetime.fromisoformat(row["effective_from"]),
        effective_to=(
            datetime.fromisoformat(row["effective_to"]) if row["effective_to"] is not None else None
        ),
        approved_by=row["approved_by"],
        approval_status=SyntheticPolicyStatus(row["approval_status"]),
        audit_reference=row["audit_reference"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_scenario(row: sqlite3.Row) -> SyntheticScenario:
    return SyntheticScenario(
        scenario_record_id=row["scenario_record_id"],
        scenario_id=row["scenario_id"],
        dataset_id=row["dataset_id"],
        scenario_version=row["scenario_version"],
        schema_version=row["schema_version"],
        configuration_version=row["configuration_version"],
        synthetic_profile=SyntheticProfile(row["synthetic_profile"]),
        volume_profile=row["volume_profile"],
        distribution_profile=row["distribution_profile"],
        missingness_profile=row["missingness_profile"],
        defect_injection_profile=row["defect_injection_profile"],
        privacy_profile=row["privacy_profile"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_temporal_profile(row: sqlite3.Row) -> SyntheticTemporalProfile:
    return SyntheticTemporalProfile(
        profile_version=row["profile_version"],
        base_time=datetime.fromisoformat(row["base_time"]),
        period_count=row["period_count"],
        period_duration_seconds=row["period_duration_seconds"],
        source_created_delay_seconds=row["source_created_delay_seconds"],
        source_updated_delay_seconds=row["source_updated_delay_seconds"],
        ingestion_delay_seconds=row["ingestion_delay_seconds"],
        processing_delay_seconds=row["processing_delay_seconds"],
        quality_check_delay_seconds=row["quality_check_delay_seconds"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_run(row: sqlite3.Row) -> SyntheticGenerationRun:
    return SyntheticGenerationRun(
        generation_run_id=row["generation_run_id"],
        dataset_id=row["dataset_id"],
        scenario_id=row["scenario_id"],
        scenario_version=row["scenario_version"],
        generator_version=row["generator_version"],
        configuration_version=row["configuration_version"],
        schema_version=row["schema_version"],
        policy_version=row["policy_version"],
        random_seed=int(row["random_seed"]),
        requested_record_count=row["requested_record_count"],
        requested_by=row["requested_by"],
        audit_reference=row["audit_reference"],
        status=SyntheticRunStatus(row["status"]),
        output_reference=row["output_reference"],
        validation_reference=row["validation_reference"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_ground_truth(row: sqlite3.Row) -> SyntheticGroundTruth:
    return SyntheticGroundTruth(
        synthetic_record_id=row["synthetic_record_id"],
        generation_run_id=row["generation_run_id"],
        dataset_id=row["dataset_id"],
        scenario_id=row["scenario_id"],
        scenario_version=row["scenario_version"],
        generator_version=row["generator_version"],
        random_seed=int(row["random_seed"]),
        source_system=row["source_system"],
        expected_subject_count=row["expected_subject_count"],
        expected_observation_count=row["expected_observation_count"],
        expected_primary_keys_unique=bool(row["expected_primary_keys_unique"]),
        expected_foreign_keys_valid=bool(row["expected_foreign_keys_valid"]),
        expected_status_transitions_valid=bool(row["expected_status_transitions_valid"]),
        expected_reference_codes_valid=bool(row["expected_reference_codes_valid"]),
        expected_temporal_order_valid=bool(row["expected_temporal_order_valid"]),
        expected_rule_result=row["expected_rule_result"],
        expected_severity=row["expected_severity"],
        expected_dataset_score=(
            Decimal(row["expected_dataset_score"])
            if row["expected_dataset_score"] is not None
            else None
        ),
        expected_notification=bool(row["expected_notification"]),
        expected_escalation=bool(row["expected_escalation"]),
        ground_truth_version=row["ground_truth_version"],
        audit_reference=row["audit_reference"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_validation_result(row: sqlite3.Row) -> SyntheticValidationResult:
    return SyntheticValidationResult(
        validation_result_id=row["validation_result_id"],
        generation_run_id=row["generation_run_id"],
        synthetic_record_id=row["synthetic_record_id"],
        ground_truth_version=row["ground_truth_version"],
        validation_class=row["validation_class"],
        status=SyntheticValidationStatus(row["status"]),
        reason_codes=tuple(json.loads(row["reason_codes"])),
        actual_subject_count=row["actual_subject_count"],
        actual_observation_count=row["actual_observation_count"],
        actual_primary_keys_unique=bool(row["actual_primary_keys_unique"]),
        actual_foreign_keys_valid=bool(row["actual_foreign_keys_valid"]),
        actual_status_transitions_valid=bool(row["actual_status_transitions_valid"]),
        actual_reference_codes_valid=bool(row["actual_reference_codes_valid"]),
        actual_temporal_order_valid=bool(row["actual_temporal_order_valid"]),
        actual_output_reference=row["actual_output_reference"],
        audit_reference=row["audit_reference"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_run_completion(row: sqlite3.Row) -> SyntheticRunCompletion:
    return SyntheticRunCompletion(
        completion_id=row["completion_id"],
        generation_run_id=row["generation_run_id"],
        status=SyntheticRunStatus(row["status"]),
        output_reference=row["output_reference"],
        canonical_sha256=row["canonical_sha256"],
        payload_byte_count=row["payload_byte_count"],
        subject_count=row["subject_count"],
        observation_count=row["observation_count"],
        validation_result_id=row["validation_result_id"],
        validation_status=SyntheticValidationStatus(row["validation_status"]),
        retention_policy_id=row["retention_policy_id"],
        audit_reference=row["audit_reference"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )
