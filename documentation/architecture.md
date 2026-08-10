# Architecture

This page describes the **observed** runtime architecture as traced from
executable entrypoints. No architectural claim is made without a source path.

> **Source evidence:** [repository-inventory.json → runtime_processes](evidence/repository-inventory.json)

## Runtime Topology

```
┌────────────┐     ┌──────────┐     ┌───────────────┐
│  Frontend  │────▶│  API (1)  │────▶│  PostgreSQL   │
│  :5173     │     │  :8000    │     │  :55432       │
└────────────┘     └──────────┘     └───────┬───────┘
                                            │
                                    ┌───────┴───────┐
                                    │   Worker (2)   │
                                    │  (dq-worker)   │
                                    └────────────────┘

(1) uvicorn scripts.run_dev:app
(2) veri_kalitesi.jobs.entrypoint:main
```

All four processes are defined in
[`infra/development/compose.yaml`](../infra/development/compose.yaml).

### Startup Order

1. **postgres** — health-checked via `pg_isready`.
2. **migrate** — `alembic upgrade head`; waits for postgres healthy.
3. **api** + **worker** — both wait for migrate to complete successfully.
4. **frontend** — waits for api to start; proxies `/api` to the API container.

Source: [compose.yaml](../infra/development/compose.yaml) `depends_on` directives.

## API Composition Chain

The API process follows this call chain at startup:

| Step | File | Function |
|------|------|----------|
| 1 | [`infra/application/Dockerfile`](../infra/application/Dockerfile) | `CMD uvicorn scripts.run_dev:app` |
| 2 | [`scripts/run_dev.py`](../scripts/run_dev.py) | `app = create_development_app()` |
| 3 | [`src/veri_kalitesi/api/development_runtime.py`](../src/veri_kalitesi/api/development_runtime.py) | `create_development_app()` → `create_application()` |
| 4 | [`src/veri_kalitesi/api/composition.py`](../src/veri_kalitesi/api/composition.py) | `create_application()` wires all services, runs preflight |
| 5 | [`src/veri_kalitesi/api/app.py`](../src/veri_kalitesi/api/app.py) | `create_dashboard_api()` → `FastAPI` instance with all routers |

The composition root validates that 33 required database tables exist and that
the Alembic migration head matches `20260806_20` before accepting traffic
([composition.py L183-207](../src/veri_kalitesi/api/composition.py)).

## Worker Composition Chain

| Step | File | Function |
|------|------|----------|
| 1 | [`pyproject.toml`](../pyproject.toml) | `[project.scripts] dq-worker = veri_kalitesi.jobs.entrypoint:main` |
| 2 | [`src/veri_kalitesi/jobs/entrypoint.py`](../src/veri_kalitesi/jobs/entrypoint.py) | `main()` → `create_production_worker(settings)` |
| 3 | [`src/veri_kalitesi/jobs/production.py`](../src/veri_kalitesi/jobs/production.py) | Wires audit, execution, metadata, and conditionally score/notification handlers |
| 4 | [`src/veri_kalitesi/jobs/composition.py`](../src/veri_kalitesi/jobs/composition.py) | `create_persistent_job_runtime()` → `PersistentJobWorker` |
| 5 | [`src/veri_kalitesi/jobs/worker.py`](../src/veri_kalitesi/jobs/worker.py) | `run_forever()` — poll loop with fork-based subprocess isolation |

The worker uses `multiprocessing.Process(fork)` to isolate each job handler
execution. A heartbeat/lease mechanism prevents concurrent claims.

## Persistence Layer

- **Single database:** PostgreSQL, enforced by
  [`persistence/database.py`](../src/veri_kalitesi/persistence/database.py) —
  only `postgresql+psycopg` driver and `data_quality` database name are accepted.
- **Schema:** Configurable via `DATA_QUALITY_DATABASE_SCHEMA` (default `dq`).
- **Session factory:** SQLAlchemy `sessionmaker` with `pool_pre_ping` and
  `pool_recycle=1800`.
- **Migrations:** 20 Alembic revisions in a linear chain
  ([alembic/env.py](../alembic/env.py)).

## Backend Module Map

22 Python packages under `src/veri_kalitesi/`:

| Domain | Packages |
|--------|----------|
| HTTP / Identity | `api`, `identity` |
| Core domains | `data_sources`, `rules`, `issues`, `executions`, `scoring` |
| Infrastructure | `persistence`, `jobs`, `audit`, `notifications` |
| Extended | `reporting`, `retention`, `lineage`, `catalog` (inside `data_sources`) |
| Auxiliary | `dashboard`, `synthetic_data`, `secure_sdlc`, `servicenow`, `incident_response`, `enterprise_lab`, `environment_security`, `data_protection` |

## Frontend Architecture

- **Framework:** React 19 with `react-router-dom` 7 for client-side routing.
- **UI library:** MUI 9 with Emotion for styling.
- **Charts:** ECharts 6.
- **Build:** Vite 8 with `@vitejs/plugin-react`.
- **API proxy:** Vite dev server proxies `/api` requests to the backend
  ([vite.config.ts](../frontend/vite.config.ts)).
- **20 client routes** defined in [`frontend/src/App.tsx`](../frontend/src/App.tsx).
- **12 API client modules** (`frontend/src/*/api.ts`).
