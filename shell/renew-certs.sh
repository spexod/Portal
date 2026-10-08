#!/bin/bash
# Renew the Let's Encrypt certificate if it is due, then reload it in nginx and MySQL.
# Run daily from root's crontab on the server (see shell/ssl.md):
#   0 15 * * * /home/ubuntu/Portal/shell/renew-certs.sh >> /var/log/spexodisks-certs.log 2>&1
cd "$(dirname "$0")/.." || exit 1
echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') certificate renewal check"

# Renews only when the certificate is close to expiring. After a renewal, certbot's deploy hook
# (shell/certbot-mysql-hook.sh) copies the new certificate for MySQL.
docker compose run --rm certbot renew --quiet

# Load the current certificate without dropping connections. Harmless when nothing was renewed.
docker compose exec -T nginx nginx -s reload
docker compose exec -T mysqlDB sh -c \
    'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "ALTER INSTANCE RELOAD TLS" 2>&1 | grep -v "Using a password" || true'
