"""Geliştirme bileşimi için bellek içi SQL şablonu deposu."""

from __future__ import annotations

from threading import Lock

from veri_kalitesi.sql_templates.errors import (
    SqlTemplateConflictError,
    SqlTemplateNotFoundError,
)
from veri_kalitesi.sql_templates.models import SqlTemplate


class InMemorySqlTemplateRepository:
    """Süreç ömrü boyunca yaşayan şablon deposu; yalnız geliştirme içindir."""

    def __init__(self, seed: tuple[SqlTemplate, ...] = ()) -> None:
        self._templates: dict[str, SqlTemplate] = {item.template_id: item for item in seed}
        self._lock = Lock()

    def list_all(self) -> list[SqlTemplate]:
        with self._lock:
            return sorted(self._templates.values(), key=lambda item: item.name.casefold())

    def get(self, template_id: str) -> SqlTemplate:
        with self._lock:
            template = self._templates.get(template_id)
        if template is None:
            raise SqlTemplateNotFoundError("SQL template not found.")
        return template

    def add(self, template: SqlTemplate) -> SqlTemplate:
        with self._lock:
            self._require_unique_name(template)
            self._templates[template.template_id] = template
        return template

    def replace(self, template: SqlTemplate, *, expected_version: int) -> SqlTemplate:
        with self._lock:
            current = self._templates.get(template.template_id)
            if current is None:
                raise SqlTemplateNotFoundError("SQL template not found.")
            if current.version != expected_version:
                raise SqlTemplateConflictError("SQL template was changed concurrently.")
            self._require_unique_name(template)
            self._templates[template.template_id] = template
        return template

    def delete(self, template_id: str) -> None:
        with self._lock:
            if self._templates.pop(template_id, None) is None:
                raise SqlTemplateNotFoundError("SQL template not found.")

    def _require_unique_name(self, template: SqlTemplate) -> None:
        folded = template.name.casefold()
        for existing in self._templates.values():
            if existing.template_id == template.template_id:
                continue
            if existing.name.casefold() == folded:
                raise SqlTemplateConflictError("A SQL template with this name already exists.")
