"""Yetki kapsamlı, veri-minimum çalıştırma geçmişi sorgusu."""

from __future__ import annotations

import sqlite3
from typing import Protocol

from veri_kalitesi.executions.models import RuleExecution
from veri_kalitesi.identity import ActorContext, AuthorizationService, IdentityError


class ExecutionReader(Protocol):
    def list_executions_for_sources(
        self,
        allowed_source_ids: frozenset[str],
        *,
        limit: int = 100,
    ) -> list[RuleExecution]: ...


class ExecutionQueryError(Exception):
    def __init__(self, message: str, correlation_id: str) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id


class ExecutionQueryAuthorizationError(ExecutionQueryError):
    """Güvenilir kaynak kapsamı üretilemedi."""


class ExecutionQueryTechnicalError(ExecutionQueryError):
    """Çalıştırma geçmişi sorgusu teknik nedenle tamamlanamadı."""


class ExecutionQueryService:
    def __init__(
        self,
        reader: ExecutionReader,
        authorization_service: AuthorizationService,
        *,
        page_limit: int = 100,
    ) -> None:
        if not 1 <= page_limit <= 100:
            raise ValueError("Execution page limit must be between 1 and 100.")
        self.reader = reader
        self.authorization_service = authorization_service
        self.page_limit = page_limit

    def list_for_actor(self, actor_context: ActorContext | None) -> tuple[RuleExecution, ...]:
        correlation_id = (
            actor_context.correlation_id if actor_context is not None else "authorization-denied"
        )
        try:
            decision = self.authorization_service.authorize_dashboard(actor_context)
        except IdentityError as exc:
            raise ExecutionQueryAuthorizationError(
                "Execution scope is not available.", correlation_id
            ) from exc
        try:
            return tuple(
                self.reader.list_executions_for_sources(
                    decision.permitted_source_ids,
                    limit=self.page_limit,
                )
            )
        except (sqlite3.Error, OSError) as exc:
            raise ExecutionQueryTechnicalError(
                "Execution query could not be completed.", correlation_id
            ) from exc
