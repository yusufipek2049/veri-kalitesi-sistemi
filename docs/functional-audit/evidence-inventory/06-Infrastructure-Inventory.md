# Infrastructure Inventory — Read-Only Evidence

> Source: `infra/`, `pyproject.toml`, `.github/`, `scripts/run_dev.py`

## 1. Python Backend

| Item | Evidence |
|------|----------|
| **Language** | Python 3.10+ |
| **Package manager** | pyproject.toml (setuptools) |
| **Web framework** | FastAPI + Uvicorn |
| **ORM** | SQLAlchemy 2.x + psycopg (PostgreSQL) |
| **Migrations** | Alembic (14 migrations in `alembic/versions/`) |
| **Validation** | Pydantic v2 (BaseModel, ConfigDict) |
| **Entry point (dev)** | `scripts/run_dev.py` → `create_development_app()` |
| **Entry point (prod)** | `src/veri_kalitesi/api/app.py` → `create_dashboard_api()` |

## 2. Frontend

| Item | Evidence |
|------|----------|
| **Framework** | React 18+ (TypeScript) |
| **Build** | Vite |
| **UI library** | MUI (Material UI) |
| **Charts** | ECharts (via echarts-for-react) |
| **Routing** | React Router v6 |
| **Testing** | Vitest (unit), Playwright (E2E), Storybook (visual) |
| **Config files** | `vite.config.ts`, `vitest.config.ts`, `playwright.config.ts` |

## 3. Enterprise Lab (Docker Compose)

**File**: `infra/enterprise-lab/compose.yaml`

| Service | Image | Purpose |
|---------|-------|---------|
| `environment-gate` | Custom Dockerfile | Pre-flight environment validation |
| `keycloak` | `quay.io/keycloak/keycloak:26.3.3` | Identity provider (OIDC/LDAP) |
| `postgres-primary` | `postgres:16.13-alpine3.22` | Primary PostgreSQL (WAL enabled) |
| `postgres-standby` | `postgres:16.13-alpine3.22` | Streaming replica |
| `rabbitmq` | `rabbitmq:4.1.2-management-alpine` | Message broker |
| `local-secret-manager` | Custom mock | Secret management mock |
| `fake-servicenow` | Custom mock | ServiceNow mock |
| `siem-collector` | Custom mock | SIEM/WORM mock |
| `evidence-store` | Custom mock | Evidence storage mock |
| `adapter-e2e` | Custom | Live adapter E2E tests (profile: acceptance) |

**Networks**: `enterprise-lab` (single network)
**Volumes**: `postgres-primary-data`, `postgres-standby-data`, `evidence-data`
**Secrets**: 8 secret files in `runtime-secrets/`

## 4. CI/CD

**File**: `.github/workflows/quality.yml`

| Item | Evidence |
|------|----------|
| **Platform** | GitHub Actions |
| **Quality checks** | mypy, ruff, pytest |

## 5. Scripts

| File | Purpose |
|------|---------|
| `scripts/check_documentation.py` | Documentation completeness check |
| `scripts/generate_synthetic_test_data.py` | Generate synthetic test data |
| `scripts/reset_synthetic_test_data.py` | Reset synthetic test data |

## 6. Agent/Tool Infrastructure

| Path | Purpose |
|------|---------|
| `tools/agent-loop/agentctl.sh` | Agent controller |
| `tools/agent-loop/controller.sh` | Agent loop controller |
| `tools/agent-loop/devam.sh` | Continue agent |
| `tools/agent-loop/ledger.sh` | Agent ledger |
| `tools/agent-loop/lib.sh` | Shared library |
| `tools/agent-loop/roles.sh` | Role definitions |
| `tools/agent-loop/prompts/` | Agent prompts |

## 7. Key Observations

1. **No production Dockerfile** for the application itself — only `scripts/run_dev.py` and enterprise lab compose
2. **No Kubernetes/Helm charts** — no orchestration manifests
3. **No nginx/reverse proxy config** — no gateway configuration
4. **No CI pipeline for deployment** — quality.yml only runs checks, not deploy
5. **Enterprise lab is test-only** — compose defines mock services, not production
6. **Database URL hardcoded** in `scripts/run_dev.py` — no environment-based config for dev
7. **Secrets managed via files** in `runtime-secrets/` — not via vault/KMS in dev mode
