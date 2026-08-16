"""Cozum kaydi icin kanit defteri.

Cozum formundaki ``evidence_reference_id`` alani, once serbest metin bir UUID
bekliyordu; girilen degerin gercek bir kanita ait oldugu hicbir yerde
dogrulanmiyordu. Bu modul kanidi birinci sinif bir kayit haline getirir:

- Kanit adaylari kural calistirmasinin sonuclarindan ve deneme kayitlarindan
  (log) turetilir; kullanici serbest metin girmez, listeden secer.
- Secilen aday kalici bir ``issue_evidence`` kaydina donusur ve kendi UUID'sini
  alir. Boylece calistirma kimliginin UUID olup olmamasi onemsizdir.
- Cozum kaydi bu UUID'ye FK ile baglanir; servis katmani da kanidin ayni
  issue'ya ait oldugunu dogrular (fail-closed).

Veri-minimum: kanit kaydi ham satir tutmaz. Yalnizca sayimlar, olcum durumu,
referanslar (fingerprint/query/plan) ve icerik ozeti saklanir.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from collections.abc import Callable
from typing import Protocol, Sequence
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError

from veri_kalitesi.identity import ActorContext, AuthorizationService, IdentityError
from veri_kalitesi.issues.errors import (
    IssueAuthorizationError,
    IssueNotFoundError,
    IssueTechnicalError,
    IssueValidationError,
)
from veri_kalitesi.issues.models import DataQualityIssue, IssueScopeType


_CANDIDATE_KEY_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}")
_MAX_LABEL_LENGTH = 200


class IssueEvidenceKind(str, Enum):
    """Kanit turu."""

    EXECUTION_RESULT = "EXECUTION_RESULT"
    EXECUTION_LOG = "EXECUTION_LOG"
    LEGACY_REFERENCE = "LEGACY_REFERENCE"
    UPLOADED_FILE = "UPLOADED_FILE"


@dataclass(frozen=True)
class IssueEvidenceCandidate:
    """Henuz kaydedilmemis, calistirmadan turetilmis kanit adayi."""

    candidate_key: str
    kind: IssueEvidenceKind
    label: str
    execution_id: str
    observed_at: datetime
    rule_version_id: str | None = None
    evaluated_count: int | None = None
    failed_count: int | None = None
    measurement_status: str | None = None
    fingerprint: str | None = None
    query_reference: str | None = None
    plan_reference: str | None = None


@dataclass(frozen=True)
class IssueEvidenceRecord:
    """Kalici kanit kaydi. ``evidence_id`` cozum kaydinin FK hedefidir."""

    issue_id: str
    kind: IssueEvidenceKind
    label: str
    execution_id: str
    observed_at: datetime
    captured_at: datetime
    captured_by: str
    content_digest: str
    source_digest: str
    rule_version_id: str | None = None
    evaluated_count: int | None = None
    failed_count: int | None = None
    measurement_status: str | None = None
    fingerprint: str | None = None
    query_reference: str | None = None
    plan_reference: str | None = None
    evidence_id: str = ""

    def __post_init__(self) -> None:
        if not self.evidence_id:
            object.__setattr__(self, "evidence_id", str(uuid4()))


class IssueEvidenceReader(Protocol):
    """Kanit okuma yuzeyi (cozum dogrulamasi bunu kullanir)."""

    def list_evidence(self, issue_id: str) -> list[IssueEvidenceRecord]: ...

    def get_evidence(self, evidence_id: str) -> IssueEvidenceRecord | None: ...


class IssueEvidenceStore(IssueEvidenceReader, Protocol):
    """Kanit yazma yuzeyi."""

    def add_evidence(self, record: IssueEvidenceRecord) -> IssueEvidenceRecord: ...


class IssueEvidenceCandidateProvider(Protocol):
    """Issue icin kanit adaylarini uretir."""

    def list_candidates(self, issue: DataQualityIssue) -> Sequence[IssueEvidenceCandidate]: ...


class IssueEvidenceIssueReader(Protocol):
    def get(self, issue_id: str) -> DataQualityIssue: ...


_PERSISTENCE_ERRORS = (sqlite3.Error, SQLAlchemyError, OSError)


class IssueEvidenceService:
    """Kanit listeleme ve kanit kaydi olusturma servisi.

    AC-01: Kanit adaylari kural calistirmasinin sonuc ve loglarindan turetilir.
    AC-02: Kaydedilen kanit kendi UUID'sini alir, issue'ya baglidir.
    AC-03: Ayni aday tekrar kaydedilirse mevcut kayit doner (idempotent).
    AC-04: Kapsam disi aktor veri sizdirmayan hata alir.
    """

    def __init__(
        self,
        *,
        issue_reader: IssueEvidenceIssueReader,
        evidence_store: IssueEvidenceStore,
        candidate_provider: IssueEvidenceCandidateProvider,
        authorization_service: AuthorizationService,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._issue_reader = issue_reader
        self._evidence_store = evidence_store
        self._candidate_provider = candidate_provider
        self._authorization_service = authorization_service
        self._clock = clock

    def list_evidence(
        self,
        *,
        issue_id: str,
        actor_context: ActorContext | None,
    ) -> tuple[tuple[IssueEvidenceRecord, ...], tuple[IssueEvidenceCandidate, ...]]:
        """Kayitli kanitlari ve henuz kaydedilmemis adaylari dondurur."""
        issue = self._authorized_issue(issue_id, actor_context)
        correlation_id = _correlation_id(actor_context)
        try:
            stored = tuple(self._evidence_store.list_evidence(issue.issue_id))
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError("Issue evidence could not be read.", correlation_id) from exc
        try:
            candidates = tuple(self._candidate_provider.list_candidates(issue))
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError(
                "Issue evidence candidates could not be read.", correlation_id
            ) from exc
        captured = {record.source_digest for record in stored}
        pending = tuple(
            candidate
            for candidate in candidates
            if candidate_source_digest(candidate.candidate_key) not in captured
        )
        return stored, pending

    def capture(
        self,
        *,
        issue_id: str,
        candidate_key: str,
        actor_context: ActorContext | None,
    ) -> IssueEvidenceRecord:
        """Bir adayi kalici kanit kaydina donusturur (idempotent)."""
        validate_candidate_key(candidate_key)
        issue = self._authorized_issue(issue_id, actor_context)
        assert actor_context is not None  # _authorized_issue None aktoru reddeder
        correlation_id = actor_context.correlation_id
        source_digest = candidate_source_digest(candidate_key)
        try:
            existing = next(
                (
                    record
                    for record in self._evidence_store.list_evidence(issue.issue_id)
                    if record.source_digest == source_digest
                ),
                None,
            )
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError("Issue evidence could not be read.", correlation_id) from exc
        if existing is not None:
            return existing

        try:
            candidates = tuple(self._candidate_provider.list_candidates(issue))
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError(
                "Issue evidence candidates could not be read.", correlation_id
            ) from exc
        candidate = next(
            (item for item in candidates if item.candidate_key == candidate_key),
            None,
        )
        if candidate is None:
            raise IssueValidationError("Evidence candidate is not available for this issue.")

        record = IssueEvidenceRecord(
            issue_id=issue.issue_id,
            kind=candidate.kind,
            label=candidate.label[:_MAX_LABEL_LENGTH],
            execution_id=candidate.execution_id,
            observed_at=candidate.observed_at,
            captured_at=self._now(),
            captured_by=actor_context.actor_id,
            content_digest=evidence_content_digest(candidate),
            source_digest=source_digest,
            rule_version_id=candidate.rule_version_id,
            evaluated_count=candidate.evaluated_count,
            failed_count=candidate.failed_count,
            measurement_status=candidate.measurement_status,
            fingerprint=candidate.fingerprint,
            query_reference=candidate.query_reference,
            plan_reference=candidate.plan_reference,
        )
        validate_evidence_record(record)
        try:
            return self._evidence_store.add_evidence(record)
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError(
                "Issue evidence could not be persisted.", correlation_id
            ) from exc

    def _authorized_issue(
        self,
        issue_id: str,
        actor_context: ActorContext | None,
    ) -> DataQualityIssue:
        correlation_id = _correlation_id(actor_context)
        try:
            decision = self._authorization_service.authorize_dashboard(actor_context)
        except IdentityError as exc:
            raise IssueAuthorizationError("Actor cannot access issue evidence.") from exc
        try:
            issue = self._issue_reader.get(issue_id)
        except _PERSISTENCE_ERRORS as exc:
            raise IssueTechnicalError("Issue could not be read.", correlation_id) from exc
        if not _scope_permitted(issue, decision):
            raise IssueNotFoundError("The requested issue is not available.")
        return issue

    def _now(self) -> datetime:
        if self._clock is not None:
            return self._clock()
        return datetime.now(timezone.utc)


def _correlation_id(actor_context: ActorContext | None) -> str:
    return actor_context.correlation_id if actor_context is not None else "authorization-denied"


def _scope_permitted(issue: DataQualityIssue, decision: object) -> bool:
    from veri_kalitesi.identity import DashboardAuthorizationDecision

    if not isinstance(decision, DashboardAuthorizationDecision):
        return False
    if issue.scope_type is IssueScopeType.SOURCE:
        return issue.scope_id in decision.permitted_source_ids
    if issue.scope_type is IssueScopeType.DATASET:
        return issue.scope_id in decision.permitted_dataset_ids
    return False


def candidate_source_digest(candidate_key: str) -> str:
    """Aday anahtarindan idempotanlik ozeti uretir."""
    return hashlib.sha256(candidate_key.encode("utf-8")).hexdigest()


def evidence_content_digest(candidate: IssueEvidenceCandidate) -> str:
    """Kanit iceriginin degismezlik ozeti (veri-minimum alanlar uzerinden)."""
    payload = {
        "kind": candidate.kind.value,
        "execution_id": candidate.execution_id,
        "rule_version_id": candidate.rule_version_id,
        "evaluated_count": candidate.evaluated_count,
        "failed_count": candidate.failed_count,
        "measurement_status": candidate.measurement_status,
        "fingerprint": candidate.fingerprint,
        "query_reference": candidate.query_reference,
        "plan_reference": candidate.plan_reference,
        "observed_at": candidate.observed_at.isoformat(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_candidate_key(candidate_key: str) -> None:
    if not isinstance(candidate_key, str) or not _CANDIDATE_KEY_PATTERN.fullmatch(candidate_key):
        raise IssueValidationError("candidate_key is invalid.")


def validate_evidence_record(record: IssueEvidenceRecord) -> None:
    from uuid import UUID

    try:
        UUID(record.evidence_id)
    except (AttributeError, TypeError, ValueError) as exc:
        raise IssueValidationError("evidence_id must be a UUID.") from exc
    if not isinstance(record.kind, IssueEvidenceKind):
        raise IssueValidationError("evidence kind is invalid.")
    if not record.label.strip() or len(record.label) > _MAX_LABEL_LENGTH:
        raise IssueValidationError("evidence label is invalid.")
    if "<" in record.label or ">" in record.label:
        raise IssueValidationError("evidence label contains unsafe markup.")
    if not record.execution_id.strip():
        raise IssueValidationError("evidence execution_id is required.")
    for field_name, value in (
        ("observed_at", record.observed_at),
        ("captured_at", record.captured_at),
    ):
        if value.tzinfo is None or value.utcoffset() is None:
            raise IssueValidationError(f"evidence {field_name} must be timezone-aware.")
