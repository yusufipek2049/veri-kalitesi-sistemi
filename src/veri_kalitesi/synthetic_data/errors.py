"""Sentetik veri kayıt çekirdeği hata sınıfları."""


class SyntheticDataError(Exception):
    """Sentetik veri domain hatalarının tabanı."""


class SyntheticDataValidationError(SyntheticDataError):
    """Geçersiz veya eksik sentetik veri sözleşmesi."""


class SyntheticDataAuthorizationError(SyntheticDataError):
    """Güvenilir bağlam veya kapsam reddi."""


class SyntheticDataConflictError(SyntheticDataError):
    """Değişmez kimlik ya da sürüm çakışması."""


class SyntheticDataTechnicalError(SyntheticDataError):
    """Depo veya audit altyapısı teknik hatası."""
