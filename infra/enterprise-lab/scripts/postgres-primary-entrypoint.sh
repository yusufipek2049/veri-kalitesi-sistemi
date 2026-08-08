#!/bin/sh
set -eu

if [ "$(id -u)" = "0" ]; then
    install -o postgres -g postgres -m 0400 \
        /run/secrets/postgres_admin_password /tmp/postgres_admin_password
    install -o postgres -g postgres -m 0400 \
        /run/secrets/postgres_app_password /tmp/postgres_app_password
    install -o postgres -g postgres -m 0400 \
        /run/secrets/postgres_replication_password /tmp/postgres_replication_password
fi

export POSTGRES_PASSWORD_FILE=/tmp/postgres_admin_password
exec /usr/local/bin/docker-entrypoint.sh "$@"
