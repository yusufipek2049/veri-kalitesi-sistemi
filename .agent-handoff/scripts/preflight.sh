#!/usr/bin/env bash
set -u

printf '=== Platform ===\n'
printf 'WSL_DISTRO_NAME=%s\n' "${WSL_DISTRO_NAME:-not-set}"
uname -a
printf 'HOME=%s\nPATH=%s\n' "$HOME" "$PATH"

printf '\n=== Repository ===\n'
pwd
git rev-parse --show-toplevel
git status --short

printf '\n=== Hermes ===\n'
command -v hermes || true
hermes --version || true
hermes skills list 2>/dev/null | grep -E 'claude-code|codex|terminal' || true

printf '\n=== Claude Code ===\n'
command -v claude || true
claude --version || true
claude auth status --text || true
claude doctor || true

printf '\n=== Codex ===\n'
command -v codex || true
codex --version || true
codex login status || true
codex doctor --summary 2>/dev/null || codex doctor 2>/dev/null || true

printf '\n=== Helpers ===\n'
command -v jq || true
command -v sha256sum || true
command -v git || true
