"""Kisisel veri isleme envanteri domain sozlesmesi."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from veri_kalitesi.data_protection.errors import InventoryValidationError
from veri_kalitesi.data_protection.policy import ClassificationCode


_REFERENCE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}")
INVENTORY_REQUIRED_CLASSIFICATIONS = frozenset(
    {
        ClassificationCode.PERSONAL_DATA,
        ClassificationCode.SPECIAL_CATEGORY_PERSONAL_DATA,
    }
)


class InventoryCoverageStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    NO_REQUIRED_FIELDS = "NO_REQUIRED_FIELDS"


@dataclass(frozen=True)
class InventoryCoverageItem:
    data_source_id: str
    dataset_id: str
    data_field_id: str
    classification: ClassificationCode
    inventory_version: int | None
    issue_code: str | None


@dataclass(frozen=True)
class InventoryCoverageReport:
    status: InventoryCoverageStatus
    total_required_count: int
    complete_count: int
    missing_count: int
    items: tuple[InventoryCoverageItem, ...]


@dataclass(frozen=True)
class DataProcessingInventory:
    data_field_id: str
    version_number: int
    processing_purpose: str
    legal_basis_reference: str
    data_owner_id: str
    retention_policy_id: str
    access_role_codes: tuple[str, ...]
    cross_border_transfer: bool
    recipient_groups: tuple[str, ...] = ()
    inventory_id: str = field(default_factory=lambda: str(uuid4()))
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def validate_inventory(inventory: DataProcessingInventory) -> None:
    if inventory.version_number < 1:
        raise InventoryValidationError("Inventory version must be positive.")
    for field_name, value in (
        ("data_field_id", inventory.data_field_id),
        ("processing_purpose", inventory.processing_purpose),
        ("legal_basis_reference", inventory.legal_basis_reference),
        ("data_owner_id", inventory.data_owner_id),
        ("retention_policy_id", inventory.retention_policy_id),
    ):
        _validate_reference(field_name, value)
    _validate_reference_list("access_role_codes", inventory.access_role_codes, required=True)
    _validate_reference_list("recipient_groups", inventory.recipient_groups, required=False)
    if not isinstance(inventory.cross_border_transfer, bool):
        raise InventoryValidationError("cross_border_transfer must be boolean.")
    if inventory.recorded_at.tzinfo is None or inventory.recorded_at.utcoffset() is None:
        raise InventoryValidationError("Inventory time must be timezone-aware.")


def _validate_reference(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not _REFERENCE_PATTERN.fullmatch(value):
        raise InventoryValidationError(f"{field_name} must be a non-secret governance reference.")
    if value.lower().startswith("secret://"):
        raise InventoryValidationError(f"{field_name} must be a non-secret governance reference.")


def _validate_reference_list(field_name: str, values: tuple[str, ...], *, required: bool) -> None:
    if not isinstance(values, tuple) or (required and not values) or len(values) > 50:
        raise InventoryValidationError(f"{field_name} contains invalid references.")
    if len(set(values)) != len(values):
        raise InventoryValidationError(f"{field_name} must not contain duplicates.")
    for value in values:
        _validate_reference(field_name, value)
