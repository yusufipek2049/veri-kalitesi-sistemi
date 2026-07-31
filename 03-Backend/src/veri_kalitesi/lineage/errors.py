"""Lineage, yönetişim ve etki domain hata tipleri."""


class LineageError(Exception):
    """Lineage/yönetişim modülü için temel hata."""


class LineageValidationError(LineageError):
    """Lineage, yönetişim profili veya etki girdisi geçersiz."""
