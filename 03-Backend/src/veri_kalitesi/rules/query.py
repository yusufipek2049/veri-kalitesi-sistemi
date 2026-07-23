"""Yetki kapsamlı, veri-minimum kural envanteri sorgusu."""

from __future__ import annotations

import sqlite3
from typing import Protocol

from sqlalchemy.exc import SQLAlchemyError

from veri_kalitesi.identity import ActorContext, AuthorizationService, IdentityError
from veri_kalitesi.rules.models import QualityRule, RuleVersion


class RuleReader(Protocol):
    def list_rules_with_latest_version(
        self, allowed_dataset_ids: frozenset[str]
    ) -> list[tuple[QualityRule, RuleVersion]]: ...


class RuleQueryError(Exception):
    def __init__(self, message: str, correlation_id: str) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id


class RuleQueryAuthorizationError(RuleQueryError):
    """Güvenilir dataset kapsamı üretilemedi."""


class RuleQueryTechnicalError(RuleQueryError):
    """Kural envanteri sorgusu teknik nedenle tamamlanamadı."""


class RuleQueryService:
    def __init__(self, reader: RuleReader, authorization_service: AuthorizationService) -> None:
        self.reader = reader
        self.authorization_service = authorization_service

    def list_for_actor(
        self, actor_context: ActorContext | None
    ) -> tuple[tuple[QualityRule, RuleVersion], ...]:
        correlation_id = (
            actor_context.correlation_id if actor_context is not None else "authorization-denied"
        )
        try:
            decision = self.authorization_service.authorize_dashboard(actor_context)
        except IdentityError as exc:
            raise RuleQueryAuthorizationError(
                "Rule scope is not available.", correlation_id
            ) from exc
        try:
            return tuple(self.reader.list_rules_with_latest_version(decision.permitted_dataset_ids))
        except (sqlite3.Error, SQLAlchemyError, OSError) as exc:
            raise RuleQueryTechnicalError(
                "Rule query could not be completed.", correlation_id
            ) from exc
