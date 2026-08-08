#!/bin/sh
set -eu

password=$(cat /run/secrets/rabbitmq_password)
umask 077
{
    printf 'default_user = lab_operator\n'
    printf 'default_pass = %s\n' "$password"
    printf 'loopback_users.lab_operator = false\n'
} >/tmp/rabbitmq.conf
chown rabbitmq:rabbitmq /tmp/rabbitmq.conf
unset password

export RABBITMQ_CONFIG_FILE=/tmp/rabbitmq
exec docker-entrypoint.sh rabbitmq-server
