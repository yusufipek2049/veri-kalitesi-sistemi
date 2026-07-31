"""DQ-CAP-013: Deterministik yürütme strateji motoru.

Stratejiler full/partition/incremental/sample/aggregate olarak modellenir.
Incremental yalnız kaynak-özel, değişmez watermark sözleşmesi varsa; resume
yalnız tamamlanmış partition/checkpoint sınırında yapılır. Concurrency, timeout,
kota, maliyet bütçesi ve çalışma penceresi onaylı politikadan gelir; eksikse
daha pahalı stratejiye otomatik geçilmez.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Mapping

from veri_kalitesi.executions.errors import ExecutionValidationError


# ---------------------------------------------------------------------------
# Strategy models
# ---------------------------------------------------------------------------


class ExecutionStrategy(str, Enum):
    FULL = "FULL"
    PARTITION = "PARTITION"
    INCREMENTAL = "INCREMENTAL"
    SAMPLE = "SAMPLE"
    AGGREGATE = "AGGREGATE"


class StrategyResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    REJECTED_NO_POLICY = "REJECTED_NO_POLICY"
    REJECTED_NO_WATERMARK = "REJECTED_NO_WATERMARK"
    REJECTED_NO_CHECKPOINT = "REJECTED_NO_CHECKPOINT"
    REJECTED_POLICY_NOT_APPROVED = "REJECTED_POLICY_NOT_APPROVED"


@dataclass(frozen=True)
class WatermarkContract:
    """Kaynak-özel değişmez watermark sözleşmesi.

    Incremental strateji yalnız bu sözleşme varsa kullanılabilir.
    """

    source_id: str
    watermark_field: str
    watermark_kind: str  # TIMESTAMP, SEQUENCE, OFFSET
    contract_version: str
    immutable: bool = True

    def __post_init__(self) -> None:
        if not self.source_id or not self.source_id.strip():
            raise ExecutionValidationError("Watermark source_id is required.")
        if not self.watermark_field or not self.watermark_field.strip():
            raise ExecutionValidationError("Watermark field is required.")
        if not self.watermark_kind or not self.watermark_kind.strip():
            raise ExecutionValidationError("Watermark kind is required.")
        if not self.immutable:
            raise ExecutionValidationError("Watermark contract must be immutable.")


@dataclass(frozen=True)
class CheckpointState:
    """Tamamlanmış partition/checkpoint durumu (resume için)."""

    partition_id: str
    completed: bool
    resumed_at: datetime | None = None


@dataclass(frozen=True)
class ExecutionStrategyPolicy:
    """Onaylı yürütme strateji politikası.

    Politika yoksa veya onaylı değilse daha pahalı stratejiye otomatik geçilmez.
    """

    version: str
    approved: bool
    allowed_strategies: frozenset[ExecutionStrategy]
    max_concurrency: int = 1
    timeout_seconds: int = 3600
    cost_budget_units: int | None = None
    working_window_start: str | None = None
    working_window_end: str | None = None

    def __post_init__(self) -> None:
        if not self.version or not self.version.strip():
            raise ExecutionValidationError("Strategy policy version is required.")
        if not self.allowed_strategies:
            raise ExecutionValidationError("Strategy policy must allow at least one strategy.")
        if self.max_concurrency < 1:
            raise ExecutionValidationError("Strategy policy concurrency must be positive.")
        if self.timeout_seconds < 1:
            raise ExecutionValidationError("Strategy policy timeout must be positive.")


@dataclass(frozen=True)
class StrategyResolution:
    """Strateji çözümleme sonucu."""

    strategy: ExecutionStrategy | None
    status: StrategyResolutionStatus
    reason: str
    policy_version: str | None = None
    watermark: WatermarkContract | None = None


# ---------------------------------------------------------------------------
# Strategy engine
# ---------------------------------------------------------------------------


class ExecutionStrategyEngine:
    """Deterministik yürütme strateji çözümleyicisi.

    Kurallar:
    - Politika yoksa veya onaylı değilse → REJECTED, otomatik geçiş yok.
    - INCREMENTAL yalnız watermark sözleşmesi varsa.
    - PARTITION resume yalnız tamamlanmış checkpoint varsa.
    - Strateji politikada izin verilenler arasında olmalı.
    - Eksik politika daha pahalı stratejiye otomatik geçmez.
    """

    def resolve(
        self,
        requested: ExecutionStrategy,
        *,
        policy: ExecutionStrategyPolicy | None,
        watermark: WatermarkContract | None = None,
        checkpoints: Mapping[str, CheckpointState] | None = None,
        source_id: str | None = None,
    ) -> StrategyResolution:
        """İstenen stratejiyi politika ve sözleşmelere göre çözer."""
        # No policy → reject (fail-closed, no auto-escalation)
        if policy is None:
            return StrategyResolution(
                strategy=None,
                status=StrategyResolutionStatus.REJECTED_NO_POLICY,
                reason="No execution strategy policy available; refusing to escalate.",
            )

        # Policy not approved → reject
        if not policy.approved:
            return StrategyResolution(
                strategy=None,
                status=StrategyResolutionStatus.REJECTED_POLICY_NOT_APPROVED,
                reason="Execution strategy policy is not approved.",
                policy_version=policy.version,
            )

        # Strategy not in allowed set → reject
        if requested not in policy.allowed_strategies:
            return StrategyResolution(
                strategy=None,
                status=StrategyResolutionStatus.REJECTED_NO_POLICY,
                reason=f"Strategy {requested.value} is not in approved policy.",
                policy_version=policy.version,
            )

        # INCREMENTAL requires watermark
        if requested is ExecutionStrategy.INCREMENTAL:
            if watermark is None:
                return StrategyResolution(
                    strategy=None,
                    status=StrategyResolutionStatus.REJECTED_NO_WATERMARK,
                    reason="Incremental strategy requires a source-specific watermark contract.",
                    policy_version=policy.version,
                )
            if not watermark.immutable:
                return StrategyResolution(
                    strategy=None,
                    status=StrategyResolutionStatus.REJECTED_NO_WATERMARK,
                    reason="Watermark contract must be immutable.",
                    policy_version=policy.version,
                )
            if source_id is not None and watermark.source_id != source_id:
                return StrategyResolution(
                    strategy=None,
                    status=StrategyResolutionStatus.REJECTED_NO_WATERMARK,
                    reason="Watermark contract source does not match execution source.",
                    policy_version=policy.version,
                )
            return StrategyResolution(
                strategy=ExecutionStrategy.INCREMENTAL,
                status=StrategyResolutionStatus.RESOLVED,
                reason="Incremental strategy resolved with valid watermark contract.",
                policy_version=policy.version,
                watermark=watermark,
            )

        # PARTITION resume requires completed checkpoint
        if requested is ExecutionStrategy.PARTITION and checkpoints:
            incomplete = [
                pid for pid, cp in checkpoints.items() if not cp.completed
            ]
            if incomplete:
                return StrategyResolution(
                    strategy=None,
                    status=StrategyResolutionStatus.REJECTED_NO_CHECKPOINT,
                    reason=f"Incomplete checkpoints block resume: {incomplete}.",
                    policy_version=policy.version,
                )

        # All other strategies resolve directly from policy
        return StrategyResolution(
            strategy=requested,
            status=StrategyResolutionStatus.RESOLVED,
            reason=f"Strategy {requested.value} resolved from approved policy.",
            policy_version=policy.version,
        )
