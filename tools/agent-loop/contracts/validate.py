#!/usr/bin/env python3
"""tools/agent-loop/contracts/validate.py

Fail-closed contract validator for schema v3.

Usage:
    python3 validate.py <contract.json>
    python3 validate.py --check-must-disappear <contract.json> <repo-root>
    python3 validate.py --check-forbidden-substitutes <contract.json> <repo-root>
    python3 validate.py --post-impl <contract.json> <repo-root>

Exit codes:
    0  Contract is valid / checks passed
    1  Contract is invalid (fail-closed)
    2  Usage error

Design principles:
    - schema_version MUST be exactly 3. No v2 fallback, no shim.
    - All required fields must be present.
    - additionalProperties: false is enforced.
    - must_disappear and forbidden_substitutes are deterministic, file-based checks.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def _fail(msg: str) -> int:
    print(f"CONTRACT_INVALID: {msg}", file=sys.stderr)
    return 1


def _load(path: str) -> dict | None:
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        _fail(f"cannot load contract: {e}")
        return None


# --- Schema v3 structural validation ----------------------------------------

_REQUIRED_TOP = {"schema_version", "contract_status", "iteration", "task",
                 "repository", "scope", "acceptance_criteria"}
_ALLOWED_TOP = _REQUIRED_TOP | {"must_disappear", "forbidden_substitutes",
                                 "runtime_rules", "created_at", "updated_at"}

_REQUIRED_TASK = {"id", "title", "objective", "selection_mode", "source"}
_ALLOWED_TASK = _REQUIRED_TASK

_REQUIRED_SOURCE = {"type"}
_ALLOWED_SOURCE = _REQUIRED_SOURCE | {"reference"}
_VALID_SOURCE_TYPES = {"user_objective", "backlog", "bootstrap"}

_REQUIRED_REPO = {"root", "branch", "base_ref"}
_ALLOWED_REPO = _REQUIRED_REPO | {"base_ref_policy"}

_REQUIRED_SCOPE = {"allowed_files"}
_ALLOWED_SCOPE = _REQUIRED_SCOPE | {"forbidden_patterns", "forbidden_git_operations"}

_VALID_STATUSES = {"BOOTSTRAP", "READY", "IN_PROGRESS", "COMPLETED", "FAILED"}
_VALID_SELECTION_MODES = {"manual", "automatic", "backlog"}


def validate_contract(data: dict) -> str | None:
    """Return error message or None if valid."""
    # --- top-level ---
    missing = _REQUIRED_TOP - set(data.keys())
    if missing:
        return f"missing required top-level fields: {sorted(missing)}"
    extra = set(data.keys()) - _ALLOWED_TOP
    if extra:
        return f"unexpected top-level fields: {sorted(extra)}"

    # schema_version must be exactly 3
    sv = data.get("schema_version")
    if sv != 3:
        return f"schema_version must be 3, got {sv!r}. Schema v2 is not supported."

    # contract_status
    cs = data.get("contract_status")
    if cs not in _VALID_STATUSES:
        return f"invalid contract_status: {cs!r}"

    # iteration
    it = data.get("iteration")
    if not isinstance(it, int) or it < 0:
        return f"iteration must be non-negative integer, got {it!r}"

    # --- task ---
    task = data.get("task", {})
    if not isinstance(task, dict):
        return "task must be an object"
    missing_t = _REQUIRED_TASK - set(task.keys())
    if missing_t:
        return f"task missing required fields: {sorted(missing_t)}"
    extra_t = set(task.keys()) - _ALLOWED_TASK
    if extra_t:
        return f"task has unexpected fields: {sorted(extra_t)}"
    for k in ("id", "title", "objective"):
        v = task.get(k)
        if not isinstance(v, str) or not v.strip():
            return f"task.{k} must be non-empty string"
    if task["selection_mode"] not in _VALID_SELECTION_MODES:
        return f"task.selection_mode invalid: {task['selection_mode']!r}"

    # --- task.source ---
    source = task.get("source", {})
    if not isinstance(source, dict):
        return "task.source must be an object"
    missing_s = _REQUIRED_SOURCE - set(source.keys())
    if missing_s:
        return f"task.source missing: {sorted(missing_s)}"
    extra_s = set(source.keys()) - _ALLOWED_SOURCE
    if extra_s:
        return f"task.source unexpected fields: {sorted(extra_s)}"
    if source["type"] not in _VALID_SOURCE_TYPES:
        return f"task.source.type invalid: {source['type']!r}"

    # Reject legacy v2 fields on task
    for legacy in ("source_docs", "source_work_package", "priority_reason"):
        if legacy in task:
            return f"legacy v2 field task.{legacy} is not allowed in v3"

    # --- repository ---
    repo = data.get("repository", {})
    if not isinstance(repo, dict):
        return "repository must be an object"
    missing_r = _REQUIRED_REPO - set(repo.keys())
    if missing_r:
        return f"repository missing: {sorted(missing_r)}"
    extra_r = set(repo.keys()) - _ALLOWED_REPO
    if extra_r:
        return f"repository unexpected: {sorted(extra_r)}"

    # --- scope ---
    scope = data.get("scope", {})
    if not isinstance(scope, dict):
        return "scope must be an object"
    missing_sc = _REQUIRED_SCOPE - set(scope.keys())
    if missing_sc:
        return f"scope missing: {sorted(missing_sc)}"
    extra_sc = set(scope.keys()) - _ALLOWED_SCOPE
    if extra_sc:
        return f"scope unexpected: {sorted(extra_sc)}"
    af = scope.get("allowed_files")
    if not isinstance(af, list):
        return "scope.allowed_files must be an array"
    for item in af:
        if not isinstance(item, str) or not item.strip():
            return "scope.allowed_files items must be non-empty strings"

    # --- must_disappear ---
    md = data.get("must_disappear")
    if md is not None:
        if not isinstance(md, list):
            return "must_disappear must be an array"
        for item in md:
            if not isinstance(item, str) or not item.strip():
                return "must_disappear items must be non-empty strings"

    # --- forbidden_substitutes ---
    fs = data.get("forbidden_substitutes")
    if fs is not None:
        if not isinstance(fs, list):
            return "forbidden_substitutes must be an array"
        for pat in fs:
            if not isinstance(pat, str):
                return "forbidden_substitutes items must be strings"
            try:
                re.compile(pat)
            except re.error as e:
                return f"forbidden_substitutes invalid regex {pat!r}: {e}"

    # --- acceptance_criteria ---
    ac = data.get("acceptance_criteria")
    if not isinstance(ac, list):
        return "acceptance_criteria must be an array"
    for item in ac:
        if not isinstance(item, dict):
            return "acceptance_criteria items must be objects"
        if "id" not in item or "requirement" not in item:
            return "acceptance_criteria items need id and requirement"

    return None


# --- Deterministic file-based checks ----------------------------------------

def check_must_disappear(data: dict, repo_root: str) -> tuple[bool, list[str]]:
    """Check must_disappear files/patterns.

    Pre-impl: returns (ok, messages) where ok=True means files exist (task valid).
    Post-impl: returns (ok, messages) where ok=True means files are gone (task done).
    """
    md = data.get("must_disappear") or []
    if not md:
        return True, ["no must_disappear constraints"]
    messages = []
    all_ok = True
    for pattern in md:
        p = Path(repo_root) / pattern
        matches = list(Path(repo_root).glob(pattern)) if "*" in pattern else [p]
        for m in matches:
            if m.exists():
                messages.append(f"EXISTS: {m.relative_to(repo_root)}")
                all_ok = False
            else:
                messages.append(f"GONE: {pattern}")
    if not messages:
        messages.append("no matches found for patterns")
    return all_ok, messages


def check_forbidden_substitutes(data: dict, repo_root: str) -> tuple[bool, list[str]]:
    """Check that forbidden_substitutes patterns don't appear in the repo."""
    fs = data.get("forbidden_substitutes") or []
    if not fs:
        return True, ["no forbidden_substitutes constraints"]
    messages = []
    all_ok = True
    # Scan source files for forbidden patterns
    scan_dirs = ["src", "tests"]
    for scan_dir in scan_dirs:
        base = Path(repo_root) / scan_dir
        if not base.exists():
            continue
        for fpath in base.rglob("*"):
            if not fpath.is_file() or not fpath.suffix in (".py", ".ts", ".tsx", ".js", ".sh"):
                continue
            try:
                content = fpath.read_text(errors="replace")
            except OSError:
                continue
            for pat in fs:
                try:
                    if re.search(pat, content):
                        rel = fpath.relative_to(repo_root)
                        messages.append(f"FOUND: pattern={pat!r} in {rel}")
                        all_ok = False
                except re.error:
                    pass
    if not messages:
        messages.append("no forbidden patterns found")
    return all_ok, messages


def check_out_of_scope(data: dict, repo_root: str, changed_files: list[str]) -> tuple[bool, list[str]]:
    """Check that changed files are within allowed scope."""
    allowed = data.get("scope", {}).get("allowed_files", [])
    if not allowed:
        return True, ["no allowed_files constraint (minimal scope derived by implementer)"]
    messages = []
    all_ok = True
    allowed_set = set(allowed)
    for f in changed_files:
        if f not in allowed_set:
            messages.append(f"OUT_OF_SCOPE: {f}")
            all_ok = False
        else:
            messages.append(f"OK: {f}")
    if not messages:
        messages.append("no changes detected")
    return all_ok, messages


# --- CLI entry point --------------------------------------------------------

def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("Usage: validate.py [--check-must-disappear|--check-forbidden-substitutes"
              "|--post-impl|--check-scope] <contract.json> [repo-root] [changed-files...]",
              file=sys.stderr)
        return 2

    mode = "validate"
    if args[0].startswith("--"):
        mode = args[0].lstrip("-")
        args = args[1:]

    if not args:
        print("Missing contract path", file=sys.stderr)
        return 2

    contract_path = args[0]
    data = _load(contract_path)
    if data is None:
        return 1

    if mode == "validate":
        err = validate_contract(data)
        if err:
            return _fail(err)
        print("CONTRACT_VALID schema_version=3")
        return 0

    # Modes that need repo root
    if len(args) < 2:
        print("Missing repo-root argument", file=sys.stderr)
        return 2
    repo_root = args[1]

    if mode == "check-must-disappear":
        ok, msgs = check_must_disappear(data, repo_root)
        for m in msgs:
            print(m)
        print(f"MUST_DISAPPEAR={'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1

    if mode == "check-forbidden-substitutes":
        ok, msgs = check_forbidden_substitutes(data, repo_root)
        for m in msgs:
            print(m)
        print(f"FORBIDDEN_SUBSTITUTES={'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1

    if mode == "check-scope":
        changed = args[2:] if len(args) > 2 else []
        ok, msgs = check_out_of_scope(data, repo_root, changed)
        for m in msgs:
            print(m)
        print(f"SCOPE_CHECK={'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1

    if mode == "post-impl":
        # Run all post-implementation checks
        rc = 0
        # 1. must_disappear: files should be GONE
        md = data.get("must_disappear") or []
        if md:
            ok, msgs = check_must_disappear(data, repo_root)
            for m in msgs:
                print(m)
            if not ok:
                print("POST_IMPL: must_disappear files still exist")
                rc = 1
            else:
                print("POST_IMPL: must_disappear OK")

        # 2. forbidden_substitutes: patterns should NOT be present
        fs = data.get("forbidden_substitutes") or []
        if fs:
            ok, msgs = check_forbidden_substitutes(data, repo_root)
            for m in msgs:
                print(m)
            if not ok:
                print("POST_IMPL: forbidden_substitutes detected")
                rc = 1
            else:
                print("POST_IMPL: forbidden_substitutes OK")

        # 3. scope check
        if len(args) > 2:
            changed = args[2:]
            ok, msgs = check_out_of_scope(data, repo_root, changed)
            for m in msgs:
                print(m)
            if not ok:
                print("POST_IMPL: out-of-scope changes detected")
                rc = 1
            else:
                print("POST_IMPL: scope OK")

        return rc

    print(f"Unknown mode: {mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
