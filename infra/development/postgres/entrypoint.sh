#!/bin/sh
set -eu

tls_dir=/run/postgres-tls
certificate="$tls_dir/server.crt"
private_key="$tls_dir/server.key"

mkdir -p "$tls_dir"
if [ ! -s "$certificate" ] || [ ! -s "$private_key" ]; then
  openssl req -x509 -newkey rsa:2048 -sha256 -nodes \
    -days 30 \
    -subj "/CN=postgres" \
    -addext "subjectAltName=DNS:postgres,DNS:localhost,IP:127.0.0.1" \
    -keyout "$private_key" \
    -out "$certificate"
fi
chown postgres:postgres "$certificate" "$private_key"
chmod 0644 "$certificate"
chmod 0600 "$private_key"

exec /usr/local/bin/docker-entrypoint.sh "$@" \
  -c ssl=on \
  -c "ssl_cert_file=$certificate" \
  -c "ssl_key_file=$private_key"
