"""DS-06 revision 19 migration PostgreSQL entegrasyon kanıtı.

Revision 19 şu varlıkları oluşturur:
  - scoring_configurations (+ partial unique: bir adet aktif)
  - scoring_configuration_approvals (+ maker!=checker check)
  - dataset_partial_score_policies (+ range check'ler, unique dataset+version)
  - score_publications (+ period partial unique, status check)
  - quality_scores (+ scope/status/level/value check'ler, exec+scope unique)
  - score_contribution_graphs → quality_scores FK
  - Varsayılan scoring configuration seed
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from veri_kalitesi.persistence import DatabaseSettings, create_session_factory

POSTGRES_TEST_URL = os.environ.get("DATA_QUALITY_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="DATA_QUALITY_POSTGRES_TEST_URL is required for PostgreSQL integration.",
)
ROOT = Path(__file__).resolve().parents[2]


class _PgFixture:
    def __init__(self, url: str, schema: str) -> None:
        self.schema = schema
        self.settings = DatabaseSettings.from_url(url, schema=schema)
        self.engine = create_engine(self.settings.url, pool_pre_ping=True)
        self.session_factory = create_session_factory(self.settings, engine=self.engine)


class _postgres_fixture:
    def __enter__(self) -> _PgFixture:
        assert POSTGRES_TEST_URL is not None
        schema = f"dq_ds06mig_{uuid4().hex[:10]}"
        self.fixture = _PgFixture(POSTGRES_TEST_URL, schema)
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option(
            "sqlalchemy.url",
            self.fixture.settings.url.render_as_string(hide_password=False),
        )
        config.set_main_option("data_quality_schema", schema)
        command.upgrade(config, "head")
        return self.fixture

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        with self.fixture.engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{self.fixture.schema}" CASCADE'))
        self.fixture.engine.dispose()


def test_revision_19_creates_all_expected_tables() -> None:
    """Migration 19 beş yeni tablo oluşturur."""
    with _postgres_fixture() as pg:
        inspector = inspect(pg.engine)
        tables = set(inspector.get_table_names(schema=pg.schema))
        expected = {
            "scoring_configurations",
            "scoring_configuration_approvals",
            "dataset_partial_score_policies",
            "score_publications",
            "quality_scores",
        }
        assert expected.issubset(tables), f"Missing tables: {expected - tables}"


def test_quality_scores_check_constraints() -> None:
    """quality_scores tablosu scope, status, level, value range check'leri içerir."""
    with _postgres_fixture() as pg:
        inspector = inspect(pg.engine)
        checks = {
            c["name"]: str(c["sqltext"])
            for c in inspector.get_check_constraints("quality_scores", schema=pg.schema)
        }
        assert "ck_quality_score_scope_type" in checks
        assert "ck_quality_score_status" in checks
        assert "ck_quality_score_level" in checks
        assert "ck_quality_score_value_range" in checks
        assert "ck_quality_score_level_requires_value" in checks
        assert "ck_quality_score_scope_id_required" in checks
        assert "ck_quality_score_published_must_be_official" in checks
        for scope in ("RULE", "DATASET", "DIMENSION", "SOURCE", "ENTERPRISE"):
            assert scope in checks["ck_quality_score_scope_type"]
        for status in ("CALCULATED", "NOT_CALCULATED", "NO_DATA", "PARTIAL"):
            assert status in checks["ck_quality_score_status"]


def test_score_publications_check_and_indexes() -> None:
    """score_publications status check, period partial unique ve published_at index."""
    with _postgres_fixture() as pg:
        inspector = inspect(pg.engine)
        checks = {
            c["name"]: str(c["sqltext"])
            for c in inspector.get_check_constraints("score_publications", schema=pg.schema)
        }
        assert "ck_publication_status" in checks
        assert "ck_publication_status_superseded_consistency" in checks
        assert "PUBLISHED" in checks["ck_publication_status"]
        assert "SUPERSEDED" in checks["ck_publication_status"]

        indexes = {
            idx["name"]: idx
            for idx in inspector.get_indexes("score_publications", schema=pg.schema)
        }
        assert "uq_publication_period_current" in indexes
        period_idx = indexes["uq_publication_period_current"]
        assert period_idx["unique"] is True
        assert "ix_publication_published_at" in indexes
        assert "ix_publication_period_status" in indexes


def test_contribution_graph_fk_to_quality_scores() -> None:
    """score_contribution_graphs tablosu quality_scores'a FK taşır."""
    with _postgres_fixture() as pg:
        inspector = inspect(pg.engine)
        fks = inspector.get_foreign_keys("score_contribution_graphs", schema=pg.schema)
        score_fks = [fk for fk in fks if fk.get("referred_table") == "quality_scores"]
        assert len(score_fks) >= 1, "score_contribution_graphs must FK to quality_scores"
        constrained = score_fks[0]["constrained_columns"]
        assert "quality_score_id" in constrained


def test_scoring_configurations_one_active_partial_unique() -> None:
    """scoring_configurations yalnız bir adet aktif konfigürasyona izin verir."""
    with _postgres_fixture() as pg:
        inspector = inspect(pg.engine)
        indexes = {
            idx["name"]: idx
            for idx in inspector.get_indexes("scoring_configurations", schema=pg.schema)
        }
        assert "uq_scoring_config_one_active" in indexes
        active_idx = indexes["uq_scoring_config_one_active"]
        assert active_idx["unique"] is True

        checks = {
            c["name"]: str(c["sqltext"])
            for c in inspector.get_check_constraints("scoring_configurations", schema=pg.schema)
        }
        assert "ck_scoring_config_thresholds" in checks


def test_default_scoring_configuration_is_seeded() -> None:
    """Migration varsayılan scoring konfigürasyonunu seed'ler."""
    with _postgres_fixture() as pg:
        with pg.engine.connect() as connection:
            row = connection.execute(
                text(
                    f'SELECT version, is_active FROM "{pg.schema}".scoring_configurations '
                    "WHERE configuration_id = 'default-scoring-configuration'"
                )
            ).fetchone()
        assert row is not None
        assert row[0] == "DEFAULT_SCORING_V1"
        assert row[1] is True


def test_quality_scores_unique_execution_scope() -> None:
    """quality_scores execution_id+scope_type+scope_id unique constraint."""
    with _postgres_fixture() as pg:
        inspector = inspect(pg.engine)
        indexes = {
            idx["name"]: idx for idx in inspector.get_indexes("quality_scores", schema=pg.schema)
        }
        assert "uq_quality_score_exec_scope" in indexes
        assert indexes["uq_quality_score_exec_scope"]["unique"] is True


def test_dataset_partial_score_policies_constraints() -> None:
    """dataset_partial_score_policies range ve maker!=checker check'leri."""
    with _postgres_fixture() as pg:
        inspector = inspect(pg.engine)
        checks = {
            c["name"]: str(c["sqltext"])
            for c in inspector.get_check_constraints(
                "dataset_partial_score_policies", schema=pg.schema
            )
        }
        assert "ck_partial_policy_approval_status" in checks
        assert "ck_partial_policy_coverage_range" in checks
        assert "ck_partial_policy_missing_range" in checks
        assert "ck_partial_policy_tech_error_range" in checks
        assert "ck_partial_policy_success_range" in checks
        assert "ck_partial_policy_maker_ne_checker" in checks
