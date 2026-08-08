"""Fail-fast application environment settings."""

from __future__ import annotations

from dataclasses import dataclass
import os

from veri_kalitesi.persistence import DatabaseSettings


@dataclass(frozen=True)
class ApplicationSettings:
    runtime_environment: str
    database: DatabaseSettings
    allowed_origins: tuple[str, ...]
    audit_policy_version: str = "AUDIT_OUTBOX_V1"
    data_source_policy_version: str = "DATA_SOURCE_COMMAND_POLICY_V1"
    rule_policy_version: str = "RULE_APPROVAL_POLICY_V1"
    issue_policy_version: str = "ISSUE_ACCESS_POLICY_V1"
    actor_policy_version: str = "DASHBOARD_POLICY_V1"
    execution_command_policy_version: str = "EXECUTION_COMMAND_POLICY_V1"
    scoring_configuration_version: str = "DEFAULT_SCORING_V1"
    migration_check_enabled: bool = True
    local_secret_dir: str | None = None

    def __post_init__(self) -> None:
        if self.runtime_environment not in {"production", "development", "test"}:
            raise ValueError("Runtime environment is invalid.")
        if not self.allowed_origins or any(
            origin == "*" or not origin.strip() for origin in self.allowed_origins
        ):
            raise ValueError("At least one explicit application origin is required.")
        versions = (
            self.audit_policy_version,
            self.data_source_policy_version,
            self.rule_policy_version,
            self.issue_policy_version,
            self.actor_policy_version,
            self.execution_command_policy_version,
            self.scoring_configuration_version,
        )
        if any(not value.strip() for value in versions):
            raise ValueError("Application policy versions are required.")
        if (
            self.runtime_environment in {"production", "development"}
            and not self.migration_check_enabled
        ):
            raise ValueError("Migration preflight cannot be disabled for executable runtime.")
        if self.runtime_environment == "production" and self.local_secret_dir is not None:
            raise ValueError("Mounted local secrets are not a production provider.")

    @classmethod
    def from_environment(cls, *, runtime_environment: str | None = None) -> "ApplicationSettings":
        environment = runtime_environment or os.environ.get(
            "DATA_QUALITY_RUNTIME_ENVIRONMENT", "production"
        )
        origins = tuple(
            origin.strip()
            for origin in os.environ.get("DATA_QUALITY_ALLOWED_ORIGINS", "").split(",")
            if origin.strip()
        )
        return cls(
            runtime_environment=environment,
            database=DatabaseSettings.from_environment(),
            allowed_origins=origins,
            audit_policy_version=os.environ.get(
                "DATA_QUALITY_AUDIT_POLICY_VERSION", "AUDIT_OUTBOX_V1"
            ),
            data_source_policy_version=os.environ.get(
                "DATA_QUALITY_DATA_SOURCE_POLICY_VERSION",
                "DATA_SOURCE_COMMAND_POLICY_V1",
            ),
            rule_policy_version=os.environ.get(
                "DATA_QUALITY_RULE_POLICY_VERSION",
                "RULE_APPROVAL_POLICY_V1",
            ),
            issue_policy_version=os.environ.get(
                "DATA_QUALITY_ISSUE_POLICY_VERSION",
                "ISSUE_ACCESS_POLICY_V1",
            ),
            actor_policy_version=os.environ.get(
                "DATA_QUALITY_ACTOR_POLICY_VERSION", "DASHBOARD_POLICY_V1"
            ),
            execution_command_policy_version=os.environ.get(
                "DATA_QUALITY_EXECUTION_COMMAND_POLICY_VERSION",
                "EXECUTION_COMMAND_POLICY_V1",
            ),
            scoring_configuration_version=os.environ.get(
                "DATA_QUALITY_SCORING_CONFIGURATION_VERSION",
                "DEFAULT_SCORING_V1",
            ),
            local_secret_dir=os.environ.get("DATA_QUALITY_LOCAL_SECRET_DIR"),
        )
