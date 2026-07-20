"""Trusted, data-minimum incident and breach assessment service."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID, uuid4

from veri_kalitesi.audit import (
    AuditEventInput,
    AuditResult,
    PreparedAuditEvent,
    SQLiteTransactionalAudit,
)
from veri_kalitesi.identity import ActorContext, ActorType, is_trusted_actor_context
from veri_kalitesi.incident_response.errors import (
    IncidentAuthorizationError,
    IncidentConflictError,
    IncidentNotFoundError,
    IncidentTechnicalError,
    IncidentValidationError,
)
from veri_kalitesi.incident_response.models import (
    BreachAssessmentStatus,
    BreachDeadlineStatus,
    BreachDecisionDraft,
    BreachNotificationDecision,
    BreachNotificationDecisionRecord,
    BreachOrigin,
    BreachSuspicionDraft,
    BreachTimelineEventView,
    BreachTimelineQuery,
    BreachTimelineView,
    IncidentResponseAccessPolicy,
    IncidentScopeType,
    IncidentSeverity,
    IncidentSource,
    IncidentTimelineEntry,
    IncidentTimelineEventType,
    PersonalDataBreachSuspicion,
    PersonalDataCategory,
    SecurityIncident,
    SecurityIncidentDraft,
    SecurityIncidentScope,
)
from veri_kalitesi.incident_response.repository import SQLiteIncidentResponseRepository


_CODE_PATTERN = re.compile(r"[A-Z0-9_.-]{1,120}")


class IncidentResponseService:
    def __init__(
        self,
        repository: SQLiteIncidentResponseRepository,
        transactional_audit: SQLiteTransactionalAudit,
        access_policy: IncidentResponseAccessPolicy,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        _validate_policy(access_policy)
        if transactional_audit.connection is not repository.connection:
            raise IncidentValidationError(
                "Incident repository and audit outbox must share a connection."
            )
        self.repository = repository
        self.transactional_audit = transactional_audit
        self.access_policy = access_policy
        self.clock = clock

    def record_security_incident(
        self,
        draft: SecurityIncidentDraft,
        actor_context: ActorContext | None,
    ) -> SecurityIncident:
        now = self._now()
        context = self._authorize(actor_context, self.access_policy.incident_roles, now)
        try:
            _validate_security_incident_draft(draft, context, now)
        except IncidentAuthorizationError as exc:
            self._record_denial(context, exc.reason_code, now)
            raise
        incident = SecurityIncident(
            incident_id=str(uuid4()),
            source_event_reference_id=draft.source_event_reference_id,
            detected_at=draft.detected_at.astimezone(timezone.utc),
            source=draft.source,
            severity=draft.severity,
            event_code=draft.event_code,
            scope_type=draft.scope_type,
            scope_id=draft.scope_id,
            evidence_reference_id=draft.evidence_reference_id,
            recorded_by=context.actor_id,
            recorded_at=now,
        )
        timeline = IncidentTimelineEntry(
            timeline_id=str(uuid4()),
            incident_id=incident.incident_id,
            breach_id=None,
            event_type=IncidentTimelineEventType.SECURITY_INCIDENT_RECORDED,
            event_at=incident.detected_at,
            actor_id=context.actor_id,
            reason_code=incident.event_code,
            evidence_reference_id=incident.evidence_reference_id,
        )
        audit = self._prepare_audit(
            context,
            action="SECURITY_INCIDENT_RECORDED",
            object_type="SecurityIncident",
            object_id=incident.incident_id,
            reason_code=incident.event_code,
            values={
                "policy_version": self.access_policy.version,
                "source": incident.source.value,
                "severity": incident.severity.value,
                "event_code": incident.event_code,
                "scope_type": incident.scope_type.value,
                "status": "DETECTED",
            },
            occurred_at=now,
        )
        try:
            self.repository.create_incident(incident, timeline, audit, self.transactional_audit)
        except IncidentConflictError:
            raise
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            raise IncidentTechnicalError(context.correlation_id) from exc
        self.transactional_audit.publish_pending()
        return incident

    def record_breach_suspicion(
        self,
        draft: BreachSuspicionDraft,
        actor_context: ActorContext | None,
    ) -> PersonalDataBreachSuspicion:
        now = self._now()
        context = self._authorize(actor_context, self.access_policy.privacy_roles, now)
        _validate_breach_draft(draft, now)
        try:
            incident = self.repository.get_incident(draft.incident_id)
        except IncidentNotFoundError:
            raise
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            raise IncidentTechnicalError(context.correlation_id) from exc
        try:
            _require_scope(context, incident)
        except IncidentAuthorizationError as exc:
            self._record_denial(context, exc.reason_code, now)
            raise
        if draft.learned_at < incident.detected_at:
            raise IncidentValidationError("Breach learned time cannot precede incident detection.")
        learned_at = draft.learned_at.astimezone(timezone.utc)
        breach = PersonalDataBreachSuspicion(
            breach_id=str(uuid4()),
            incident_id=incident.incident_id,
            learned_at=learned_at,
            evaluation_deadline_at=learned_at + timedelta(hours=72),
            origin=draft.origin,
            data_categories=frozenset(draft.data_categories),
            affected_scope_code=draft.affected_scope_code,
            containment_action_code=draft.containment_action_code,
            evidence_reference_id=draft.evidence_reference_id,
            processor_notification_evidence_id=draft.processor_notification_evidence_id,
            status=BreachAssessmentStatus.ASSESSMENT_PENDING,
            recorded_by=context.actor_id,
            recorded_at=now,
        )
        timeline = [
            IncidentTimelineEntry(
                timeline_id=str(uuid4()),
                incident_id=incident.incident_id,
                breach_id=breach.breach_id,
                event_type=IncidentTimelineEventType.BREACH_SUSPICION_RECORDED,
                event_at=learned_at,
                actor_id=context.actor_id,
                reason_code=breach.affected_scope_code,
                evidence_reference_id=breach.evidence_reference_id,
            ),
            IncidentTimelineEntry(
                timeline_id=str(uuid4()),
                incident_id=incident.incident_id,
                breach_id=breach.breach_id,
                event_type=IncidentTimelineEventType.CONTAINMENT_RECORDED,
                event_at=now,
                actor_id=context.actor_id,
                reason_code=breach.containment_action_code,
                evidence_reference_id=breach.evidence_reference_id,
            ),
        ]
        if breach.processor_notification_evidence_id is not None:
            timeline.append(
                IncidentTimelineEntry(
                    timeline_id=str(uuid4()),
                    incident_id=incident.incident_id,
                    breach_id=breach.breach_id,
                    event_type=(IncidentTimelineEventType.PROCESSOR_NOTICE_EVIDENCE_RECORDED),
                    event_at=now,
                    actor_id=context.actor_id,
                    reason_code="PROCESSOR_NOTICE_EVIDENCE_PRESENT",
                    evidence_reference_id=breach.processor_notification_evidence_id,
                )
            )
        audit = self._prepare_audit(
            context,
            action="PERSONAL_DATA_BREACH_SUSPICION_RECORDED",
            object_type="PersonalDataBreachSuspicion",
            object_id=breach.breach_id,
            reason_code="ASSESSMENT_PENDING",
            values={
                "policy_version": self.access_policy.version,
                "origin": breach.origin.value,
                "data_category_count": len(breach.data_categories),
                "assessment_status": breach.status.value,
                "evaluation_deadline_at": breach.evaluation_deadline_at.isoformat(),
                "processor_notification_evidence_present": (
                    breach.processor_notification_evidence_id is not None
                ),
                "containment_action_code": breach.containment_action_code,
            },
            occurred_at=now,
        )
        try:
            self.repository.create_breach_suspicion(
                breach, tuple(timeline), audit, self.transactional_audit
            )
        except IncidentConflictError:
            raise
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            raise IncidentTechnicalError(context.correlation_id) from exc
        self.transactional_audit.publish_pending()
        return breach

    def record_notification_decision(
        self,
        draft: BreachDecisionDraft,
        actor_context: ActorContext | None,
    ) -> BreachNotificationDecisionRecord:
        now = self._now()
        context = self._authorize(actor_context, self.access_policy.privacy_roles, now)
        _validate_decision_draft(draft, now)
        try:
            breach = self.repository.get_breach_suspicion(draft.breach_id)
            incident = self.repository.get_incident(breach.incident_id)
        except IncidentNotFoundError:
            raise
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            raise IncidentTechnicalError(context.correlation_id) from exc
        try:
            _require_scope(context, incident)
        except IncidentAuthorizationError as exc:
            self._record_denial(context, exc.reason_code, now)
            raise
        if breach.recorded_by == context.actor_id:
            self._record_denial(context, "MAKER_CHECKER_REQUIRED", now)
            raise IncidentAuthorizationError("MAKER_CHECKER_REQUIRED", context.correlation_id)
        if draft.decided_at < breach.learned_at:
            raise IncidentValidationError("Breach decision time cannot precede learned time.")
        decision = BreachNotificationDecisionRecord(
            decision_id=str(uuid4()),
            breach_id=breach.breach_id,
            decision=draft.decision,
            decided_at=draft.decided_at.astimezone(timezone.utc),
            reason_code=draft.reason_code,
            evidence_reference_id=draft.evidence_reference_id,
            decided_by=context.actor_id,
            recorded_at=now,
        )
        timeline = IncidentTimelineEntry(
            timeline_id=str(uuid4()),
            incident_id=incident.incident_id,
            breach_id=breach.breach_id,
            event_type=IncidentTimelineEventType.NOTIFICATION_DECISION_RECORDED,
            event_at=decision.decided_at,
            actor_id=context.actor_id,
            reason_code=decision.reason_code,
            evidence_reference_id=decision.evidence_reference_id,
        )
        deadline_status = (
            "ON_TIME" if decision.decided_at <= breach.evaluation_deadline_at else "OVERDUE"
        )
        audit = self._prepare_audit(
            context,
            action="PERSONAL_DATA_BREACH_DECISION_RECORDED",
            object_type="BreachNotificationDecision",
            object_id=decision.decision_id,
            reason_code=decision.reason_code,
            values={
                "policy_version": self.access_policy.version,
                "decision": decision.decision.value,
                "decision_reason_code": decision.reason_code,
                "deadline_status": deadline_status,
                "evidence_present": True,
                "external_notification_dispatched": False,
            },
            occurred_at=now,
        )
        try:
            self.repository.add_breach_decision(decision, timeline, audit, self.transactional_audit)
        except IncidentConflictError:
            raise
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            raise IncidentTechnicalError(context.correlation_id) from exc
        self.transactional_audit.publish_pending()
        return decision

    def view_breach_timeline(
        self,
        query: BreachTimelineQuery,
        actor_context: ActorContext | None,
    ) -> BreachTimelineView:
        now = self._now()
        context = self._authorize(actor_context, self.access_policy.privacy_roles, now)
        _validate_timeline_query(query)
        try:
            incident_scope = self.repository.get_breach_incident_scope(query.breach_id)
        except IncidentNotFoundError:
            raise
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            raise IncidentTechnicalError(context.correlation_id) from exc
        try:
            _require_scope_reference(context, incident_scope)
        except IncidentAuthorizationError as exc:
            self._record_denial(context, exc.reason_code, now)
            raise
        try:
            breach = self.repository.get_breach_suspicion(query.breach_id)
            incident = self.repository.get_incident(breach.incident_id)
        except IncidentNotFoundError:
            raise
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            raise IncidentTechnicalError(context.correlation_id) from exc
        if incident.incident_id != incident_scope.incident_id:
            raise IncidentTechnicalError(context.correlation_id)
        try:
            decision = self.repository.get_breach_decision(breach.breach_id)
            timeline = self.repository.list_timeline(incident.incident_id)
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            raise IncidentTechnicalError(context.correlation_id) from exc
        if not _timeline_is_valid(timeline, incident, breach, decision, now):
            raise IncidentTechnicalError(context.correlation_id)
        deadline_status = _deadline_status(breach, decision, now)
        view = BreachTimelineView(
            breach_id=breach.breach_id,
            learned_at=breach.learned_at,
            evaluation_deadline_at=breach.evaluation_deadline_at,
            assessment_status=breach.status,
            deadline_status=deadline_status,
            origin=breach.origin,
            data_category_count=len(breach.data_categories),
            affected_scope_code=breach.affected_scope_code,
            containment_action_code=breach.containment_action_code,
            processor_notification_evidence_present=(
                breach.processor_notification_evidence_id is not None
            ),
            decision=decision.decision if decision is not None else None,
            decided_at=decision.decided_at if decision is not None else None,
            decision_reason_code=decision.reason_code if decision is not None else None,
            external_notification_dispatched=False,
            timeline=tuple(
                BreachTimelineEventView(
                    event_type=entry.event_type,
                    event_at=entry.event_at,
                    reason_code=entry.reason_code,
                )
                for entry in sorted(
                    timeline,
                    key=lambda item: (item.event_at, item.event_type.value),
                )
            ),
            generated_at=now,
            policy_version=self.access_policy.version,
        )
        self._record_timeline_view(context, query, view, now)
        return view

    def _record_timeline_view(
        self,
        context: ActorContext,
        query: BreachTimelineQuery,
        view: BreachTimelineView,
        occurred_at: datetime,
    ) -> None:
        audit = self._prepare_audit(
            context,
            action="PERSONAL_DATA_BREACH_TIMELINE_VIEWED",
            object_type="PersonalDataBreachTimeline",
            object_id=view.breach_id,
            reason_code="QUERY_COMPLETED",
            values={
                "policy_version": self.access_policy.version,
                "query_reason_code": query.reason_code,
                "assessment_status": view.assessment_status.value,
                "deadline_status": view.deadline_status.value,
                "timeline_event_count": len(view.timeline),
                "data_category_count": view.data_category_count,
                "processor_notification_evidence_present": (
                    view.processor_notification_evidence_present
                ),
                "external_notification_dispatched": False,
            },
            occurred_at=occurred_at,
        )
        try:
            self.repository.record_audit(audit, self.transactional_audit)
            self.transactional_audit.publish_pending()
        except Exception as exc:
            raise IncidentTechnicalError(context.correlation_id) from exc

    def _authorize(
        self,
        context: ActorContext | None,
        allowed_roles: frozenset[str],
        now: datetime,
    ) -> ActorContext:
        reason_code = _authorization_denial_reason(
            context, allowed_roles, self.access_policy.actor_policy_version, now
        )
        if reason_code is None:
            assert context is not None
            return context
        trusted = context if is_trusted_actor_context(context) else None
        correlation_id = trusted.correlation_id if trusted is not None else "incident-access-denied"
        self._record_denial(trusted, reason_code, now)
        raise IncidentAuthorizationError(reason_code, correlation_id)

    def _record_denial(
        self,
        context: ActorContext | None,
        reason_code: str,
        now: datetime,
    ) -> None:
        correlation_id = context.correlation_id if context is not None else "incident-access-denied"
        audit = AuditEventInput(
            actor_id=context.actor_id if context is not None else "UNKNOWN",
            actor_type=context.actor_type.value if context is not None else None,
            correlation_id=correlation_id,
            action="INCIDENT_RESPONSE_AUTHORIZATION",
            object_type="AuthorizationDecision",
            object_id=None,
            result=AuditResult.DENIED,
            reason_code=reason_code,
            old_values={},
            new_values={
                "policy_version": self.access_policy.version,
                "reason_code": reason_code,
            },
            occurred_at=now,
            session_id=context.session_id if context is not None else None,
        )
        try:
            prepared = self.transactional_audit.prepare(audit)
            self.repository.record_audit(prepared, self.transactional_audit)
            self.transactional_audit.publish_pending()
        except Exception as exc:
            raise IncidentTechnicalError(correlation_id) from exc

    def _prepare_audit(
        self,
        context: ActorContext,
        *,
        action: str,
        object_type: str,
        object_id: str,
        reason_code: str,
        values: dict[str, object],
        occurred_at: datetime,
    ) -> PreparedAuditEvent:
        event = AuditEventInput(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            correlation_id=context.correlation_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            result=AuditResult.SUCCESS,
            reason_code=reason_code,
            old_values={},
            new_values=values,
            occurred_at=occurred_at,
            session_id=context.session_id,
        )
        try:
            return self.transactional_audit.prepare(event)
        except Exception as exc:
            raise IncidentTechnicalError(context.correlation_id) from exc

    def _now(self) -> datetime:
        now = self.clock()
        if not _timezone_aware(now):
            raise IncidentValidationError("Incident response clock must be timezone-aware.")
        return now.astimezone(timezone.utc)


def _validate_policy(policy: IncidentResponseAccessPolicy) -> None:
    if not _valid_code(policy.version) or not _valid_code(policy.actor_policy_version):
        raise IncidentValidationError("Incident access policy version is invalid.")
    if not policy.incident_roles or not policy.privacy_roles:
        raise IncidentValidationError("Incident access policy roles are required.")
    if any(not _valid_code(role) for role in policy.incident_roles.union(policy.privacy_roles)):
        raise IncidentValidationError("Incident access policy roles are invalid.")


def _validate_security_incident_draft(
    draft: SecurityIncidentDraft, context: ActorContext, now: datetime
) -> None:
    if not isinstance(draft.source, IncidentSource):
        raise IncidentValidationError("Incident source is invalid.")
    if not isinstance(draft.severity, IncidentSeverity):
        raise IncidentValidationError("Incident severity is invalid.")
    if not isinstance(draft.scope_type, IncidentScopeType):
        raise IncidentValidationError("Incident scope type is invalid.")
    _require_uuid(draft.source_event_reference_id, "source event reference")
    _require_uuid(draft.evidence_reference_id, "evidence reference")
    if not _timezone_aware(draft.detected_at) or draft.detected_at > now:
        raise IncidentValidationError("Incident detection time is invalid.")
    if not _valid_code(draft.event_code):
        raise IncidentValidationError("Incident event code is invalid.")
    if draft.scope_type is IncidentScopeType.ENTERPRISE:
        if draft.scope_id is not None or not context.can_view_enterprise:
            raise IncidentAuthorizationError("ENTERPRISE_SCOPE_DENIED", context.correlation_id)
    elif not draft.scope_id or len(draft.scope_id) > 200:
        raise IncidentValidationError("Incident scope is invalid.")
    elif draft.scope_type is IncidentScopeType.SOURCE:
        if draft.scope_id not in context.permitted_source_ids:
            raise IncidentAuthorizationError("SOURCE_SCOPE_DENIED", context.correlation_id)
    elif draft.scope_id not in context.permitted_dataset_ids:
        raise IncidentAuthorizationError("DATASET_SCOPE_DENIED", context.correlation_id)


def _validate_breach_draft(draft: BreachSuspicionDraft, now: datetime) -> None:
    if not isinstance(draft.origin, BreachOrigin):
        raise IncidentValidationError("Breach origin is invalid.")
    if any(not isinstance(category, PersonalDataCategory) for category in draft.data_categories):
        raise IncidentValidationError("Personal data category is invalid.")
    _require_uuid(draft.incident_id, "incident")
    _require_uuid(draft.evidence_reference_id, "evidence reference")
    if not _timezone_aware(draft.learned_at) or draft.learned_at > now:
        raise IncidentValidationError("Breach learned time is invalid.")
    if not draft.data_categories:
        raise IncidentValidationError("At least one personal data category is required.")
    if not _valid_code(draft.affected_scope_code):
        raise IncidentValidationError("Affected scope code is invalid.")
    if not _valid_code(draft.containment_action_code):
        raise IncidentValidationError("Containment action code is invalid.")
    if draft.origin is BreachOrigin.DATA_PROCESSOR:
        if draft.processor_notification_evidence_id is None:
            raise IncidentValidationError(
                "Processor-origin suspicion requires notification evidence."
            )
        _require_uuid(
            draft.processor_notification_evidence_id,
            "processor notification evidence",
        )
    elif draft.processor_notification_evidence_id is not None:
        raise IncidentValidationError(
            "Processor notification evidence is only valid for processor origin."
        )


def _validate_decision_draft(draft: BreachDecisionDraft, now: datetime) -> None:
    if not isinstance(draft.decision, BreachNotificationDecision):
        raise IncidentValidationError("Breach notification decision is invalid.")
    _require_uuid(draft.breach_id, "breach")
    _require_uuid(draft.evidence_reference_id, "evidence reference")
    if not _timezone_aware(draft.decided_at) or draft.decided_at > now:
        raise IncidentValidationError("Breach decision time is invalid.")
    if not _valid_code(draft.reason_code):
        raise IncidentValidationError("Breach decision reason code is invalid.")


def _validate_timeline_query(query: BreachTimelineQuery) -> None:
    _require_uuid(query.breach_id, "breach")
    if not _valid_code(query.reason_code):
        raise IncidentValidationError("Breach timeline query reason code is invalid.")


def _timeline_is_valid(
    timeline: tuple[IncidentTimelineEntry, ...],
    incident: SecurityIncident,
    breach: PersonalDataBreachSuspicion,
    decision: BreachNotificationDecisionRecord | None,
    now: datetime,
) -> bool:
    if not 3 <= len(timeline) <= 5:
        return False
    event_types = tuple(entry.event_type for entry in timeline)
    required = {
        IncidentTimelineEventType.SECURITY_INCIDENT_RECORDED,
        IncidentTimelineEventType.BREACH_SUSPICION_RECORDED,
        IncidentTimelineEventType.CONTAINMENT_RECORDED,
    }
    if not required.issubset(event_types) or len(set(event_types)) != len(event_types):
        return False
    if (IncidentTimelineEventType.NOTIFICATION_DECISION_RECORDED in event_types) != (
        decision is not None
    ):
        return False
    processor_event_present = (
        IncidentTimelineEventType.PROCESSOR_NOTICE_EVIDENCE_RECORDED in event_types
    )
    if processor_event_present != (breach.processor_notification_evidence_id is not None):
        return False
    for entry in timeline:
        if entry.incident_id != incident.incident_id:
            return False
        if entry.event_type is IncidentTimelineEventType.SECURITY_INCIDENT_RECORDED:
            if entry.breach_id is not None:
                return False
        elif entry.breach_id != breach.breach_id:
            return False
        if not _timezone_aware(entry.event_at) or entry.event_at > now:
            return False
        if not _valid_code(entry.reason_code):
            return False
    return True


def _deadline_status(
    breach: PersonalDataBreachSuspicion,
    decision: BreachNotificationDecisionRecord | None,
    now: datetime,
) -> BreachDeadlineStatus:
    if decision is None:
        return (
            BreachDeadlineStatus.ASSESSMENT_OVERDUE
            if now > breach.evaluation_deadline_at
            else BreachDeadlineStatus.ASSESSMENT_PENDING
        )
    return (
        BreachDeadlineStatus.DECIDED_OVERDUE
        if decision.decided_at > breach.evaluation_deadline_at
        else BreachDeadlineStatus.DECIDED_ON_TIME
    )


def _require_scope(context: ActorContext, incident: SecurityIncident) -> None:
    _require_scope_values(
        context,
        incident.scope_type,
        incident.scope_id,
    )


def _require_scope_reference(
    context: ActorContext,
    incident_scope: SecurityIncidentScope,
) -> None:
    _require_scope_values(
        context,
        incident_scope.scope_type,
        incident_scope.scope_id,
    )


def _require_scope_values(
    context: ActorContext,
    scope_type: IncidentScopeType,
    scope_id: str | None,
) -> None:
    if scope_type is IncidentScopeType.ENTERPRISE:
        allowed = context.can_view_enterprise
    elif scope_type is IncidentScopeType.SOURCE:
        allowed = scope_id in context.permitted_source_ids
    else:
        allowed = scope_id in context.permitted_dataset_ids
    if not allowed:
        raise IncidentAuthorizationError("INCIDENT_SCOPE_DENIED", context.correlation_id)


def _authorization_denial_reason(
    context: ActorContext | None,
    roles: frozenset[str],
    policy_version: str,
    now: datetime,
) -> str | None:
    if not is_trusted_actor_context(context):
        return "UNTRUSTED_CONTEXT"
    assert context is not None
    if context.issued_at > now:
        return "CONTEXT_NOT_YET_VALID"
    if context.expires_at <= now:
        return "CONTEXT_EXPIRED"
    if context.policy_version != policy_version:
        return "POLICY_VERSION_MISMATCH"
    if context.actor_type is not ActorType.USER:
        return "ACTOR_TYPE_NOT_ALLOWED"
    if context.privileged:
        return "PRIVILEGED_CONTEXT_NOT_ALLOWED"
    if not context.roles.intersection(roles):
        return "INCIDENT_ROLE_REQUIRED"
    return None


def _valid_code(value: str) -> bool:
    return bool(_CODE_PATTERN.fullmatch(value))


def _require_uuid(value: str, label: str) -> None:
    try:
        UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise IncidentValidationError(f"Incident {label} must be a UUID.") from exc


def _timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None
