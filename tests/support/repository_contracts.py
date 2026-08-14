"""SQLite ve PostgreSQL depolarina ayni beklentileri uygulayan Faz 3 test destegi."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RepositoryContract:
    name: str
    required_methods: frozenset[str]
    observe_empty_state: Callable[[Any], Any]

    def assert_surface(self, repository_type: type[Any]) -> None:
        missing = sorted(
            method
            for method in self.required_methods
            if not callable(getattr(repository_type, method, None))
        )
        assert not missing, f"{repository_type.__name__} missing {self.name} methods: {missing}"

    def assert_equivalent(self, sqlite_repository: Any, postgresql_repository: Any) -> None:
        sqlite_observation = self.observe_empty_state(sqlite_repository)
        postgresql_observation = self.observe_empty_state(postgresql_repository)
        assert sqlite_observation == postgresql_observation, (
            f"{self.name} behavior diverged: "
            f"SQLite={sqlite_observation!r}, PostgreSQL={postgresql_observation!r}"
        )


REPOSITORY_CONTRACTS = (
    RepositoryContract(
        name="audit",
        required_methods=frozenset(
            {
                "append",
                "latest_sequence_no",
                "query_events",
                "query_summary",
                "verify_integrity",
            }
        ),
        observe_empty_state=lambda repository: repository.latest_sequence_no(),
    ),
    RepositoryContract(
        name="data_sources",
        required_methods=frozenset(
            {
                "add_data_source",
                "get_data_source",
                "list_all_data_sources",
                "list_data_fields",
                "list_datasets",
                "replace_metadata",
            }
        ),
        observe_empty_state=lambda repository: repository.list_all_data_sources(),
    ),
    RepositoryContract(
        name="executions",
        required_methods=frozenset(
            {
                "add_attempt",
                "claim_next",
                "complete_cancelled",
                "complete_success",
                "complete_technical_error",
                "complete_timeout",
                "create_or_get",
                "get",
                "list_attempts",
                "list_cancel_requested",
                "list_executions_for_sources",
                "list_results",
                "request_cancel",
            }
        ),
        observe_empty_state=lambda repository: repository.list_cancel_requested(),
    ),
    RepositoryContract(
        name="notifications",
        required_methods=frozenset({"list_for_recipient"}),
        observe_empty_state=lambda repository: repository.list_for_recipient("contract-user"),
    ),
    RepositoryContract(
        name="rules",
        required_methods=frozenset(
            {
                "add_rule_with_version",
                "add_version",
                "get_rule",
                "get_version",
                "list_rules_with_latest_version",
                "list_versions",
                "update_rule_status",
            }
        ),
        observe_empty_state=lambda repository: repository.list_rules_with_latest_version(
            frozenset()
        ),
    ),
    RepositoryContract(
        name="scoring",
        required_methods=frozenset(
            {
                "get",
                "get_active_configuration",
                "get_configuration",
                "list_for_dashboard_trend",
                "list_for_execution",
            }
        ),
        observe_empty_state=lambda repository: repository.list_for_execution(
            "contract-execution"
        ),
    ),
)
