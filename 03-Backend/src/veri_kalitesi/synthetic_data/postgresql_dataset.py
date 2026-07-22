"""Deterministik ve ground-truth kontrollü PostgreSQL sentetik kaynak dataset'i."""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
import resource
from time import perf_counter
from typing import Any

import psycopg
from psycopg import sql

from veri_kalitesi.synthetic_data.errors import (
    SyntheticDataTechnicalError,
    SyntheticDataValidationError,
)


GENERATOR_VERSION = "RELATIONAL_BANKING_GENERATOR_V1"
SCHEMA_VERSION = "RELATIONAL_BANKING_SCHEMA_V1"
CONFIGURATION_VERSION = "RELATIONAL_QUALITY_CONFIGURATION_V1"
GROUND_TRUTH_VERSION = "RELATIONAL_GROUND_TRUTH_V1"
POLICY_VERSION = "LOCAL_SYNTHETIC_DATASET_POLICY_V1"
SOURCE_SCHEMA = "synthetic_source"
CONTROL_SCHEMA = "synthetic_control"
DEFAULT_SEED = 2026
DEFAULT_ROW_COUNT = 19_000
MIN_ROW_COUNT = 17_000
MAX_ROW_COUNT = 22_000
REFERENCE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)
STALE_THRESHOLD = REFERENCE_TIME - timedelta(days=365)
OUTLIER_THRESHOLD = Decimal("10000000.00")
ALLOWED_ENVIRONMENTS = frozenset({"local", "development", "test"})
VALID_STATUSES = ("ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE", "INACTIVE", "CLOSED")


@dataclass(frozen=True)
class RelationSpec:
    column: str
    target_table: str
    target_key: str


@dataclass(frozen=True)
class TableSpec:
    name: str
    purpose: str
    primary_key: str
    business_key: str
    descriptive_column: str
    formatted_column: str
    status_column: str
    measure_column: str
    format_kind: str
    relations: tuple[RelationSpec, ...] = ()


@dataclass(frozen=True)
class DefectTruth:
    table_name: str
    record_key: str
    column_name: str
    quality_dimension: str
    defect_type: str
    expected_rule_result: str
    expected_severity: str


@dataclass(frozen=True)
class TableGenerationMetric:
    table_name: str
    generated_row_count: int
    clean_row_count: int
    defective_row_count: int
    expected_defect_count: int
    generation_duration_seconds: float
    rows_per_second: float


@dataclass(frozen=True)
class ValidationMetric:
    table_name: str
    defect_type: str
    expected_defect_count: int
    detected_defect_count: int
    true_positive: int
    false_positive: int
    false_negative: int
    precision: Decimal
    recall: Decimal
    execution_duration_seconds: float


@dataclass(frozen=True)
class ProfileMetric:
    table_name: str
    row_count: int
    required_value_null_count: int
    distinct_business_key_count: int
    minimum_measure: Decimal | None
    maximum_measure: Decimal | None
    profiling_duration_seconds: float


@dataclass(frozen=True)
class GenerationSummary:
    run_id: str
    generator_version: str
    schema_version: str
    configuration_version: str
    seed: int
    scenario: str
    row_count_per_table: int
    table_metrics: tuple[TableGenerationMetric, ...]
    profile_metrics: tuple[ProfileMetric, ...]
    validation_metrics: tuple[ValidationMetric, ...]
    canonical_sha256: str
    generation_duration_seconds: float
    database_size_bytes: int
    peak_memory_bytes: int

    @property
    def total_rows(self) -> int:
        return sum(metric.generated_row_count for metric in self.table_metrics)

    @property
    def total_expected_defects(self) -> int:
        return sum(metric.expected_defect_count for metric in self.table_metrics)

    @property
    def all_validations_passed(self) -> bool:
        return all(
            metric.false_positive == 0 and metric.false_negative == 0
            for metric in self.validation_metrics
        )


TABLE_SPECS: tuple[TableSpec, ...] = (
    TableSpec(
        "synthetic_customers",
        "Sentetik müşteri ana kayıtları",
        "customer_id",
        "customer_number",
        "full_name",
        "email_address",
        "customer_status",
        "activity_score",
        "email",
    ),
    TableSpec(
        "synthetic_customer_contacts",
        "Sentetik telefon ve e-posta iletişim kayıtları",
        "contact_id",
        "contact_reference",
        "contact_label",
        "contact_value",
        "contact_status",
        "verification_score",
        "contact",
        (RelationSpec("customer_id", "synthetic_customers", "customer_id"),),
    ),
    TableSpec(
        "synthetic_customer_addresses",
        "Sentetik müşteri adres ve konum kayıtları",
        "address_id",
        "address_reference",
        "address_line",
        "postal_code",
        "address_status",
        "location_score",
        "postal",
        (RelationSpec("customer_id", "synthetic_customers", "customer_id"),),
    ),
    TableSpec(
        "synthetic_accounts",
        "Sentetik mevduat ve ödeme hesapları",
        "account_id",
        "account_number",
        "account_name",
        "iban_code",
        "account_status",
        "current_balance",
        "iban",
        (RelationSpec("customer_id", "synthetic_customers", "customer_id"),),
    ),
    TableSpec(
        "synthetic_account_balances",
        "Sentetik hesap bakiye anlık görüntüleri",
        "balance_id",
        "balance_reference",
        "balance_note",
        "currency_code",
        "balance_status",
        "closing_balance",
        "currency",
        (RelationSpec("account_id", "synthetic_accounts", "account_id"),),
    ),
    TableSpec(
        "synthetic_transactions",
        "Sentetik hesap işlemleri",
        "transaction_row_id",
        "transaction_id",
        "transaction_description",
        "channel_code",
        "transaction_status",
        "transaction_amount",
        "channel",
        (RelationSpec("account_id", "synthetic_accounts", "account_id"),),
    ),
    TableSpec(
        "synthetic_cards",
        "Sentetik banka ve kredi kartları",
        "card_id",
        "card_reference",
        "card_label",
        "masked_pan",
        "card_status",
        "card_limit",
        "masked_pan",
        (
            RelationSpec("customer_id", "synthetic_customers", "customer_id"),
            RelationSpec("account_id", "synthetic_accounts", "account_id"),
        ),
    ),
    TableSpec(
        "synthetic_card_transactions",
        "Sentetik kart harcama ve çekim işlemleri",
        "card_transaction_id",
        "card_transaction_reference",
        "card_transaction_description",
        "authorization_code",
        "card_transaction_status",
        "card_transaction_amount",
        "authorization",
        (
            RelationSpec("card_id", "synthetic_cards", "card_id"),
            RelationSpec("merchant_id", "synthetic_merchants", "merchant_id"),
        ),
    ),
    TableSpec(
        "synthetic_loans",
        "Sentetik kredi sözleşmeleri",
        "loan_id",
        "loan_reference",
        "loan_description",
        "product_code",
        "loan_status",
        "principal_amount",
        "product",
        (RelationSpec("customer_id", "synthetic_customers", "customer_id"),),
    ),
    TableSpec(
        "synthetic_loan_installments",
        "Sentetik kredi ödeme planları",
        "installment_id",
        "installment_reference",
        "installment_description",
        "currency_code",
        "installment_status",
        "installment_amount",
        "currency",
        (RelationSpec("loan_id", "synthetic_loans", "loan_id"),),
    ),
    TableSpec(
        "synthetic_payments",
        "Sentetik hesap, işlem ve taksit ödemeleri",
        "payment_id",
        "payment_reference",
        "payment_description",
        "payment_channel",
        "payment_status",
        "payment_amount",
        "channel",
        (
            RelationSpec("account_id", "synthetic_accounts", "account_id"),
            RelationSpec("transaction_row_id", "synthetic_transactions", "transaction_row_id"),
            RelationSpec("installment_id", "synthetic_loan_installments", "installment_id"),
        ),
    ),
    TableSpec(
        "synthetic_beneficiaries",
        "Sentetik kayıtlı transfer alıcıları",
        "beneficiary_id",
        "beneficiary_reference",
        "beneficiary_name",
        "beneficiary_account_code",
        "beneficiary_status",
        "transfer_limit",
        "account_code",
        (
            RelationSpec("customer_id", "synthetic_customers", "customer_id"),
            RelationSpec("account_id", "synthetic_accounts", "account_id"),
        ),
    ),
    TableSpec(
        "synthetic_merchants",
        "Sentetik üye işyeri ana kayıtları",
        "merchant_id",
        "merchant_reference",
        "merchant_name",
        "category_code",
        "merchant_status",
        "merchant_risk_score",
        "category",
    ),
    TableSpec(
        "synthetic_merchant_transactions",
        "Sentetik üye işyeri mutabakat işlemleri",
        "merchant_transaction_id",
        "settlement_reference",
        "settlement_description",
        "settlement_code",
        "settlement_status",
        "settlement_amount",
        "settlement",
        (
            RelationSpec("merchant_id", "synthetic_merchants", "merchant_id"),
            RelationSpec(
                "card_transaction_id",
                "synthetic_card_transactions",
                "card_transaction_id",
            ),
        ),
    ),
    TableSpec(
        "synthetic_customer_risk_profiles",
        "Sentetik sürümlü müşteri risk değerlendirmeleri",
        "risk_profile_id",
        "risk_profile_reference",
        "risk_description",
        "risk_model_code",
        "risk_status",
        "risk_score",
        "risk_model",
        (RelationSpec("customer_id", "synthetic_customers", "customer_id"),),
    ),
    TableSpec(
        "synthetic_service_requests",
        "Sentetik müşteri hizmet ve operasyon talepleri",
        "service_request_id",
        "request_reference",
        "request_description",
        "request_type",
        "request_status",
        "resolution_hours",
        "request_type",
        (
            RelationSpec("customer_id", "synthetic_customers", "customer_id"),
            RelationSpec("account_id", "synthetic_accounts", "account_id"),
            RelationSpec("card_id", "synthetic_cards", "card_id"),
            RelationSpec("loan_id", "synthetic_loans", "loan_id"),
        ),
    ),
    TableSpec(
        "synthetic_data_events",
        "Sentetik kaynak ingestion, güncelleme ve tazelik olayları",
        "data_event_id",
        "event_reference",
        "event_description",
        "entity_type",
        "event_status",
        "lag_seconds",
        "entity_type",
        (
            RelationSpec("customer_id", "synthetic_customers", "customer_id"),
            RelationSpec("account_id", "synthetic_accounts", "account_id"),
            RelationSpec("transaction_row_id", "synthetic_transactions", "transaction_row_id"),
            RelationSpec("card_id", "synthetic_cards", "card_id"),
            RelationSpec("loan_id", "synthetic_loans", "loan_id"),
        ),
    ),
)


BASE_DEFECT_RATES: Mapping[str, float] = {
    "missing_value": 0.03,
    "blank_or_whitespace": 0.01,
    "duplicate": 0.02,
    "invalid_format": 0.025,
    "invalid_domain_value": 0.015,
    "consistency_error": 0.025,
    "referential_integrity_error": 0.015,
    "stale_record": 0.035,
    "outlier": 0.02,
}

SCENARIO_DEFECT_RATIOS: Mapping[str, float] = {
    "clean-baseline": 0.01,
    "mixed-quality": 0.18,
    "high-defect": 0.35,
    "stale-data": 0.18,
    "duplicate-heavy": 0.18,
    "referential-integrity": 0.18,
}

DEFECT_DIMENSIONS: Mapping[str, str] = {
    "missing_value": "completeness",
    "blank_or_whitespace": "completeness",
    "duplicate": "uniqueness",
    "invalid_format": "validity",
    "invalid_domain_value": "validity",
    "consistency_error": "consistency",
    "referential_integrity_error": "referential_integrity",
    "stale_record": "timeliness",
    "outlier": "outlier_detection",
}


def validate_generation_request(
    *,
    environment: str,
    database_name: str,
    allow_test_data: bool,
    row_count: int,
    scenario: str,
) -> None:
    if environment not in ALLOWED_ENVIRONMENTS:
        raise SyntheticDataValidationError("Synthetic generation environment is not allowed.")
    if not allow_test_data:
        raise SyntheticDataValidationError("Explicit test-data permission is required.")
    lowered_database = database_name.strip().lower()
    if not lowered_database or "prod" in lowered_database or "production" in lowered_database:
        raise SyntheticDataValidationError("Production-like database name is not allowed.")
    if lowered_database not in {"data_quality", "data_quality_test"}:
        raise SyntheticDataValidationError(
            "Synthetic dataset requires an approved data_quality test database."
        )
    if not MIN_ROW_COUNT <= row_count <= MAX_ROW_COUNT:
        raise SyntheticDataValidationError(
            f"Row count must be between {MIN_ROW_COUNT} and {MAX_ROW_COUNT}."
        )
    if scenario not in SCENARIO_DEFECT_RATIOS:
        raise SyntheticDataValidationError("Synthetic scenario is not supported.")
    if len(TABLE_SPECS) != 17 or len({spec.name for spec in TABLE_SPECS}) != 17:
        raise SyntheticDataTechnicalError("Synthetic table contract must contain 17 tables.")


def _entropy(seed: int, label: str, index: int) -> int:
    payload = f"{GENERATOR_VERSION}:{seed}:{label}:{index}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _uniform(seed: int, label: str, index: int) -> float:
    return _entropy(seed, label, index) / float(2**64)


def _record_key(table_name: str, index: int) -> str:
    prefix = table_name.removeprefix("synthetic_").upper()[:12]
    return f"SYN-{prefix}-{index:08d}"


def _business_key(table_name: str, index: int) -> str:
    prefix = table_name.removeprefix("synthetic_").upper()[:10]
    return f"BIZ-{prefix}-{index:08d}"


def _parent_index(seed: int, table_name: str, column: str, index: int, row_count: int) -> int:
    probability = _uniform(seed, f"{table_name}:{column}:activity-segment", index)
    entropy = _entropy(seed, f"{table_name}:{column}:parent", index)
    if probability < 0.60:
        return entropy % max(1, row_count // 10)
    if probability < 0.90:
        return row_count // 10 + entropy % max(1, row_count * 4 // 10)
    return row_count // 2 + entropy % max(1, row_count - row_count // 2)


def _valid_formatted_value(kind: str, seed: int, index: int) -> str:
    suffix = _entropy(seed, f"format:{kind}", index) % 10_000_000
    values = {
        "email": f"synthetic-{suffix}@example.invalid",
        "contact": (
            f"synthetic-{suffix}@example.invalid" if index % 2 == 0 else f"+90000{suffix:07d}"
        ),
        "postal": f"SYN-{suffix % 100000:05d}",
        "iban": f"SYN-IBAN-{suffix:010d}",
        "currency": "SYN",
        "channel": ("BRANCH", "MOBILE", "WEB", "ATM")[suffix % 4],
        "masked_pan": f"****-****-****-{suffix % 10000:04d}",
        "authorization": f"AUTH-{suffix:07d}",
        "product": ("SYN-CONSUMER", "SYN-AUTO", "SYN-HOME")[suffix % 3],
        "account_code": f"SYN-ACCOUNT-{suffix:07d}",
        "category": f"SYN-MCC-{suffix % 100:03d}",
        "settlement": f"SYN-SETTLEMENT-{suffix:07d}",
        "risk_model": f"SYN-RISK-{suffix % 5:02d}",
        "request_type": ("INQUIRY", "UPDATE", "DISPUTE", "CLOSURE")[suffix % 4],
        "entity_type": ("CUSTOMER", "ACCOUNT", "TRANSACTION", "CARD", "LOAN")[suffix % 5],
    }
    return values[kind]


def _measure(seed: int, table_name: str, index: int) -> Decimal:
    first = max(_uniform(seed, f"{table_name}:normal-a", index), 1e-12)
    second = _uniform(seed, f"{table_name}:normal-b", index)
    normal = math.sqrt(-2.0 * math.log(first)) * math.cos(2.0 * math.pi * second)
    value = min(math.exp(7.0 + normal), 1_000_000.0)
    return Decimal(f"{value:.2f}")


def _event_time(seed: int, table_name: str, index: int) -> datetime:
    day_offset = _entropy(seed, f"{table_name}:event-day", index) % 180
    seasonal_boost = 21 if index % 10 < 3 else 0
    second_offset = _entropy(seed, f"{table_name}:event-second", index) % 86_400
    return REFERENCE_TIME - timedelta(
        days=max(0, int(day_offset) - seasonal_boost), seconds=int(second_offset)
    )


def _scenario_rates(scenario: str, *, supports_relation_defect: bool) -> dict[str, float]:
    target = SCENARIO_DEFECT_RATIOS[scenario]
    if scenario == "stale-data":
        candidates = {"stale_record": 1.0}
    elif scenario == "duplicate-heavy":
        candidates = {"duplicate": 1.0}
    elif scenario == "referential-integrity":
        candidates = (
            {"referential_integrity_error": 1.0}
            if supports_relation_defect
            else {"consistency_error": 1.0}
        )
    else:
        candidates = dict(BASE_DEFECT_RATES)
        if not supports_relation_defect:
            candidates.pop("referential_integrity_error")
    return _scale_independent_rates(candidates, target)


def _scale_independent_rates(rates: Mapping[str, float], target_union: float) -> dict[str, float]:
    low, high = 0.0, 100.0
    for _ in range(80):
        factor = (low + high) / 2.0
        union = 1.0
        for rate in rates.values():
            union *= 1.0 - min(rate * factor, 0.95)
        union = 1.0 - union
        if union < target_union:
            low = factor
        else:
            high = factor
    factor = (low + high) / 2.0
    return {name: min(rate * factor, 0.95) for name, rate in rates.items()}


def _selected_defects(
    spec: TableSpec,
    seed: int,
    scenario: str,
    index: int,
) -> tuple[str, ...]:
    rates = _scenario_rates(scenario, supports_relation_defect=bool(spec.relations))
    selected: list[str] = []
    for defect_type, rate in rates.items():
        selection_index = index // 2 if defect_type == "duplicate" else index
        if _uniform(seed, f"{spec.name}:defect:{defect_type}", selection_index) < rate:
            selected.append(defect_type)
    return tuple(selected)


def build_source_row(
    spec: TableSpec,
    *,
    seed: int,
    scenario: str,
    index: int,
    row_count: int,
) -> tuple[tuple[object, ...], tuple[DefectTruth, ...]]:
    record_key = _record_key(spec.name, index)
    values: dict[str, object] = {
        spec.primary_key: record_key,
        spec.business_key: _business_key(spec.name, index),
        spec.descriptive_column: f"Tamamen sentetik {spec.purpose.lower()} {index:08d}",
        spec.formatted_column: _valid_formatted_value(spec.format_kind, seed, index),
        spec.status_column: VALID_STATUSES[
            _entropy(seed, f"{spec.name}:status", index) % len(VALID_STATUSES)
        ],
        spec.measure_column: _measure(seed, spec.name, index),
        "required_value": f"SYN-REQUIRED-{index:08d}",
        "effective_from": REFERENCE_TIME.date() - timedelta(days=180 + index % 30),
        "effective_to": REFERENCE_TIME.date() + timedelta(days=index % 30),
        "event_time": _event_time(seed, spec.name, index),
        "updated_at": _event_time(seed, spec.name, index) + timedelta(hours=2),
        "ingestion_time": _event_time(seed, spec.name, index) + timedelta(hours=3),
        "synthetic_origin": True,
    }
    for relation in spec.relations:
        parent_index = _parent_index(seed, spec.name, relation.column, index, row_count)
        values[relation.column] = _record_key(relation.target_table, parent_index)

    truths: dict[tuple[str, str], DefectTruth] = {}
    selected = _selected_defects(spec, seed, scenario, index)
    for defect_type in selected:
        column = _apply_defect(spec, values, defect_type, seed=seed, index=index)
        truths[(record_key, defect_type)] = _truth(spec, record_key, column, defect_type)
        if defect_type == "duplicate":
            paired_index = index - 1 if index % 2 else index + 1
            if paired_index < row_count:
                paired_key = _record_key(spec.name, paired_index)
                truths[(paired_key, defect_type)] = _truth(
                    spec,
                    paired_key,
                    spec.business_key,
                    defect_type,
                )

    columns = _source_columns(spec)
    return tuple(values[column] for column in columns), tuple(truths.values())


def _apply_defect(
    spec: TableSpec,
    values: dict[str, object],
    defect_type: str,
    *,
    seed: int,
    index: int,
) -> str:
    if defect_type == "missing_value":
        values["required_value"] = None
        return "required_value"
    if defect_type == "blank_or_whitespace":
        values[spec.descriptive_column] = "   "
        return spec.descriptive_column
    if defect_type == "duplicate":
        values[spec.business_key] = f"DUP-{spec.name.upper()}-{index // 2:08d}"
        return spec.business_key
    if defect_type == "invalid_format":
        values[spec.formatted_column] = "INVALID_FORMAT"
        return spec.formatted_column
    if defect_type == "invalid_domain_value":
        values[spec.status_column] = "INVALID_STATUS"
        return spec.status_column
    if defect_type == "consistency_error":
        values["effective_to"] = REFERENCE_TIME.date() - timedelta(days=365)
        return "effective_to"
    if defect_type == "referential_integrity_error":
        relation = spec.relations[0]
        values[relation.column] = f"SYN-MISSING-{_entropy(seed, spec.name, index):016X}"
        return relation.column
    if defect_type == "stale_record":
        stale_event = REFERENCE_TIME - timedelta(days=900 + index % 30)
        values["event_time"] = stale_event
        values["updated_at"] = stale_event + timedelta(hours=1)
        values["ingestion_time"] = stale_event + timedelta(hours=2)
        return "updated_at"
    if defect_type == "outlier":
        values[spec.measure_column] = OUTLIER_THRESHOLD + Decimal(index + 1)
        return spec.measure_column
    raise SyntheticDataTechnicalError(f"Unsupported synthetic defect type: {defect_type}")


def _truth(
    spec: TableSpec,
    record_key: str,
    column_name: str,
    defect_type: str,
) -> DefectTruth:
    severity = (
        "HIGH"
        if defect_type in {"consistency_error", "referential_integrity_error", "stale_record"}
        else "MEDIUM"
    )
    return DefectTruth(
        table_name=spec.name,
        record_key=record_key,
        column_name=column_name,
        quality_dimension=DEFECT_DIMENSIONS[defect_type],
        defect_type=defect_type,
        expected_rule_result="FAIL",
        expected_severity=severity,
    )


def _source_columns(spec: TableSpec) -> tuple[str, ...]:
    return (
        spec.primary_key,
        spec.business_key,
        *(relation.column for relation in spec.relations),
        spec.descriptive_column,
        spec.formatted_column,
        spec.status_column,
        spec.measure_column,
        "required_value",
        "effective_from",
        "effective_to",
        "event_time",
        "updated_at",
        "ingestion_time",
        "synthetic_origin",
    )


def _iter_rows(
    spec: TableSpec,
    *,
    seed: int,
    scenario: str,
    row_count: int,
) -> Iterator[tuple[tuple[object, ...], tuple[DefectTruth, ...]]]:
    for index in range(row_count):
        yield build_source_row(
            spec,
            seed=seed,
            scenario=scenario,
            index=index,
            row_count=row_count,
        )


class PostgreSQLSyntheticDatasetManager:
    """Yerel/test PostgreSQL üzerinde kontrollü source dataset yaşam döngüsü."""

    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        if not connection.autocommit:
            raise SyntheticDataValidationError(
                "Synthetic PostgreSQL manager requires an autocommit connection."
            )
        self.connection = connection

    def reset(self) -> None:
        with self.connection.transaction(), self.connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(SOURCE_SCHEMA))
            )
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(CONTROL_SCHEMA))
            )

    def generate(
        self,
        *,
        environment: str,
        allow_test_data: bool,
        seed: int,
        scenario: str,
        row_count: int,
        reset: bool,
        progress: bool = True,
    ) -> GenerationSummary:
        database_name = self._database_name()
        validate_generation_request(
            environment=environment,
            database_name=database_name,
            allow_test_data=allow_test_data,
            row_count=row_count,
            scenario=scenario,
        )
        if reset:
            self.reset()
        started = perf_counter()
        run_id = _run_id(seed=seed, scenario=scenario, row_count=row_count)
        digest = hashlib.sha256()
        table_metrics: list[TableGenerationMetric] = []
        profile_metrics: list[ProfileMetric] = []
        validation_metrics: list[ValidationMetric] = []
        try:
            with self.connection.transaction(), self.connection.cursor() as cursor:
                self._reject_existing_generation(cursor)
                self._create_control_schema(cursor)
                self._create_source_tables(cursor)
                for table_index, spec in enumerate(TABLE_SPECS, start=1):
                    metric = self._generate_table(
                        cursor,
                        spec,
                        run_id=run_id,
                        seed=seed,
                        scenario=scenario,
                        row_count=row_count,
                        digest=digest,
                    )
                    table_metrics.append(metric)
                    if progress:
                        print(
                            json.dumps(
                                {
                                    "event": "table_generated",
                                    "table": spec.name,
                                    "table_index": table_index,
                                    "table_count": len(TABLE_SPECS),
                                    "rows": metric.generated_row_count,
                                    "defective_rows": metric.defective_row_count,
                                    "duration_seconds": round(
                                        metric.generation_duration_seconds, 6
                                    ),
                                },
                                sort_keys=True,
                            )
                        )
                self._create_source_indexes(cursor)
                profile_metrics.extend(self._profile_tables(cursor))
                validation_metrics.extend(self._validate_ground_truth(cursor, run_id))
                duration = perf_counter() - started
                peak_memory_bytes = _peak_memory_bytes()
                self._store_summary(
                    cursor,
                    run_id=run_id,
                    environment=environment,
                    seed=seed,
                    scenario=scenario,
                    row_count=row_count,
                    table_metrics=table_metrics,
                    profile_metrics=profile_metrics,
                    validation_metrics=validation_metrics,
                    canonical_sha256=digest.hexdigest(),
                    generation_duration_seconds=duration,
                    peak_memory_bytes=peak_memory_bytes,
                )
            database_size = self._database_size()
        except (psycopg.Error, OSError, ValueError, TypeError) as exc:
            raise SyntheticDataTechnicalError(
                "Synthetic PostgreSQL dataset generation failed."
            ) from exc

        summary = GenerationSummary(
            run_id=run_id,
            generator_version=GENERATOR_VERSION,
            schema_version=SCHEMA_VERSION,
            configuration_version=CONFIGURATION_VERSION,
            seed=seed,
            scenario=scenario,
            row_count_per_table=row_count,
            table_metrics=tuple(table_metrics),
            profile_metrics=tuple(profile_metrics),
            validation_metrics=tuple(validation_metrics),
            canonical_sha256=digest.hexdigest(),
            generation_duration_seconds=perf_counter() - started,
            database_size_bytes=database_size,
            peak_memory_bytes=peak_memory_bytes,
        )
        if not summary.all_validations_passed:
            raise SyntheticDataTechnicalError(
                "Independent ground-truth validation detected a dataset mismatch."
            )
        return summary

    def _database_name(self) -> str:
        with self.connection.cursor() as cursor:
            value = cursor.execute("SELECT current_database()").fetchone()
        if value is None:
            raise SyntheticDataTechnicalError("PostgreSQL database name could not be resolved.")
        return str(value[0])

    def _database_size(self) -> int:
        with self.connection.cursor() as cursor:
            value = cursor.execute("SELECT pg_database_size(current_database())").fetchone()
        if value is None:
            raise SyntheticDataTechnicalError("PostgreSQL database size could not be measured.")
        return int(value[0])

    @staticmethod
    def _create_control_schema(cursor: psycopg.Cursor[Any]) -> None:
        cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(CONTROL_SCHEMA)))
        cursor.execute(
            sql.SQL(
                """
                CREATE TABLE {}.generation_runs (
                    run_id TEXT PRIMARY KEY,
                    generator_version TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    configuration_version TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    seed BIGINT NOT NULL,
                    scenario TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    generation_timestamp TIMESTAMPTZ NOT NULL,
                    table_count INTEGER NOT NULL,
                    row_count_per_table INTEGER NOT NULL,
                    total_row_count BIGINT NOT NULL,
                    total_expected_defect_count BIGINT NOT NULL,
                    defect_configuration JSONB NOT NULL,
                    canonical_sha256 TEXT NOT NULL,
                    generation_duration_seconds DOUBLE PRECISION NOT NULL,
                    profiling_duration_seconds DOUBLE PRECISION NOT NULL,
                    rule_validation_duration_seconds DOUBLE PRECISION NOT NULL,
                    peak_memory_bytes BIGINT NOT NULL,
                    synthetic_origin BOOLEAN NOT NULL,
                    UNIQUE (generator_version, seed, scenario, row_count_per_table)
                )
                """
            ).format(sql.Identifier(CONTROL_SCHEMA))
        )
        cursor.execute(
            sql.SQL(
                """
                CREATE TABLE {}.table_metrics (
                    run_id TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    generated_row_count INTEGER NOT NULL,
                    clean_row_count INTEGER NOT NULL,
                    defective_row_count INTEGER NOT NULL,
                    expected_defect_count INTEGER NOT NULL,
                    generation_duration_seconds DOUBLE PRECISION NOT NULL,
                    rows_per_second DOUBLE PRECISION NOT NULL,
                    PRIMARY KEY (run_id, table_name)
                )
                """
            ).format(sql.Identifier(CONTROL_SCHEMA))
        )
        cursor.execute(
            sql.SQL(
                """
                CREATE TABLE {}.profile_metrics (
                    run_id TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    row_count INTEGER NOT NULL,
                    required_value_null_count INTEGER NOT NULL,
                    distinct_business_key_count INTEGER NOT NULL,
                    minimum_measure NUMERIC(20, 2),
                    maximum_measure NUMERIC(20, 2),
                    profiling_duration_seconds DOUBLE PRECISION NOT NULL,
                    PRIMARY KEY (run_id, table_name)
                )
                """
            ).format(sql.Identifier(CONTROL_SCHEMA))
        )
        cursor.execute(
            sql.SQL(
                """
                CREATE TABLE {}.defect_manifest (
                    run_id TEXT NOT NULL,
                    scenario_id TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    record_key TEXT NOT NULL,
                    column_name TEXT NOT NULL,
                    quality_dimension TEXT NOT NULL,
                    defect_type TEXT NOT NULL,
                    expected_rule_result TEXT NOT NULL,
                    expected_severity TEXT NOT NULL,
                    generator_version TEXT NOT NULL,
                    seed BIGINT NOT NULL,
                    ground_truth_version TEXT NOT NULL,
                    PRIMARY KEY (
                        run_id, table_name, record_key, column_name, defect_type
                    )
                )
                """
            ).format(sql.Identifier(CONTROL_SCHEMA))
        )
        cursor.execute(
            sql.SQL(
                """
                CREATE TABLE {}.validation_metrics (
                    run_id TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    defect_type TEXT NOT NULL,
                    expected_defect_count INTEGER NOT NULL,
                    detected_defect_count INTEGER NOT NULL,
                    true_positive INTEGER NOT NULL,
                    false_positive INTEGER NOT NULL,
                    false_negative INTEGER NOT NULL,
                    precision NUMERIC(12, 10) NOT NULL,
                    recall NUMERIC(12, 10) NOT NULL,
                    execution_duration_seconds DOUBLE PRECISION NOT NULL,
                    PRIMARY KEY (run_id, table_name, defect_type)
                )
                """
            ).format(sql.Identifier(CONTROL_SCHEMA))
        )

    @staticmethod
    def _reject_existing_generation(cursor: psycopg.Cursor[Any]) -> None:
        existing = cursor.execute(
            """
            SELECT 1
            FROM pg_namespace
            WHERE nspname IN (%s, %s)
            LIMIT 1
            """,
            (SOURCE_SCHEMA, CONTROL_SCHEMA),
        ).fetchone()
        if existing is not None:
            raise SyntheticDataValidationError(
                "Synthetic dataset already exists; explicit reset is required."
            )

    @staticmethod
    def _create_source_tables(cursor: psycopg.Cursor[Any]) -> None:
        cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(SOURCE_SCHEMA)))
        for spec in TABLE_SPECS:
            relation_columns = sql.SQL(", ").join(
                sql.SQL("{} TEXT").format(sql.Identifier(relation.column))
                for relation in spec.relations
            )
            optional_relations = sql.SQL(", ") + relation_columns if spec.relations else sql.SQL("")
            cursor.execute(
                sql.SQL(
                    """
                    CREATE TABLE {}.{} (
                        {} TEXT PRIMARY KEY,
                        {} TEXT{}
                        , {} TEXT
                        , {} TEXT
                        , {} TEXT
                        , {} NUMERIC(20, 2)
                        , required_value TEXT
                        , effective_from DATE NOT NULL
                        , effective_to DATE NOT NULL
                        , event_time TIMESTAMPTZ NOT NULL
                        , updated_at TIMESTAMPTZ NOT NULL
                        , ingestion_time TIMESTAMPTZ NOT NULL
                        , synthetic_origin BOOLEAN NOT NULL
                    )
                    """
                ).format(
                    sql.Identifier(SOURCE_SCHEMA),
                    sql.Identifier(spec.name),
                    sql.Identifier(spec.primary_key),
                    sql.Identifier(spec.business_key),
                    optional_relations,
                    sql.Identifier(spec.descriptive_column),
                    sql.Identifier(spec.formatted_column),
                    sql.Identifier(spec.status_column),
                    sql.Identifier(spec.measure_column),
                )
            )

    def _generate_table(
        self,
        cursor: psycopg.Cursor[Any],
        spec: TableSpec,
        *,
        run_id: str,
        seed: int,
        scenario: str,
        row_count: int,
        digest: Any,
    ) -> TableGenerationMetric:
        started = perf_counter()
        truths: dict[tuple[str, str, str], DefectTruth] = {}
        copy_statement = sql.SQL("COPY {}.{} ({}) FROM STDIN").format(
            sql.Identifier(SOURCE_SCHEMA),
            sql.Identifier(spec.name),
            sql.SQL(", ").join(map(sql.Identifier, _source_columns(spec))),
        )
        with cursor.copy(copy_statement) as copy:
            for row, row_truths in _iter_rows(
                spec,
                seed=seed,
                scenario=scenario,
                row_count=row_count,
            ):
                copy.write_row(row)
                digest.update(_canonical_row(row))
                for truth in row_truths:
                    truths[(truth.record_key, truth.column_name, truth.defect_type)] = truth

        truth_values = tuple(
            sorted(
                truths.values(),
                key=lambda item: (item.record_key, item.column_name, item.defect_type),
            )
        )
        manifest_statement = sql.SQL(
            """
            COPY {}.defect_manifest (
                run_id, scenario_id, table_name, record_key, column_name,
                quality_dimension, defect_type, expected_rule_result,
                expected_severity, generator_version, seed, ground_truth_version
            ) FROM STDIN
            """
        ).format(sql.Identifier(CONTROL_SCHEMA))
        with cursor.copy(manifest_statement) as copy:
            for truth in truth_values:
                copy.write_row(
                    (
                        run_id,
                        scenario,
                        truth.table_name,
                        truth.record_key,
                        truth.column_name,
                        truth.quality_dimension,
                        truth.defect_type,
                        truth.expected_rule_result,
                        truth.expected_severity,
                        GENERATOR_VERSION,
                        seed,
                        GROUND_TRUTH_VERSION,
                    )
                )
                digest.update(_canonical_truth(truth))
        defective_records = {truth.record_key for truth in truth_values}
        duration = perf_counter() - started
        return TableGenerationMetric(
            table_name=spec.name,
            generated_row_count=row_count,
            clean_row_count=row_count - len(defective_records),
            defective_row_count=len(defective_records),
            expected_defect_count=len(truth_values),
            generation_duration_seconds=duration,
            rows_per_second=row_count / duration if duration else 0.0,
        )

    @staticmethod
    def _create_source_indexes(cursor: psycopg.Cursor[Any]) -> None:
        for spec in TABLE_SPECS:
            index_columns = (
                spec.business_key,
                spec.status_column,
                "updated_at",
                *(relation.column for relation in spec.relations),
            )
            for column in index_columns:
                index_name = f"idx_{spec.name.removeprefix('synthetic_')}_{column}"[:63]
                cursor.execute(
                    sql.SQL("CREATE INDEX {} ON {}.{} ({})").format(
                        sql.Identifier(index_name),
                        sql.Identifier(SOURCE_SCHEMA),
                        sql.Identifier(spec.name),
                        sql.Identifier(column),
                    )
                )

    def _validate_ground_truth(
        self,
        cursor: psycopg.Cursor[Any],
        run_id: str,
    ) -> tuple[ValidationMetric, ...]:
        results: list[ValidationMetric] = []
        for spec in TABLE_SPECS:
            defect_types = cursor.execute(
                sql.SQL(
                    """
                    SELECT DISTINCT defect_type
                    FROM {}.defect_manifest
                    WHERE run_id = %s AND table_name = %s
                    ORDER BY defect_type
                    """
                ).format(sql.Identifier(CONTROL_SCHEMA)),
                (run_id, spec.name),
            ).fetchall()
            for defect_row in defect_types:
                defect_type = str(defect_row[0])
                expected = {
                    str(row[0])
                    for row in cursor.execute(
                        sql.SQL(
                            """
                            SELECT record_key
                            FROM {}.defect_manifest
                            WHERE run_id = %s AND table_name = %s AND defect_type = %s
                            """
                        ).format(sql.Identifier(CONTROL_SCHEMA)),
                        (run_id, spec.name, defect_type),
                    ).fetchall()
                }
                validation_started = perf_counter()
                detected = self._detect_defect(cursor, spec, defect_type)
                validation_duration = perf_counter() - validation_started
                true_positive = len(expected & detected)
                false_positive = len(detected - expected)
                false_negative = len(expected - detected)
                precision = _ratio(true_positive, true_positive + false_positive)
                recall = _ratio(true_positive, true_positive + false_negative)
                results.append(
                    ValidationMetric(
                        table_name=spec.name,
                        defect_type=defect_type,
                        expected_defect_count=len(expected),
                        detected_defect_count=len(detected),
                        true_positive=true_positive,
                        false_positive=false_positive,
                        false_negative=false_negative,
                        precision=precision,
                        recall=recall,
                        execution_duration_seconds=validation_duration,
                    )
                )
        return tuple(results)

    @staticmethod
    def _profile_tables(cursor: psycopg.Cursor[Any]) -> tuple[ProfileMetric, ...]:
        metrics: list[ProfileMetric] = []
        for spec in TABLE_SPECS:
            started = perf_counter()
            result = cursor.execute(
                sql.SQL(
                    """
                    SELECT
                        COUNT(*),
                        COUNT(*) FILTER (WHERE required_value IS NULL),
                        COUNT(DISTINCT {}),
                        MIN({}),
                        MAX({})
                    FROM {}.{}
                    """
                ).format(
                    sql.Identifier(spec.business_key),
                    sql.Identifier(spec.measure_column),
                    sql.Identifier(spec.measure_column),
                    sql.Identifier(SOURCE_SCHEMA),
                    sql.Identifier(spec.name),
                )
            ).fetchone()
            if result is None:
                raise SyntheticDataTechnicalError("Synthetic profile query returned no result.")
            metrics.append(
                ProfileMetric(
                    table_name=spec.name,
                    row_count=int(result[0]),
                    required_value_null_count=int(result[1]),
                    distinct_business_key_count=int(result[2]),
                    minimum_measure=(Decimal(result[3]) if result[3] is not None else None),
                    maximum_measure=(Decimal(result[4]) if result[4] is not None else None),
                    profiling_duration_seconds=perf_counter() - started,
                )
            )
        return tuple(metrics)

    @staticmethod
    def _detect_defect(
        cursor: psycopg.Cursor[Any],
        spec: TableSpec,
        defect_type: str,
    ) -> set[str]:
        table = sql.Identifier(SOURCE_SCHEMA, spec.name)
        primary_key = sql.Identifier(spec.primary_key)
        if defect_type == "missing_value":
            query = sql.SQL("SELECT {} FROM {} WHERE required_value IS NULL").format(
                primary_key, table
            )
        elif defect_type == "blank_or_whitespace":
            query = sql.SQL("SELECT {} FROM {} WHERE btrim({}) = ''").format(
                primary_key, table, sql.Identifier(spec.descriptive_column)
            )
        elif defect_type == "duplicate":
            query = sql.SQL(
                """
                SELECT source.{}
                FROM {} AS source
                JOIN (
                    SELECT {} FROM {}
                    WHERE {} IS NOT NULL
                    GROUP BY {} HAVING COUNT(*) > 1
                ) AS duplicates
                ON source.{} = duplicates.{}
                """
            ).format(
                primary_key,
                table,
                sql.Identifier(spec.business_key),
                table,
                sql.Identifier(spec.business_key),
                sql.Identifier(spec.business_key),
                sql.Identifier(spec.business_key),
                sql.Identifier(spec.business_key),
            )
        elif defect_type == "invalid_format":
            query = sql.SQL("SELECT {} FROM {} WHERE {} = 'INVALID_FORMAT'").format(
                primary_key, table, sql.Identifier(spec.formatted_column)
            )
        elif defect_type == "invalid_domain_value":
            query = sql.SQL("SELECT {} FROM {} WHERE {} = 'INVALID_STATUS'").format(
                primary_key, table, sql.Identifier(spec.status_column)
            )
        elif defect_type == "consistency_error":
            query = sql.SQL("SELECT {} FROM {} WHERE effective_to < effective_from").format(
                primary_key, table
            )
        elif defect_type == "referential_integrity_error":
            relation = spec.relations[0]
            query = sql.SQL(
                """
                SELECT source.{}
                FROM {} AS source
                LEFT JOIN {} AS parent
                  ON source.{} = parent.{}
                WHERE source.{} IS NOT NULL AND parent.{} IS NULL
                """
            ).format(
                primary_key,
                table,
                sql.Identifier(SOURCE_SCHEMA, relation.target_table),
                sql.Identifier(relation.column),
                sql.Identifier(relation.target_key),
                sql.Identifier(relation.column),
                sql.Identifier(relation.target_key),
            )
        elif defect_type == "stale_record":
            query = sql.SQL("SELECT {} FROM {} WHERE updated_at < %s").format(primary_key, table)
            return {str(row[0]) for row in cursor.execute(query, (STALE_THRESHOLD,)).fetchall()}
        elif defect_type == "outlier":
            query = sql.SQL("SELECT {} FROM {} WHERE {} > %s").format(
                primary_key, table, sql.Identifier(spec.measure_column)
            )
            return {str(row[0]) for row in cursor.execute(query, (OUTLIER_THRESHOLD,)).fetchall()}
        else:
            raise SyntheticDataTechnicalError(
                f"Unsupported independent defect validation: {defect_type}"
            )
        return {str(row[0]) for row in cursor.execute(query).fetchall()}

    @staticmethod
    def _store_summary(
        cursor: psycopg.Cursor[Any],
        *,
        run_id: str,
        environment: str,
        seed: int,
        scenario: str,
        row_count: int,
        table_metrics: Sequence[TableGenerationMetric],
        profile_metrics: Sequence[ProfileMetric],
        validation_metrics: Sequence[ValidationMetric],
        canonical_sha256: str,
        generation_duration_seconds: float,
        peak_memory_bytes: int,
    ) -> None:
        cursor.execute(
            sql.SQL(
                """
                INSERT INTO {}.generation_runs (
                    run_id, generator_version, schema_version,
                    configuration_version, policy_version, seed, scenario,
                    environment, generation_timestamp, table_count,
                    row_count_per_table, total_row_count,
                    total_expected_defect_count, defect_configuration,
                    canonical_sha256, generation_duration_seconds,
                    profiling_duration_seconds, rule_validation_duration_seconds,
                    peak_memory_bytes, synthetic_origin
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, TRUE
                )
                """
            ).format(sql.Identifier(CONTROL_SCHEMA)),
            (
                run_id,
                GENERATOR_VERSION,
                SCHEMA_VERSION,
                CONFIGURATION_VERSION,
                POLICY_VERSION,
                seed,
                scenario,
                environment,
                datetime.now(timezone.utc),
                len(TABLE_SPECS),
                row_count,
                sum(metric.generated_row_count for metric in table_metrics),
                sum(metric.expected_defect_count for metric in table_metrics),
                json.dumps(
                    {
                        "requested_default_rates": BASE_DEFECT_RATES,
                        "target_defective_record_ratio": SCENARIO_DEFECT_RATIOS[scenario],
                        "effective_rates_with_relations": _scenario_rates(
                            scenario, supports_relation_defect=True
                        ),
                        "effective_rates_without_relations": _scenario_rates(
                            scenario, supports_relation_defect=False
                        ),
                    },
                    sort_keys=True,
                ),
                canonical_sha256,
                generation_duration_seconds,
                sum(metric.profiling_duration_seconds for metric in profile_metrics),
                sum(metric.execution_duration_seconds for metric in validation_metrics),
                peak_memory_bytes,
            ),
        )
        cursor.executemany(
            sql.SQL(
                """
                INSERT INTO {}.table_metrics (
                    run_id, table_name, generated_row_count, clean_row_count,
                    defective_row_count, expected_defect_count,
                    generation_duration_seconds, rows_per_second
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
            ).format(sql.Identifier(CONTROL_SCHEMA)),
            [
                (
                    run_id,
                    metric.table_name,
                    metric.generated_row_count,
                    metric.clean_row_count,
                    metric.defective_row_count,
                    metric.expected_defect_count,
                    metric.generation_duration_seconds,
                    metric.rows_per_second,
                )
                for metric in table_metrics
            ],
        )
        cursor.executemany(
            sql.SQL(
                """
                INSERT INTO {}.profile_metrics (
                    run_id, table_name, row_count, required_value_null_count,
                    distinct_business_key_count, minimum_measure, maximum_measure,
                    profiling_duration_seconds
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
            ).format(sql.Identifier(CONTROL_SCHEMA)),
            [
                (
                    run_id,
                    metric.table_name,
                    metric.row_count,
                    metric.required_value_null_count,
                    metric.distinct_business_key_count,
                    metric.minimum_measure,
                    metric.maximum_measure,
                    metric.profiling_duration_seconds,
                )
                for metric in profile_metrics
            ],
        )
        cursor.executemany(
            sql.SQL(
                """
                INSERT INTO {}.validation_metrics (
                    run_id, table_name, defect_type, expected_defect_count,
                    detected_defect_count, true_positive, false_positive,
                    false_negative, precision, recall
                    , execution_duration_seconds
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
            ).format(sql.Identifier(CONTROL_SCHEMA)),
            [
                (
                    run_id,
                    metric.table_name,
                    metric.defect_type,
                    metric.expected_defect_count,
                    metric.detected_defect_count,
                    metric.true_positive,
                    metric.false_positive,
                    metric.false_negative,
                    metric.precision,
                    metric.recall,
                    metric.execution_duration_seconds,
                )
                for metric in validation_metrics
            ],
        )


def _run_id(*, seed: int, scenario: str, row_count: int) -> str:
    payload = (
        f"{GENERATOR_VERSION}:{SCHEMA_VERSION}:{CONFIGURATION_VERSION}:"
        f"{seed}:{scenario}:{row_count}"
    ).encode()
    return f"SYN-RUN-{hashlib.sha256(payload).hexdigest()[:24].upper()}"


def _canonical_value(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _canonical_row(row: Sequence[object]) -> bytes:
    payload = json.dumps(
        [_canonical_value(value) for value in row],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return payload.encode() + b"\n"


def _canonical_truth(truth: DefectTruth) -> bytes:
    payload = (
        truth.table_name,
        truth.record_key,
        truth.column_name,
        truth.quality_dimension,
        truth.defect_type,
        truth.expected_rule_result,
        truth.expected_severity,
    )
    return json.dumps(payload, separators=(",", ":")).encode() + b"\n"


def _ratio(numerator: int, denominator: int) -> Decimal:
    if denominator == 0:
        return Decimal("1.0000000000")
    return (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.0000000001"))


def _peak_memory_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def _connect(args: argparse.Namespace) -> psycopg.Connection[Any]:
    password = os.environ.get("PGPASSWORD")
    if not password:
        raise SyntheticDataValidationError("PGPASSWORD is required and must not be logged.")
    try:
        return psycopg.connect(
            host=args.host,
            port=args.port,
            dbname=args.database,
            user=args.user,
            password=password,
            connect_timeout=10,
            application_name="veri-kalitesi-synthetic-generator",
            autocommit=True,
        )
    except psycopg.Error as exc:
        raise SyntheticDataTechnicalError("Synthetic PostgreSQL connection failed.") from exc


def _summary_payload(summary: GenerationSummary) -> dict[str, object]:
    return {
        "run_id": summary.run_id,
        "generator_version": summary.generator_version,
        "schema_version": summary.schema_version,
        "configuration_version": summary.configuration_version,
        "seed": summary.seed,
        "scenario": summary.scenario,
        "table_count": len(summary.table_metrics),
        "row_count_per_table": summary.row_count_per_table,
        "total_rows": summary.total_rows,
        "total_expected_defects": summary.total_expected_defects,
        "canonical_sha256": summary.canonical_sha256,
        "generation_duration_seconds": round(summary.generation_duration_seconds, 6),
        "profiling_duration_seconds": round(
            sum(metric.profiling_duration_seconds for metric in summary.profile_metrics), 6
        ),
        "rule_validation_duration_seconds": round(
            sum(metric.execution_duration_seconds for metric in summary.validation_metrics), 6
        ),
        "slowest_quality_rules": [
            {
                "table": metric.table_name,
                "defect_type": metric.defect_type,
                "duration_seconds": round(metric.execution_duration_seconds, 6),
            }
            for metric in sorted(
                summary.validation_metrics,
                key=lambda item: item.execution_duration_seconds,
                reverse=True,
            )[:5]
        ],
        "database_size_bytes": summary.database_size_bytes,
        "peak_memory_bytes": summary.peak_memory_bytes,
        "ground_truth_validation_passed": summary.all_validations_passed,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("generate", "reset"))
    parser.add_argument("--environment", required=True, choices=sorted(ALLOWED_ENVIRONMENTS))
    parser.add_argument("--allow-test-data", action="store_true")
    parser.add_argument("--host", default=os.environ.get("PGHOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PGPORT", "5432")))
    parser.add_argument("--database", default=os.environ.get("PGDATABASE", ""))
    parser.add_argument("--user", default=os.environ.get("PGUSER", ""))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--scenario", choices=sorted(SCENARIO_DEFECT_RATIOS), default="mixed-quality"
    )
    parser.add_argument("--row-count", type=int, default=DEFAULT_ROW_COUNT)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    validate_generation_request(
        environment=args.environment,
        database_name=args.database,
        allow_test_data=args.allow_test_data,
        row_count=args.row_count,
        scenario=args.scenario,
    )
    connection = _connect(args)
    try:
        manager = PostgreSQLSyntheticDatasetManager(connection)
        if args.operation == "reset":
            manager.reset()
            print(json.dumps({"status": "reset", "synthetic_schemas_removed": True}))
            return 0
        summary = manager.generate(
            environment=args.environment,
            allow_test_data=args.allow_test_data,
            seed=args.seed,
            scenario=args.scenario,
            row_count=args.row_count,
            reset=args.reset,
            progress=not args.quiet,
        )
        print(json.dumps(_summary_payload(summary), sort_keys=True))
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
