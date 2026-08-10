# Known Gaps

Capabilities that exist as source code (domain logic, services, tests) but are
**not** reachable through the current runtime composition. Each gap is backed
by evidence from the composition root.

> **Source evidence:** [repository-inventory.json → contradictions](evidence/repository-inventory.json)

## Unwired API Routes

These endpoints are registered in the FastAPI application and appear in the
OpenAPI spec, but return **503** at runtime because their backing services are
not passed from the composition root.

### Dashboard Summary

- **Route:** `GET /api/v1/dashboard/summary`
- **Symptom:** `UnavailableDashboardService` raises `DashboardQueryError`.
- **Evidence:** [composition.py L156-161](../src/veri_kalitesi/api/composition.py),
  [composition.py L408](../src/veri_kalitesi/api/composition.py)
- **Domain code exists:** `src/veri_kalitesi/dashboard/` (5 files)

### Profile Comparison & Snapshots

- **Routes:** `GET /api/v1/profile-comparisons`, `GET /api/v1/profile-snapshots/*`
- **Symptom:** `ProfileComparisonService` and `ProfileSnapshotQueryService` are
  not passed from `composition.py`.
- **Evidence:** [composition.py L407-440](../src/veri_kalitesi/api/composition.py)

### Score Reproduction

- **Route:** `POST /api/v1/scores/{id}/reproduction`
- **Symptom:** `score_publication_service=None` in composition.
- **Evidence:** [composition.py L407-440](../src/veri_kalitesi/api/composition.py)

### Reports (All Endpoints)

- **Routes:** All 9 routes under `/api/v1/reports/*` and `/api/v1/report-schedules/*`
- **Symptom:** `ReportPreviewService`, `ReportService`, and
  `ReportScheduleService` are all `None`.
- **Evidence:** [composition.py L407-440](../src/veri_kalitesi/api/composition.py)
- **Domain code exists:** `src/veri_kalitesi/reporting/` (9 files)

### Lineage & Governance

- **Routes:** `GET /api/v1/lineage/snapshots/{id}`,
  `GET /api/v1/governance/{asset_ref}/projection`
- **Symptom:** `PostgreSQLLineageEvidenceRepository` and
  `PostgreSQLGovernanceProfileReader` are `None`.
- **Evidence:** [composition.py L407-440](../src/veri_kalitesi/api/composition.py)
- **Domain code exists:** `src/veri_kalitesi/lineage/` (7 files)

### Session Logout

- **Route:** `POST /api/v1/session/logout`
- **Symptom:** Requires `BffSessionBoundary` which is only available in
  production identity mode, not in the development runtime.

## Test-Only Modules

These modules have domain logic and unit tests but are not exposed through any
API route or worker handler. They are reachable only through `pytest`.

| Module | Test Files | Description |
|--------|-----------|-------------|
| `retention/` | 4 test files | Data retention, archival, disposal, legal hold |
| `synthetic_data/` | 5 test files | Synthetic data generation, oracle, temporal |
| `secure_sdlc/` | 7 test files | SAST, SBOM, pentest, evidence gates |
| `servicenow/` | 1 test file | ServiceNow integration |
| `incident_response/` | 1 test file | Incident response |
| `enterprise_lab/` | 2 test files | Enterprise lab adapters |

## Contradictions

### 1. Rules Mutation in Development

Rule mutation POST routes (`/api/v1/rules`, `/test`, `/approval`, etc.) require
`RuleCommandAdapter` which is `None` when `phase_b_providers` is absent. The
development composition does not provide `PhaseBProviders`, so rule mutations
return errors in dev mode even though the routes are registered.

- [composition.py L360-376](../src/veri_kalitesi/api/composition.py)
- [development_runtime.py L15-47](../src/veri_kalitesi/api/development_runtime.py)

### 2. Frontend Dashboard Route vs. Backend

The frontend has a `DashboardRoute` component and calls the dashboard API, but
the backend always returns an error because `UnavailableDashboardService` is
composed. The frontend page loads but displays an error state.

## Unresolved Questions

1. **Production API composition** — `production.py` requires `BffSessionBoundary`
   and `PhaseBProviders` which are not instantiated in this repository. They
   must come from an external deployment package.
2. **Dashboard service** — Is there an alternate composition that provides a
   real `DashboardQueryService`?
3. **Report and Lineage services** — Full domain logic and tests exist but are
   never wired. Are they awaiting a future iteration?
4. **Test-only modules** — Are `retention`, `synthetic_data`, `secure_sdlc`,
   `servicenow`, `incident_response`, and `enterprise_lab` planned for future
   API exposure?
5. **Packaging** — No `[build-system]` is defined in `pyproject.toml`; CI
   installs dependencies by parsing the TOML directly.
