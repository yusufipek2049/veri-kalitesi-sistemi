"""Command-line interface for the local secret scanner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

from veri_kalitesi.secure_sdlc.errors import (
    SecretScanTechnicalError,
    SecretScanValidationError,
)
from veri_kalitesi.secure_sdlc.scanner import RepositorySecretScanner


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    parser = argparse.ArgumentParser(description="Run the local data-minimum secret scan.")
    parser.add_argument("root", nargs="?", default=".", type=Path)
    arguments = parser.parse_args(argv)

    try:
        report = RepositorySecretScanner().scan(arguments.root)
    except SecretScanTechnicalError as exc:
        _write_json(
            error_output,
            {
                "status": "TECHNICAL_ERROR",
                "operation_code": exc.operation_code,
                "relative_path": exc.relative_path,
            },
        )
        return 2
    except SecretScanValidationError as exc:
        _write_json(error_output, {"status": "VALIDATION_ERROR", "reason_code": exc.reason_code})
        return 2

    _write_json(
        output,
        {
            "status": "CLEAN" if report.passed else "FINDINGS",
            "policy_version": report.policy_version,
            "scanned_file_count": report.scanned_file_count,
            "skipped_file_count": report.skipped_file_count,
            "finding_count": len(report.findings),
            "findings": [
                {
                    "relative_path": finding.relative_path,
                    "line_number": finding.line_number,
                    "column_number": finding.column_number,
                    "rule_code": finding.rule_code,
                }
                for finding in report.findings
            ],
        },
    )
    return 0 if report.passed else 1


def _write_json(stream: TextIO, payload: object) -> None:
    stream.write(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    stream.write("\n")
