"""PostgreSQL lineage/yönetişim/etki kanıtı snapshot repository'si."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping

from sqlalchemy import Column, DateTime, MetaData, String, Table, insert, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import RowMapping

from veri_kalitesi.audit.models import PreparedAuditEvent
from veri_kalitesi.audit.postgresql_outbox import PostgreSQLTransactionalAudit
from veri_kalitesi.lineage.errors import LineageValidationError
from veri_kalitesi.lineage.governance import (
    DataAssetGovernanceProfile,
    governance_profile_from_snapshot,
)
from veri_kalitesi.persistence import (
    DEFAULT_SCHEMA_NAME,
    SessionFactory,
    transactional_session,
)


class LineageSnapshotKind(str, Enum):
    GOVERNANCE_PROFILE = "GOVERNANCE_PROFILE"
    LINEAGE_EVENTS = "LINEAGE_EVENTS"
    IMPACT_ASSESSMENT = "IMPACT_ASSESSMENT"
    ROOT_CAUSE_HYPOTHESIS = "ROOT_CAUSE_HYPOTHESIS"


@dataclass(frozen=True)
class StoredLineageSnapshot:
    snapshot_id: str
    snapshot_kind: str
    subject_ref: str
    version_label: str
    digest: str
    payload: Mapping[str, Any]
    created_at: datetime


def lineage_snapshot_table(schema: str = DEFAULT_SCHEMA_NAME) -> Table:
    return Table(
        "lineage_evidence_snapshots",
        MetaData(schema=schema),
        Column("snapshot_id", String(64), primary_key=True),
        Column("snapshot_kind", String(32), nullable=False),
        Column("subject_ref", String(256), nullable=False),
        Column("version_label", String(128), nullable=False),
        Column("digest", String(71), nullable=False),
        Column("payload", JSONB, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )


class PostgreSQLLineageEvidenceRepository:
    """Snapshot ve audit outbox kaydını aynı transaction'da değişmez yazar."""

    def __init__(
        self, session_factory: SessionFactory, *, schema: str = DEFAULT_SCHEMA_NAME
    ) -> None:
        self._session_factory = session_factory
        self._table = lineage_snapshot_table(schema)

    def add_snapshot(
        self,
        snapshot_kind: LineageSnapshotKind,
        subject_ref: str,
        version_label: str,
        payload: Mapping[str, Any],
        *,
        created_at: datetime,
        audit_event: PreparedAuditEvent,
        audit_outbox: PostgreSQLTransactionalAudit,
    ) -> StoredLineageSnapshot:
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise LineageValidationError("Lineage snapshot created_at must be timezone-aware.")
        if audit_outbox.session_factory is not self._session_factory:
            raise LineageValidationError(
                "Audit outbox must share the lineage snapshot transaction."
            )
        digest = payload.get("digest")
        if not isinstance(digest, str) or not digest.startswith("sha256:"):
            raise LineageValidationError("Lineage snapshot payload must carry a sha256 digest.")
        snapshot = StoredLineageSnapshot(
            snapshot_id=digest.split(":", 1)[1],
            snapshot_kind=snapshot_kind.value,
            subject_ref=subject_ref,
            version_label=version_label,
            digest=digest,
            payload=dict(payload),
            created_at=created_at,
        )
        with transactional_session(self._session_factory) as session:
            existing = (
                session.execute(
                    select(self._table).where(self._table.c.snapshot_id == snapshot.snapshot_id)
                )
                .mappings()
                .one_or_none()
            )
            if existing is not None:
                if dict(existing["payload"]) != dict(snapshot.payload):
                    raise LineageValidationError(
                        "Lineage evidence snapshot is immutable for a digest."
                    )
                return _from_row(existing)
            session.execute(
                insert(self._table).values(
                    snapshot_id=snapshot.snapshot_id,
                    snapshot_kind=snapshot.snapshot_kind,
                    subject_ref=snapshot.subject_ref,
                    version_label=snapshot.version_label,
                    digest=snapshot.digest,
                    payload=dict(snapshot.payload),
                    created_at=snapshot.created_at,
                )
            )
            audit_outbox.stage(audit_event, session=session)
        return snapshot

    def get(self, snapshot_id: str) -> StoredLineageSnapshot | None:
        with transactional_session(self._session_factory) as session:
            row = (
                session.execute(select(self._table).where(self._table.c.snapshot_id == snapshot_id))
                .mappings()
                .one_or_none()
            )
        return _from_row(row) if row is not None else None

    def get_version(
        self,
        snapshot_kind: LineageSnapshotKind,
        subject_ref: str,
        version_label: str,
    ) -> StoredLineageSnapshot | None:
        with transactional_session(self._session_factory) as session:
            row = (
                session.execute(
                    select(self._table).where(
                        self._table.c.snapshot_kind == snapshot_kind.value,
                        self._table.c.subject_ref == subject_ref,
                        self._table.c.version_label == version_label,
                    )
                )
                .mappings()
                .one_or_none()
            )
        return _from_row(row) if row is not None else None


def _from_row(row: RowMapping) -> StoredLineageSnapshot:
    return StoredLineageSnapshot(
        snapshot_id=str(row["snapshot_id"]),
        snapshot_kind=str(row["snapshot_kind"]),
        subject_ref=str(row["subject_ref"]),
        version_label=str(row["version_label"]),
        digest=str(row["digest"]),
        payload=dict(row["payload"]),
        created_at=row["created_at"],
    )


class PostgreSQLGovernanceProfileReader:
    """``GovernanceProfileReader`` protokolünün PostgreSQL uygulaması.

    Yalnız ``GOVERNANCE_PROFILE`` türündeki snapshot'ları okur ve
    ``DataAssetGovernanceProfile`` nesnesine geri dönüştürür.
    Kanıt yoksa boş liste döner; fail-closed davranış korunur.
    """

    def __init__(
        self, session_factory: SessionFactory, *, schema: str = DEFAULT_SCHEMA_NAME
    ) -> None:
        self._session_factory = session_factory
        self._table = lineage_snapshot_table(schema)

    def list_governance_profiles(self, asset_ref: str) -> list[DataAssetGovernanceProfile]:
        with transactional_session(self._session_factory) as session:
            rows = (
                session.execute(
                    select(self._table).where(
                        self._table.c.snapshot_kind == LineageSnapshotKind.GOVERNANCE_PROFILE.value,
                        self._table.c.subject_ref == asset_ref,
                    )
                )
                .mappings()
                .all()
            )
        profiles: list[DataAssetGovernanceProfile] = []
        for row in rows:
            payload = dict(row["payload"])
            try:
                profiles.append(governance_profile_from_snapshot(payload))
            except LineageValidationError:
                continue
        return profiles
