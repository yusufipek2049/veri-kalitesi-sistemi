# Documentation

This directory contains the canonical, evidence-based documentation for the
Veri Kalitesi Sistemi. Every claim in these pages traces back to an executable
source file — no undocumented assumption survives.

> **Legacy warning:** The top-level `docs/` directory contains historical SRS,
> architecture, and compliance documents that have **not** been re-verified
> against the current codebase. They are preserved for reference only. The
> pages below are the authoritative starting point.

## Pages

| Document | Purpose |
|----------|---------|
| [System Overview](system-overview.md) | What the system does, verified capabilities, component summary |
| [Architecture](architecture.md) | Observed runtime topology, composition roots, data flow |
| [Getting Started](getting-started.md) | Prerequisites, Docker Compose quick start, smoke checks |
| [Runtime Configuration](runtime-configuration.md) | Environment variables, policy versions, secrets |
| [API, Data & Workers](api-data-and-workers.md) | API routes, persistence/migrations, background worker |
| [Testing & Quality](testing-and-quality.md) | Test commands, CI gates, quality tooling |
| [Known Gaps](known-gaps.md) | Unwired capabilities, contradictions, unresolved questions |
| [Cleanup Iteration Plan](cleanup-iteration-plan.md) | Evidence-based subtractive cleanup sequence and acceptance gates |

## Evidence

The machine-readable repository inventory that underpins this documentation:

- [evidence/repository-inventory.json](evidence/repository-inventory.json)
- [evidence/repository-inventory.md](evidence/repository-inventory.md)
