# Getting Started

Step-by-step guide to run the full stack locally with Docker Compose.

> **Source evidence:** [compose.yaml](../infra/development/compose.yaml),
> [Dockerfile](../infra/application/Dockerfile),
> [run_dev.py](../scripts/run_dev.py)

## Prerequisites

| Tool | Minimum Version | Notes |
|------|----------------|-------|
| Docker + Docker Compose v2 | Docker 24+, Compose v2.20+ | Compose file version: implicit (no `version:` key) |
| Python | 3.10+ | Only needed for running tests or CLI tools outside containers |
| Node.js | 22+ | Only needed for running the frontend outside containers |

## 1. Environment Preparation

### Database password

The Compose file requires `DQ_POSTGRES_PASSWORD` to be set. Create a `.env`
file in the repository root or export it in your shell:

```bash
# Example — choose your own password
export DQ_POSTGRES_PASSWORD=example-dev-password
```

### Runtime secrets (data-source credentials)

The API container reads mounted-file secrets from
`infra/development/runtime-secrets/data-sources/`. Copy the example directory:

```bash
cp -r infra/development/runtime-secrets.example \
      infra/development/runtime-secrets
```

Then create per-source credential files as described in
[`runtime-secrets.example/README.md`](../infra/development/runtime-secrets.example/README.md).
Each source needs a `username` file and a `password` file inside
`runtime-secrets/data-sources/<reference>/`.

> Never commit the `runtime-secrets/` directory — it is listed in `.gitignore`.

### Key environment variables

The Compose file sets these for the API and worker containers. For the full
reference see [Runtime Configuration](runtime-configuration.md).

| Variable | Value in Compose | Purpose |
|----------|-----------------|---------|
| `DATA_QUALITY_DATABASE_URL` | `postgresql+psycopg://dq_app:${DQ_POSTGRES_PASSWORD}@postgres:5432/data_quality` | Database connection |
| `DATA_QUALITY_DATABASE_SCHEMA` | `dq` | Application schema |
| `DATA_QUALITY_RUNTIME_ENVIRONMENT` | `development` | Enables dev identity resolver |
| `DATA_QUALITY_ALLOWED_ORIGINS` | `http://127.0.0.1:5173,http://localhost:5173` | CORS origins |
| `DATA_QUALITY_ACTOR_POLICY_VERSION` | `DEVELOPMENT_DASHBOARD_POLICY_V1` | Actor policy |
| `DATA_QUALITY_LOCAL_SECRET_DIR` | `/run/secrets/data-sources` | Mounted secret directory |

## 2. Docker Compose Quick Start

```bash
# From the repository root:
export DQ_POSTGRES_PASSWORD=example-dev-password

# Build and start all services
docker compose -f infra/development/compose.yaml up --build
```

This starts five containers in dependency order:

1. `postgres` — PostgreSQL 16.4 on host port **55432**
2. `migrate` — runs `alembic upgrade head`, then exits
3. `api` — FastAPI on host port **8000**
4. `worker` — `dq-worker` background poll loop
5. `frontend` — Vite dev server on host port **5173**

## 3. Smoke Check

After all containers are up:

```bash
# Verify the API is responding (OpenAPI spec)
curl -s http://127.0.0.1:8000/api/v1/openapi.json | head -c 200

# List development users (dev-only endpoint)
curl -s http://127.0.0.1:8000/api/v1/development/users | python3 -m json.tool

# List data sources (empty on fresh database)
curl -s http://127.0.0.1:8000/api/v1/data-sources | python3 -m json.tool
```

Open the frontend at <http://localhost:5173>. You will see the development
login page. Select a development user to proceed.

## 4. Database Seed (Optional)

A seed script is available for populating demo data:

```bash
# Outside containers — requires direct PostgreSQL access
DATA_QUALITY_DATABASE_URL="postgresql+psycopg://dq_app:example-dev-password@127.0.0.1:55432/data_quality" \
    python scripts/seed_database.py
```

> The seed script connects to the database directly. When using Docker Compose,
> the PostgreSQL port is mapped to host port 55432.

## 5. Running Tests

```bash
# Backend unit tests (inside a Python environment with dependencies installed)
pytest -q

# Backend lint
ruff check .
ruff format --check .

# Backend type check
mypy src

# Frontend unit tests
cd frontend && npm test

# Frontend type check
cd frontend && npm run typecheck
```

For the full test matrix see [Testing & Quality](testing-and-quality.md).

## 6. Stop & Reset

```bash
# Stop all containers (preserves volumes)
docker compose -f infra/development/compose.yaml down

# Stop and remove all volumes (destroys database)
docker compose -f infra/development/compose.yaml down -v

# Rebuild from scratch after volume removal
export DQ_POSTGRES_PASSWORD=example-dev-password
docker compose -f infra/development/compose.yaml up --build
```

## Next Steps

- [Runtime Configuration](runtime-configuration.md) — all environment variables
- [API, Data & Workers](api-data-and-workers.md) — available endpoints and job types
- [Known Gaps](known-gaps.md) — capabilities that exist in code but are not wired
