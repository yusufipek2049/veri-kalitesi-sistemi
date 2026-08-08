"""Salt okunur ihlal inceleme kanit servisi.

BE-04: Issue investigation evidence endpoint.
- Kural/query aciklamasi
- Beklenen/gerceklesen degerler
- Maskeli kotu ornekler (veri-minimum ve maskeleme kurallarindan gecer)
- Benzer gecmis (tanimsiz → Unknown)
- Kaynakli oneri (tanimsiz → Unknown)

Her bilesen kaynak siniflandirmasi tasir (Observed/Calculated/Estimated/Unknown).
Kaniti olmayan bilesen Unknown doner (fail-closed).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from sqlalchemy.exc import SQLAlchemyError

from veri_kalitesi.identity import ActorContext, AuthorizationService, IdentityError
from veri_kalitesi.issues.errors import (
    IssueAuthorizationError,
    IssueNotFoundError,
    IssueTechnicalError,
)
from veri_kalitesi.issues.models import DataQualityIssue, IssueScopeType


class EvidenceSource(str, Enum):
    """Kanit bileseni kaynak siniflandirmasi."""

    OBSERVED = "Observed"
    CALCULATED = "Calculated"
    ESTIMATED = "Estimated"
    UNKNOWN = "Unknown"


@dataclass(frozen=True)
class EvidenceComponent:
    """Tek bir kanit bileseni."""

    source: EvidenceSource
    value: dict[str, object] | list[object] | str | None
    references: tuple[str, ...] = ()


@dataclass(frozen=True)
class InvestigationEvidence:
    """Issue inceleme kaniti."""

    issue_id: str
    rule_description: EvidenceComponent
    expected_summary: EvidenceComponent
    actual_summary: EvidenceComponent
    masked_samples: EvidenceComponent
    similar_history: EvidenceComponent
    recommendation: EvidenceComponent
    rule_version_id: str | None
    ir_version: str | None
    evidence_fingerprint: str | None
    evidence_query_reference: str | None
    evidence_plan_reference: str | None
    authorization_policy_version: str


class IssueEvidenceProvider(Protocol):
    """Issue icin inceleme kaniti saglayici."""

    def get_evidence_for_issue(
        self,
        issue_id: str,
        scope_type: IssueScopeType,
        scope_id: str,
    ) -> IssueEvidencePayload | None: ...


@dataclass(frozen=True)
class IssueEvidencePayload:
    """Issue ile iliskili calistirma kaniti."""

    rule_version_id: str
    rule_description: str
    ir_version: str
    expected_summary: dict[str, int]
    actual_summary: dict[str, int]
    masked_samples: list[str]
    fingerprint: str
    query_reference: str
    plan_reference: str


class IssueInvestigationReader(Protocol):
    """Issue okuyucu (tekil erisim)."""

    def get(self, issue_id: str) -> DataQualityIssue: ...


_MAX_MASKED_SAMPLES = 10


class IssueInvestigationEvidenceService:
    """Salt okunur ihlal inceleme kanit servisi.

    AC-01: Tek yanitta tum kanit bilesenlerini doner.
    AC-02: Maskeli ornekler veri-minimum kurallarindan gecer, bounded.
    AC-03: Her bilesen kaynak siniflandirmasi tasir.
    AC-04: Kaniti olmayan bilesen Unknown doner (fail-closed).
    AC-05: Yetki kapsami kontrolu, veri sizdirmayan hata.
    AC-07: Kural surumu, politika surumu ve kanit referanslari tasir.
    """

    def __init__(
        self,
        reader: IssueInvestigationReader,
        authorization_service: AuthorizationService,
        evidence_provider: IssueEvidenceProvider,
    ) -> None:
        self.reader = reader
        self.authorization_service = authorization_service
        self.evidence_provider = evidence_provider

    def get_investigation_evidence(
        self,
        *,
        issue_id: str,
        actor_context: ActorContext | None,
    ) -> InvestigationEvidence:
        """Issue icin inceleme kaniti dondur.

        Yazma yan etkisi yoktur (AC-01).
        """
        correlation_id = (
            actor_context.correlation_id if actor_context is not None else "authorization-denied"
        )

        # AC-05: Yetki kapsami kontrolu
        try:
            decision = self.authorization_service.authorize_dashboard(actor_context)
        except IdentityError as exc:
            raise IssueAuthorizationError(
                "Actor cannot access this investigation evidence."
            ) from exc

        # Issue'yu al
        try:
            issue = self.reader.get(issue_id)
        except (sqlite3.Error, SQLAlchemyError, OSError) as exc:
            raise IssueTechnicalError(
                "Issue investigation evidence could not be read.",
                correlation_id,
            ) from exc

        # AC-05: Kapsam kontrolu - yetkisiz erisim veri sizdirmayan hata
        if not _is_scope_permitted(issue, decision):
            raise IssueNotFoundError("The requested issue is not available.")

        # Kanit saglayicidan calistirma kanitini al
        payload = self.evidence_provider.get_evidence_for_issue(
            issue_id=issue.issue_id,
            scope_type=issue.scope_type,
            scope_id=issue.scope_id,
        )

        return _assemble_evidence(
            issue=issue,
            payload=payload,
            policy_version=decision.policy_version,
        )


def _is_scope_permitted(
    issue: DataQualityIssue,
    decision: object,
) -> bool:
    """Issue kapsami yetkili kapsamlarda mi kontrol et."""
    from veri_kalitesi.identity import DashboardAuthorizationDecision

    if not isinstance(decision, DashboardAuthorizationDecision):
        return False

    if issue.scope_type is IssueScopeType.SOURCE:
        return issue.scope_id in decision.permitted_source_ids
    if issue.scope_type is IssueScopeType.DATASET:
        return issue.scope_id in decision.permitted_dataset_ids
    return False


def _assemble_evidence(
    *,
    issue: DataQualityIssue,
    payload: IssueEvidencePayload | None,
    policy_version: str,
) -> InvestigationEvidence:
    """Kanit bilesenlerini birlestir.

    AC-04: Kaniti olmayan bilesen Unknown doner.
    AC-03: Her bilesen kaynak siniflandirmasi tasir.
    """
    if payload is None:
        # Kanit yok - tum bilesenler Unknown (fail-closed)
        unknown = EvidenceComponent(source=EvidenceSource.UNKNOWN, value=None)
        return InvestigationEvidence(
            issue_id=issue.issue_id,
            rule_description=unknown,
            expected_summary=unknown,
            actual_summary=unknown,
            masked_samples=unknown,
            similar_history=unknown,
            recommendation=unknown,
            rule_version_id=None,
            ir_version=None,
            evidence_fingerprint=None,
            evidence_query_reference=None,
            evidence_plan_reference=None,
            authorization_policy_version=policy_version,
        )

    # AC-02: Maskeli ornekler bounded ve veri-minimum formatinda
    bounded_samples = payload.masked_samples[:_MAX_MASKED_SAMPLES]

    return InvestigationEvidence(
        issue_id=issue.issue_id,
        # AC-03: Kural aciklamasi - Observed (calistirma kanitindan)
        rule_description=EvidenceComponent(
            source=EvidenceSource.OBSERVED,
            value=payload.rule_description,
            references=(payload.rule_version_id,),
        ),
        # AC-03: Beklenen degerler - Observed
        expected_summary=EvidenceComponent(
            source=EvidenceSource.OBSERVED,
            value=payload.expected_summary,
            references=(payload.query_reference,),
        ),
        # AC-03: Gerceklesen degerler - Observed
        actual_summary=EvidenceComponent(
            source=EvidenceSource.OBSERVED,
            value=payload.actual_summary,
            references=(payload.query_reference,),
        ),
        # AC-02: Maskeli ornekler - Observed, bounded
        masked_samples=EvidenceComponent(
            source=EvidenceSource.OBSERVED,
            value=bounded_samples,
            references=(payload.fingerprint,),
        ),
        # AC-04: Benzer gecmis - tanimsiz, Unknown (fail-closed)
        similar_history=EvidenceComponent(
            source=EvidenceSource.UNKNOWN,
            value=None,
        ),
        # AC-04: Kaynakli oneri - tanimsiz, Unknown (fail-closed)
        recommendation=EvidenceComponent(
            source=EvidenceSource.UNKNOWN,
            value=None,
        ),
        # AC-07: Kural surumu ve kanit referanslari
        rule_version_id=payload.rule_version_id,
        ir_version=payload.ir_version,
        evidence_fingerprint=payload.fingerprint,
        evidence_query_reference=payload.query_reference,
        evidence_plan_reference=payload.plan_reference,
        authorization_policy_version=policy_version,
    )
