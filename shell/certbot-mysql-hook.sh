#!/bin/sh
# Certbot deploy hook: copy the website's Let's Encrypt certificate to where MySQL can read it.
#
# certbot runs this inside its container after every successful renewal: compose.yaml mounts it at
# /etc/letsencrypt/renewal-hooks/deploy/mysql-ssl.sh. MySQL runs as uid 999 and cannot read
# certbot's root-only private key, so MySQL gets its own copy in /etc/letsencrypt/mysql-ssl/.
# To make the first copy by hand (see shell/ssl.md):
#   docker compose run --rm --entrypoint /bin/sh certbot /etc/letsencrypt/renewal-hooks/deploy/mysql-ssl.sh
set -eu

lineage="${RENEWED_LINEAGE:-/etc/letsencrypt/live/spexodisks.com}"
dest=/etc/letsencrypt/mysql-ssl

mkdir -p "$dest"
chmod 755 "$dest"
# copy the files the symlinks in live/ point to, then swap them into place
cp -L "$lineage/fullchain.pem" "$dest/fullchain.pem.new"
cp -L "$lineage/privkey.pem" "$dest/privkey.pem.new"
chown 999:999 "$dest/fullchain.pem.new" "$dest/privkey.pem.new"
chmod 644 "$dest/fullchain.pem.new"
chmod 600 "$dest/privkey.pem.new"
mv "$dest/fullchain.pem.new" "$dest/fullchain.pem"
mv "$dest/privkey.pem.new" "$dest/privkey.pem"
echo "mysql-ssl: copied the certificate from ${lineage} for MySQL"
