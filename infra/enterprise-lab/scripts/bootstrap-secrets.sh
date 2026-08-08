#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
lab_dir=$(dirname "$script_dir")
secret_dir="$lab_dir/runtime-secrets"

umask 077
mkdir -p "$secret_dir"

for name in \
    keycloak_admin_password \
    keycloak_lab_user_password \
    lab_fault_control_token \
    local_secret_manager_token \
    postgres_admin_password \
    postgres_app_password \
    postgres_replication_password \
    rabbitmq_password
do
    target="$secret_dir/$name"
    if [ ! -s "$target" ]; then
        openssl rand -hex 32 >"$target"
    fi
    chmod 600 "$target"
done

echo "ENTERPRISE-LAB-01/02/03 runtime secret files are ready (values are not printed)."
