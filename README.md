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

The Git token you use here will need super-powers (ie. have every authorization enabled, when you request it on Git); see here if you need a new token: https://github.com/settings/tokens/new

If you need to update your previously stored token to a new one see here: https://gist.github.com/jonjack/bf295d4170edeb00e96fb158f9b1ba3c#updating-an-existing-access-token

### Updating the Server (update-deploy.sh)

Updating the server requirements requires access to the server.

The Server require code accept the `update-deploy.sh` script, so the 
server only has one repository 'SpExServer'.

Following the prompts in the script, once the images are pulled and the
containers are launched (wait 10 seconds for the initialization), 
navigate to the live website in your browser using <https://spexodisks.com>.
Congratulations, you just deployed the SpExoDisks website. 

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

`docker comopse` always looks for a compose.yaml file for
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
