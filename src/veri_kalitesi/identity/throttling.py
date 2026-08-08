"""Kalici ve veri-minimum LDAP giris sinirlandirmasi."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from threading import RLock
from typing import Protocol

from veri_kalitesi.identity.errors import (
    ActorContextValidationError,
    AuthenticationThrottleTechnicalError,
)


class AuthenticationThrottleScope(str, Enum):
    USER = "USER"
    CLIENT = "CLIENT"


@dataclass(frozen=True)
class AuthenticationThrottleKeys:
    user_key: str
    client_key: str


class AuthenticationThrottleKeyProvider(Protocol):
    """Guvenilir giris sinirinda kimlikleri opak anahtarlara donusturur."""

    version: str

    def derive(self, *, principal: str, client_reference: str) -> AuthenticationThrottleKeys: ...


@dataclass(frozen=True)
class AuthenticationThrottlePolicy:
    version: str
    max_failures: int
    failure_window: timedelta
    block_duration: timedelta

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ActorContextValidationError("Throttle policy version is required.")
        if not 1 <= self.max_failures <= 5:
            raise ActorContextValidationError(
                "Throttle failure threshold must be between one and five."
            )
        if self.failure_window <= timedelta(0):
            raise ActorContextValidationError("Throttle failure window must be positive.")
        if self.block_duration < timedelta(minutes=15):
            raise ActorContextValidationError(
                "Throttle block duration must be at least fifteen minutes."
            )


@dataclass(frozen=True)
class AuthenticationThrottleDecision:
    blocked: bool
    failure_count: int
    blocked_scope_count: int


class SQLiteAuthenticationThrottleRepository:
    """Opak kullanici ve istemci anahtarlarini ayri sayaclarda saklar."""

    def __init__(self, database: str = ":memory:") -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS authentication_throttle_states (
                scope_type TEXT NOT NULL,
                scope_key TEXT NOT NULL,
                failure_count INTEGER NOT NULL CHECK (failure_count >= 0),
                window_started_at TEXT NOT NULL,
                blocked_until TEXT,
                policy_version TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (scope_type, scope_key)
            );

            CREATE INDEX IF NOT EXISTS idx_authentication_throttle_blocked_until
            ON authentication_throttle_states(blocked_until);
            """
        )
        self.connection.commit()

    def evaluate(
        self,
        keys: AuthenticationThrottleKeys,
        policy: AuthenticationThrottlePolicy,
        now: datetime,
    ) -> AuthenticationThrottleDecision:
        _validate_inputs(keys, now)
        try:
            with self._lock, self.connection:
                states = [
                    self._read_active(scope, key, policy, now) for scope, key in _scoped_keys(keys)
                ]
            return _decision(states, now)
        except sqlite3.Error as exc:
            raise AuthenticationThrottleTechnicalError() from exc

    def record_failure(
        self,
        keys: AuthenticationThrottleKeys,
        policy: AuthenticationThrottlePolicy,
        now: datetime,
    ) -> AuthenticationThrottleDecision:
        _validate_inputs(keys, now)
        try:
            with self._lock, self.connection:
                states = [
                    self._increment(scope, key, policy, now) for scope, key in _scoped_keys(keys)
                ]
            return _decision(states, now)
        except sqlite3.Error as exc:
            raise AuthenticationThrottleTechnicalError() from exc

    def reset(
        self,
        keys: AuthenticationThrottleKeys,
        now: datetime,
    ) -> None:
        _validate_inputs(keys, now)
        try:
            with self._lock, self.connection:
                self.connection.executemany(
                    """
                    DELETE FROM authentication_throttle_states
                    WHERE scope_type = ? AND scope_key = ?
                    """,
                    [(scope.value, key) for scope, key in _scoped_keys(keys)],
                )
        except sqlite3.Error as exc:
            raise AuthenticationThrottleTechnicalError() from exc

    def _read_active(
        self,
        scope: AuthenticationThrottleScope,
        key: str,
        policy: AuthenticationThrottlePolicy,
        now: datetime,
    ) -> tuple[int, datetime | None]:
        row = self.connection.execute(
            """
            SELECT failure_count, window_started_at, blocked_until
            FROM authentication_throttle_states
            WHERE scope_type = ? AND scope_key = ?
            """,
            (scope.value, key),
        ).fetchone()
        if row is None:
            return 0, None
        window_started_at = datetime.fromisoformat(row["window_started_at"])
        blocked_until = _optional_datetime(row["blocked_until"])
        if (blocked_until is None or blocked_until <= now) and (
            now - window_started_at >= policy.failure_window
        ):
            self.connection.execute(
                """
                DELETE FROM authentication_throttle_states
                WHERE scope_type = ? AND scope_key = ?
                """,
                (scope.value, key),
            )
            return 0, None
        return int(row["failure_count"]), blocked_until

    def _increment(
        self,
        scope: AuthenticationThrottleScope,
        key: str,
        policy: AuthenticationThrottlePolicy,
        now: datetime,
    ) -> tuple[int, datetime | None]:
        failure_count, blocked_until = self._read_active(scope, key, policy, now)
        if blocked_until is not None and blocked_until > now:
            return failure_count, blocked_until
        if failure_count == 0:
            window_started_at = now
        else:
            row = self.connection.execute(
                """
                SELECT window_started_at
                FROM authentication_throttle_states
                WHERE scope_type = ? AND scope_key = ?
                """,
                (scope.value, key),
            ).fetchone()
            window_started_at = datetime.fromisoformat(row["window_started_at"])
        failure_count += 1
        blocked_until = (
            now + policy.block_duration if failure_count >= policy.max_failures else None
        )
        self.connection.execute(
            """
            INSERT INTO authentication_throttle_states (
                scope_type, scope_key, failure_count, window_started_at,
                blocked_until, policy_version, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scope_type, scope_key) DO UPDATE SET
                failure_count = excluded.failure_count,
                window_started_at = excluded.window_started_at,
                blocked_until = excluded.blocked_until,
                policy_version = excluded.policy_version,
                updated_at = excluded.updated_at
            """,
            (
                scope.value,
                key,
                failure_count,
                window_started_at.isoformat(),
                blocked_until.isoformat() if blocked_until else None,
                policy.version,
                now.isoformat(),
            ),
        )
        return failure_count, blocked_until


class AuthenticationThrottleService:
    def __init__(
        self,
        repository: SQLiteAuthenticationThrottleRepository,
        policy: AuthenticationThrottlePolicy,
    ) -> None:
        self.repository = repository
        self.policy = policy

    def evaluate(
        self, keys: AuthenticationThrottleKeys, now: datetime
    ) -> AuthenticationThrottleDecision:
        return self.repository.evaluate(keys, self.policy, now)

    def record_failure(
        self, keys: AuthenticationThrottleKeys, now: datetime
    ) -> AuthenticationThrottleDecision:
        return self.repository.record_failure(keys, self.policy, now)

    def reset(self, keys: AuthenticationThrottleKeys, now: datetime) -> None:
        self.repository.reset(keys, now)


def _scoped_keys(
    keys: AuthenticationThrottleKeys,
) -> tuple[tuple[AuthenticationThrottleScope, str], ...]:
    return (
        (AuthenticationThrottleScope.USER, keys.user_key),
        (AuthenticationThrottleScope.CLIENT, keys.client_key),
    )


def _validate_inputs(keys: AuthenticationThrottleKeys, now: datetime) -> None:
    if not keys.user_key.strip() or not keys.client_key.strip():
        raise ActorContextValidationError("Opaque throttle keys are required.")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ActorContextValidationError("Throttle time must be timezone-aware.")


def _optional_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _decision(
    states: list[tuple[int, datetime | None]], now: datetime
) -> AuthenticationThrottleDecision:
    return AuthenticationThrottleDecision(
        blocked=any(
            blocked_until is not None and blocked_until > now for _, blocked_until in states
        ),
        failure_count=max((failure_count for failure_count, _ in states), default=0),
        blocked_scope_count=sum(
            blocked_until is not None and blocked_until > now for _, blocked_until in states
        ),
    )
