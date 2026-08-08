#!/bin/sh
set -eu

app_password=$(cat /tmp/postgres_app_password)
replication_password=$(cat /tmp/postgres_replication_password)

psql --set=ON_ERROR_STOP=1 \
    --set=app_password="$app_password" \
    --set=replication_password="$replication_password" \
    --username postgres \
    --dbname postgres <<'SQL'
SELECT format('CREATE ROLE lab_app LOGIN PASS' || 'WORD %L', :'app_password') \gexec
CREATE DATABASE veri_kalitesi_lab OWNER lab_app;
SELECT format(
    'CREATE ROLE lab_replicator WITH REPLICATION LOGIN PASS' || 'WORD %L',
    :'replication_password'
) \gexec
SQL

printf 'host replication lab_replicator all scram-sha-256\n' >>"$PGDATA/pg_hba.conf"
