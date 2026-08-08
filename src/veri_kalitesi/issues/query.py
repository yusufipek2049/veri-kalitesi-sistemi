"""Yetki kapsamlı, veri-minimum sorun envanteri sorgusu."""

from __future__ import annotations

import sqlite3
from typing import Protocol

from sqlalchemy.exc import SQLAlchemyError

from veri_kalitesi.identity import ActorContext, AuthorizationService, IdentityError
from veri_kalitesi.issues.models import DataQualityIssue


class IssueReader(Protocol):
    def list_issues_for_scopes(
        self,
        allowed_source_ids: frozenset[str],
        allowed_dataset_ids: frozenset[str],
        *,
        limit: int = 100,
    ) -> list[DataQualityIssue]: ...


class IssueQueryError(Exception):
    def __init__(self, message: str, correlation_id: str) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id


class IssueQueryAuthorizationError(IssueQueryError):
    """Güvenilir sorun kapsamı üretilemedi."""


class IssueQueryTechnicalError(IssueQueryError):
    """Sorun envanteri sorgusu teknik nedenle tamamlanamadı."""


class IssueQueryService:
    def __init__(
        self,
        reader: IssueReader,
        authorization_service: AuthorizationService,
        *,
        page_limit: int = 100,
    ) -> None:
        if not 1 <= page_limit <= 100:
            raise ValueError("Issue page limit must be between 1 and 100.")
        self.reader = reader
        self.authorization_service = authorization_service
        self.page_limit = page_limit

    def list_for_actor(self, actor_context: ActorContext | None) -> tuple[DataQualityIssue, ...]:
        correlation_id = (
            actor_context.correlation_id if actor_context is not None else "authorization-denied"
        )
        try:
            decision = self.authorization_service.authorize_dashboard(actor_context)
        except IdentityError as exc:
            raise IssueQueryAuthorizationError(
                "Issue scope is not available.", correlation_id
            ) from exc
        try:
            return tuple(
                self.reader.list_issues_for_scopes(
                    decision.permitted_source_ids,
                    decision.permitted_dataset_ids,
                    limit=self.page_limit,
                )
            )
        except (sqlite3.Error, SQLAlchemyError, OSError) as exc:
            raise IssueQueryTechnicalError(
                "Issue query could not be completed.", correlation_id
            ) from exc
