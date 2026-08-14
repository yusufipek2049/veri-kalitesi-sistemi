"""Ikili kalicilik sözlesmesinin hizli, veritabani gerektirmeyen kapilari."""

from __future__ import annotations

import pytest

from repository_contracts import REPOSITORY_CONTRACTS, RepositoryContract
from veri_kalitesi.audit.postgresql_repository import PostgreSQLAuditRepository
from veri_kalitesi.audit.repository import SQLiteAuditRepository
from veri_kalitesi.data_sources.postgresql_repository import PostgreSQLDataSourceRepository
from veri_kalitesi.data_sources.repository import SQLiteDataSourceRepository
from veri_kalitesi.executions.postgresql_repository import PostgreSQLExecutionRepository
from veri_kalitesi.executions.repository import SQLiteExecutionRepository
from veri_kalitesi.notifications.postgresql_repository import PostgreSQLNotificationRepository
from veri_kalitesi.notifications.repository import SQLiteNotificationRepository
from veri_kalitesi.rules.postgresql_repository import PostgreSQLRuleRepository
from veri_kalitesi.rules.repository import SQLiteRuleRepository
from veri_kalitesi.scoring.postgresql_repository import PostgreSQLScoreRepository
from veri_kalitesi.scoring.repository import SQLiteScoreRepository


REPOSITORY_TYPES = {
    "audit": (SQLiteAuditRepository, PostgreSQLAuditRepository),
    "data_sources": (SQLiteDataSourceRepository, PostgreSQLDataSourceRepository),
    "executions": (SQLiteExecutionRepository, PostgreSQLExecutionRepository),
    "notifications": (SQLiteNotificationRepository, PostgreSQLNotificationRepository),
    "rules": (SQLiteRuleRepository, PostgreSQLRuleRepository),
    "scoring": (SQLiteScoreRepository, PostgreSQLScoreRepository),
}


@pytest.mark.parametrize("contract", REPOSITORY_CONTRACTS, ids=lambda item: item.name)
def test_both_implementations_expose_the_shared_contract(
    contract: RepositoryContract,
) -> None:
    for repository_type in REPOSITORY_TYPES[contract.name]:
        contract.assert_surface(repository_type)


def test_contract_gate_rejects_an_intentional_behavior_divergence() -> None:
    contract = RepositoryContract(
        name="deliberate-divergence",
        required_methods=frozenset({"observe"}),
        observe_empty_state=lambda repository: repository.observe(),
    )

    class ExpectedRepository:
        def observe(self) -> tuple[str, ...]:
            return ()

    class DivergentRepository:
        def observe(self) -> tuple[str, ...]:
            return ("unexpected",)

    with pytest.raises(AssertionError, match="behavior diverged"):
        contract.assert_equivalent(ExpectedRepository(), DivergentRepository())
