# Veri Kalitesi İzleme ve Skorlama Sistemi

An enterprise data-quality monitoring and scoring platform. The system connects
to relational data sources in **read-only** mode, evaluates quality rules, and
produces quality scores, issues, and audit trails. Source production data is
never modified.

> **This system is not production-ready.** Corporate IdP/LDAP, PAM/secrets,
> HA, message broker, SIEM/WORM, ServiceNow, DR, and bank compliance approvals
> are separate efforts.

## Capabilities

| Area | What Works |
|------|-----------|
| **Data sources** | Create, activate, passivate, test connections; query metadata |
| **Quality rules** | List rules and versions; query rule history |
| **Issues** | Create, investigate, assign, resolve, verify, close |
| **Executions** | Start, cancel, and query rule executions |
| **Scores** | List, detail, and compare quality scores |
| **Audit** | Query audit events |
| **Notifications** | Inbox, deliveries, channels, subscriptions |
| **Catalog** | Metadata discovery, dataset/field browsing, diff application |
| **Background worker** | EXECUTION, METADATA_DISCOVERY, and NOTIFICATION_DELIVERY job types |

For the full capability matrix (including unwired and test-only areas) see
[Known Gaps](documentation/known-gaps.md).

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI 0.135, Python ≥ 3.10, Uvicorn |
| Database | PostgreSQL 16, SQLAlchemy 2.0, Alembic 1.18 |
| Background worker | Pure-Python poll loop with fork-based subprocess isolation |
| Frontend | React 19, MUI 9, Vite 8, TypeScript 7 |

## Prerequisites

- **Docker** 24+ and **Docker Compose** v2.20+
- **Python** 3.10+ (for running tests outside containers)
- **Node.js** 22+ (for running the frontend outside containers)

## Quick Start

### 1. Set the database password

```bash
export DQ_POSTGRES_PASSWORD=example-dev-password
```

### 2. Prepare runtime secrets

```bash
cp -r infra/development/runtime-secrets.example \
      infra/development/runtime-secrets
```

Create per-source credential files inside
`infra/development/runtime-secrets/data-sources/<reference>/` — each needs a
`username` and `password` file. See
[`runtime-secrets.example/README.md`](infra/development/runtime-secrets.example/README.md).

### 3. Start the stack

```bash
docker compose -f infra/development/compose.yaml up --build
```

This starts five containers:

| Container | Port | Purpose |
|-----------|------|---------|
| `postgres` | 55432 | PostgreSQL 16 |
| `migrate` | — | Runs `alembic upgrade head`, then exits |
| `api` | 8000 | FastAPI backend |
| `worker` | — | Background job processor |
| `frontend` | 5173 | React dev server (proxies `/api` to backend) |

### 4. Verify

```bash
# API is responding
curl -s http://127.0.0.1:8000/api/v1/openapi.json | head -c 100

# List development users
curl -s http://127.0.0.1:8000/api/v1/development/users | python3 -m json.tool
```

Open <http://localhost:5173> in your browser. Select a development user to
log in.

### 5. Seed demo data (optional)

```bash
DATA_QUALITY_DATABASE_URL="postgresql+psycopg://dq_app:example-dev-password@127.0.0.1:55432/data_quality" \
    python scripts/seed_database.py
```

## Test & Quality Commands

```bash
# Backend
pytest -q                        # All tests (unit + integration)
ruff check .                     # Lint
ruff format --check .            # Format check
mypy src                         # Type check

# Frontend
cd frontend && npm test          # Unit tests (Vitest)
cd frontend && npm run typecheck # TypeScript check
cd frontend && npm run build     # Production build
```

All five CI jobs are **blocking** on every push/PR. See
[Testing & Quality](documentation/testing-and-quality.md) for the full matrix.

## Stop & Reset

```bash
# Stop (preserves database volume)
docker compose -f infra/development/compose.yaml down

# Stop and destroy database
docker compose -f infra/development/compose.yaml down -v
```

## Documentation

The canonical documentation lives in [`documentation/`](documentation/):

| Document | Purpose |
|----------|---------|
| [System Overview](documentation/system-overview.md) | What the system does, verified capabilities |
| [Architecture](documentation/architecture.md) | Runtime topology, composition chains |
| [Getting Started](documentation/getting-started.md) | Full setup guide with secrets and environment |
| [Runtime Configuration](documentation/runtime-configuration.md) | All environment variables |
| [API, Data & Workers](documentation/api-data-and-workers.md) | Endpoints, migrations, job types |
| [Testing & Quality](documentation/testing-and-quality.md) | CI gates, test commands |
| [Known Gaps](documentation/known-gaps.md) | Unwired capabilities, contradictions |

### Legacy Documentation

> **Warning:** The `docs/` directory contains historical SRS, architecture
> decisions, compliance artifacts, and iteration records that have **not** been
> re-verified against the current executable source code. They are preserved
> for reference only. The `documentation/` directory above is the authoritative
> starting point.
