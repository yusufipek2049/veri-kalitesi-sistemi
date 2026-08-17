"""Gerçek psycopg 3 ve SQLAlchemy PostgreSQL bağlantı testi adaptörü."""

from __future__ import annotations

import socket
from collections.abc import Mapping
from datetime import date, datetime, time, timezone
from typing import Any, NoReturn

import psycopg
from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError

from veri_kalitesi.data_sources.errors import ValidationError
from veri_kalitesi.data_sources.models import (
    DataField,
    Dataset,
    DatasetType,
    MetadataDatasetCandidate,
    MetadataDiscoveryOutcome,
    MetadataFieldCandidate,
    ProfileComputationResult,
    ProfileAnalysisPolicy,
    ProfileOptions,
    ProfileStatus,
    OutlierMethod,
)
from veri_kalitesi.data_sources.profiling import validate_freshness_field_scope
from veri_kalitesi.data_sources.postgresql import (
    AuthenticationConnectionError,
    DNSConnectionError,
    DriverConnectionError,
    NetworkConnectionError,
    PermissionConnectionError,
    PostgreSQLProbeResult,
    TLSConnectionError,
    TimeoutConnectionError,
)

_ROLE_CAPABILITY_QUERY = """
SELECT
    current_database() AS database_name,
    current_user AS user_name,
    version() AS server_version,
    current_setting('transaction_read_only') = 'on' AS transaction_read_only,
    NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = current_user
          AND (rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls)
    ) AS role_is_unprivileged,
    NOT has_database_privilege(current_user, current_database(), 'CREATE') AS no_database_create,
    NOT EXISTS (
        SELECT 1
        FROM pg_namespace
        WHERE nspname NOT IN ('pg_catalog', 'information_schema')
          AND nspname NOT LIKE 'pg_toast%'
          AND nspname NOT LIKE 'pg_temp_%'
          AND has_schema_privilege(current_user, oid, 'CREATE')
    ) AS no_schema_create,
    NOT EXISTS (
        SELECT 1
        FROM pg_class
        WHERE relkind IN ('r', 'p', 'v', 'm', 'f')
          AND relnamespace NOT IN (
              SELECT oid FROM pg_namespace
              WHERE nspname IN ('pg_catalog', 'information_schema')
                 OR nspname LIKE 'pg_toast%'
                 OR nspname LIKE 'pg_temp_%'
          )
          AND has_table_privilege(
              current_user,
              oid,
              'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'
          )
    ) AS no_table_write
"""


class SQLAlchemyPostgreSQLDriver:
    """FR-008 için TLS zorunlu ve salt okunur PostgreSQL probe adaptörü."""

    def probe(
        self,
        *,
        config: Mapping[str, Any],
        credentials: Mapping[str, Any],
        test_query: str,
        connect_timeout_seconds: int,
        statement_timeout_ms: int,
    ) -> PostgreSQLProbeResult:
        engine = self._create_engine(
            config=config,
            credentials=credentials,
            connect_timeout_seconds=connect_timeout_seconds,
            statement_timeout_ms=statement_timeout_ms,
        )
        try:
            with engine.connect() as connection:
                connection.exec_driver_sql(test_query).fetchone()
                capability = connection.exec_driver_sql(_ROLE_CAPABILITY_QUERY).mappings().one()
            read_only = all(
                bool(capability[field])
                for field in (
                    "transaction_read_only",
                    "role_is_unprivileged",
                    "no_database_create",
                    "no_schema_create",
                    "no_table_write",
                )
            )
            return PostgreSQLProbeResult(
                database_name=str(capability["database_name"]),
                user_name=str(capability["user_name"]),
                server_version=str(capability["server_version"]),
                read_only=read_only,
            )
        except Exception as exc:
            _raise_classified(exc)
        finally:
            engine.dispose()

    def discover_metadata(
        self,
        *,
        config: Mapping[str, Any],
        credentials: Mapping[str, Any],
        scope: Mapping[str, Any],
        page_size: int,
        max_objects: int,
        timeout_seconds: int,
    ) -> MetadataDiscoveryOutcome:
        include_patterns = list(scope.get("include_patterns", []))
        exclude_patterns = list(scope.get("exclude_patterns", []))
        engine = self._create_engine(
            config=config,
            credentials=credentials,
            connect_timeout_seconds=int(config.get("connect_timeout_seconds", 5)),
            statement_timeout_ms=timeout_seconds * 1000,
        )
        try:
            return self._discover_metadata_on_engine(
                engine,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                page_size=page_size,
                max_objects=max_objects,
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:
            _raise_classified(exc)
        finally:
            engine.dispose()

    def execute_count_query(
        self,
        *,
        config: Mapping[str, Any],
        credentials: Mapping[str, Any],
        sql: str,
        connection_timeout_seconds: int,
        statement_timeout_ms: int,
    ) -> int:
        engine = self._create_engine(
            config=config,
            credentials=credentials,
            connect_timeout_seconds=connection_timeout_seconds,
            statement_timeout_ms=statement_timeout_ms,
        )
        try:
            with engine.connect() as connection:
                result = connection.execute(text(sql)).scalar_one()
                return int(result)
        except Exception as exc:
            _raise_classified(exc)
        finally:
            engine.dispose()

    def preview_table(
        self,
        *,
        config: Mapping[str, Any],
        credentials: Mapping[str, Any],
        schema: str,
        table: str,
        columns: tuple[str, ...],
        limit: int,
        connect_timeout_seconds: int,
        statement_timeout_ms: int,
    ) -> tuple[tuple[str | None, ...], ...]:
        if not columns:
            raise ValidationError("Preview requires at least one catalog field.")
        engine = self._create_engine(
            config=config,
            credentials=credentials,
            connect_timeout_seconds=connect_timeout_seconds,
            statement_timeout_ms=statement_timeout_ms,
        )
        preparer = engine.dialect.identifier_preparer
        table_ref = f"{preparer.quote(schema)}.{preparer.quote(table)}"
        column_exprs = ", ".join(
            f"{preparer.quote(column)}::text AS {preparer.quote(f'col_{index}')}"
            for index, column in enumerate(columns)
        )
        try:
            with engine.connect() as connection:
                rows = connection.execute(
                    text(f"SELECT {column_exprs} FROM {table_ref} LIMIT :preview_limit"),
                    {"preview_limit": limit},
                ).all()
            return tuple(tuple(_cell_to_text(value) for value in row) for row in rows)
        except Exception as exc:
            _raise_classified(exc)
        finally:
            engine.dispose()

    @staticmethod
    def _discover_metadata_on_engine(
        engine: Engine,
        *,
        include_patterns: list[Any],
        exclude_patterns: list[Any],
        page_size: int,
        max_objects: int,
        timeout_seconds: int,
    ) -> MetadataDiscoveryOutcome:
        from fnmatch import fnmatch
        from time import perf_counter

        started = perf_counter()
        candidates: list[MetadataDatasetCandidate] = []
        scanned_object_count = 0
        object_count = 0
        is_complete = True
        partial_reason_code: str | None = None
        completed_scope: dict[str, Any] = {}

        def _matches_scope(schema_name: str, table_name: str) -> bool:
            fqn = f"{schema_name}.{table_name}"
            if exclude_patterns:
                for pattern in exclude_patterns:
                    pat = str(pattern)
                    if fnmatch(fqn, pat) or fnmatch(schema_name, pat):
                        return False
            if include_patterns:
                for pattern in include_patterns:
                    pat = str(pattern)
                    if fnmatch(fqn, pat) or fnmatch(schema_name, pat):
                        return True
                return False
            return True

        with engine.connect() as connection:
            table_query = text(
                """
                SELECT t.table_schema, t.table_name, t.table_type,
                       obj_description((t.table_schema || '.' || t.table_name)::regclass)
                           AS table_comment
                FROM information_schema.tables t
                WHERE t.table_schema NOT IN ('pg_catalog', 'information_schema')
                  AND t.table_type IN ('BASE TABLE', 'VIEW')
                ORDER BY t.table_schema, t.table_name
                """
            )
            tables = connection.execute(table_query).mappings().fetchmany(page_size)

            while tables:
                for table_row in tables:
                    elapsed = perf_counter() - started
                    if elapsed >= timeout_seconds:
                        is_complete = False
                        partial_reason_code = "TIMEOUT_EXCEEDED"
                        break
                    if object_count >= max_objects:
                        is_complete = False
                        partial_reason_code = "MAX_OBJECTS_EXCEEDED"
                        break

                    schema_name = str(table_row["table_schema"])
                    table_name = str(table_row["table_name"])
                    table_type = str(table_row["table_type"])

                    if not _matches_scope(schema_name, table_name):
                        continue

                    scanned_object_count += 1
                    object_count += 1

                    column_query = text(
                        """
                        SELECT c.column_name, c.data_type, c.is_nullable,
                               c.ordinal_position
                        FROM information_schema.columns c
                        WHERE c.table_schema = :schema AND c.table_name = :table
                        ORDER BY c.ordinal_position
                        """
                    )
                    columns = (
                        connection.execute(
                            column_query, {"schema": schema_name, "table": table_name}
                        )
                        .mappings()
                        .all()
                    )

                    fields = tuple(
                        MetadataFieldCandidate(
                            name=str(col["column_name"]),
                            native_data_type=str(col["data_type"]),
                            is_nullable=str(col["is_nullable"]).upper() == "YES",
                        )
                        for col in columns
                    )
                    scanned_object_count += len(fields)

                    ds_type = DatasetType.VIEW if table_type == "VIEW" else DatasetType.TABLE
                    estimated_row_count = _try_estimate_row_count(
                        connection, schema_name, table_name
                    )
                    candidates.append(
                        MetadataDatasetCandidate(
                            namespace=schema_name,
                            name=table_name,
                            dataset_type=ds_type,
                            estimated_row_count=estimated_row_count,
                            fields=fields,
                        )
                    )

                if not is_complete:
                    break

                tables = connection.execute(table_query).mappings().fetchmany(page_size)

        completed_scope = {
            "include_patterns": [str(p) for p in include_patterns],
            "exclude_patterns": [str(p) for p in exclude_patterns],
            "schemas_scanned": sorted({c.namespace for c in candidates}),
        }
        return MetadataDiscoveryOutcome(
            candidates=tuple(candidates),
            completed_scope=completed_scope,
            scanned_object_count=scanned_object_count,
            is_complete=is_complete,
            partial_reason_code=partial_reason_code,
        )

    def profile_dataset(
        self,
        *,
        config: Mapping[str, Any],
        credentials: Mapping[str, Any],
        dataset: Dataset,
        fields: tuple[DataField, ...],
        options: ProfileOptions,
    ) -> ProfileComputationResult:
        policy = options.analysis_policy
        selected = [
            field
            for field in fields
            if not options.field_names or field.name in options.field_names
        ]
        validate_freshness_field_scope(
            policy,
            fields,
            selected_field_names=tuple(field.name for field in selected),
        )
        if policy is not None and any(
            field.name in policy.freshness_field_names
            and not _is_freshness_type(field.native_data_type)
            for field in selected
        ):
            raise ValidationError(
                "PostgreSQL freshness fields must use a timezone-safe date/time type."
            )
        engine = self._create_engine(
            config=config,
            credentials=credentials,
            connect_timeout_seconds=int(config.get("connect_timeout_seconds", 5)),
            statement_timeout_ms=int(config.get("statement_timeout_ms", 5000)),
        )
        preparer = engine.dialect.identifier_preparer
        table_ref = f"{preparer.quote(dataset.namespace)}.{preparer.quote(dataset.name)}"
        try:
            with engine.connect() as connection:
                row_count = int(
                    connection.execute(text(f"SELECT count(*) FROM {table_ref}")).scalar_one()
                )
                metrics: dict[str, Any] = {
                    "record_count": row_count,
                    "sampled_count": row_count,
                    "method": "AGGREGATE",
                    "sample_ratio": None,
                    "fields": {},
                    "advanced_analysis": {
                        "status": "RESOLVED" if policy is not None else "CONFIGURATION_ERROR",
                        "reason": None if policy is not None else "ACTIVE_PROFILE_POLICY_MISSING",
                    },
                    "analysis_execution": {
                        "method": "SOURCE_AGGREGATE",
                        "query_version": options.query_version,
                        "raw_rows_transferred": False,
                    },
                }
                for field in selected:
                    column = preparer.quote(field.name)
                    base = (
                        connection.execute(
                            text(
                                f"""
                            SELECT count(*) FILTER (WHERE {column} IS NULL) AS null_count,
                                   count(DISTINCT {column}) AS distinct_count
                            FROM {table_ref}
                            """
                            )
                        )
                        .mappings()
                        .one()
                    )
                    non_null_count = row_count - int(base["null_count"])
                    field_metrics: dict[str, Any] = {
                        "null_count": int(base["null_count"]),
                        "null_ratio": (int(base["null_count"]) / row_count if row_count else None),
                        "distinct_count": int(base["distinct_count"]),
                        "distinct_ratio": (
                            int(base["distinct_count"]) / non_null_count if non_null_count else None
                        ),
                        "distinct_measurement": "SOURCE_AGGREGATE",
                    }
                    if field.is_sensitive:
                        field_metrics["masked"] = True
                    if policy is not None:
                        field_metrics.update(
                            self._advanced_source_metrics(
                                connection,
                                table_ref=table_ref,
                                column=column,
                                field=field,
                                non_null_count=non_null_count,
                                distinct_count=int(base["distinct_count"]),
                                options=options,
                            )
                        )
                    metrics["fields"][field.name] = field_metrics
            return ProfileComputationResult(
                status=ProfileStatus.NO_DATA if row_count == 0 else ProfileStatus.COMPLETED,
                metrics=metrics,
                row_count=row_count,
                message="PostgreSQL source-aggregate profile completed.",
            )
        except Exception as exc:
            _raise_classified(exc)
        finally:
            engine.dispose()

    @staticmethod
    def _advanced_source_metrics(
        connection: Any,
        *,
        table_ref: str,
        column: str,
        field: DataField,
        non_null_count: int,
        distinct_count: int,
        options: ProfileOptions,
    ) -> dict[str, Any]:
        policy = options.analysis_policy
        assert policy is not None
        top_rows = connection.execute(
            text(
                f"""
                SELECT CAST({column} AS text) AS value, count(*) AS value_count
                FROM {table_ref}
                WHERE {column} IS NOT NULL
                GROUP BY {column}
                ORDER BY value_count DESC, CAST({column} AS text)
                LIMIT :top_n_limit
                """
            ),
            {"top_n_limit": policy.top_n_limit},
        ).mappings()
        result: dict[str, Any] = {
            "type_distribution": (
                {_source_type_family(field.native_data_type): non_null_count}
                if non_null_count
                else {}
            ),
            "format_distribution": _source_format_distribution(connection, table_ref, column),
            "top_values": [
                {
                    "rank": rank,
                    "value": str(row["value"]),
                    "count": int(row["value_count"]),
                }
                for rank, row in enumerate(top_rows, start=1)
            ],
            "sampling": {
                "strategy": "SOURCE_AGGREGATE",
                "observed_non_null_count": non_null_count,
                "high_cardinality_threshold": policy.high_cardinality_threshold,
                "high_cardinality": distinct_count > policy.high_cardinality_threshold,
                "raw_rows_transferred": False,
            },
        }
        if field.name in policy.freshness_field_names:
            freshness_max = connection.execute(
                text(f"SELECT max({column}) AS freshness_max FROM {table_ref}")
            ).scalar_one()
            if freshness_max is not None:
                result["freshness_max"] = _normalize_freshness_aggregate(freshness_max)
        if not _is_numeric_type(field.native_data_type):
            result["numeric_summary"] = {
                "status": "NOT_NUMERIC",
                "observed_count": non_null_count,
            }
            result["outlier_candidates"] = []
            return result
        summary = (
            connection.execute(
                text(
                    f"""
                SELECT count({column}) AS value_count,
                       min({column})::double precision AS minimum,
                       max({column})::double precision AS maximum,
                       avg({column})::double precision AS mean,
                       percentile_cont(0.5) WITHIN GROUP (ORDER BY {column})::double precision
                           AS median,
                       percentile_cont(0.25) WITHIN GROUP (ORDER BY {column})::double precision
                           AS q1,
                       percentile_cont(0.75) WITHIN GROUP (ORDER BY {column})::double precision
                           AS q3
                FROM {table_ref}
                WHERE {column} IS NOT NULL
                """
                )
            )
            .mappings()
            .one()
        )
        count = int(summary["value_count"])
        if count < policy.minimum_numeric_sample:
            result["numeric_summary"] = {
                "status": "INSUFFICIENT_SAMPLE",
                "observed_count": count,
                "minimum_required": policy.minimum_numeric_sample,
            }
            result["outlier_candidates"] = []
            return result
        numeric_summary = {
            "count": count,
            "min": float(summary["minimum"]),
            "max": float(summary["maximum"]),
            "mean": float(summary["mean"]),
            "median": float(summary["median"]),
            "q1": float(summary["q1"]),
            "q3": float(summary["q3"]),
        }
        mad = float(
            connection.execute(
                text(
                    f"""
                    SELECT percentile_cont(0.5) WITHIN GROUP
                           (ORDER BY abs({column}::double precision - :median))
                    FROM {table_ref}
                    WHERE {column} IS NOT NULL
                    """
                ),
                {"median": numeric_summary["median"]},
            ).scalar_one()
        )
        numeric_summary["mad"] = mad
        result["numeric_summary"] = numeric_summary
        result["outlier_candidates"] = _source_outlier_candidates(
            connection,
            table_ref,
            column,
            numeric_summary,
            policy,
        )
        return result

    @staticmethod
    def _create_engine(
        *,
        config: Mapping[str, Any],
        credentials: Mapping[str, Any],
        connect_timeout_seconds: int,
        statement_timeout_ms: int,
    ) -> Engine:
        username = credentials.get("username")
        password = credentials.get("password")
        if not isinstance(username, str) or not username or not isinstance(password, str):
            raise AuthenticationConnectionError()

        connect_args: dict[str, object] = {
            "connect_timeout": connect_timeout_seconds,
            "sslmode": str(config["ssl_mode"]),
            "options": (
                f"-c statement_timeout={statement_timeout_ms} -c default_transaction_read_only=on"
            ),
            "application_name": "veri-kalitesi-connection-probe",
        }
        ssl_root_cert = config.get("ssl_root_cert")
        if ssl_root_cert is not None:
            if not isinstance(ssl_root_cert, str) or not ssl_root_cert:
                raise TLSConnectionError()
            connect_args["sslrootcert"] = ssl_root_cert

        url = URL.create(
            "postgresql+psycopg",
            username=username,
            password=password,
            host=str(config["host"]),
            port=int(config["port"]),
            database=str(config["database"]),
        )
        try:
            return create_engine(
                url,
                connect_args=connect_args,
                hide_parameters=True,
                pool_pre_ping=True,
            )
        except SQLAlchemyError as exc:
            raise DriverConnectionError() from exc


def _cell_to_text(value: Any) -> str | None:
    """Hücre değerini önizleme için güvenli metne çevirir."""
    if value is None:
        return None
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    return str(value)


def _raise_classified(exc: Exception) -> NoReturn:
    original = exc.orig if isinstance(exc, DBAPIError) else exc
    sqlstate = getattr(original, "sqlstate", None)
    message = str(original).lower()

    if isinstance(original, psycopg.errors.InvalidPassword) or sqlstate == "28P01":
        raise AuthenticationConnectionError() from exc
    if isinstance(original, psycopg.errors.InsufficientPrivilege) or sqlstate == "42501":
        raise PermissionConnectionError() from exc
    if isinstance(original, (TimeoutError, psycopg.errors.QueryCanceled)) or any(
        marker in message for marker in ("timeout expired", "timed out", "statement timeout")
    ):
        raise TimeoutConnectionError() from exc
    if isinstance(original, socket.gaierror) or any(
        marker in message
        for marker in ("could not translate host name", "name or service not known")
    ):
        raise DNSConnectionError() from exc
    if any(
        marker in message
        for marker in (
            "certificate verify failed",
            "root certificate file",
            "server does not support ssl",
            "ssl error",
            "tls",
        )
    ):
        raise TLSConnectionError() from exc
    if isinstance(exc, OperationalError):
        raise NetworkConnectionError() from exc
    if isinstance(exc, SQLAlchemyError):
        raise DriverConnectionError() from exc
    raise DriverConnectionError() from exc


def _source_format_distribution(
    connection: Any,
    table_ref: str,
    column: str,
) -> dict[str, int]:
    rows = connection.execute(
        text(
            f"""
            SELECT CASE
                     WHEN CAST({column} AS text) ~ '^[+-]?[0-9]+$' THEN 'INTEGER'
                     WHEN CAST({column} AS text) ~
                          '^[+-]?([0-9]+\\.[0-9]*|[0-9]*\\.[0-9]+)$' THEN 'DECIMAL'
                     WHEN CAST({column} AS text) ~
                          '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}[ T]' THEN 'ISO_DATETIME'
                     WHEN CAST({column} AS text) ~
                          '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$' THEN 'ISO_DATE'
                     WHEN CAST({column} AS text) ~ '^[[:alpha:]]+$' THEN 'ALPHA'
                     WHEN CAST({column} AS text) ~ '^[[:alnum:]]+$' THEN 'ALPHANUMERIC'
                     ELSE 'OTHER'
                   END AS format_name,
                   count(*) AS format_count
            FROM {table_ref}
            WHERE {column} IS NOT NULL
            GROUP BY format_name
            ORDER BY format_name
            """
        )
    ).mappings()
    return {str(row["format_name"]): int(row["format_count"]) for row in rows}


def _source_outlier_candidates(
    connection: Any,
    table_ref: str,
    column: str,
    summary: Mapping[str, Any],
    policy: ProfileAnalysisPolicy,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    count = int(summary["count"])
    for method in policy.enabled_outlier_methods:
        if method is OutlierMethod.IQR:
            iqr = float(summary["q3"]) - float(summary["q1"])
            lower = float(summary["q1"]) - policy.iqr_multiplier * iqr
            upper = float(summary["q3"]) + policy.iqr_multiplier * iqr
            candidate_count = int(
                connection.execute(
                    text(
                        f"""
                        SELECT count(*) FROM {table_ref}
                        WHERE {column} IS NOT NULL
                          AND ({column} < :lower_bound OR {column} > :upper_bound)
                        """
                    ),
                    {"lower_bound": lower, "upper_bound": upper},
                ).scalar_one()
            )
            candidates.append(
                {
                    "method": method.value,
                    "parameters": {"iqr_multiplier": policy.iqr_multiplier},
                    "candidate_count": candidate_count,
                    "candidate_ratio": candidate_count / count,
                    "lower_bound": lower,
                    "upper_bound": upper,
                    "result_kind": "OUTLIER_CANDIDATE",
                }
            )
        elif method is OutlierMethod.ROBUST_Z_SCORE:
            mad = float(summary["mad"])
            if mad == 0:
                candidate_count = 0
                state = "ZERO_MAD"
            else:
                candidate_count = int(
                    connection.execute(
                        text(
                            f"""
                            SELECT count(*) FROM {table_ref}
                            WHERE {column} IS NOT NULL
                              AND abs(0.6745 * ({column}::double precision - :median) / :mad)
                                  > :threshold
                            """
                        ),
                        {
                            "median": float(summary["median"]),
                            "mad": mad,
                            "threshold": policy.robust_z_score_threshold,
                        },
                    ).scalar_one()
                )
                state = "EVALUATED"
            candidates.append(
                {
                    "method": method.value,
                    "parameters": {"threshold": policy.robust_z_score_threshold},
                    "candidate_count": candidate_count,
                    "candidate_ratio": candidate_count / count,
                    "state": state,
                    "result_kind": "OUTLIER_CANDIDATE",
                }
            )
    return candidates


def _is_numeric_type(native_data_type: str) -> bool:
    normalized = native_data_type.upper().split("(", 1)[0].strip()
    return normalized in {
        "BIGINT",
        "DECIMAL",
        "DOUBLE PRECISION",
        "INTEGER",
        "NUMERIC",
        "REAL",
        "SMALLINT",
    }


def _is_freshness_type(native_data_type: str) -> bool:
    normalized = native_data_type.upper().split("(", 1)[0].strip()
    return normalized in {
        "DATE",
        "TIMESTAMPTZ",
        "TIMESTAMP WITH TIME ZONE",
    }


def _normalize_freshness_aggregate(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError(
                "PostgreSQL freshness aggregate must include timezone information."
            )
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc).isoformat()
    raise ValidationError("PostgreSQL freshness aggregate returned an incompatible value.")


def _source_type_family(native_data_type: str) -> str:
    normalized = native_data_type.upper().split("(", 1)[0].strip()
    if normalized in {"SMALLINT", "INTEGER", "BIGINT"}:
        return "INTEGER"
    if _is_numeric_type(normalized):
        return "DECIMAL"
    if normalized in {"BOOLEAN", "BOOL"}:
        return "BOOLEAN"
    if normalized == "DATE":
        return "DATE"
    if "TIMESTAMP" in normalized:
        return "DATETIME"
    return "TEXT"


def _try_estimate_row_count(connection: Any, schema: str, table: str) -> int | None:
    """Return an estimated row count from pg_class statistics, or None."""
    try:
        row = (
            connection.execute(
                text(
                    """
                SELECT c.reltuples::bigint AS estimated_rows
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = :schema AND c.relname = :table
                """
                ),
                {"schema": schema, "table": table},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        estimated = int(row["estimated_rows"])
        return max(0, estimated)
    except Exception:
        return None
