"""PostgreSQL gerektirmeyen iş kuyruğu domain testleri."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from veri_kalitesi.jobs import (
    BackgroundJob,
    JobLeasePolicy,
    JobStatus,
    JobValidationError,
    job_tables,
)


NOW = datetime(2026, 7, 28, 9, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "payload",
    [
        {"password": "value-that-must-not-leak"},
        {"nested": {"access_token": "value-that-must-not-leak"}},
        {"reference": "token=value-that-must-not-leak"},
        {"items": [{"private_key_path": "value-that-must-not-leak"}]},
    ],
)
def test_payload_rejects_sensitive_keys_and_text_without_leaking_value(
    payload: dict[str, object],
) -> None:
    secret_value = "value-that-must-not-leak"

    with pytest.raises(JobValidationError) as captured:
        BackgroundJob(job_type="EXECUTION", payload=payload, available_at=NOW)

    assert secret_value not in str(captured.value)
    assert "payload" in str(captured.value)


def test_background_job_validates_fields_and_freezes_payload() -> None:
    payload = {"execution_ref": "execution-001"}
    job = BackgroundJob(
        job_type="EXECUTION",
        payload=payload,
        priority=3,
        available_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )
    payload["execution_ref"] = "changed"

    assert job.payload == {"execution_ref": "execution-001"}
    with pytest.raises(TypeError):
        job.payload["new"] = "value"  # type: ignore[index]
    with pytest.raises(JobValidationError, match="priority"):
        BackgroundJob(job_type="EXECUTION", payload={}, priority=-1, available_at=NOW)
    with pytest.raises(JobValidationError, match="timezone-aware"):
        BackgroundJob(
            job_type="EXECUTION",
            payload={},
            available_at=datetime(2026, 7, 28, 9, 0),
        )


def test_background_job_detaches_nested_dictionary_mutations() -> None:
    nested = {"execution": {"reference": "execution-001"}}
    job = BackgroundJob(job_type="EXECUTION", payload=nested, available_at=NOW)

    nested["execution"]["reference"] = "changed"
    nested["execution"]["password"] = "must-not-reach-job"

    assert job.payload["execution"] == {"reference": "execution-001"}
    with pytest.raises(TypeError):
        job.payload["execution"]["reference"] = "changed-through-job"  # type: ignore[index]


def test_background_job_detaches_nested_list_mutations() -> None:
    items = [{"reference": "report-001"}]
    payload = {"items": items}
    job = BackgroundJob(job_type="REPORT", payload=payload, available_at=NOW)

    items[0]["reference"] = "changed"
    items[0]["access_token"] = "must-not-reach-job"
    items.append({"reference": "report-002"})

    assert job.payload["items"] == ({"reference": "report-001"},)
    with pytest.raises(AttributeError):
        job.payload["items"].append({"reference": "report-003"})  # type: ignore[union-attr]


def test_lease_duration_is_configurable_and_positive() -> None:
    policy = JobLeasePolicy(duration=timedelta(seconds=37))

    assert policy.duration == timedelta(seconds=37)
    with pytest.raises(JobValidationError, match="positive"):
        JobLeasePolicy(duration=timedelta(0))


def test_claim_sort_key_is_deterministic() -> None:
    created_at = NOW - timedelta(minutes=2)
    job = BackgroundJob(
        job_id="job-002",
        job_type="REPORT",
        payload={"report_ref": "report-001"},
        priority=9,
        available_at=NOW - timedelta(minutes=1),
        created_at=created_at,
        updated_at=created_at,
    )

    assert job.claim_sort_key() == (
        -9,
        NOW - timedelta(minutes=1),
        created_at,
        "job-002",
    )


def test_status_vocabulary_matches_canonical_names() -> None:
    assert {status.value for status in JobStatus} == {
        "QUEUED",
        "RUNNING",
        "SUCCESS",
        "TECHNICAL_ERROR",
        "TIMEOUT",
        "CANCELLED",
    }


def test_table_contract_defines_constraints_and_indexes() -> None:
    table = job_tables().background_jobs

    assert {constraint.name for constraint in table.constraints} >= {
        "uq_background_jobs_type_idempotency",
        "ck_background_jobs_status",
        "ck_background_jobs_priority",
        "ck_background_jobs_attempt_count",
        "ck_background_jobs_version",
    }
    assert {index.name for index in table.indexes} == {
        "ix_dq_background_jobs_claim",
        "ix_dq_background_jobs_lease",
        "ix_dq_background_jobs_job_type",
    }
