#!/bin/sh
set -eu

export KC_BOOTSTRAP_ADMIN_USERNAME=lab-admin
KC_BOOTSTRAP_ADMIN_PASSWORD=$(cat /run/secrets/keycloak_admin_password)
export KC_BOOTSTRAP_ADMIN_PASSWORD
LAB_USER_PASSWORD=$(cat /run/secrets/keycloak_lab_user_password)
export LAB_USER_PASSWORD

exec /opt/keycloak/bin/kc.sh start-dev \
    --health-enabled=true \
    --http-enabled=true \
    --hostname-strict=false \
    --import-realm
