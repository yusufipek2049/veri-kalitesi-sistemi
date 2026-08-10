# System Overview

The Veri Kalitesi Sistemi is an enterprise data-quality monitoring and scoring
platform. It connects to relational data sources in read-only mode, evaluates
quality rules against those sources, and produces quality scores, issues, and
audit trails. Source production data is never modified; only the system's own
metadata, policies, results, and audit records are written.

> **Source evidence:** [repository-inventory.md §2](evidence/repository-inventory.md)

## Component Summary

| Component | Technology | Role |
|-----------|-----------|------|
| **API server** | FastAPI 0.135 on Python ≥ 3.10, served by Uvicorn | HTTP API for dashboard, data sources, rules, issues, executions, scores, audit, notifications, catalog |
| **Background worker** | Pure-Python poll loop (`dq-worker`) | Claims jobs from a PostgreSQL queue and executes them in forked subprocesses |
| **Database** | PostgreSQL 16 (via `psycopg` 3.3, SQLAlchemy 2.0) | Single source of truth for all application state; 33 tables across 20 migrations |
| **Frontend** | React 19, MUI 9, Vite 8, TypeScript 7 | Single-page application with 20 client routes |
| **Migration** | Alembic 1.18 | Schema versioning; `alembic upgrade head` runs before API/worker start |

## Verified Capabilities

The table below lists only capabilities traced from entrypoint through
composition to a wired service. Capabilities that are unwired, test-only, or
dev-only are documented in [Known Gaps](known-gaps.md).

| Capability | Entry Point | Status |
|------------|-------------|--------|
| Data source query & commands (create, activate, passivate, test) | `GET/POST /api/v1/data-sources` | **Reachable** |
| Rules query | `GET /api/v1/rules` | **Reachable** |
| Issues query, create, investigate, close | `GET/POST /api/v1/issues` | **Reachable** |
| Executions query, start, cancel | `GET/POST /api/v1/executions` | **Reachable** |
| Scores query (list, detail, history, comparison) | `GET /api/v1/scores` | **Reachable** |
| Audit event query | `GET /api/v1/audit/events` | **Reachable** |
| Notifications (inbox, deliveries, channels, subscriptions) | `GET /api/v1/notifications/*` | **Reachable** |
| Catalog & metadata discovery | `GET/POST /api/v1/datasets`, `/api/v1/metadata-discoveries/*` | **Reachable** |
| Background job: EXECUTION | Worker poll loop | **Reachable** |
| Background job: METADATA_DISCOVERY | Worker poll loop | **Reachable** |
| Background job: NOTIFICATION_DELIVERY | Worker poll loop | **Reachable** |
| Development user list | `GET /api/v1/development/users` | **Dev-only** |

## What This System Is Not

- **Not production-ready.** Corporate IdP/LDAP integration, PAM/secrets
  management, HA session/data, message broker, SIEM/WORM audit, ServiceNow
  integration, DR, and bank compliance approvals are separate efforts.
- **Not a general-purpose data pipeline.** The worker processes a fixed set of
  job types defined in the composition root.
- **Not writable to source systems.** All data-source connectors operate in
  read-only mode.
