# Hermes + Claude Code + Codex Pipeline Bundle

Bu paket minimum çalışan, dosya tabanlı dört aşamalı hattı içerir.

## Projeye kopyalama

```bash
cp -a hermes-claude-codex-pipeline/schemas <repo>/.agent-handoff/
cp -a hermes-claude-codex-pipeline/prompts <repo>/.agent-handoff/
cp -a hermes-claude-codex-pipeline/scripts <repo>/.agent-handoff/
cp hermes-claude-codex-pipeline/examples/REQUEST.smoke-test.md <repo>/.agent-handoff/REQUEST.md
chmod +x <repo>/.agent-handoff/scripts/*.sh
```

Önce `preflight.sh`, ardından temiz bir git worktree içinde `run-pipeline.sh` çalıştırın.

Script hiçbir commit, push, merge veya PR işlemi yapmaz. Claude aşamaları plan/read-only modundadır. Codex oturumları her aşamada yeni `codex exec` süreçleridir.
