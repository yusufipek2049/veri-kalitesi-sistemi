"""Atomik skor yayım servisi — publication, supersede ve reproduction."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, insert, select, update

from veri_kalitesi.audit.models import (
    AuditEventInput,
    AuditResult,
)
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.executions.models import (
    ExecutionStatus,
    RuleExecutionResult,
)
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.persistence import transactional_session
from veri_kalitesi.scoring.contributions import contribution_graph
from veri_kalitesi.scoring.postgresql_contributions import contribution_graph_table
from veri_kalitesi.scoring.errors import (
    ScorePublicationError,
    ScoreReproductionError,
    ScoringConflictError,
    ScoringValidationError,
)
from veri_kalitesi.scoring.models import (
    QualityScore,
    ScorePublication,
    ScorePublicationStatus,
    ScoreScopeType,
    ScoringConfiguration,
    is_official_score,
    utc_now,
)
from veri_kalitesi.scoring.postgresql_repository import (
    PostgreSQLScoreRepository,
    score_tables,
)
from veri_kalitesi.scoring.service import (
    ExecutionHistory,
    RuleCatalog,
    ScoringService,
    SourceCatalog,
)


@dataclass(frozen=True)
class ScorePublicationCommand:
    """Yayım komutu — execution_id ve period ile tetiklenir."""

    execution_id: str
    period: str
    configuration_version: str
    idempotency_key: str | None = None


@dataclass(frozen=True)
class ScorePublicationResult:
    """Yayım sonucu — publication ve score set."""

    publication: ScorePublication
    scores: tuple[QualityScore, ...]
    is_idempotent_hit: bool = False


@dataclass(frozen=True)
class ScoreReproductionResult:
    """Yeniden üretim doğrulama sonucu."""

    original_score_id: str
    reproduced_score: QualityScore
    matches: bool
    delta_value: Decimal | None = None
    delta_level: bool = False
    reason_codes: tuple[str, ...] = ()


class ScorePublicationService:
    """Tam skor setini hesaplar ve atomik PostgreSQL yayımı yapar.

    Tek transaction'da:
      1. score_publications PUBLISHED
      2. quality_scores (tüm seviyeler)
      3. score_contribution_graphs
      4. audit outbox (RULE_SCORE_CALCULATED, SCORE_AGGREGATED, SCORE_PUBLISHED)
      5. Önceki yayın SUPERSEDED
    """

    def __init__(
        self,
        scoring_service: ScoringService,
        score_repository: PostgreSQLScoreRepository,
        execution_history: ExecutionHistory,
        rule_catalog: RuleCatalog,
        *,
        source_catalog: SourceCatalog | None = None,
        transactional_audit: PostgreSQLTransactionalAudit,
        clock: Any = utc_now,
    ) -> None:
        self.scoring_service = scoring_service
        self.score_repository = score_repository
        self.execution_history = execution_history
        self.rule_catalog = rule_catalog
        self.source_catalog = source_catalog
        self.transactional_audit = transactional_audit
        self.clock = clock

    def publish_execution(
        self,
        command: ScorePublicationCommand,
        *,
        actor_context: ActorContext | None = None,
    ) -> ScorePublicationResult:
        execution = self.execution_history.get(command.execution_id)
        if execution.status not in (
            ExecutionStatus.SUCCESS,
            ExecutionStatus.PARTIAL,
        ):
            raise ScorePublicationError(
                f"Execution {command.execution_id} is not in a scoreable status:"
                f" {execution.status.value}"
            )
        results = self.execution_history.list_results(command.execution_id)
        configuration = self.score_repository.get_active_configuration()
        input_digest = _compute_input_digest(results, configuration)
        existing = self.score_repository.get_publication_by_execution(command.execution_id)
        if existing is not None:
            if existing.input_digest == input_digest:
                scores = self.score_repository.get_by_publication(existing.publication_id)
                return ScorePublicationResult(
                    publication=existing,
                    scores=tuple(scores),
                    is_idempotent_hit=True,
                )
            raise ScoringConflictError(
                f"Execution {command.execution_id} already published with different input digest."
            )
        all_scores = self.scoring_service.calculate_full_score_set(
            command.execution_id,
            configuration=configuration,
            _persist=False,
        )
        official_scores = tuple(s for s in all_scores if is_official_score(s))
        if not official_scores:
            raise ScorePublicationError("No official scores produced; publication is not allowed.")
        now = self.clock()
        publication_id = str(uuid4())
        publication = ScorePublication(
            publication_id=publication_id,
            execution_id=command.execution_id,
            period=command.period,
            input_digest=input_digest,
            status=ScorePublicationStatus.PUBLISHED,
            policy_version=configuration.version,
            published_at=now,
        )
        scores_with_publication = tuple(
            QualityScore(
                quality_score_id=s.quality_score_id,
                execution_id=s.execution_id,
                rule_result_id=s.rule_result_id,
                rule_version_id=s.rule_version_id,
                scope_type=s.scope_type,
                scope_id=s.scope_id,
                score_value=s.score_value,
                score_status=s.score_status,
                measurement_status=s.measurement_status,
                level=s.level,
                calculation_details=s.calculation_details,
                calculated_at=s.calculated_at,
                publication_id=(publication_id if s.score_value is not None else None),
                rule_version_digest=s.rule_version_digest,
                policy_version=configuration.version,
                included_component_count=s.included_component_count,
                excluded_component_count=s.excluded_component_count,
            )
            for s in all_scores
        )
        audit_events = _build_publication_audit_events(
            publication=publication,
            scores=scores_with_publication,
            actor_context=actor_context,
            clock=self.clock,
        )
        self._atomic_publish(
            publication=publication,
            scores=scores_with_publication,
            audit_events=audit_events,
        )
        return ScorePublicationResult(
            publication=publication,
            scores=scores_with_publication,
        )

    def reproduce_score(
        self,
        quality_score_id: str,
    ) -> ScoreReproductionResult:
        original = self.score_repository.get(quality_score_id)
        if original.rule_version_id is None:
            raise ScoringValidationError("Only rule-level scores can be reproduced directly.")
        execution = self.execution_history.get(original.execution_id)
        results = self.execution_history.list_results(original.execution_id)
        result = next(
            (r for r in results if r.rule_version_id == original.rule_version_id),
            None,
        )
        if result is None:
            raise ScoreReproductionError("Rule result not found for reproduction.")
        configuration = self.score_repository.get_active_configuration()
        version = self.rule_catalog.get_version(original.rule_version_id)
        reproduced = self.scoring_service.reproduce_rule_score(
            execution=execution,
            version=version,
            result=result,
            configuration=configuration,
        )
        matches = True
        reason_codes: list[str] = []
        delta_value = None
        delta_level = False
        if reproduced.score_value != original.score_value:
            matches = False
            reason_codes.append("SCORE_VALUE_MISMATCH")
            if reproduced.score_value is not None and original.score_value is not None:
                delta_value = reproduced.score_value - original.score_value
        if reproduced.level != original.level:
            matches = False
            reason_codes.append("LEVEL_MISMATCH")
            delta_level = True
        if reproduced.score_status != original.score_status:
            matches = False
            reason_codes.append("STATUS_MISMATCH")
        return ScoreReproductionResult(
            original_score_id=quality_score_id,
            reproduced_score=reproduced,
            matches=matches,
            delta_value=delta_value,
            delta_level=delta_level,
            reason_codes=tuple(reason_codes),
        )

    def _atomic_publish(
        self,
        *,
        publication: ScorePublication,
        scores: tuple[QualityScore, ...],
        audit_events: list[AuditEventInput],
    ) -> None:
        tables = score_tables(self._schema())
        prepared_events = [self.transactional_audit.prepare(event) for event in audit_events]
        with transactional_session(self._session_factory()) as session:
            existing_pub = (
                session.execute(
                    select(tables.score_publications).where(
                        and_(
                            tables.score_publications.c.period == publication.period,
                            tables.score_publications.c.status
                            == ScorePublicationStatus.PUBLISHED.value,
                        )
                    )
                )
                .mappings()
                .one_or_none()
            )
            if existing_pub is not None:
                session.execute(
                    update(tables.score_publications)
                    .where(
                        tables.score_publications.c.publication_id == existing_pub["publication_id"]
                    )
                    .values(
                        status=ScorePublicationStatus.SUPERSEDED.value,
                        superseded_at=publication.published_at,
                    )
                )
                session.execute(
                    update(tables.quality_scores)
                    .where(tables.quality_scores.c.publication_id == existing_pub["publication_id"])
                    .values(publication_id=None)
                )
            session.execute(
                insert(tables.score_publications).values(
                    publication_id=publication.publication_id,
                    execution_id=publication.execution_id,
                    period=publication.period,
                    input_digest=publication.input_digest,
                    status=publication.status.value,
                    policy_version=publication.policy_version,
                    published_at=publication.published_at,
                    superseded_at=publication.superseded_at,
                )
            )
            for score in scores:
                if score.score_value is None:
                    continue
                session.execute(
                    insert(tables.quality_scores).values(
                        quality_score_id=score.quality_score_id,
                        publication_id=score.publication_id,
                        execution_id=score.execution_id,
                        rule_result_id=score.rule_result_id,
                        rule_version_id=score.rule_version_id,
                        scope_type=score.scope_type.value,
                        scope_id=score.scope_id,
                        score_value=score.score_value,
                        score_status=score.score_status.value,
                        measurement_status=(
                            score.measurement_status.value if score.measurement_status else None
                        ),
                        level=score.level.value if score.level else None,
                        rule_version_digest=score.rule_version_digest,
                        policy_version=score.policy_version or "",
                        included_component_count=score.included_component_count,
                        excluded_component_count=score.excluded_component_count,
                        calculation_details=_thaw_dict(score.calculation_details),
                        calculated_at=score.calculated_at,
                    )
                )
                graph = contribution_graph(score)
                graph_table = contribution_graph_table(self._schema())
                session.execute(
                    insert(graph_table).values(
                        quality_score_id=score.quality_score_id,
                        execution_id=score.execution_id,
                        scope_type=score.scope_type.value,
                        scope_id=score.scope_id,
                        graph=dict(graph),
                        created_at=score.calculated_at,
                    )
                )
            for prepared_event in prepared_events:
                self.transactional_audit.stage(prepared_event, session=session)
        self.transactional_audit.publish_pending()

    def _session_factory(self):
        return self.score_repository._session_factory

    def _schema(self) -> str:
        return self.score_repository._tables.quality_scores.schema or "dq"


def _compute_input_digest(
    results: list[RuleExecutionResult],
    configuration: ScoringConfiguration,
) -> str:
    canonical = json.dumps(
        {
            "results": sorted(
                [
                    {
                        "rule_version_id": r.rule_version_id,
                        "passed": r.passed_count,
                        "failed": r.failed_count,
                        "evaluated": r.evaluated_count,
                        "population": r.population_count,
                        "measurement": (
                            r.measurement_status.value if r.measurement_status else None
                        ),
                    }
                    for r in results
                ],
                key=lambda r: r["rule_version_id"],
            ),
            "config_version": configuration.version,
        },
        sort_keys=True,
    )
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


def _build_publication_audit_events(
    *,
    publication: ScorePublication,
    scores: tuple[QualityScore, ...],
    actor_context: ActorContext | None,
    clock: Any,
) -> list[AuditEventInput]:
    events: list[AuditEventInput] = []
    now = clock()
    actor_id = actor_context.actor_id if actor_context else "system"
    actor_type = actor_context.actor_type.value if actor_context else "SERVICE"
    correlation_id = actor_context.correlation_id if actor_context else str(uuid4())
    session_id = actor_context.session_id if actor_context else None
    rule_scores = [s for s in scores if s.scope_type is ScoreScopeType.RULE]
    for score in rule_scores:
        events.append(
            AuditEventInput(
                actor_id=actor_id,
                actor_type=actor_type,
                correlation_id=correlation_id,
                action="RULE_SCORE_CALCULATED",
                object_type="QualityScore",
                object_id=score.quality_score_id,
                result=AuditResult.SUCCESS,
                reason_code="RULE_SCORE_CALCULATED",
                old_values={},
                new_values={
                    "execution_id": score.execution_id,
                    "scope_type": score.scope_type.value,
                    "scope_id": score.scope_id or "",
                    "score_status": score.score_status.value,
                    "score_value": str(score.score_value) if score.score_value else None,
                    "level": score.level.value if score.level else None,
                    "policy_version": score.policy_version or "",
                },
                occurred_at=now,
                session_id=session_id,
            )
        )
    agg_scores = [
        s
        for s in scores
        if s.scope_type
        in (
            ScoreScopeType.DATASET,
            ScoreScopeType.DIMENSION,
            ScoreScopeType.SOURCE,
            ScoreScopeType.ENTERPRISE,
        )
    ]
    for score in agg_scores:
        events.append(
            AuditEventInput(
                actor_id=actor_id,
                actor_type=actor_type,
                correlation_id=correlation_id,
                action="SCORE_AGGREGATED",
                object_type="QualityScore",
                object_id=score.quality_score_id,
                result=AuditResult.SUCCESS,
                reason_code="SCORE_AGGREGATED",
                old_values={},
                new_values={
                    "execution_id": score.execution_id,
                    "scope_type": score.scope_type.value,
                    "scope_id": score.scope_id or "",
                    "score_status": score.score_status.value,
                    "score_value": str(score.score_value) if score.score_value else None,
                    "level": score.level.value if score.level else None,
                    "policy_version": score.policy_version or "",
                },
                occurred_at=now,
                session_id=session_id,
            )
        )
    events.append(
        AuditEventInput(
            actor_id=actor_id,
            actor_type=actor_type,
            correlation_id=correlation_id,
            action="SCORE_PUBLISHED",
            object_type="ScorePublication",
            object_id=publication.publication_id,
            result=AuditResult.SUCCESS,
            reason_code="SCORE_PUBLISHED",
            old_values={},
            new_values={
                "execution_id": publication.execution_id,
                "period": publication.period,
                "status": publication.status.value,
                "policy_version": publication.policy_version,
                "score_count": str(len(scores)),
            },
            occurred_at=now,
            session_id=session_id,
        )
    )
    return events


def _thaw_dict(value: Any) -> Any:
    if hasattr(value, "keys"):
        return {k: _thaw_dict(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw_dict(item) for item in value]
    return value
