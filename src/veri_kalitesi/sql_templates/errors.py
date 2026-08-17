"""Adlandırılmış SQL şablonu hata türleri."""

from __future__ import annotations


class SqlTemplateError(Exception):
    """SQL şablonu domain hata kökü."""


class SqlTemplateValidationError(SqlTemplateError):
    """Şablon girdisi domain doğrulamasını geçemedi (ad, SQL, limitler)."""


class SqlTemplateAuthorizationError(SqlTemplateError):
    """Aktör bağlamı şablon üzerinde bu işlemi yapmaya yetkili değil."""


class SqlTemplateNotFoundError(SqlTemplateError):
    """Şablon kimliği mevcut değil."""


class SqlTemplateConflictError(SqlTemplateError):
    """Şablon adı zaten kullanılıyor veya sürüm eşzamanlı değişti."""


class SqlTemplateTechnicalError(SqlTemplateError):
    """Şablon deposu geçici olarak kullanılamıyor."""
