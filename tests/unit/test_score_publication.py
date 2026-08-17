"""DS-06: ScorePublicationService birim testleri.

FR-04.06, FR-04.14, AC-06
Kapsam: tam set kapısı, ineligible/partial/no-data reddi, supersede state-machine,
reproduction mismatch, audit payload minimization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from veri_kalitesi.executions.models import (
    ExecutionStatus,
    MeasurementStatus,
    RuleExecution,
    RuleExecutionResult,
)
from veri_kalitesi.identity import ActorContext, ActorContextIssuer, ActorType
from veri_kalitesi.scoring.errors import (
    ScorePublicationError,
    ScoringConflictError,
    ScoringValidationError,
)
from veri_kalitesi.scoring.models import (
    QualityScore,
    ScoreLevel,
    ScorePublication,
    ScorePublicationStatus,
    ScoreScopeType,
    ScoreStatus,
    ScoringConfiguration,
    ThresholdSet,
)
from veri_kalitesi.scoring.publication import (
    ScorePublicationCommand,
    ScorePublicationService,
    _compute_input_digest,
)


# ── Stubs ────────────────────────────────────────────────────────────

_ACTOR_POLICY = "DASHBOARD_POLICY_V1"


def _actor() -> ActorContext:
    now = datetime(2026, 8, 6, tzinfo=timezone.utc)
    return ActorContextIssuer().issue(
        actor_id="score-worker",
        actor_type=ActorType.SERVICE,
        authentication_source="synthetic-identity-adapter",
        session_id="session-worker",
        roles=frozenset({"SCORE_PUBLICATION_WORKER"}),
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset(),
        can_view_enterprise=True,
        privileged=True,
        issued_at=now - timedelta(minutes=5),
        expires_at=now + timedelta(hours=1),
        policy_version=_ACTOR_POLICY,
        correlation_id="correlation-worker",
    )


def _configuration() -> ScoringConfiguration:
    return ScoringConfiguration(
        version="DEFAULT_SCORING_V1",
        threshold_set=ThresholdSet(version="DEFAULT_THRESHOLDS_V1"),
        dimension_weights={},
        criticality_weights={},
        created_by="system",
        is_active=True,
        created_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
    )


def _result(
    rule_version_id: str = "rv-1",
    passed: int = 90,
    failed: int = 10,
    evaluated: int = 100,
    population: int = 1000,
) -> RuleExecutionResult:
    return RuleExecutionResult(
        execution_id="exec-1",
        rule_version_id=rule_version_id,
        passed_count=passed,
        failed_count=failed,
        evaluated_count=evaluated,
        eligible_count=evaluated,
        population_count=population,
        excluded_count=0,
        technical_error_count=0,
        unknown_count=0,
        measurement_status=MeasurementStatus.PASSED,
        eligible_for_official_scoring=True,
    )


def _score(
    *,
    quality_score_id: str = "qs-1",
    scope_type: ScoreScopeType = ScoreScopeType.RULE,
    scope_id: str | None = "ds-1",
    score_value: Decimal | None = Decimal("90.00"),
    level: ScoreLevel | None = ScoreLevel.GOOD,
    rule_version_id: str | None = "rv-1",
    score_status: ScoreStatus = ScoreStatus.CALCULATED,
) -> QualityScore:
    return QualityScore(
        quality_score_id=quality_score_id,
        execution_id="exec-1",
        rule_result_id=f"rr-{quality_score_id}",
        rule_version_id=rule_version_id,
        scope_type=scope_type,
        scope_id=scope_id,
        score_value=score_value,
        score_status=score_status,
        level=level,
        calculation_details={},
        calculated_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
        rule_version_digest="rv-digest-1",
        policy_version="DEFAULT_SCORING_V1",
    )


@dataclass
class _StubScoringService:
    scores: list[QualityScore] = field(default_factory=list)
    reproduced: QualityScore | None = None

    def calculate_full_score_set(
        self, execution_id: str, *, configuration: Any = None, _persist: bool = True
    ) -> tuple[QualityScore, ...]:
        assert _persist is False
        return tuple(self.scores)

    def reproduce_rule_score(self, **kwargs: Any) -> QualityScore:
        assert self.reproduced is not None
        return self.reproduced


@dataclass
class _StubScoreRepository:
    configuration: ScoringConfiguration | None = None
    existing_publication: ScorePublication | None = None
    published_scores: list[QualityScore] = field(default_factory=list)
    scores_by_id: dict[str, QualityScore] = field(default_factory=dict)
    _stored_publications: list[ScorePublication] = field(default_factory=list)
    _stored_scores: list[tuple[ScorePublication, tuple[QualityScore, ...]]] = field(
        default_factory=list
    )

    def get_active_configuration(self) -> ScoringConfiguration:
        assert self.configuration is not None
        return self.configuration

    def get_publication_by_execution(self, execution_id: str) -> ScorePublication | None:
        return self.existing_publication

    def get(self, quality_score_id: str) -> QualityScore:
        if quality_score_id in self.scores_by_id:
            return self.scores_by_id[quality_score_id]
        from veri_kalitesi.scoring.errors import ScoreNotFoundError

        raise ScoreNotFoundError(f"Not found: {quality_score_id}")

    def get_publication(self, publication_id: str) -> ScorePublication | None:
        return None

    def get_by_publication(self, publication_id: str) -> list[QualityScore]:
        return self.published_scores


@dataclass
class _StubExecutionHistory:
    execution: RuleExecution | None = None
    results: list[RuleExecutionResult] = field(default_factory=list)

    def get(self, execution_id: str) -> RuleExecution:
        assert self.execution is not None
        return self.execution

    def list_results(self, execution_id: str) -> list[RuleExecutionResult]:
        return self.results

    def list_latest_results_for_rule_versions(
        self, rule_version_ids: frozenset[str]
    ) -> dict[str, RuleExecutionResult]:
        return {}


@dataclass
class _StubTransactionalAudit:
    _schema: str = "dq"

    def prepare(self, event: Any) -> Any:
        return event

    def stage(self, prepared: Any, *, session: Any) -> None:
        pass

    def publish_pending(self) -> None:
        pass


def _execution(status: ExecutionStatus = ExecutionStatus.SUCCESS) -> RuleExecution:
    return RuleExecution(
        execution_id="exec-1",
        idempotency_key_hash="key-exec-1",
        payload_hash="payload-exec-1",
        rule_version_ids=("rv-1",),
        scope={"dataset_id": "ds-1"},
        triggered_by="system",
        correlation_id="correlation-exec-1",
        status=status,
        started_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
        finished_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
    )


def _command(**overrides: Any) -> ScorePublicationCommand:
    defaults = dict(
        execution_id="exec-1",
        period="2026-08-06",
        configuration_version="DEFAULT_SCORING_V1",
    )
    defaults.update(overrides)
    return ScorePublicationCommand(**defaults)


# ── Input digest ─────────────────────────────────────────────────────


def test_input_digest_is_deterministic() -> None:
    results = [_result("rv-1"), _result("rv-2")]
    config = _configuration()
    d1 = _compute_input_digest(results, config)
    d2 = _compute_input_digest(results, config)
    assert d1 == d2
    assert d1.startswith("sha256:")


def test_input_digest_changes_with_results() -> None:
    config = _configuration()
    d1 = _compute_input_digest([_result("rv-1", passed=90)], config)
    d2 = _compute_input_digest([_result("rv-1", passed=80)], config)
    assert d1 != d2


# ── Publication gate ─────────────────────────────────────────────────


def test_publish_rejects_non_success_execution() -> None:
    """FR-04.06: Başarısız execution yayımlanamaz."""
    scoring = _StubScoringService()
    repo = _StubScoreRepository(configuration=_configuration())
    history = _StubExecutionHistory(execution=_execution(ExecutionStatus.TECHNICAL_ERROR))
    service = ScorePublicationService(
        scoring_service=scoring,
        score_repository=repo,
        execution_history=history,
        rule_catalog=history,  # type: ignore[arg-type]
        transactional_audit=_StubTransactionalAudit(),
    )
    with pytest.raises(ScorePublicationError, match="not in a scoreable status"):
        service.publish_execution(_command())


def test_publish_rejects_no_official_scores() -> None:
    """Hiçbir resmi skor üretilmezse yayım reddedilir."""
    scoring = _StubScoringService(
        scores=[
            _score(score_value=None, level=None, score_status=ScoreStatus.NOT_CALCULATED),
        ]
    )
    repo = _StubScoreRepository(configuration=_configuration())
    history = _StubExecutionHistory(execution=_execution(), results=[_result()])
    service = ScorePublicationService(
        scoring_service=scoring,
        score_repository=repo,
        execution_history=history,
        rule_catalog=history,  # type: ignore[arg-type]
        transactional_audit=_StubTransactionalAudit(),
    )
    with pytest.raises(ScorePublicationError, match="No official scores"):
        service.publish_execution(_command())


def test_publish_returns_idempotent_hit_for_same_digest() -> None:
    """Aynı digest ile tekrar yayım idempotent hit döner."""
    results = [_result()]
    config = _configuration()
    digest = _compute_input_digest(results, config)
    existing_pub = ScorePublication(
        publication_id="pub-existing",
        execution_id="exec-1",
        period="2026-08-06",
        input_digest=digest,
        status=ScorePublicationStatus.PUBLISHED,
        policy_version="DEFAULT_SCORING_V1",
        published_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
    )
    scoring = _StubScoringService()
    repo = _StubScoreRepository(
        configuration=config,
        existing_publication=existing_pub,
        published_scores=[_score()],
    )
    history = _StubExecutionHistory(execution=_execution(), results=results)
    service = ScorePublicationService(
        scoring_service=scoring,
        score_repository=repo,
        execution_history=history,
        rule_catalog=history,  # type: ignore[arg-type]
        transactional_audit=_StubTransactionalAudit(),
    )
    result = service.publish_execution(_command())
    assert result.is_idempotent_hit is True
    assert result.publication.publication_id == "pub-existing"


def test_publish_raises_conflict_for_different_digest() -> None:
    """Farklı digest ile tekrar yayım conflict fırlatır."""
    existing_pub = ScorePublication(
        publication_id="pub-existing",
        execution_id="exec-1",
        period="2026-08-06",
        input_digest="sha256:different",
        status=ScorePublicationStatus.PUBLISHED,
        policy_version="DEFAULT_SCORING_V1",
        published_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
    )
    scoring = _StubScoringService()
    repo = _StubScoreRepository(
        configuration=_configuration(),
        existing_publication=existing_pub,
    )
    history = _StubExecutionHistory(execution=_execution(), results=[_result()])
    service = ScorePublicationService(
        scoring_service=scoring,
        score_repository=repo,
        execution_history=history,
        rule_catalog=history,  # type: ignore[arg-type]
        transactional_audit=_StubTransactionalAudit(),
    )
    with pytest.raises(ScoringConflictError, match="different input digest"):
        service.publish_execution(_command())


# ── Reproduction ─────────────────────────────────────────────────────


def test_reproduce_matches_original() -> None:
    """Reproduction orijinal ile eşleşirse matches=True."""
    original = _score(
        quality_score_id="qs-orig",
        score_value=Decimal("90.00"),
        level=ScoreLevel.GOOD,
    )
    reproduced = _score(
        quality_score_id="qs-reproduced",
        score_value=Decimal("90.00"),
        level=ScoreLevel.GOOD,
    )
    scoring = _StubScoringService(reproduced=reproduced)
    repo = _StubScoreRepository(
        configuration=_configuration(),
        scores_by_id={"qs-orig": original},
    )
    history = _StubExecutionHistory(execution=_execution(), results=[_result()])

    @dataclass
    class _StubRuleCatalog:
        def get_version(self, rule_version_id: str) -> str:
            return rule_version_id

        def list_rules_with_latest_version(self, dataset_ids: frozenset[str]) -> list:
            return []

    service = ScorePublicationService(
        scoring_service=scoring,
        score_repository=repo,
        execution_history=history,
        rule_catalog=_StubRuleCatalog(),  # type: ignore[arg-type]
        transactional_audit=_StubTransactionalAudit(),
    )
    result = service.reproduce_score("qs-orig")
    assert result.matches is True
    assert result.delta_value is None
    assert result.reason_codes == ()


def test_reproduce_detects_value_mismatch() -> None:
    """Skor değeri farklıysa matches=False ve delta hesaplanır."""
    original = _score(
        quality_score_id="qs-orig",
        score_value=Decimal("90.00"),
        level=ScoreLevel.GOOD,
    )
    reproduced = _score(
        quality_score_id="qs-reproduced",
        score_value=Decimal("85.00"),
        level=ScoreLevel.RISKY,
    )
    scoring = _StubScoringService(reproduced=reproduced)
    repo = _StubScoreRepository(
        configuration=_configuration(),
        scores_by_id={"qs-orig": original},
    )
    history = _StubExecutionHistory(execution=_execution(), results=[_result()])

    @dataclass
    class _StubRuleCatalog:
        def get_version(self, rule_version_id: str) -> str:
            return rule_version_id

        def list_rules_with_latest_version(self, dataset_ids: frozenset[str]) -> list:
            return []

    service = ScorePublicationService(
        scoring_service=scoring,
        score_repository=repo,
        execution_history=history,
        rule_catalog=_StubRuleCatalog(),  # type: ignore[arg-type]
        transactional_audit=_StubTransactionalAudit(),
    )
    result = service.reproduce_score("qs-orig")
    assert result.matches is False
    assert "SCORE_VALUE_MISMATCH" in result.reason_codes
    assert "LEVEL_MISMATCH" in result.reason_codes
    assert result.delta_value == Decimal("-5.00")
    assert result.delta_level is True


def test_reproduce_rejects_non_rule_score() -> None:
    """Rule-level olmayan skor yeniden üretilemez."""
    original = _score(
        quality_score_id="qs-agg",
        scope_type=ScoreScopeType.ENTERPRISE,
        scope_id=None,
        rule_version_id=None,
    )
    repo = _StubScoreRepository(
        configuration=_configuration(),
        scores_by_id={"qs-agg": original},
    )
    history = _StubExecutionHistory(execution=_execution())
    scoring = _StubScoringService()
    service = ScorePublicationService(
        scoring_service=scoring,
        score_repository=repo,
        execution_history=history,
        rule_catalog=history,  # type: ignore[arg-type]
        transactional_audit=_StubTransactionalAudit(),
    )
    with pytest.raises(ScoringValidationError, match="Only rule-level"):
        service.reproduce_score("qs-agg")
