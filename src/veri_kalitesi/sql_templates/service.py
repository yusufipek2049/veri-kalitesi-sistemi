"""SQL şablonu sorgu ve komut servisi.

Doğrulama fail-closed uygulanır: güvenilir olmayan aktör bağlamı hiçbir
şablonu göremez, salt okunur olmayan SQL hiç saklanmaz ve şablonu yalnızca
sahibi (veya kurumsal görünürlüğe sahip aktör) değiştirebilir.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from veri_kalitesi.data_sources.postgresql import is_read_only_sql
from veri_kalitesi.identity import ActorContext, is_trusted_actor_context
from veri_kalitesi.sql_templates.errors import (
    SqlTemplateAuthorizationError,
    SqlTemplateValidationError,
)
from veri_kalitesi.sql_templates.models import (
    DESCRIPTION_MAX_LENGTH,
    NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
    ROW_LIMIT_MAX,
    ROW_LIMIT_MIN,
    SQL_MAX_LENGTH,
    TIMEOUT_SECONDS_MAX,
    TIMEOUT_SECONDS_MIN,
    SqlTemplate,
)


class SqlTemplateRepository(Protocol):
    """Şablon deposunun servis tarafından tüketilen yüzeyi."""

    def list_all(self) -> list[SqlTemplate]: ...

    def get(self, template_id: str) -> SqlTemplate: ...

    def add(self, template: SqlTemplate) -> SqlTemplate: ...

    def replace(self, template: SqlTemplate, *, expected_version: int) -> SqlTemplate: ...

    def delete(self, template_id: str) -> None: ...


class SqlTemplateService:
    """Adlandırılmış SQL şablonlarının okuma ve yazma sınırı."""

    def __init__(
        self,
        repository: SqlTemplateRepository,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._repository = repository
        self._clock = clock

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def list_templates(self, actor_context: ActorContext | None) -> tuple[SqlTemplate, ...]:
        _require_trusted(actor_context)
        return tuple(self._repository.list_all())

    def get_template(self, actor_context: ActorContext | None, template_id: str) -> SqlTemplate:
        _require_trusted(actor_context)
        return self._repository.get(template_id)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def create_template(
        self,
        actor_context: ActorContext | None,
        *,
        name: str,
        sql_text: str,
        description: str | None = None,
        default_timeout_seconds: int,
        default_row_limit: int,
    ) -> SqlTemplate:
        actor = _require_trusted(actor_context)
        now = self._clock()
        template = SqlTemplate(
            template_id=str(uuid4()),
            name=_validated_name(name),
            description=_validated_description(description),
            sql_text=_validated_sql(sql_text),
            default_timeout_seconds=_validated_timeout(default_timeout_seconds),
            default_row_limit=_validated_row_limit(default_row_limit),
            owner_user_id=actor.actor_id,
            created_at=now,
            updated_at=now,
            version=1,
        )
        return self._repository.add(template)

    def update_template(
        self,
        actor_context: ActorContext | None,
        template_id: str,
        *,
        name: str | None = None,
        sql_text: str | None = None,
        description: str | None = None,
        default_timeout_seconds: int | None = None,
        default_row_limit: int | None = None,
    ) -> SqlTemplate:
        actor = _require_trusted(actor_context)
        current = self._repository.get(template_id)
        _require_owner(actor, current)
        updated = SqlTemplate(
            template_id=current.template_id,
            name=current.name if name is None else _validated_name(name),
            description=(
                current.description if description is None else _validated_description(description)
            ),
            sql_text=current.sql_text if sql_text is None else _validated_sql(sql_text),
            default_timeout_seconds=(
                current.default_timeout_seconds
                if default_timeout_seconds is None
                else _validated_timeout(default_timeout_seconds)
            ),
            default_row_limit=(
                current.default_row_limit
                if default_row_limit is None
                else _validated_row_limit(default_row_limit)
            ),
            owner_user_id=current.owner_user_id,
            created_at=current.created_at,
            updated_at=self._clock(),
            version=current.version + 1,
        )
        return self._repository.replace(updated, expected_version=current.version)

    def delete_template(self, actor_context: ActorContext | None, template_id: str) -> None:
        actor = _require_trusted(actor_context)
        current = self._repository.get(template_id)
        _require_owner(actor, current)
        self._repository.delete(template_id)


# ----------------------------------------------------------------------
# Validation helpers
# ----------------------------------------------------------------------


def _require_trusted(actor_context: ActorContext | None) -> ActorContext:
    if not is_trusted_actor_context(actor_context):
        raise SqlTemplateAuthorizationError("A trusted actor context is required.")
    assert actor_context is not None
    return actor_context


def _require_owner(actor: ActorContext, template: SqlTemplate) -> None:
    if actor.actor_id != template.owner_user_id and not actor.can_view_enterprise:
        raise SqlTemplateAuthorizationError("Only the template owner can change this template.")


def _validated_name(name: str) -> str:
    candidate = (name or "").strip()
    if not NAME_MIN_LENGTH <= len(candidate) <= NAME_MAX_LENGTH:
        raise SqlTemplateValidationError(
            f"Template name must be between {NAME_MIN_LENGTH} and {NAME_MAX_LENGTH} characters."
        )
    return candidate


def _validated_description(description: str | None) -> str | None:
    if description is None:
        return None
    candidate = description.strip()
    if not candidate:
        return None
    if len(candidate) > DESCRIPTION_MAX_LENGTH:
        raise SqlTemplateValidationError(
            f"Template description must be at most {DESCRIPTION_MAX_LENGTH} characters."
        )
    return candidate


def _validated_sql(sql_text: str) -> str:
    candidate = (sql_text or "").strip()
    if not candidate:
        raise SqlTemplateValidationError("Template SQL must not be empty.")
    if len(candidate) > SQL_MAX_LENGTH:
        raise SqlTemplateValidationError(
            f"Template SQL must be at most {SQL_MAX_LENGTH} characters."
        )
    if not is_read_only_sql(candidate):
        raise SqlTemplateValidationError("Template SQL must be a single read-only statement.")
    return candidate


def _validated_timeout(timeout_seconds: int) -> int:
    if not TIMEOUT_SECONDS_MIN <= int(timeout_seconds) <= TIMEOUT_SECONDS_MAX:
        raise SqlTemplateValidationError(
            f"Template timeout must be between {TIMEOUT_SECONDS_MIN} and"
            f" {TIMEOUT_SECONDS_MAX} seconds."
        )
    return int(timeout_seconds)


def _validated_row_limit(row_limit: int) -> int:
    if not ROW_LIMIT_MIN <= int(row_limit) <= ROW_LIMIT_MAX:
        raise SqlTemplateValidationError(
            f"Template row limit must be between {ROW_LIMIT_MIN} and {ROW_LIMIT_MAX}."
        )
    return int(row_limit)
