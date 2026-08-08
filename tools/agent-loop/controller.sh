#!/usr/bin/env bash
# tools/agent-loop/controller.sh
#
# Agent-loop çekirdek sürücüsü. Tek instance flock ile korunur; kalıcı kütüphaneyi
# (lib.sh) yükler, runtime .agent-handoff alanını kurar ve state-machine main()
# döngüsünü çalıştırır.
#
# Kullanım: controller.sh continue [not|görev|karar]
#
# ROOT ve TOOLS_DIR bu dosyanın konumundan çözülür; env-file yapılandırma sağlar.
set -uo pipefail

TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${AGENT_LOOP_TARGET:-$(cd "$TOOLS_DIR/../.." && pwd)}"
ENV_FILE="${AGENT_LOOP_ENV_FILE:-$HOME/.config/veri-kalitesi/agent-loop.env}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  # AGENT_LOOP_TARGET env-file'da tanımlıysa onu kullan.
  ROOT="${AGENT_LOOP_TARGET:-$ROOT}"
fi

# shellcheck source=tools/agent-loop/lib.sh
source "$TOOLS_DIR/lib.sh"

# Rol yapılandırması geçersizse init fail-closed döner: hiçbir ajan başlatılmaz.
if ! agentloop_init "$ROOT" "$TOOLS_DIR"; then
  echo "agent-loop başlatılamadı (rol yapılandırması geçersiz)." >&2
  echo "Düzeltmek için: .agent/config/agents.yaml" >&2
  exit 36
fi

# Tek instance koruması: kilit alınamazsa sessizce çık (paralel çalışmaz).
exec 9>"$H/state/pipeline.lock"
if ! flock -n 9; then
  echo "Agent loop zaten çalışıyor."
  exit 0
fi

main "$@"
