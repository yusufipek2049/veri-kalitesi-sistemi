"""F-02: scope_version check constraint'i ile domain sözleşmesinin uyumu.

Migration 24, ``scope_version > 0`` koşulunu koymuştu; execution alanındaki üç
talep tipi ise ``scope_version=0`` üretir. Bu, üç iş akışının PostgreSQL
INSERT'ini check-constraint ihlaliyle düşürüyordu ve depo katmanı hatayı
yanıltıcı bir "pending request" çakışmasına çeviriyordu.

Buradaki testler PostgreSQL gerektirmez: constraint ifadesi SQLite üzerinde
gerçek DDL olarak uygulanır, sınıflandırma ise doğrudan denenir.
"""

from __future__ import annotations

import importlib.util
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy.exc import IntegrityError

from veri_kalitesi.governance.errors import (
    GovernanceConflictError,
    GovernanceValidationError,
)
from veri_kalitesi.governance.repository import (
    PENDING_REQUEST_INDEX,
    _classify_integrity_error,
    _violated_constraint,
)
from veri_kalitesi.governance.service import _EXECUTION_REQUEST_TYPES

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20260816_27_governance_scope_version_execution.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_27", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = _load_migration()


@pytest.fixture
def constrained_table() -> Iterator[sqlite3.Connection]:
    """Constraint ifadesini gerçek DDL olarak uygulayan minimal tablo."""

    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE governance_approval_requests ("
        " approval_request_id TEXT PRIMARY KEY,"
        " request_type TEXT NOT NULL,"
        " scope_version INTEGER NOT NULL,"
        f" CONSTRAINT {MIGRATION.CONSTRAINT_NAME} CHECK ({MIGRATION.SCOPE_VERSION_CHECK})"
        ")"
    )
    yield connection
    connection.close()


def _insert(connection: sqlite3.Connection, request_type: str, scope_version: int) -> None:
    connection.execute(
        "INSERT INTO governance_approval_requests VALUES (?, ?, ?)",
        (f"{request_type}-{scope_version}", request_type, scope_version),
    )


@pytest.mark.parametrize("request_type", MIGRATION.EXECUTION_REQUEST_TYPES)
def test_execution_requests_may_carry_zero_scope_version(
    constrained_table: sqlite3.Connection, request_type: str
) -> None:
    _insert(constrained_table, request_type, 0)


@pytest.mark.parametrize(
    "request_type",
    ["DATASET_OWNER_CHANGE", "METADATA_CRITICAL_CHANGE", "FIELD_SENSITIVITY_MARK"],
)
def test_versioned_requests_still_require_positive_scope_version(
    constrained_table: sqlite3.Connection, request_type: str
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        _insert(constrained_table, request_type, 0)
    _insert(constrained_table, request_type, 1)


def test_negative_scope_version_is_rejected_for_every_type(
    constrained_table: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        _insert(constrained_table, "DATASET_OWNER_CHANGE", -1)


def test_migration_execution_types_match_domain_execution_types() -> None:
    """Constraint listesi domain'deki execution talep tipleriyle aynı olmalı."""

    assert set(MIGRATION.EXECUTION_REQUEST_TYPES) == {
        request_type.value for request_type in _EXECUTION_REQUEST_TYPES
    }


# ----------------------------------------------------------------------
# IntegrityError siniflandirmasi
# ----------------------------------------------------------------------


class _Diagnostics:
    def __init__(self, constraint_name: str | None) -> None:
        self.constraint_name = constraint_name


class _PsycopgError(Exception):
    def __init__(self, message: str, constraint_name: str | None) -> None:
        super().__init__(message)
        self.diag = _Diagnostics(constraint_name)


def _integrity_error(message: str, constraint_name: str | None = None) -> IntegrityError:
    return IntegrityError(
        "INSERT INTO governance_approval_requests ...",
        {},
        _PsycopgError(message, constraint_name),
    )


def test_pending_request_index_maps_to_conflict() -> None:
    error = _classify_integrity_error(
        _integrity_error("duplicate key value", PENDING_REQUEST_INDEX)
    )

    assert isinstance(error, GovernanceConflictError)
    assert "pending governance approval request" in str(error)


def test_check_constraint_violation_is_not_reported_as_pending_conflict() -> None:
    error = _classify_integrity_error(
        _integrity_error(
            "new row violates check constraint", "ck_governance_approval_scope_version"
        )
    )

    assert isinstance(error, GovernanceValidationError)
    assert "ck_governance_approval_scope_version" in str(error)
    assert "pending" not in str(error)


def test_unknown_constraint_falls_back_to_generic_conflict() -> None:
    error = _classify_integrity_error(_integrity_error("some other violation", None))

    assert isinstance(error, GovernanceConflictError)
    assert "pending governance approval request" not in str(error)


def test_constraint_name_recovered_from_message_without_diagnostics() -> None:
    error = _integrity_error(
        'new row violates check constraint "ck_governance_approval_status"', None
    )

    assert _violated_constraint(error) == "ck_governance_approval_status"
