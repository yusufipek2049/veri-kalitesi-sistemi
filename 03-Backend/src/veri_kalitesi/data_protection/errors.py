"""Veri koruma politika hatalari."""


class DataProtectionError(Exception):
    """Veri koruma temel hatasi."""


class ClassificationValidationError(DataProtectionError):
    """Onayli siniflandirma sozlugu disindaki deger."""


class InventoryValidationError(DataProtectionError):
    """Kisisel veri isleme envanteri dogrulamasi basarisiz."""


class InventoryCoverageTechnicalError(DataProtectionError):
    """Isleme envanteri kapsam raporu teknik nedenle okunamadi."""
