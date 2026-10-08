#!/bin/bash
# Load the current Let's Encrypt certificate into nginx and MySQL, without restarting either.
#
# Run by the systemd unit spexodisks-certs-changed.service when certbot replaces the certificate
# (see "Certificate renewal with systemd" in shell/ssl.md). To run it by hand on the server:
#   sudo systemctl start spexodisks-certs-changed.service     (output: journalctl -u spexodisks-certs-changed)
set -euo pipefail
cd "$(dirname "$0")/.."

# Run SQL as root in the mysqlDB container, over the local socket. Passes MySQL's exit status
# through and drops only the warning about the password on the command line.
mysql_root() {
    docker compose exec -T mysqlDB sh -c \
        'out=$(mysql -uroot -p"$MYSQL_ROOT_PASSWORD" --batch --skip-column-names -e "$1" 2>&1); status=$?
         printf "%s\n" "$out" | grep -v "Using a password on the command line" || true
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
echo "MySQL serves a certificate valid until: $(mysql_root "SELECT variable_value FROM performance_schema.tls_channel_status WHERE channel = 'mysql_main' AND property = 'Ssl_server_not_after'")"
