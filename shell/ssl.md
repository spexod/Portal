# Prerequisites

It is recommended to do this with only a bare IP4 address, 
but it is possible to use a domain name if that is already set up.

> [!WARNING]
> As of September 2024, GitHub is not supporting IP6 addresses 
> for clone and push operations. For this reason,
> we are using the IP4 address for the server.

## Software
- docker 
- git

## Open ports listening with TLS
- 22 (ssh)
- 80 (http)
- 443 (https)
- 3306 (for MySQL), restricted to the IP addresses of the computers that upload data,
  see [Restrict the MySQL port](#restrict-the-mysql-port)



# Make add an appropriate `.env` file

.env
```
# required setting for public server
COMPOSE_PROFILES=db,api,web
MYSQL_HOST="mysqlDB"
DATA_NEW_UPLOADS_ONLY=true
VOLUME_SPECIFICATION="ro"
DATA_MIGRATE_FROM_STAGED=true
NGINX_CONFIG_FILE="setup.conf"
DEBUG=false
API_USE_NEW_TABLES=false
MYSQL_CONFIG_FILE="deploy.cnf"
# Authentication
MYSQL_USER=<server-username>
MYSQL_PASSWORD=<some-super-secure-password>
MYSQL_CONFIG_FILE="deploy.cnf"
DJANGO_EMAIL_USER="unmonitoredspexodisks@gmail.com"
DJANGO_EMAIL_APP_PASSWORD="<another-password-not-the-same>"
DJANGO_SECRET_KEY="some-key-that-is-50-characters-long-and-contains-letters-and-numbers"
```
# Start the MySQL database

## Database initialization
It this is the first time initializing the database,
there are files can be added to the database at initiation
by copying them to the `Portal/mysql/init` directory.

More on this in the data export explanation available in the README.md file.

## TLS certificate for MySQL

MySQL uses the website's Let's Encrypt certificate, which does not exist yet on a new server.
Until it does (see [MySQL TLS](#mysql-tls-with-the-lets-encrypt-certificate) below),
start the database with `MYSQL_CONFIG_FILE="local.cnf"` in the `.env` file,
then switch to `deploy.cnf`.


## Bring up the MySQL database service
When ready, bring up the database with the following command:

> [!TIP]
> Use `./mysql/reset.sh` to clear the previous database and start fresh.

```
docker compose up mysqlDB --detach
```

## Populate the database

This is usually done from a remote connection 
(point to the IP address of the server in th .env file), 
but this script also works on the server itself 
if the .env file has `VOLUME_SPECIFICATION="rw"`, 
but only for a data initialization script.

```
./data.sh
```

### Remote only

> [!WARNING]
> For remote upload AWS key file (*spexo-ssh-key.pem*) is required.
> This keys is expected to be in the Portal directory.

> [!TIP]
> You make need to change the host from spexodisks.com to the IP address of the server.
```
./data_upload.sh
```

## Test and Upload new docker images

```
./display.sh
```

```
./deploy.sh
```

### Remote only

> [!WARNING]
> This script requires token file (*.git_token.txt*) to be in the Portal directory.
> This file is expected to contain a GitHub token with 
> read permissions to GitHub packages (which includes the container registry).
> This token needs only minimal permissions needed read docker images
> and must be set to expire in periodically. 

```
deploy_upload.sh
```

# SSL configuration for the website (https)

THis is meant to set up a http so that we are able to get a certificate from certbot
(proof of ownership for the domain).

> [!TIP]
> Use `docker container ls` to see if the required containers are running.
> Use should be able to see this with the unsecure *http* site http://spexodisks.com
> (or the IP address of the server instead of the spexodisks.com).

## Start an HTTP server to get the SSL certificate
Navigate to the root of the project (Portal/) and start the http server

```
docker compose up --detach
```

## run the certbot docker container

```
docker compose up certbot
```

## we now no longer need the http server, so we can get rid of it

```
docker compose down
```

## set the environment variable to use the deployment version of NGINX server with SSL certificates


```
NGINX_CONFIG_FILE="deploy.conf"
```

It was previously set to `setup.conf` in the `.env` file.


## with an SSL certificate we can now use the deployment version of the website.

```
docker compose up --detach
```

## MySQL TLS with the Let's Encrypt certificate

MySQL (`mysql/deploy.cnf`) uses the same Let's Encrypt certificate as the website.
MySQL runs as uid 999 and cannot read certbot's root-only private key, so it reads a copy in
`/etc/letsencrypt/mysql-ssl/` (inside the `ssl_keys` volume).
Certbot makes a new copy after every renewal with the deploy hook `shell/certbot-mysql-hook.sh`.

Make the first copy:

```
docker compose run --rm --entrypoint /bin/sh certbot /etc/letsencrypt/renewal-hooks/deploy/mysql-ssl.sh
```

Then (re)start the database with `MYSQL_CONFIG_FILE="deploy.cnf"` in the `.env` file
and check the certificate that MySQL serves, which should show the Let's Encrypt expiration date:

```
docker compose up mysqlDB --detach
docker compose exec mysqlDB sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "SHOW GLOBAL STATUS LIKE \"Ssl_server_not_after\""'
```

Database clients request TLS (see `MYSQL_SSL_MODE` in `backend/science/db/sql.py`):
remote clients connect to `spexodisks.com` and check the certificate and host name,
and the backend on the server connects to `mysqlDB` encrypted without the host name check
(`mysqlDB` is not on the certificate, and the traffic stays inside the server).

When every client uses TLS, set `require_secure_transport=ON` in `mysql/deploy.cnf`
so that MySQL rejects unencrypted connections. To list the current connections and their TLS version
(an empty version means unencrypted):

```
docker compose exec mysqlDB sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "SELECT t.processlist_user, t.processlist_host, s.variable_value AS tls FROM performance_schema.threads t LEFT JOIN performance_schema.status_by_thread s ON s.thread_id = t.thread_id AND s.variable_name = \"Ssl_version\" WHERE t.processlist_user IS NOT NULL"'
```

## Restrict the MySQL port

Docker publishes port 3306 directly, bypassing host firewalls such as `ufw`,
so restrict it in the cloud provider's firewall (for AWS Lightsail: the instance's
**Networking** tab, in both the IPv4 and IPv6 firewalls).
Limit the MySQL/3306 rule to the IP addresses of the computers that upload data,
and update the rule when those addresses change.
The website itself is not affected: the backend reaches MySQL inside the Docker network.

### When the upload computer's IP address changes

Home internet providers change addresses from time to time.
The sign is that `./data.sh` or `./deploy.sh` cannot reach the database
(`Can't connect to MySQL server on 'spexodisks.com:3306'`, usually after a timeout)
while the website keeps working.

1. Find the computer's current public IPv4 address. Run this on the upload computer, not the server:

   ```
   curl -4 https://checkip.amazonaws.com
   ```

   With a VPN connected, this is the VPN's address, and the uploads use it too.
   Either allow that address or disconnect the VPN.

2. Update the firewall rule in the [Lightsail console](https://lightsail.aws.amazon.com):
   choose the instance, open the **Networking** tab, and in the **IPv4 Firewall** section
   choose **Edit** (the pencil icon) on the MySQL/Aurora rule (TCP 3306).
   Keep **Restrict to IP address** selected, replace the old address with the new one,
   and save. The change takes effect within a few moments.
   The **IPv6 Firewall** section should not have an open 3306 rule.

3. Check that the port is reachable from the upload computer, then rerun the upload:

   ```
   nc -vz spexodisks.com 3306
   ```

   `succeeded` (or `open`) means the rule works; a timeout means the address in the rule does not
   match the one from step 1.

If the SSH rule (port 22) is also restricted to an IP address, the same steps apply to it.
Keep **Allow Lightsail browser SSH** selected on that rule, so the browser-based SSH client in the
Lightsail console still works when the address is out of date.

## Certificate renewal with systemd

Four systemd units in `shell/systemd/` keep the certificate current:

- `spexodisks-certbot.timer` starts `spexodisks-certbot.service` twice a day.
  It runs `certbot renew`, which renews the certificate only when it is close to expiring.
  After a renewal, certbot's deploy hook (`shell/certbot-mysql-hook.sh`) copies it for MySQL.
- `spexodisks-certs-changed.path` watches the symbolic links in `live/spexodisks.com/`
  inside the `ssl_keys` volume. When certbot replaces them, it starts
  `spexodisks-certs-changed.service`, which runs `shell/reload-certs.sh`:
  it copies the certificate for MySQL again and reloads it in nginx and MySQL
  without restarting either.

### Install the units

The path unit watches the `ssl_keys` volume's directory on the server.
Check that `spexodisks-certs-changed.path` starts with the volume's mount point:

```
docker volume inspect portal_ssl_keys --format '{{ .Mountpoint }}'
```

Copy the units to systemd and start them.
Repeat these commands after changing a file in `shell/systemd/`.

```
sudo install -m 644 shell/systemd/spexodisks-* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now spexodisks-certbot.timer spexodisks-certs-changed.path
```

On a server that used the older cron setup, remove the certificate lines
(`certbot renew`, `renew-certs.sh`, or `restart nginx`) with `sudo crontab -e`.

### Check the renewal

```
systemctl list-timers spexodisks-certbot.timer
systemctl status spexodisks-certs-changed.path
journalctl -u spexodisks-certbot -u spexodisks-certs-changed --since "-7 days"
```

To test the whole renewal path against Let's Encrypt's staging servers,
without changing the certificate:

```
docker compose run --rm certbot renew --dry-run
```

To load the current certificate into nginx and MySQL by hand (it waits 30 seconds first):

```
sudo systemctl start spexodisks-certs-changed.service
```
