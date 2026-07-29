#!/bin/sh
set -eu

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$PGDATA"
    chown -R postgres:postgres "$PGDATA"
    install -o postgres -g postgres -m 0400 \
        /run/secrets/postgres_replication_password /tmp/postgres_replication_password
    exec gosu postgres "$0" "$@"
fi

if [ ! -s "$PGDATA/PG_VERSION" ]; then
    export PGPASSWORD
    PGPASSWORD=$(cat /tmp/postgres_replication_password)
    until pg_isready --host postgres-primary --username lab_replicator --dbname postgres; do
        sleep 2
    done
    pg_basebackup \
        --host postgres-primary \
        --username lab_replicator \
        --pgdata "$PGDATA" \
        --format plain \
        --wal-method stream \
        --write-recovery-conf \
        --no-password
    chmod 700 "$PGDATA"
    unset PGPASSWORD
fi

exec /usr/local/bin/docker-entrypoint.sh postgres
