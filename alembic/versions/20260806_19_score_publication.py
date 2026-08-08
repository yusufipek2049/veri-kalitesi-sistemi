"""DS-06 skor kalıcılığı ve atomik yayım.

Revision ID: 20260806_19
Revises: 20260806_18

DS-06 dikey dilimi:
  1. scoring_configurations — aktif konfigürasyon kalıcılığı
  2. scoring_configuration_approvals — maker-checker onay kayıtları
  3. dataset_partial_score_policies — kısmi skor uygunluk politikası
  4. score_publications — atomik yayın state-machine (PUBLISHED/SUPERSEDED)
  5. quality_scores — kalıcı skor kayıtları (tüm scope seviyeleri)
  6. score_contribution_graphs FK — quality_scores'a referans
  7. İndeksler, check constraint'ler, partial unique constraint'ler
  8. Varsayılan scoring configuration seed
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260806_19"
down_revision = "20260806_18"
branch_labels = None
depends_on = None


def _schema() -> str:
    return op.get_context().config.get_main_option("data_quality_schema", "dq")


def upgrade() -> None:
    schema = _schema()

    # ── 1. scoring_configurations ──
    op.create_table(
        "scoring_configurations",
        sa.Column("configuration_id", sa.String(36), primary_key=True),
        sa.Column("version", sa.String(80), nullable=False, unique=True),
        sa.Column("threshold_version", sa.String(80), nullable=False),
        sa.Column("critical_upper_exclusive", sa.Numeric(7, 4), nullable=False),
        sa.Column("risky_upper_exclusive", sa.Numeric(7, 4), nullable=False),
        sa.Column("acceptable_upper_exclusive", sa.Numeric(7, 4), nullable=False),
        sa.Column(
            "dimension_weights",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "criticality_weights",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "critical_upper_exclusive > 0"
            " AND risky_upper_exclusive > critical_upper_exclusive"
            " AND acceptable_upper_exclusive > risky_upper_exclusive"
            " AND acceptable_upper_exclusive <= 100",
            name="ck_scoring_config_thresholds",
        ),
        schema=schema,
    )
    op.create_index(
        "uq_scoring_config_one_active",
        "scoring_configurations",
        ["is_active"],
        unique=True,
        schema=schema,
        postgresql_where=sa.text("is_active = true"),
    )

    # ── 2. scoring_configuration_approvals ──
    op.create_table(
        "scoring_configuration_approvals",
        sa.Column("approval_id", sa.String(36), primary_key=True),
        sa.Column(
            "configuration_id",
            sa.String(36),
            sa.ForeignKey(f"{schema}.scoring_configurations.configuration_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("maker_actor_id", sa.String(128), nullable=False),
        sa.Column("checker_actor_id", sa.String(128)),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("decision_reason_code", sa.String(120)),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED')",
            name="ck_config_approval_status",
        ),
        sa.CheckConstraint(
            "maker_actor_id <> checker_actor_id OR checker_actor_id IS NULL",
            name="ck_config_approval_maker_ne_checker",
        ),
        schema=schema,
    )

    # ── 3. dataset_partial_score_policies ──
    op.create_table(
        "dataset_partial_score_policies",
        sa.Column("policy_id", sa.String(36), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.String(36),
            sa.ForeignKey(f"{schema}.datasets.dataset_id"),
            nullable=False,
        ),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("allow_official_partial_score", sa.Boolean(), nullable=False),
        sa.Column("minimum_coverage_ratio", sa.Numeric(7, 6), nullable=False),
        sa.Column(
            "required_critical_rule_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "required_partitions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "maximum_missing_record_ratio",
            sa.Numeric(7, 6),
            nullable=False,
        ),
        sa.Column(
            "maximum_technical_error_ratio",
            sa.Numeric(7, 6),
            nullable=False,
        ),
        sa.Column(
            "minimum_successful_rule_ratio",
            sa.Numeric(7, 6),
            nullable=False,
        ),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approval_status", sa.String(20), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("approved_by", sa.String(128)),
        sa.Column("audit_reference", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "dataset_id",
            "policy_version",
            name="uq_partial_policy_dataset_version",
        ),
        sa.CheckConstraint(
            "approval_status IN"
            " ('DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'WITHDRAWN', 'EXPIRED')",
            name="ck_partial_policy_approval_status",
        ),
        sa.CheckConstraint(
            "minimum_coverage_ratio >= 0 AND minimum_coverage_ratio <= 1",
            name="ck_partial_policy_coverage_range",
        ),
        sa.CheckConstraint(
            "maximum_missing_record_ratio >= 0 AND maximum_missing_record_ratio <= 1",
            name="ck_partial_policy_missing_range",
        ),
        sa.CheckConstraint(
            "maximum_technical_error_ratio >= 0 AND maximum_technical_error_ratio <= 1",
            name="ck_partial_policy_tech_error_range",
        ),
        sa.CheckConstraint(
            "minimum_successful_rule_ratio >= 0 AND minimum_successful_rule_ratio <= 1",
            name="ck_partial_policy_success_range",
        ),
        sa.CheckConstraint(
            "created_by <> approved_by OR approved_by IS NULL",
            name="ck_partial_policy_maker_ne_checker",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_partial_policy_dataset_effective",
        "dataset_partial_score_policies",
        ["dataset_id", "effective_from"],
        schema=schema,
    )

    # ── 4. score_publications ──
    op.create_table(
        "score_publications",
        sa.Column("publication_id", sa.String(36), primary_key=True),
        sa.Column(
            "execution_id",
            sa.String(36),
            sa.ForeignKey(f"{schema}.rule_executions.execution_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("period", sa.String(80), nullable=False),
        sa.Column("input_digest", sa.String(71), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('PUBLISHED', 'SUPERSEDED')",
            name="ck_publication_status",
        ),
        sa.CheckConstraint(
            "(status = 'PUBLISHED' AND superseded_at IS NULL)"
            " OR (status = 'SUPERSEDED' AND superseded_at IS NOT NULL)",
            name="ck_publication_status_superseded_consistency",
        ),
        schema=schema,
    )
    op.create_index(
        "uq_publication_period_current",
        "score_publications",
        ["period"],
        unique=True,
        schema=schema,
        postgresql_where=sa.text("status = 'PUBLISHED'"),
    )
    op.create_index(
        "ix_publication_published_at",
        "score_publications",
        [sa.text("published_at DESC")],
        schema=schema,
    )
    op.create_index(
        "ix_publication_period_status",
        "score_publications",
        ["period", "status"],
        schema=schema,
    )

    # ── 5. quality_scores ──
    op.create_table(
        "quality_scores",
        sa.Column("quality_score_id", sa.String(36), primary_key=True),
        sa.Column(
            "publication_id",
            sa.String(36),
            sa.ForeignKey(f"{schema}.score_publications.publication_id"),
        ),
        sa.Column(
            "execution_id",
            sa.String(36),
            sa.ForeignKey(f"{schema}.rule_executions.execution_id"),
            nullable=False,
        ),
        sa.Column(
            "rule_result_id",
            sa.String(36),
            sa.ForeignKey(f"{schema}.rule_execution_results.rule_result_id"),
        ),
        sa.Column(
            "rule_version_id",
            sa.String(36),
            sa.ForeignKey(f"{schema}.rule_versions.rule_version_id"),
        ),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("scope_id", sa.String(128)),
        sa.Column("score_value", sa.Numeric(7, 4)),
        sa.Column("score_status", sa.String(40), nullable=False),
        sa.Column("measurement_status", sa.String(30)),
        sa.Column("level", sa.String(20)),
        sa.Column("rule_version_digest", sa.String(71)),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("included_component_count", sa.Integer()),
        sa.Column("excluded_component_count", sa.Integer()),
        sa.Column(
            "calculation_details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "scope_type IN ('RULE', 'DATASET', 'DIMENSION', 'SOURCE', 'ENTERPRISE')",
            name="ck_quality_score_scope_type",
        ),
        sa.CheckConstraint(
            "score_value IS NULL OR (score_value >= 0 AND score_value <= 100)",
            name="ck_quality_score_value_range",
        ),
        sa.CheckConstraint(
            "score_status IN"
            " ('CALCULATED', 'NOT_CALCULATED', 'NO_DATA', 'PARTIAL',"
            " 'NOT_CALCULATED_TECHNICAL_ERROR', 'CONFIG_ERROR')",
            name="ck_quality_score_status",
        ),
        sa.CheckConstraint(
            "level IS NULL OR level IN ('GOOD', 'ACCEPTABLE', 'RISKY', 'CRITICAL')",
            name="ck_quality_score_level",
        ),
        sa.CheckConstraint(
            "score_value IS NOT NULL OR level IS NULL",
            name="ck_quality_score_level_requires_value",
        ),
        sa.CheckConstraint(
            "scope_type = 'ENTERPRISE' OR scope_id IS NOT NULL",
            name="ck_quality_score_scope_id_required",
        ),
        sa.CheckConstraint(
            "included_component_count IS NULL OR included_component_count >= 0",
            name="ck_quality_score_included_count",
        ),
        sa.CheckConstraint(
            "excluded_component_count IS NULL OR excluded_component_count >= 0",
            name="ck_quality_score_excluded_count",
        ),
        sa.CheckConstraint(
            "publication_id IS NULL"
            " OR (score_value IS NOT NULL"
            "     AND score_status IN ('CALCULATED', 'PARTIAL'))",
            name="ck_quality_score_published_must_be_official",
        ),
        schema=schema,
    )
    op.create_index(
        "uq_quality_score_exec_scope",
        "quality_scores",
        ["execution_id", "scope_type", sa.text("COALESCE(scope_id, '')")],
        unique=True,
        schema=schema,
    )
    op.create_index(
        "ix_quality_score_scope_time",
        "quality_scores",
        ["scope_type", "scope_id", sa.text("calculated_at DESC")],
        schema=schema,
    )
    op.create_index(
        "ix_quality_score_publication",
        "quality_scores",
        ["publication_id"],
        schema=schema,
    )
    op.create_index(
        "ix_quality_score_execution",
        "quality_scores",
        ["execution_id"],
        schema=schema,
    )

    # ── 6. score_contribution_graphs FK ──
    op.create_foreign_key(
        "fk_contribution_graph_quality_score",
        "score_contribution_graphs",
        "quality_scores",
        ["quality_score_id"],
        ["quality_score_id"],
        source_schema=schema,
        referent_schema=schema,
    )

    # ── 7. Default scoring configuration seed ──
    op.execute(
        f"""
        INSERT INTO {schema}.scoring_configurations (
            configuration_id, version, threshold_version,
            critical_upper_exclusive, risky_upper_exclusive,
            acceptable_upper_exclusive,
            dimension_weights, criticality_weights,
            created_by, created_at, is_active, activated_at
        ) SELECT
            'default-scoring-configuration',
            'DEFAULT_SCORING_V1',
            'DEFAULT_THRESHOLDS_V1',
            50.00, 75.00, 90.00,
            '{{"COMPLETENESS":"1.0","ACCURACY":"1.0","VALIDITY":"1.0",'
            '"CONSISTENCY":"1.0","UNIQUENESS":"1.0","TIMELINESS":"1.0",'
            '"INTEGRITY":"1.0"}}'::jsonb,
            '{{"LOW":"1.0","MEDIUM":"1.0","HIGH":"1.0","CRITICAL":"1.0"}}'::jsonb,
            'system',
            NOW(),
            true,
            NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM {schema}.scoring_configurations LIMIT 1
        )
        """
    )


def downgrade() -> None:
    raise RuntimeError(
        "Production downgrade is disabled for DS-06 score publication; "
        "create a forward corrective migration instead."
    )
