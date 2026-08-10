# Runtime Configuration

All runtime behavior is controlled by environment variables. No configuration
files are read at application startup — every value comes from the process
environment.

> **Source evidence:** [api/settings.py](../src/veri_kalitesi/api/settings.py),
> [jobs/settings.py](../src/veri_kalitesi/jobs/settings.py),
> [persistence/database.py](../src/veri_kalitesi/persistence/database.py)

## Database

| Variable | Required | Default | Source |
|----------|----------|---------|--------|
| `DATA_QUALITY_DATABASE_URL` | **Yes** | — | [persistence/database.py](../src/veri_kalitesi/persistence/database.py) |
| `DATA_QUALITY_DATABASE_SCHEMA` | No | `dq` | [persistence/database.py](../src/veri_kalitesi/persistence/database.py) |

**Constraints enforced in code:**

- Driver must be `postgresql+psycopg`.
- Database name must be `data_quality`.
- Schema must match `[a-z][a-z0-9_]{0,62}`.

## API Settings

| Variable | Required | Default | Source |
|----------|----------|---------|--------|
| `DATA_QUALITY_RUNTIME_ENVIRONMENT` | No | `production` | [api/settings.py](../src/veri_kalitesi/api/settings.py) |
| `DATA_QUALITY_ALLOWED_ORIGINS` | **Yes** (effective) | — | [api/settings.py](../src/veri_kalitesi/api/settings.py) |
| `DATA_QUALITY_LOCAL_SECRET_DIR` | No | — | [api/settings.py](../src/veri_kalitesi/api/settings.py) |

**Allowed values for `DATA_QUALITY_RUNTIME_ENVIRONMENT`:**
`production`, `development`, `test`.

**`DATA_QUALITY_ALLOWED_ORIGINS`:** Comma-separated list of allowed CORS
origins. Wildcard `*` and blank entries are rejected.

**`DATA_QUALITY_LOCAL_SECRET_DIR`:** Path to a directory containing mounted
file secrets. Accepted only in `development` runtime; rejected in `production`.

### Policy Version Variables

These control the version labels embedded in authorization and audit policies.
They all have sensible defaults and rarely need overriding.

| Variable | Default |
|----------|---------|
| `DATA_QUALITY_AUDIT_POLICY_VERSION` | `AUDIT_OUTBOX_V1` |
| `DATA_QUALITY_DATA_SOURCE_POLICY_VERSION` | `DATA_SOURCE_COMMAND_POLICY_V1` |
| `DATA_QUALITY_RULE_POLICY_VERSION` | `RULE_APPROVAL_POLICY_V1` |
| `DATA_QUALITY_ISSUE_POLICY_VERSION` | `ISSUE_ACCESS_POLICY_V1` |
| `DATA_QUALITY_ACTOR_POLICY_VERSION` | `DASHBOARD_POLICY_V1` |
| `DATA_QUALITY_EXECUTION_COMMAND_POLICY_VERSION` | `EXECUTION_COMMAND_POLICY_V1` |
| `DATA_QUALITY_SCORING_CONFIGURATION_VERSION` | `DEFAULT_SCORING_V1` |

Source: [api/settings.py L66-91](../src/veri_kalitesi/api/settings.py).

## Worker Settings

| Variable | Required | Default | Source |
|----------|----------|---------|--------|
| `DQ_WORKER_ID` | No | `worker-01` | [jobs/settings.py](../src/veri_kalitesi/jobs/settings.py) |
| `DQ_WORKER_HOSTNAME` | No | `localhost` | [jobs/settings.py](../src/veri_kalitesi/jobs/settings.py) |
| `DQ_WORKER_CAPACITY` | No | `1` | [jobs/settings.py](../src/veri_kalitesi/jobs/settings.py) |
| `DQ_WORKER_LEASE_SECONDS` | No | `300` | [jobs/settings.py](../src/veri_kalitesi/jobs/settings.py) |
| `DQ_WORKER_IDLE_WAIT_SECONDS` | No | `0.5` | [jobs/settings.py](../src/veri_kalitesi/jobs/settings.py) |
| `DQ_WORKER_SHUTDOWN_GRACE_SECONDS` | No | `5.0` | [jobs/settings.py](../src/veri_kalitesi/jobs/settings.py) |

The worker also reads `DATA_QUALITY_DATABASE_URL`,
`DATA_QUALITY_DATABASE_SCHEMA`, `DATA_QUALITY_LOCAL_SECRET_DIR`,
`DATA_QUALITY_ISSUE_POLICY_VERSION`, and `DATA_QUALITY_ACTOR_POLICY_VERSION`
from the same environment.

## Frontend

| Variable | Required | Default | Source |
|----------|----------|---------|--------|
| `VITE_API_PROXY_TARGET` | No | `http://127.0.0.1:8000` | [vite.config.ts](../frontend/vite.config.ts) |

In the Docker Compose development environment this is set to
`http://api:8000` so the Vite dev server proxies `/api` requests to the API
container.

## Secrets

The application does not read secrets from environment variables directly.
Instead, data-source connection credentials are resolved from mounted files
via the `MountedFileSecretResolver` ([data_sources/secrets.py](../src/veri_kalitesi/data_sources/secrets.py)).

Each data source references a secret URI like `secret://local/<reference>`.
The resolver looks for `<DATA_QUALITY_LOCAL_SECRET_DIR>/<reference>/username`
and `<DATA_QUALITY_LOCAL_SECRET_DIR>/<reference>/password` files.

See [Getting Started §1](getting-started.md) for the development setup.
