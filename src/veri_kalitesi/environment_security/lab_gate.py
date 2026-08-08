"""DQ-CAP-012: Kapılı sentetik güvenlik adaptörleri için fail-closed lab kapısı.

Sentetik IdP, yerel dosya tabanlı secret, fake SIEM/ServiceNow yalnız açık lab
ortamında çalışır. Gerçek IdP/PAM/KMS/SIEM/WORM erişimi olmadan
PrototypeVerified üstü durum üretilemez. Bu modül, adaptör işlemlerinden önce
lab ortamının açık ve kanıtlı olduğunu doğrular.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Protocol

from veri_kalitesi.environment_security.errors import (
    EnvironmentPolicyBlockedError,
)


class LabGateStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class LabGateEvidence:
    """Lab kapısından geçen doğrulama kanıtı."""

    lab_id: str
    policy_version: str
    classification: str
    environment: str
    data_origin: str
    gate_status: LabGateStatus
    verified_at: datetime
    checks: tuple[str, ...]


class LabEnvironmentProvider(Protocol):
    """Lab ortam kanıtını sağlayan sözleşme."""

    def current_evidence(self) -> LabGateEvidence | None:
        """Mevcut lab kanıtını döndürür; kanıt yoksa None (fail-closed)."""
        ...


class LabAdapterGate:
    """Sentetik adaptör işlemlerinden önce fail-closed lab doğrulaması.

    Kurallar:
    - Kanıt yoksa işlem engellenir (fail-closed).
    - Lab kapısı CLOSED ise işlem engellenir.
    - Classification 'PrototypeVerified' değilse işlem engellenir.
    - Data origin 'SYNTHETIC' değilse işlem engellenir.
    - Environment 'PRODUCTION' ise işlem engellenir.
    - Kanıt yaşı maksimum ömrü aştıysa işlem engellenir.
    """

    def __init__(
        self,
        provider: LabEnvironmentProvider,
        *,
        max_evidence_age_seconds: int,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._provider = provider
        self._max_evidence_age_seconds = max_evidence_age_seconds
        self._clock = clock

    def verify_open(self) -> LabGateEvidence:
        """Lab kapısının açık olduğunu doğrular; değilse fail-closed hata fırlatır."""
        try:
            evidence = self._provider.current_evidence()
        except Exception as exc:
            raise EnvironmentPolicyBlockedError("LAB_EVIDENCE_PROVIDER_UNAVAILABLE") from exc

        if evidence is None:
            raise EnvironmentPolicyBlockedError("LAB_EVIDENCE_MISSING")

        if evidence.gate_status is not LabGateStatus.OPEN:
            raise EnvironmentPolicyBlockedError("LAB_GATE_CLOSED")

        if evidence.classification != "PrototypeVerified":
            raise EnvironmentPolicyBlockedError("LAB_CLASSIFICATION_INVALID")

        if evidence.data_origin != "SYNTHETIC":
            raise EnvironmentPolicyBlockedError("LAB_DATA_ORIGIN_NOT_SYNTHETIC")

        if evidence.environment == "PRODUCTION":
            raise EnvironmentPolicyBlockedError("LAB_PRODUCTION_ENVIRONMENT_FORBIDDEN")

        now = self._clock()
        if now.tzinfo is None:
            raise EnvironmentPolicyBlockedError("LAB_CLOCK_NOT_AWARE")
        age = (now - evidence.verified_at).total_seconds()
        if age > self._max_evidence_age_seconds or age < 0:
            raise EnvironmentPolicyBlockedError("LAB_EVIDENCE_EXPIRED")

        return evidence

    def guard(self, operation: str) -> LabGateEvidence:
        """Adaptör işlemi öncesi kapı doğrulaması. Operation adı audit içindir."""
        if not operation or not operation.strip():
            raise EnvironmentPolicyBlockedError("LAB_GUARD_OPERATION_INVALID")
        return self.verify_open()


@dataclass(frozen=True)
class StaticLabEnvironmentProvider:
    """Test/geliştirme için sabit kanıt sağlayan adaptör."""

    evidence: LabGateEvidence | None

    def current_evidence(self) -> LabGateEvidence | None:
        return self.evidence
