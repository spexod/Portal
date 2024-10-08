# Install the available repositories

## SpExServer (this public repository)

```
git clone https://github.com/spexod/SpExServer
```

and then enter the base repository with `cd SpExServer` for the following commands.


## Additional repositories 

These may require permissions as they are private repositories.
But these can be installed with:

```
./shell/init.sh
```

## required files for development
### .env

An `.env` file is required in the root directory of the SpExServer repository.
See the `.env.example` file for examples of the required fields.

SpExoDisks developers will need to get credentials to
connect to the MySQL server at spexodisks.com.

Local database development is also possible. The first time the 
initializes the MySQL database with the usernames and passwords in the `.env` file,
that are then used for all future connections. For example:

```
COMPOSE_PROFILES=db,api,frontend
MYSQL_USER="your-username-for-mysql"
MYSQL_PASSWORD="your-password-for-mysql"
## Host for inside the docker network
MYSQL_HOST="mysqlDB"
```

### spexod-us-est-1.pem

The private key for the AWS server. This is required to access the server.

# Pipeline for Public Website

For configuration, 
local docker containers connect to the MySQL server at spexodisks.com.
TThis MySQL Server is used public website and for this pipeline.

## .evn File Configuration

The `.env` will provided to you by the SpExoDisks administrators,
if contains a number authentication credentials and other fields
that need to be kept secret.

```
# Configuration
COMPOSE_PROFILES=api,web
MYSQL_HOST="spexodisks.com"
DATA_NEW_UPLOADS_ONLY=true
# Authentication
MYSQL_USER="?YourUsername"
MYSQL_PASSWORD="?AReallyLongPassword"
DJANGO_EMAIL_USER="?not.very.secret.email.address@gmail.com"
DJANGO_EMAIL_APP_PASSWORD="?super-sectet-passoword"
```

# Development using a Local MySQL Server

> [!TIP]
> `./mysql/reset.sh` is a hard reset for the local MySQL service.
> If the MySQL container is started, 
> it creates files that are viewable at `./mysql/local/`.
> Use (or see this script) if you want to start fresh 
> by deleting the persistent database files or resetting the username and password.

## .evn File Configuration

```
COMPOSE_PROFILES=db,api
MYSQL_USER="root"
MYSQL_PASSWORD="do-not-use-keyboard-walking-passwords"
```

## Recommended Scripts for Local Database Development

Create MySQL tables and FITs files for the SpExoDisks website with:

```
./data.sh
```

Build and display the frontend website locally with:

```
./display.sh
```


## Starting the MySQL Server

Local development can be done with a MySQL server running in a Docker container.

> [!WARNING]
> This MySQL server is required at build-time for "backend" Docker images.
> Local development users have two options to keep in mind. 
> Consider these options to start the MySQL server in the background
> before calling the primary shell scripts used build the Docker images
> (`./data.sh`, `./display.sh`, `deploy.sh`).
> 
### Option 1: Start the MySQL Server with Docker Compose

```
docker compose up mysqlDB --detach
```

This starts the MySQL server in the background. 
The server can be stopped with: `docker compose down`.

### Option 2: Start the MySQL Server with the backend Docker Image

This required uncommenting three lines in the compose.yaml 
in the "backend" service, using the `depends_on` directive.

```
    # Optionally uncomment the following lines when using the "db" profile.
    # Wait for the database to be ready before starting the backend.
#    depends_on:
#      mysqlDB:
#        condition: service_healthy
```

> [!WARNING]
> Do not commit uncommented line to the repository,
> as causes the mysqlDB container to start in all situations
> and not only when the "db" profile is used.
> The production database pipeline does not use the "db" profile.

# Environment Variables

The `.env` file is used to store environment variables for the Docker Compose.

## DATA_NEW_UPLOADS_ONLY

This variable is used to control the data upload process. 
When set to `true`, the data upload process will 
only upload new spectra and files to the MySQL server.

`true` is the default value for this variable, set in compose.yaml,
that is when the variable is not set in the `.env` file.

When set to `false`, the data upload process will re-upload all spectra and files.
This could be a useful to update all spectra after formatting changes,
such as to the changes to FITS files.

```



# SpExServer
This is an assembly repository that links the work of the SpExoDisks
development teams. This repository contains the linking and manage files
(docker-compose.yml,  nginx-setup.conf, nginx.conf) to set up a 
containerized sever on any computer with Docker and Docker-Compose.
## Running on a Sever/Local Machine Setup

### Warning
[Docker](https://docs.docker.com), which is required to run the SpExoDisks
website server, downloads a lot of files, and new versions of 
Python, NginX, Node base images as well as the changes made to 
the code base for the SpExoDisks website.
It is recommended to have a fast internet connection and a lot of
storage space. Periodically, you may find it helpful to run 

`docker system prune --all`

to remove all old images, containers, caches, etc. (everything that is 
not currently running). I find that I have enough hard disk space, 
but that my back-up storage drives get full much faster.

### Initial Setup
This repo (SpExServer) is super lightweight, it does not contain the
code (and in the future, simply the docker images) needed to build the
website. However, this repository does contain scripts to download
the current recommended configuration.

*Here is what you need before you start:*
- A unix terminal (Git-Bash on Windows works)
- sudo privileges
- Git installation
- a GitHub.com account
  - Obtain a personal access token: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
    Save this in a save place to cut and paste from later.
  - Send your GitHub username to the SpExoDisks Technical Administrators
    (Andrea, Isaac, or Caleb in 2023).
- Docker installation https://docs.docker.com/engine/install/
- Unix step: docker-compose installation (docker-compose comes with
Windows and Mac Installation) https://docs.docker.com/compose/install/.
- Test the docker is running with `docker version` You should see both a `client` and `Engine`.
- Get the connection credentials (sql_config.py) for the SpExoDisks MySQL server.
  - It is easy to generate these files, ask SpExoDisks Technical 
    Administrators (Isaac or Caleb in 2021)
  - In the code below this file is expected to be in the parent directory
    of SpExoSever so that `cp sql_config.py SpExSever/.` is ready to
    be copied by the `init.sh` script.

*Cloning and Running SpExSever*
With your command line environment setup, and the correct privileges
to clone the various GitHub repositories and/or docker images, the process
is meant to be streamed lined with a script, SpExServer/init.sh.

For Git-Bash, `sudo` is not needed in Git-Bash  and the neither is the `chmod 744`
```angular2html
# check to make sure `sql_config.py` is in the current directory
ls -l *sql_config.py*
# clone this repository
git clone https://github.com/chw3k5/SpExServer
# change directory to SpExServer
cd SpExServer
# call the initialization script, that takes care of the rest.
./init.sh
```

For Mac Linux,
```angular2html
# check to make sure `sql_config.py` is in the current directory
ls -l *sql_config.py*
# clone this repository
git clone https://github.com/chw3k5/SpExServer
# change directory to SpExServer
cd SpExServer
# give the scripts permission to be executed
chmod 744 *.sh
# call the initialization script, that takes care of the rest.
sudo ./init.sh
```

Depending on how you use your computer or if you are on an unix server,
you may have to enter your GitHub.com `username` and paste your 
`personal access token`.

## Scripts

All the scripts discussed in the section
stop several times and wait for the user to press
any-key to continue. The stops happen at critical steps to allow users to read
any error message before continuing to subsequent steps. Use _`control-c`_ in the 
terminal to stop a script at any time for any reason.

Running the scripts can be a little different each operating system. 
For each system type, see the examples below for running the `build-test.sh` script.

__Linux__

`sudo ./build-test.sh`

__Mac__

sudo is not allowed for docker commands, so we use:
`./build-test.sh`

__Windows (GitBash)__

`./build-test.sh`

__Windows (PowerShell)__

`.\build-test.sh`

this just opens GitBash.

### Updating (update.sh)

There are 4 git repositories to remember to update. You and do this manually
with the git commands, but there is a convenience script to do this if you
want to test only the `main` branches of the repositories, `update.sh`. 
This is the best practice configuration deploying the website.

This script does not contain any docker commands, but the server still
requires the use of `sudo` for permission to overwrite files. 

### Testing (build-test.sh)

This does not affect the live website, but it does use a shared resource
(the MySQL server) to test the data upload. Make sure to communicate with
your team members so that this is only being done by one person at time 
(Consider setting up a local SQL sever on your computer and setting the 
sql_config.py to point to that server if you find there are often conflicts).

To test the initialization or any updates, we can make a full version of the
test website using `build-test.sh` (make sure the docker damon is running!)
This script takes a long time on for two reasons:
1. It builds the docker images from freshly downloaded repositories with no cache,
   subsequent builds will use cached data.
2. There is a 45-minute upload step to put data in test schema on the MySQL server.

Following the prompts in the script, once the images are built and then launched
into containers, see the test website on your local machine by navigating your
browser to <http://localhost>.

Once you are done testing the website in the browser, use `control-c` to
stop the containers.

### Build Deployable containers (build-deploy)

The server requires a configuration that is not compatible with local testing.
Building docker images to be used and pulled by the server uses a special 
script, `build-deploy.sh`.

`build-deploy.sh` is meant to be run directly after a successful `build-test`.
When this happens the data upload step is skipped, and the data is
migrated to the main database schemas used by the live site. This leads to a
much shorting run time compared to `build-test.sh`.

If, for any reason, the data is marked as `new_data_staged=1` (meaning 
the data upload to MySQL severs was successful) in the `data_status.status`
table on the MySQL server, the `build-deploy.sh` will first preform this
long upload process before migrating the data the schemas used by the live
site.

When running this step, the prompt will ask (the first point on Macs only):

```angular2html 
Prepare to Enter:
  1) Your Mac's default password
  2) GitHub Username
  3) Github Auth Token
```

At the prompt request you will first enter your Mac pwd (if using a Mac); after that, the Git token will be automatically read from what's stored on your machine, if you entered it before.

The Git token you use here will need super-powers (ie. have every authorization enabled, when you request it on Git); see here if you need a new token: https://github.com/settings/tokens/new

If you need to update your previously stored token to a new one see here: https://gist.github.com/jonjack/bf295d4170edeb00e96fb158f9b1ba3c#updating-an-existing-access-token

### Updating the Server (update-deploy.sh)

Updating the server requirements requires access to the server. In 2022-2023, this step has to be performed on AWS that is hosting the website; after migration to the TXST servers, this will be done there.

Instructions for AWS:
1) go to Lightsail, and click on the server (named Sp2_4GB in 2023)
2) click on their "Connect using SSH"

These steps are same:
3) cd /home/ubuntu/SpExServer
4) sudo ./update-deploy.sh
5) will ask you Git username and token (will ask twice, but second time you can just hit enter)
6) this will start the process of uploading the newly made image to the server from Git repository, then bring live website down, and this one up; at the end will tell you "SpExServer Server Update Script"
7) go test the live site, to check that all went well
8) then prune to delete old image and free space (should be about 8 GB, in 2023)
9) logout

The Server require code accept the `update-deploy.sh` script, so the 
server only has one repository 'SpExServer'.

Following the prompts in the script, once the images are pulled and the
containers are launched (wait 10 seconds for the initialization), 
navigate to the live website in your browser using <https://spexodisks.com>.

Congratulations, you just deployed the SpExoDisks website! 

## Local Machine Testing
SpExServer is a conglomerate repository that brings together other smaller
component repositories. On a local machine, we can individually control 
which branch and commit are checked out for the component repositories.
This *time-machine* allows us to test developments before deploying to the
server.

### Changing Component git branches and 
For example, the .git files SpExServer/.git, SpExServer/SpExo-FrontEnd/.git,
and SpExServer/SpExwebsite/.git can all be controlled independently simple by
using 'cd' to get into that directory. There are editors that can visually
demonstrate this selection process, we recommend https://www.jetbrains.com/edu-products/download/#section=idea, 
but this editor has many advance features that may be difficult to learn.

- git cheatsheet https://education.github.com/git-cheat-sheet-education.pdf
- the command to check out a branch https://git-scm.com/docs/git-checkout
  - `git checkout your_branch_name`

### Building with Docker-Compose

Everyone should use the scrips to manage and update the repository. However,
software development will require us to update and test parts of the scripts.
In this sense, everyone would have some understanding of the basic docker 
commands used in our scripts.

`docker compose` always looks for a compose.yaml file for
instructions. So we 
```angular2html
cd SpExServer
```
to be in the same directory as 
SpExServer/docker-compose.yml

*End the Old Docker-Compose Deployment*
Gracefully shut down any existing containers and networks with:
```angular2html
docker compose down
```

*Build the Docker Images from the Repositories*
Build the Images from the repositories and their Dockerfiles, locations
specified in SpExServer/docker-compose.yml.
```angular2html
docker compose build
```

*Deploy the Docker images into running Containers*
With a successful container deployment, check `localhost` 
on a browser, and you should see the deployed website and API.docker-compose
```angular2html
docker compose up
```

A variation of `docker compose up` with `-d` (detach argument) to disconnect the terminal session from the docker-compose
deployment (remember to clean up with `docker-compose down` after).
```angular2html
docker compose up -d
```

A variation of `docker compose up` with `--build` (build argument) 
to automatically *build* the images and then bring *up* the containers.
```angular2html
docker compose up --build
```

*Check the status of a detected Docker-Compose Build:
```angular2html
docker compose ps
```

# Rare Database actions

## Exporting to an SQL Dump File for data initialization. 

Once we exported data from a production server to a new production server. This was done in two steps:

1. Export the data from the production server to an SQL dump file.
2. Load the data from the SQL into a new docker SQL image.

### Exporting the data from the production server to an SQL dump file.

For this we need to use the [MySQL Workbench](https://dev.mysql.com/downloads/workbench/), a GUI for MySQL. 

On the top menu plain select Server -> Data Export 

![The menu location for the MySQL data-export command](./static/ExportCommand.png "Export Command")

Remember to check the box for **Include Create Schema**. 
This will make sure that the schema are created when the data is imported into the new database.

![The control panel in MySQl Workbench that shows the Include-Create-Schema's box as checked. Otherwise this view shows the default options selected. ](./static/ExportDataView.png "Export Data View")

Save this file to **mysql/local/** directory in this repository.

> [!WARNING]
> This directory will use all the files in the directory to initialize the database.
> Make sure you only have the SQL dump files you want to use in this directory.


### Loading the data from the SQL into a new docker SQL image.

When you initialize this repository, the **mysql/local/** and **mysql/init/** directories are empty
expect for a single file ".gitignore" in each.

> [!WARNING]
> You must delete all files and directories in mysql/local/ **except** for the .gitignore file
> before you run any commands in this section. 
> You may also need to delete files to retry after failed commands.

The directory **mysql/init/** is where the SQL dump file will be placed. This file is only read
when the docker image is initialized for the first time, so this data is only loaded once.

To initialize a new MySQL docker image with the data from the SQL dump file, run the following

```angular2html
docker compose up mysqlDB
```

This will start the MySQL docker image and load the data from the SQL dump file. 
This process takes a few minutes extra to load the data.
Once it completes, the new database will be running as a server on your local machine. 
This is a good time to test logging into the database with [MySQL Workbench](https://dev.mysql.com/downloads/workbench/).