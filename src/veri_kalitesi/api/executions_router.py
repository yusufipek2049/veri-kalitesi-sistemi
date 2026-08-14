"""Çalıştırma/executions alanı HTTP route kayıtları."""

from __future__ import annotations

from typing import Protocol

from fastapi import FastAPI, Request, Response

from veri_kalitesi.api.bff import CSRF_HEADER_NAME
from veri_kalitesi.api.identity import DevelopmentActorContextResolver
from veri_kalitesi.api.models import (
    ExecutionCancelRequest,
    ExecutionDatasetRef,
    ExecutionDetailResponse,
    ExecutionListResponse,
    ExecutionListItemResponse,
    ExecutionStartRequest,
    ExecutionStartResponse,
    JobInfoRef,
)
from veri_kalitesi.executions.models import ExecutionMode, RuleExecution
from veri_kalitesi.executions.query import (
    ExecutionQueryService,
    ExecutionQueryTechnicalError,
)
from veri_kalitesi.identity import ActorContext


class ExecutionStartService(Protocol):
    def start_manual(
        self,
        *,
        rule_version_ids: tuple[str, ...],
        source_ids: tuple[str, ...],
        idempotency_key: str,
        actor_context: ActorContext,
        execution_mode: ExecutionMode = ExecutionMode.OFFICIAL,
    ) -> RuleExecution: ...


class ExecutionCancelService(Protocol):
    def cancel(
        self,
        execution_id: str,
        *,
        reason: str,
        actor_context: ActorContext,
    ) -> RuleExecution: ...


class RuleVersionCatalog(Protocol):
    """Kural sürümü tanımı okuma protokolü."""

    def get_version(self, rule_version_id: str) -> object: ...


class DatasetResolver(Protocol):
    """Dataset ve kaynak isim cozumleme protokolü.

    CatalogReader ile ayni yuzeyi paylasir; execution listesinde
    source_ids uzerinden dataset/kaynak isimlerini cozumlemek icin kullanilir.
    """

    def get_data_source_name(self, data_source_id: str) -> str | None: ...
    def list_datasets_for_source(self, data_source_id: str) -> list[dict[str, str]]: ...


class _Resolver(Protocol):
    def resolve(self, request: Request) -> ActorContext | None: ...


def _generate_sql_representation(rule_type: str | None, definition: dict) -> str | None:
    """Generate a human-readable SQL representation from a rule definition.

    For CUSTOM_SQL rules, returns the stored SQL directly.
    For template rules, generates a descriptive SQL representation.
    """
    if not rule_type or not definition:
        return None

    operator = definition.get("operator", "")

    if rule_type == "CUSTOM_SQL" or operator == "CUSTOM_SQL":
        sql = definition.get("sql")
        return sql if isinstance(sql, str) and sql.strip() else None

    field_id = definition.get("field_id", "<field>")

    if operator == "IS_NOT_NULL":
        return f"SELECT *\nFROM <dataset>\nWHERE {field_id} IS NULL"

    if operator == "UNIQUE":
        field_ids = definition.get("field_ids", [field_id])
        fields = ", ".join(str(f) for f in field_ids) if field_ids else field_id
        return (
            f"SELECT {fields}, COUNT(*) AS duplicates\n"
            f"FROM <dataset>\nGROUP BY {fields}\nHAVING COUNT(*) > 1"
        )

    if operator == "BETWEEN":
        minimum = definition.get("minimum")
        maximum = definition.get("maximum")
        conditions = []
        if minimum is not None:
            conditions.append(f"{field_id} < {minimum}")
        if maximum is not None:
            conditions.append(f"{field_id} > {maximum}")
        where = " OR ".join(conditions) if conditions else f"{field_id} OUT OF RANGE"
        return f"SELECT *\nFROM <dataset>\nWHERE {where}"

    if operator == "REGEX_MATCH":
        pattern = definition.get("pattern", "<pattern>")
        return f"SELECT *\nFROM <dataset>\nWHERE {field_id} !~ '{pattern}'"

    if operator == "MAX_AGE":
        max_age = definition.get("max_age_minutes", "<max_age>")
        timezone = definition.get("timezone", "UTC")
        return (
            f"SELECT *\nFROM <dataset>\n"
            f"WHERE NOW() AT TIME ZONE '{timezone}' - {field_id} > INTERVAL '{max_age} minutes'"
        )

    if operator == "REFERENCE_EXISTS":
        ref_dataset = definition.get("reference_dataset_id", "<ref_dataset>")
        source_fields = definition.get("source_field_ids", [field_id])
        ref_fields = definition.get("reference_field_ids", [])
        join_conditions = (
            " AND ".join(f"src.{sf} = ref.{rf}" for sf, rf in zip(source_fields, ref_fields))
            or "<join condition>"
        )
        return (
            f"SELECT src.*\nFROM <dataset> src\n"
            f"LEFT JOIN {ref_dataset} ref ON {join_conditions}\n"
            f"WHERE ref.{ref_fields[0] if ref_fields else '<ref_field>'} IS NULL"
        )

    if operator == "CROSS_TABLE_EQUALS":
        ref_dataset = definition.get("reference_dataset_id", "<ref_dataset>")
        source_fields = definition.get("source_field_ids", [field_id])
        ref_fields = definition.get("reference_field_ids", [])
        comparison = definition.get("comparison", "EQUALS")
        op = "<>" if comparison == "NOT_EQUALS" else "="
        src_field = source_fields[0] if source_fields else "<field>"
        ref_field = ref_fields[0] if ref_fields else "<ref_field>"
        return (
            f"-- Cross-table consistency ({comparison})\n"
            f"SELECT src.*\nFROM <dataset> src\n"
            f"JOIN {ref_dataset} ref ON ...\n"
            f"WHERE src.{src_field} {op} ref.{ref_field}"
        )

    return None


class JobInfoResolver(Protocol):
    """Job kuyruğu lifecycle bilgisi cozumleme protokolü.

    execution_id = job_id iliskisi uzerinden job detaylarini getirir.
    """

    def get_job_info(self, job_id: str) -> dict | None: ...


def _resolve_datasets(
    execution: RuleExecution,
    dataset_resolver: DatasetResolver | None,
) -> tuple[ExecutionDatasetRef, ...]:
    """Execution'in source_ids'nden dataset referanslarini cozumle."""
    if dataset_resolver is None or not execution.source_ids:
        return ()
    refs: list[ExecutionDatasetRef] = []
    for source_id in execution.source_ids:
        source_name = dataset_resolver.get_data_source_name(source_id)
        if source_name is None:
            continue
        try:
            datasets = dataset_resolver.list_datasets_for_source(source_id)
        except Exception:
            refs.append(
                ExecutionDatasetRef(
                    dataset_id="",
                    name="",
                    namespace="",
                    source_id=source_id,
                    source_name=source_name,
                )
            )
            continue
        for ds in datasets:
            refs.append(
                ExecutionDatasetRef(
                    dataset_id=ds.get("dataset_id", ""),
                    name=ds.get("name", ""),
                    namespace=ds.get("namespace", ""),
                    source_id=source_id,
                    source_name=source_name,
                )
            )
        if not datasets:
            refs.append(
                ExecutionDatasetRef(
                    dataset_id="",
                    name="",
                    namespace="",
                    source_id=source_id,
                    source_name=source_name,
                )
            )
    return tuple(refs)


def _extract_schedule_id(execution: RuleExecution) -> str | None:
    """Execution scope'undan schedule_id'yi cikar."""
    return execution.scope.get("schedule_id")


def _resolve_job_info(
    execution_id: str,
    job_info_resolver: JobInfoResolver | None,
) -> JobInfoRef | None:
    """Execution icin job kuyruğu bilgisini cozumle."""
    if job_info_resolver is None:
        return None
    try:
        info = job_info_resolver.get_job_info(execution_id)
    except Exception:
        return None
    if info is None:
        return None
    return JobInfoRef(
        job_id=info["job_id"],
        status=info["status"],
        queue_position=info.get("queue_position"),
        worker_id=info.get("worker_id"),
        leased_until=info.get("leased_until"),
        attempt_count=info.get("attempt_count", 0),
        last_error_class=info.get("last_error_class"),
        completed_at=info.get("completed_at"),
        completion_outcome=info.get("completion_outcome"),
    )


def register_executions_routes(
    app: FastAPI,
    *,
    execution_query_service: ExecutionQueryService | None,
    execution_start_service: ExecutionStartService | None,
    execution_cancel_service: ExecutionCancelService | None,
    rule_version_catalog: RuleVersionCatalog | None = None,
    dataset_resolver: DatasetResolver | None = None,
    job_info_resolver: JobInfoResolver | None = None,
    resolver: _Resolver,
    data_origin: str,
) -> None:
    """Çalıştırma alanının route'larını FastAPI uygulamasına kaydeder."""

    @app.get(
        "/api/v1/executions",
        response_model=ExecutionListResponse,
        tags=["executions"],
    )
    async def get_executions(
        request: Request,
        response: Response,
        dataset_id: str | None = None,
        schedule_id: str | None = None,
    ) -> ExecutionListResponse:
        if execution_query_service is None:
            raise ExecutionQueryTechnicalError(
                "Execution service is unavailable.", request.state.correlation_id
            )
        actor_context = resolver.resolve(request)
        executions = execution_query_service.list_for_actor(actor_context)
        response.headers["Cache-Control"] = "no-store"

        items: list[ExecutionListItemResponse] = []
        for execution in executions:
            datasets = _resolve_datasets(execution, dataset_resolver)
            sched_id = _extract_schedule_id(execution)
            # Apply dataset_id filter: at least one resolved dataset must match
            if dataset_id and not any(ds.dataset_id == dataset_id for ds in datasets):
                continue
            # Apply schedule_id filter
            if schedule_id and sched_id != schedule_id:
                continue
            items.append(
                ExecutionListItemResponse.from_domain(
                    execution,
                    datasets=datasets,
                    schedule_id=sched_id,
                )
            )

        return ExecutionListResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            limit=execution_query_service.page_limit,
            items=tuple(items),
        )

    @app.get(
        "/api/v1/executions/{execution_id}",
        response_model=ExecutionDetailResponse,
        tags=["executions"],
    )
    async def get_execution_detail(
        execution_id: str,
        request: Request,
        response: Response,
    ) -> ExecutionDetailResponse:
        if execution_query_service is None:
            raise ExecutionQueryTechnicalError(
                "Execution service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        execution, results = execution_query_service.get_detail_for_actor(
            execution_id, actor_context
        )
        response.headers["Cache-Control"] = "no-store"
        if isinstance(resolver, DevelopmentActorContextResolver):
            response.headers[CSRF_HEADER_NAME] = resolver.request_proof
        # Look up rule definitions (SQL) if catalog is available
        rule_definitions: list[dict] = []
        if rule_version_catalog is not None:
            seen: set[str] = set()
            for result in results:
                vid = result.rule_version_id
                if vid in seen:
                    continue
                seen.add(vid)
                try:
                    version = rule_version_catalog.get_version(vid)
                    definition = getattr(version, "definition", {})
                    rule_type = getattr(version, "rule_type", None)
                    rule_type_value = getattr(rule_type, "value", None)
                    def_dict = dict(definition) if definition else {}
                    sql = _generate_sql_representation(rule_type_value, def_dict)
                    rule_definitions.append(
                        {
                            "rule_version_id": vid,
                            "rule_type": rule_type_value,
                            "definition": def_dict,
                            "sql": sql,
                        }
                    )
                except Exception:
                    rule_definitions.append(
                        {"rule_version_id": vid, "rule_type": None, "definition": {}, "sql": None}
                    )
        return ExecutionDetailResponse.from_domain(
            execution,
            results,
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            rule_definitions=rule_definitions,
            datasets=_resolve_datasets(execution, dataset_resolver),
            schedule_id=_extract_schedule_id(execution),
            job_info=_resolve_job_info(execution.execution_id, job_info_resolver),
        )

    @app.post(
        "/api/v1/executions",
        response_model=ExecutionStartResponse,
        status_code=201,
        tags=["executions"],
    )
    async def start_manual_execution(
        payload: ExecutionStartRequest,
        request: Request,
        response: Response,
    ) -> ExecutionStartResponse:
        if execution_start_service is None:
            raise ExecutionQueryTechnicalError(
                "Execution start service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        assert actor_context is not None  # narrowed after resolver
        execution = execution_start_service.start_manual(
            rule_version_ids=payload.rule_version_ids,
            source_ids=payload.source_ids,
            idempotency_key=payload.idempotency_key,
            actor_context=actor_context,
            execution_mode=ExecutionMode(payload.execution_mode),
        )
        response.headers["Cache-Control"] = "no-store"
        return ExecutionStartResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=ExecutionListItemResponse.from_domain(
                execution,
                datasets=_resolve_datasets(execution, dataset_resolver),
                schedule_id=_extract_schedule_id(execution),
            ),
        )

    @app.post(
        "/api/v1/executions/{execution_id}/cancel",
        response_model=ExecutionStartResponse,
        tags=["executions"],
    )
    async def cancel_execution(
        execution_id: str,
        payload: ExecutionCancelRequest,
        request: Request,
        response: Response,
    ) -> ExecutionStartResponse:
        if execution_cancel_service is None:
            raise ExecutionQueryTechnicalError(
                "Execution cancel service is unavailable.", request.state.correlation_id
            )
        actor_context = getattr(request.state, "actor_context", None)
        if actor_context is None:
            actor_context = resolver.resolve(request)
        assert actor_context is not None  # narrowed after resolver
        execution = execution_cancel_service.cancel(
            execution_id,
            reason=payload.reason,
            actor_context=actor_context,
        )
        response.headers["Cache-Control"] = "no-store"
        return ExecutionStartResponse(
            data_origin=data_origin,
            correlation_id=request.state.correlation_id,
            item=ExecutionListItemResponse.from_domain(
                execution,
                datasets=_resolve_datasets(execution, dataset_resolver),
                schedule_id=_extract_schedule_id(execution),
            ),
        )
