"""DS-06: SCORE_PUBLICATION job payload, idempotency ve handler testleri.

FR-04.05, FR-04.06, AC-06
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Event
from typing import Any

import pytest

from veri_kalitesi.jobs.models import BackgroundJob, JobCompletionOutcome
from veri_kalitesi.jobs.worker import PermanentJobError
from veri_kalitesi.scoring.jobs import (
    ScorePublicationJobHandler,
    ScorePublicationJobPayload,
    canonical_period,
    score_publication_idempotency_key,
)
from veri_kalitesi.scoring.publication import (
    ScorePublicationCommand,
    ScorePublicationResult,
)
from veri_kalitesi.scoring.models import ScorePublication, ScorePublicationStatus


# ── Payload ──────────────────────────────────────────────────────────


def test_payload_round_trip() -> None:
    """FR-04.05: Payload dict↔model dönüşümünde veri kaybı olmaz."""
    payload = ScorePublicationJobPayload(
        execution_id="exec-1",
        period="2026-08-06",
        configuration_version="DEFAULT_SCORING_V1",
    )
    data = payload.to_dict()
    restored = ScorePublicationJobPayload.from_dict(data)
    assert restored == payload


def test_payload_rejects_blank_execution_id() -> None:
    """FR-04.05: Boş execution_id kalıcı hata fırlatır."""
    with pytest.raises(PermanentJobError, match="INVALID_SCORE_PUBLICATION_JOB_PAYLOAD"):
        ScorePublicationJobPayload.from_dict(
            {"execution_id": "", "period": "2026-08-06", "configuration_version": "V1"}
        )


def test_payload_rejects_missing_period() -> None:
    with pytest.raises(PermanentJobError, match="INVALID_SCORE_PUBLICATION_JOB_PAYLOAD"):
        ScorePublicationJobPayload.from_dict(
            {"execution_id": "exec-1", "period": "", "configuration_version": "V1"}
        )


def test_payload_rejects_blank_configuration_version() -> None:
    with pytest.raises(PermanentJobError, match="INVALID_SCORE_PUBLICATION_JOB_PAYLOAD"):
        ScorePublicationJobPayload.from_dict(
            {"execution_id": "exec-1", "period": "2026-08-06", "configuration_version": "  "}
        )


# ── Idempotency key ─────────────────────────────────────────────────


def test_idempotency_key_is_deterministic() -> None:
    """AC-06: Aynı execution_id için aynı key üretilir."""
    assert score_publication_idempotency_key("exec-1") == score_publication_idempotency_key(
        "exec-1"
    )


def test_idempotency_key_differs_per_execution() -> None:
    assert score_publication_idempotency_key("exec-1") != score_publication_idempotency_key(
        "exec-2"
    )


def test_idempotency_key_has_score_pub_prefix() -> None:
    key = score_publication_idempotency_key("exec-42")
    assert key.startswith("score-pub:")
    assert "exec-42" in key


# ── Canonical period ────────────────────────────────────────────────


def test_canonical_period_uses_utc_date() -> None:
    at = datetime(2026, 8, 6, 23, 59, 59, tzinfo=timezone.utc)
    assert canonical_period(at) == "2026-08-06"


def test_canonical_period_default_is_not_empty() -> None:
    assert len(canonical_period()) == 10  # YYYY-MM-DD


# ── Handler ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _StubPublicationService:
    """publish_execution çağrısını kaydeden stub."""

    result: ScorePublicationResult | None = None
    error: Exception | None = None

    def publish_execution(
        self, command: ScorePublicationCommand, *, actor_context: Any = None
    ) -> ScorePublicationResult:
        if self.error is not None:
            raise self.error
        return self.result  # type: ignore[return-value]


def _job(payload: dict[str, str]) -> BackgroundJob:
    now = datetime(2026, 8, 6, tzinfo=timezone.utc)
    return BackgroundJob(
        job_id="score-pub-job",
        job_type="SCORE_PUBLICATION",
        payload=payload,
        created_at=now,
        updated_at=now,
        available_at=now,
    )


def _handler_kwargs() -> dict[str, Any]:
    return {
        "connection_timeout_seconds": 30,
        "query_timeout_seconds": 60,
        "total_timeout_seconds": 120,
        "cancellation_event": Event(),
    }


def test_handler_delegates_to_publication_service() -> None:
    """FR-04.06: Handler, job payload'ı ScorePublicationCommand'a çevirir."""
    publication = ScorePublication(
        publication_id="pub-1",
        execution_id="exec-1",
        period="2026-08-06",
        input_digest="sha256:abc",
        status=ScorePublicationStatus.PUBLISHED,
        policy_version="DEFAULT_SCORING_V1",
        published_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
    )
    result = ScorePublicationResult(publication=publication, scores=())
    stub = _StubPublicationService(result=result)
    handler = ScorePublicationJobHandler(publication_service=stub)  # type: ignore[arg-type]
    outcome = handler(
        _job(
            ScorePublicationJobPayload(
                execution_id="exec-1",
                period="2026-08-06",
                configuration_version="DEFAULT_SCORING_V1",
            ).to_dict()
        ),
        **_handler_kwargs(),
    )
    assert outcome is JobCompletionOutcome.SUCCESS


def test_handler_wraps_unexpected_error_as_permanent() -> None:
    """FR-04.06: Beklenmeyen hata PermanentJobError'a sarılır."""
    stub = _StubPublicationService(error=RuntimeError("db connection lost"))
    handler = ScorePublicationJobHandler(publication_service=stub)  # type: ignore[arg-type]
    with pytest.raises(PermanentJobError, match="SCORE_PUBLICATION_FAILED"):
        handler(
            _job({"execution_id": "exec-1", "period": "2026-08-06", "configuration_version": "V1"}),
            **_handler_kwargs(),
        )


def test_handler_propagates_permanent_job_error() -> None:
    """PermanentJobError doğrudan yayılır — çift sarma yapılmaz."""
    stub = _StubPublicationService(error=PermanentJobError("INVALID_PAYLOAD"))
    handler = ScorePublicationJobHandler(publication_service=stub)  # type: ignore[arg-type]
    with pytest.raises(PermanentJobError, match="INVALID_PAYLOAD"):
        handler(
            _job({"execution_id": "exec-1", "period": "2026-08-06", "configuration_version": "V1"}),
            **_handler_kwargs(),
        )
