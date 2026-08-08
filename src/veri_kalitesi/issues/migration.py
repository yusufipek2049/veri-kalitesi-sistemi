"""Legacy SQLite issue kayıtlarını PostgreSQL'e seçici ve idempotent aktarır."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from sqlalchemy import Table, func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.orm import Session

from veri_kalitesi.audit.postgresql_outbox import audit_outbox_table
from veri_kalitesi.issues.errors import IssueMigrationError
from veri_kalitesi.issues.postgresql_repository import issue_tables
from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory, transactional_session

_ISSUE_OBJECT_TYPE = "DATA_QUALITY_ISSUE"
_CHUNK_SIZE = 500


@dataclass(frozen=True)
class MigratedTable:
    table_name: str
    source_count: int
    inserted_count: int
    source_hash: str
    target_hash: str


@dataclass(frozen=True)
class IssueMigrationReport:
    tables: tuple[MigratedTable, ...]
    foreign_key_violations: int
    source_sha256_before: str
    source_sha256_after: str

    @property
    def source_count(self) -> int:
        return sum(item.source_count for item in self.tables)

    @property
    def inserted_count(self) -> int:
        return sum(item.inserted_count for item in self.tables)


@dataclass(frozen=True)
class _TablePlan:
    name: str
    table: Table
    key: str
    columns: tuple[str, ...]


class SQLiteIssueMigrator:
    """Bir legacy SQLite dosyasındaki otoriter issue kayıtlarını taşır."""

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        tables = issue_tables(schema)
        self._session_factory = session_factory
        self._plans = (
            _TablePlan(
                "data_quality_issues",
                tables.issues,
                "issue_id",
                (
                    "issue_id",
                    "issue_no",
                    "source_event_id",
                    "source_event_type",
                    "trigger_type",
                    "scope_type",
                    "scope_id",
                    "status",
                    "priority",
                    "assignee_user_id",
                    "deduplication_key_digest",
                    "payload_digest",
                    "occurrence_count",
                    "version",
                    "created_at",
                    "updated_at",
                    "last_seen_at",
                ),
            ),
            _TablePlan(
                "issue_history",
                tables.history,
                "history_id",
                (
                    "history_id",
                    "issue_id",
                    "action",
                    "actor_id",
                    "old_status",
                    "new_status",
                    "old_assignee_user_id",
                    "new_assignee_user_id",
                    "old_priority",
                    "new_priority",
                    "resolution_id",
                    "verification_id",
                    "occurred_at",
                ),
            ),
            _TablePlan(
                "issue_resolutions",
                tables.resolutions,
                "resolution_id",
                (
                    "resolution_id",
                    "issue_id",
                    "root_cause",
                    "corrective_action",
                    "evidence_reference_id",
                    "completed_at",
                    "protection_policy_version",
                    "created_by",
                    "created_at",
                ),
            ),
            _TablePlan(
                "issue_verifications",
                tables.verifications,
                "verification_id",
                (
                    "verification_id",
                    "issue_id",
                    "verification_reference_id",
                    "execution_id",
                    "score_id",
                    "scope_type",
                    "scope_id",
                    "outcome",
                    "completed_at",
                    "recorded_by",
                    "recorded_at",
                ),
            ),
            _TablePlan(
                "issue_relationships",
                tables.relationships,
                "relationship_id",
                (
                    "relationship_id",
                    "predecessor_issue_id",
                    "successor_issue_id",
                    "relationship_type",
                    "created_at",
                ),
            ),
            _TablePlan(
                "audit_outbox",
                audit_outbox_table(schema),
                "event_id",
                (
                    "event_id",
                    "prepared_event",
                    "policy_version",
                    "status",
                    "attempt_count",
                    "last_error_code",
                    "created_at",
                    "published_at",
                ),
            ),
        )

    def migrate(self, legacy_database: str | Path) -> IssueMigrationReport:
        source = Path(legacy_database).expanduser().resolve(strict=True)
        if not source.is_file():
            raise IssueMigrationError("Legacy issue kaynağı normal bir dosya olmalıdır.")
        source_hash_before = _file_sha256(source)
        rows_by_table = self._read_source(source)

        with transactional_session(self._session_factory) as session:
            reports = tuple(
                self._migrate_table(session, plan, rows_by_table[plan.name]) for plan in self._plans
            )
            foreign_key_violations = self._foreign_key_violations(session)
            if foreign_key_violations:
                raise IssueMigrationError("PostgreSQL issue foreign-key doğrulaması başarısız.")
            source_hash_after = _file_sha256(source)
            if source_hash_before != source_hash_after:
                raise IssueMigrationError("Salt okunur legacy issue kaynağı değişti.")

        return IssueMigrationReport(
            tables=reports,
            foreign_key_violations=foreign_key_violations,
            source_sha256_before=source_hash_before,
            source_sha256_after=source_hash_after,
        )

    def _read_source(self, source: Path) -> dict[str, list[dict[str, object]]]:
        uri = f"file:{quote(str(source), safe='/')}?mode=ro"
        try:
            with sqlite3.connect(uri, uri=True) as connection:
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA query_only = ON")
                rows = {plan.name: self._read_table(connection, plan) for plan in self._plans}
        except sqlite3.Error as exc:
            raise IssueMigrationError("Legacy issue kaynağı güvenli biçimde okunamadı.") from exc
        return rows

    def _read_table(
        self,
        connection: sqlite3.Connection,
        plan: _TablePlan,
    ) -> list[dict[str, object]]:
        source_columns = tuple(column for column in plan.columns if column != "version")
        quoted = ", ".join(f'"{column}"' for column in source_columns)
        try:
            raw_rows = connection.execute(
                f'SELECT {quoted} FROM "{plan.name}" ORDER BY "{plan.key}"'
            ).fetchall()
        except sqlite3.Error as exc:
            raise IssueMigrationError(f"Legacy {plan.name} tablosu eksik veya geçersiz.") from exc

        rows: list[dict[str, object]] = []
        for raw in raw_rows:
            row = {column: raw[column] for column in source_columns}
            if plan.name == "data_quality_issues":
                row["version"] = 1
            if plan.name == "audit_outbox":
                if row["status"] != "PENDING":
                    continue
                prepared = _json_document(row["prepared_event"])
                if prepared.get("object_type") != _ISSUE_OBJECT_TYPE:
                    continue
                row["prepared_event"] = prepared
            rows.append(_coerce_datetimes(plan.table, row))
        return rows

    def _migrate_table(
        self,
        session: Session,
        plan: _TablePlan,
        source_rows: list[dict[str, object]],
    ) -> MigratedTable:
        inserted = 0
        for chunk in _chunks(source_rows, _CHUNK_SIZE):
            inserted += len(
                session.execute(
                    postgresql_insert(plan.table)
                    .values(chunk)
                    .on_conflict_do_nothing()
                    .returning(plan.table.c[plan.key])
                )
                .scalars()
                .all()
            )

        target_rows = self._target_rows(session, plan, source_rows)
        source_hash = _rows_hash(source_rows, plan.key, plan.columns)
        target_hash = _rows_hash(target_rows, plan.key, plan.columns)
        if len(target_rows) != len(source_rows) or target_hash != source_hash:
            raise IssueMigrationError(f"{plan.name} sayaç veya hash doğrulaması başarısız.")
        return MigratedTable(
            table_name=plan.name,
            source_count=len(source_rows),
            inserted_count=inserted,
            source_hash=source_hash,
            target_hash=target_hash,
        )

    @staticmethod
    def _target_rows(
        session: Session,
        plan: _TablePlan,
        source_rows: Sequence[Mapping[str, object]],
    ) -> list[dict[str, object]]:
        keys = [row[plan.key] for row in source_rows]
        rows: list[dict[str, object]] = []
        for chunk in _chunks(keys, _CHUNK_SIZE):
            selected = (
                session.execute(
                    select(*(plan.table.c[column] for column in plan.columns)).where(
                        plan.table.c[plan.key].in_(chunk)
                    )
                )
                .mappings()
                .all()
            )
            rows.extend(dict(row) for row in selected)
        return rows

    def _foreign_key_violations(self, session: Session) -> int:
        tables = self._plans
        issues = tables[0].table
        history, resolutions, verifications, relationships = (
            tables[1].table,
            tables[2].table,
            tables[3].table,
            tables[4].table,
        )
        checks = (
            select(func.count())
            .select_from(history.outerjoin(issues, history.c.issue_id == issues.c.issue_id))
            .where(issues.c.issue_id.is_(None)),
            select(func.count())
            .select_from(resolutions.outerjoin(issues, resolutions.c.issue_id == issues.c.issue_id))
            .where(issues.c.issue_id.is_(None)),
            select(func.count())
            .select_from(
                verifications.outerjoin(issues, verifications.c.issue_id == issues.c.issue_id)
            )
            .where(issues.c.issue_id.is_(None)),
            select(func.count())
            .select_from(
                relationships.outerjoin(
                    issues,
                    relationships.c.predecessor_issue_id == issues.c.issue_id,
                )
            )
            .where(issues.c.issue_id.is_(None)),
            select(func.count())
            .select_from(
                relationships.outerjoin(
                    issues,
                    relationships.c.successor_issue_id == issues.c.issue_id,
                )
            )
            .where(issues.c.issue_id.is_(None)),
        )
        return sum(int(session.scalar(statement) or 0) for statement in checks)


def _coerce_datetimes(table: Table, row: dict[str, object]) -> dict[str, object]:
    converted = dict(row)
    for column in table.columns:
        value = converted.get(column.name)
        if value is not None and isinstance(column.type.python_type, type):
            if column.type.python_type is datetime and isinstance(value, str):
                converted[column.name] = datetime.fromisoformat(value)
    return converted


def _json_document(value: object) -> dict[str, object]:
    if not isinstance(value, str):
        raise IssueMigrationError("Legacy audit olayı JSON metni olmalıdır.")
    try:
        document = json.loads(value)
    except json.JSONDecodeError as exc:
        raise IssueMigrationError("Legacy audit olayı geçerli JSON değildir.") from exc
    if not isinstance(document, dict):
        raise IssueMigrationError("Legacy audit olayı JSON nesnesi olmalıdır.")
    return document


def _rows_hash(
    rows: Iterable[Mapping[str, object]],
    key: str,
    columns: Sequence[str],
) -> str:
    canonical = [
        {column: _canonical_value(row[column]) for column in columns}
        for row in sorted(rows, key=lambda item: str(item[key]))
    ]
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_value(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value


def _chunks(values: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
