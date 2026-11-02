#!/bin/bash
# Load the current Let's Encrypt certificate into nginx and MySQL, without restarting either.
#
# Run by the systemd unit spexodisks-certs-changed.service when certbot replaces the certificate
# (see "Certificate renewal with systemd" in shell/ssl.md). To run it by hand on the server:
#   sudo systemctl start spexodisks-certs-changed.service     (output: journalctl -u spexodisks-certs-changed)
set -euo pipefail
cd "$(dirname "$0")/.."

# Run SQL as root in the mysqlDB container, over the local socket. The password comes from the
# container's MYSQL_ROOT_PASSWORD through a temporary option file (as in mysql/upgrade.sh), so it
# never appears on a command line, where any user on the host can read it while the client runs.
mysql_root() {
    docker compose exec -T mysqlDB sh -c \
        'cnf=$(mktemp)
         printf "[client]\nuser=root\npassword=\"%s\"\n" "$MYSQL_ROOT_PASSWORD" > "$cnf"
         mysql --defaults-extra-file="$cnf" --batch --skip-column-names -e "$1"; status=$?
         rm -f "$cnf"
         exit $status' sh "$1"
}

# Make MySQL's copy of the certificate. certbot's deploy hook already does this after a renewal;
# repeating it is harmless and also covers certificates replaced in other ways (certbot certonly).
echo "Copying the certificate for MySQL..."
docker compose run --rm --no-deps -T --entrypoint /bin/sh certbot \
    /etc/letsencrypt/renewal-hooks/deploy/mysql-ssl.sh

echo "Reloading nginx..."
docker compose exec -T nginx nginx -s reload

# If the new certificate does not validate, the reload fails and MySQL keeps the previous one.
echo "Reloading the MySQL TLS certificate..."
mysql_root "ALTER INSTANCE RELOAD TLS"
echo "MySQL serves a certificate valid until: $(mysql_root "SELECT value FROM performance_schema.tls_channel_status WHERE channel = 'mysql_main' AND property = 'Ssl_server_not_after'")"
