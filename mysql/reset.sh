#!/bin/bash
# Delete the local MySQL data directory (mysql/local). The database is initialized again from the
# files in mysql/init the next time the mysqlDB container starts. Not for the production server.
set -euo pipefail
cd "$(dirname "$0")/.."
if docker compose ps --services --status running 2>/dev/null | grep -qx mysqlDB; then
    echo "mysqlDB is running, stop it first: docker compose --profile db down" >&2
    exit 1
fi
read -r -p "Delete every database file in $PWD/mysql/local? [y/N] " answer
[ "$answer" = "y" ] || { echo "nothing deleted"; exit 1; }
cd mysql/local
rm -rf -- * .cache
echo "deleted, the database is initialized from mysql/init at the next start"
