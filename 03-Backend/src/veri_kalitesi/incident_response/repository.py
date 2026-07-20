"""Append-only SQLite persistence for incident response records."""

from __future__ import annotations

import sqlite3
from threading import RLock

from veri_kalitesi.audit import PreparedAuditEvent, SQLiteTransactionalAudit
from veri_kalitesi.incident_response.errors import (
    IncidentConflictError,
    IncidentNotFoundError,
)
from veri_kalitesi.incident_response.models import (
    BreachAssessmentStatus,
    BreachNotificationDecision,
    BreachNotificationDecisionRecord,
    BreachOrigin,
    IncidentScopeType,
    IncidentSeverity,
    IncidentSource,
    IncidentTimelineEntry,
    IncidentTimelineEventType,
    PersonalDataBreachSuspicion,
    PersonalDataCategory,
    SecurityIncident,
)


class SQLiteIncidentResponseRepository:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS security_incidents (
                incident_id TEXT PRIMARY KEY,
                source_event_reference_id TEXT NOT NULL UNIQUE,
                detected_at TEXT NOT NULL,
                source TEXT NOT NULL,
                severity TEXT NOT NULL,
                event_code TEXT NOT NULL,
                scope_type TEXT NOT NULL,
                scope_id TEXT,
                evidence_reference_id TEXT NOT NULL,
                recorded_by TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS personal_data_breach_suspicions (
                breach_id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL UNIQUE,
                learned_at TEXT NOT NULL,
                evaluation_deadline_at TEXT NOT NULL,
                origin TEXT NOT NULL,
                data_categories TEXT NOT NULL,
                affected_scope_code TEXT NOT NULL,
                containment_action_code TEXT NOT NULL,
                evidence_reference_id TEXT NOT NULL,
                processor_notification_evidence_id TEXT,
                status TEXT NOT NULL,
                recorded_by TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (incident_id) REFERENCES security_incidents(incident_id)
            );

            CREATE TABLE IF NOT EXISTS breach_notification_decisions (
                sequence_no INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT NOT NULL UNIQUE,
                breach_id TEXT NOT NULL UNIQUE,
                decision TEXT NOT NULL,
                decided_at TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                evidence_reference_id TEXT NOT NULL,
                decided_by TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                external_notification_dispatched INTEGER NOT NULL CHECK (
                    external_notification_dispatched = 0
                ),
                FOREIGN KEY (breach_id) REFERENCES personal_data_breach_suspicions(breach_id)
            );

            CREATE TABLE IF NOT EXISTS incident_timeline (
                sequence_no INTEGER PRIMARY KEY AUTOINCREMENT,
                timeline_id TEXT NOT NULL UNIQUE,
                incident_id TEXT NOT NULL,
                breach_id TEXT,
                event_type TEXT NOT NULL,
                event_at TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                evidence_reference_id TEXT NOT NULL,
                FOREIGN KEY (incident_id) REFERENCES security_incidents(incident_id),
                FOREIGN KEY (breach_id) REFERENCES personal_data_breach_suspicions(breach_id)
            );

            CREATE INDEX IF NOT EXISTS idx_incident_timeline_incident_sequence
            ON incident_timeline(incident_id, sequence_no);
            """
        )
        self.connection.commit()

    def create_incident(
        self,
        incident: SecurityIncident,
        timeline: IncidentTimelineEntry,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> None:
        self._require_shared_audit_transaction(audit_outbox)
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """
                    INSERT INTO security_incidents (
                        incident_id, source_event_reference_id, detected_at, source,
                        severity, event_code, scope_type, scope_id, evidence_reference_id,
                        recorded_by, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        incident.incident_id,
                        incident.source_event_reference_id,
                        incident.detected_at.isoformat(),
                        incident.source.value,
                        incident.severity.value,
                        incident.event_code,
                        incident.scope_type.value,
                        incident.scope_id,
                        incident.evidence_reference_id,
                        incident.recorded_by,
                        incident.recorded_at.isoformat(),
                    ),
                )
                self._insert_timeline(timeline)
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise IncidentConflictError("Security incident already exists.") from exc

    def create_breach_suspicion(
        self,
        breach: PersonalDataBreachSuspicion,
        timeline: tuple[IncidentTimelineEntry, ...],
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> None:
        self._require_shared_audit_transaction(audit_outbox)
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """
                    INSERT INTO personal_data_breach_suspicions (
                        breach_id, incident_id, learned_at, evaluation_deadline_at,
                        origin, data_categories, affected_scope_code,
                        containment_action_code, evidence_reference_id,
                        processor_notification_evidence_id, status, recorded_by, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        breach.breach_id,
                        breach.incident_id,
                        breach.learned_at.isoformat(),
                        breach.evaluation_deadline_at.isoformat(),
                        breach.origin.value,
                        ",".join(sorted(item.value for item in breach.data_categories)),
                        breach.affected_scope_code,
                        breach.containment_action_code,
                        breach.evidence_reference_id,
                        breach.processor_notification_evidence_id,
                        breach.status.value,
                        breach.recorded_by,
                        breach.recorded_at.isoformat(),
                    ),
                )
                for entry in timeline:
                    self._insert_timeline(entry)
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise IncidentConflictError("Breach suspicion already exists.") from exc

    def add_breach_decision(
        self,
        decision: BreachNotificationDecisionRecord,
        timeline: IncidentTimelineEntry,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> None:
        self._require_shared_audit_transaction(audit_outbox)
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """
                    INSERT INTO breach_notification_decisions (
                        decision_id, breach_id, decision, decided_at, reason_code,
                        evidence_reference_id, decided_by, recorded_at,
                        external_notification_dispatched
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        decision.decision_id,
                        decision.breach_id,
                        decision.decision.value,
                        decision.decided_at.isoformat(),
                        decision.reason_code,
                        decision.evidence_reference_id,
                        decision.decided_by,
                        decision.recorded_at.isoformat(),
                    ),
                )
                self._insert_timeline(timeline)
                audit_outbox.stage(audit_event)
        except sqlite3.IntegrityError as exc:
            raise IncidentConflictError("Breach decision already exists.") from exc

    def record_audit(
        self,
        audit_event: PreparedAuditEvent,
        audit_outbox: SQLiteTransactionalAudit,
    ) -> None:
        self._require_shared_audit_transaction(audit_outbox)
        with self._lock, self.connection:
            audit_outbox.stage(audit_event)

    def get_incident(self, incident_id: str) -> SecurityIncident:
        row = self.connection.execute(
            "SELECT * FROM security_incidents WHERE incident_id = ?", (incident_id,)
        ).fetchone()
        if row is None:
            raise IncidentNotFoundError("Security incident was not found.")
        return _incident_from_row(row)

    def get_breach_suspicion(self, breach_id: str) -> PersonalDataBreachSuspicion:
        row = self.connection.execute(
            """
            SELECT breach.*,
                   EXISTS (
                       SELECT 1 FROM breach_notification_decisions decision
                       WHERE decision.breach_id = breach.breach_id
                   ) AS decision_exists
            FROM personal_data_breach_suspicions breach
            WHERE breach.breach_id = ?
            """,
            (breach_id,),
        ).fetchone()
        if row is None:
            raise IncidentNotFoundError("Breach suspicion was not found.")
        return _breach_from_row(row)

    def get_breach_decision(self, breach_id: str) -> BreachNotificationDecisionRecord | None:
        row = self.connection.execute(
            "SELECT * FROM breach_notification_decisions WHERE breach_id = ?", (breach_id,)
        ).fetchone()
        if row is None:
            return None
        return BreachNotificationDecisionRecord(
            decision_id=row["decision_id"],
            breach_id=row["breach_id"],
            decision=BreachNotificationDecision(row["decision"]),
            decided_at=_datetime(row["decided_at"]),
            reason_code=row["reason_code"],
            evidence_reference_id=row["evidence_reference_id"],
            decided_by=row["decided_by"],
            recorded_at=_datetime(row["recorded_at"]),
            external_notification_dispatched=bool(row["external_notification_dispatched"]),
        )

    def list_timeline(self, incident_id: str) -> tuple[IncidentTimelineEntry, ...]:
        rows = self.connection.execute(
            """
            SELECT * FROM incident_timeline
            WHERE incident_id = ? ORDER BY sequence_no
            """,
            (incident_id,),
        ).fetchall()
        return tuple(
            IncidentTimelineEntry(
                timeline_id=row["timeline_id"],
                incident_id=row["incident_id"],
                breach_id=row["breach_id"],
                event_type=IncidentTimelineEventType(row["event_type"]),
                event_at=_datetime(row["event_at"]),
                actor_id=row["actor_id"],
                reason_code=row["reason_code"],
                evidence_reference_id=row["evidence_reference_id"],
            )
            for row in rows
        )

    def _insert_timeline(self, entry: IncidentTimelineEntry) -> None:
        self.connection.execute(
            """
            INSERT INTO incident_timeline (
                timeline_id, incident_id, breach_id, event_type, event_at,
                actor_id, reason_code, evidence_reference_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.timeline_id,
                entry.incident_id,
                entry.breach_id,
                entry.event_type.value,
                entry.event_at.isoformat(),
                entry.actor_id,
                entry.reason_code,
                entry.evidence_reference_id,
            ),
        )

    def _require_shared_audit_transaction(self, audit_outbox: SQLiteTransactionalAudit) -> None:
        if audit_outbox.connection is not self.connection:
            raise ValueError("Incident repository and audit outbox must share a connection.")


def _incident_from_row(row: sqlite3.Row) -> SecurityIncident:
    return SecurityIncident(
        incident_id=row["incident_id"],
        source_event_reference_id=row["source_event_reference_id"],
        detected_at=_datetime(row["detected_at"]),
        source=IncidentSource(row["source"]),
        severity=IncidentSeverity(row["severity"]),
        event_code=row["event_code"],
        scope_type=IncidentScopeType(row["scope_type"]),
        scope_id=row["scope_id"],
        evidence_reference_id=row["evidence_reference_id"],
        recorded_by=row["recorded_by"],
        recorded_at=_datetime(row["recorded_at"]),
    )


def _breach_from_row(row: sqlite3.Row) -> PersonalDataBreachSuspicion:
    return PersonalDataBreachSuspicion(
        breach_id=row["breach_id"],
        incident_id=row["incident_id"],
        learned_at=_datetime(row["learned_at"]),
        evaluation_deadline_at=_datetime(row["evaluation_deadline_at"]),
        origin=BreachOrigin(row["origin"]),
        data_categories=frozenset(
            PersonalDataCategory(value) for value in row["data_categories"].split(",")
        ),
        affected_scope_code=row["affected_scope_code"],
        containment_action_code=row["containment_action_code"],
        evidence_reference_id=row["evidence_reference_id"],
        processor_notification_evidence_id=row["processor_notification_evidence_id"],
        status=(
            BreachAssessmentStatus.NOTIFICATION_DECIDED
            if "decision_exists" in row.keys() and row["decision_exists"]
            else BreachAssessmentStatus(row["status"])
        ),
        recorded_by=row["recorded_by"],
        recorded_at=_datetime(row["recorded_at"]),
    )


def _datetime(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value)
