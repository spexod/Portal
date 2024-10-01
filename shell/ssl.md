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
- 3306 (for MySQL)



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

## Initialize SSL certificates

Using the docker container, we can initialize the SSL certificates

```
docker compose up cert-gen
```

Keep only the three requires files in the `Portal/mysql/cert` directory:

```
ca.crt
mysql.crt
mysql.key
```


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

## Renewal With CronTab

### install cron, probably already installed on Ubuntu
```
sudo apt-get install cron
```

### Enable the cron app to run in the background

```
sudo systemctl enable cron
```

### Open the crontab to setup a new cron job

```
sudo crontab -e
```


### We add a line cron tab file to check if the certificate needs to be renewed, it checks once a day at 3:00PM.

```
0 15 * * * docker compose --file /home/ubuntu/Portal/compose.yaml run certbot renew --quiet
```