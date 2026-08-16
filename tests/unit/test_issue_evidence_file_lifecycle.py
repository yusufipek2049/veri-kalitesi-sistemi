"""F-08: Yuklenen dosya kaniti icin uctan uca yasam dongusu testleri.

Denetim, upload/download yuzeyinin (backend coverage %58) test edilmedigini
tespit etti. Buradaki testler gercek ``LocalEvidenceStorage`` ile calisir ve
su davranislari kanitlar:

* yukleme karantinaya yazar ve dosyayi PENDING_SCAN birakir,
* yalniz temiz cikan dosya AVAILABLE olup indirilebilir,
* tarayici yapilandirilmamissa akis fail-closed kalir (F-04),
* zararli dosya REJECTED olur ve depodan silinir,
* idempotency anahtari tekrarli yuklemede yeni kayit uretmez,
* kapsam disi veya yetkisiz aktor veri sizdirmayan hata alir.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest

from veri_kalitesi.identity import (
    ActorContext,
    ActorContextIssuer,
    ActorType,
    DashboardAuthorizationDecision,
)
from veri_kalitesi.issues import (
    DataQualityIssue,
    IssueAuthorizationError,
    IssueNotFoundError,
    IssuePriority,
    IssueScopeType,
    IssueSourceEventType,
    IssueStatus,
    IssueTriggerType,
    IssueValidationError,
)
from veri_kalitesi.issues.evidence_files import (
    AllowAllDevelopmentScanner,
    EvidenceFilePolicy,
    EvidenceScanStatus,
    IssueEvidenceFileService,
    LocalEvidenceStorage,
)

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "EVIDENCE_FILE_TEST_V1"
ISSUE_ID = "issue-upload-001"
DATASET_ID = "dataset-a"
ASSIGNEE = "steward-1"

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"payload-bytes" * 8
EICAR_BYTES = b"%PDF-1.7\nEICAR-STANDARD-ANTIVIRUS-TEST-FILE!\n"


def _issue(status: IssueStatus = IssueStatus.INVESTIGATING) -> DataQualityIssue:
    return DataQualityIssue(
        issue_id=ISSUE_ID,
        issue_no="DQI-UPLOAD-1",
        source_event_id="source-event-1",
        source_event_type=IssueSourceEventType.QUALITY,
        trigger_type=IssueTriggerType.QUALITY_THRESHOLD,
        scope_type=IssueScopeType.DATASET,
        scope_id=DATASET_ID,
        status=status,
        priority=IssuePriority.HIGH,
        assignee_user_id=ASSIGNEE,
        deduplication_key_digest="sha256:dedup",
        occurrence_count=1,
        created_at=NOW - timedelta(days=1),
        updated_at=NOW,
        last_seen_at=NOW,
    )


class FakeIssueReader:
    def __init__(self, issue: DataQualityIssue) -> None:
        self.issue = issue

    def get(self, issue_id: str) -> DataQualityIssue:
        if issue_id != self.issue.issue_id:
            raise IssueNotFoundError("Issue not found.")
        return self.issue


class FakeAuthorization:
    def __init__(self, dataset_ids: frozenset[str] = frozenset({DATASET_ID})) -> None:
        self._dataset_ids = dataset_ids

    def authorize_dashboard(self, context: ActorContext | None) -> DashboardAuthorizationDecision:
        permitted = (
            self._dataset_ids & context.permitted_dataset_ids
            if context is not None
            else frozenset()
        )
        return DashboardAuthorizationDecision(
            permitted_source_ids=frozenset(),
            permitted_dataset_ids=permitted,
            can_view_enterprise=False,
            policy_version=POLICY_VERSION,
        )


class FakeEvidenceRepository:
    """issue_evidence + issue_evidence_files ikilisinin bellekte karsiligi."""

    def __init__(self) -> None:
        self.evidence: dict[str, object] = {}
        self.files: dict[str, object] = {}
        self.referenced: set[str] = set()

    def add_uploaded_evidence(self, evidence, file):
        self.evidence[evidence.evidence_id] = evidence
        self.files[file.evidence_id] = file
        return evidence, file

    def get_evidence(self, evidence_id: str):
        return self.evidence.get(evidence_id)

    def get_evidence_file(self, evidence_id: str):
        return self.files.get(evidence_id)

    def list_evidence_files(self, issue_id: str) -> list:
        return [
            file
            for file in self.files.values()
            if self.evidence[file.evidence_id].issue_id == issue_id
        ]

    def update_evidence_file(self, file) -> None:
        self.files[file.evidence_id] = file

    def evidence_is_referenced(self, evidence_id: str) -> bool:
        return evidence_id in self.referenced


class RecordingAuditSink:
    def __init__(self) -> None:
        self.events: list = []

    def append(self, event) -> object:
        self.events.append(event)
        return event

    def actions(self) -> list[str]:
        return [event.action for event in self.events]


def _actor(
    actor_id: str = ASSIGNEE,
    *,
    roles: set[str] | None = None,
    dataset_ids: set[str] | None = None,
    privileged: bool = False,
) -> ActorContext:
    return ActorContextIssuer().issue(
        actor_id=actor_id,
        actor_type=ActorType.USER,
        authentication_source="test-idp",
        session_id=f"session-{actor_id}",
        roles=frozenset(roles or {"DATA_STEWARD"}),
        permitted_source_ids=frozenset(),
        permitted_dataset_ids=frozenset(dataset_ids or {DATASET_ID}),
        can_view_enterprise=False,
        privileged=privileged,
        issued_at=NOW - timedelta(minutes=5),
        expires_at=NOW + timedelta(hours=1),
        policy_version=POLICY_VERSION,
        correlation_id="evidence-upload-test",
    )


def _service(
    tmp_path,
    *,
    scanner=None,
    issue: DataQualityIssue | None = None,
    repository: FakeEvidenceRepository | None = None,
    audit: RecordingAuditSink | None = None,
) -> IssueEvidenceFileService:
    return IssueEvidenceFileService(
        issue_reader=FakeIssueReader(issue or _issue()),
        repository=repository or FakeEvidenceRepository(),
        authorization_service=FakeAuthorization(),
        storage=LocalEvidenceStorage(tmp_path / "evidence"),
        scanner=scanner,
        policy=EvidenceFilePolicy(version=POLICY_VERSION),
        # Audit sink zorunlu: yoksa servis fail-closed davranir.
        audit_sink=audit or RecordingAuditSink(),
        clock=lambda: NOW,
    )


def _upload(service, *, payload: bytes = PNG_BYTES, filename: str = "kanit.png", key: str = "k-1"):
    return service.upload(
        issue_id=ISSUE_ID,
        source=BytesIO(payload),
        original_filename=filename,
        declared_media_type="image/png",
        label="Ekran goruntusu",
        classification="INTERNAL",
        idempotency_key=key,
        actor_context=_actor(),
    )


# ----------------------------------------------------------------------
# Mutlu yol: upload -> scan -> download
# ----------------------------------------------------------------------


def test_upload_quarantines_file_as_pending_scan(tmp_path) -> None:
    service = _service(tmp_path)

    _evidence, file = _upload(service)

    assert file.scan_status is EvidenceScanStatus.PENDING_SCAN
    assert file.object_key.startswith("quarantine/")
    assert file.detected_media_type == "image/png"
    assert file.byte_size == len(PNG_BYTES)


def test_clean_file_becomes_available_and_downloadable(tmp_path) -> None:
    audit = RecordingAuditSink()
    service = _service(tmp_path, scanner=AllowAllDevelopmentScanner(), audit=audit)
    evidence, _file = _upload(service)

    scanned = service.scan(evidence_id=evidence.evidence_id)

    assert scanned.scan_status is EvidenceScanStatus.AVAILABLE
    assert scanned.object_key.startswith("available/")
    assert scanned.scan_completed_at == NOW

    metadata = service.authorize_read(
        issue_id=ISSUE_ID, evidence_id=evidence.evidence_id, actor_context=_actor()
    )
    with service.storage.open(metadata.object_key) as handle:
        assert handle.read() == PNG_BYTES

    service.record_download(
        issue_id=ISSUE_ID, evidence_id=evidence.evidence_id, actor_context=_actor()
    )
    assert "ISSUE_EVIDENCE_UPLOAD_COMPLETED" in audit.actions()


# ----------------------------------------------------------------------
# Fail-closed davranislar
# ----------------------------------------------------------------------


def test_without_a_scanner_the_file_never_becomes_available(tmp_path) -> None:
    """F-04: Tarayici bagli degilse akis fail-closed kalir."""

    service = _service(tmp_path, scanner=None)
    evidence, _file = _upload(service)

    scanned = service.scan(evidence_id=evidence.evidence_id)

    assert scanned.scan_status is EvidenceScanStatus.SCAN_FAILED
    assert scanned.scan_reason_code == "SCANNER_UNAVAILABLE"
    assert scanned.object_key.startswith("quarantine/")


def test_infected_file_is_rejected_and_removed_from_storage(tmp_path) -> None:
    service = _service(tmp_path, scanner=AllowAllDevelopmentScanner())
    evidence, file = service.upload(
        issue_id=ISSUE_ID,
        source=BytesIO(EICAR_BYTES),
        original_filename="zararli.pdf",
        declared_media_type="application/pdf",
        label="Supheli dosya",
        classification="INTERNAL",
        idempotency_key="k-eicar",
        actor_context=_actor(),
    )

    scanned = service.scan(evidence_id=evidence.evidence_id)

    assert scanned.scan_status is EvidenceScanStatus.REJECTED
    assert scanned.scan_reason_code == "MALWARE_DETECTED"
    with pytest.raises(OSError):
        service.storage.open(file.object_key)


def test_scan_is_idempotent_after_a_terminal_verdict(tmp_path) -> None:
    service = _service(tmp_path, scanner=AllowAllDevelopmentScanner())
    evidence, _file = _upload(service)
    first = service.scan(evidence_id=evidence.evidence_id)

    second = service.scan(evidence_id=evidence.evidence_id)

    assert second.object_key == first.object_key
    assert second.scan_status is EvidenceScanStatus.AVAILABLE


# ----------------------------------------------------------------------
# Dogrulama ve yetkilendirme
# ----------------------------------------------------------------------


def test_repeated_idempotency_key_returns_the_existing_file(tmp_path) -> None:
    repository = FakeEvidenceRepository()
    service = _service(tmp_path, repository=repository)

    _evidence, first = _upload(service, key="same-key")
    _evidence2, second = _upload(service, key="same-key")

    assert first.file_id == second.file_id
    assert len(repository.files) == 1


def test_extension_content_mismatch_is_rejected_and_leaves_no_orphan(tmp_path) -> None:
    service = _service(tmp_path)

    with pytest.raises(IssueValidationError):
        _upload(service, payload=PNG_BYTES, filename="kanit.pdf", key="k-mismatch")

    quarantine = tmp_path / "evidence" / "quarantine"
    assert list(quarantine.iterdir()) == []


def test_disallowed_extension_is_rejected(tmp_path) -> None:
    service = _service(tmp_path)

    with pytest.raises(IssueValidationError, match="File type is not allowed"):
        _upload(service, filename="kanit.exe", key="k-exe")


def test_actor_outside_dataset_scope_gets_not_found(tmp_path) -> None:
    service = _service(tmp_path)

    with pytest.raises(IssueNotFoundError):
        service.upload(
            issue_id=ISSUE_ID,
            source=BytesIO(PNG_BYTES),
            original_filename="kanit.png",
            declared_media_type="image/png",
            label="Ekran goruntusu",
            classification="INTERNAL",
            idempotency_key="k-scope",
            actor_context=_actor(dataset_ids={"other-dataset"}),
        )


def test_non_assignee_cannot_upload(tmp_path) -> None:
    service = _service(tmp_path)

    with pytest.raises(IssueAuthorizationError):
        service.upload(
            issue_id=ISSUE_ID,
            source=BytesIO(PNG_BYTES),
            original_filename="kanit.png",
            declared_media_type="image/png",
            label="Ekran goruntusu",
            classification="INTERNAL",
            idempotency_key="k-other",
            actor_context=_actor("someone-else"),
        )


def test_upload_to_a_closed_issue_is_rejected(tmp_path) -> None:
    service = _service(tmp_path, issue=_issue(status=IssueStatus.CLOSED))

    with pytest.raises(Exception) as excinfo:
        _upload(service, key="k-closed")
    assert "open issue" in str(excinfo.value)


def test_deleted_file_is_no_longer_readable(tmp_path) -> None:
    service = _service(tmp_path, scanner=AllowAllDevelopmentScanner())
    evidence, _file = _upload(service)
    service.scan(evidence_id=evidence.evidence_id)

    service.delete(issue_id=ISSUE_ID, evidence_id=evidence.evidence_id, actor_context=_actor())

    with pytest.raises(IssueNotFoundError):
        service.authorize_read(
            issue_id=ISSUE_ID, evidence_id=evidence.evidence_id, actor_context=_actor()
        )


def test_evidence_used_by_a_resolution_cannot_be_deleted(tmp_path) -> None:
    repository = FakeEvidenceRepository()
    service = _service(tmp_path, repository=repository, scanner=AllowAllDevelopmentScanner())
    evidence, _file = _upload(service)
    repository.referenced.add(evidence.evidence_id)

    with pytest.raises(Exception) as excinfo:
        service.delete(issue_id=ISSUE_ID, evidence_id=evidence.evidence_id, actor_context=_actor())
    assert "resolution" in str(excinfo.value)
