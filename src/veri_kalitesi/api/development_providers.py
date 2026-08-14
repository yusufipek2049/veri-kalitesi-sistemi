"""Development-ortamı için PhaseBProviders implementasyonları.

Bu modül yalnızca development runtime'da kullanılır.
Gerçek üretim bağımlılıklarının yerini tutan basit/fonksiyonel
implementasyonlar sağlar.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import uuid4

from veri_kalitesi.identity import ActorType

from veri_kalitesi.api.identity import DevelopmentUserRegistry
from veri_kalitesi.api.models import IssueAssigneeOptionResponse
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.issues.models import (
    IssueAssignment,
    IssueAssigneeProfile,
    IssuePriority,
    IssueScopeType,
    IssueTrigger,
)
from veri_kalitesi.issues.models import (
    ProtectedIssueResolution,
    TrustedIssueVerificationResult,
    IssueVerificationOutcome,
)
from veri_kalitesi.notifications.contracts import (
    _StagedDelivery,
    _StagedEvent,
)
from veri_kalitesi.notifications.models import (
    NotificationDeliveryStatus,
    NotificationEvent,
)
from veri_kalitesi.notifications.postgresql_repository import (
    PostgreSQLNotificationRepository,
)
from veri_kalitesi.rules.models import (
    QualityRule,
    RuleTestComputation,
    RuleVersion,
)


# ── RuleTestExecutor ───────────────────────────────────────────────────


class DevelopmentRuleTestExecutor:
    """Development için kural test yürütücüsü — tüm kontrolleri başarılı sayar."""

    def execute(
        self,
        *,
        rule: QualityRule,
        version: RuleVersion,
        record_limit: int,
    ) -> RuleTestComputation:
        return RuleTestComputation(
            checked_count=min(record_limit, 100),
            passed_count=min(record_limit, 100),
            failed_count=0,
            not_evaluated_count=0,
        )


# ── IssueAssigneeDirectory ─────────────────────────────────────────────


class DevelopmentIssueAssigneeDirectory:
    """DevelopmentUserRegistry üzerinden atama profili çözer."""

    def __init__(self, user_registry: DevelopmentUserRegistry) -> None:
        self._registry = user_registry

    def get_assignee_profile(self, user_id: str) -> IssueAssigneeProfile | None:
        user = self._registry.get_user(user_id)
        if user is None:
            return None
        return IssueAssigneeProfile(
            user_id=user.user_id,
            active=True,
            permitted_source_ids=user.permitted_source_ids,
            permitted_dataset_ids=user.permitted_dataset_ids,
        )


# ── IssueAssignmentResolver ────────────────────────────────────────────


class DevelopmentIssueAssignmentResolver:
    """Development için basit assignment resolver.

    Manuel issue oluşturma senaryosunda, issue'yu oluşturan kullanıcıya atar.
    Otomatik trigger'larda ilk uygun dev kullanıcıyı seçer.
    """

    def __init__(self, user_registry: DevelopmentUserRegistry) -> None:
        self._registry = user_registry

    def resolve_assignment(self, trigger: IssueTrigger) -> IssueAssignment:
        # Manuel trigger: varsayılan steward'a ata
        default_assignee = self._registry.get_user("dev-data-steward") or self._registry.get_user(
            "dev-data-owner"
        )
        if default_assignee is None:
            users = self._registry.list_users()
            default_assignee = users[0] if users else None

        if default_assignee is None:
            from veri_kalitesi.issues.errors import IssueAssignmentError

            raise IssueAssignmentError("No development users available for assignment.")

        return IssueAssignment(
            assignee_user_id=default_assignee.user_id,
            priority=IssuePriority.MEDIUM,
        )


# ── IssueAssigneeOptionProvider ────────────────────────────────────────


class DevelopmentIssueAssigneeOptionProvider:
    """Development kullanıcılarını atama seçenekleri olarak listeler."""

    def __init__(self, user_registry: DevelopmentUserRegistry) -> None:
        self._registry = user_registry

    def list_assignment_options(
        self,
        issue_id: str,
        actor_context: ActorContext | None,
    ) -> tuple[IssueAssigneeOptionResponse, ...]:
        from uuid import UUID

        return tuple(
            IssueAssigneeOptionResponse(
                user_id=UUID(user.user_id),
                display_name=user.display_name,
            )
            for user in self._registry.list_users()
        )


# ── IssueResolutionProtector ───────────────────────────────────────────


class DevelopmentIssueResolutionProtector:
    """Development için çözüm koruması — taslağı olduğu gibi kabul eder."""

    def protect_resolution(
        self,
        draft: object,
    ) -> ProtectedIssueResolution:
        from veri_kalitesi.issues.models import IssueResolutionDraft

        assert isinstance(draft, IssueResolutionDraft)
        return ProtectedIssueResolution(
            root_cause=draft.root_cause,
            corrective_action=draft.corrective_action,
            evidence_reference_id=draft.evidence_reference_id,
            completed_at=draft.completed_at,
            protection_policy_version="DEVELOPMENT_PASSTHROUGH_V1",
        )


# ── IssueVerificationResolver ──────────────────────────────────────────


class DevelopmentIssueVerificationResolver:
    """Development için doğrulama çözücü — başarılı sonuç döner."""

    def resolve_verification(
        self,
        verification_reference_id: str,
    ) -> TrustedIssueVerificationResult | None:
        return TrustedIssueVerificationResult(
            verification_reference_id=verification_reference_id,
            execution_id=f"dev-exec-{verification_reference_id[:8]}",
            score_id=None,
            scope_type=IssueScopeType.DATASET,
            scope_id="dataset-customer",
            outcome=IssueVerificationOutcome.QUALITY_PASSED,
            completed_at=datetime.now(timezone.utc),
        )


# ── IssueNotificationPublisher ─────────────────────────────────────────


class DevelopmentIssueNotificationPublisher:
    """Development için basit bildirim yayımcısı.

    NotificationRepository üzerinden event ve delivery kayıtları oluşturur.
    """

    def __init__(
        self,
        notification_repository: PostgreSQLNotificationRepository,
    ) -> None:
        self._repository = notification_repository

    def create_for_event(
        self,
        event: NotificationEvent,
        actor_context: ActorContext | None,
    ) -> tuple[object, ...]:
        now = datetime.now(timezone.utc)
        staged_event = _StagedEvent(
            event_id=event.event_id,
            event_type=event.event_type.value,
            scope_type=event.scope_type.value,
            scope_id=event.scope_id,
            source_ref=event.source_ref or "",
            deduplication_key_digest=hashlib.sha256(event.deduplication_key.encode()).hexdigest()[
                :32
            ],
            payload_digest=hashlib.sha256(str(event.payload).encode()).hexdigest()[:16],
            payload=event.payload,
            correlation_id=event.correlation_id,
            policy_version=event.policy_version,
            occurred_at=event.occurred_at,
            published_at=now,
        )
        delivery_id = str(uuid4())
        recipient = actor_context.actor_id if actor_context else "development-dashboard-user"
        staged_delivery = _StagedDelivery(
            delivery_id=delivery_id,
            event_id=event.event_id,
            recipient_user_id=recipient,
            channel_id="default-inapp-channel",
            status=NotificationDeliveryStatus.DELIVERED,
            created_at=now,
        )
        # Repository'nin kendi session_factory'sini kullanarak doğrudan yaz
        with self._repository._session_factory() as session:
            self._repository._insert_event(session, staged_event)
            self._repository._insert_delivery(session, staged_delivery)
            session.commit()
        return (delivery_id,)


# ── ActorContext provider ──────────────────────────────────────────────


def build_development_actor_context_provider(
    resolver: object,
) -> Callable[[], ActorContext]:
    """Development resolver'dan sabit bir ActorContext üretici oluşturur."""

    def _provide() -> ActorContext:
        from veri_kalitesi.api.identity import DevelopmentActorContextResolver

        if isinstance(resolver, DevelopmentActorContextResolver):
            # Sentinel bir request oluşturmak yerine doğrudan issuer kullan
            return resolver.issuer.issue(
                actor_id="development-dashboard-user",
                actor_type=ActorType.USER,
                authentication_source="development-only-adapter",
                session_id="development-only-session",
                roles=frozenset({"DATA_VIEWER", "DATA_STEWARD"}),
                permitted_source_ids=frozenset(),
                permitted_dataset_ids=frozenset(),
                can_view_enterprise=True,
                privileged=False,
                issued_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
                policy_version=resolver.policy_version,
                correlation_id="development-notification-context",
            )
        raise RuntimeError(
            "Development actor context provider requires a DevelopmentActorContextResolver."
        )

    return _provide


# ── IssueEvidenceProvider (development) ────────────────────────────────


class DevelopmentIssueEvidenceProvider:
    """Development için boş kanıt sağlayıcı — tüm kanıtlar Unknown döner."""

    def get_evidence_for_issue(
        self,
        issue_id: str,
        scope_type: object,
        scope_id: str,
    ) -> None:
        return None


# ── Factory ────────────────────────────────────────────────────────────


def build_development_phase_b_providers(
    *,
    user_registry: DevelopmentUserRegistry,
    notification_repository: PostgreSQLNotificationRepository,
    resolver: object,
):
    """Development ortamı için tam PhaseBProviders oluşturur."""

    from veri_kalitesi.api.composition import PhaseBProviders

    return PhaseBProviders(
        rule_test_executor=DevelopmentRuleTestExecutor(),
        issue_assignee_directory=DevelopmentIssueAssigneeDirectory(user_registry),
        issue_assignment_resolver=DevelopmentIssueAssignmentResolver(user_registry),
        issue_assignee_option_provider=DevelopmentIssueAssigneeOptionProvider(user_registry),
        issue_resolution_protector=DevelopmentIssueResolutionProtector(),
        issue_verification_resolver=DevelopmentIssueVerificationResolver(),
        issue_notification_publisher=DevelopmentIssueNotificationPublisher(notification_repository),
        issue_notification_actor_context_provider=(
            build_development_actor_context_provider(resolver)
        ),
    )
