"""Kural oluşturma, sürümleme ve kontrollü test uygulama servisi."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Callable, Protocol
from uuid import uuid4

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditResult,
    AuditSink,
    SQLiteTransactionalAudit,
)
from veri_kalitesi.data_sources.models import (
    DataField,
    DataSource,
    DataSourceStatus,
    Dataset,
)
from veri_kalitesi.data_sources.postgresql import is_read_only_sql
from veri_kalitesi.identity import ActorContext, ActorType, is_trusted_actor_context
from veri_kalitesi.rules.errors import (
    RuleAuthorizationError,
    RuleTestTechnicalError,
    RuleValidationError,
)
from veri_kalitesi.rules.models import (
    QualityDimension,
    QualityRule,
    RuleApprovalPolicy,
    RuleApprovalRequest,
    RuleApprovalStatus,
    RuleCriticality,
    RuleStatus,
    RuleTestComputation,
    RuleTestOptions,
    RuleTestResult,
    RuleTestStatus,
    RuleType,
    RuleVersion,
    utc_now,
)
from veri_kalitesi.rules.repository import SQLiteRuleRepository
from veri_kalitesi.rules.templates import build_rule_plan, reference_scope, referenced_fields


class MetadataCatalog(Protocol):
    def get_dataset(self, dataset_id: str) -> Dataset: ...

    def list_data_fields(self, dataset_id: str) -> list[DataField]: ...

    def get_data_source(self, data_source_id: str) -> DataSource: ...


class RuleTestExecutor(Protocol):
    def execute(
        self,
        *,
        rule: QualityRule,
        version: RuleVersion,
        record_limit: int,
    ) -> RuleTestComputation: ...


class BusinessCalendar(Protocol):
    @property
    def version(self) -> str: ...

    def add_business_days(self, start_at: datetime, business_days: int) -> datetime: ...


class RuleService:
    def __init__(
        self,
        repository: SQLiteRuleRepository,
        metadata_catalog: MetadataCatalog,
        executor: RuleTestExecutor,
        *,
        audit_sink: AuditSink,
        transactional_audit: SQLiteTransactionalAudit,
        approval_policy: RuleApprovalPolicy | None = None,
        approval_calendar: BusinessCalendar | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.repository = repository
        self.metadata_catalog = metadata_catalog
        self.executor = executor
        self.audit_sink = audit_sink
        self.transactional_audit = transactional_audit
        self.approval_policy = approval_policy
        self.approval_calendar = approval_calendar
        self.clock = clock
        if approval_policy is not None:
            _validate_approval_policy(approval_policy)
            _validate_approval_calendar(approval_policy, approval_calendar)

    def create_rule(
        self,
        *,
        actor_id: str,
        code: str,
        name: str,
        dataset_id: str,
        rule_type: str,
        parameters: Mapping[str, Any],
        primary_dimension: str,
        threshold: float,
        weight: float,
        criticality: str,
        owner_user_id: str,
        correlation_id: str | None = None,
        actor_context: ActorContext | None = None,
    ) -> tuple[QualityRule, RuleVersion]:
        correlation_id = _resolve_correlation_id(correlation_id)
        parsed_type = _parse_enum(RuleType, rule_type, "rule_type")
        dimension = _parse_enum(QualityDimension, primary_dimension, "primary_dimension")
        parsed_criticality = _parse_enum(RuleCriticality, criticality, "criticality")
        _validate_common(code, name, actor_id, owner_user_id, threshold, weight)
        self.metadata_catalog.get_dataset(dataset_id)
        if self._requires_approval(parsed_criticality):
            trusted_actor = self._authorize_approval_actor(
                actor_context,
                required_roles=self._require_approval_policy().maker_roles,
                dataset_id=dataset_id,
            )
            if trusted_actor.actor_id != actor_id:
                raise RuleAuthorizationError(
                    "Critical RuleVersion actor_id must match trusted maker context."
                )
        plan = build_rule_plan(parsed_type, parameters)
        fields = referenced_fields(plan)
        if fields:
            _validate_fields(self.metadata_catalog, dataset_id, fields)
        reference = reference_scope(plan)
        if reference is not None:
            reference_dataset_id, reference_fields = reference
            self.metadata_catalog.get_dataset(reference_dataset_id)
            _validate_fields(self.metadata_catalog, reference_dataset_id, reference_fields)

        rule = QualityRule(
            code=code.strip().upper(),
            name=name.strip(),
            dataset_id=dataset_id,
            field_ids=fields,
            primary_dimension=dimension,
            owner_user_id=owner_user_id,
        )
        version = RuleVersion(
            quality_rule_id=rule.quality_rule_id,
            version_no=1,
            rule_type=parsed_type,
            definition=plan,
            threshold=float(threshold),
            weight=float(weight),
            criticality=parsed_criticality,
            prepared_by_actor_id=actor_id,
        )
        audit_event = self._build_audit_event(
            actor_id,
            correlation_id,
            "QUALITY_RULE_CREATED",
            rule.quality_rule_id,
            AuditResult.SUCCESS,
            "QUALITY_RULE_CREATED",
            {
                "rule_version_id": version.rule_version_id,
                "version_no": version.version_no,
                "rule_type": version.rule_type.value,
                "status": rule.status.value,
            },
        )
        prepared = self.transactional_audit.prepare(audit_event)
        self.repository.add_rule_with_version(
            rule,
            version,
            audit_event=prepared,
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return rule, version

    def create_version(
        self,
        *,
        actor_id: str,
        quality_rule_id: str,
        parameters: Mapping[str, Any],
        threshold: float,
        weight: float,
        criticality: str,
        correlation_id: str | None = None,
        actor_context: ActorContext | None = None,
    ) -> RuleVersion:
        correlation_id = _resolve_correlation_id(correlation_id)
        rule = self.repository.get_rule(quality_rule_id)
        versions = self.repository.list_versions(quality_rule_id)
        if not versions:
            raise RuleValidationError("QualityRule must have an existing version.")
        latest = versions[-1]
        _validate_threshold_weight(threshold, weight)
        parsed_criticality = _parse_enum(RuleCriticality, criticality, "criticality")
        if self._requires_approval(parsed_criticality):
            trusted_actor = self._authorize_approval_actor(
                actor_context,
                required_roles=self._require_approval_policy().maker_roles,
                dataset_id=rule.dataset_id,
            )
            if trusted_actor.actor_id != actor_id:
                raise RuleAuthorizationError(
                    "Critical RuleVersion actor_id must match trusted maker context."
                )
        plan = build_rule_plan(latest.rule_type, parameters)
        fields = referenced_fields(plan)
        if fields:
            _validate_fields(self.metadata_catalog, rule.dataset_id, fields)
        reference = reference_scope(plan)
        if reference is not None:
            self.metadata_catalog.get_dataset(reference[0])
            _validate_fields(self.metadata_catalog, reference[0], reference[1])
        version = RuleVersion(
            quality_rule_id=quality_rule_id,
            version_no=latest.version_no + 1,
            rule_type=latest.rule_type,
            definition=plan,
            threshold=float(threshold),
            weight=float(weight),
            criticality=parsed_criticality,
            prepared_by_actor_id=actor_id,
        )
        audit_event = self._build_audit_event(
            actor_id,
            correlation_id,
            "QUALITY_RULE_VERSION_CREATED",
            quality_rule_id,
            AuditResult.SUCCESS,
            "QUALITY_RULE_VERSION_CREATED",
            {
                "rule_version_id": version.rule_version_id,
                "version_no": version.version_no,
            },
        )
        self.repository.add_version(
            version,
            audit_event=self.transactional_audit.prepare(audit_event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return version

    def test_rule(
        self,
        *,
        actor_id: str,
        rule_version_id: str,
        options: RuleTestOptions | None = None,
        correlation_id: str | None = None,
    ) -> RuleTestResult:
        correlation_id = _resolve_correlation_id(correlation_id)
        options = options or RuleTestOptions()
        _validate_test_limit(options.limit)
        version = self.repository.get_version(rule_version_id)
        rule = self.repository.get_rule(version.quality_rule_id)
        dataset = self.metadata_catalog.get_dataset(rule.dataset_id)
        data_source = self.metadata_catalog.get_data_source(dataset.data_source_id)
        if data_source.status not in {
            DataSourceStatus.TEST_SUCCEEDED,
            DataSourceStatus.ACTIVE,
        }:
            raise RuleValidationError("Rule test requires a successful connection test.")
        if version.rule_type is RuleType.CUSTOM_SQL and not is_read_only_sql(
            str(version.definition.get("sql", ""))
        ):
            raise RuleValidationError("Custom SQL must remain read-only.")

        try:
            computation = self.executor.execute(
                rule=rule,
                version=version,
                record_limit=options.limit,
            )
            _validate_counts(computation)
            evaluable_count = computation.passed_count + computation.failed_count
            success_rate = round(computation.passed_count * 100 / evaluable_count, 2)
            result = RuleTestResult(
                rule_version_id=version.rule_version_id,
                status=RuleTestStatus.SUCCESS,
                record_limit=options.limit,
                checked_count=computation.checked_count,
                passed_count=computation.passed_count,
                failed_count=computation.failed_count,
                not_evaluated_count=computation.not_evaluated_count,
                success_rate=success_rate,
                preview_score=success_rate,
                message="Rule test completed outside official scoring.",
            )
        except RuleTestTechnicalError as exc:
            result = RuleTestResult(
                rule_version_id=version.rule_version_id,
                status=RuleTestStatus.TECHNICAL_ERROR,
                record_limit=options.limit,
                error_class=exc.error_class,
                message="Rule test failed with a classified technical error.",
            )

        succeeded = result.status is RuleTestStatus.SUCCESS
        audit_event = self._build_audit_event(
            actor_id,
            correlation_id,
            "QUALITY_RULE_TESTED",
            rule.quality_rule_id,
            AuditResult.SUCCESS if succeeded else AuditResult.FAILURE,
            "RULE_TEST_COMPLETED" if succeeded else (result.error_class or "TECHNICAL_ERROR"),
            {
                "rule_version_id": version.rule_version_id,
                "rule_test_result_id": result.rule_test_result_id,
                "status": result.status.value,
                "record_limit": result.record_limit,
                "checked_count": result.checked_count,
                "passed_count": result.passed_count,
                "failed_count": result.failed_count,
                "error_class": result.error_class,
                "official_score_included": False,
            },
        )
        self.repository.add_test_result(
            result,
            audit_event=self.transactional_audit.prepare(audit_event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return result

    def activate_rule(
        self,
        *,
        actor_id: str,
        quality_rule_id: str,
        correlation_id: str | None = None,
    ) -> QualityRule:
        correlation_id = _resolve_correlation_id(correlation_id)
        rule = self.repository.get_rule(quality_rule_id)
        if rule.status is not RuleStatus.DRAFT:
            raise RuleValidationError("Only a draft rule can be activated.")
        versions = self.repository.list_versions(quality_rule_id)
        if not versions:
            raise RuleValidationError("Rule activation requires a version.")
        if self._requires_approval(versions[-1].criticality):
            raise RuleValidationError("Critical rule activation requires maker-checker approval.")
        latest_test = self.repository.latest_test_result(versions[-1].rule_version_id)
        if latest_test is None or latest_test.status is not RuleTestStatus.SUCCESS:
            raise RuleValidationError("Rule activation requires a successful latest-version test.")
        if not rule.owner_user_id.strip():
            raise RuleValidationError("Rule activation requires an owner.")
        audit_event = self._build_audit_event(
            actor_id,
            correlation_id,
            "QUALITY_RULE_ACTIVATED",
            quality_rule_id,
            AuditResult.SUCCESS,
            "QUALITY_RULE_ACTIVATED",
            {
                "rule_version_id": versions[-1].rule_version_id,
                "status": RuleStatus.ACTIVE.value,
            },
            old_values={"status": RuleStatus.DRAFT.value},
        )
        active_rule = self.repository.update_rule_status(
            quality_rule_id,
            RuleStatus.ACTIVE,
            audit_event=self.transactional_audit.prepare(audit_event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return active_rule

    def request_rule_approval(
        self,
        *,
        actor_context: ActorContext | None,
        quality_rule_id: str,
    ) -> RuleApprovalRequest:
        policy = self._require_approval_policy()
        rule = self.repository.get_rule(quality_rule_id)
        context = self._authorize_approval_actor(
            actor_context,
            required_roles=policy.maker_roles,
            dataset_id=rule.dataset_id,
        )
        if rule.status is not RuleStatus.DRAFT:
            raise RuleValidationError("Only a draft rule can request approval.")
        versions = self.repository.list_versions(quality_rule_id)
        if not versions:
            raise RuleValidationError("Rule approval requires a version.")
        version = versions[-1]
        if version.criticality not in policy.criticalities:
            raise RuleValidationError("Rule version does not require approval.")
        if version.prepared_by_actor_id != context.actor_id:
            raise RuleAuthorizationError("Only the trusted RuleVersion maker can request approval.")
        latest_test = self.repository.latest_test_result(version.rule_version_id)
        if latest_test is None or latest_test.status is not RuleTestStatus.SUCCESS:
            raise RuleValidationError("Rule approval requires a successful latest-version test.")
        if not rule.owner_user_id.strip():
            raise RuleValidationError("Rule approval requires an owner.")
        requested_at = self.clock()
        if not _is_aware(requested_at):
            raise RuleValidationError("Rule approval clock must be timezone-aware.")
        target_at, expires_at, calendar_version = self._approval_timing(requested_at)
        request = RuleApprovalRequest(
            rule_version_id=version.rule_version_id,
            maker_actor_id=context.actor_id,
            policy_version=policy.version,
            requested_at=requested_at,
            target_at=target_at,
            expires_at=expires_at,
            business_calendar_version=calendar_version,
        )
        audit_event = self._build_audit_event(
            context.actor_id,
            context.correlation_id,
            "QUALITY_RULE_APPROVAL_REQUESTED",
            quality_rule_id,
            AuditResult.SUCCESS,
            "RULE_APPROVAL_REQUESTED",
            {
                "rule_version_id": version.rule_version_id,
                "approval_request_id": request.approval_request_id,
                "policy_version": policy.version,
                "status": request.status.value,
                "target_at": target_at.isoformat() if target_at else None,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "business_calendar_version": calendar_version,
            },
            actor_type=context.actor_type.value,
            session_id=context.session_id,
        )
        stored = self.repository.add_approval_request(
            request,
            audit_event=self.transactional_audit.prepare(audit_event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return stored

    def decide_rule_approval(
        self,
        *,
        actor_context: ActorContext | None,
        approval_request_id: str,
        decision: str,
        reason_code: str,
    ) -> RuleApprovalRequest:
        policy = self._require_approval_policy()
        request = self.repository.get_approval_request(approval_request_id)
        version = self.repository.get_version(request.rule_version_id)
        rule = self.repository.get_rule(version.quality_rule_id)
        context = self._authorize_approval_actor(
            actor_context,
            required_roles=policy.checker_roles,
            dataset_id=rule.dataset_id,
        )
        if request.status is not RuleApprovalStatus.PENDING:
            raise RuleValidationError("Rule approval request is not pending.")
        if self._approval_request_expired(request):
            raise RuleValidationError("Rule approval request has expired and must be recreated.")
        if request.policy_version != policy.version:
            raise RuleValidationError("Rule approval policy version changed.")
        if request.maker_actor_id == context.actor_id:
            raise RuleAuthorizationError("Maker cannot approve or reject the same change.")
        if version.prepared_by_actor_id == context.actor_id:
            raise RuleAuthorizationError("RuleVersion preparer cannot decide the same change.")
        latest_versions = self.repository.list_versions(rule.quality_rule_id)
        if not latest_versions or latest_versions[-1].rule_version_id != version.rule_version_id:
            raise RuleValidationError("Approval request does not target the latest RuleVersion.")
        status = _parse_approval_decision(decision)
        normalized_reason = _validate_reason_code(reason_code)
        decided = RuleApprovalRequest(
            approval_request_id=request.approval_request_id,
            rule_version_id=request.rule_version_id,
            maker_actor_id=request.maker_actor_id,
            checker_actor_id=context.actor_id,
            policy_version=request.policy_version,
            status=status,
            decision_reason_code=normalized_reason,
            requested_at=request.requested_at,
            target_at=request.target_at,
            expires_at=request.expires_at,
            business_calendar_version=request.business_calendar_version,
            decided_at=self.clock(),
        )
        audit_event = self._build_audit_event(
            context.actor_id,
            context.correlation_id,
            "QUALITY_RULE_APPROVAL_DECIDED",
            rule.quality_rule_id,
            AuditResult.SUCCESS,
            f"RULE_APPROVAL_{status.value}",
            {
                "rule_version_id": version.rule_version_id,
                "approval_request_id": request.approval_request_id,
                "policy_version": policy.version,
                "status": status.value,
            },
            old_values={"status": RuleApprovalStatus.PENDING.value},
            actor_type=context.actor_type.value,
            session_id=context.session_id,
        )
        stored = self.repository.decide_approval_request(
            decided,
            quality_rule_id=rule.quality_rule_id,
            activate_rule=status is RuleApprovalStatus.APPROVED,
            audit_event=self.transactional_audit.prepare(audit_event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return stored

    def withdraw_rule_approval(
        self,
        *,
        actor_context: ActorContext | None,
        approval_request_id: str,
        reason_code: str,
    ) -> RuleApprovalRequest:
        policy = self._require_approval_policy()
        request = self.repository.get_approval_request(approval_request_id)
        version = self.repository.get_version(request.rule_version_id)
        rule = self.repository.get_rule(version.quality_rule_id)
        context = self._authorize_approval_actor(
            actor_context,
            required_roles=policy.maker_roles,
            dataset_id=rule.dataset_id,
        )
        if request.status is not RuleApprovalStatus.PENDING:
            raise RuleValidationError("Rule approval request is not pending.")
        if self._approval_request_expired(request):
            raise RuleValidationError("Rule approval request has expired and must be recreated.")
        if request.maker_actor_id != context.actor_id:
            raise RuleAuthorizationError("Only the approval request maker can withdraw it.")
        if version.prepared_by_actor_id != context.actor_id:
            raise RuleAuthorizationError(
                "Only the RuleVersion preparer can withdraw its approval request."
            )
        normalized_reason = _validate_reason_code(reason_code)
        withdrawn_at = self.clock()
        if not _is_aware(withdrawn_at):
            raise RuleValidationError("Rule approval clock must be timezone-aware.")
        withdrawn = RuleApprovalRequest(
            approval_request_id=request.approval_request_id,
            rule_version_id=request.rule_version_id,
            maker_actor_id=request.maker_actor_id,
            policy_version=request.policy_version,
            status=RuleApprovalStatus.WITHDRAWN,
            decision_reason_code=normalized_reason,
            requested_at=request.requested_at,
            target_at=request.target_at,
            expires_at=request.expires_at,
            business_calendar_version=request.business_calendar_version,
            decided_at=withdrawn_at,
        )
        audit_event = self._build_audit_event(
            context.actor_id,
            context.correlation_id,
            "QUALITY_RULE_APPROVAL_WITHDRAWN",
            rule.quality_rule_id,
            AuditResult.SUCCESS,
            "RULE_APPROVAL_WITHDRAWN",
            {
                "rule_version_id": version.rule_version_id,
                "approval_request_id": request.approval_request_id,
                "policy_version": request.policy_version,
                "status": RuleApprovalStatus.WITHDRAWN.value,
            },
            old_values={"status": RuleApprovalStatus.PENDING.value},
            actor_type=context.actor_type.value,
            session_id=context.session_id,
        )
        stored = self.repository.withdraw_approval_request(
            withdrawn,
            audit_event=self.transactional_audit.prepare(audit_event),
            audit_outbox=self.transactional_audit,
        )
        self.transactional_audit.publish_pending()
        return stored

    def expire_due_rule_approvals(
        self,
        *,
        actor_context: ActorContext | None,
    ) -> tuple[RuleApprovalRequest, ...]:
        context = self._authorize_expiry_actor(actor_context)
        expired_at = self.clock()
        if not _is_aware(expired_at):
            raise RuleValidationError("Rule approval clock must be timezone-aware.")
        due = self.repository.list_due_approval_requests(expired_at)
        resolved: list[tuple[RuleApprovalRequest, RuleVersion, QualityRule]] = []
        for request in due:
            version = self.repository.get_version(request.rule_version_id)
            rule = self.repository.get_rule(version.quality_rule_id)
            if rule.dataset_id not in context.permitted_dataset_ids:
                raise RuleAuthorizationError("Expiry worker is outside the rule dataset scope.")
            resolved.append((request, version, rule))

        expired_requests = []
        for request, version, rule in resolved:
            expired = RuleApprovalRequest(
                approval_request_id=request.approval_request_id,
                rule_version_id=request.rule_version_id,
                maker_actor_id=request.maker_actor_id,
                policy_version=request.policy_version,
                status=RuleApprovalStatus.EXPIRED,
                decision_reason_code="RULE.APPROVAL.EXPIRED",
                requested_at=request.requested_at,
                target_at=request.target_at,
                expires_at=request.expires_at,
                business_calendar_version=request.business_calendar_version,
                decided_at=expired_at,
            )
            audit_event = self._build_audit_event(
                context.actor_id,
                context.correlation_id,
                "QUALITY_RULE_APPROVAL_EXPIRED",
                rule.quality_rule_id,
                AuditResult.SUCCESS,
                "RULE_APPROVAL_EXPIRED",
                {
                    "rule_version_id": version.rule_version_id,
                    "approval_request_id": request.approval_request_id,
                    "policy_version": request.policy_version,
                    "business_calendar_version": request.business_calendar_version,
                    "status": RuleApprovalStatus.EXPIRED.value,
                },
                old_values={"status": RuleApprovalStatus.PENDING.value},
                actor_type=context.actor_type.value,
                session_id=context.session_id,
            )
            stored = self.repository.expire_approval_request(
                expired,
                audit_event=self.transactional_audit.prepare(audit_event),
                audit_outbox=self.transactional_audit,
            )
            self.transactional_audit.publish_pending()
            expired_requests.append(stored)
        return tuple(expired_requests)

    def _approval_timing(
        self, requested_at: datetime
    ) -> tuple[datetime | None, datetime | None, str | None]:
        policy = self._require_approval_policy()
        if policy.expiration_business_days is None:
            return None, None, None
        assert policy.target_business_days is not None
        assert policy.business_calendar_version is not None
        assert self.approval_calendar is not None
        target_at = self.approval_calendar.add_business_days(
            requested_at, policy.target_business_days
        )
        expires_at = self.approval_calendar.add_business_days(
            requested_at, policy.expiration_business_days
        )
        if not _is_aware(target_at) or not _is_aware(expires_at):
            raise RuleValidationError("Rule approval calendar must return timezone-aware values.")
        if not requested_at < target_at < expires_at:
            raise RuleValidationError("Rule approval calendar returned an invalid time window.")
        return target_at, expires_at, policy.business_calendar_version

    def _approval_request_expired(self, request: RuleApprovalRequest) -> bool:
        if request.expires_at is None:
            return False
        now = self.clock()
        if not _is_aware(now):
            raise RuleValidationError("Rule approval clock must be timezone-aware.")
        return now >= request.expires_at

    def _authorize_expiry_actor(self, context: ActorContext | None) -> ActorContext:
        policy = self._require_approval_policy()
        now = self.clock()
        if not _is_aware(now):
            raise RuleValidationError("Rule approval clock must be timezone-aware.")
        if not is_trusted_actor_context(context):
            raise RuleAuthorizationError("Trusted expiry service context is required.")
        assert context is not None
        if context.issued_at > now or context.expires_at <= now:
            raise RuleAuthorizationError("Expiry service context is not currently valid.")
        if context.policy_version != policy.actor_policy_version:
            raise RuleAuthorizationError("Expiry service policy version is not accepted.")
        if context.actor_type is not ActorType.SERVICE:
            raise RuleAuthorizationError("Rule approval expiry requires a service account.")
        if not policy.expiry_service_roles or context.roles.isdisjoint(policy.expiry_service_roles):
            raise RuleAuthorizationError("Service account cannot expire rule approvals.")
        return context

    def _requires_approval(self, criticality: RuleCriticality) -> bool:
        if self.approval_policy is None:
            return criticality is RuleCriticality.CRITICAL
        return criticality in self.approval_policy.criticalities

    def _require_approval_policy(self) -> RuleApprovalPolicy:
        if self.approval_policy is None:
            raise RuleAuthorizationError("Rule approval policy is not configured.")
        return self.approval_policy

    def _authorize_approval_actor(
        self,
        context: ActorContext | None,
        *,
        required_roles: frozenset[str],
        dataset_id: str,
    ) -> ActorContext:
        policy = self._require_approval_policy()
        now = self.clock()
        if not _is_aware(now):
            raise RuleValidationError("Rule approval clock must be timezone-aware.")
        if not is_trusted_actor_context(context):
            raise RuleAuthorizationError("Trusted actor context is required.")
        assert context is not None
        if context.issued_at > now or context.expires_at <= now:
            raise RuleAuthorizationError("Actor context is not currently valid.")
        if context.policy_version != policy.actor_policy_version:
            raise RuleAuthorizationError("Actor context policy version is not accepted.")
        if context.actor_type not in policy.allowed_actor_types:
            raise RuleAuthorizationError("Actor type is not allowed for rule approval.")
        if context.roles.isdisjoint(required_roles):
            raise RuleAuthorizationError("Actor does not have the required approval role.")
        if dataset_id not in context.permitted_dataset_ids:
            raise RuleAuthorizationError("Actor is outside the rule dataset scope.")
        return context

    def _build_audit_event(
        self,
        actor_id: str,
        correlation_id: str,
        action: str,
        object_id: str,
        result: AuditResult,
        reason_code: str,
        new_values: dict[str, Any],
        *,
        old_values: dict[str, Any] | None = None,
        actor_type: str = "USER",
        session_id: str | None = None,
    ) -> AuditEventInput:
        return AuditEventInput(
            actor_id=actor_id,
            actor_type=actor_type,
            correlation_id=correlation_id,
            action=action,
            object_type="QualityRule",
            object_id=object_id,
            result=result,
            reason_code=reason_code,
            old_values=old_values or {},
            new_values=new_values,
            occurred_at=utc_now(),
            session_id=session_id,
        )


def _validate_common(
    code: str,
    name: str,
    actor_id: str,
    owner_user_id: str,
    threshold: float,
    weight: float,
) -> None:
    if not actor_id.strip():
        raise RuleValidationError("actor_id is required.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,120}", code):
        raise RuleValidationError("Rule code format is invalid.")
    if not name.strip() or len(name.strip()) > 250:
        raise RuleValidationError("Rule name must contain 1 to 250 characters.")
    if not owner_user_id.strip():
        raise RuleValidationError("Rule owner is required.")
    _validate_threshold_weight(threshold, weight)


def _resolve_correlation_id(correlation_id: str | None) -> str:
    if correlation_id is None:
        return str(uuid4())
    if not correlation_id.strip():
        raise RuleValidationError("correlation_id must not be blank.")
    return correlation_id


def _validate_threshold_weight(threshold: float, weight: float) -> None:
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, int | float)
        or not 0 <= threshold <= 100
    ):
        raise RuleValidationError("Rule threshold must be between 0 and 100.")
    if isinstance(weight, bool) or not isinstance(weight, int | float) or weight <= 0:
        raise RuleValidationError("Rule weight must be greater than zero.")


def _validate_fields(catalog: MetadataCatalog, dataset_id: str, field_ids: tuple[str, ...]) -> None:
    known = {field.data_field_id for field in catalog.list_data_fields(dataset_id)}
    if not field_ids or any(field_id not in known for field_id in field_ids):
        raise RuleValidationError("Rule contains an invalid field reference.")


def _validate_test_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10_000:
        raise RuleValidationError("Rule test limit must be between 1 and 10000.")


def _validate_counts(computation: RuleTestComputation) -> None:
    counts = (
        computation.checked_count,
        computation.passed_count,
        computation.failed_count,
        computation.not_evaluated_count,
    )
    if any(isinstance(count, bool) or not isinstance(count, int) or count < 0 for count in counts):
        raise RuleValidationError("Rule test counts must be non-negative integers.")
    if computation.checked_count != sum(counts[1:]):
        raise RuleValidationError("Rule test counts are inconsistent.")
    if computation.passed_count + computation.failed_count == 0:
        raise RuleValidationError("Rule test has no evaluable records.")


def _parse_enum(enum_type: type[Any], value: str, field_name: str) -> Any:
    try:
        return enum_type(value.upper())
    except (AttributeError, ValueError) as exc:
        raise RuleValidationError(f"{field_name} is invalid.") from exc


def _validate_approval_policy(policy: RuleApprovalPolicy) -> None:
    if not policy.version.strip() or not policy.actor_policy_version.strip():
        raise RuleValidationError("Rule approval policy versions are required.")
    if not policy.maker_roles or not policy.checker_roles:
        raise RuleValidationError("Rule approval policy roles are required.")
    if not policy.criticalities or not policy.allowed_actor_types:
        raise RuleValidationError("Rule approval policy scope is required.")
    if any(not role.strip() for role in (*policy.maker_roles, *policy.checker_roles)):
        raise RuleValidationError("Rule approval policy roles must not be blank.")
    timing = (
        policy.target_business_days,
        policy.expiration_business_days,
        policy.business_calendar_version,
    )
    if any(value is not None for value in timing) and not all(
        value is not None for value in timing
    ):
        raise RuleValidationError("Rule approval timing policy must be complete.")
    if policy.expiration_business_days is not None:
        target = policy.target_business_days
        expiration = policy.expiration_business_days
        if (
            isinstance(target, bool)
            or isinstance(expiration, bool)
            or not isinstance(target, int)
            or not isinstance(expiration, int)
            or target < 1
            or expiration <= target
        ):
            raise RuleValidationError("Rule approval business-day limits are invalid.")
        if not policy.business_calendar_version or not policy.business_calendar_version.strip():
            raise RuleValidationError("Rule approval business calendar version is required.")
        if not policy.expiry_service_roles or any(
            not role.strip() for role in policy.expiry_service_roles
        ):
            raise RuleValidationError("Rule approval expiry service roles are required.")


def _validate_approval_calendar(
    policy: RuleApprovalPolicy, calendar: BusinessCalendar | None
) -> None:
    if policy.expiration_business_days is None:
        return
    if calendar is None:
        raise RuleValidationError("Rule approval business calendar is required.")
    if calendar.version != policy.business_calendar_version:
        raise RuleValidationError("Rule approval business calendar version does not match policy.")


def _parse_approval_decision(decision: str) -> RuleApprovalStatus:
    try:
        return {
            "APPROVE": RuleApprovalStatus.APPROVED,
            "REJECT": RuleApprovalStatus.REJECTED,
        }[decision.strip().upper()]
    except (AttributeError, KeyError) as exc:
        raise RuleValidationError("Rule approval decision is invalid.") from exc


def _validate_reason_code(reason_code: str) -> str:
    normalized = reason_code.strip().upper()
    if not re.fullmatch(r"[A-Z0-9_.-]{1,120}", normalized):
        raise RuleValidationError("Rule approval reason code is invalid.")
    return normalized


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
