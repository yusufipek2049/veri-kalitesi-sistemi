"""Yönetişim onay merkezi hata türleri."""

from __future__ import annotations


class GovernanceError(Exception):
    """Yönetişim domain hata kökü."""


class GovernanceValidationError(GovernanceError):
    """Talep girdisi veya yaşam döngüsü koşulu domain doğrulamasını geçemedi."""


class GovernanceAuthorizationError(GovernanceError):
    """Aktör bağlamı, rolü veya nesne kapsamı maker-checker denetimini geçemedi."""


class GovernanceNotFoundError(GovernanceError):
    """Talep veya hedef nesne kimliği mevcut değil."""


class GovernanceConflictError(GovernanceError):
    """Talep hedef nesneyle veya eşzamanlı bir kararla çakışıyor."""
