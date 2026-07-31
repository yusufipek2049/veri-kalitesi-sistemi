"""Sentetik OpenLineage uyumlu sürümlü lineage olayı ve değişmez snapshot'ı.

`OPEN-028` gereği kurumsal veri kataloğu sistem-of-record'dur. Bu modül olayı
üretmez; yetkili kaynaktan gelen run/job/dataset ve kolon ilişkilerini doğrular,
W3C PROV `Entity/Activity/Agent` anlamlarına eşler ve eksik veya eski kapsama
durumunu digest'li snapshot içinde saklar. OpenLineage sürüm/şema referansı
uydurulmaz; olayı sağlayan kaynak taşır.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import re
from typing import Any, Iterable, Sequence

from veri_kalitesi.lineage.errors import LineageValidationError
from veri_kalitesi.lineage.governance import canonical_digest


LINEAGE_EVENT_VERSION = "DQ_LINEAGE_EVENT_V1"
SYNTHETIC_LINEAGE_AUTHORITY = "SYNTHETIC_LINEAGE_REGISTRY"

_SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@=-]{0,255}")
_SAFE_URI = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[A-Za-z0-9._:/@#?=&%-]{1,400}")


class LineageEventType(str, Enum):
    START = "START"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    ABORT = "ABORT"
    FAIL = "FAIL"


class LineageCoverageStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class LineageDatasetRef:
    namespace: str
    name: str

    @property
    def ref(self) -> str:
        return f"{self.namespace}:{self.name}"


@dataclass(frozen=True)
class ColumnLineageEdge:
    output_dataset: LineageDatasetRef
    output_field: str
    input_dataset: LineageDatasetRef
    input_field: str
    transformation_ref: str | None = None


@dataclass(frozen=True)
class LineageEvent:
    event_type: LineageEventType
    event_time: datetime
    run_id: str
    job_namespace: str
    job_name: str
    producer: str
    schema_url: str
    source_authority: str
    observed_at: datetime
    inputs: tuple[LineageDatasetRef, ...] = ()
    outputs: tuple[LineageDatasetRef, ...] = ()
    column_edges: tuple[ColumnLineageEdge, ...] = field(default_factory=tuple)


def validate_lineage_event(event: LineageEvent) -> None:
    _require_aware("event_time", event.event_time)
    _require_aware("observed_at", event.observed_at)
    for field_name, value in (
        ("run_id", event.run_id),
        ("job_namespace", event.job_namespace),
        ("job_name", event.job_name),
        ("source_authority", event.source_authority),
    ):
        _require_name(field_name, value)
    _require_uri("producer", event.producer)
    _require_uri("schema_url", event.schema_url)
    if not event.inputs and not event.outputs:
        raise LineageValidationError(
            "Lineage event must reference at least one dataset."
        )
    for dataset in (*event.inputs, *event.outputs):
        _require_name("dataset.namespace", dataset.namespace)
        _require_name("dataset.name", dataset.name)
    output_refs = {dataset.ref for dataset in event.outputs}
    for edge in event.column_edges:
        _require_name("column_edge.output_field", edge.output_field)
        _require_name("column_edge.input_field", edge.input_field)
        _require_name("column_edge.output_dataset", edge.output_dataset.ref)
        _require_name("column_edge.input_dataset", edge.input_dataset.ref)
        if edge.transformation_ref is not None:
            _require_name("column_edge.transformation_ref", edge.transformation_ref)
        if edge.output_dataset.ref not in output_refs:
            raise LineageValidationError(
                "Column lineage output dataset must be declared as an event output."
            )


def openlineage_document(event: LineageEvent) -> dict[str, Any]:
    """Olayı OpenLineage `RunEvent` alan adlarıyla deterministik belgeye çevirir."""

    validate_lineage_event(event)
    edges_by_output: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for edge in event.column_edges:
        fields = edges_by_output.setdefault(edge.output_dataset.ref, {})
        fields.setdefault(edge.output_field, []).append(
            {
                "namespace": edge.input_dataset.namespace,
                "name": edge.input_dataset.name,
                "field": edge.input_field,
                "transformation": edge.transformation_ref,
            }
        )
    return {
        "eventType": event.event_type.value,
        "eventTime": event.event_time.isoformat(),
        "run": {"runId": event.run_id},
        "job": {"namespace": event.job_namespace, "name": event.job_name},
        "inputs": [_dataset_document(dataset) for dataset in event.inputs],
        "outputs": [
            {
                **_dataset_document(dataset),
                "facets": {
                    "columnLineage": {
                        "fields": {
                            output_field: {
                                "inputFields": sorted(
                                    input_fields,
                                    key=lambda item: (
                                        item["namespace"],
                                        item["name"],
                                        item["field"],
                                    ),
                                )
                            }
                            for output_field, input_fields in sorted(
                                edges_by_output.get(dataset.ref, {}).items()
                            )
                        }
                    }
                }
                if dataset.ref in edges_by_output
                else {},
            }
            for dataset in event.outputs
        ],
        "producer": event.producer,
        "schemaURL": event.schema_url,
        "sourceAuthority": event.source_authority,
        "observedAt": event.observed_at.isoformat(),
        "contractVersion": LINEAGE_EVENT_VERSION,
    }


def prov_mapping(events: Sequence[LineageEvent]) -> dict[str, Any]:
    """Dataset→`Entity`, run→`Activity`, job/producer→`Agent` eşlemesi üretir."""

    entities: set[str] = set()
    activities: set[str] = set()
    agents: set[str] = set()
    used: set[tuple[str, str]] = set()
    generated: set[tuple[str, str]] = set()
    associated: set[tuple[str, str]] = set()
    derived: set[tuple[str, str]] = set()
    for event in events:
        validate_lineage_event(event)
        activity = f"run:{event.run_id}"
        agent = f"job:{event.job_namespace}/{event.job_name}"
        activities.add(activity)
        agents.add(agent)
        agents.add(f"producer:{event.producer}")
        associated.add((activity, agent))
        for dataset in event.inputs:
            entities.add(f"dataset:{dataset.ref}")
            used.add((activity, f"dataset:{dataset.ref}"))
        for dataset in event.outputs:
            entities.add(f"dataset:{dataset.ref}")
            generated.add((f"dataset:{dataset.ref}", activity))
        for edge in event.column_edges:
            entities.add(f"column:{edge.output_dataset.ref}#{edge.output_field}")
            entities.add(f"column:{edge.input_dataset.ref}#{edge.input_field}")
            derived.add(
                (
                    f"column:{edge.output_dataset.ref}#{edge.output_field}",
                    f"column:{edge.input_dataset.ref}#{edge.input_field}",
                )
            )
    return {
        "entities": sorted(entities),
        "activities": sorted(activities),
        "agents": sorted(agents),
        "used": [list(item) for item in sorted(used)],
        "wasGeneratedBy": [list(item) for item in sorted(generated)],
        "wasAssociatedWith": [list(item) for item in sorted(associated)],
        "wasDerivedFrom": [list(item) for item in sorted(derived)],
    }


def lineage_snapshot(
    events: Iterable[LineageEvent],
    *,
    as_of: datetime,
    freshness_limit: timedelta | None,
    freshness_policy_version: str | None = None,
) -> dict[str, Any]:
    """Değişmez digest'li snapshot; eksik veya eski kapsama durumunu saklar."""

    _require_aware("as_of", as_of)
    ordered = sorted(
        tuple(events),
        key=lambda item: (item.event_time, item.run_id, item.event_type.value),
    )
    documents = [openlineage_document(event) for event in ordered]
    status, reason_codes = _coverage(
        ordered,
        as_of=as_of,
        freshness_limit=freshness_limit,
    )
    latest_observed_at = (
        max(event.observed_at for event in ordered) if ordered else None
    )
    document: dict[str, Any] = {
        "snapshot_contract_version": LINEAGE_EVENT_VERSION,
        "as_of": as_of.isoformat(),
        "coverage_status": status.value,
        "coverage_reason_codes": list(reason_codes),
        "freshness_policy_version": freshness_policy_version,
        "freshness_limit_seconds": (
            int(freshness_limit.total_seconds())
            if freshness_limit is not None
            else None
        ),
        "latest_observed_at": (
            latest_observed_at.isoformat() if latest_observed_at is not None else None
        ),
        "run_ids": sorted({event.run_id for event in ordered}),
        "source_authorities": sorted({event.source_authority for event in ordered}),
        "dataset_refs": sorted(
            {
                dataset.ref
                for event in ordered
                for dataset in (*event.inputs, *event.outputs)
            }
        ),
        "column_edge_count": sum(len(event.column_edges) for event in ordered),
        "events": documents,
        "prov": prov_mapping(ordered),
    }
    document["digest"] = f"sha256:{canonical_digest(document)}"
    return document


def upstream_dataset_refs(
    snapshot: dict[str, Any],
    dataset_ref: str,
) -> tuple[str, ...]:
    """Snapshot kanıtına göre bir dataset'in doğrudan upstream referansları."""

    return _neighbours(snapshot, dataset_ref, upstream=True)


def downstream_dataset_refs(
    snapshot: dict[str, Any],
    dataset_ref: str,
) -> tuple[str, ...]:
    """Snapshot kanıtına göre bir dataset'in doğrudan downstream referansları."""

    return _neighbours(snapshot, dataset_ref, upstream=False)


def _neighbours(
    snapshot: dict[str, Any],
    dataset_ref: str,
    *,
    upstream: bool,
) -> tuple[str, ...]:
    found: set[str] = set()
    for document in snapshot.get("events", ()):
        inputs = {
            f"{item['namespace']}:{item['name']}" for item in document.get("inputs", ())
        }
        outputs = {
            f"{item['namespace']}:{item['name']}"
            for item in document.get("outputs", ())
        }
        if upstream and dataset_ref in outputs:
            found |= inputs
        if not upstream and dataset_ref in inputs:
            found |= outputs
    found.discard(dataset_ref)
    return tuple(sorted(found))


def _coverage(
    events: Sequence[LineageEvent],
    *,
    as_of: datetime,
    freshness_limit: timedelta | None,
) -> tuple[LineageCoverageStatus, tuple[str, ...]]:
    reason_codes: list[str] = []
    if not events:
        reason_codes.append("NO_LINEAGE_EVENT")
    if freshness_limit is None:
        reason_codes.append("MISSING_FRESHNESS_POLICY")
    if not events or freshness_limit is None:
        return LineageCoverageStatus.UNKNOWN, tuple(sorted(set(reason_codes)))
    if freshness_limit <= timedelta(0):
        return (
            LineageCoverageStatus.UNKNOWN,
            ("INVALID_FRESHNESS_POLICY",),
        )
    latest_observed_at = max(event.observed_at for event in events)
    stale = as_of - latest_observed_at > freshness_limit
    if stale:
        reason_codes.append("STALE_LINEAGE_COVERAGE")
    incomplete = False
    for event in events:
        covered_outputs = {edge.output_dataset.ref for edge in event.column_edges}
        if any(dataset.ref not in covered_outputs for dataset in event.outputs):
            reason_codes.append("MISSING_COLUMN_LINEAGE")
            incomplete = True
        declared_inputs = {dataset.ref for dataset in event.inputs}
        if any(
            edge.input_dataset.ref not in declared_inputs
            for edge in event.column_edges
        ):
            reason_codes.append("UNDECLARED_INPUT_DATASET")
            incomplete = True
    codes = tuple(sorted(set(reason_codes)))
    if stale:
        return LineageCoverageStatus.STALE, codes
    if incomplete:
        return LineageCoverageStatus.INCOMPLETE, codes
    return LineageCoverageStatus.COMPLETE, codes


def _dataset_document(dataset: LineageDatasetRef) -> dict[str, Any]:
    return {"namespace": dataset.namespace, "name": dataset.name}


def _require_aware(field_name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise LineageValidationError(f"{field_name} must be timezone-aware.")


def _require_name(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not _SAFE_NAME.fullmatch(value):
        raise LineageValidationError(f"{field_name} must be a safe lineage reference.")


def _require_uri(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not _SAFE_URI.fullmatch(value):
        raise LineageValidationError(f"{field_name} must be a source-provided URI.")
