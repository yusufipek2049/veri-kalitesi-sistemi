# Tool Baseline — GQ-01

> Generated 2026-08-06. All findings are **non-blocking** in this first iteration.
> Source code was NOT bulk-modified. Only targeted line-wrap fixes for E501.

---

## 1. Tool Versions (verified)

| Tool | Version | Runtime | Config location |
|---|---|---|---|
| Python | 3.10.12 | system | — |
| Node.js | 20.20.2 | nvm | — |
| ruff | 0.15.13 | pip | `pyproject.toml` `[tool.ruff]` |
| mypy | 2.1.0 | pip | `pyproject.toml` `[tool.mypy]` |
| pytest | 9.0.3 | pip | `pyproject.toml` `[tool.pytest.ini_options]` |
| pytest-cov | 7.1.0 | pip | `pyproject.toml` (addopts) |
| vulture | 2.16 | pip | `pyproject.toml` `[tool.vulture]` |
| semgrep | 1.163.0 | pip | `tools/semgrep/rules/` |
| eslint | 9.39.5 | npm | `frontend/eslint.config.js` |
| @babel/eslint-parser | 7.29.7 | npm | (TS syntax parser) |
| eslint-plugin-react-hooks | 5.2.0 | npm | — |
| @vitest/coverage-v8 | 4.1.10 | npm | `frontend/vitest.config.ts` |
| jscpd | 5.0.14 | npm | `.jscpd.json` |
| knip | 6.32.0 | npm | `frontend/knip.json` |
| graphify | (system) | pip | `GRAPHIFY_OUT=build/graphify` |

### Known limitations

- **@typescript-eslint/parser v8** throws at module load with TypeScript 7.0
  ([issue #10940](https://github.com/typescript-eslint/typescript-eslint/issues/10940)).
  We use `@babel/eslint-parser` + `@babel/preset-typescript` for TS syntax parsing.
- **eslint-plugin-sonarjs v2/v3** depends on `ts-api-utils` which also fails with TS 7.
  SonarJS rules are deferred until upstream supports TS 7.
- Type-level checking for frontend is handled by `tsc` (`npm run typecheck`).

---

## 2. Tool Responsibilities (non-overlapping)

| Concern | Tool | Scope |
|---|---|---|
| Syntax / import errors | ruff (E, F) | Python |
| Code formatting | ruff format | Python |
| Type checking | mypy | Python (src/) |
| Type checking | tsc | Frontend (src/) |
| Unit / integration tests | pytest | Python |
| Unit / component tests | vitest | Frontend |
| Coverage (Python) | pytest-cov | src/ |
| Coverage (Frontend) | @vitest/coverage-v8 | frontend/src/ |
| Dead code (Python) | vulture | src/ |
| Dead code / unused exports (Frontend) | knip | frontend/src/ |
| Copy-paste detection | jscpd | src/ + frontend/src/ |
| Custom code-smell rules | semgrep | src/ (when rules exist) |
| Architectural graph | graphify | whole repo |
| Lint (React hooks, unused vars) | eslint | frontend/src/ |
| Extended advisory rules | ruff (--select) | Python |

---

## 3. Blocking CI Gates (unchanged)

These gates are enforced in `.github/workflows/quality.yml`. **No gate was weakened.**

| Gate | Command | Status |
|---|---|---|
| Backend lint | `ruff check .` | **PASS** (0 errors) |
| Backend format | `ruff format --check .` | **PASS** (315 files) |
| Backend tests | `pytest -q` | **PASS** (1588 passed, 123 skipped) |
| Backend types | `mypy src` | 85 errors in 27 files (pre-existing) |
| Frontend typecheck | `tsc -b` | **PASS** |
| Frontend tests | `vitest run` | **PASS** (280 passed, 31 files) |
| Frontend build | `vite build` | **PASS** |

---

## 4. Advisory Findings (non-blocking)

### 4.1 Ruff Extended Rules

Command: `ruff check --select W,I,B,UP,SIM,TCH,A,PTH,RUF .`

| Count | Rule | Description |
|---:|---|---|
| 1349 | RUF002 | ambiguous-unicode-character-docstring |
| 213 | TC001 | typing-only-first-party-import |
| 200 | I001 | unsorted-imports |
| 114 | RUF003 | ambiguous-unicode-character-comment |
| 87 | RUF001 | ambiguous-unicode-character-string |
| 71 | TC003 | typing-only-standard-library-import |
| 63 | UP035 | deprecated-import |
| 47 | TC006 | runtime-cast-value |
| 29 | TC002 | typing-only-third-party-import |
| 18 | RUF022 | unsorted-dunder-all |
| 9 | B008 | function-call-in-default-argument |
| 7 | B009 | get-attr-with-constant |
| 7 | B904 | raise-without-from-inside-except |
| 7 | B905 | zip-without-explicit-strict |
| 4 | B007 | unused-loop-control-variable |
| 4 | B017 | assert-raises-exception |
| 4 | RUF100 | unused-noqa |
| 4 | SIM102 | collapsible-if |
| 4 | UP037 | quoted-annotation |
| 3 | PTH201 | path-constructor-current-directory |
| 3 | RUF059 | unused-unpacked-variable |
| 3 | SIM105 | suppressible-exception |
| 3 | SIM117 | multiple-with-statements |
| ≤2 | (10 more rules) | various |

**Total: 2268 errors** (354 auto-fixable, 335 with `--unsafe-fixes`)

**Dominant finding**: RUF002 (ambiguous unicode in docstrings) = 1349 / 59%.
These are Turkish characters in docstrings. Fixing requires a deliberate decision
on docstring encoding policy.

### 4.2 Vulture (dead code — Python)

Command: `vulture src/ --min-confidence 80`

| File | Symbol | Confidence |
|---|---|---|
| `data_sources/service.py:96` | `business_days` (unused variable) | 100% |
| `rules/service.py:73` | `business_days` (unused variable) | 100% |

**Total: 2 findings** — both are unused variables, likely dead code from refactoring.

### 4.3 ESLint (Frontend)

Command: `eslint src/`

| Severity | Count | Dominant rule |
|---|---:|---|
| warning | 709 | `no-unused-vars` (unused imports) |
| error | 0 | — |

All 709 warnings are unused imports/variables. These are candidates for cleanup
but not blocking.

### 4.4 Knip (unused exports — Frontend)

Command: `knip`

| Category | Count |
|---|---:|
| Unused devDependencies | 1 (`@babel/preset-typescript` — needed at runtime by eslint) |
| Unused exports | 12 |
| Unused exported types | 18 |
| Duplicate exports | 1 |
| Configuration hints | 12 |

Unused exports are API surface that may be consumed by future features or
external integrations. Triage needed before removal.

### 4.5 jscpd (copy-paste detection)

Command: `jscpd --config .jscpd.json src/ frontend/src/`

| Metric | Value |
|---|---|
| Files analyzed | 249 |
| Total lines | 60,320 |
| Clones found | 177 |
| Duplicated lines | 2,250 (3.73%) |
| Duplicated tokens | 13,530 (4.33%) |

Breakdown by language:
- Python: 150 clones, 1,773 duplicated lines
- TypeScript: 27 clones, 319 duplicated lines (6.69% of TS)

### 4.6 Semgrep

No custom rules in `tools/semgrep/rules/` yet. GQ-03 iteration will add them.

### 4.7 Coverage

| Scope | Lines | Covered | Missing | Coverage % |
|---|---:|---:|---:|---:|
| Python (src/) | 23,810 | 18,175 | 5,635 | **76%** |
| Frontend | — | — | — | not yet measured |

---

## 5. Unified Commands

```bash
# Blocking checks only
./scripts/check_quality.sh

# Blocking + advisory
./scripts/check_quality.sh --all

# Advisory only
./scripts/check_quality.sh --advisory

# Individual tools
ruff check .                                    # Python lint (blocking)
ruff format --check .                           # Python format (blocking)
pytest -q                                       # Python tests
mypy src                                        # Python types
vulture src/ --min-confidence 80                # Python dead code
ruff check --select W,I,B,UP,SIM,TCH,A,PTH,RUF .  # Extended advisory

cd frontend
npm run typecheck                               # TS type check
npm test                                        # Vitest
npm run build                                   # Vite build
npm run test:coverage                           # Coverage with v8
npm run lint:advisory                           # ESLint (all warnings)
npm run dead-code                               # Knip
npm run copy-paste                              # jscpd
```

---

## 6. Rollback

All changes in this iteration are configuration-only:
- `pyproject.toml` — added tool configs, test deps
- `frontend/package.json` — added devDeps, scripts
- `frontend/eslint.config.js` — new file
- `frontend/vitest.config.ts` — added coverage config
- `frontend/knip.json` — new file
- `.jscpd.json` — new file
- `scripts/check_quality.sh` — new file
- `scripts/vulture_whitelist.txt` — new file

Revert: `git checkout -- pyproject.toml frontend/` and remove new files.
