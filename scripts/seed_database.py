#!/usr/bin/env python3
"""PostgreSQL seed script — Alembic migration + kapsamli demo veri.

Kullanim:
    # Baglanti bilgisi .env veya ortam degiskeninden okunur:
    #   DATA_QUALITY_DATABASE_URL=postgresql+psycopg://app:secret@localhost/data_quality
    DATA_QUALITY_DATABASE_URL="postgresql+psycopg://app:pwd@localhost/data_quality" \
        python scripts/seed_database.py
"""

# ruff: noqa: E402 — sys.path düzeni sonrası import

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# ---------------------------------------------------------------------------
# Path setup — src/ import edilebilir olsun
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# .env dosyasi varsa yukle
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig

from veri_kalitesi.audit.models import AuditEvent, AuditEventInput, AuditResult, PreparedAuditEvent
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.policies import build_default_redaction_policy
from veri_kalitesi.data_protection.policy import ClassificationCode
from veri_kalitesi.data_sources.models import (
    DataSource,
    DataSourceStatus,
    DataField,
    DataProfile,
    Dataset,
    DatasetType,
    Criticality,
    MetadataDiscoveryResult,
    ProfileMethod,
    ProfileStatus,
    SourceType,
)
from veri_kalitesi.data_sources.postgresql_repository import PostgreSQLDataSourceRepository
from veri_kalitesi.executions.models import (
    ExecutionMode,
    ExecutionStatus,
    ExecutionType,
    MeasurementStatus,
    RuleExecution,
    RuleExecutionResult,
    WorkloadClass,
)
from veri_kalitesi.executions.postgresql_repository import PostgreSQLExecutionRepository
from veri_kalitesi.executions.postgresql_source_usage import (
    PostgreSQLSourceUsagePolicyRepository,
)
from veri_kalitesi.executions.source_usage_policies import (
    SourceUsagePolicy,
    SourceUsagePolicyStatus,
)
from veri_kalitesi.issues.models import (
    DataQualityIssue,
    IssueHistoryEntry,
    IssuePriority,
    IssueScopeType,
    IssueSourceEventType,
    IssueStatus,
    IssueTriggerType,
)
from veri_kalitesi.issues.postgresql_repository import PostgreSQLIssueRepository
from veri_kalitesi.jobs.models import BackgroundJob, JobCompletionOutcome, JobStatus
from veri_kalitesi.jobs.postgresql_repository import PostgreSQLJobQueueRepository
from veri_kalitesi.persistence import (
    DEFAULT_SCHEMA_NAME,
    DatabaseSettings,
    create_session_factory,
)
from veri_kalitesi.reporting.models import ReportFormat, ReportRequest, ReportType
from veri_kalitesi.reporting.repository import (
    PostgreSQLReportRepository,
    PostgreSQLReportScheduleRepository,
)
from veri_kalitesi.reporting.scheduling import ReportSchedule, ScheduleType
from veri_kalitesi.rules.models import (
    QualityDimension,
    QualityRule,
    RuleCriticality,
    RuleScopeType,
    RuleStatus,
    RuleType,
    RuleVersion,
)
from veri_kalitesi.rules.postgresql_repository import PostgreSQLRuleRepository
from veri_kalitesi.scoring.models import ScoreLevel, ScoreScopeType, ScoreStatus
from veri_kalitesi.scoring.postgresql_repository import score_tables

ALEMBIC_INI = ROOT / "alembic.ini"

# ---------------------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    return _utc_now() - timedelta(days=n)


def _hours_ago(n: int) -> datetime:
    return _utc_now() - timedelta(hours=n)


class _SeedPreparedAuditRepository:
    """Seed icin PreparedAuditRepository protocol uygulamasi."""

    def __init__(self) -> None:
        self._seq = 0

    def append(self, prepared: PreparedAuditEvent) -> AuditEvent:
        self._seq += 1
        return AuditEvent(
            sequence_no=self._seq,
            event_id=prepared.event_id,
            event_version=prepared.event_version,
            occurred_at=prepared.occurred_at,
            actor_id=prepared.actor_id,
            actor_type=prepared.actor_type,
            session_id_digest=prepared.session_id_digest,
            correlation_id=prepared.correlation_id,
            action=prepared.action,
            object_type=prepared.object_type,
            object_id=prepared.object_id,
            result=prepared.result,
            reason_code=prepared.reason_code,
            old_value_summary=prepared.old_value_summary,
            new_value_summary=prepared.new_value_summary,
            old_value_digest=prepared.old_value_digest,
            new_value_digest=prepared.new_value_digest,
            redacted_fields=prepared.redacted_fields,
            redaction_policy_version=prepared.redaction_policy_version,
            previous_event_hash=uuid4().hex,
            event_hash=uuid4().hex,
        )


def _make_audit_event(
    audit_outbox: PostgreSQLTransactionalAudit,
    action: str,
    object_type: str,
    object_id: str | None = None,
    reason_code: str = "SEED",
    new_values: dict | None = None,
) -> PreparedAuditEvent:
    event = AuditEventInput(
        actor_id="SEED_SYSTEM",
        actor_type="SYSTEM",
        correlation_id=str(uuid4()),
        action=action,
        object_type=object_type,
        object_id=object_id or str(uuid4()),
        result=AuditResult.SUCCESS,
        reason_code=reason_code,
        old_values={},
        new_values=new_values or {"seeded": True},
        occurred_at=_utc_now(),
    )
    return audit_outbox.prepare(event)


def _idempotency_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _already_seeded(session_factory, schema: str) -> bool:
    """Check if seed data already exists in the database."""
    from sqlalchemy import text

    with session_factory() as session:
        count = session.scalar(text(f'SELECT COUNT(*) FROM "{schema}".data_sources'))
        return count > 0


def _make_seed_evidence() -> dict:
    """Create valid violation evidence for seed execution results."""
    return {
        "fingerprint": "sha256:" + hashlib.sha256(b"seed-violation-fingerprint").hexdigest(),
        "masked_samples": [
            "hmac-sha256://seed-sample/" + hashlib.sha256(f"seed-sample-{i}".encode()).hexdigest()
            for i in range(3)
        ],
        "expected_summary": {"population_count": 2_500_000, "eligible_count": 2_500_000},
        "actual_summary": {"passed_count": 2_499_800, "failed_count": 200},
        "query_reference": "query-template://seed/dq-acc-001",
        "plan_reference": "plan://seed/dq-acc-001",
    }


# ---------------------------------------------------------------------------
# Alembic migration
# ---------------------------------------------------------------------------


def run_alembic_migration(settings: DatabaseSettings) -> None:
    print(f"[1/10] Alembic migration calistiriliyor ({settings.safe_url()}) ...")
    cfg = AlembicConfig(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", settings.url.render_as_string(hide_password=False))
    cfg.set_main_option("data_quality_schema", settings.schema)
    alembic_command.upgrade(cfg, "head")
    print("      Migration tamamlandi.")


# ---------------------------------------------------------------------------
# Seed fonksiyonlari
# ---------------------------------------------------------------------------


def seed_data_sources(
    repo: PostgreSQLDataSourceRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    schema: str,
) -> dict[str, DataSource]:
    """3 farkli veri kaynagi ekler."""
    print("[2/10] Veri kaynaklari ekleniyor ...")
    sources = {
        "pg_core_banking": DataSource(
            name="Core Banking PostgreSQL",
            source_type=SourceType.POSTGRESQL,
            connection_config={
                "host": "core-bank-pg.internal",
                "port": 5432,
                "database": "core_banking",
                "ssl_mode": "verify-full",
                "connect_timeout_seconds": 5,
                "statement_timeout_ms": 5000,
            },
            secret_reference="secret://datasources/core-banking-pg",
            owner_user_id="user-data-steward-01",
            status=DataSourceStatus.ACTIVE,
            revision=1,
            last_test_at=_days_ago(1),
            created_at=_days_ago(30),
        ),
        "mssql_risk": DataSource(
            name="Risk Analiz MSSQL",
            source_type=SourceType.MSSQL,
            connection_config={
                "host": "risk-mssql.internal",
                "port": 1433,
                "database": "risk_analytics",
                "ssl_mode": "verify-full",
                "connect_timeout_seconds": 5,
                "statement_timeout_ms": 10000,
            },
            secret_reference="secret://datasources/risk-mssql",
            owner_user_id="user-data-owner-01",
            status=DataSourceStatus.TEST_SUCCEEDED,
            revision=1,
            last_test_at=_days_ago(2),
            created_at=_days_ago(20),
        ),
        "csv_kyc_export": DataSource(
            name="KYC Export CSV",
            source_type=SourceType.CSV,
            connection_config={
                "host": "s3.internal",
                "port": 9000,
                "database": "kyc-exports",
                "ssl_mode": "verify-full",
                "connect_timeout_seconds": 5,
                "statement_timeout_ms": 3000,
            },
            secret_reference="secret://datasources/kyc-csv",
            owner_user_id="user-data-steward-01",
            status=DataSourceStatus.ACTIVE,
            revision=1,
            last_test_at=_hours_ago(6),
            created_at=_days_ago(15),
        ),
    }
    for key, source in sources.items():
        audit_event = _make_audit_event(
            audit_outbox,
            action="DATA_SOURCE_CREATED",
            object_type="DataSource",
            object_id=source.data_source_id,
            reason_code="SEED_DATA_SOURCE",
            new_values={"name": source.name, "source_type": source.source_type.value},
        )
        repo.add_data_source(source, audit_event=audit_event, audit_outbox=audit_outbox)
        print(f"      + {source.name} ({source.data_source_id[:8]}...)")
    return sources


def seed_metadata(
    repo: PostgreSQLDataSourceRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    sources: dict[str, DataSource],
    schema: str,
) -> dict[str, Dataset]:
    """Her kaynak icin dataset + field + discovery + profile ekler."""
    print("[3/10] Metadata (dataset, field, discovery, profile) ekleniyor ...")
    datasets: dict[str, Dataset] = {}

    # --- Core Banking datasets ---
    core_src = sources["pg_core_banking"]

    ds_accounts = Dataset(
        data_source_id=core_src.data_source_id,
        namespace=schema,
        name="accounts",
        dataset_type=DatasetType.TABLE,
        criticality=Criticality.CRITICAL,
        owner_user_id="user-data-steward-01",
        estimated_row_count=2_500_000,
    )
    ds_transactions = Dataset(
        data_source_id=core_src.data_source_id,
        namespace=schema,
        name="transactions",
        dataset_type=DatasetType.TABLE,
        criticality=Criticality.HIGH,
        owner_user_id="user-data-steward-01",
        estimated_row_count=45_000_000,
    )
    ds_customers = Dataset(
        data_source_id=core_src.data_source_id,
        namespace=schema,
        name="customers",
        dataset_type=DatasetType.TABLE,
        criticality=Criticality.CRITICAL,
        owner_user_id="user-data-owner-01",
        estimated_row_count=800_000,
    )

    fields_accounts = [
        DataField(
            dataset_id=ds_accounts.dataset_id,
            name="account_id",
            native_data_type="UUID",
            is_nullable=False,
            classification=ClassificationCode.BANK_SECRET,
        ),
        DataField(
            dataset_id=ds_accounts.dataset_id,
            name="customer_id",
            native_data_type="UUID",
            is_nullable=False,
            classification=ClassificationCode.BANK_SECRET,
        ),
        DataField(
            dataset_id=ds_accounts.dataset_id,
            name="iban",
            native_data_type="VARCHAR(34)",
            is_nullable=False,
            classification=ClassificationCode.BANK_SECRET,
        ),
        DataField(
            dataset_id=ds_accounts.dataset_id,
            name="balance",
            native_data_type="NUMERIC(18,2)",
            is_nullable=False,
            classification=ClassificationCode.INTERNAL,
        ),
        DataField(
            dataset_id=ds_accounts.dataset_id,
            name="currency",
            native_data_type="VARCHAR(3)",
            is_nullable=False,
            classification=ClassificationCode.INTERNAL,
        ),
        DataField(
            dataset_id=ds_accounts.dataset_id,
            name="status",
            native_data_type="VARCHAR(20)",
            is_nullable=False,
            classification=ClassificationCode.INTERNAL,
        ),
        DataField(
            dataset_id=ds_accounts.dataset_id,
            name="opened_at",
            native_data_type="TIMESTAMPTZ",
            is_nullable=False,
            classification=ClassificationCode.INTERNAL,
        ),
    ]
    fields_transactions = [
        DataField(
            dataset_id=ds_transactions.dataset_id,
            name="transaction_id",
            native_data_type="UUID",
            is_nullable=False,
            classification=ClassificationCode.BANK_SECRET,
        ),
        DataField(
            dataset_id=ds_transactions.dataset_id,
            name="account_id",
            native_data_type="UUID",
            is_nullable=False,
            classification=ClassificationCode.BANK_SECRET,
        ),
        DataField(
            dataset_id=ds_transactions.dataset_id,
            name="amount",
            native_data_type="NUMERIC(18,2)",
            is_nullable=False,
            classification=ClassificationCode.INTERNAL,
        ),
        DataField(
            dataset_id=ds_transactions.dataset_id,
            name="transaction_type",
            native_data_type="VARCHAR(30)",
            is_nullable=False,
            classification=ClassificationCode.INTERNAL,
        ),
        DataField(
            dataset_id=ds_transactions.dataset_id,
            name="executed_at",
            native_data_type="TIMESTAMPTZ",
            is_nullable=False,
            classification=ClassificationCode.INTERNAL,
        ),
        DataField(
            dataset_id=ds_transactions.dataset_id,
            name="reference",
            native_data_type="VARCHAR(200)",
            is_nullable=True,
            classification=ClassificationCode.INTERNAL,
        ),
    ]
    fields_customers = [
        DataField(
            dataset_id=ds_customers.dataset_id,
            name="customer_id",
            native_data_type="UUID",
            is_nullable=False,
            classification=ClassificationCode.PERSONAL_DATA,
        ),
        DataField(
            dataset_id=ds_customers.dataset_id,
            name="full_name",
            native_data_type="VARCHAR(200)",
            is_nullable=False,
            classification=ClassificationCode.PERSONAL_DATA,
        ),
        DataField(
            dataset_id=ds_customers.dataset_id,
            name="tax_number",
            native_data_type="VARCHAR(11)",
            is_nullable=True,
            classification=ClassificationCode.SPECIAL_CATEGORY_PERSONAL_DATA,
        ),
        DataField(
            dataset_id=ds_customers.dataset_id,
            name="email",
            native_data_type="VARCHAR(254)",
            is_nullable=True,
            classification=ClassificationCode.PERSONAL_DATA,
        ),
        DataField(
            dataset_id=ds_customers.dataset_id,
            name="segment",
            native_data_type="VARCHAR(30)",
            is_nullable=False,
            classification=ClassificationCode.INTERNAL,
        ),
        DataField(
            dataset_id=ds_customers.dataset_id,
            name="kyc_status",
            native_data_type="VARCHAR(20)",
            is_nullable=False,
            classification=ClassificationCode.INTERNAL,
        ),
    ]

    # --- Risk dataset ---
    risk_src = sources["mssql_risk"]
    ds_risk_scores = Dataset(
        data_source_id=risk_src.data_source_id,
        namespace=schema,
        name="risk_scores",
        dataset_type=DatasetType.TABLE,
        criticality=Criticality.HIGH,
        owner_user_id="user-data-owner-01",
        estimated_row_count=800_000,
    )
    fields_risk = [
        DataField(
            dataset_id=ds_risk_scores.dataset_id,
            name="customer_id",
            native_data_type="UNIQUEIDENTIFIER",
            is_nullable=False,
            classification=ClassificationCode.BANK_SECRET,
        ),
        DataField(
            dataset_id=ds_risk_scores.dataset_id,
            name="score_value",
            native_data_type="DECIMAL(5,2)",
            is_nullable=False,
            classification=ClassificationCode.CONFIDENTIAL,
        ),
        DataField(
            dataset_id=ds_risk_scores.dataset_id,
            name="score_date",
            native_data_type="DATETIME2",
            is_nullable=False,
            classification=ClassificationCode.INTERNAL,
        ),
        DataField(
            dataset_id=ds_risk_scores.dataset_id,
            name="model_version",
            native_data_type="VARCHAR(20)",
            is_nullable=False,
            classification=ClassificationCode.INTERNAL,
        ),
    ]

    # --- KYV CSV dataset ---
    kyc_src = sources["csv_kyc_export"]
    ds_kyc = Dataset(
        data_source_id=kyc_src.data_source_id,
        namespace=schema,
        name="kyc_records",
        dataset_type=DatasetType.FILE_SHEET,
        criticality=Criticality.HIGH,
        owner_user_id="user-data-steward-01",
        estimated_row_count=120_000,
    )
    fields_kyc = [
        DataField(
            dataset_id=ds_kyc.dataset_id,
            name="record_id",
            native_data_type="TEXT",
            is_nullable=False,
            classification=ClassificationCode.INTERNAL,
        ),
        DataField(
            dataset_id=ds_kyc.dataset_id,
            name="customer_id",
            native_data_type="TEXT",
            is_nullable=False,
            classification=ClassificationCode.PERSONAL_DATA,
        ),
        DataField(
            dataset_id=ds_kyc.dataset_id,
            name="kyc_level",
            native_data_type="TEXT",
            is_nullable=False,
            classification=ClassificationCode.INTERNAL,
        ),
        DataField(
            dataset_id=ds_kyc.dataset_id,
            name="last_review",
            native_data_type="TEXT",
            is_nullable=True,
            classification=ClassificationCode.INTERNAL,
        ),
    ]

    all_datasets = {
        "accounts": ds_accounts,
        "transactions": ds_transactions,
        "customers": ds_customers,
        "risk_scores": ds_risk_scores,
        "kyc_records": ds_kyc,
    }
    datasets.update(all_datasets)

    field_map = {
        ds_accounts.dataset_id: fields_accounts,
        ds_transactions.dataset_id: fields_transactions,
        ds_customers.dataset_id: fields_customers,
        ds_risk_scores.dataset_id: fields_risk,
        ds_kyc.dataset_id: fields_kyc,
    }

    # --- Core Banking metadata ---
    for src_key, ds_list, fields_by_ds_key in [
        (
            "pg_core_banking",
            [ds_accounts, ds_transactions, ds_customers],
            {
                ds_accounts.dataset_id: fields_accounts,
                ds_transactions.dataset_id: fields_transactions,
                ds_customers.dataset_id: fields_customers,
            },
        ),
    ]:
        src = sources[src_key]
        all_fields: list[DataField] = []
        for fl in fields_by_ds_key.values():
            all_fields.extend(fl)
        discovery = MetadataDiscoveryResult(
            data_source_id=src.data_source_id,
            succeeded=True,
            duration_ms=1250,
            scanned_object_count=len(ds_list),
            changes=(),
            discovered_at=_days_ago(10),
        )
        audit_event = _make_audit_event(
            audit_outbox,
            action="METADATA_DISCOVERED",
            object_type="DataSource",
            object_id=src.data_source_id,
            reason_code="SEED_METADATA",
        )
        repo.replace_metadata(
            src.data_source_id,
            ds_list,
            fields_by_ds_key,
            discovery,
            audit_event=audit_event,
            audit_outbox=audit_outbox,
        )
        print(f"      + {src.name}: {len(ds_list)} dataset, {len(all_fields)} field")

    # Risk source metadata
    risk_discovery = MetadataDiscoveryResult(
        data_source_id=risk_src.data_source_id,
        succeeded=True,
        duration_ms=800,
        scanned_object_count=1,
        changes=(),
        discovered_at=_days_ago(8),
    )
    audit_event = _make_audit_event(
        audit_outbox,
        action="METADATA_DISCOVERED",
        object_type="DataSource",
        object_id=risk_src.data_source_id,
        reason_code="SEED_METADATA",
    )
    repo.replace_metadata(
        risk_src.data_source_id,
        [ds_risk_scores],
        {ds_risk_scores.dataset_id: fields_risk},
        risk_discovery,
        audit_event=audit_event,
        audit_outbox=audit_outbox,
    )
    print(f"      + {risk_src.name}: 1 dataset, {len(fields_risk)} field")

    # KYC source metadata
    kyc_discovery = MetadataDiscoveryResult(
        data_source_id=kyc_src.data_source_id,
        succeeded=True,
        duration_ms=450,
        scanned_object_count=1,
        changes=(),
        discovered_at=_days_ago(5),
    )
    audit_event = _make_audit_event(
        audit_outbox,
        action="METADATA_DISCOVERED",
        object_type="DataSource",
        object_id=kyc_src.data_source_id,
        reason_code="SEED_METADATA",
    )
    repo.replace_metadata(
        kyc_src.data_source_id,
        [ds_kyc],
        {ds_kyc.dataset_id: fields_kyc},
        kyc_discovery,
        audit_event=audit_event,
        audit_outbox=audit_outbox,
    )
    print(f"      + {kyc_src.name}: 1 dataset, {len(fields_kyc)} field")

    # --- Data profiles ---
    for ds_name, ds in all_datasets.items():
        profile = DataProfile(
            dataset_id=ds.dataset_id,
            execution_id=str(uuid4()),
            method=ProfileMethod.FULL,
            metrics={
                "row_count": ds.estimated_row_count or 0,
                "field_count": len(field_map.get(ds.dataset_id, [])),
                "null_ratio_avg": 0.02,
                "distinct_ratio_avg": 0.85,
            },
            status=ProfileStatus.COMPLETED,
            sample_ratio=1.0,
            duration_ms=3200,
            started_at=_days_ago(3),
            finished_at=_days_ago(3),
        )
        audit_event = _make_audit_event(
            audit_outbox,
            action="DATA_PROFILED",
            object_type="Dataset",
            object_id=ds.dataset_id,
            reason_code="SEED_PROFILE",
        )
        repo.add_data_profile(profile, audit_event=audit_event, audit_outbox=audit_outbox)
    print("      + 5 data profile eklendi.")

    return datasets


def seed_rules(
    repo: PostgreSQLRuleRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    datasets: dict[str, Dataset],
) -> dict[str, tuple[QualityRule, RuleVersion]]:
    """6 farkli kalite kurali ekler."""
    print("[4/10] Kalite kurallari ekleniyor ...")
    rules: dict[str, tuple[QualityRule, RuleVersion]] = {}

    definitions = [
        {
            "key": "required_iban",
            "rule": QualityRule(
                code="DQ-ACC-001",
                name="IBAN alanı boş olamaz",
                dataset_id=datasets["accounts"].dataset_id,
                field_ids=(),
                primary_dimension=QualityDimension.COMPLETENESS,
                owner_user_id="user-data-steward-01",
                status=RuleStatus.ACTIVE,
            ),
            "version": RuleVersion(
                quality_rule_id="",  # altta doldurulacak
                version_no=1,
                rule_type=RuleType.REQUIRED,
                definition={"field": "iban", "operator": "IS_NOT_NULL"},
                threshold=0.999,
                weight=1.0,
                criticality=RuleCriticality.CRITICAL,
                prepared_by_actor_id="SEED_SYSTEM",
                scope_type=RuleScopeType.COLUMN,
            ),
        },
        {
            "key": "unique_account_id",
            "rule": QualityRule(
                code="DQ-ACC-002",
                name="Hesap numarası benzersiz olmalı",
                dataset_id=datasets["accounts"].dataset_id,
                field_ids=(),
                primary_dimension=QualityDimension.UNIQUENESS,
                owner_user_id="user-data-steward-01",
                status=RuleStatus.ACTIVE,
            ),
            "version": RuleVersion(
                quality_rule_id="",
                version_no=1,
                rule_type=RuleType.UNIQUE,
                definition={"field": "account_id", "operator": "IS_UNIQUE"},
                threshold=1.0,
                weight=1.0,
                criticality=RuleCriticality.CRITICAL,
                prepared_by_actor_id="SEED_SYSTEM",
                scope_type=RuleScopeType.COLUMN,
            ),
        },
        {
            "key": "range_balance",
            "rule": QualityRule(
                code="DQ-ACC-003",
                name="Bakiye negatif olamaz",
                dataset_id=datasets["accounts"].dataset_id,
                field_ids=(),
                primary_dimension=QualityDimension.VALIDITY,
                owner_user_id="user-data-steward-01",
                status=RuleStatus.ACTIVE,
            ),
            "version": RuleVersion(
                quality_rule_id="",
                version_no=1,
                rule_type=RuleType.RANGE,
                definition={"field": "balance", "min": 0, "max": 999_999_999_999},
                threshold=0.995,
                weight=0.8,
                criticality=RuleCriticality.HIGH,
                prepared_by_actor_id="SEED_SYSTEM",
                scope_type=RuleScopeType.COLUMN,
            ),
        },
        {
            "key": "freshness_transactions",
            "rule": QualityRule(
                code="DQ-TXN-001",
                name="İşlem verileri 24 saatten eski olmamalı",
                dataset_id=datasets["transactions"].dataset_id,
                field_ids=(),
                primary_dimension=QualityDimension.TIMELINESS,
                owner_user_id="user-data-steward-01",
                status=RuleStatus.ACTIVE,
            ),
            "version": RuleVersion(
                quality_rule_id="",
                version_no=1,
                rule_type=RuleType.FRESHNESS,
                definition={"field": "executed_at", "max_age_seconds": 86400},
                threshold=0.99,
                weight=0.9,
                criticality=RuleCriticality.HIGH,
                prepared_by_actor_id="SEED_SYSTEM",
                scope_type=RuleScopeType.DATASET,
            ),
        },
        {
            "key": "regex_tax_number",
            "rule": QualityRule(
                code="DQ-CUST-001",
                name="Vergi numarası formatı doğrulanmalı",
                dataset_id=datasets["customers"].dataset_id,
                field_ids=(),
                primary_dimension=QualityDimension.VALIDITY,
                owner_user_id="user-data-owner-01",
                status=RuleStatus.ACTIVE,
            ),
            "version": RuleVersion(
                quality_rule_id="",
                version_no=1,
                rule_type=RuleType.REGEX,
                definition={"field": "tax_number", "pattern": "^\\d{10,11}$"},
                threshold=0.998,
                weight=0.7,
                criticality=RuleCriticality.HIGH,
                prepared_by_actor_id="SEED_SYSTEM",
                scope_type=RuleScopeType.COLUMN,
            ),
        },
        {
            "key": "consistency_risk_score",
            "rule": QualityRule(
                code="DQ-RISK-001",
                name="Risk skoru 0-100 aralığında olmalı",
                dataset_id=datasets["risk_scores"].dataset_id,
                field_ids=(),
                primary_dimension=QualityDimension.ACCURACY,
                owner_user_id="user-data-owner-01",
                status=RuleStatus.ACTIVE,
            ),
            "version": RuleVersion(
                quality_rule_id="",
                version_no=1,
                rule_type=RuleType.RANGE,
                definition={"field": "score_value", "min": 0, "max": 100},
                threshold=0.999,
                weight=1.0,
                criticality=RuleCriticality.CRITICAL,
                prepared_by_actor_id="SEED_SYSTEM",
                scope_type=RuleScopeType.COLUMN,
            ),
        },
    ]

    for defn in definitions:
        rule = defn["rule"]
        version = defn["version"]
        # quality_rule_id'yi version'a bagla
        object.__setattr__(version, "quality_rule_id", rule.quality_rule_id)

        audit_event = _make_audit_event(
            audit_outbox,
            action="RULE_CREATED",
            object_type="QualityRule",
            object_id=rule.quality_rule_id,
            reason_code="SEED_RULE",
            new_values={"code": rule.code, "name": rule.name},
        )
        repo.add_rule_with_version(
            rule, version, audit_event=audit_event, audit_outbox=audit_outbox
        )
        rules[defn["key"]] = (rule, version)
        print(f"      + {rule.code}: {rule.name}")

    return rules


def seed_executions(
    repo: PostgreSQLExecutionRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    rules: dict[str, tuple[QualityRule, RuleVersion]],
    sources: dict[str, DataSource],
) -> dict[str, RuleExecution]:
    """3 calistirma (1 basarili, 1 kismi, 1 teknik hata) ekler."""
    print("[5/10] Kural calistirmalari ekleniyor ...")
    executions: dict[str, RuleExecution] = {}

    rule_version_ids = tuple(v.rule_version_id for _, v in rules.values())
    core_source_id = sources["pg_core_banking"].data_source_id

    # --- Basarili calistirma ---
    exec_success = RuleExecution(
        idempotency_key_hash=_idempotency_hash("seed-exec-success-001"),
        payload_hash=hashlib.sha256(b"seed-payload-success").hexdigest(),
        rule_version_ids=rule_version_ids[:3],
        scope={"source_id": core_source_id, "dataset": "accounts"},
        triggered_by="SEED_SYSTEM",
        correlation_id=str(uuid4()),
        source_ids=(core_source_id,),
        workload_class=WorkloadClass.LIGHT,
        execution_type=ExecutionType.MANUAL,
        execution_mode=ExecutionMode.OFFICIAL,
        status=ExecutionStatus.SUCCESS,
        created_at=_hours_ago(12),
        started_at=_hours_ago(12),
        finished_at=_hours_ago(11),
    )
    audit_event = _make_audit_event(
        audit_outbox,
        action="EXECUTION_CREATED",
        object_type="RuleExecution",
        object_id=exec_success.execution_id,
        reason_code="SEED_EXECUTION",
    )
    created, _ = repo.create_or_get(
        exec_success, audit_event=audit_event, audit_outbox=audit_outbox
    )
    executions["success"] = created

    # Sonuclari ekle
    seed_evidence = _make_seed_evidence()
    results_success = tuple(
        RuleExecutionResult(
            execution_id=exec_success.execution_id,
            rule_version_id=vid,
            population_count=2_500_000,
            eligible_count=2_500_000,
            evaluated_count=2_500_000,
            passed_count=2_499_800,
            failed_count=200,
            excluded_count=0,
            technical_error_count=0,
            unknown_count=0,
            measurement_status=MeasurementStatus.PASSED,
            evidence=seed_evidence,
        )
        for vid in rule_version_ids[:3]
    )
    repo.complete_success(
        exec_success.execution_id,
        results_success,
        finished_at=_hours_ago(11),
    )
    print(f"      + SUCCESS  {exec_success.execution_id[:8]}... (accounts, 3 kural)")

    # --- Kismi calistirma ---
    exec_partial = RuleExecution(
        idempotency_key_hash=_idempotency_hash("seed-exec-partial-002"),
        payload_hash=hashlib.sha256(b"seed-payload-partial").hexdigest(),
        rule_version_ids=rule_version_ids[3:5],
        scope={"source_id": core_source_id, "dataset": "transactions"},
        triggered_by="SCHEDULER",
        correlation_id=str(uuid4()),
        source_ids=(core_source_id,),
        workload_class=WorkloadClass.HEAVY,
        execution_type=ExecutionType.SCHEDULED,
        execution_mode=ExecutionMode.OFFICIAL,
        status=ExecutionStatus.QUEUED,
        created_at=_hours_ago(6),
    )
    audit_event = _make_audit_event(
        audit_outbox,
        action="EXECUTION_CREATED",
        object_type="RuleExecution",
        object_id=exec_partial.execution_id,
        reason_code="SEED_EXECUTION",
    )
    created, _ = repo.create_or_get(
        exec_partial, audit_event=audit_event, audit_outbox=audit_outbox
    )
    executions["partial"] = created

    results_partial = (
        RuleExecutionResult(
            execution_id=exec_partial.execution_id,
            rule_version_id=rule_version_ids[3],
            population_count=45_000_000,
            eligible_count=44_500_000,
            evaluated_count=44_500_000,
            passed_count=44_000_000,
            failed_count=500_000,
            excluded_count=0,
            technical_error_count=0,
            unknown_count=0,
            measurement_status=MeasurementStatus.FAILED,
            evidence={
                "fingerprint": "sha256:" + hashlib.sha256(b"seed-partial-violation").hexdigest(),
                "masked_samples": [
                    "hmac-sha256://seed-sample/"
                    + hashlib.sha256(f"partial-sample-{i}".encode()).hexdigest()
                    for i in range(3)
                ],
                "expected_summary": {"population_count": 45_000_000, "eligible_count": 44_500_000},
                "actual_summary": {"passed_count": 44_000_000, "failed_count": 500_000},
                "query_reference": "query-template://seed/dq-txn-001",
                "plan_reference": "plan://seed/dq-txn-001",
            },
        ),
    )
    repo.complete_success(
        exec_partial.execution_id,
        results_partial,
        finished_at=_hours_ago(5),
    )
    print(f"      + PARTIAL  {exec_partial.execution_id[:8]}... (transactions, 1/2 kural basarili)")

    # --- Teknik hata ---
    exec_error = RuleExecution(
        idempotency_key_hash=_idempotency_hash("seed-exec-error-003"),
        payload_hash=hashlib.sha256(b"seed-payload-error").hexdigest(),
        rule_version_ids=(rule_version_ids[5],),
        scope={"source_id": sources["mssql_risk"].data_source_id, "dataset": "risk_scores"},
        triggered_by="SCHEDULER",
        correlation_id=str(uuid4()),
        source_ids=(sources["mssql_risk"].data_source_id,),
        workload_class=WorkloadClass.LIGHT,
        execution_type=ExecutionType.SCHEDULED,
        execution_mode=ExecutionMode.SHADOW,
        status=ExecutionStatus.QUEUED,
        created_at=_hours_ago(3),
    )
    audit_event = _make_audit_event(
        audit_outbox,
        action="EXECUTION_CREATED",
        object_type="RuleExecution",
        object_id=exec_error.execution_id,
        reason_code="SEED_EXECUTION",
    )
    created, _ = repo.create_or_get(exec_error, audit_event=audit_event, audit_outbox=audit_outbox)
    executions["error"] = created
    repo.complete_technical_error(
        exec_error.execution_id,
        error_class="TIMEOUT",
        finished_at=_hours_ago(2),
    )
    print(f"      + ERROR    {exec_error.execution_id[:8]}... (risk_scores, timeout)")

    return executions


def seed_issues(
    repo: PostgreSQLIssueRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
    datasets: dict[str, Dataset],
) -> dict[str, DataQualityIssue]:
    """3 farkli durumda quality issue ekler."""
    print("[6/10] Kalite sorunlari ekleniyor ...")
    issues: dict[str, DataQualityIssue] = {}

    issue_defs = [
        {
            "key": "open_critical",
            "issue": DataQualityIssue(
                issue_no="ISS-2026-0001",
                source_event_id=str(uuid4()),
                source_event_type=IssueSourceEventType.QUALITY,
                trigger_type=IssueTriggerType.CRITICAL_RULE_FAILURE,
                scope_type=IssueScopeType.DATASET,
                scope_id=datasets["accounts"].dataset_id,
                status=IssueStatus.NEW,
                priority=IssuePriority.CRITICAL,
                assignee_user_id="user-data-steward-01",
                deduplication_key_digest=hashlib.sha256(b"seed-issue-iban-null").hexdigest(),
                occurrence_count=200,
                created_at=_hours_ago(12),
                updated_at=_hours_ago(12),
                last_seen_at=_hours_ago(1),
            ),
        },
        {
            "key": "investigating",
            "issue": DataQualityIssue(
                issue_no="ISS-2026-0002",
                source_event_id=str(uuid4()),
                source_event_type=IssueSourceEventType.QUALITY,
                trigger_type=IssueTriggerType.QUALITY_THRESHOLD,
                scope_type=IssueScopeType.DATASET,
                scope_id=datasets["transactions"].dataset_id,
                status=IssueStatus.INVESTIGATING,
                priority=IssuePriority.HIGH,
                assignee_user_id="user-data-owner-01",
                deduplication_key_digest=hashlib.sha256(b"seed-issue-txn-freshness").hexdigest(),
                occurrence_count=500_000,
                created_at=_days_ago(2),
                updated_at=_hours_ago(6),
                last_seen_at=_hours_ago(2),
            ),
        },
        {
            "key": "resolved",
            "issue": DataQualityIssue(
                issue_no="ISS-2026-0003",
                source_event_id=str(uuid4()),
                source_event_type=IssueSourceEventType.TECHNICAL,
                trigger_type=IssueTriggerType.TECHNICAL_ERROR,
                scope_type=IssueScopeType.SOURCE,
                scope_id=datasets["risk_scores"].dataset_id,
                status=IssueStatus.RESOLVED,
                priority=IssuePriority.MEDIUM,
                assignee_user_id="user-data-steward-01",
                deduplication_key_digest=hashlib.sha256(b"seed-issue-risk-timeout").hexdigest(),
                occurrence_count=15,
                created_at=_days_ago(7),
                updated_at=_days_ago(1),
                last_seen_at=_days_ago(3),
            ),
        },
    ]

    for defn in issue_defs:
        issue = defn["issue"]
        history = IssueHistoryEntry(
            issue_id=issue.issue_id,
            action="CREATED",
            actor_id="SEED_SYSTEM",
            old_status=None,
            new_status=issue.status,
            occurred_at=issue.created_at,
            old_assignee_user_id=None,
            new_assignee_user_id=issue.assignee_user_id,
            old_priority=None,
            new_priority=issue.priority,
        )
        audit_event = _make_audit_event(
            audit_outbox,
            action="ISSUE_CREATED",
            object_type="DataQualityIssue",
            object_id=issue.issue_id,
            reason_code="SEED_ISSUE",
            new_values={"issue_no": issue.issue_no, "status": issue.status.value},
        )
        reopen_event = _make_audit_event(
            audit_outbox,
            action="ISSUE_NOOP",
            object_type="DataQualityIssue",
            object_id=issue.issue_id,
        )
        repo.add_or_increment(
            issue,
            history,
            payload_digest=hashlib.sha256(issue.issue_no.encode()).hexdigest(),
            source_event_occurred_at=issue.created_at,
            relationship=None,
            relationship_history=None,
            audit_event=audit_event,
            reopen_audit_event=reopen_event,
            relationship_audit_event=None,
            audit_outbox=audit_outbox,
        )
        issues[defn["key"]] = issue
        print(f"      + {issue.issue_no} [{issue.status.value}] {issue.priority.value}")

    return issues


def seed_jobs(
    repo: PostgreSQLJobQueueRepository,
    audit_outbox: PostgreSQLTransactionalAudit,
) -> dict[str, BackgroundJob]:
    """5 farkli durumda is kuyrugu kaydi ekler."""
    print("[7/10] Is kuyrugu kayitlari ekleniyor ...")
    jobs: dict[str, BackgroundJob] = {}

    job_defs = [
        {
            "key": "queued_profile",
            "job": BackgroundJob(
                job_type="DATA_PROFILE_EXECUTION",
                payload={"dataset_id": "accounts", "method": "FULL"},
                idempotency_key="seed-job-profile-001",
                priority=5,
                status=JobStatus.QUEUED,
                created_at=_hours_ago(1),
            ),
        },
        {
            "key": "running_rule",
            "job": BackgroundJob(
                job_type="RULE_EXECUTION_BATCH",
                payload={"rule_ids": ["DQ-ACC-001", "DQ-ACC-002"]},
                idempotency_key="seed-job-rule-002",
                priority=8,
                status=JobStatus.RUNNING,
                claimed_by="worker-node-01",
                created_at=_hours_ago(2),
            ),
        },
        {
            "key": "completed_report",
            "job": BackgroundJob(
                job_type="REPORT_GENERATION",
                payload={"report_type": "SUMMARY", "format": "PDF"},
                idempotency_key="seed-job-report-003",
                priority=3,
                status=JobStatus.SUCCESS,
                created_at=_days_ago(1),
                completed_at=_days_ago(1),
                completion_outcome=JobCompletionOutcome.SUCCESS,
            ),
        },
        {
            "key": "failed_sync",
            "job": BackgroundJob(
                job_type="METADATA_SYNC",
                payload={"source_id": "mssql_risk"},
                idempotency_key="seed-job-sync-004",
                priority=6,
                status=JobStatus.TECHNICAL_ERROR,
                attempt_count=3,
                last_error_class="CONNECTION_TIMEOUT",
                created_at=_days_ago(1),
            ),
        },
        {
            "key": "cancelled_cleanup",
            "job": BackgroundJob(
                job_type="DATA_RETENTION_CLEANUP",
                payload={"retention_days": 365},
                idempotency_key="seed-job-cleanup-005",
                priority=1,
                status=JobStatus.CANCELLED,
                created_at=_days_ago(3),
                cancel_requested_by="admin-user",
                cancel_reason_code="MANUAL_CANCEL",
            ),
        },
    ]

    for defn in job_defs:
        job = defn["job"]
        audit_event = _make_audit_event(
            audit_outbox,
            action="JOB_ENQUEUED",
            object_type="BackgroundJob",
            object_id=job.job_id,
            reason_code="SEED_JOB",
            new_values={"job_type": job.job_type, "status": job.status.value},
        )
        repo.enqueue(job, audit_event=audit_event, audit_outbox=audit_outbox)
        jobs[defn["key"]] = job
        print(f"      + {job.job_type} [{job.status.value}]")

    return jobs


def seed_reports(
    repo: PostgreSQLReportRepository,
    schedule_repo: PostgreSQLReportScheduleRepository,
) -> None:
    """2 rapor + 2 rapor zamani ekler."""
    print("[8/10] Raporlar ve rapor zamanlari ekleniyor ...")

    # Raporlar
    report_requests = [
        ReportRequest(
            report_type=ReportType.SUMMARY,
            format=ReportFormat.PDF,
            parameters={"scope": "all", "period": "last_30_days"},
            reason_code="SEED_REPORT",
            sensitivity_level="INTERNAL",
        ),
        ReportRequest(
            report_type=ReportType.DETAIL,
            format=ReportFormat.XLSX,
            parameters={"dataset": "accounts", "include_scores": True},
            reason_code="SEED_REPORT",
            sensitivity_level="CONFIDENTIAL",
        ),
    ]
    for req in report_requests:
        report = repo.create_report(req, requested_by="SEED_SYSTEM")
        print(
            f"      + Rapor {report.report_id[:8]}... [{req.report_type.value}/{req.format.value}]"
        )

    # Rapor zamanlari
    now = _utc_now()
    schedules = [
        ReportSchedule(
            schedule_id=str(uuid4()),
            name="Haftalik Ozet Rapor",
            report_type=ReportType.SUMMARY,
            format=ReportFormat.PDF,
            parameters={"scope": "all"},
            sensitivity_level="INTERNAL",
            recipients=("user-data-steward-01", "user-data-owner-01"),
            schedule_type=ScheduleType.WEEKLY,
            timezone_name="Europe/Istanbul",
            local_time=time(8, 0),
            day_of_week=1,
            is_active=True,
            next_run_at=now + timedelta(days=(7 - now.weekday()) % 7 or 7),
            created_by="SEED_SYSTEM",
        ),
        ReportSchedule(
            schedule_id=str(uuid4()),
            name="Aylik Detayli Kalite Raporu",
            report_type=ReportType.DETAIL,
            format=ReportFormat.XLSX,
            parameters={"include_scores": True},
            sensitivity_level="CONFIDENTIAL",
            recipients=("user-data-owner-01",),
            schedule_type=ScheduleType.MONTHLY,
            timezone_name="Europe/Istanbul",
            local_time=time(9, 0),
            day_of_month=1,
            is_active=True,
            next_run_at=now.replace(day=28) + timedelta(days=5),
            created_by="SEED_SYSTEM",
        ),
    ]
    for sched in schedules:
        schedule_repo.add(sched)
        print(f"      + Schedule: {sched.name}")


def seed_source_usage_policy(
    repo: PostgreSQLSourceUsagePolicyRepository,
) -> SourceUsagePolicy:
    """Global kaynak kullanım politikası ekler (worker için gerekli)."""
    print("[9/10] Kaynak kullanım politikası ekleniyor ...")
    policy = SourceUsagePolicy(
        policy_id=str(uuid4()),
        policy_version=1,
        status=SourceUsagePolicyStatus.ACTIVE,
        source_id=None,
        source_type=None,
        max_concurrent_queries=10,
        max_workers=4,
        connection_timeout_seconds=15,
        query_timeout_seconds=300,
        total_job_timeout_seconds=3600,
        retry_count=2,
        retry_delay_seconds=5.0,
        rate_limit={"requests_per_minute": 100},
        allowed_windows=(),
        blocked_windows=(),
        cpu_limit_percent=80.0,
        io_limit_percent=70.0,
        peak_hours_behavior="DEFER",
        timeout_cancel_behavior="CANCEL",
        approved_by="SEED_SYSTEM",
        audit_reference="SEED_POLICY_V1",
    )
    repo.save(policy)
    print(f"      + Global policy {policy.policy_id[:8]}... (ACTIVE)")
    return policy


def seed_quality_scores(
    session_factory,
    schema: str,
    sources: dict[str, DataSource],
) -> None:
    """Dashboard trend icin son 20 gunun kalite skorlarini ekler."""
    print("[10/10] Kalite skorlari ekleniyor ...")
    from veri_kalitesi.persistence import transactional_session
    from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table
    from sqlalchemy.dialects.postgresql import JSON as SA_JSON

    # rule_executions tablosu (FK gereksinimi icin minimal tanim)
    exec_meta = MetaData(schema=schema)
    exec_table = Table(
        "rule_executions",
        exec_meta,
        Column("execution_id", String(36), primary_key=True),
        Column("execution_type", String(20), nullable=False),
        Column("status", String(30), nullable=False),
        Column("idempotency_key_hash", String(64), nullable=False, unique=True),
        Column("payload_hash", String(64), nullable=False),
        Column("rule_version_ids", SA_JSON, nullable=False),
        Column("scope", SA_JSON, nullable=False),
        Column("triggered_by", String(128), nullable=False),
        Column("correlation_id", String(36), nullable=False),
        Column("source_ids", SA_JSON, nullable=False),
        Column("workload_class", String(20), nullable=False),
        Column("execution_mode", String(20), nullable=False),
        Column("attempt_count", Integer, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        extend_existing=True,
    )

    tables = score_tables(schema)
    t = tables.quality_scores

    source_configs = [
        {"key": "pg_core_banking", "base": Decimal("88")},
        {"key": "mssql_risk", "base": Decimal("76")},
        {"key": "csv_kyc_export", "base": Decimal("82")},
    ]

    score_rows: list[dict] = []
    exec_rows: list[dict] = []
    now = _utc_now()

    def _level_for(value: Decimal) -> str:
        if value >= Decimal("90"):
            return ScoreLevel.GOOD.value
        if value >= Decimal("75"):
            return ScoreLevel.ACCEPTABLE.value
        if value >= Decimal("50"):
            return ScoreLevel.RISKY.value
        return ScoreLevel.CRITICAL.value

    # Kaynak skorlari
    for cfg in source_configs:
        source_id = sources[cfg["key"]].data_source_id
        base = cfg["base"]
        for day_offset in range(20, 0, -1):
            exec_id = str(uuid4())
            calculated_at = (now - timedelta(days=day_offset)).replace(
                hour=6, minute=0, second=0, microsecond=0
            )
            variation = (day_offset % 5 - 2) * Decimal("1.5")
            score_value = base + variation
            exec_rows.append(
                {
                    "execution_id": exec_id,
                    "execution_type": "SCHEDULED",
                    "status": "SUCCESS",
                    "idempotency_key_hash": hashlib.sha256(
                        f"seed-score-{exec_id}".encode()
                    ).hexdigest(),
                    "payload_hash": hashlib.sha256(b"seed-score-payload").hexdigest(),
                    "rule_version_ids": [],
                    "scope": {"source_id": source_id},
                    "triggered_by": "SEED_DASHBOARD",
                    "correlation_id": str(uuid4()),
                    "source_ids": [source_id],
                    "workload_class": "LIGHT",
                    "execution_mode": "OFFICIAL",
                    "attempt_count": 0,
                    "created_at": calculated_at,
                }
            )
            score_rows.append(
                {
                    "quality_score_id": str(uuid4()),
                    "execution_id": exec_id,
                    "scope_type": ScoreScopeType.SOURCE.value,
                    "scope_id": source_id,
                    "score_value": score_value,
                    "score_status": ScoreStatus.CALCULATED.value,
                    "measurement_status": "Passed",
                    "level": _level_for(score_value),
                    "policy_version": "SEED_SCORING_V1",
                    "calculation_details": {
                        "included_in_official_aggregation": True,
                        "component_count": 5,
                        "seed": True,
                    },
                    "calculated_at": calculated_at,
                }
            )

    # Enterprise skorlari (kaynak ortalamalari)
    for day_offset in range(20, 0, -1):
        exec_id = str(uuid4())
        calculated_at = (now - timedelta(days=day_offset)).replace(
            hour=7, minute=0, second=0, microsecond=0
        )
        day_source_values = []
        for cfg in source_configs:
            variation = (day_offset % 5 - 2) * Decimal("1.5")
            day_source_values.append(cfg["base"] + variation)
        enterprise_value = sum(day_source_values) / len(day_source_values)
        all_source_ids = [sources[c["key"]].data_source_id for c in source_configs]
        exec_rows.append(
            {
                "execution_id": exec_id,
                "execution_type": "SCHEDULED",
                "status": "SUCCESS",
                "idempotency_key_hash": hashlib.sha256(f"seed-ent-{exec_id}".encode()).hexdigest(),
                "payload_hash": hashlib.sha256(b"seed-ent-payload").hexdigest(),
                "rule_version_ids": [],
                "scope": {"scope": "enterprise"},
                "triggered_by": "SEED_DASHBOARD",
                "correlation_id": str(uuid4()),
                "source_ids": all_source_ids,
                "workload_class": "LIGHT",
                "execution_mode": "OFFICIAL",
                "attempt_count": 0,
                "created_at": calculated_at,
            }
        )
        score_rows.append(
            {
                "quality_score_id": str(uuid4()),
                "execution_id": exec_id,
                "scope_type": ScoreScopeType.ENTERPRISE.value,
                "scope_id": None,
                "score_value": enterprise_value,
                "score_status": ScoreStatus.CALCULATED.value,
                "measurement_status": "Passed",
                "level": _level_for(enterprise_value),
                "policy_version": "SEED_SCORING_V1",
                "calculation_details": {
                    "included_in_official_aggregation": True,
                    "component_count": 15,
                    "seed": True,
                },
                "calculated_at": calculated_at,
            }
        )

    # Seed skorlari icin bir publication kaydi olustur
    publication_id = str(uuid4())
    publication_rows = [
        {
            "publication_id": publication_id,
            "execution_id": exec_rows[0]["execution_id"] if exec_rows else str(uuid4()),
            "period": "SEED_PERIOD",
            "input_digest": "sha256:" + hashlib.sha256(b"seed-publication").hexdigest(),
            "status": "PUBLISHED",
            "policy_version": "SEED_SCORING_V1",
            "published_at": now - timedelta(days=1),
            "superseded_at": None,
        }
    ]

    with transactional_session(session_factory) as session:
        for row in exec_rows:
            session.execute(exec_table.insert().values(**row))
        pub_table = tables.score_publications
        for row in publication_rows:
            session.execute(pub_table.insert().values(**row))
        for row in score_rows:
            row["publication_id"] = publication_id
            session.execute(t.insert().values(**row))

    source_count = len(score_rows) - 20
    print(f"      + {source_count} kaynak skoru + 20 enterprise skoru ({len(score_rows)} toplam)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    raw_url = os.environ.get("DATA_QUALITY_DATABASE_URL")
    if not raw_url:
        print(
            "HATA: DATA_QUALITY_DATABASE_URL ortam degiskeni ayarlanmali.\n"
            "Ornek: postgresql+psycopg://app:pwd@localhost/data_quality",
            file=sys.stderr,
        )
        return 2

    schema = os.environ.get("DATA_QUALITY_DATABASE_SCHEMA", DEFAULT_SCHEMA_NAME)
    settings = DatabaseSettings.from_url(raw_url, schema=schema)

    # 1. Alembic migration
    run_alembic_migration(settings)

    # 2. Session factory
    session_factory = create_session_factory(settings)

    # 3. Idempotency check — skip if already seeded
    if _already_seeded(session_factory, schema):
        print("=" * 60)
        print("  Seed verisi zaten mevcut, atlanıyor.")
        print("  Temiz başlangıç için: docker compose down -v")
        print("=" * 60)
        return 0

    # 4. Audit altyapisi
    redactor = AuditRedactor(build_default_redaction_policy())
    prepared_repo = _SeedPreparedAuditRepository()
    audit_outbox = PostgreSQLTransactionalAudit(
        session_factory=session_factory,
        redactor=redactor,
        repository=prepared_repo,
        policy_version="SEED_V1",
        schema=schema,
    )

    # 5. Repository'ler
    ds_repo = PostgreSQLDataSourceRepository(session_factory, schema=schema)
    rule_repo = PostgreSQLRuleRepository(session_factory, schema=schema)
    exec_repo = PostgreSQLExecutionRepository(session_factory, schema=schema)
    issue_repo = PostgreSQLIssueRepository(session_factory, schema=schema)
    job_repo = PostgreSQLJobQueueRepository(session_factory, schema=schema)
    report_repo = PostgreSQLReportRepository(session_factory, schema=schema)
    report_sched_repo = PostgreSQLReportScheduleRepository(session_factory, schema=schema)
    source_usage_policy_repo = PostgreSQLSourceUsagePolicyRepository(session_factory, schema=schema)

    print("=" * 60)
    print("  Veri Kalitesi Sistemi — Seed Script")
    print(f"  Database : {settings.safe_url()}")
    print(f"  Schema   : {schema}")
    print("=" * 60)

    # 6. Seed verileri
    sources = seed_data_sources(ds_repo, audit_outbox, schema)
    datasets = seed_metadata(ds_repo, audit_outbox, sources, schema)
    rules = seed_rules(rule_repo, audit_outbox, datasets)
    seed_executions(exec_repo, audit_outbox, rules, sources)
    seed_issues(issue_repo, audit_outbox, datasets)
    seed_jobs(job_repo, audit_outbox)
    seed_reports(report_repo, report_sched_repo)
    seed_source_usage_policy(source_usage_policy_repo)
    seed_quality_scores(session_factory, schema, sources)

    # 7. Publish pending audit events
    outbox_status = audit_outbox.publish_pending()
    print(f"\nAudit outbox: {outbox_status.published_count} event publish edildi.")

    print("\n" + "=" * 60)
    print("  Seed basariyla tamamlandi!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
