"""Guvenilir kapsamli ve auditli rapor onizleme servisi."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable, Protocol

from veri_kalitesi.audit import AuditEventInput, AuditResult, AuditSink
from veri_kalitesi.identity import ActorContext, ActorType, is_trusted_actor_context
from veri_kalitesi.reporting.errors import (
    ReportAuthorizationError,
    ReportTechnicalError,
    ReportValidationError,
)
from veri_kalitesi.reporting.models import (
    ReportPreview,
    ReportPreviewAccessPolicy,
    ReportPreviewFilter,
    ReportPreviewRequest,
    ReportScoreObservation,
    ReportSummaryRow,
    ReportType,
)
from veri_kalitesi.scoring.models import ScoreStatus


_CODE_PATTERN = re.compile(r"[A-Z0-9_.-]{1,120}")


class ReportPreviewReader(Protocol):
    def latest_source_scores(
        self,
        start_at: datetime,
        end_at: datetime,
        allowed_source_ids: frozenset[str],
    ) -> tuple[ReportScoreObservation, ...]: ...


class ReportPreviewService:
    def __init__(
        self,
        reader: ReportPreviewReader,
        audit_sink: AuditSink,
        policy: ReportPreviewAccessPolicy,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        _validate_policy(policy)
        self.reader = reader
        self.audit_sink = audit_sink
        self.policy = policy
        self.clock = clock

    def preview_summary(
        self,
        request: ReportPreviewRequest,
        actor_context: ActorContext | None,
    ) -> ReportPreview:
        context = self._authorize_context(actor_context)
        normalized = _validate_request(request, self.policy)
        source_ids = self._authorize_scope(normalized, context)
        try:
            observations = self.reader.latest_source_scores(
                normalized.start_at,
                normalized.end_at,
                source_ids,
            )
        except (sqlite3.Error, OSError, ValueError, TypeError) as exc:
            raise ReportTechnicalError(context.correlation_id) from exc
        if not _observations_are_valid(observations, source_ids, normalized):
            raise ReportTechnicalError(context.correlation_id)
        rows = tuple(
            ReportSummaryRow(
                source_id=item.source_id,
                score_value=item.score_value,
                score_status=item.score_status,
                level=item.level,
                calculated_at=item.calculated_at,
            )
            for item in sorted(observations, key=lambda observation: observation.source_id)
        )
        calculated = tuple(
            row.score_value
            for row in rows
            if row.score_status is ScoreStatus.CALCULATED and row.score_value is not None
        )
        average_score = (
            (sum(calculated, Decimal("0")) / Decimal(len(calculated))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if calculated
            else None
        )
        generated_at = self._now()
        preview = ReportPreview(
            report_type=ReportType.SUMMARY,
            generated_at=generated_at,
            filters=ReportPreviewFilter(
                start_at=normalized.start_at,
                end_at=normalized.end_at,
                source_ids=tuple(sorted(source_ids)),
            ),
            rows=rows,
            source_count=len(rows),
            calculated_source_count=len(calculated),
            average_score=average_score,
            policy_version=self.policy.version,
        )
        self._record_preview(context, normalized, preview)
        return preview

    def _authorize_context(self, context: ActorContext | None) -> ActorContext:
        now = self._now()
        reason_code = _context_denial_reason(context, self.policy, now)
        if reason_code is not None:
            trusted = context if is_trusted_actor_context(context) else None
            self._record_denial(trusted, reason_code, now)
            raise ReportAuthorizationError(
                reason_code,
                trusted.correlation_id if trusted is not None else "report-access-denied",
            )
        assert context is not None
        return context

    def _authorize_scope(
        self,
        request: ReportPreviewRequest,
        context: ActorContext,
    ) -> frozenset[str]:
        source_ids = request.requested_source_ids
        if source_ids is None:
            source_ids = context.permitted_source_ids
        if not source_ids.issubset(context.permitted_source_ids):
            self._record_denial(context, "SOURCE_SCOPE_DENIED", self._now())
            raise ReportAuthorizationError("SOURCE_SCOPE_DENIED", context.correlation_id)
        if len(source_ids) > self.policy.max_source_count:
            raise ReportValidationError("Report preview source count exceeds policy.")
        return source_ids

    def _record_denial(
        self,
        context: ActorContext | None,
        reason_code: str,
        occurred_at: datetime,
    ) -> None:
        event = AuditEventInput(
            actor_id=context.actor_id if context is not None else "UNKNOWN",
            actor_type=context.actor_type.value if context is not None else None,
            correlation_id=(
                context.correlation_id if context is not None else "report-access-denied"
            ),
            action="REPORT_PREVIEW_AUTHORIZATION",
            object_type="AuthorizationDecision",
            object_id=None,
            result=AuditResult.DENIED,
            reason_code=reason_code,
            old_values={},
            new_values={
                "policy_version": self.policy.version,
                "reason_code": reason_code,
            },
            occurred_at=occurred_at,
            session_id=context.session_id if context is not None else None,
        )
        self._append_audit(event)

    def _record_preview(
        self,
        context: ActorContext,
        request: ReportPreviewRequest,
        preview: ReportPreview,
    ) -> None:
        event = AuditEventInput(
            actor_id=context.actor_id,
            actor_type=context.actor_type.value,
            correlation_id=context.correlation_id,
            action="REPORT_PREVIEW_VIEWED",
            object_type="ReportPreview",
            object_id=None,
            result=AuditResult.SUCCESS,
            reason_code="QUERY_COMPLETED",
            old_values={},
            new_values={
                "policy_version": self.policy.version,
                "report_type": request.report_type.value,
                "query_reason_code": request.reason_code,
                "requested_source_count": len(preview.filters.source_ids),
                "returned_source_count": preview.source_count,
                "calculated_source_count": preview.calculated_source_count,
                "window_days": (request.end_at - request.start_at).days,
                "masking_mode": preview.masking_mode,
            },
            occurred_at=preview.generated_at,
            session_id=context.session_id,
        )
        self._append_audit(event)

    def _append_audit(self, event: AuditEventInput) -> None:
        try:
            self.audit_sink.append(event)
        except Exception as exc:
            raise ReportTechnicalError(event.correlation_id) from exc

    def _now(self) -> datetime:
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ReportValidationError("Report preview clock must be timezone-aware.")
        return now.astimezone(timezone.utc)


def _validate_policy(policy: ReportPreviewAccessPolicy) -> None:
    if not _CODE_PATTERN.fullmatch(policy.version):
        raise ReportValidationError("Report access policy version is invalid.")
    if not policy.actor_policy_version.strip():
        raise ReportValidationError("Report actor policy version is required.")
    if not policy.allowed_roles or any(
        not _CODE_PATTERN.fullmatch(role) for role in policy.allowed_roles
    ):
        raise ReportValidationError("Report access roles are invalid.")
    if (
        isinstance(policy.max_window_days, bool)
        or not isinstance(policy.max_window_days, int)
        or not 1 <= policy.max_window_days <= 366
    ):
        raise ReportValidationError("Report preview window policy is invalid.")
    if (
        isinstance(policy.max_source_count, bool)
        or not isinstance(policy.max_source_count, int)
        or not 1 <= policy.max_source_count <= 500
    ):
        raise ReportValidationError("Report source count policy is invalid.")


def _validate_request(
    request: ReportPreviewRequest,
    policy: ReportPreviewAccessPolicy,
) -> ReportPreviewRequest:
    if request.start_at.tzinfo is None or request.start_at.utcoffset() is None:
        raise ReportValidationError("Report start time must be timezone-aware.")
    if request.end_at.tzinfo is None or request.end_at.utcoffset() is None:
        raise ReportValidationError("Report end time must be timezone-aware.")
    start_at = request.start_at.astimezone(timezone.utc)
    end_at = request.end_at.astimezone(timezone.utc)
    if start_at > end_at:
        raise ReportValidationError("Report start must not follow end time.")
    if end_at - start_at > timedelta(days=policy.max_window_days):
        raise ReportValidationError("Report preview requires asynchronous reporting.")
    if not _CODE_PATTERN.fullmatch(request.reason_code):
        raise ReportValidationError("Report reason code is invalid.")
    if request.report_type is not ReportType.SUMMARY:
        raise ReportValidationError("Only summary report preview is supported.")
    if request.requested_source_ids is not None:
        if any(
            not source_id.strip() or len(source_id) > 200
            for source_id in request.requested_source_ids
        ):
            raise ReportValidationError("Report source filters are invalid.")
    return ReportPreviewRequest(
        start_at=start_at,
        end_at=end_at,
        reason_code=request.reason_code,
        requested_source_ids=(
            frozenset(request.requested_source_ids)
            if request.requested_source_ids is not None
            else None
        ),
        report_type=request.report_type,
    )


def _context_denial_reason(
    context: ActorContext | None,
    policy: ReportPreviewAccessPolicy,
    now: datetime,
) -> str | None:
    if not is_trusted_actor_context(context):
        return "UNTRUSTED_CONTEXT"
    assert context is not None
    if context.issued_at > now:
        return "CONTEXT_NOT_YET_VALID"
    if context.expires_at <= now:
        return "CONTEXT_EXPIRED"
    if context.policy_version != policy.actor_policy_version:
        return "POLICY_VERSION_MISMATCH"
    if context.actor_type is not ActorType.USER:
        return "ACTOR_TYPE_NOT_ALLOWED"
    if context.privileged:
        return "PRIVILEGED_CONTEXT_NOT_ALLOWED"
    if not context.roles.intersection(policy.allowed_roles):
        return "REPORT_ROLE_REQUIRED"
    return None


def _observations_are_valid(
    observations: tuple[ReportScoreObservation, ...],
    source_ids: frozenset[str],
    request: ReportPreviewRequest,
) -> bool:
    if len({item.source_id for item in observations}) != len(observations):
        return False
    for item in observations:
        if item.source_id not in source_ids:
            return False
        if item.calculated_at.tzinfo is None or item.calculated_at.utcoffset() is None:
            return False
        calculated_at = item.calculated_at.astimezone(timezone.utc)
        if not request.start_at <= calculated_at <= request.end_at:
            return False
        if item.score_status is ScoreStatus.CALCULATED:
            if (
                item.score_value is None
                or not item.score_value.is_finite()
                or not Decimal("0") <= item.score_value <= Decimal("100")
            ):
                return False
        elif item.score_value is not None or item.level is not None:
            return False
    return True
