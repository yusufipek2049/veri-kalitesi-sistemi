"""Data-minimum CSV and JSON serialization for audit exports."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterator

from veri_kalitesi.audit.models import AuditEvent, AuditQueryPage

EXPORT_COLUMNS = (
    "sequence_no",
    "occurred_at",
    "actor_id",
    "actor_type",
    "action",
    "object_type",
    "object_id",
    "result",
    "reason_code",
    "correlation_id",
    "redacted_field_count",
)


class AuditEventExporter:
    """Serialize an audit page without old/new value payloads."""

    def __init__(self, page: AuditQueryPage) -> None:
        self.page = page

    def export(self, export_format: str) -> Iterator[bytes]:
        if export_format == "csv":
            yield self.to_csv().encode("utf-8")
            return
        if export_format == "json":
            yield self.to_json().encode("utf-8")
            return
        raise ValueError("Unsupported audit export format.")

    def to_csv(self) -> str:
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=EXPORT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(_export_row(event) for event in self.page.events)
        return output.getvalue()

    def to_json(self) -> str:
        return json.dumps(
            [_export_row(event) for event in self.page.events],
            ensure_ascii=False,
            separators=(",", ":"),
        )


def _export_row(event: AuditEvent) -> dict[str, object]:
    return {
        "sequence_no": event.sequence_no,
        "occurred_at": event.occurred_at.isoformat(),
        "actor_id": event.actor_id,
        "actor_type": event.actor_type,
        "action": event.action,
        "object_type": event.object_type,
        "object_id": event.object_id,
        "result": event.result.value,
        "reason_code": event.reason_code,
        "correlation_id": event.correlation_id,
        "redacted_field_count": len(event.redacted_fields),
    }
