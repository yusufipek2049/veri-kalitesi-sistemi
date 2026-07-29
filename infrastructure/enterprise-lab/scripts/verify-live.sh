#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
lab_dir=$(dirname "$script_dir")
compose_file="$lab_dir/compose.yaml"

"$script_dir/bootstrap-secrets.sh"
docker compose -f "$compose_file" config --quiet
docker compose -f "$compose_file" up -d --build --wait --wait-timeout 240
docker compose -f "$compose_file" --profile acceptance up \
    --no-deps \
    --build \
    --force-recreate \
    --abort-on-container-exit \
    --exit-code-from adapter-e2e \
    adapter-e2e
