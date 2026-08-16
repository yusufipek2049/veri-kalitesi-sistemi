"""Secure uploaded-file evidence domain and local storage adapter."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4

from veri_kalitesi.audit.models import AuditEventInput, AuditResult
from veri_kalitesi.identity import ActorContext
from veri_kalitesi.issues.errors import (
    IssueAuthorizationError,
    IssueConflictError,
    IssueNotFoundError,
    IssueValidationError,
)
from veri_kalitesi.issues.evidence import (
    IssueEvidenceKind,
    IssueEvidenceRecord,
    _scope_permitted,
)
from veri_kalitesi.issues.models import DataQualityIssue, IssueStatus


class EvidenceScanStatus(str, Enum):
    UPLOADING = "UPLOADING"
    PENDING_SCAN = "PENDING_SCAN"
    AVAILABLE = "AVAILABLE"
    REJECTED = "REJECTED"
    SCAN_FAILED = "SCAN_FAILED"


class EvidenceClassification(str, Enum):
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


@dataclass(frozen=True)
class EvidenceFilePolicy:
    version: str
    max_bytes: int = 20 * 1024 * 1024
    max_files_per_issue: int = 20
    allowed_extensions: frozenset[str] = frozenset(
        {".png", ".jpg", ".jpeg", ".pdf", ".txt", ".log"}
    )
    allowed_media_types: frozenset[str] = frozenset(
        {"image/png", "image/jpeg", "application/pdf", "text/plain"}
    )


@dataclass(frozen=True)
class IssueEvidenceFileRecord:
    file_id: str
    evidence_id: str
    original_filename: str
    safe_filename: str
    declared_media_type: str | None
    detected_media_type: str
    byte_size: int
    object_key: str
    sha256_digest: str
    scan_status: EvidenceScanStatus
    scan_reason_code: str | None
    scan_completed_at: datetime | None
    classification: EvidenceClassification
    uploaded_by: str
    uploaded_at: datetime
    retention_until: datetime | None = None
    legal_hold: bool = False
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    idempotency_digest: str = ""


@dataclass(frozen=True)
class StoredUpload:
    object_key: str
    byte_size: int
    sha256_digest: str
    prefix: bytes


class EvidenceObjectStorage(Protocol):
    def write_quarantine(self, source: BinaryIO, *, max_bytes: int) -> StoredUpload: ...
    def open(self, object_key: str) -> BinaryIO: ...
    def promote(self, object_key: str) -> str: ...
    def delete(self, object_key: str) -> None: ...


class MalwareScanner(Protocol):
    def scan(self, source: BinaryIO) -> tuple[bool, str | None]: ...


class EvidenceAuditSink(Protocol):
    def append(self, event: AuditEventInput) -> object: ...


class EvidenceFileRepository(Protocol):
    def add_uploaded_evidence(
        self, evidence: IssueEvidenceRecord, file: IssueEvidenceFileRecord
    ) -> tuple[IssueEvidenceRecord, IssueEvidenceFileRecord]: ...
    def get_evidence_file(self, evidence_id: str) -> IssueEvidenceFileRecord | None: ...
    def list_evidence_files(self, issue_id: str) -> list[IssueEvidenceFileRecord]: ...
    def update_evidence_file(self, file: IssueEvidenceFileRecord) -> None: ...
    def evidence_is_referenced(self, evidence_id: str) -> bool: ...


class LocalEvidenceStorage:
    """Non-public, non-executable filesystem storage for development."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.quarantine = self.root / "quarantine"
        self.available = self.root / "available"
        self.quarantine.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.available.mkdir(parents=True, exist_ok=True, mode=0o700)

    def write_quarantine(self, source: BinaryIO, *, max_bytes: int) -> StoredUpload:
        object_key = f"quarantine/{uuid4().hex}"
        target = self._path(object_key)
        digest = hashlib.sha256()
        size = 0
        prefix = bytearray()
        try:
            with target.open("xb") as output:
                os.chmod(target, 0o600)
                while chunk := source.read(64 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise IssueValidationError("File exceeds the configured size limit.")
                    if len(prefix) < 8192:
                        prefix.extend(chunk[: 8192 - len(prefix)])
                    digest.update(chunk)
                    output.write(chunk)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        if size == 0:
            target.unlink(missing_ok=True)
            raise IssueValidationError("Empty files are not accepted.")
        return StoredUpload(object_key, size, digest.hexdigest(), bytes(prefix))

    def open(self, object_key: str) -> BinaryIO:
        return self._path(object_key).open("rb")

    def promote(self, object_key: str) -> str:
        source = self._path(object_key)
        new_key = f"available/{uuid4().hex}"
        shutil.move(str(source), str(self._path(new_key)))
        return new_key

    def delete(self, object_key: str) -> None:
        self._path(object_key).unlink(missing_ok=True)

    def _path(self, object_key: str) -> Path:
        if not re.fullmatch(r"(?:quarantine|available)/[a-f0-9]{32}", object_key):
            raise ValueError("Invalid storage key.")
        path = (self.root / object_key).resolve()
        if self.root not in path.parents:
            raise ValueError("Invalid storage key.")
        return path


class AllowAllDevelopmentScanner:
    """Explicit development-only scanner; production must inject a real adapter."""

    def scan(self, source: BinaryIO) -> tuple[bool, str | None]:
        # EICAR is rejected so security behaviour remains testable without AV.
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            if b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in chunk:
                return False, "MALWARE_DETECTED"
        return True, None


class IssueEvidenceFileService:
    def __init__(
        self,
        *,
        issue_reader: object,
        repository: EvidenceFileRepository,
        authorization_service: object,
        storage: EvidenceObjectStorage,
        scanner: MalwareScanner | None,
        policy: EvidenceFilePolicy | None,
        audit_sink: EvidenceAuditSink | None = None,
        clock: object = None,
    ) -> None:
        self.issue_reader = issue_reader
        self.repository = repository
        self.authorization_service = authorization_service
        self.storage = storage
        self.scanner = scanner
        self.policy = policy
        self.audit_sink = audit_sink
        self.clock = clock

    def upload(
        self,
        *,
        issue_id: str,
        source: BinaryIO,
        original_filename: str,
        declared_media_type: str | None,
        label: str,
        classification: str,
        idempotency_key: str,
        actor_context: ActorContext | None,
    ) -> tuple[IssueEvidenceRecord, IssueEvidenceFileRecord]:
        issue, actor = self._authorized_issue(issue_id, actor_context, mutate=True)
        policy = self._require_policy()
        self._audit(
            actor,
            issue_id,
            None,
            "ISSUE_EVIDENCE_UPLOAD_STARTED",
            AuditResult.SUCCESS,
            "UPLOAD_ACCEPTED",
        )
        if not idempotency_key.strip() or len(idempotency_key) > 200:
            raise IssueValidationError("idempotency_key is invalid.")
        if not label.strip() or len(label) > 200 or "<" in label or ">" in label:
            raise IssueValidationError("Evidence label is invalid.")
        try:
            validated_classification = EvidenceClassification(classification)
        except ValueError as exc:
            raise IssueValidationError("Evidence classification is invalid.") from exc
        idempotency_digest = hashlib.sha256(idempotency_key.encode()).hexdigest()
        for existing in self.repository.list_evidence_files(issue_id):
            if existing.idempotency_digest == idempotency_digest and existing.deleted_at is None:
                evidence = self.repository.get_evidence(existing.evidence_id)  # type: ignore[attr-defined]
                assert evidence is not None
                return evidence, existing
        if (
            len(
                [
                    item
                    for item in self.repository.list_evidence_files(issue_id)
                    if item.deleted_at is None
                ]
            )
            >= policy.max_files_per_issue
        ):
            raise IssueValidationError("Evidence file count limit has been reached.")
        safe_name, extension = sanitize_filename(original_filename)
        if extension not in policy.allowed_extensions:
            raise IssueValidationError("File type is not allowed.")
        stored = self.storage.write_quarantine(source, max_bytes=policy.max_bytes)
        try:
            detected = detect_media_type(stored.prefix)
            normalized_declared = (declared_media_type or "").split(";", 1)[0].strip().lower()
            if detected not in policy.allowed_media_types or (
                normalized_declared
                and normalized_declared not in {detected, "application/octet-stream"}
            ):
                raise IssueValidationError("Declared and detected file types do not match.")
            if not extension_matches_media_type(extension, detected):
                raise IssueValidationError("File extension and content do not match.")
            now = self._now()
            evidence = IssueEvidenceRecord(
                issue_id=issue_id,
                kind=IssueEvidenceKind.UPLOADED_FILE,
                label=(label.strip() or safe_name)[:200],
                execution_id=f"upload:{uuid4()}",
                observed_at=now,
                captured_at=now,
                captured_by=actor.actor_id,
                content_digest=stored.sha256_digest,
                source_digest=hashlib.sha256(f"upload:{idempotency_digest}".encode()).hexdigest(),
            )
            file = IssueEvidenceFileRecord(
                file_id=str(uuid4()),
                evidence_id=evidence.evidence_id,
                original_filename=original_filename[:255],
                safe_filename=safe_name,
                declared_media_type=normalized_declared or None,
                detected_media_type=detected,
                byte_size=stored.byte_size,
                object_key=stored.object_key,
                sha256_digest=stored.sha256_digest,
                scan_status=EvidenceScanStatus.PENDING_SCAN,
                scan_reason_code=None,
                scan_completed_at=None,
                classification=validated_classification,
                uploaded_by=actor.actor_id,
                uploaded_at=now,
                idempotency_digest=idempotency_digest,
            )
            result = self.repository.add_uploaded_evidence(evidence, file)
            if result[1].object_key != stored.object_key:
                self.storage.delete(stored.object_key)
        except Exception:
            self.storage.delete(stored.object_key)
            raise
        self._audit(
            actor,
            issue_id,
            result[0].evidence_id,
            "ISSUE_EVIDENCE_UPLOAD_COMPLETED",
            AuditResult.SUCCESS,
            "PENDING_SCAN",
        )
        return result

    def scan(self, *, evidence_id: str) -> IssueEvidenceFileRecord:
        file = self.repository.get_evidence_file(evidence_id)
        if file is None or file.deleted_at is not None:
            raise IssueValidationError("Evidence file is not available.")
        if file.scan_status is not EvidenceScanStatus.PENDING_SCAN:
            return file
        now = self._now()
        if self.scanner is None:
            updated = _replace_file(
                file,
                scan_status=EvidenceScanStatus.SCAN_FAILED,
                scan_reason_code="SCANNER_UNAVAILABLE",
                scan_completed_at=now,
            )
        else:
            try:
                with self.storage.open(file.object_key) as source:
                    clean, reason = self.scanner.scan(source)
                if clean:
                    key = self.storage.promote(file.object_key)
                    updated = _replace_file(
                        file,
                        object_key=key,
                        scan_status=EvidenceScanStatus.AVAILABLE,
                        scan_reason_code=None,
                        scan_completed_at=now,
                    )
                else:
                    self.storage.delete(file.object_key)
                    updated = _replace_file(
                        file,
                        scan_status=EvidenceScanStatus.REJECTED,
                        scan_reason_code=reason or "MALWARE_DETECTED",
                        scan_completed_at=now,
                    )
            except OSError:
                updated = _replace_file(
                    file,
                    scan_status=EvidenceScanStatus.SCAN_FAILED,
                    scan_reason_code="SCAN_TECHNICAL_ERROR",
                    scan_completed_at=now,
                )
        self.repository.update_evidence_file(updated)
        evidence = self.repository.get_evidence(evidence_id)  # type: ignore[attr-defined]
        if evidence is not None:
            self._audit_system(
                evidence.issue_id,
                evidence_id,
                "ISSUE_EVIDENCE_SCAN_COMPLETED",
                updated.scan_status.value,
                updated.scan_reason_code or updated.scan_status.value,
            )
        return updated

    def authorize_read(
        self, *, issue_id: str, evidence_id: str, actor_context: ActorContext | None
    ) -> IssueEvidenceFileRecord:
        self._authorized_issue(issue_id, actor_context, mutate=False)
        file = self.repository.get_evidence_file(evidence_id)
        evidence = self.repository.get_evidence(evidence_id)  # type: ignore[attr-defined]
        if file is None or evidence is None or evidence.issue_id != issue_id or file.deleted_at:
            raise IssueNotFoundError("Evidence file is not available.")
        return file

    def delete(
        self, *, issue_id: str, evidence_id: str, actor_context: ActorContext | None
    ) -> None:
        _, actor = self._authorized_issue(issue_id, actor_context, mutate=True)
        file = self.authorize_read(
            issue_id=issue_id, evidence_id=evidence_id, actor_context=actor_context
        )
        if file.legal_hold or self.repository.evidence_is_referenced(evidence_id):
            raise IssueConflictError("Evidence used by a resolution cannot be deleted.")
        updated = _replace_file(file, deleted_at=self._now(), deleted_by=actor.actor_id)
        self.repository.update_evidence_file(updated)
        self._audit(
            actor,
            issue_id,
            evidence_id,
            "ISSUE_EVIDENCE_DELETED",
            AuditResult.SUCCESS,
            "SOFT_DELETED",
        )

    def record_download(
        self, *, issue_id: str, evidence_id: str, actor_context: ActorContext
    ) -> None:
        self._audit(
            actor_context,
            issue_id,
            evidence_id,
            "ISSUE_EVIDENCE_DOWNLOADED",
            AuditResult.SUCCESS,
            "AUTHORIZED_DOWNLOAD",
        )

    def _authorized_issue(
        self, issue_id: str, actor: ActorContext | None, *, mutate: bool
    ) -> tuple[DataQualityIssue, ActorContext]:
        if actor is None:
            raise IssueAuthorizationError("Actor cannot access issue evidence.")
        decision = self.authorization_service.authorize_dashboard(actor)  # type: ignore[attr-defined]
        issue = self.issue_reader.get(issue_id)  # type: ignore[attr-defined]
        if not _scope_permitted(issue, decision):
            raise IssueNotFoundError("The requested issue is not available.")
        if mutate:
            if (
                actor.privileged
                or actor.actor_id != issue.assignee_user_id
                or not (actor.roles & {"DATA_STEWARD", "DATA_ENGINEER", "EVIDENCE_MANAGER"})
            ):
                raise IssueAuthorizationError("Actor cannot modify issue evidence.")
            if issue.status in {
                IssueStatus.RESOLVED,
                IssueStatus.VERIFIED,
                IssueStatus.CLOSED,
                IssueStatus.CANCELLED,
            }:
                raise IssueConflictError("Evidence can only be uploaded to an open issue.")
        return issue, actor

    def _require_policy(self) -> EvidenceFilePolicy:
        if self.policy is None or not self.policy.version.strip():
            raise IssueConflictError("Evidence upload policy is unavailable.")
        return self.policy

    def _now(self) -> datetime:
        return self.clock() if callable(self.clock) else datetime.now(timezone.utc)

    def _audit(
        self,
        actor: ActorContext,
        issue_id: str,
        evidence_id: str | None,
        action: str,
        result: AuditResult,
        reason: str,
    ) -> None:
        if self.audit_sink is None:
            raise IssueConflictError("Evidence audit service is unavailable.")
        self.audit_sink.append(
            AuditEventInput(
                actor_id=actor.actor_id,
                actor_type=actor.actor_type.value,
                correlation_id=actor.correlation_id,
                action=action,
                object_type="IssueEvidence",
                object_id=evidence_id,
                result=result,
                reason_code=reason,
                old_values={},
                new_values={"issue_id": issue_id, "evidence_id": evidence_id or ""},
                occurred_at=self._now(),
                session_id=actor.session_id,
            )
        )

    def _audit_system(
        self, issue_id: str, evidence_id: str, action: str, result: str, reason: str
    ) -> None:
        if self.audit_sink is None:
            raise IssueConflictError("Evidence audit service is unavailable.")
        self.audit_sink.append(
            AuditEventInput(
                actor_id="evidence-scanner",
                actor_type="SERVICE",
                correlation_id=evidence_id,
                action=action,
                object_type="IssueEvidence",
                object_id=evidence_id,
                result=AuditResult.SUCCESS if result == "AVAILABLE" else AuditResult.FAILURE,
                reason_code=reason,
                old_values={"scan_status": "PENDING_SCAN"},
                new_values={
                    "issue_id": issue_id,
                    "evidence_id": evidence_id,
                    "scan_status": result,
                },
                occurred_at=self._now(),
            )
        )


def sanitize_filename(filename: str) -> tuple[str, str]:
    base = Path(filename.replace("\\", "/")).name.strip().replace("\x00", "")
    extension = Path(base).suffix.lower()
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(base).stem).strip("._") or "evidence"
    return f"{stem[:220]}{extension}"[:255], extension


def detect_media_type(prefix: bytes) -> str:
    if prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if prefix.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if prefix.startswith(b"%PDF-"):
        return "application/pdf"
    if b"\x00" not in prefix:
        try:
            prefix.decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            pass
    return "application/octet-stream"


def extension_matches_media_type(extension: str, media_type: str) -> bool:
    return extension in {
        "image/png": {".png"},
        "image/jpeg": {".jpg", ".jpeg"},
        "application/pdf": {".pdf"},
        "text/plain": {".txt", ".log"},
    }.get(media_type, set())


def _replace_file(file: IssueEvidenceFileRecord, **changes: object) -> IssueEvidenceFileRecord:
    values = dict(file.__dict__)
    values.update(changes)
    return IssueEvidenceFileRecord(**values)
