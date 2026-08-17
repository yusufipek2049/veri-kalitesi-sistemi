"""sql_query_templates tablosu PostgreSQL deposu.

Ad benzersizliği veritabanındaki case-insensitive unique index ile korunur;
güncellemeler optimistic concurrency (version CAS) ile uygulanır.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError

from veri_kalitesi.persistence import DEFAULT_SCHEMA_NAME, SessionFactory, transactional_session
from veri_kalitesi.sql_templates.errors import (
    SqlTemplateConflictError,
    SqlTemplateNotFoundError,
)
from veri_kalitesi.sql_templates.models import SqlTemplate

#: Ada göre benzersizliği koruyan case-insensitive index (migration 28).
UNIQUE_NAME_INDEX = "ux_sql_query_templates_name"

#: Liste yanıtı sınırsız büyümesin diye uygulanan üst sınır.
LIST_LIMIT = 500


@dataclass(frozen=True)
class SqlTemplateTables:
    templates: Table


def sql_template_tables(schema: str = DEFAULT_SCHEMA_NAME) -> SqlTemplateTables:
    metadata = MetaData(schema=schema)
    templates = Table(
        "sql_query_templates",
        metadata,
        Column("template_id", String(36), primary_key=True),
        Column("name", String(120), nullable=False),
        Column("description", String(500)),
        Column("sql_text", Text, nullable=False),
        Column("default_timeout_seconds", Integer, nullable=False),
        Column("default_row_limit", Integer, nullable=False),
        Column("owner_user_id", String(128), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
        Column("version", Integer, nullable=False),
    )
    return SqlTemplateTables(templates=templates)


class PostgreSQLSqlTemplateRepository:
    """Adlandırılmış SQL şablonlarını PostgreSQL'de saklar."""

    def __init__(
        self,
        session_factory: SessionFactory,
        tables: SqlTemplateTables | None = None,
        *,
        schema: str = DEFAULT_SCHEMA_NAME,
    ) -> None:
        self.session_factory = session_factory
        self.tables = tables or sql_template_tables(schema)

    def list_all(self) -> list[SqlTemplate]:
        table = self.tables.templates
        with self.session_factory() as session:
            rows = (
                session.execute(select(table).order_by(table.c.name.asc()).limit(LIST_LIMIT))
                .mappings()
                .all()
            )
        return [_row_to_template(row) for row in rows]

    def get(self, template_id: str) -> SqlTemplate:
        table = self.tables.templates
        with self.session_factory() as session:
            row = (
                session.execute(select(table).where(table.c.template_id == template_id))
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise SqlTemplateNotFoundError("SQL template not found.")
        return _row_to_template(row)

    def add(self, template: SqlTemplate) -> SqlTemplate:
        with transactional_session(self.session_factory) as session:
            try:
                session.execute(
                    insert(self.tables.templates).values(**_template_to_values(template))
                )
            except IntegrityError as exc:
                raise _classify_integrity_error(exc) from exc
        return template

    def replace(self, template: SqlTemplate, *, expected_version: int) -> SqlTemplate:
        table = self.tables.templates
        with transactional_session(self.session_factory) as session:
            try:
                result = session.execute(
                    update(table)
                    .where(
                        table.c.template_id == template.template_id,
                        table.c.version == expected_version,
                    )
                    .values(
                        name=template.name,
                        description=template.description,
                        sql_text=template.sql_text,
                        default_timeout_seconds=template.default_timeout_seconds,
                        default_row_limit=template.default_row_limit,
                        updated_at=template.updated_at,
                        version=template.version,
                    )
                )
            except IntegrityError as exc:
                raise _classify_integrity_error(exc) from exc
            if result.rowcount != 1:  # type: ignore[attr-defined]
                raise SqlTemplateConflictError("SQL template was changed concurrently.")
        return self.get(template.template_id)

    def delete(self, template_id: str) -> None:
        table = self.tables.templates
        with transactional_session(self.session_factory) as session:
            result = session.execute(delete(table).where(table.c.template_id == template_id))
            if result.rowcount != 1:  # type: ignore[attr-defined]
                raise SqlTemplateNotFoundError("SQL template not found.")


def _violated_constraint(exc: IntegrityError) -> str:
    diagnostics = getattr(getattr(exc, "orig", None), "diag", None)
    name = getattr(diagnostics, "constraint_name", None)
    if name:
        return str(name)
    message = str(getattr(exc, "orig", exc))
    for candidate in re.findall(r'"([a-z0-9_]+)"', message):
        if candidate.startswith(("ux_sql_query_templates", "ck_sql_query_templates")):
            return str(candidate)
    return ""


def _classify_integrity_error(exc: IntegrityError) -> Exception:
    constraint = _violated_constraint(exc)
    if constraint == UNIQUE_NAME_INDEX:
        return SqlTemplateConflictError("A SQL template with this name already exists.")
    return SqlTemplateConflictError(
        "The SQL template could not be stored due to a database constraint"
        f"{f' ({constraint})' if constraint else ''}."
    )


def _template_to_values(template: SqlTemplate) -> dict:
    return {
        "template_id": template.template_id,
        "name": template.name,
        "description": template.description,
        "sql_text": template.sql_text,
        "default_timeout_seconds": template.default_timeout_seconds,
        "default_row_limit": template.default_row_limit,
        "owner_user_id": template.owner_user_id,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
        "version": template.version,
    }


def _row_to_template(row) -> SqlTemplate:
    return SqlTemplate(
        template_id=row["template_id"],
        name=row["name"],
        description=row["description"],
        sql_text=row["sql_text"],
        default_timeout_seconds=row["default_timeout_seconds"],
        default_row_limit=row["default_row_limit"],
        owner_user_id=row["owner_user_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        version=row["version"],
    )
