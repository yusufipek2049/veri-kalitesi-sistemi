"""Legacy SQLite audit kayitlarini merkezi zincire guvenli aktarma."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from veri_kalitesi.audit.errors import AuditMigrationTechnicalError, AuditValidationError
from veri_kalitesi.audit.models import AuditEventInput, AuditResult
from veri_kalitesi.audit.redaction import AuditRedactor
from veri_kalitesi.audit.repository import SQLiteAuditRepository


_REQUIRED_COLUMNS = frozenset(
    {
        "audit_id",
        "actor_id",
        "action",
        "object_type",
        "object_id",
        "result",
        "old_values",
        "new_values",
        "created_at",
    }
)


@dataclass(frozen=True)
class LegacyAuditInventory:
    table_exists: bool
    columns: tuple[str, ...]
    record_count: int


@dataclass(frozen=True)
class LegacyAuditIssue:
    record_id_digest: str | None
    code: str


@dataclass(frozen=True)
class LegacyAuditMigrationReport:
    source_id_digest: str
    total_count: int
    migrated_count: int
    duplicate_count: int
    skipped_count: int
    issues: tuple[LegacyAuditIssue, ...]


class LegacyAuditMigrator:
    def __init__(
        self,
        source_connection: sqlite3.Connection,
        repository: SQLiteAuditRepository,
        redactor: AuditRedactor,
        *,
        source_id: str,
    ) -> None:
        if not source_id.strip():
            raise ValueError("Legacy audit source_id is required.")
        self.source_connection = source_connection
        self.repository = repository
        self.redactor = redactor
        self.source_id = source_id

    def inventory(self) -> LegacyAuditInventory:
        try:
            rows = self.source_connection.execute("PRAGMA table_info(audit_records)").fetchall()
            columns = tuple(str(row[1]) for row in rows)
            if not columns:
                return LegacyAuditInventory(False, (), 0)
            count = int(
                self.source_connection.execute("SELECT COUNT(*) FROM audit_records").fetchone()[0]
            )
        except sqlite3.Error as exc:
            raise AuditMigrationTechnicalError("Legacy audit inventory could not be read.") from exc
        return LegacyAuditInventory(True, columns, count)

    def migrate(self) -> LegacyAuditMigrationReport:
        inventory = self.inventory()
        source_digest = _digest(self.source_id)
        if not inventory.table_exists or not _REQUIRED_COLUMNS.issubset(inventory.columns):
            return LegacyAuditMigrationReport(
                source_id_digest=source_digest,
                total_count=inventory.record_count,
                migrated_count=0,
                duplicate_count=0,
                skipped_count=inventory.record_count,
                issues=(LegacyAuditIssue(None, "UNSUPPORTED_LEGACY_SCHEMA"),),
            )
        try:
            rows = self.source_connection.execute(
                """
                SELECT audit_id, actor_id, action, object_type, object_id, result,
                       old_values, new_values, created_at
                FROM audit_records
                ORDER BY created_at, audit_id
                """
            ).fetchall()
        except sqlite3.Error as exc:
            raise AuditMigrationTechnicalError("Legacy audit records could not be read.") from exc

        migrated = 0
        duplicates = 0
        issues: list[LegacyAuditIssue] = []
        for row in rows:
            record_id = str(row[0])
            record_digest = _digest(record_id)
            prepared, issue_code = self._prepare_row(row)
            if prepared is None:
                issues.append(LegacyAuditIssue(record_digest, issue_code or "INVALID_LEGACY_ROW"))
                continue
            try:
                existing = self.repository.find_event(prepared.event_id)
                stored = self.repository.append(prepared)
            except AuditValidationError:
                issues.append(LegacyAuditIssue(record_digest, "EVENT_CONTENT_MISMATCH"))
                continue
            except sqlite3.Error as exc:
                raise AuditMigrationTechnicalError(
                    "Central audit repository could not accept a migrated event."
                ) from exc
            if existing is None:
                migrated += 1
            elif stored.event_id == prepared.event_id:
                duplicates += 1

        return LegacyAuditMigrationReport(
            source_id_digest=source_digest,
            total_count=len(rows),
            migrated_count=migrated,
            duplicate_count=duplicates,
            skipped_count=len(issues),
            issues=tuple(issues),
        )

    def _prepare_row(self, row: sqlite3.Row | tuple[object, ...]):
        audit_id, actor_id, action, object_type, object_id, result, old_raw, new_raw, created = row
        if str(action) not in self.redactor.policy.allowed_fields_by_action:
            return None, "UNSUPPORTED_ACTION"
        try:
            old_values = json.loads(str(old_raw))
            new_values = json.loads(str(new_raw))
            occurred_at = datetime.fromisoformat(str(created))
            parsed_result = AuditResult(str(result))
        except (ValueError, TypeError, json.JSONDecodeError):
            return None, "INVALID_LEGACY_VALUE"
        if not isinstance(old_values, dict) or not isinstance(new_values, dict):
            return None, "INVALID_LEGACY_VALUE"
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            return None, "NAIVE_EVENT_TIME"
        event_key = f"{self.source_id}:{audit_id}"
        try:
            prepared = self.redactor.prepare(
                AuditEventInput(
                    actor_id=str(actor_id),
                    actor_type="USER",
                    correlation_id=f"legacy-audit-{_digest(event_key)[:24]}",
                    action=str(action),
                    object_type=str(object_type),
                    object_id=str(object_id),
                    result=parsed_result,
                    reason_code="LEGACY_AUDIT_MIGRATED",
                    old_values=old_values,
                    new_values=new_values,
                    occurred_at=occurred_at,
                )
            )
        except AuditValidationError:
            return None, "INVALID_LEGACY_ENVELOPE"
        return replace(
            prepared,
            event_id=str(uuid5(NAMESPACE_URL, f"veri-kalitesi:audit:{event_key}")),
        ), None


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
