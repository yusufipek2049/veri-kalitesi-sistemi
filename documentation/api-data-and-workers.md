# API, Data & Workers

This page documents the reachable API surface, the persistence layer, and the
background worker job types — all traced from executable source code.

> **Source evidence:** [repository-inventory.json → api_routes](evidence/repository-inventory.json)

## API Routes

The API exposes 70 registered endpoints across 13 route groups. The base path
is `/api/v1/`. The OpenAPI specification is available at
`/api/v1/openapi.json`.

### Reachable Endpoints

These endpoints are wired through the composition root to a concrete service.

#### Data Sources

| Method | Path | Service |
|--------|------|---------|
| GET | `/api/v1/data-sources` | DataSourceQueryService |
| POST | `/api/v1/data-sources` | DataSourceCommandAdapter |
| GET | `/api/v1/data-sources/{id}/test` | DataSourceCommandAdapter |
| POST | `/api/v1/data-sources/{id}/activation` | DataSourceCommandAdapter |
| POST | `/api/v1/data-source-activation-requests/{id}/decision` | DataSourceCommandAdapter |
| POST | `/api/v1/data-sources/{id}/passivation` | DataSourceCommandAdapter |

Source: [data_sources_router.py](../src/veri_kalitesi/api/data_sources_router.py)

#### Rules

| Method | Path | Service |
|--------|------|---------|
| GET | `/api/v1/rules` | RuleQueryService |
| POST | `/api/v1/rules` | RuleCommandAdapter (Phase B) |
| POST | `/api/v1/rules/{id}/versions` | RuleQueryService |
| POST | `/api/v1/rules/{id}/test` | RuleCommandAdapter (Phase B) |
| POST | `/api/v1/rules/{id}/activation` | RuleCommandAdapter (Phase B) |
| POST | `/api/v1/rules/{id}/approval` | RuleCommandAdapter (Phase B) |
| POST | `/api/v1/rules/approval/{id}/decide` | RuleCommandAdapter (Phase B) |
| POST | `/api/v1/rules/approval/{id}/withdraw` | RuleCommandAdapter (Phase B) |
| POST | `/api/v1/rules/{id}/passivation` | RuleCommandAdapter (Phase B) |

> **Note:** Rule mutation endpoints (POST) require `PhaseBProviders` which are
> not composed in the development runtime. They return errors in dev mode.
> See [Known Gaps](known-gaps.md).

Source: [rules_router.py](../src/veri_kalitesi/api/rules_router.py)

#### Issues

| Method | Path | Service |
|--------|------|---------|
| GET | `/api/v1/issues` | IssueQueryService |
| POST | `/api/v1/issues` | IssueService |
| POST | `/api/v1/issues/{id}/investigation` | IssueService |
| GET | `/api/v1/issues/{id}/investigation/evidence` | IssueService |
| GET | `/api/v1/issues/{id}/assignment-options` | IssueService (Phase B) |
| POST | `/api/v1/issues/{id}/assignment` | IssueService (Phase B) |
| POST | `/api/v1/issues/{id}/resolution` | IssueService (Phase B) |
| POST | `/api/v1/issues/{id}/verification` | IssueService (Phase B) |
| POST | `/api/v1/issues/{id}/closure` | IssueService |

Source: [issues_router.py](../src/veri_kalitesi/api/issues_router.py)

#### Executions

| Method | Path | Service |
|--------|------|---------|
| GET | `/api/v1/executions` | ExecutionQueryService |
| GET | `/api/v1/executions/{id}` | ExecutionQueryService |
| POST | `/api/v1/executions` | PostgreSQLExecutionStartService |
| POST | `/api/v1/executions/{id}/cancel` | PostgreSQLExecutionCancelService |

Source: [executions_router.py](../src/veri_kalitesi/api/executions_router.py)

#### Scores

| Method | Path | Service |
|--------|------|---------|
| GET | `/api/v1/scores` | ScoreQueryService |
| GET | `/api/v1/scores/rules/{id}` | ScoreQueryService |
| GET | `/api/v1/scores/comparison` | ScoreQueryService |
| GET | `/api/v1/scores/{id}` | ScoreQueryService |

Source: [scores_router.py](../src/veri_kalitesi/api/scores_router.py)

#### Audit

| Method | Path | Service |
|--------|------|---------|
| GET | `/api/v1/audit/events` | AuditQueryService |

Source: [audit_router.py](../src/veri_kalitesi/api/audit_router.py)

#### Notifications

| Method | Path | Service |
|--------|------|---------|
| GET | `/api/v1/notifications/inbox` | NotificationQueryService |
| GET | `/api/v1/notifications/inbox/unread-count` | NotificationQueryService |
| GET | `/api/v1/notifications/deliveries/{id}` | NotificationQueryService |
| POST | `/api/v1/notifications/deliveries/{id}/read` | NotificationDeliveryService |
| GET | `/api/v1/notifications/events/{id}` | NotificationQueryService |
| GET | `/api/v1/notifications/subscriptions` | NotificationQueryService |
| GET | `/api/v1/notifications/channels` | NotificationQueryService |

Source: [notifications_router.py](../src/veri_kalitesi/api/notifications_router.py)

#### Catalog & Metadata Discovery

| Method | Path | Service |
|--------|------|---------|
| POST | `/api/v1/data-sources/{id}/metadata-discoveries` | PostgreSQLMetadataCommandService |
| PUT | `/api/v1/data-sources/{id}/discovery-scope` | PostgreSQLMetadataCommandService |
| GET | `/api/v1/data-sources/{id}/discovery-scope` | PostgreSQLMetadataCommandService |
| GET | `/api/v1/metadata-discoveries/{id}` | CatalogQueryService |
| GET | `/api/v1/metadata-discoveries/{id}/diff` | CatalogQueryService |
| POST | `/api/v1/metadata-diffs/{id}/application` | PostgreSQLMetadataCommandService |
| GET | `/api/v1/datasets` | CatalogQueryService |
| GET | `/api/v1/datasets/{id}` | CatalogQueryService |
| GET | `/api/v1/datasets/{id}/fields` | CatalogQueryService |
| GET | `/api/v1/fields/{id}` | CatalogQueryService |

Source: [catalog_router.py](../src/veri_kalitesi/api/catalog_router.py)

#### Development

| Method | Path | Service |
|--------|------|---------|
| GET | `/api/v1/development/users` | DevelopmentUserRegistry |

Available only when `DATA_QUALITY_RUNTIME_ENVIRONMENT=development`.

### Unwired Endpoints

The following routes are registered in the OpenAPI spec but return 503 at
runtime because their backing services are not composed. See
[Known Gaps](known-gaps.md) for details.

- `GET /api/v1/dashboard/summary` — `UnavailableDashboardService`
- `GET /api/v1/profile-comparisons`, `/api/v1/profile-snapshots/*` — not passed
- `POST /api/v1/scores/{id}/reproduction` — `score_publication_service=None`
- All `/api/v1/reports/*` and `/api/v1/report-schedules/*` — services are `None`
- `GET /api/v1/lineage/snapshots/{id}`, `/api/v1/governance/{ref}/projection` — `None`
- `POST /api/v1/session/logout` — requires BFF identity provider

## Persistence & Migrations

- **Database engine:** PostgreSQL only (`postgresql+psycopg` driver enforced)
- **ORM:** SQLAlchemy 2.0.51
- **Migration tool:** Alembic 1.18.4
- **Default schema:** `dq` (configurable via `DATA_QUALITY_DATABASE_SCHEMA`)
- **Database name:** `data_quality` (enforced — other names are rejected)
- **Migration head:** `20260806_20`
- **Total migrations:** 20 in a linear chain
- **Required tables:** 33 (validated at API startup by the composition preflight)

The full migration chain is listed in
[evidence/repository-inventory.md §6](evidence/repository-inventory.md).

### Running Migrations

```bash
# Via Docker Compose (automatic on startup):
docker compose -f infra/development/compose.yaml up migrate

# Directly (requires DATA_QUALITY_DATABASE_URL):
alembic -c alembic.ini upgrade head
```

## Background Worker

The worker is a single-threaded poll loop that claims jobs from the
`background_jobs` PostgreSQL table and executes them in forked subprocesses.

Source: [worker.py](../src/veri_kalitesi/jobs/worker.py)

### Job Types

| Job Type | Handler | Wired in Default Worker |
|----------|---------|------------------------|
| `EXECUTION` | `ExecutionJobHandler` | **Yes** |
| `METADATA_DISCOVERY` | `MetadataDiscoveryJobHandler` | **Yes** |
| `NOTIFICATION_DELIVERY` | `NotificationDeliveryJobHandler` | **Yes** |

`REPORT` ve `SCORE_PUBLICATION` varsayılan entrypoint'ten ulaşılamadığı ve somut
üretim composition çağıranları bulunmadığı için worker kayıt/enqueue yüzeyinden
kaldırılmıştır.

### Worker Lifecycle

1. Register in `workers` table (state: `STARTING`).
2. Poll loop: release expired claims → heartbeat → `claim_next()`.
3. Fork a child process for the handler; monitor via pipe.
4. On success: complete job (state: `SUCCESS`).
5. On failure: retry (re-queue) or terminal error based on retry policy.
6. On SIGTERM/SIGINT: drain (state: `DRAINING` → `STOPPED`).

### Starting the Worker

```bash
# Via Docker Compose (automatic):
docker compose -f infra/development/compose.yaml up worker

# Directly (requires pip-installed package):
DQ_WORKER_ID=worker-dev-01 \
DATA_QUALITY_DATABASE_URL="postgresql+psycopg://dq_app:password@localhost:55432/data_quality" \
DATA_QUALITY_LOCAL_SECRET_DIR=infra/development/runtime-secrets/data-sources \
    dq-worker
```
