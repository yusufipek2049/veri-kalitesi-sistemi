"""Data-minimum models for local repository secret scanning."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID


DEFAULT_EXCLUDED_DIRECTORIES = frozenset(
    {
        ".cache",
        ".git",
        ".mypy_cache",
        ".nox",
        ".npm",
        ".pnpm-store",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        ".yarn",
        "__pycache__",
        "artifacts",
        "build",
        "dist",
        "node_modules",
        "site-packages",
        "vendor",
        "venv",
    }
)


@dataclass(frozen=True)
class SecretScanPolicy:
    version: str = "28A-v1"
    max_file_size_bytes: int = 1_048_576
    excluded_directories: frozenset[str] = field(
        default_factory=lambda: DEFAULT_EXCLUDED_DIRECTORIES
    )


@dataclass(frozen=True, order=True)
class SecretFinding:
    relative_path: str
    line_number: int
    column_number: int
    rule_code: str


@dataclass(frozen=True)
class SecretScanReport:
    policy_version: str
    scanned_file_count: int
    skipped_file_count: int
    findings: tuple[SecretFinding, ...]

    @property
    def passed(self) -> bool:
        return not self.findings


@dataclass(frozen=True, order=True)
class DeclaredDependency:
    canonical_name: str
    version: str
    environment_marker: str | None = None


@dataclass(frozen=True)
class PythonProjectInventory:
    name: str
    version: str
    requires_python: str
    dependencies: tuple[DeclaredDependency, ...]


class SastSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SastScanStatus(str, Enum):
    COMPLETED = "COMPLETED"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"


@dataclass(frozen=True, order=True)
class SastFinding:
    scanner_id: str
    scanner_version: str
    rule_code: str
    severity: SastSeverity
    relative_path: str
    line_number: int
    column_number: int


@dataclass(frozen=True)
class SastScanReport:
    scanner_id: str
    scanner_version: str
    status: SastScanStatus
    findings: tuple[SastFinding, ...]


@dataclass(frozen=True)
class SastReleaseEvidence:
    project_name: str
    project_version: str
    gate_policy_version: str
    scanner_id: str
    scanner_version: str
    finding_count: int
    critical_finding_count: int
    findings_digest: str


class VulnerabilitySeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DependencyVulnerabilityScanStatus(str, Enum):
    COMPLETED = "COMPLETED"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"


@dataclass(frozen=True, order=True)
class DependencyVulnerabilityFinding:
    scanner_id: str
    scanner_version: str
    advisory_source: str
    advisory_source_version: str
    advisory_id: str
    severity: VulnerabilitySeverity
    dependency_name: str
    dependency_version: str


@dataclass(frozen=True)
class DependencyVulnerabilityScanReport:
    scanner_id: str
    scanner_version: str
    advisory_source: str
    advisory_source_version: str
    status: DependencyVulnerabilityScanStatus
    findings: tuple[DependencyVulnerabilityFinding, ...]


@dataclass(frozen=True)
class DependencyVulnerabilityReleaseEvidence:
    project_name: str
    project_version: str
    gate_policy_version: str
    inventory_scope: str
    dependency_count: int
    dependency_inventory_digest: str
    scanner_id: str
    scanner_version: str
    advisory_source: str
    advisory_source_version: str
    finding_count: int
    critical_finding_count: int
    findings_digest: str


class PentestSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PentestFindingStatus(str, Enum):
    OPEN = "OPEN"
    READY_FOR_RETEST = "READY_FOR_RETEST"
    CLOSED = "CLOSED"


class PentestRetestOutcome(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"


class PentestAssessmentStatus(str, Enum):
    COMPLETED = "COMPLETED"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"


@dataclass(frozen=True)
class PentestFindingRecord:
    assessment_reference: UUID
    finding_reference: UUID
    severity: PentestSeverity
    action_reference: UUID
    responsible_reference: UUID
    status: PentestFindingStatus
    revision: int
    retest_outcome: PentestRetestOutcome | None = None
    retest_evidence_reference: UUID | None = None


@dataclass(frozen=True)
class PentestAssessmentReport:
    assessment_reference: UUID
    status: PentestAssessmentStatus
    findings: tuple[PentestFindingRecord, ...]


@dataclass(frozen=True)
class PentestTrackingEvidence:
    assessment_reference: UUID
    policy_version: str
    finding_count: int
    open_finding_count: int
    ready_for_retest_count: int
    closed_finding_count: int
    unresolved_critical_finding_count: int
    findings_digest: str


class EvidenceTechnicalStatus(str, Enum):
    TECHNICALLY_VERIFIED = "TechnicallyVerified"
    PARTIAL = "Partial"
    MISSING = "Missing"


class EvidenceReviewStatus(str, Enum):
    COMPLIANCE_REVIEW_REQUIRED = "ComplianceReviewRequired"
    APPROVED_BY_BANK = "ApprovedByBank"
    NOT_APPLICABLE = "NotApplicable"


@dataclass(frozen=True)
class ControlEvidenceRecord:
    control_id: str
    technical_status: EvidenceTechnicalStatus
    review_status: EvidenceReviewStatus
    evidence_paths: tuple[str, ...]
    blocker_ids: tuple[str, ...] = ()
    decision_reference: UUID | None = None


@dataclass(frozen=True)
class TechnicalEvidenceCatalog:
    catalog_version: str
    scope: str
    required_control_ids: tuple[str, ...]
    records: tuple[ControlEvidenceRecord, ...]


@dataclass(frozen=True, order=True)
class EvidenceArtifact:
    relative_path: str
    sha256: str


@dataclass(frozen=True)
class ManifestControlRecord:
    control_id: str
    technical_status: EvidenceTechnicalStatus
    review_status: EvidenceReviewStatus
    evidence_artifacts: tuple[EvidenceArtifact, ...]
    blocker_ids: tuple[str, ...]
    decision_reference: UUID | None


@dataclass(frozen=True)
class TechnicalEvidenceManifest:
    schema_version: int
    policy_version: str
    catalog_version: str
    scope: str
    required_control_count: int
    control_count: int
    unique_evidence_artifact_count: int
    technical_status_counts: tuple[tuple[str, int], ...]
    review_status_counts: tuple[tuple[str, int], ...]
    missing_control_ids: tuple[str, ...]
    blocked_control_ids: tuple[str, ...]
    compliance_review_required_control_ids: tuple[str, ...]
    controls: tuple[ManifestControlRecord, ...]
    controls_digest: str


class EvidenceManifestVerificationStatus(str, Enum):
    MATCH = "MATCH"
    DRIFT = "DRIFT"


@dataclass(frozen=True)
class EvidenceManifestVerification:
    policy_version: str
    status: EvidenceManifestVerificationStatus
    stored_manifest_sha256: str
    generated_manifest_sha256: str
