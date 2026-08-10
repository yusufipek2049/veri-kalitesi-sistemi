# Testing & Quality

All quality gates that run in CI and the commands to reproduce them locally.

> **Source evidence:** [.github/workflows/quality.yml](../.github/workflows/quality.yml),
> [pyproject.toml](../pyproject.toml), [frontend/package.json](../frontend/package.json)

## CI Gates (Blocking)

Every push and pull request runs these five jobs. All must pass.

| Job | Command | Purpose |
|-----|---------|---------|
| Backend tests | `pytest -q` | 65 unit tests + 17 integration tests |
| Integration (PostgreSQL) | `pytest -q tests/integration` | PostgreSQL-backed tests; **skipped=0 enforced** |
| Backend lint | `ruff check .` + `ruff format --check .` | pycodestyle errors (E) + Pyflakes (F) |
| Backend types | `mypy src` | Static type checking (72 pre-existing errors allowed) |
| Frontend | `npm test` + `npm run typecheck` + `npm run build` | Vitest + TypeScript + Vite production build |

Source: [quality.yml](../.github/workflows/quality.yml)

### Integration Test Requirements

Integration tests require a live PostgreSQL instance. The CI job uses a
`postgres:16-alpine` service container with these environment variables:

| Variable | CI Value |
|----------|----------|
| `DATA_QUALITY_POSTGRES_TEST_URL` | `postgresql+psycopg://dqtest:dqtest@127.0.0.1:5432/data_quality` |
| `DATA_QUALITY_DATABASE_SCHEMA` | `data_quality` |
| `SYNTHETIC_POSTGRES_TEST` | `1` |
| `PGHOST` / `PGPORT` / `PGDATABASE` / `PGUSER` / `PGPASSWORD` | `127.0.0.1` / `5432` / `data_quality` / `dqtest` / `dqtest` |

If any integration test is skipped, the CI job fails.

## Backend Commands

```bash
# Install dependencies (no build-system; parsed from pyproject.toml)
pip install tomli
pip install $(python -c "import tomli; data = tomli.load(open('pyproject.toml', 'rb')); print(' '.join(data['project']['dependencies'] + data['project']['optional-dependencies']['test']))")

# Unit + integration tests with coverage
pytest -q

# Only unit tests
pytest -q tests/unit

# Only integration tests (requires PostgreSQL)
pytest -q tests/integration

# Lint (blocking rules: E, F)
ruff check .
ruff format --check .

# Extended advisory lint (non-blocking)
ruff check --select E,F,W,I,B,UP,SIM,TCH,A,PTH,RUF .

# Type check
mypy src

# Dead code detection
vulture src/ --min-confidence 80

# Cognitive complexity (advisory)
complexipy src
```

### Test Configuration

Defined in [pyproject.toml](../pyproject.toml):

```ini
pythonpath = ["src", "tests/support"]
testpaths = ["tests"]
addopts = ["--cov=src", "--cov-report=term-missing", ...]
```

## Frontend Commands

```bash
cd frontend

# Install dependencies
npm ci

# Unit tests (Vitest)
npm test

# Unit tests with coverage
npm run test:coverage

# TypeScript type check
npm run typecheck

# Production build
npm run build

# Lint (blocking: --max-warnings 0)
npm run lint

# Dead code detection (Knip)
npm run dead-code

# Copy-paste detection (jscpd)
npm run copy-paste

# Storybook (development)
npm run storybook

# E2E tests (Playwright — requires running app)
npm run test:e2e
```

### Test Inventory

| Category | Count | Location |
|----------|-------|----------|
| Backend unit tests | 65 files | `tests/unit/` |
| Backend integration tests | 17 files | `tests/integration/` |
| Frontend unit tests | 31 files | `frontend/src/**/*.test.*` |
| Frontend E2E specs | 8 files | `frontend/e2e/` |
| Storybook stories | 8 files | `frontend/src/**/*.stories.*` |

## Documentation Validation

```bash
# Check documentation links and structure (default: README.md + documentation/**)
python scripts/check_documentation.py

# Include legacy docs/** in the link scan
python scripts/check_documentation.py --legacy
```
