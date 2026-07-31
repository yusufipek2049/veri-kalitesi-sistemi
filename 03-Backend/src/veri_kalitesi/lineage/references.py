"""Mevcut sahiplik/sınıflandırma/saklama yüzeylerine salt okunur referans üretimi.

Bu adaptörler değer kopyalamaz; sürümlü yönetişim profiline hangi kanonik alanın
okunduğunu (`source_system` + `field_path`) taşır. Böylece profil ikinci bir
sahip kaydı oluşturmaz.
"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from veri_kalitesi.data_protection.inventory import DataProcessingInventory
from veri_kalitesi.data_sources.models import DataField, DataSource, Dataset
from veri_kalitesi.lineage.governance import (
    GovernanceAssetKind,
    GovernanceReference,
    build_governance_profile,
    DataAssetGovernanceProfile,
)
from veri_kalitesi.retention.models import RetentionPolicy


DATA_SOURCES_SYSTEM = "VERI_KALITESI_DATA_SOURCES"
DATA_PROTECTION_SYSTEM = "VERI_KALITESI_DATA_PROTECTION"
RETENTION_SYSTEM = "VERI_KALITESI_RETENTION"


def data_source_owner_reference(source: DataSource) -> GovernanceReference:
    return GovernanceReference(
        source_system=DATA_SOURCES_SYSTEM,
        field_path="data_sources.DataSource.owner_user_id",
        value=source.owner_user_id,
    )


def dataset_owner_reference(dataset: Dataset) -> GovernanceReference:
    return GovernanceReference(
        source_system=DATA_SOURCES_SYSTEM,
        field_path="data_sources.Dataset.owner_user_id",
        value=dataset.owner_user_id,
    )


def dataset_criticality_reference(dataset: Dataset) -> GovernanceReference:
    return GovernanceReference(
        source_system=DATA_SOURCES_SYSTEM,
        field_path="data_sources.Dataset.criticality",
        value=dataset.criticality.value,
    )


def data_field_classification_reference(data_field: DataField) -> GovernanceReference:
    return GovernanceReference(
        source_system=DATA_SOURCES_SYSTEM,
        field_path="data_sources.DataField.classification",
        value=data_field.classification.value,
    )


def inventory_owner_reference(
    inventory: DataProcessingInventory,
) -> GovernanceReference:
    return GovernanceReference(
        source_system=DATA_PROTECTION_SYSTEM,
        field_path="data_protection.DataProcessingInventory.data_owner_id",
        value=inventory.data_owner_id,
    )


def inventory_retention_reference(
    inventory: DataProcessingInventory,
) -> GovernanceReference:
    return GovernanceReference(
        source_system=DATA_PROTECTION_SYSTEM,
        field_path="data_protection.DataProcessingInventory.retention_policy_id",
        value=inventory.retention_policy_id,
    )


def retention_policy_reference(policy: RetentionPolicy) -> GovernanceReference:
    return GovernanceReference(
        source_system=RETENTION_SYSTEM,
        field_path="retention.RetentionPolicy.code",
        value=f"{policy.code}:{policy.version}",
    )


def unknown_reference(source_system: str, field_path: str) -> GovernanceReference:
    """Kanonik yüzeyi olmayan alan `UNKNOWN` referansı olarak taşınır."""

    return GovernanceReference(
        source_system=source_system,
        field_path=field_path,
        value=None,
    )


def build_governance_profile_from_sources(
    *,
    dataset: Dataset,
    data_source: DataSource | None = None,
    inventory: DataProcessingInventory | None = None,
    retention_policy: RetentionPolicy | None = None,
    version_number: int,
    effective_from: datetime,
    effective_to: datetime | None = None,
    related_asset_refs: Sequence[str] = (),
    profile_id: str | None = None,
) -> DataAssetGovernanceProfile:
    """Mevcut kanonik yüzeylerden sürümlü yönetişim profili üretir.

    Hiçbir sahiplik değerini kopyalamaz; her alan ilgili yüzeye
    ``GovernanceReference`` ile bağlanır. Çelişen ikinci sahip kaydı üretilmez.
    """

    attributes: dict[str, GovernanceReference | Sequence[GovernanceReference]] = {}
    owner_refs: list[GovernanceReference] = [dataset_owner_reference(dataset)]
    if data_source is not None:
        owner_refs.append(data_source_owner_reference(data_source))
    if inventory is not None:
        owner_refs.append(inventory_owner_reference(inventory))
    attributes["data_owner"] = tuple(owner_refs)
    attributes["criticality"] = dataset_criticality_reference(dataset)
    if inventory is not None:
        attributes["retention"] = inventory_retention_reference(inventory)
    if retention_policy is not None:
        attributes["retention"] = retention_policy_reference(retention_policy)
    return build_governance_profile(
        asset_ref=dataset.dataset_id,
        asset_kind=GovernanceAssetKind.DATASET,
        version_number=version_number,
        effective_from=effective_from,
        effective_to=effective_to,
        attributes=attributes,
        related_asset_refs=related_asset_refs,
        profile_id=profile_id,
    )
