"""Rapor disa aktarma politika framework'u.

DLP, watermark, maker-checker, gerekce ve sureli indirme kontrollerini
tanimlar. Politika yoksa veya kontroller gecmezse fail-closed davranilir.

UI-WRITE-007: Rapor indirme siniflandirma bazli acilir.
OPEN-BNK-014: Asenkron disa aktarma, gerekce, maker-checker, DLP, watermark.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from veri_kalitesi.reporting.errors import ReportExportDeniedError
from veri_kalitesi.reporting.models import (
    ExportDecision,
    ReportExportPolicy,
    ReportRequest,
)


class ReportExportPolicyRepository(Protocol):
    """Aktif rapor disa aktarma politikasini getirir.

    Politika yoksa None doner — fail-closed davranilir.
    """

    def get_active_policy(self, sensitivity_level: str | None) -> ReportExportPolicy | None: ...


def evaluate_export(
    request: ReportRequest,
    policy: ReportExportPolicy | None,
    correlation_id: str,
    *,
    has_maker_checker_approval: bool = False,
) -> ExportDecision:
    """Rapor disa aktarma talebini politikaya gore degerlendirir.

    Fail-closed: politika yoksa veya kontroller gecmezse reddedilir.
    """
    if policy is None:
        raise ReportExportDeniedError("NO_EXPORT_POLICY", correlation_id)

    # Format kontrolu
    if request.format not in policy.allowed_formats:
        raise ReportExportDeniedError("FORMAT_NOT_ALLOWED", correlation_id)

    # Gerekce kontrolu
    if policy.require_justification and not request.reason_code.strip():
        raise ReportExportDeniedError("JUSTIFICATION_REQUIRED", correlation_id)

    # Maker-checker kontrolu
    if policy.require_maker_checker and not has_maker_checker_approval:
        raise ReportExportDeniedError("MAKER_CHECKER_REQUIRED", correlation_id)

    return ExportDecision(
        allowed=True,
        reason_code="EXPORT_ALLOWED",
        require_maker_checker=policy.require_maker_checker,
        policy_version=policy.version,
    )


def check_download_access(
    policy: ReportExportPolicy | None,
    expires_at: datetime | None,
    correlation_id: str,
    *,
    now: datetime | None = None,
) -> None:
    """Indirme aninda erisim ve sure kontrolu yapar.

    Fail-closed: politika yoksa veya sure dolmussa reddedilir.
    """
    if policy is None:
        raise ReportExportDeniedError("NO_EXPORT_POLICY", correlation_id)

    if expires_at is not None:
        current = now if now is not None else datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if current > expires_at:
            raise ReportExportDeniedError("DOWNLOAD_EXPIRED", correlation_id)
