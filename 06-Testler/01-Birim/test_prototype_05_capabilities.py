"""DQ-CAP-PROTOTYPE-05 birim testleri: bildirim adaptörleri, lab kapıları, strateji motoru."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from veri_kalitesi.environment_security.errors import EnvironmentPolicyBlockedError
from veri_kalitesi.environment_security.lab_gate import (
    LabAdapterGate,
    LabGateEvidence,
    LabGateStatus,
    StaticLabEnvironmentProvider,
)
from veri_kalitesi.executions.errors import ExecutionValidationError
from veri_kalitesi.executions.strategy_engine import (
    CheckpointState,
    ExecutionStrategy,
    ExecutionStrategyEngine,
    ExecutionStrategyPolicy,
    StrategyResolutionStatus,
    WatermarkContract,
)
from veri_kalitesi.notifications.channel_adapters import (
    ChannelDeliveryStatus,
    ChannelKind,
    ChannelRoute,
    FakeChannelAdapter,
    NotificationChannelDispatcher,
    NotificationChannelPolicy,
)
from veri_kalitesi.notifications.errors import NotificationValidationError
from veri_kalitesi.notifications.models import (
    NotificationEvent,
    NotificationEventType,
    NotificationScopeType,
)


NOW = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)

# Prototip laboratuvari kanit omeri (DQ-CAP-012); surumlu politikaya
# tasinana kadar testlerde kapida acik verilir.
_LAB_EVIDENCE_AGE_SECONDS = 3600


def _lab_gate(provider, *, clock=lambda: NOW):
    return LabAdapterGate(
        provider,
        max_evidence_age_seconds=_LAB_EVIDENCE_AGE_SECONDS,
        clock=clock,
    )


# ---------------------------------------------------------------------------
# DQ-CAP-009: Notification channel adapters
# ---------------------------------------------------------------------------


def _event(
    event_type: NotificationEventType = NotificationEventType.QUALITY_THRESHOLD,
    dedup_key: str = "dedup-key-1",
) -> NotificationEvent:
    return NotificationEvent(
        event_type=event_type,
        scope_type=NotificationScopeType.RULE,
        scope_id=str(uuid4()),
        deduplication_key=dedup_key,
        occurred_at=NOW - timedelta(minutes=1),
        correlation_id=str(uuid4()),
    )


def _policy(**overrides) -> NotificationChannelPolicy:
    defaults = {
        "version": "NOTIFICATION_CHANNEL_V1",
        "routes": (
            ChannelRoute(
                channel=ChannelKind.EMAIL,
                event_types=frozenset(
                    {
                        NotificationEventType.QUALITY_THRESHOLD,
                        NotificationEventType.CRITICAL_RULE_FAILURE,
                    }
                ),
            ),
            ChannelRoute(
                channel=ChannelKind.MESSAGING,
                event_types=frozenset({NotificationEventType.TECHNICAL_ERROR}),
            ),
        ),
        "dedup_window_seconds": 300,
    }
    defaults.update(overrides)
    return NotificationChannelPolicy(**defaults)


class TestNotificationChannelPolicy:
    def test_valid_policy_is_accepted(self) -> None:
        policy = _policy()
        assert policy.version == "NOTIFICATION_CHANNEL_V1"
        assert len(policy.routes) == 2

    def test_empty_version_rejected(self) -> None:
        with pytest.raises(NotificationValidationError):
            _policy(version="")

    def test_negative_dedup_window_rejected(self) -> None:
        with pytest.raises(NotificationValidationError):
            _policy(dedup_window_seconds=-1)

    def test_policy_requires_dedup_window(self) -> None:
        # dedup_window_seconds artik zorunlu; verilmeden kurulamaz (fail-closed).
        with pytest.raises(TypeError):
            NotificationChannelPolicy(
                version="NOTIFICATION_CHANNEL_V1",
                routes=(),
            )


class TestNotificationChannelDispatcher:
    def test_routes_matching_event_to_email(self) -> None:
        email = FakeChannelAdapter(ChannelKind.EMAIL)
        dispatcher = NotificationChannelDispatcher(
            _policy(),
            {ChannelKind.EMAIL: email},
            clock=lambda: NOW,
        )
        event = _event(NotificationEventType.QUALITY_THRESHOLD)

        outcome = dispatcher.dispatch(event)

        assert not outcome.suppressed
        assert len(outcome.results) == 1
        assert outcome.results[0].channel is ChannelKind.EMAIL
        assert outcome.results[0].status is ChannelDeliveryStatus.DELIVERED
        assert len(email.delivered_log) == 1

    def test_non_matching_event_type_not_routed(self) -> None:
        email = FakeChannelAdapter(ChannelKind.EMAIL)
        dispatcher = NotificationChannelDispatcher(
            _policy(),
            {ChannelKind.EMAIL: email},
            clock=lambda: NOW,
        )
        event = _event(NotificationEventType.ISSUE_ASSIGNED)

        outcome = dispatcher.dispatch(event)

        assert not outcome.suppressed
        assert len(outcome.results) == 0
        assert len(email.delivered_log) == 0

    def test_dedup_suppression_within_window(self) -> None:
        email = FakeChannelAdapter(ChannelKind.EMAIL)
        dispatcher = NotificationChannelDispatcher(
            _policy(dedup_window_seconds=300),
            {ChannelKind.EMAIL: email},
            clock=lambda: NOW,
        )
        event = _event(dedup_key="same-key")

        first = dispatcher.dispatch(event)
        second = dispatcher.dispatch(event)

        assert not first.suppressed
        assert second.suppressed
        assert len(email.delivered_log) == 1

    def test_dedup_window_expires(self) -> None:
        email = FakeChannelAdapter(ChannelKind.EMAIL)
        times = [NOW, NOW + timedelta(seconds=301)]
        call_count = [0]

        def advancing_clock() -> datetime:
            idx = min(call_count[0], len(times) - 1)
            call_count[0] += 1
            return times[idx]

        dispatcher = NotificationChannelDispatcher(
            _policy(dedup_window_seconds=300),
            {ChannelKind.EMAIL: email},
            clock=advancing_clock,
        )
        event1 = _event(dedup_key="expire-key")
        event2 = _event(dedup_key="expire-key")

        first = dispatcher.dispatch(event1)
        second = dispatcher.dispatch(event2)

        assert not first.suppressed
        assert not second.suppressed

    def test_idempotency_same_event_not_redelivered(self) -> None:
        email = FakeChannelAdapter(ChannelKind.EMAIL)
        dispatcher = NotificationChannelDispatcher(
            _policy(),
            {ChannelKind.EMAIL: email},
            clock=lambda: NOW,
        )
        event = _event(dedup_key="key-a")

        dispatcher.dispatch(event)
        # Manually reset dedup log to allow re-dispatch of same event_id
        dispatcher._dedup_log.clear()
        outcome = dispatcher.dispatch(event)

        # Idempotency prevents re-delivery even if dedup doesn't catch it
        assert len(outcome.results) == 1
        assert outcome.results[0].status is ChannelDeliveryStatus.DELIVERED
        # But adapter only received it once (idempotency key matched)
        assert len(email.delivered_log) == 1

    def test_adapter_failure_does_not_raise(self) -> None:
        disabled = FakeChannelAdapter(ChannelKind.EMAIL, _enabled=False)
        dispatcher = NotificationChannelDispatcher(
            _policy(),
            {ChannelKind.EMAIL: disabled},
            clock=lambda: NOW,
        )
        event = _event()

        outcome = dispatcher.dispatch(event)

        assert len(outcome.results) == 1
        assert outcome.results[0].status is ChannelDeliveryStatus.FAILED

    def test_missing_adapter_reports_failed(self) -> None:
        dispatcher = NotificationChannelDispatcher(
            _policy(),
            {},  # No adapters registered
            clock=lambda: NOW,
        )
        event = _event()

        outcome = dispatcher.dispatch(event)

        assert len(outcome.results) == 1
        assert outcome.results[0].status is ChannelDeliveryStatus.FAILED

    def test_empty_routes_rejected(self) -> None:
        with pytest.raises(NotificationValidationError):
            NotificationChannelDispatcher(
                _policy(routes=()),
                {},
                clock=lambda: NOW,
            )


# ---------------------------------------------------------------------------
# DQ-CAP-012: Lab security gates
# ---------------------------------------------------------------------------


def _lab_evidence(
    *,
    gate_status: LabGateStatus = LabGateStatus.OPEN,
    classification: str = "PrototypeVerified",
    data_origin: str = "SYNTHETIC",
    environment: str = "LOCAL",
    verified_at: datetime = NOW,
) -> LabGateEvidence:
    return LabGateEvidence(
        lab_id="LAB-01",
        policy_version="ENTERPRISE-LAB-01-v1",
        classification=classification,
        environment=environment,
        data_origin=data_origin,
        gate_status=gate_status,
        verified_at=verified_at,
        checks=("PINNED_CONFIGURATION_VERIFIED",),
    )


class TestLabAdapterGate:
    def test_open_lab_passes(self) -> None:
        gate = _lab_gate(
            StaticLabEnvironmentProvider(_lab_evidence()),
            clock=lambda: NOW,
        )
        evidence = gate.verify_open()
        assert evidence.gate_status is LabGateStatus.OPEN

    def test_missing_evidence_fails_closed(self) -> None:
        gate = _lab_gate(
            StaticLabEnvironmentProvider(None),
            clock=lambda: NOW,
        )
        with pytest.raises(EnvironmentPolicyBlockedError, match="LAB_EVIDENCE_MISSING"):
            gate.verify_open()

    def test_closed_gate_blocks(self) -> None:
        gate = _lab_gate(
            StaticLabEnvironmentProvider(_lab_evidence(gate_status=LabGateStatus.CLOSED)),
            clock=lambda: NOW,
        )
        with pytest.raises(EnvironmentPolicyBlockedError, match="LAB_GATE_CLOSED"):
            gate.verify_open()

    def test_wrong_classification_blocks(self) -> None:
        gate = _lab_gate(
            StaticLabEnvironmentProvider(_lab_evidence(classification="ProductionReady")),
            clock=lambda: NOW,
        )
        with pytest.raises(EnvironmentPolicyBlockedError, match="LAB_CLASSIFICATION_INVALID"):
            gate.verify_open()

    def test_non_synthetic_origin_blocks(self) -> None:
        gate = _lab_gate(
            StaticLabEnvironmentProvider(_lab_evidence(data_origin="BANK_PRODUCTION")),
            clock=lambda: NOW,
        )
        with pytest.raises(EnvironmentPolicyBlockedError, match="LAB_DATA_ORIGIN_NOT_SYNTHETIC"):
            gate.verify_open()

    def test_production_environment_blocks(self) -> None:
        gate = _lab_gate(
            StaticLabEnvironmentProvider(_lab_evidence(environment="PRODUCTION")),
            clock=lambda: NOW,
        )
        with pytest.raises(
            EnvironmentPolicyBlockedError, match="LAB_PRODUCTION_ENVIRONMENT_FORBIDDEN"
        ):
            gate.verify_open()

    def test_expired_evidence_blocks(self) -> None:
        old = NOW - timedelta(seconds=3601)
        gate = _lab_gate(
            StaticLabEnvironmentProvider(_lab_evidence(verified_at=old)),
            clock=lambda: NOW,
        )
        with pytest.raises(EnvironmentPolicyBlockedError, match="LAB_EVIDENCE_EXPIRED"):
            gate.verify_open()

    def test_guard_requires_operation_name(self) -> None:
        gate = _lab_gate(
            StaticLabEnvironmentProvider(_lab_evidence()),
            clock=lambda: NOW,
        )
        with pytest.raises(EnvironmentPolicyBlockedError, match="LAB_GUARD_OPERATION_INVALID"):
            gate.guard("")

    def test_guard_passes_with_valid_operation(self) -> None:
        gate = _lab_gate(
            StaticLabEnvironmentProvider(_lab_evidence()),
            clock=lambda: NOW,
        )
        evidence = gate.guard("servicenow.create_ticket")
        assert evidence.lab_id == "LAB-01"

    def test_gate_requires_max_evidence_age_seconds(self) -> None:
        # max_evidence_age_seconds artik zorunlu; verilmeden kurulamaz.
        with pytest.raises(TypeError):
            LabAdapterGate(StaticLabEnvironmentProvider(_lab_evidence()))


# ---------------------------------------------------------------------------
# DQ-CAP-013: Deterministic execution strategy engine
# ---------------------------------------------------------------------------


def _strategy_policy(
    *,
    approved: bool = True,
    strategies: frozenset[ExecutionStrategy] | None = None,
) -> ExecutionStrategyPolicy:
    return ExecutionStrategyPolicy(
        version="EXECUTION_STRATEGY_V1",
        approved=approved,
        # Prototip timeout'u (DQ-CAP-013); surumlu politikaya tasinana kadar.
        timeout_seconds=3600,
        allowed_strategies=strategies or frozenset(ExecutionStrategy),
    )


class TestExecutionStrategyEngine:
    def setup_method(self) -> None:
        self.engine = ExecutionStrategyEngine()

    def test_full_strategy_resolves_from_approved_policy(self) -> None:
        result = self.engine.resolve(
            ExecutionStrategy.FULL,
            policy=_strategy_policy(),
        )
        assert result.status is StrategyResolutionStatus.RESOLVED
        assert result.strategy is ExecutionStrategy.FULL

    def test_no_policy_rejects_without_escalation(self) -> None:
        result = self.engine.resolve(
            ExecutionStrategy.FULL,
            policy=None,
        )
        assert result.status is StrategyResolutionStatus.REJECTED_NO_POLICY
        assert result.strategy is None

    def test_unapproved_policy_rejects(self) -> None:
        result = self.engine.resolve(
            ExecutionStrategy.FULL,
            policy=_strategy_policy(approved=False),
        )
        assert result.status is StrategyResolutionStatus.REJECTED_POLICY_NOT_APPROVED
        assert result.strategy is None

    def test_incremental_without_watermark_rejects(self) -> None:
        result = self.engine.resolve(
            ExecutionStrategy.INCREMENTAL,
            policy=_strategy_policy(),
            watermark=None,
        )
        assert result.status is StrategyResolutionStatus.REJECTED_NO_WATERMARK
        assert result.strategy is None

    def test_incremental_with_valid_watermark_resolves(self) -> None:
        wm = WatermarkContract(
            source_id="source-1",
            watermark_field="updated_at",
            watermark_kind="TIMESTAMP",
            contract_version="WM_V1",
        )
        result = self.engine.resolve(
            ExecutionStrategy.INCREMENTAL,
            policy=_strategy_policy(),
            watermark=wm,
            source_id="source-1",
        )
        assert result.status is StrategyResolutionStatus.RESOLVED
        assert result.strategy is ExecutionStrategy.INCREMENTAL
        assert result.watermark is wm

    def test_incremental_source_mismatch_rejects(self) -> None:
        wm = WatermarkContract(
            source_id="source-1",
            watermark_field="updated_at",
            watermark_kind="TIMESTAMP",
            contract_version="WM_V1",
        )
        result = self.engine.resolve(
            ExecutionStrategy.INCREMENTAL,
            policy=_strategy_policy(),
            watermark=wm,
            source_id="source-2",
        )
        assert result.status is StrategyResolutionStatus.REJECTED_NO_WATERMARK

    def test_partition_with_incomplete_checkpoint_rejects(self) -> None:
        checkpoints = {
            "p1": CheckpointState(partition_id="p1", completed=True),
            "p2": CheckpointState(partition_id="p2", completed=False),
        }
        result = self.engine.resolve(
            ExecutionStrategy.PARTITION,
            policy=_strategy_policy(),
            checkpoints=checkpoints,
        )
        assert result.status is StrategyResolutionStatus.REJECTED_NO_CHECKPOINT
        assert result.strategy is None

    def test_partition_with_all_completed_checkpoints_resolves(self) -> None:
        checkpoints = {
            "p1": CheckpointState(partition_id="p1", completed=True),
            "p2": CheckpointState(partition_id="p2", completed=True),
        }
        result = self.engine.resolve(
            ExecutionStrategy.PARTITION,
            policy=_strategy_policy(),
            checkpoints=checkpoints,
        )
        assert result.status is StrategyResolutionStatus.RESOLVED
        assert result.strategy is ExecutionStrategy.PARTITION

    def test_strategy_not_in_policy_rejects(self) -> None:
        result = self.engine.resolve(
            ExecutionStrategy.INCREMENTAL,
            policy=_strategy_policy(
                strategies=frozenset({ExecutionStrategy.FULL, ExecutionStrategy.SAMPLE})
            ),
        )
        assert result.status is StrategyResolutionStatus.REJECTED_NO_POLICY
        assert result.strategy is None

    def test_sample_strategy_resolves(self) -> None:
        result = self.engine.resolve(
            ExecutionStrategy.SAMPLE,
            policy=_strategy_policy(),
        )
        assert result.status is StrategyResolutionStatus.RESOLVED
        assert result.strategy is ExecutionStrategy.SAMPLE

    def test_aggregate_strategy_resolves(self) -> None:
        result = self.engine.resolve(
            ExecutionStrategy.AGGREGATE,
            policy=_strategy_policy(),
        )
        assert result.status is StrategyResolutionStatus.RESOLVED
        assert result.strategy is ExecutionStrategy.AGGREGATE

    def test_watermark_must_be_immutable(self) -> None:
        with pytest.raises(ExecutionValidationError):
            WatermarkContract(
                source_id="s1",
                watermark_field="f1",
                watermark_kind="OFFSET",
                contract_version="V1",
                immutable=False,
            )

    def test_policy_requires_version(self) -> None:
        with pytest.raises(ExecutionValidationError):
            ExecutionStrategyPolicy(
                version="",
                approved=True,
                timeout_seconds=3600,
                allowed_strategies=frozenset({ExecutionStrategy.FULL}),
            )

    def test_policy_requires_timeout_seconds(self) -> None:
        # timeout_seconds artik zorunlu; verilmeden kurulamaz.
        with pytest.raises(TypeError):
            ExecutionStrategyPolicy(
                version="EXECUTION_STRATEGY_V1",
                approved=True,
                allowed_strategies=frozenset(ExecutionStrategy),
            )
