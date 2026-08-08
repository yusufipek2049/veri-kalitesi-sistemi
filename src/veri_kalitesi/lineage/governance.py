"""Sürümlü veri varlığı yönetişim profili ve fail-closed routing sözleşmesi.

Kurumsal veri kataloğu sistem-of-record'dur (`OPEN-028`). Bu modül rakip ana
katalog kurmaz: her yönetişim alanı mevcut kanonik yüzeylere **referans** listesi
taşır. Aynı alanı besleyen referanslar çelişirse kazanan uydurulmaz; alan
`CONFLICT` olur ve ikinci bir sahip kaydı doğmaz.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence
from uuid import uuid4

from veri_kalitesi.lineage.errors import LineageValidationError


GOVERNANCE_PROFILE_VERSION = "DQ_ASSET_GOVERNANCE_PROFILE_V1"
SYNTHETIC_REGISTRY_ORIGIN = "SYNTHETIC_GOVERNANCE_REGISTRY"
ENTERPRISE_CATALOG_SYSTEM_OF_RECORD = "ENTERPRISE_DATA_CATALOG"

GOVERNANCE_ATTRIBUTE_KEYS = (
    "data_owner",
    "technical_owner",
    "steward",
    "business_unit",
    "criticality",
    "classification",
    "quality_target",
    "sla",
    "data_risk",
    "retention",
)
OWNER_ATTRIBUTE_KEYS = ("data_owner", "technical_owner", "steward")

_SAFE_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@-]{0,255}")
_SAFE_VALUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@ -]{0,255}")
_SAFE_STATUS = re.compile(r"[A-Z0-9_.:/-]{1,120}")
_SECRET_SCHEMES = ("secret://", "vault://", "token://")


class GovernanceAssetKind(str, Enum):
    DATA_SOURCE = "DATA_SOURCE"
    DATASET = "DATASET"
    DATA_FIELD = "DATA_FIELD"


class GovernanceAttributeStatus(str, Enum):
    REFERENCED = "REFERENCED"
    CONFLICT = "CONFLICT"
    UNKNOWN = "UNKNOWN"


class GovernanceProfileStatus(str, Enum):
    ACTIVE = "ACTIVE"
    NO_ACTIVE_PROFILE = "NO_ACTIVE_PROFILE"
    AMBIGUOUS_EFFECTIVITY = "AMBIGUOUS_EFFECTIVITY"


class RoutingStatus(str, Enum):
    ASSIGNED = "ASSIGNED"
    FAIL_CLOSED = "FAIL_CLOSED"


@dataclass(frozen=True)
class GovernanceReference:
    """Mevcut kanonik yüzeye işaret eden salt okunur referans."""

    source_system: str
    field_path: str
    value: str | None = None


@dataclass(frozen=True)
class AttributeResolution:
    """Bir yönetişim alanını besleyen referansların çözümü."""

    status: GovernanceAttributeStatus
    reference: GovernanceReference | None = None
    conflicting_field_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class DataAssetGovernanceProfile:
    asset_ref: str
    asset_kind: GovernanceAssetKind
    version_number: int
    effective_from: datetime
    effective_to: datetime | None = None
    attributes: Mapping[str, tuple[GovernanceReference, ...]] = field(default_factory=dict)
    related_asset_refs: tuple[str, ...] = ()
    registry_origin: str = SYNTHETIC_REGISTRY_ORIGIN
    system_of_record: str = ENTERPRISE_CATALOG_SYSTEM_OF_RECORD
    profile_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(frozen=True)
class GovernanceRoutingPolicy:
    """Zorunlu routing alanları yalnız aktif politikadan çözülür."""

    version: str
    required_attribute_keys: tuple[str, ...]
    assignee_attribute_key: str


@dataclass(frozen=True)
class GovernanceProfileResolution:
    status: GovernanceProfileStatus
    profile: DataAssetGovernanceProfile | None
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoutingDecision:
    status: RoutingStatus
    assignee_ref: str | None
    policy_version: str | None
    reason_codes: tuple[str, ...] = ()


def build_governance_profile(
    *,
    asset_ref: str,
    asset_kind: GovernanceAssetKind,
    version_number: int,
    effective_from: datetime,
    effective_to: datetime | None = None,
    attributes: Mapping[str, GovernanceReference | Sequence[GovernanceReference]],
    related_asset_refs: Sequence[str] = (),
    registry_origin: str = SYNTHETIC_REGISTRY_ORIGIN,
    profile_id: str | None = None,
) -> DataAssetGovernanceProfile:
    """Sürümlü profili doğrular; hiçbir yönetişim değerini kendisi üretmez."""

    if version_number < 1:
        raise LineageValidationError("Governance profile version must be positive.")
    _require_aware("effective_from", effective_from)
    if effective_to is not None:
        _require_aware("effective_to", effective_to)
        if effective_to <= effective_from:
            raise LineageValidationError("Governance profile effectivity range must be increasing.")
    _require_reference("asset_ref", asset_ref)
    _require_reference("registry_origin", registry_origin)
    unknown_keys = tuple(sorted(set(attributes) - set(GOVERNANCE_ATTRIBUTE_KEYS)))
    if unknown_keys:
        raise LineageValidationError(
            f"Unsupported governance attributes: {', '.join(unknown_keys)}."
        )
    normalized: dict[str, tuple[GovernanceReference, ...]] = {}
    for key, value in attributes.items():
        references = (value,) if isinstance(value, GovernanceReference) else tuple(value)
        if not references:
            raise LineageValidationError(f"{key} must reference at least one canonical surface.")
        for reference in references:
            if not isinstance(reference, GovernanceReference):
                raise LineageValidationError(
                    f"{key} must be a GovernanceReference to an existing surface."
                )
            _require_reference(f"{key}.source_system", reference.source_system)
            _require_reference(f"{key}.field_path", reference.field_path)
            if reference.value is not None:
                _require_value(f"{key}.value", reference.value)
        field_paths = tuple(reference.field_path for reference in references)
        if len(set(field_paths)) != len(field_paths):
            raise LineageValidationError(f"{key} must not reference the same field path twice.")
        normalized[key] = references
    related = tuple(related_asset_refs)
    if len(set(related)) != len(related):
        raise LineageValidationError("related_asset_refs must not contain duplicates.")
    for related_ref in related:
        _require_reference("related_asset_refs", related_ref)
    return DataAssetGovernanceProfile(
        asset_ref=asset_ref,
        asset_kind=asset_kind,
        version_number=version_number,
        effective_from=effective_from,
        effective_to=effective_to,
        attributes=normalized,
        related_asset_refs=related,
        registry_origin=registry_origin,
        profile_id=profile_id or str(uuid4()),
    )


def resolve_active_profile(
    profiles: Iterable[DataAssetGovernanceProfile],
    at: datetime,
) -> GovernanceProfileResolution:
    """Etkinlik aralığı içinde tek sürüm yoksa fail-closed sonuç döner."""

    _require_aware("at", at)
    candidates = tuple(
        profile
        for profile in profiles
        if profile.effective_from <= at
        and (profile.effective_to is None or at < profile.effective_to)
    )
    if not candidates:
        return GovernanceProfileResolution(
            GovernanceProfileStatus.NO_ACTIVE_PROFILE,
            None,
            ("NO_ACTIVE_GOVERNANCE_PROFILE",),
        )
    if len({profile.asset_ref for profile in candidates}) > 1:
        return GovernanceProfileResolution(
            GovernanceProfileStatus.AMBIGUOUS_EFFECTIVITY,
            None,
            ("MULTIPLE_ASSETS_IN_RESOLUTION",),
        )
    if len(candidates) > 1:
        return GovernanceProfileResolution(
            GovernanceProfileStatus.AMBIGUOUS_EFFECTIVITY,
            None,
            ("OVERLAPPING_EFFECTIVITY_RANGE",),
        )
    return GovernanceProfileResolution(GovernanceProfileStatus.ACTIVE, candidates[0], ())


def resolve_attribute_references(
    references: Sequence[GovernanceReference],
) -> AttributeResolution:
    """Çelişen referanslarda kazanan seçmez; `CONFLICT` bildirir."""

    known = tuple(reference for reference in references if reference.value is not None)
    if not known:
        return AttributeResolution(GovernanceAttributeStatus.UNKNOWN)
    if len({reference.value for reference in known}) > 1:
        return AttributeResolution(
            GovernanceAttributeStatus.CONFLICT,
            None,
            tuple(sorted(reference.field_path for reference in known)),
        )
    return AttributeResolution(GovernanceAttributeStatus.REFERENCED, known[0])


def resolve_attribute(
    profile: DataAssetGovernanceProfile,
    key: str,
) -> AttributeResolution:
    return resolve_attribute_references(profile.attributes.get(key, ()))


def governance_profile_snapshot(
    profile: DataAssetGovernanceProfile,
) -> dict[str, Any]:
    """Değişmez, deterministik ve digest'li yönetişim snapshot'ı üretir."""

    document: dict[str, Any] = {
        "profile_contract_version": GOVERNANCE_PROFILE_VERSION,
        "profile_id": profile.profile_id,
        "asset_ref": profile.asset_ref,
        "asset_kind": profile.asset_kind.value,
        "version_number": profile.version_number,
        "effective_from": profile.effective_from.isoformat(),
        "effective_to": (
            profile.effective_to.isoformat() if profile.effective_to is not None else None
        ),
        "registry_origin": profile.registry_origin,
        "system_of_record": profile.system_of_record,
        "related_asset_refs": sorted(profile.related_asset_refs),
        "attributes": {
            key: _attribute_document(profile, key) for key in sorted(profile.attributes)
        },
    }
    document["digest"] = f"sha256:{canonical_digest(document)}"
    return document


def routing_decision(
    profile: DataAssetGovernanceProfile | None,
    policy: GovernanceRoutingPolicy | None,
) -> RoutingDecision:
    """Politika veya zorunlu routing alanı eksikse otomatik atama yapılmaz."""

    if policy is None:
        return RoutingDecision(RoutingStatus.FAIL_CLOSED, None, None, ("MISSING_ROUTING_POLICY",))
    if profile is None:
        return RoutingDecision(
            RoutingStatus.FAIL_CLOSED,
            None,
            policy.version,
            ("NO_ACTIVE_GOVERNANCE_PROFILE",),
        )
    reason_codes: list[str] = []
    if policy.assignee_attribute_key not in policy.required_attribute_keys:
        reason_codes.append("ASSIGNEE_ATTRIBUTE_NOT_REQUIRED_BY_POLICY")
    for key in policy.required_attribute_keys:
        if key not in GOVERNANCE_ATTRIBUTE_KEYS:
            reason_codes.append(f"UNSUPPORTED_ROUTING_ATTRIBUTE_{key.upper()}")
            continue
        resolution = resolve_attribute(profile, key)
        if resolution.status is GovernanceAttributeStatus.CONFLICT:
            reason_codes.append(f"CONFLICTING_{key.upper()}")
        elif resolution.status is GovernanceAttributeStatus.UNKNOWN:
            reason_codes.append(f"MISSING_{key.upper()}")
    if reason_codes:
        return RoutingDecision(
            RoutingStatus.FAIL_CLOSED,
            None,
            policy.version,
            tuple(sorted(set(reason_codes))),
        )
    assignee = resolve_attribute(profile, policy.assignee_attribute_key)
    assert assignee.reference is not None
    return RoutingDecision(RoutingStatus.ASSIGNED, assignee.reference.value, policy.version, ())


def governance_projection(
    resolution: GovernanceProfileResolution,
) -> dict[str, Any]:
    """Kanıt varsa kritik asset/risk/SLA durumunu besler; yoksa `UNKNOWN` bırakır."""

    profile = resolution.profile
    projection: dict[str, Any] = {
        "governance_profile_status": resolution.status.value,
        "governance_reason_codes": list(resolution.reason_codes),
        "governance_version": None,
        "governance_asset_ref": None,
        "critical_asset_status": "UNKNOWN",
        "risk_status": "UNKNOWN",
        "sla_status": "UNKNOWN",
    }
    if profile is None:
        return projection
    projection["governance_version"] = (
        f"{GOVERNANCE_PROFILE_VERSION}:{profile.asset_ref}:{profile.version_number}"
    )
    projection["governance_asset_ref"] = profile.asset_ref
    reason_codes = list(resolution.reason_codes)
    for projection_key, attribute_key in (
        ("critical_asset_status", "criticality"),
        ("risk_status", "data_risk"),
        ("sla_status", "sla"),
    ):
        attribute = resolve_attribute(profile, attribute_key)
        if attribute.status is GovernanceAttributeStatus.CONFLICT:
            reason_codes.append(f"CONFLICTING_{attribute_key.upper()}")
            continue
        if attribute.reference is None or attribute.reference.value is None:
            continue
        projection[projection_key] = _status_token(attribute.reference.value)
    projection["governance_reason_codes"] = sorted(set(reason_codes))
    return projection


def governance_profile_from_snapshot(
    document: Mapping[str, Any],
) -> DataAssetGovernanceProfile:
    """Değişmez snapshot belgesinden ``DataAssetGovernanceProfile`` nesnesine döner."""

    if document.get("profile_contract_version") != GOVERNANCE_PROFILE_VERSION:
        raise LineageValidationError(
            "Snapshot profile_contract_version does not match the supported contract."
        )
    attributes: dict[str, tuple[GovernanceReference, ...]] = {}
    raw_attributes = document.get("attributes")
    if isinstance(raw_attributes, Mapping):
        for key, attr_doc in raw_attributes.items():
            if not isinstance(attr_doc, Mapping):
                continue
            raw_refs = attr_doc.get("references")
            if not isinstance(raw_refs, list):
                continue
            refs = tuple(
                GovernanceReference(
                    source_system=str(ref["source_system"]),
                    field_path=str(ref["field_path"]),
                    value=str(ref["value"]) if ref.get("value") is not None else None,
                )
                for ref in raw_refs
                if isinstance(ref, Mapping)
            )
            if refs:
                attributes[key] = refs
    effective_to_raw = document.get("effective_to")
    return DataAssetGovernanceProfile(
        asset_ref=str(document["asset_ref"]),
        asset_kind=GovernanceAssetKind(str(document["asset_kind"])),
        version_number=int(document["version_number"]),
        effective_from=datetime.fromisoformat(str(document["effective_from"])),
        effective_to=(
            datetime.fromisoformat(str(effective_to_raw)) if effective_to_raw is not None else None
        ),
        attributes=attributes,
        related_asset_refs=tuple(sorted(document.get("related_asset_refs") or ())),
        registry_origin=str(document.get("registry_origin") or SYNTHETIC_REGISTRY_ORIGIN),
        profile_id=str(document.get("profile_id") or ""),
    )


def canonical_digest(document: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        {key: value for key, value in document.items() if key != "digest"},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _attribute_document(
    profile: DataAssetGovernanceProfile,
    key: str,
) -> dict[str, Any]:
    resolution = resolve_attribute(profile, key)
    return {
        "status": resolution.status.value,
        "value": (resolution.reference.value if resolution.reference is not None else None),
        "resolved_field_path": (
            resolution.reference.field_path if resolution.reference is not None else None
        ),
        "conflicting_field_paths": list(resolution.conflicting_field_paths),
        "references": [
            {
                "source_system": reference.source_system,
                "field_path": reference.field_path,
                "value": reference.value,
            }
            for reference in sorted(profile.attributes[key], key=lambda item: item.field_path)
        ],
    }


def _status_token(value: str) -> str:
    normalized = value.strip().upper().replace(" ", "_")
    return normalized if _SAFE_STATUS.fullmatch(normalized) else "UNKNOWN"


def _require_aware(field_name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise LineageValidationError(f"{field_name} must be timezone-aware.")


def _require_reference(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not _SAFE_REFERENCE.fullmatch(value):
        raise LineageValidationError(f"{field_name} must be a non-secret governance reference.")
    _reject_secret(field_name, value)


def _require_value(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not _SAFE_VALUE.fullmatch(value):
        raise LineageValidationError(f"{field_name} must be a non-secret governance value.")
    _reject_secret(field_name, value)


def _reject_secret(field_name: str, value: str) -> None:
    lowered = value.lower()
    if any(lowered.startswith(scheme) for scheme in _SECRET_SCHEMES):
        raise LineageValidationError(f"{field_name} must not carry a secret reference scheme.")
