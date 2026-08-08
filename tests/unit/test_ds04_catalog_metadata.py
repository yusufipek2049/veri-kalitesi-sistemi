"""DS-04: Katalog ve metadata keşfi birim testleri.

Kapsam:
- validate_discovery_pattern: canonical/invalid glob ve güvenlik kontrolleri
- MetadataDiscoveryOutcome: typed connector result
- CatalogQueryService: scope-safe okuma projeksiyonları
- create_service_actor_context: güvenilir SERVICE ActorContext
- DiscoveryScope / MetadataDiff / MetadataDiscoveryResult domain modelleri
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from veri_kalitesi.data_sources.models import (
    CatalogItemStatus,
    DataField,
    DataSource,
    DataSourceStatus,
    Dataset,
    DatasetType,
    DiscoveryScope,
    DiscoveryStatus,
    MetadataDatasetCandidate,
    MetadataDiff,
    MetadataDiffStatus,
    MetadataDiscoveryOutcome,
    MetadataDiscoveryResult,
    MetadataFieldCandidate,
    SourceType,
)
from veri_kalitesi.data_sources.service import validate_discovery_pattern
from veri_kalitesi.data_sources.catalog import (
    CatalogQueryService,
)
from veri_kalitesi.data_sources.errors import NotFoundError, ValidationError
from veri_kalitesi.identity import (
    ActorType,
    create_service_actor_context,
    is_trusted_actor_context,
)


# ── validate_discovery_pattern ──────────────────────────────────────


class TestValidateDiscoveryPattern:
    def test_accepts_simple_wildcard(self) -> None:
        assert validate_discovery_pattern("*") == "*"

    def test_accepts_glob_with_question_mark(self) -> None:
        assert validate_discovery_pattern("table_?") == "table_?"

    def test_accepts_alphanumeric_with_underscore(self) -> None:
        assert validate_discovery_pattern("public.my_table_01") == "public.my_table_01"

    def test_rejects_empty_pattern(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_discovery_pattern("")
        assert exc_info.value.code == "DISCOVERY_SCOPE_PATTERN_INVALID"

    def test_rejects_double_dot_path_traversal(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_discovery_pattern("../etc/passwd")
        assert exc_info.value.code == "DISCOVERY_SCOPE_PATTERN_INVALID"

    def test_rejects_forward_slash(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_discovery_pattern("schema/table")
        assert exc_info.value.code == "DISCOVERY_SCOPE_PATTERN_INVALID"

    def test_rejects_backslash(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_discovery_pattern(r"schema\table")
        assert exc_info.value.code == "DISCOVERY_SCOPE_PATTERN_INVALID"

    def test_rejects_sql_injection_semicolon(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_discovery_pattern("table; DROP TABLE")
        assert exc_info.value.code == "DISCOVERY_SCOPE_PATTERN_INVALID"

    def test_rejects_sql_comment_double_dash(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_discovery_pattern("table--comment")
        assert exc_info.value.code == "DISCOVERY_SCOPE_PATTERN_INVALID"

    def test_rejects_control_characters(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_discovery_pattern("table\x00name")
        assert exc_info.value.code == "DISCOVERY_SCOPE_PATTERN_INVALID"

    def test_rejects_overly_long_pattern(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            validate_discovery_pattern("a" * 300)
        assert exc_info.value.code == "DISCOVERY_SCOPE_PATTERN_INVALID"


# ── MetadataDiscoveryOutcome ────────────────────────────────────────


class TestMetadataDiscoveryOutcome:
    def test_complete_outcome(self) -> None:
        candidate = MetadataDatasetCandidate(
            namespace="public",
            name="users",
            fields=(MetadataFieldCandidate(name="id", native_data_type="integer"),),
        )
        outcome = MetadataDiscoveryOutcome(
            candidates=(candidate,),
            completed_scope={"schemas": ["public"]},
            scanned_object_count=1,
            is_complete=True,
        )
        assert outcome.is_complete is True
        assert outcome.partial_reason_code is None
        assert len(outcome.candidates) == 1
        assert outcome.scanned_object_count == 1

    def test_partial_outcome(self) -> None:
        outcome = MetadataDiscoveryOutcome(
            candidates=(),
            completed_scope={},
            scanned_object_count=100_000,
            is_complete=False,
            partial_reason_code="MAX_OBJECTS_REACHED",
        )
        assert outcome.is_complete is False
        assert outcome.partial_reason_code == "MAX_OBJECTS_REACHED"


# ── CatalogQueryService ─────────────────────────────────────────────


class _FakeCatalogReader:
    """CatalogQueryService testleri için minimum CatalogReader implementasyonu."""

    def __init__(
        self,
        sources: dict[str, DataSource] | None = None,
        datasets: dict[str, list[Dataset]] | None = None,
        fields: dict[str, list[DataField]] | None = None,
        discoveries: dict[int, MetadataDiscoveryResult] | None = None,
        diffs_by_discovery: dict[int, MetadataDiff | None] | None = None,
        diffs_by_id: dict[str, MetadataDiff] | None = None,
        scopes: dict[str, DiscoveryScope | None] | None = None,
    ) -> None:
        self._sources = sources or {}
        self._datasets = datasets or {}
        self._fields = fields or {}
        self._discoveries = discoveries or {}
        self._diffs_by_discovery = diffs_by_discovery or {}
        self._diffs_by_id = diffs_by_id or {}
        self._scopes = scopes or {}

    def get_data_source(self, data_source_id: str) -> DataSource:
        if data_source_id not in self._sources:
            raise NotFoundError(f"Source {data_source_id}")
        return self._sources[data_source_id]

    def list_data_sources(self, allowed_source_ids: frozenset[str]) -> list[DataSource]:
        return [s for sid, s in self._sources.items() if sid in allowed_source_ids]

    def list_all_data_sources(self) -> list[DataSource]:
        return list(self._sources.values())

    def list_datasets(self, data_source_id: str) -> list[Dataset]:
        return self._datasets.get(data_source_id, [])

    def get_dataset(self, dataset_id: str) -> Dataset:
        for ds_list in self._datasets.values():
            for ds in ds_list:
                if ds.dataset_id == dataset_id:
                    return ds
        raise NotFoundError(f"Dataset {dataset_id}")

    def list_data_fields(self, dataset_id: str) -> list[DataField]:
        return self._fields.get(dataset_id, [])

    def get_data_field(self, data_field_id: str) -> DataField:
        for flist in self._fields.values():
            for f in flist:
                if f.data_field_id == data_field_id:
                    return f
        raise NotFoundError(f"Field {data_field_id}")

    def get_discovery_result(self, discovery_id: int) -> MetadataDiscoveryResult:
        if discovery_id not in self._discoveries:
            raise NotFoundError(f"Discovery {discovery_id}")
        return self._discoveries[discovery_id]

    def get_diff_by_discovery(self, discovery_id: int) -> MetadataDiff | None:
        return self._diffs_by_discovery.get(discovery_id)

    def get_metadata_diff(self, metadata_diff_id: str) -> MetadataDiff:
        if metadata_diff_id not in self._diffs_by_id:
            raise NotFoundError(f"Diff {metadata_diff_id}")
        return self._diffs_by_id[metadata_diff_id]

    def list_pending_diffs(self, data_source_id: str) -> list[MetadataDiff]:
        return [
            d
            for d in self._diffs_by_id.values()
            if d.data_source_id == data_source_id and d.status == MetadataDiffStatus.PENDING
        ]

    def get_discovery_scope(self, data_source_id: str) -> DiscoveryScope | None:
        return self._scopes.get(data_source_id)


def _source(source_id: str = "src-1") -> DataSource:
    return DataSource(
        name="Test DB",
        source_type=SourceType.POSTGRESQL,
        connection_config={},
        secret_reference="secret://test",
        data_source_id=source_id,
        status=DataSourceStatus.ACTIVE,
    )


def _dataset(dataset_id: str = "ds-1", source_id: str = "src-1") -> Dataset:
    return Dataset(
        data_source_id=source_id,
        namespace="public",
        name="users",
        dataset_id=dataset_id,
    )


def _field(field_id: str = "f-1", dataset_id: str = "ds-1") -> DataField:
    return DataField(
        dataset_id=dataset_id,
        name="id",
        native_data_type="integer",
        data_field_id=field_id,
    )


class TestCatalogQueryService:
    def test_list_datasets_empty_scope_returns_empty(self) -> None:
        reader = _FakeCatalogReader(sources={"src-1": _source()})
        svc = CatalogQueryService(reader)
        result = svc.list_datasets_for_actor(permitted_source_ids=frozenset())
        assert result == []

    def test_list_datasets_returns_views_for_permitted_source(self) -> None:
        src = _source()
        ds = _dataset()
        reader = _FakeCatalogReader(
            sources={"src-1": src},
            datasets={"src-1": [ds]},
            fields={"ds-1": [_field()]},
        )
        svc = CatalogQueryService(reader)
        views = svc.list_datasets_for_actor(permitted_source_ids=frozenset({"src-1"}))
        assert len(views) == 1
        assert views[0].dataset.dataset_id == "ds-1"
        assert views[0].field_count == 1

    def test_get_dataset_view_raises_for_out_of_scope(self) -> None:
        reader = _FakeCatalogReader(
            sources={"src-1": _source()},
            datasets={"src-1": [_dataset()]},
        )
        svc = CatalogQueryService(reader)
        with pytest.raises(NotFoundError):
            svc.get_dataset_view("ds-1", permitted_source_ids=frozenset({"other-src"}))

    def test_list_fields_for_dataset_scope_check(self) -> None:
        reader = _FakeCatalogReader(
            sources={"src-1": _source()},
            datasets={"src-1": [_dataset()]},
            fields={"ds-1": [_field()]},
        )
        svc = CatalogQueryService(reader)
        fields = svc.list_fields_for_dataset("ds-1", permitted_source_ids=frozenset({"src-1"}))
        assert len(fields) == 1

    def test_get_field_view_raises_for_out_of_scope(self) -> None:
        reader = _FakeCatalogReader(
            sources={"src-1": _source()},
            datasets={"src-1": [_dataset()]},
            fields={"ds-1": [_field()]},
        )
        svc = CatalogQueryService(reader)
        with pytest.raises(NotFoundError):
            svc.get_field_view("f-1", permitted_source_ids=frozenset({"other-src"}))

    def test_get_discovery_scope_returns_none_when_absent(self) -> None:
        reader = _FakeCatalogReader(sources={"src-1": _source()})
        svc = CatalogQueryService(reader)
        scope = svc.get_discovery_scope("src-1", permitted_source_ids=frozenset({"src-1"}))
        assert scope is None

    def test_get_discovery_scope_returns_scope(self) -> None:
        expected = DiscoveryScope(
            data_source_id="src-1",
            include_patterns=("public.*",),
            exclude_patterns=("tmp.*",),
        )
        reader = _FakeCatalogReader(
            sources={"src-1": _source()},
            scopes={"src-1": expected},
        )
        svc = CatalogQueryService(reader)
        scope = svc.get_discovery_scope("src-1", permitted_source_ids=frozenset({"src-1"}))
        assert scope is not None
        assert scope.include_patterns == ("public.*",)

    def test_get_discovery_scope_raises_for_out_of_scope(self) -> None:
        reader = _FakeCatalogReader(sources={"src-1": _source()})
        svc = CatalogQueryService(reader)
        with pytest.raises(NotFoundError):
            svc.get_discovery_scope("src-1", permitted_source_ids=frozenset({"other-src"}))

    def test_list_pending_diffs_for_source_empty_when_out_of_scope(self) -> None:
        reader = _FakeCatalogReader()
        svc = CatalogQueryService(reader)
        result = svc.list_pending_diffs_for_source("src-1", permitted_source_ids=frozenset())
        assert result == []


# ── create_service_actor_context ────────────────────────────────────


class TestServiceActorContext:
    def test_creates_trusted_service_context(self) -> None:
        ctx = create_service_actor_context(
            actor_id="worker-1",
            correlation_id="corr-1",
            roles=frozenset({"METADATA_DISCOVERY_WORKER"}),
            permitted_source_ids=frozenset({"src-1"}),
        )
        assert is_trusted_actor_context(ctx)
        assert ctx.actor_type is ActorType.SERVICE
        assert ctx.actor_id == "worker-1"
        assert ctx.correlation_id == "corr-1"
        assert "METADATA_DISCOVERY_WORKER" in ctx.roles
        assert "src-1" in ctx.permitted_source_ids
        assert ctx.can_view_enterprise is True
        assert ctx.privileged is False

    def test_context_has_valid_expiry(self) -> None:
        ctx = create_service_actor_context(
            actor_id="worker-1",
            correlation_id="corr-1",
        )
        now = datetime.now(timezone.utc)
        assert ctx.issued_at <= now
        assert ctx.expires_at > now


# ── Domain model invariants ─────────────────────────────────────────


class TestDiscoveryDomainModels:
    def test_discovery_status_values(self) -> None:
        assert DiscoveryStatus.QUEUED.value == "QUEUED"
        assert DiscoveryStatus.RUNNING.value == "RUNNING"
        assert DiscoveryStatus.SUCCESS.value == "SUCCESS"
        assert DiscoveryStatus.PARTIAL.value == "PARTIAL"
        assert DiscoveryStatus.TECHNICAL_ERROR.value == "TECHNICAL_ERROR"
        assert DiscoveryStatus.CANCELLED.value == "CANCELLED"

    def test_metadata_diff_status_values(self) -> None:
        assert MetadataDiffStatus.PENDING.value == "PENDING"
        assert MetadataDiffStatus.APPLIED.value == "APPLIED"

    def test_catalog_item_status_values(self) -> None:
        assert CatalogItemStatus.ACTIVE.value == "ACTIVE"
        assert CatalogItemStatus.INACTIVE.value == "INACTIVE"

    def test_dataset_type_values(self) -> None:
        assert DatasetType.TABLE.value == "TABLE"
        assert DatasetType.VIEW.value == "VIEW"
        assert DatasetType.FILE_SHEET.value == "FILE_SHEET"
        assert DatasetType.API_COLLECTION.value == "API_COLLECTION"

    def test_metadata_diff_defaults(self) -> None:
        diff = MetadataDiff(
            metadata_diff_id="diff-1",
            discovery_id=1,
            data_source_id="src-1",
        )
        assert diff.status == MetadataDiffStatus.PENDING
        assert diff.requires_rule_review is False
        assert diff.applied_at is None
        assert diff.version == 1

    def test_discovery_scope_defaults(self) -> None:
        scope = DiscoveryScope(data_source_id="src-1")
        assert scope.include_patterns == ()
        assert scope.exclude_patterns == ()
        assert scope.page_size == 1000
        assert scope.max_objects == 100_000
        assert scope.timeout_seconds == 60
        assert scope.version == 1

    def test_metadata_discovery_result_lifecycle_fields(self) -> None:
        result = MetadataDiscoveryResult(
            data_source_id="src-1",
            succeeded=True,
            duration_ms=500,
            status=DiscoveryStatus.SUCCESS,
            started_at=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
            finished_at=datetime(2026, 8, 5, 10, 0, 1, tzinfo=timezone.utc),
            discovery_id=42,
        )
        assert result.started_at is not None
        assert result.finished_at is not None
        assert result.discovery_id == 42
        assert result.partial_reason_code is None
