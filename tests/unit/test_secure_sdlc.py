"""BFR-SDLC-001/002 and NFR-SEC-005/012 local secret scan tests."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest

from veri_kalitesi.secure_sdlc import (
    RepositorySecretScanner,
    SecretScanPolicy,
    SecretScanTechnicalError,
    SecretScanValidationError,
)
from veri_kalitesi.secure_sdlc.cli import main


def test_detects_supported_rules_without_retaining_secret_values(tmp_path: Path) -> None:
    sensitive_value = "Bank-Test-Value-48291"
    source = "\n".join(
        (
            "pass" + f'word = "{sensitive_value}"',
            "-----BEGIN " + "PRIVATE KEY-----",
            "AKIA" + "A1B2C3D4E5F6G7H8",
            "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1L2",
        )
    )
    (tmp_path / "settings.txt").write_text(source, encoding="utf-8")

    report = RepositorySecretScanner().scan(tmp_path)

    assert [finding.rule_code for finding in report.findings] == [
        "HARDCODED_SECRET_ASSIGNMENT",
        "PRIVATE_KEY_MATERIAL",
        "CLOUD_ACCESS_KEY_ID",
        "SOURCE_CONTROL_TOKEN",
    ]
    assert sensitive_value not in repr(report)
    assert all(finding.relative_path == "settings.txt" for finding in report.findings)


@pytest.mark.parametrize(
    "value",
    (
        "secret://synthetic/application",
        "${APP_PASSWORD}",
        "vault:synthetic/path",
        "placeholder",
        "not-real",
    ),
)
def test_ignores_approved_references_and_placeholders(tmp_path: Path, value: str) -> None:
    (tmp_path / "safe.env").write_text("to" + f'ken = "{value}"', encoding="utf-8")

    report = RepositorySecretScanner().scan(tmp_path)

    assert report.passed
    assert report.scanned_file_count == 1


def test_excludes_generated_binary_large_and_linked_files(tmp_path: Path) -> None:
    (tmp_path / "safe.txt").write_text("ordinary content", encoding="utf-8")
    generated = tmp_path / "node_modules"
    generated.mkdir()
    (generated / "generated.txt").write_text(
        "pass" + 'word = "Generated-Value-48291"', encoding="utf-8"
    )
    (tmp_path / "binary.bin").write_bytes(b"prefix\x00suffix")
    (tmp_path / "large.txt").write_text("x" * 33, encoding="utf-8")
    outside = tmp_path.parent / "outside-secret-scan.txt"
    outside.write_text("pass" + 'word = "Outside-Value-48291"', encoding="utf-8")
    link = tmp_path / "linked.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlinks are not available on this platform")

    report = RepositorySecretScanner(SecretScanPolicy(max_file_size_bytes=32)).scan(tmp_path)

    assert report.passed
    assert report.scanned_file_count == 1
    assert report.skipped_file_count == 3


def test_scan_is_read_only(tmp_path: Path) -> None:
    source = tmp_path / "application.conf"
    source.write_text("pass" + 'word = "Read-Only-Value-48291"', encoding="utf-8")
    before = (source.read_bytes(), source.stat().st_mtime_ns, source.stat().st_mode)

    RepositorySecretScanner().scan(tmp_path)

    after = (source.read_bytes(), source.stat().st_mtime_ns, source.stat().st_mode)
    assert after == before


def test_findings_are_deterministically_ordered(tmp_path: Path) -> None:
    (tmp_path / "z.txt").write_text("pass" + 'word = "Z-Value-48291"', encoding="utf-8")
    (tmp_path / "a.txt").write_text("to" + 'ken = "A-Value-48291"', encoding="utf-8")

    report = RepositorySecretScanner().scan(tmp_path)

    assert [finding.relative_path for finding in report.findings] == ["a.txt", "z.txt"]


def test_rejects_invalid_policy_and_scan_roots(tmp_path: Path) -> None:
    with pytest.raises(SecretScanValidationError, match="MAX_FILE_SIZE_INVALID"):
        RepositorySecretScanner(SecretScanPolicy(max_file_size_bytes=0))
    with pytest.raises(SecretScanValidationError, match="SCAN_ROOT_NOT_FOUND"):
        RepositorySecretScanner().scan(tmp_path / "missing")
    file_root = tmp_path / "file.txt"
    file_root.write_text("content", encoding="utf-8")
    with pytest.raises(SecretScanValidationError, match="SCAN_ROOT_NOT_DIRECTORY"):
        RepositorySecretScanner().scan(file_root)


def test_read_failure_is_a_safe_technical_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "unreadable.txt"
    source.write_text("content", encoding="utf-8")
    original_read_bytes = Path.read_bytes

    def fail_selected_file(path: Path) -> bytes:
        if path == source:
            raise OSError("sensitive operating system detail")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fail_selected_file)

    with pytest.raises(SecretScanTechnicalError) as exc_info:
        RepositorySecretScanner().scan(tmp_path)

    assert exc_info.value.operation_code == "FILE_READ_FAILED"
    assert exc_info.value.relative_path == "unreadable.txt"
    assert "sensitive operating system detail" not in str(exc_info.value)


def test_cli_reports_findings_without_exposing_values(tmp_path: Path) -> None:
    sensitive_value = "Cli-Value-48291"
    (tmp_path / "config.ini").write_text("api_" + f'key = "{sensitive_value}"', encoding="utf-8")
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main([str(tmp_path)], stdout=stdout, stderr=stderr)
    payload = json.loads(stdout.getvalue())

    assert exit_code == 1
    assert payload["status"] == "FINDINGS"
    assert payload["finding_count"] == 1
    assert payload["findings"] == [
        {
            "column_number": 1,
            "line_number": 1,
            "relative_path": "config.ini",
            "rule_code": "HARDCODED_SECRET_ASSIGNMENT",
        }
    ]
    assert sensitive_value not in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_cli_distinguishes_clean_and_validation_results(tmp_path: Path) -> None:
    (tmp_path / "safe.txt").write_text("safe", encoding="utf-8")
    clean_output = StringIO()
    error_output = StringIO()

    assert main([str(tmp_path)], stdout=clean_output, stderr=error_output) == 0
    assert json.loads(clean_output.getvalue())["status"] == "CLEAN"
    assert main([str(tmp_path / "missing")], stdout=StringIO(), stderr=error_output) == 2
    assert json.loads(error_output.getvalue())["status"] == "VALIDATION_ERROR"
