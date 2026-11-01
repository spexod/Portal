#!/bin/bash
# Create (or reset) the two database accounts of mysql/users.sql on the running mysqlDB container.
#
#   ./mysql/create-users.sh            # names and passwords from .env:
#                                      #   MYSQL_API_USER (default spexo_api), MYSQL_API_PASSWORD,
#                                      #   MYSQL_PIPELINE_USER (default spexo_pipeline), MYSQL_PIPELINE_PASSWORD
#
# Runs as root inside the container (the root password comes from the container's environment, as in
# mysql/upgrade.sh). Idempotent. The passwords must not contain a single quote.
set -euo pipefail
cd "$(dirname "$0")/.."

env_value() { grep -E "^$1=" .env 2>/dev/null | tail -n1 | cut -d= -f2- | tr -d "\"'"; }
api_user=$(env_value MYSQL_API_USER); api_user=${api_user:-spexo_api}
pipeline_user=$(env_value MYSQL_PIPELINE_USER); pipeline_user=${pipeline_user:-spexo_pipeline}
api_password=$(env_value MYSQL_API_PASSWORD)
pipeline_password=$(env_value MYSQL_PIPELINE_PASSWORD)
[ -n "$api_password" ] || { echo "set MYSQL_API_PASSWORD in .env" >&2; exit 1; }
[ -n "$pipeline_password" ] || { echo "set MYSQL_PIPELINE_PASSWORD in .env" >&2; exit 1; }
case "$api_password$pipeline_password" in *"'"*) echo "the passwords must not contain a single quote" >&2; exit 1;; esac

run_as_root='
cnf=$(mktemp)
printf "[client]\nuser=root\npassword=\"%s\"\n" "$MYSQL_ROOT_PASSWORD" > "$cnf"
mysql --defaults-extra-file="$cnf" --table
status=$?
rm -f "$cnf"
exit $status
'
sed -e "s|__API_USER__|$api_user|g" -e "s|__API_PASSWORD__|$api_password|g" \
    -e "s|__PIPELINE_USER__|$pipeline_user|g" -e "s|__PIPELINE_PASSWORD__|$pipeline_password|g" mysql/users.sql \
    | docker compose exec -T mysqlDB sh -c "$run_as_root"
echo "accounts $api_user and $pipeline_user are set; put the four MYSQL_*_USER/PASSWORD values in every .env that connects"
