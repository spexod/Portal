#!/bin/bash
# Helper for upgrading the MySQL server's major version (for example 8.4 -> 9.7).
# Run from the Portal directory with the mysqlDB container running.
# On Linux servers, run with sudo: the data directory belongs to the container's mysql user.
#
#   ./mysql/upgrade.sh check            Print the server version and each account's authentication
#                                       plugin, and save a fingerprint of the data (tables per schema,
#                                       rows per metadata table) as mysql/fingerprint-<version>-<time>.txt.
#                                       Run it before and after an upgrade, then diff the two files.
#   ./mysql/upgrade.sh checker 9.7      Run MySQL Shell's upgrade checker from the target version's
#                                       image against the running server (read-only).
#   ./mysql/upgrade.sh backup           Stop the other containers, save a fingerprint and a full
#                                       mysqldump, shut MySQL down cleanly, then copy the data
#                                       directory to mysql/local-<version>-<time>/.
#   ./mysql/upgrade.sh dump             Save a fingerprint and a compressed dump of the application
#                                       schemas (not the mysql system schema with its accounts) to
#                                       mysql/dump-<version>-<time>.sql.gz. Consistent, and the site
#                                       keeps running. Use it to copy production to a local database.
#   ./mysql/upgrade.sh restore <file>   Load a dump (.sql or .sql.gz) into the running server. Tables
#                                       in the dumped schemas are replaced; asks for confirmation.
#
# A major-version upgrade rewrites ./mysql/local in place the first time the new version starts,
# and it cannot be undone. The data directory copy made by "backup" is the way back: restore it
# into ./mysql/local and set MYSQL_VERSION back to the old version.
set -euo pipefail
cd "$(dirname "$0")/.."

# Shell code run inside the mysqlDB container. "$0" is the client program (mysql or mysqldump)
# and "$@" its arguments. The root password comes from the container's MYSQL_ROOT_PASSWORD
# through a temporary option file, so it never appears on a command line.
run_as_root='
cnf=$(mktemp)
printf "[client]\nuser=root\npassword=\"%s\"\n" "$MYSQL_ROOT_PASSWORD" > "$cnf"
"$0" --defaults-extra-file="$cnf" "$@"
status=$?
rm -f "$cnf"
exit $status
'

in_mysql() {
    docker compose exec -T mysqlDB sh -c "$run_as_root" "$@"
}

query() {
    in_mysql mysql --batch --skip-column-names --raw -e "$1"
}

server_version() {
    query "SELECT VERSION()"
}

fingerprint() {
    echo "# MySQL server version"
    server_version
    echo "# tables per schema"
    query "SELECT table_schema, COUNT(*) FROM information_schema.tables
           WHERE table_schema NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
           GROUP BY table_schema ORDER BY table_schema"
    echo "# rows per table in the metadata schemas"
    local counts_sql
    counts_sql=$(query "SET SESSION group_concat_max_len = 16777216;
        SELECT GROUP_CONCAT(
            CONCAT('SELECT ', QUOTE(CONCAT(table_schema, '.', table_name)), ' AS tbl, COUNT(*) AS n FROM ',
                   CHAR(96 USING utf8mb4), table_schema, CHAR(96 USING utf8mb4), '.',
                   CHAR(96 USING utf8mb4), table_name, CHAR(96 USING utf8mb4))
            SEPARATOR ' UNION ALL ')
        FROM information_schema.tables
        WHERE table_type = 'BASE TABLE'
          AND table_schema IN ('spexodisks', 'new_spexodisks', 'users', 'data_status')")
    if [ -n "$counts_sql" ] && [ "$counts_sql" != "NULL" ]; then
        query "SELECT tbl, n FROM (${counts_sql}) AS counts ORDER BY tbl"
    fi
}

check() {
    local version file
    version=$(server_version)
    file="mysql/fingerprint-${version}-$(date +%Y%m%d-%H%M%S).txt"
    echo "MySQL server version: ${version}"
    echo
    echo "Accounts and their authentication plugins"
    echo "(accounts using mysql_native_password cannot log in on MySQL 9.x):"
    in_mysql mysql --table -e "SELECT user, host, plugin FROM mysql.user ORDER BY user, host"
    echo
    fingerprint > "$file"
    echo "Fingerprint saved to ${file}"
}

checker() {
    local target="${1:?usage: ./mysql/upgrade.sh checker <target version, for example 9.7>}"
    local network password
    network=$(docker inspect mysqlDB --format '{{range $name, $net := .NetworkSettings.Networks}}{{$name}}{{end}}')
    password=$(docker compose exec -T mysqlDB printenv MYSQL_ROOT_PASSWORD)
    echo "Running the MySQL ${target} upgrade checker against the running server (read-only)..."
    printf '%s\n' "$password" | docker run --rm -i --platform linux/amd64 --network "$network" \
        "mysql:${target}" mysqlsh --uri=root@mysqlDB:3306 --passwords-from-stdin -- util check-for-server-upgrade
}

backup() {
    local version stamp dump datadir_copy others logs
    version=$(server_version)
    stamp=$(date +%Y%m%d-%H%M%S)
    dump="mysql/backup-${version}-${stamp}.sql"
    datadir_copy="mysql/local-${version}-${stamp}"

    others=$(docker compose ps --services --status running | grep -vx mysqlDB || true)
    if [ -n "$others" ]; then
        echo "Stopping the other containers so nothing writes to the database: $(echo $others)"
        # shellcheck disable=SC2086
        docker compose stop $others
    fi

    echo "Saving a fingerprint to mysql/fingerprint-${version}-${stamp}.txt..."
    fingerprint > "mysql/fingerprint-${version}-${stamp}.txt"

    echo "Writing a full logical backup to ${dump} (this can take a while)..."
    in_mysql mysqldump --all-databases --single-transaction --routines --events --triggers > "$dump"

    echo "Shutting down MySQL ${version} cleanly (slow shutdown, can take a few minutes)..."
    query "SET GLOBAL innodb_fast_shutdown = 0"
    docker compose stop --timeout 600 mysqlDB
    logs=$(docker compose logs --tail 50 mysqlDB 2>&1 || true)
    case "$logs" in
        *"Shutdown complete"*) echo "Clean shutdown confirmed in the mysqlDB logs." ;;
        *) echo "WARNING: could not confirm a clean shutdown; check 'docker compose logs mysqlDB' before upgrading." ;;
    esac

    echo "Copying the data directory ($(du -sh mysql/local | cut -f1)) to ${datadir_copy}..."
    cp -a mysql/local "$datadir_copy"

    echo
    echo "Backup complete:"
    echo "  logical dump:        ${dump}  (restore only into MySQL ${version})"
    echo "  data directory copy: ${datadir_copy}"
    echo "Next: set MYSQL_VERSION in .env to the new version, then run"
    echo "  docker compose up mysqlDB --detach && docker compose logs --follow mysqlDB"
}

dump() {
    local version stamp file schemas
    version=$(server_version)
    stamp=$(date +%Y%m%d-%H%M%S)
    file="mysql/dump-${version}-${stamp}.sql.gz"
    schemas=$(query "SELECT schema_name FROM information_schema.schemata
                     WHERE schema_name NOT IN ('mysql', 'sys', 'information_schema', 'performance_schema')
                     ORDER BY schema_name")

    echo "Saving a fingerprint to mysql/fingerprint-${version}-${stamp}.txt..."
    fingerprint > "mysql/fingerprint-${version}-${stamp}.txt"

    echo "Dumping the schemas $(echo $schemas) to ${file} (the site keeps running)..."
    # shellcheck disable=SC2086
    in_mysql mysqldump --single-transaction --routines --events --triggers --set-gtid-purged=OFF \
        --databases $schemas | gzip > "$file" || { rm -f "$file"; echo "Dump failed." >&2; exit 1; }
    echo "Dump complete: ${file} ($(du -h "$file" | cut -f1))"
}

restore() {
    local file="${1:?usage: ./mysql/upgrade.sh restore <dump file, .sql or .sql.gz>}"
    local version answer old_flush
    [ -f "$file" ] || { echo "No such file: ${file}" >&2; exit 1; }
    version=$(server_version)
    echo "This loads ${file} into MySQL ${version} in the mysqlDB container on $(hostname)."
    echo "Tables in the schemas inside the dump are dropped and replaced. Other schemas are not touched."
    read -r -p "Type 'restore' to continue: " answer
    [ "$answer" = "restore" ] || { echo "Cancelled."; exit 1; }

    # Flush the redo log about once per second instead of at every commit while loading: much
    # faster for a large dump. The previous value is put back when the script exits.
    old_flush=$(query "SELECT @@GLOBAL.innodb_flush_log_at_trx_commit")
    trap 'query "SET GLOBAL innodb_flush_log_at_trx_commit = '"${old_flush}"'"' EXIT
    query "SET GLOBAL innodb_flush_log_at_trx_commit = 2"

    echo "Loading ${file} (a large dump can take a long time)..."
    case "$file" in
        *.gz) gunzip -c "$file" | in_mysql mysql ;;
        *) in_mysql mysql < "$file" ;;
    esac
    echo "Restore complete. Run ./mysql/upgrade.sh check to save a fingerprint to compare."
}

case "${1:-}" in
    check) check ;;
    checker) checker "${2:-}" ;;
    backup) backup ;;
    dump) dump ;;
    restore) restore "${2:-}" ;;
    *) echo "usage: ./mysql/upgrade.sh check | checker <version> | backup | dump | restore <file>" >&2; exit 1 ;;
esac
