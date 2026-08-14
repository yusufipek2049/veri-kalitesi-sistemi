"""Kalıcı legal-hold geçmişine karşı veri-minimum retention değerlendirme CLI'ı."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
from typing import Sequence, TextIO
import sys

from veri_kalitesi.retention.errors import RetentionError
from veri_kalitesi.retention.models import RetentionRecordClass, RetentionRecordReference
from veri_kalitesi.retention.repository import SQLiteLegalHoldRepository
from veri_kalitesi.retention.service import RetentionEvaluator, provisional_retention_catalog


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Bir kayıt için mevcut politika/hold durumunu salt-okunur değerlendirir."""

    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    parser = argparse.ArgumentParser(description="Evaluate a retention record fail-closed.")
    parser.add_argument("--legal-hold-database", required=True, type=Path)
    parser.add_argument("--record-reference-id", required=True)
    parser.add_argument(
        "--record-class",
        required=True,
        choices=[item.value for item in RetentionRecordClass],
    )
    parser.add_argument("--retention-trigger-at", required=True)
    parser.add_argument("--as-of", required=True)
    arguments = parser.parse_args(argv)
    try:
        repository = SQLiteLegalHoldRepository(str(arguments.legal_hold_database))
        evaluation = RetentionEvaluator(
            provisional_retention_catalog(),
            repository,
        ).evaluate(
            RetentionRecordReference(
                record_reference_id=arguments.record_reference_id,
                record_class=RetentionRecordClass(arguments.record_class),
                retention_trigger_at=datetime.fromisoformat(arguments.retention_trigger_at),
            ),
            as_of=datetime.fromisoformat(arguments.as_of),
        )
    except (RetentionError, ValueError, OSError) as exc:
        _write_json(
            error_output,
            {"status": "BLOCKED", "error_class": type(exc).__name__},
        )
        return 2
    payload = asdict(evaluation)
    # Kayıt referansı operasyonel çıktıda gereksiz kişisel/iş verisi olabilir.
    payload.pop("record_reference_id", None)
    payload["record_class"] = evaluation.record_class.value
    payload["disposition"] = evaluation.disposition.value
    payload["retention_until"] = evaluation.retention_until.isoformat()
    payload["status"] = "EVALUATED"
    _write_json(output, payload)
    return 0


def _write_json(stream: TextIO, payload: object) -> None:
    stream.write(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    stream.write("\n")
