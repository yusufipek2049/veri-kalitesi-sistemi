from __future__ import annotations

from io import BytesIO

import pytest

from veri_kalitesi.issues import IssueValidationError
from veri_kalitesi.issues.evidence_files import (
    AllowAllDevelopmentScanner,
    LocalEvidenceStorage,
    detect_media_type,
    extension_matches_media_type,
    sanitize_filename,
)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (b"\x89PNG\r\n\x1a\ncontent", "image/png"),
        (b"\xff\xd8\xffcontent", "image/jpeg"),
        (b"%PDF-1.7\n", "application/pdf"),
        ("güvenli log".encode(), "text/plain"),
        (b"\x00\x01\x02", "application/octet-stream"),
    ],
)
def test_detect_media_type_uses_content_signature(payload: bytes, expected: str) -> None:
    assert detect_media_type(payload) == expected


def test_filename_is_not_used_as_storage_path() -> None:
    safe, extension = sanitize_filename("../../müşteri <kanıt>.PDF")
    assert safe == "m_teri_kan_t.pdf"
    assert extension == ".pdf"
    assert "/" not in safe


def test_extension_must_match_detected_media_type() -> None:
    assert extension_matches_media_type(".log", "text/plain")
    assert not extension_matches_media_type(".jpg", "application/pdf")


def test_local_storage_streams_hashes_and_promotes(tmp_path) -> None:
    storage = LocalEvidenceStorage(tmp_path)
    stored = storage.write_quarantine(BytesIO(b"evidence"), max_bytes=20)
    assert stored.byte_size == 8
    assert stored.object_key.startswith("quarantine/")
    promoted = storage.promote(stored.object_key)
    assert promoted.startswith("available/")
    with storage.open(promoted) as source:
        assert source.read() == b"evidence"


def test_oversized_file_is_removed_before_metadata_can_be_written(tmp_path) -> None:
    storage = LocalEvidenceStorage(tmp_path)
    with pytest.raises(IssueValidationError, match="size limit"):
        storage.write_quarantine(BytesIO(b"too large"), max_bytes=3)
    assert list((tmp_path / "quarantine").iterdir()) == []


def test_development_scanner_rejects_eicar() -> None:
    scanner = AllowAllDevelopmentScanner()
    clean, reason = scanner.scan(BytesIO(b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"))
    assert clean is False
    assert reason == "MALWARE_DETECTED"
