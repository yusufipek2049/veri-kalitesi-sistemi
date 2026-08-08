#!/bin/sh
set -eu

secret_dir=/run/secrets/data-sources/e2e-source
username_file="$secret_dir/username"
password_file="$secret_dir/password"

if [ ! -s "$username_file" ] || [ ! -s "$password_file" ]; then
  echo "E2E source username/password files are required in $secret_dir" >&2
  exit 1
fi

reader_name=$(tr -d '\r\n' < "$username_file")
reader_password=$(tr -d '\r\n' < "$password_file")
if [ "$reader_name" != "dq_e2e_reader" ] || [ -z "$reader_password" ]; then
  echo "E2E source username must be dq_e2e_reader and password must not be empty" >&2
  exit 1
fi

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=reader_name="$reader_name" \
  --set=reader_password="$reader_password" <<'SQL'
SELECT format(
  'CREATE ROLE %I LOGIN PASSWORD %L',
  :'reader_name',
  :'reader_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'reader_name')
\gexec
SQL
