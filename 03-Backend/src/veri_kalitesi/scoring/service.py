"""Execution sonuçlarından deterministik resmi kural skoru üretimi."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Any, Mapping, Protocol

from veri_kalitesi.audit import AuditEventInput, AuditResult, SQLiteTransactionalAudit
from veri_kalitesi.data_sources.models import Criticality, Dataset
from veri_kalitesi.executions.models import (
    ExecutionStatus,
    RuleExecution,
    RuleExecutionResult,
)
from veri_kalitesi.identity import ActorContext, is_trusted_actor_context
from veri_kalitesi.rules.models import QualityDimension, QualityRule, RuleVersion
from veri_kalitesi.scoring.errors import (
    ScoringAuthorizationError,
    ScoringValidationError,
)
from veri_kalitesi.scoring.models import (
    QualityScore,
    ScoreLevel,
    ScoreScopeType,
    ScoreStatus,
    ScoringApprovalPolicy,
    ScoringApprovalStatus,
    ScoringConfiguration,
    ScoringConfigurationApproval,
    ThresholdSet,
    default_criticality_weights,
    default_dimension_weights,
    utc_now,
)
from veri_kalitesi.scoring.repository import SQLiteScoreRepository


FORMULA_VERSION = "RULE_SCORE_V1"
DATASET_FORMULA_VERSION = "DATASET_WEIGHTED_V1"
DIMENSION_FORMULA_VERSION = "DIMENSION_WEIGHTED_V1"
SOURCE_FORMULA_VERSION = "SOURCE_WEIGHTED_V1"
ENTERPRISE_FORMULA_VERSION = "ENTERPRISE_EQUAL_WEIGHT_V1"
_TWO_PLACES = Decimal("0.01")


class ExecutionHistory(Protocol):
    def get(self, execution_id: str) -> RuleExecution: ...

    def list_results(self, execution_id: str) -> list[RuleExecutionResult]: ...


class RuleCatalog(Protocol):
    def get_version(self, rule_version_id: str) -> RuleVersion: ...

    def get_rule(self, quality_rule_id: str) -> QualityRule: ...


class SourceCatalog(Protocol):
    def get_dataset(self, dataset_id: str) -> Dataset: ...


class ScoringConfigurationService:
    def __init__(
        self,
        repository: SQLiteScoreRepository,
        *,
        transactional_audit: SQLiteTransactionalAudit,
        approval_policy: ScoringApprovalPolicy,
        clock: Any = utc_now,
    ) -> None:
        self.repository = repository
        self.transactional_audit = transactional_audit
        self.approval_policy = approval_policy
        self.clock = clock
        _validate_scoring_approval_policy(approval_policy)

    def create_and_submit(
        self,
        *,
        actor_context: ActorContext | None,
        version: str,
        threshold_set: ThresholdSet,
        dimension_weights: Mapping[QualityDimension, Decimal],
        criticality_weights: Mapping[Criticality, Decimal] | None = None,
    ) -> tuple[ScoringConfiguration, ScoringConfigurationApproval]:
        now = self.clock()
        _validate_aware_time(now)
        context = self._authorize_actor(
            actor_context,
            required_roles=self.approval_policy.maker_roles,
            now=now,
        )
        configuration = ScoringConfiguration(
            version=version,
            threshold_set=threshold_set,
            dimension_weights=dimension_weights,
            criticality_weights=(
                criticality_weights
                if criticality_weights is not None
                else default_criticality_weights()
            ),
            created_by=context.actor_id,
            created_at=now,
        )
        validate_scoring_configuration(configuration)
        approval = ScoringConfigurationApproval(
            configuration_id=configuration.configuration_id,
            maker_actor_id=context.actor_id,
            policy_version=self.approval_policy.version,
            requested_at=now,
        )
        previous = self.repository.get_active_configuration()
        new_values = _configuration_audit_values(configuration)
        new_values.update(
            {
                "approval_id": approval.approval_id,
                "policy_version": approval.policy_version,
                "status": approval.status.value,
            }
        )
        event = AuditEventInput(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            correlation_id=context.correlation_id,
            action="SCORING_CONFIGURATION_APPROVAL_REQUESTED",
            object_type="ScoringConfiguration",
            object_id=configuration.configuration_id,
            result=AuditResult.SUCCESS,
            reason_code="SCORING_CONFIGURATION_APPROVAL_REQUESTED",
            old_values=_configuration_audit_values(previous),
            new_values=new_values,
            occurred_at=now,
            session_id=context.session_id,
        )
        stored = self.repository.add_configuration_with_approval(
            configuration,
            approval,
            audit_event=self.transactional_audit.prepare(event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return stored

    def decide_configuration_approval(
        self,
        *,
        actor_context: ActorContext | None,
        approval_id: str,
        decision: str,
        reason_code: str,
    ) -> tuple[ScoringConfiguration, ScoringConfigurationApproval]:
        now = self.clock()
        _validate_aware_time(now)
        context = self._authorize_actor(
            actor_context,
            required_roles=self.approval_policy.checker_roles,
            now=now,
        )
        approval = self.repository.get_configuration_approval(approval_id)
        configuration = self.repository.get_configuration_by_id(approval.configuration_id)
        if approval.status is not ScoringApprovalStatus.PENDING:
            raise ScoringValidationError("Scoring configuration approval is not pending.")
        if approval.policy_version != self.approval_policy.version:
            raise ScoringValidationError("Scoring approval policy version changed.")
        if approval.maker_actor_id == context.actor_id:
            raise ScoringAuthorizationError(
                "Maker cannot approve or reject the same scoring configuration."
            )
        if configuration.created_by == context.actor_id:
            raise ScoringAuthorizationError(
                "Scoring configuration preparer cannot decide the same change."
            )
        latest = self.repository.get_latest_configuration()
        if latest.configuration_id != configuration.configuration_id:
            raise ScoringValidationError(
                "Approval does not target the latest scoring configuration."
            )
        status = _parse_scoring_approval_decision(decision)
        normalized_reason = _validate_scoring_reason_code(reason_code)
        decided = ScoringConfigurationApproval(
            approval_id=approval.approval_id,
            configuration_id=approval.configuration_id,
            maker_actor_id=approval.maker_actor_id,
            checker_actor_id=context.actor_id,
            policy_version=approval.policy_version,
            status=status,
            decision_reason_code=normalized_reason,
            requested_at=approval.requested_at,
            decided_at=now,
        )
        previous = self.repository.get_active_configuration()
        new_values = _configuration_audit_values(configuration)
        new_values.update(
            {
                "approval_id": approval.approval_id,
                "policy_version": approval.policy_version,
                "status": status.value,
            }
        )
        event = AuditEventInput(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            correlation_id=context.correlation_id,
            action="SCORING_CONFIGURATION_APPROVAL_DECIDED",
            object_type="ScoringConfiguration",
            object_id=configuration.configuration_id,
            result=AuditResult.SUCCESS,
            reason_code=f"SCORING_CONFIGURATION_{status.value}",
            old_values=_configuration_audit_values(previous),
            new_values=new_values,
            occurred_at=now,
            session_id=context.session_id,
        )
        stored = self.repository.decide_configuration_approval(
            decided,
            activate_configuration=status is ScoringApprovalStatus.APPROVED,
            activated_at=now,
            audit_event=self.transactional_audit.prepare(event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return stored

    def _authorize_actor(
        self,
        context: ActorContext | None,
        *,
        required_roles: frozenset[str],
        now: datetime,
    ) -> ActorContext:
        if not is_trusted_actor_context(context):
            raise ScoringAuthorizationError("Trusted actor context is required.")
        assert context is not None
        if context.issued_at > now or context.expires_at <= now:
            raise ScoringAuthorizationError("Actor context is not currently valid.")
        if context.policy_version != self.approval_policy.actor_policy_version:
            raise ScoringAuthorizationError("Actor context policy version is not accepted.")
        if context.actor_type not in self.approval_policy.allowed_actor_types:
            raise ScoringAuthorizationError("Actor type is not allowed for scoring approval.")
        if context.roles.isdisjoint(required_roles):
            raise ScoringAuthorizationError(
                "Actor does not have the required scoring approval role."
            )
        if self.approval_policy.require_enterprise_scope and not context.can_view_enterprise:
            raise ScoringAuthorizationError(
                "Actor does not have enterprise scoring configuration scope."
            )
        return context


class ScoringService:
    def __init__(
        self,
        repository: SQLiteScoreRepository,
        execution_history: ExecutionHistory,
        rule_catalog: RuleCatalog,
        *,
        source_catalog: SourceCatalog | None = None,
        threshold_set: ThresholdSet | None = None,
        clock: Any = utc_now,
    ) -> None:
        self.repository = repository
        self.execution_history = execution_history
        self.rule_catalog = rule_catalog
        self.source_catalog = source_catalog
        self.threshold_set_override = threshold_set
        self.clock = clock
        if threshold_set is not None:
            validate_threshold_set(threshold_set)

    def calculate_execution(self, execution_id: str) -> tuple[QualityScore, ...]:
        configuration = self._configuration()
        execution = self.execution_history.get(execution_id)
        results = self.execution_history.list_results(execution_id)
        results_by_version = {item.rule_version_id: item for item in results}
        if len(results_by_version) != len(results):
            raise ScoringValidationError("Execution contains duplicate rule results.")
        if not set(results_by_version).issubset(execution.rule_version_ids):
            raise ScoringValidationError("Execution results contain an unexpected rule version.")
        if execution.status is ExecutionStatus.SUCCESS and set(results_by_version) != set(
            execution.rule_version_ids
        ):
            raise ScoringValidationError("Successful execution has missing rule results.")

        scores = tuple(
            self._score_rule(
                execution,
                self.rule_catalog.get_version(rule_version_id),
                results_by_version.get(rule_version_id),
                configuration,
            )
            for rule_version_id in execution.rule_version_ids
        )
        return tuple(self.repository.add_or_get(score)[0] for score in scores)

    def calculate_dataset_score(self, execution_id: str, dataset_id: str) -> QualityScore:
        if not dataset_id.strip():
            raise ScoringValidationError("dataset_id is required.")
        execution = self.execution_history.get(execution_id)
        configuration = self._configuration()
        existing_scores = [
            score
            for score in self.repository.list_for_execution(execution_id)
            if score.scope_type is ScoreScopeType.RULE
        ]
        if not existing_scores:
            existing_scores = list(self.calculate_execution(execution_id))

        candidates: list[tuple[QualityScore, RuleVersion]] = []
        for score in existing_scores:
            if score.rule_version_id is None:
                continue
            version = self.rule_catalog.get_version(score.rule_version_id)
            rule = self.rule_catalog.get_rule(version.quality_rule_id)
            if rule.dataset_id == dataset_id:
                candidates.append((score, version))
        if not candidates:
            raise ScoringValidationError("Execution has no rule scores for the dataset.")

        return self._aggregate_score(
            execution=execution,
            scope_type=ScoreScopeType.DATASET,
            scope_id=dataset_id,
            candidates=candidates,
            formula_version=DATASET_FORMULA_VERSION,
            configuration=configuration,
        )

    def calculate_dimension_score(
        self, execution_id: str, dimension: QualityDimension
    ) -> QualityScore:
        if not isinstance(dimension, QualityDimension):
            raise ScoringValidationError("dimension is invalid.")
        execution = self.execution_history.get(execution_id)
        configuration = self._configuration()
        rule_scores = [
            score
            for score in self.repository.list_for_execution(execution_id)
            if score.scope_type is ScoreScopeType.RULE
        ]
        if not rule_scores:
            rule_scores = list(self.calculate_execution(execution_id))
        candidates: list[tuple[QualityScore, RuleVersion]] = []
        for score in rule_scores:
            if score.rule_version_id is None:
                continue
            version = self.rule_catalog.get_version(score.rule_version_id)
            rule = self.rule_catalog.get_rule(version.quality_rule_id)
            if rule.primary_dimension is dimension:
                candidates.append((score, version))
        if not candidates:
            raise ScoringValidationError("Execution has no rule scores for the dimension.")
        return self._aggregate_score(
            execution=execution,
            scope_type=ScoreScopeType.DIMENSION,
            scope_id=dimension.value,
            candidates=candidates,
            formula_version=DIMENSION_FORMULA_VERSION,
            configuration=configuration,
            extra_details={
                "configured_dimension_weight": str(configuration.dimension_weights[dimension])
            },
        )

    def calculate_source_score(self, execution_id: str, data_source_id: str) -> QualityScore:
        if not data_source_id.strip():
            raise ScoringValidationError("data_source_id is required.")
        if self.source_catalog is None:
            raise ScoringValidationError("Source catalog is required for source scoring.")
        execution = self.execution_history.get(execution_id)
        configuration = self._configuration()
        dataset_ids: list[str] = []
        datasets: dict[str, Dataset] = {}
        for rule_version_id in execution.rule_version_ids:
            version = self.rule_catalog.get_version(rule_version_id)
            rule = self.rule_catalog.get_rule(version.quality_rule_id)
            dataset = self.source_catalog.get_dataset(rule.dataset_id)
            datasets[dataset.dataset_id] = dataset
            if dataset.data_source_id == data_source_id:
                dataset_ids.append(dataset.dataset_id)
        dataset_ids = list(dict.fromkeys(dataset_ids))
        if not dataset_ids:
            raise ScoringValidationError("Execution has no datasets for the data source.")

        scores_by_dataset = {
            score.scope_id: score
            for score in self.repository.list_for_execution(execution_id)
            if score.scope_type is ScoreScopeType.DATASET
        }
        for dataset_id in dataset_ids:
            if dataset_id not in scores_by_dataset:
                scores_by_dataset[dataset_id] = self.calculate_dataset_score(
                    execution_id, dataset_id
                )
        candidates = [
            (scores_by_dataset[dataset_id], datasets[dataset_id]) for dataset_id in dataset_ids
        ]
        return self._aggregate_source_score(
            execution=execution,
            data_source_id=data_source_id,
            candidates=candidates,
            configuration=configuration,
        )

    def calculate_enterprise_score(self, execution_id: str) -> QualityScore:
        if self.source_catalog is None:
            raise ScoringValidationError("Source catalog is required for enterprise scoring.")
        execution = self.execution_history.get(execution_id)
        configuration = self._configuration()
        data_source_ids: list[str] = []
        for rule_version_id in execution.rule_version_ids:
            version = self.rule_catalog.get_version(rule_version_id)
            rule = self.rule_catalog.get_rule(version.quality_rule_id)
            dataset = self.source_catalog.get_dataset(rule.dataset_id)
            data_source_ids.append(dataset.data_source_id)
        data_source_ids = list(dict.fromkeys(data_source_ids))
        if not data_source_ids:
            raise ScoringValidationError("Execution has no data sources.")

        scores_by_source = {
            score.scope_id: score
            for score in self.repository.list_for_execution(execution_id)
            if score.scope_type is ScoreScopeType.SOURCE
        }
        for data_source_id in data_source_ids:
            if data_source_id not in scores_by_source:
                scores_by_source[data_source_id] = self.calculate_source_score(
                    execution_id, data_source_id
                )
        candidates = [
            (scores_by_source[data_source_id], data_source_id) for data_source_id in data_source_ids
        ]
        return self._aggregate_enterprise_score(
            execution=execution,
            candidates=candidates,
            configuration=configuration,
        )

    def _aggregate_enterprise_score(
        self,
        *,
        execution: RuleExecution,
        candidates: list[tuple[QualityScore, str]],
        configuration: ScoringConfiguration,
    ) -> QualityScore:
        included = [
            (score, data_source_id)
            for score, data_source_id in candidates
            if score.score_status is ScoreStatus.CALCULATED and score.score_value is not None
        ]
        details: dict[str, Any] = {
            "formula_version": ENTERPRISE_FORMULA_VERSION,
            "configuration_version": configuration.version,
            "threshold_version": configuration.threshold_set.version,
            "weight_policy": "EQUAL_SOURCE_WEIGHT",
            "excluded_components": [
                {
                    "quality_score_id": score.quality_score_id,
                    "data_source_id": data_source_id,
                    "status": score.score_status.value,
                }
                for score, data_source_id in candidates
                if (score, data_source_id) not in included
            ],
        }
        value: Decimal | None = None
        level: ScoreLevel | None = None
        if included:
            value = calculate_weighted_score(
                tuple(
                    (score.score_value, Decimal(1))
                    for score, _ in included
                    if score.score_value is not None
                )
            )
            level = classify_score(value, configuration.threshold_set)
            status = ScoreStatus.CALCULATED
            details["formula"] = "sum(source_score) / source_count"
            details["included_components"] = [
                {
                    "quality_score_id": score.quality_score_id,
                    "data_source_id": data_source_id,
                    "score": str(score.score_value),
                    "weight": "1",
                }
                for score, data_source_id in included
            ]
            details["weight_sum"] = str(len(included))
        else:
            status = _aggregate_empty_status(tuple(score for score, _ in candidates))
            details["included_components"] = []
        score = QualityScore(
            execution_id=execution.execution_id,
            rule_version_id=None,
            scope_type=ScoreScopeType.ENTERPRISE,
            scope_id=None,
            score_value=value,
            score_status=status,
            level=level,
            calculation_details=details,
            calculated_at=self.clock(),
        )
        return self.repository.add_or_get(score)[0]

    def _aggregate_source_score(
        self,
        *,
        execution: RuleExecution,
        data_source_id: str,
        candidates: list[tuple[QualityScore, Dataset]],
        configuration: ScoringConfiguration,
    ) -> QualityScore:
        included = [
            (score, dataset)
            for score, dataset in candidates
            if score.score_status is ScoreStatus.CALCULATED and score.score_value is not None
        ]
        details: dict[str, Any] = {
            "formula_version": SOURCE_FORMULA_VERSION,
            "configuration_version": configuration.version,
            "threshold_version": configuration.threshold_set.version,
            "excluded_components": [
                {
                    "quality_score_id": score.quality_score_id,
                    "dataset_id": dataset.dataset_id,
                    "status": score.score_status.value,
                }
                for score, dataset in candidates
                if (score, dataset) not in included
            ],
        }
        value: Decimal | None = None
        level: ScoreLevel | None = None
        if included:
            value = calculate_weighted_score(
                tuple(
                    (
                        score.score_value,
                        configuration.criticality_weights[dataset.criticality],
                    )
                    for score, dataset in included
                    if score.score_value is not None
                )
            )
            level = classify_score(value, configuration.threshold_set)
            status = ScoreStatus.CALCULATED
            details["formula"] = "sum(dataset_score * criticality_weight) / sum(weight)"
            details["included_components"] = [
                {
                    "quality_score_id": score.quality_score_id,
                    "dataset_id": dataset.dataset_id,
                    "score": str(score.score_value),
                    "criticality": dataset.criticality.value,
                    "weight": str(configuration.criticality_weights[dataset.criticality]),
                }
                for score, dataset in included
            ]
            details["weight_sum"] = str(
                sum(
                    (
                        configuration.criticality_weights[dataset.criticality]
                        for _, dataset in included
                    ),
                    Decimal(0),
                )
            )
        else:
            status = _aggregate_empty_status(tuple(score for score, _ in candidates))
            details["included_components"] = []
        score = QualityScore(
            execution_id=execution.execution_id,
            rule_version_id=None,
            scope_type=ScoreScopeType.SOURCE,
            scope_id=data_source_id,
            score_value=value,
            score_status=status,
            level=level,
            calculation_details=details,
            calculated_at=self.clock(),
        )
        return self.repository.add_or_get(score)[0]

    def _aggregate_score(
        self,
        *,
        execution: RuleExecution,
        scope_type: ScoreScopeType,
        scope_id: str,
        candidates: list[tuple[QualityScore, RuleVersion]],
        formula_version: str,
        configuration: ScoringConfiguration,
        extra_details: Mapping[str, Any] | None = None,
    ) -> QualityScore:
        invalid_weights = [
            version.rule_version_id for _, version in candidates if _weight(version.weight) <= 0
        ]
        included = [
            (score, version)
            for score, version in candidates
            if score.score_status is ScoreStatus.CALCULATED and score.score_value is not None
        ]
        details: dict[str, Any] = {
            "formula_version": formula_version,
            "configuration_version": configuration.version,
            "threshold_version": configuration.threshold_set.version,
            "excluded_components": [
                {
                    "quality_score_id": score.quality_score_id,
                    "rule_version_id": version.rule_version_id,
                    "status": score.score_status.value,
                }
                for score, version in candidates
                if (score, version) not in included
            ],
            **dict(extra_details or {}),
        }
        value: Decimal | None = None
        level: ScoreLevel | None = None
        if invalid_weights:
            status = ScoreStatus.CONFIG_ERROR
            details["invalid_weight_rule_versions"] = invalid_weights
            details["included_components"] = []
        elif included:
            value = calculate_weighted_score(
                tuple(
                    (score.score_value, _weight(version.weight))
                    for score, version in included
                    if score.score_value is not None
                )
            )
            level = classify_score(value, configuration.threshold_set)
            status = ScoreStatus.CALCULATED
            details["formula"] = "sum(score * weight) / sum(weight)"
            details["included_components"] = [
                {
                    "quality_score_id": score.quality_score_id,
                    "rule_version_id": version.rule_version_id,
                    "score": str(score.score_value),
                    "weight": str(_weight(version.weight)),
                }
                for score, version in included
            ]
            details["weight_sum"] = str(
                sum((_weight(version.weight) for _, version in included), Decimal(0))
            )
        else:
            status = _aggregate_empty_status(tuple(score for score, _ in candidates))
            details["included_components"] = []
        score = QualityScore(
            execution_id=execution.execution_id,
            rule_version_id=None,
            scope_type=scope_type,
            scope_id=scope_id,
            score_value=value,
            score_status=status,
            level=level,
            calculation_details=details,
            calculated_at=self.clock(),
        )
        return self.repository.add_or_get(score)[0]

    def _score_rule(
        self,
        execution: RuleExecution,
        version: RuleVersion,
        result: RuleExecutionResult | None,
        configuration: ScoringConfiguration,
    ) -> QualityScore:
        status = _score_status(execution, result)
        details: dict[str, Any] = {
            "formula_version": FORMULA_VERSION,
            "execution_status": execution.status.value,
            "included_in_official_aggregation": status is ScoreStatus.CALCULATED,
            "configuration_version": configuration.version,
        }
        value: Decimal | None = None
        level: ScoreLevel | None = None
        if result is not None:
            _validate_counts(result)
            details["counts"] = {
                "checked": result.checked_count,
                "passed": result.passed_count,
                "failed": result.failed_count,
                "not_evaluated": result.not_evaluated_count,
            }
            if result.checked_count > 0:
                details["rates"] = {
                    "passed": _percentage(result.passed_count, result.checked_count),
                    "failed": _percentage(result.failed_count, result.checked_count),
                    "not_evaluated": _percentage(result.not_evaluated_count, result.checked_count),
                }
            details["completed_partitions"] = list(result.completed_partitions)
        if status is ScoreStatus.CALCULATED:
            assert result is not None
            value = calculate_rule_score(result.passed_count, result.checked_count)
            level = classify_score(value, configuration.threshold_set)
            details["formula"] = "passed_count / checked_count * 100"
            details["threshold_version"] = configuration.threshold_set.version
        else:
            details["excluded_reason"] = status.value

        return QualityScore(
            execution_id=execution.execution_id,
            rule_result_id=result.rule_result_id if result else None,
            rule_version_id=version.rule_version_id,
            scope_id=version.quality_rule_id,
            score_value=value,
            score_status=status,
            level=level,
            calculation_details=details,
            calculated_at=self.clock(),
        )

    def _configuration(self) -> ScoringConfiguration:
        if self.threshold_set_override is None:
            return self.repository.get_active_configuration()
        return ScoringConfiguration(
            version=self.threshold_set_override.version,
            threshold_set=self.threshold_set_override,
            dimension_weights=default_dimension_weights(),
            criticality_weights=default_criticality_weights(),
            created_by="runtime-override",
            is_active=True,
        )


def _configuration_audit_values(configuration: ScoringConfiguration) -> dict[str, str]:
    thresholds = configuration.threshold_set
    return {
        "version": configuration.version,
        "threshold_version": thresholds.version,
        "critical_upper_exclusive": str(thresholds.critical_upper_exclusive),
        "risky_upper_exclusive": str(thresholds.risky_upper_exclusive),
        "acceptable_upper_exclusive": str(thresholds.acceptable_upper_exclusive),
        "dimension_completeness_weight": str(
            configuration.dimension_weights[QualityDimension.COMPLETENESS]
        ),
        "dimension_accuracy_weight": str(
            configuration.dimension_weights[QualityDimension.ACCURACY]
        ),
        "dimension_validity_weight": str(
            configuration.dimension_weights[QualityDimension.VALIDITY]
        ),
        "dimension_consistency_weight": str(
            configuration.dimension_weights[QualityDimension.CONSISTENCY]
        ),
        "dimension_uniqueness_weight": str(
            configuration.dimension_weights[QualityDimension.UNIQUENESS]
        ),
        "dimension_timeliness_weight": str(
            configuration.dimension_weights[QualityDimension.TIMELINESS]
        ),
        "dimension_integrity_weight": str(
            configuration.dimension_weights[QualityDimension.INTEGRITY]
        ),
        "criticality_low_weight": str(configuration.criticality_weights[Criticality.LOW]),
        "criticality_medium_weight": str(configuration.criticality_weights[Criticality.MEDIUM]),
        "criticality_high_weight": str(configuration.criticality_weights[Criticality.HIGH]),
        "criticality_critical_weight": str(configuration.criticality_weights[Criticality.CRITICAL]),
    }


def _validate_scoring_approval_policy(policy: ScoringApprovalPolicy) -> None:
    if not policy.version.strip() or not policy.actor_policy_version.strip():
        raise ScoringValidationError("Scoring approval policy versions are required.")
    if not policy.maker_roles or not policy.checker_roles:
        raise ScoringValidationError("Scoring approval policy roles are required.")
    if not policy.allowed_actor_types:
        raise ScoringValidationError("Scoring approval actor types are required.")
    if any(not role.strip() for role in (*policy.maker_roles, *policy.checker_roles)):
        raise ScoringValidationError("Scoring approval policy roles must not be blank.")


def _parse_scoring_approval_decision(decision: str) -> ScoringApprovalStatus:
    try:
        return {
            "APPROVE": ScoringApprovalStatus.APPROVED,
            "REJECT": ScoringApprovalStatus.REJECTED,
        }[decision.strip().upper()]
    except (AttributeError, KeyError) as exc:
        raise ScoringValidationError("Scoring approval decision is invalid.") from exc


def _validate_scoring_reason_code(reason_code: str) -> str:
    normalized = reason_code.strip().upper()
    if not re.fullmatch(r"[A-Z0-9_.-]{1,120}", normalized):
        raise ScoringValidationError("Scoring approval reason code is invalid.")
    return normalized


def _validate_aware_time(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ScoringValidationError("Scoring approval time must be timezone-aware.")


def calculate_rule_score(passed_count: int, checked_count: int) -> Decimal:
    if checked_count <= 0:
        raise ScoringValidationError("checked_count must be greater than zero.")
    if passed_count < 0 or passed_count > checked_count:
        raise ScoringValidationError("passed_count must be between zero and checked_count.")
    return (Decimal(passed_count) * Decimal(100) / Decimal(checked_count)).quantize(
        _TWO_PLACES, rounding=ROUND_HALF_UP
    )


def calculate_weighted_score(components: tuple[tuple[Decimal, Decimal], ...]) -> Decimal:
    if not components:
        raise ScoringValidationError("At least one score is required for aggregation.")
    if any(score < 0 or score > 100 or weight <= 0 for score, weight in components):
        raise ScoringValidationError("Scores and weights are outside allowed ranges.")
    numerator = sum((score * weight for score, weight in components), Decimal(0))
    denominator = sum((weight for _, weight in components), Decimal(0))
    return (numerator / denominator).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def classify_score(score: Decimal, threshold_set: ThresholdSet) -> ScoreLevel:
    validate_threshold_set(threshold_set)
    if score < 0 or score > 100:
        raise ScoringValidationError("Score must be between zero and one hundred.")
    if score < threshold_set.critical_upper_exclusive:
        return ScoreLevel.CRITICAL
    if score < threshold_set.risky_upper_exclusive:
        return ScoreLevel.RISKY
    if score < threshold_set.acceptable_upper_exclusive:
        return ScoreLevel.ACCEPTABLE
    return ScoreLevel.GOOD


def validate_threshold_set(threshold_set: ThresholdSet) -> None:
    if not threshold_set.version.strip():
        raise ScoringValidationError("Threshold version is required.")
    boundaries = (
        threshold_set.critical_upper_exclusive,
        threshold_set.risky_upper_exclusive,
        threshold_set.acceptable_upper_exclusive,
    )
    if not all(boundary.is_finite() for boundary in boundaries) or not (
        Decimal(0) < boundaries[0] < boundaries[1] < boundaries[2] <= Decimal(100)
    ):
        raise ScoringValidationError(
            "Thresholds must cover zero to one hundred without gaps or overlaps."
        )


def validate_scoring_configuration(configuration: ScoringConfiguration) -> None:
    if not configuration.created_by.strip():
        raise ScoringValidationError("actor_id is required.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", configuration.version):
        raise ScoringValidationError("Scoring configuration version is invalid.")
    validate_threshold_set(configuration.threshold_set)
    if set(configuration.dimension_weights) != set(QualityDimension):
        raise ScoringValidationError("Dimension weights must define every quality dimension.")
    for weight in configuration.dimension_weights.values():
        if not isinstance(weight, Decimal) or not weight.is_finite() or weight <= 0:
            raise ScoringValidationError("Dimension weights must be positive finite decimals.")
    if set(configuration.criticality_weights) != set(Criticality):
        raise ScoringValidationError("Criticality weights must define every dataset criticality.")
    for weight in configuration.criticality_weights.values():
        if not isinstance(weight, Decimal) or not weight.is_finite() or weight <= 0:
            raise ScoringValidationError("Criticality weights must be positive finite decimals.")


def _weight(value: float) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ScoringValidationError("Rule weight must be numeric.")
    return Decimal(str(value))


def _aggregate_empty_status(scores: tuple[QualityScore, ...]) -> ScoreStatus:
    statuses = {score.score_status for score in scores}
    if statuses == {ScoreStatus.NO_DATA}:
        return ScoreStatus.NO_DATA
    if ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR in statuses:
        return ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR
    return ScoreStatus.PARTIAL


def _percentage(part_count: int, total_count: int) -> float:
    value = (Decimal(part_count) * Decimal(100) / Decimal(total_count)).quantize(
        _TWO_PLACES, rounding=ROUND_HALF_UP
    )
    return float(value)


def _score_status(execution: RuleExecution, result: RuleExecutionResult | None) -> ScoreStatus:
    if execution.status in {ExecutionStatus.TECHNICAL_ERROR, ExecutionStatus.TIMEOUT}:
        return ScoreStatus.NOT_CALCULATED_TECHNICAL_ERROR
    if execution.status is ExecutionStatus.PARTIAL or (
        result is not None and not result.eligible_for_official_scoring
    ):
        return ScoreStatus.PARTIAL
    if execution.status is not ExecutionStatus.SUCCESS:
        raise ScoringValidationError("Execution is not in a scoreable terminal status.")
    if result is None:
        raise ScoringValidationError("Successful execution requires a rule result.")
    if result.checked_count == 0:
        return ScoreStatus.NO_DATA
    return ScoreStatus.CALCULATED


def _validate_counts(result: RuleExecutionResult) -> None:
    counts = (
        result.checked_count,
        result.passed_count,
        result.failed_count,
        result.not_evaluated_count,
    )
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts):
        raise ScoringValidationError("Rule result counts must be non-negative integers.")
    if result.checked_count != sum(counts[1:]):
        raise ScoringValidationError("Rule result counts are inconsistent.")
