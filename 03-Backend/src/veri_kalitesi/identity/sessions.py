"""Kalici, iptal edilebilir ve veri-minimum kullanici oturumlari."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from threading import RLock
from typing import Callable, NoReturn

from veri_kalitesi.audit import AuditEventInput, AuditResult, AuditSink
from veri_kalitesi.identity.errors import (
    ActorContextValidationError,
    SessionDeniedError,
    SessionTechnicalError,
    SessionUnavailableError,
)
from veri_kalitesi.identity.models import ActorContext, ActorType, _is_trusted_context
from veri_kalitesi.identity.service import ActorContextIssuer


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


@dataclass(frozen=True)
class SessionPolicy:
    version: str
    idle_timeout: timedelta
    absolute_timeout: timedelta

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ActorContextValidationError("Session policy version is required.")
        if not timedelta(0) < self.idle_timeout <= timedelta(minutes=30):
            raise ActorContextValidationError(
                "Session idle timeout must be positive and at most thirty minutes."
            )
        if self.absolute_timeout <= self.idle_timeout:
            raise ActorContextValidationError(
                "Session absolute timeout must exceed the idle timeout."
            )


@dataclass(frozen=True)
class SessionGrant:
    context: ActorContext
    credential: bytes = field(repr=False)


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    credential_digest: str
    actor_id: str
    actor_type: ActorType
    authentication_source: str
    roles: frozenset[str]
    permitted_source_ids: frozenset[str]
    permitted_dataset_ids: frozenset[str]
    can_view_enterprise: bool
    privileged: bool
    issued_at: datetime
    expires_at: datetime
    last_activity_at: datetime
    status: SessionStatus
    mapping_policy_version: str
    session_policy_version: str
    revoked_at: datetime | None = None
    revocation_reason: str | None = None


class SQLiteSessionRepository:
    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS identity_sessions (
                session_id TEXT PRIMARY KEY,
                credential_digest TEXT NOT NULL UNIQUE,
                actor_id TEXT NOT NULL,
                actor_type TEXT NOT NULL,
                authentication_source TEXT NOT NULL,
                roles TEXT NOT NULL,
                permitted_source_ids TEXT NOT NULL,
                permitted_dataset_ids TEXT NOT NULL,
                can_view_enterprise INTEGER NOT NULL,
                privileged INTEGER NOT NULL,
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_activity_at TEXT NOT NULL,
                status TEXT NOT NULL,
                mapping_policy_version TEXT NOT NULL,
                session_policy_version TEXT NOT NULL,
                revoked_at TEXT,
                revocation_reason TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_identity_sessions_actor_status
            ON identity_sessions(actor_id, status);

            CREATE INDEX IF NOT EXISTS idx_identity_sessions_expiry
            ON identity_sessions(status, expires_at, last_activity_at);
            """
        )
        self.connection.commit()

    def create(self, record: SessionRecord) -> None:
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """
                    INSERT INTO identity_sessions (
                        session_id, credential_digest, actor_id, actor_type,
                        authentication_source, roles, permitted_source_ids,
                        permitted_dataset_ids, can_view_enterprise, privileged,
                        issued_at, expires_at, last_activity_at, status,
                        mapping_policy_version, session_policy_version,
                        revoked_at, revocation_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _record_values(record),
                )
        except sqlite3.Error as exc:
            raise SessionTechnicalError() from exc

    def find_by_credential_digest(self, credential_digest: str) -> SessionRecord | None:
        try:
            with self._lock:
                row = self.connection.execute(
                    "SELECT * FROM identity_sessions WHERE credential_digest = ?",
                    (credential_digest,),
                ).fetchone()
            return _row_to_record(row) if row is not None else None
        except (sqlite3.Error, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise SessionTechnicalError() from exc

    def touch(self, session_id: str, occurred_at: datetime) -> SessionRecord:
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """
                    UPDATE identity_sessions
                    SET last_activity_at = ?
                    WHERE session_id = ? AND status = ?
                    """,
                    (occurred_at.isoformat(), session_id, SessionStatus.ACTIVE.value),
                )
                row = self.connection.execute(
                    "SELECT * FROM identity_sessions WHERE session_id = ?", (session_id,)
                ).fetchone()
            if row is None:
                raise SessionTechnicalError()
            return _row_to_record(row)
        except sqlite3.Error as exc:
            raise SessionTechnicalError() from exc

    def transition(
        self,
        session_id: str,
        status: SessionStatus,
        occurred_at: datetime,
        reason: str,
    ) -> SessionRecord:
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """
                    UPDATE identity_sessions
                    SET status = ?, revoked_at = ?, revocation_reason = ?
                    WHERE session_id = ? AND status = ?
                    """,
                    (
                        status.value,
                        occurred_at.isoformat(),
                        reason,
                        session_id,
                        SessionStatus.ACTIVE.value,
                    ),
                )
                row = self.connection.execute(
                    "SELECT * FROM identity_sessions WHERE session_id = ?", (session_id,)
                ).fetchone()
            if row is None:
                raise SessionTechnicalError()
            return _row_to_record(row)
        except sqlite3.Error as exc:
            raise SessionTechnicalError() from exc


class SessionService:
    def __init__(
        self,
        repository: SQLiteSessionRepository,
        policy: SessionPolicy,
        audit_sink: AuditSink,
        *,
        issuer: ActorContextIssuer | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        credential_generator: Callable[[int], bytes] = secrets.token_bytes,
        session_id_generator: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        self.repository = repository
        self.policy = policy
        self.audit_sink = audit_sink
        self.issuer = issuer or ActorContextIssuer()
        self.clock = clock
        self.credential_generator = credential_generator
        self.session_id_generator = session_id_generator

    def open_authenticated_session(
        self,
        *,
        authenticated_context: ActorContext,
        correlation_id: str,
    ) -> SessionGrant:
        now = self._now()
        if not _is_trusted_context(authenticated_context):
            raise ActorContextValidationError("Trusted authentication context is required.")
        if authenticated_context.correlation_id != correlation_id:
            raise ActorContextValidationError(
                "Authentication and session correlation IDs must match."
            )
        if authenticated_context.issued_at > now or authenticated_context.expires_at <= now:
            raise ActorContextValidationError("Authentication context is not currently valid.")
        if (
            authenticated_context.actor_type is not ActorType.USER
            or authenticated_context.privileged
        ):
            raise ActorContextValidationError("User session requires a non-privileged user.")
        credential = self.credential_generator(32)
        session_id = self.session_id_generator()
        if not isinstance(credential, bytes) or len(credential) < 32:
            raise ActorContextValidationError("Session credential must contain 32 bytes.")
        if not session_id.strip():
            raise ActorContextValidationError("Session ID is required.")
        expires_at = now + self.policy.absolute_timeout
        context = self.issuer.issue(
            actor_id=authenticated_context.actor_id,
            actor_type=authenticated_context.actor_type,
            authentication_source=authenticated_context.authentication_source,
            session_id=session_id,
            roles=authenticated_context.roles,
            permitted_source_ids=authenticated_context.permitted_source_ids,
            permitted_dataset_ids=authenticated_context.permitted_dataset_ids,
            can_view_enterprise=authenticated_context.can_view_enterprise,
            privileged=authenticated_context.privileged,
            issued_at=now,
            expires_at=expires_at,
            policy_version=authenticated_context.policy_version,
            correlation_id=correlation_id,
        )
        record = _context_to_record(context, credential, self.policy.version, now)
        self._create(record, correlation_id, now)
        try:
            self._record(record, correlation_id, AuditResult.SUCCESS, "SESSION_CREATED", now)
        except SessionUnavailableError:
            self._transition(
                session_id,
                SessionStatus.REVOKED,
                now,
                "SESSION_CREATION_AUDIT_FAILED",
                correlation_id,
            )
            raise
        return SessionGrant(context=context, credential=credential)

    def validate(self, credential: bytes, correlation_id: str) -> ActorContext:
        now = self._now()
        self._validate_request(credential, correlation_id)
        record = self._find(credential, correlation_id, now)
        if record is None:
            self._deny(None, correlation_id, "SESSION_NOT_FOUND", now)
        if record.status is not SessionStatus.ACTIVE:
            self._deny(record, correlation_id, "SESSION_NOT_ACTIVE", now)
        if record.expires_at <= now:
            record = self._transition(
                record.session_id,
                SessionStatus.EXPIRED,
                now,
                "SESSION_ABSOLUTE_TIMEOUT",
                correlation_id,
            )
            self._deny(record, correlation_id, "SESSION_ABSOLUTE_TIMEOUT", now)
        if record.last_activity_at + self.policy.idle_timeout <= now:
            record = self._transition(
                record.session_id,
                SessionStatus.EXPIRED,
                now,
                "SESSION_IDLE_TIMEOUT",
                correlation_id,
            )
            self._deny(record, correlation_id, "SESSION_IDLE_TIMEOUT", now)
        try:
            record = self.repository.touch(record.session_id, now)
        except SessionTechnicalError:
            self._unavailable(correlation_id, now)
        context = self._issue_context(record, correlation_id)
        self._record(record, correlation_id, AuditResult.SUCCESS, "SESSION_VALIDATED", now)
        return context

    def logout(self, credential: bytes, correlation_id: str) -> None:
        now = self._now()
        self._validate_request(credential, correlation_id)
        record = self._find(credential, correlation_id, now)
        if record is None:
            self._deny(None, correlation_id, "SESSION_NOT_FOUND", now)
        if record.status is SessionStatus.ACTIVE:
            record = self._transition(
                record.session_id,
                SessionStatus.REVOKED,
                now,
                "USER_LOGOUT",
                correlation_id,
            )
            reason_code = "SESSION_REVOKED"
        else:
            reason_code = "SESSION_ALREADY_INACTIVE"
        self._record(record, correlation_id, AuditResult.SUCCESS, reason_code, now)

    def _issue_context(self, record: SessionRecord, correlation_id: str) -> ActorContext:
        return self.issuer.issue(
            actor_id=record.actor_id,
            actor_type=record.actor_type,
            authentication_source=record.authentication_source,
            session_id=record.session_id,
            roles=record.roles,
            permitted_source_ids=record.permitted_source_ids,
            permitted_dataset_ids=record.permitted_dataset_ids,
            can_view_enterprise=record.can_view_enterprise,
            privileged=record.privileged,
            issued_at=record.issued_at,
            expires_at=record.expires_at,
            policy_version=record.mapping_policy_version,
            correlation_id=correlation_id,
        )

    def _deny(
        self,
        record: SessionRecord | None,
        correlation_id: str,
        reason_code: str,
        now: datetime,
    ) -> NoReturn:
        self._record(record, correlation_id, AuditResult.DENIED, reason_code, now)
        raise SessionDeniedError(reason_code, correlation_id)

    def _record(
        self,
        record: SessionRecord | None,
        correlation_id: str,
        result: AuditResult,
        reason_code: str,
        now: datetime,
    ) -> None:
        event = AuditEventInput(
            actor_id=record.actor_id if record is not None else "UNKNOWN",
            actor_type=record.actor_type.value if record is not None else None,
            correlation_id=correlation_id,
            action="IDENTITY_SESSION",
            object_type="IdentitySession",
            object_id=None,
            result=result,
            reason_code=reason_code,
            old_values={},
            new_values={
                "session_policy_version": self.policy.version,
                "status": record.status.value if record is not None else "UNKNOWN",
                "reason_code": reason_code,
            },
            occurred_at=now,
            session_id=record.session_id if record is not None else None,
        )
        try:
            self.audit_sink.append(event)
        except Exception as exc:
            raise SessionUnavailableError(correlation_id) from exc

    def _validate_request(self, credential: bytes, correlation_id: str) -> None:
        if not isinstance(credential, bytes) or not credential or not correlation_id.strip():
            raise ActorContextValidationError("Session credential and correlation ID are required.")

    def _create(self, record: SessionRecord, correlation_id: str, now: datetime) -> None:
        try:
            self.repository.create(record)
        except SessionTechnicalError:
            self._unavailable(correlation_id, now)

    def _find(self, credential: bytes, correlation_id: str, now: datetime) -> SessionRecord | None:
        try:
            return self.repository.find_by_credential_digest(_credential_digest(credential))
        except SessionTechnicalError:
            self._unavailable(correlation_id, now)

    def _transition(
        self,
        session_id: str,
        status: SessionStatus,
        now: datetime,
        reason: str,
        correlation_id: str,
    ) -> SessionRecord:
        try:
            return self.repository.transition(session_id, status, now, reason)
        except SessionTechnicalError:
            self._unavailable(correlation_id, now)

    def _unavailable(self, correlation_id: str, now: datetime) -> NoReturn:
        self._record(
            None,
            correlation_id,
            AuditResult.FAILURE,
            "SESSION_TECHNICAL_ERROR",
            now,
        )
        raise SessionUnavailableError(correlation_id)

    def _now(self) -> datetime:
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ActorContextValidationError("Session clock must be timezone-aware.")
        return now


def _context_to_record(
    context: ActorContext,
    credential: bytes,
    session_policy_version: str,
    now: datetime,
) -> SessionRecord:
    return SessionRecord(
        session_id=context.session_id,
        credential_digest=_credential_digest(credential),
        actor_id=context.actor_id,
        actor_type=context.actor_type,
        authentication_source=context.authentication_source,
        roles=context.roles,
        permitted_source_ids=context.permitted_source_ids,
        permitted_dataset_ids=context.permitted_dataset_ids,
        can_view_enterprise=context.can_view_enterprise,
        privileged=context.privileged,
        issued_at=context.issued_at,
        expires_at=context.expires_at,
        last_activity_at=now,
        status=SessionStatus.ACTIVE,
        mapping_policy_version=context.policy_version,
        session_policy_version=session_policy_version,
    )


def _credential_digest(credential: bytes) -> str:
    return hashlib.sha256(credential).hexdigest()


def _record_values(record: SessionRecord) -> tuple[object, ...]:
    return (
        record.session_id,
        record.credential_digest,
        record.actor_id,
        record.actor_type.value,
        record.authentication_source,
        json.dumps(sorted(record.roles)),
        json.dumps(sorted(record.permitted_source_ids)),
        json.dumps(sorted(record.permitted_dataset_ids)),
        int(record.can_view_enterprise),
        int(record.privileged),
        record.issued_at.isoformat(),
        record.expires_at.isoformat(),
        record.last_activity_at.isoformat(),
        record.status.value,
        record.mapping_policy_version,
        record.session_policy_version,
        record.revoked_at.isoformat() if record.revoked_at else None,
        record.revocation_reason,
    )


def _row_to_record(row: sqlite3.Row) -> SessionRecord:
    return SessionRecord(
        session_id=row["session_id"],
        credential_digest=row["credential_digest"],
        actor_id=row["actor_id"],
        actor_type=ActorType(row["actor_type"]),
        authentication_source=row["authentication_source"],
        roles=frozenset(json.loads(row["roles"])),
        permitted_source_ids=frozenset(json.loads(row["permitted_source_ids"])),
        permitted_dataset_ids=frozenset(json.loads(row["permitted_dataset_ids"])),
        can_view_enterprise=bool(row["can_view_enterprise"]),
        privileged=bool(row["privileged"]),
        issued_at=datetime.fromisoformat(row["issued_at"]),
        expires_at=datetime.fromisoformat(row["expires_at"]),
        last_activity_at=datetime.fromisoformat(row["last_activity_at"]),
        status=SessionStatus(row["status"]),
        mapping_policy_version=row["mapping_policy_version"],
        session_policy_version=row["session_policy_version"],
        revoked_at=(datetime.fromisoformat(row["revoked_at"]) if row["revoked_at"] else None),
        revocation_reason=row["revocation_reason"],
    )
