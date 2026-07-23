"""36A1 PostgreSQL-only kalıcılık temeli birim testleri."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from veri_kalitesi.issues import issue_table
from veri_kalitesi.persistence import (
    DatabaseConfigurationError,
    DatabaseSettings,
    create_session_factory,
    transactional_session,
)

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = ROOT / "05-Veritabani/alembic/versions/20260723_01_issue_baseline.py"


def test_database_settings_require_postgresql_only_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NFR-MNT-006: Eksik veya PostgreSQL dışı kalıcılık fail-closed reddedilir."""

    monkeypatch.delenv("DATA_QUALITY_DATABASE_URL", raising=False)
    with pytest.raises(DatabaseConfigurationError, match="is required"):
        DatabaseSettings.from_environment()

    with pytest.raises(DatabaseConfigurationError, match="Only postgresql"):
        DatabaseSettings.from_url("sqlite+pysqlite:///:memory:")

    with pytest.raises(DatabaseConfigurationError, match="must be data_quality"):
        DatabaseSettings.from_url("postgresql+psycopg://app@localhost/other")


def test_database_settings_hide_credentials_and_validate_schema() -> None:
    """NFR-MNT-006: Secret güvenli URL gösterimine sızmaz."""

    settings = DatabaseSettings.from_url(
        "postgresql+psycopg://app:synthetic-value@localhost/data_quality"
    )

    assert "synthetic-value" not in settings.safe_url()
    assert "***" in settings.safe_url()
    with pytest.raises(DatabaseConfigurationError, match="schema is invalid"):
        DatabaseSettings.from_url(
            "postgresql+psycopg://app@localhost/data_quality",
            schema="dq;drop",
        )


def test_session_factory_rejects_non_postgresql_engine() -> None:
    """NFR-REL-006: Kalıcı repository için bellek içi veya SQLite engine kabul edilmez."""

    settings = DatabaseSettings.from_url("postgresql+psycopg://app@localhost/data_quality")
    non_postgresql_engine = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))

    with pytest.raises(DatabaseConfigurationError, match="Only PostgreSQL"):
        create_session_factory(settings, engine=non_postgresql_engine)  # type: ignore[arg-type]


def test_transactional_session_commits_and_closes() -> None:
    """NFR-REL-006: Başarılı iş aynı transaction içinde commit edilir."""

    fake_session = _FakeSession()

    with transactional_session(lambda: fake_session):  # type: ignore[arg-type]
        fake_session.touched = True

    assert fake_session.committed is True
    assert fake_session.closed is True


def test_transactional_session_rolls_back_on_failure() -> None:
    """NFR-REL-006: Teknik hata başarılı yazma gibi commit edilmez."""

    fake_session = _FakeSession()

    with pytest.raises(RuntimeError, match="synthetic failure"):
        with transactional_session(lambda: fake_session):  # type: ignore[arg-type]
            raise RuntimeError("synthetic failure")

    assert fake_session.rolled_back is True
    assert fake_session.committed is False
    assert fake_session.closed is True


def test_issue_table_uses_dq_schema_and_optimistic_version() -> None:
    """FR-064–FR-070: İlk issue tablosu dq şeması ve sürüm alanıyla tanımlıdır."""

    table = issue_table()

    assert table.schema == "dq"
    assert "version" in table.c
    assert table.c.version.nullable is False
    assert {index.name for index in table.indexes} == {
        "ix_dq_issues_assignee_status_updated",
        "ix_dq_issues_scope_updated",
    }


def test_baseline_migration_is_forward_only() -> None:
    """PG-MIG-004: Baseline production downgrade sağlamaz."""

    spec = importlib.util.spec_from_file_location("issue_baseline", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with pytest.raises(RuntimeError, match="forward corrective migration"):
        module.downgrade()


class _FakeTransaction:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc_type is None:
            self.session.committed = True
        else:
            self.session.rolled_back = True


class _FakeSession:
    committed = False
    rolled_back = False
    closed = False
    touched = False

    def begin(self) -> _FakeTransaction:
        return _FakeTransaction(self)

    def close(self) -> None:
        self.closed = True
