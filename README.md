# SpExServer
This is an assembly repository that links the work of the SpExoDisks
development teams. This repository contains the linking and manage files
(docker-compose.yml,  nginx-setup.conf, nginx.conf) to set up a 
containerized sever on any computer with Docker and Docker-Compose.
## Running on a Sever/Local Machine Setup
### Initial Setup
This repo (SpExServer) is super lightweight, it does not contain the
code (and in the future, simply the docker images) needed to build the
website. However, this repository does contain scripts to download
the current recommended configuration.

*Here is what you need before you start:*
- A unix terminal (Git-Bash on Windows works)
- sudo privileges
- Git installation
- a Github.com account
  - Obtain a personal access token: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
    Save this in a save place to cut and paste from later.
  - Send your Github.com username to the SpExoDisks Technical Administrators
    (Isaac or Caleb in 2021).
- Docker installation https://docs.docker.com/engine/install/
- Unix step: docker-compose installation (docker-compose comes with
Windows and Mac Installation) https://docs.docker.com/compose/install/.
- Test the docker is running with `docker version` You should see both a `client` and `Engine`.
- Get the connection credentials (sql_config.py) for the SpExoDisks MySQL server.
  - It is easy to generate these files, ask SpExoDisks Technical 
    Administrators (Issac or Caleb in 2021)
  - In the code below this file is expected to be in the parent directory
    of SpExoSever so that `cp sql_config.py SpExSever/.` is ready to
    be copied by the `init.sh` script.

*Cloning and Running SpExSever*
With your command line environment setup, and the correct privileges
to clone the various github repositories and/or docker images, the process
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

Depending on how you use your computer or if you are on a unix server,
you may have to enter your Github.com `username` and paste your 
`personal access token`.

`init.sh` takes a long time on the first time as it builds the docker images 
from freshly downloaded repositories. This get faster with subsequent builds
as the Docker makes use of cached files.

### Updating
With the initialization above (chmod 744 on update.sh update_repos.sh)
it is simple to update the repositories all to the main branch with:
```angular2html
cd SpExServer
sudo ./update.sh
```

However, this script (and all the scripts) are designed for fast updates
on a remote sever that have already been verified locally. If you are doing
the local verification, you will need a finer set of tools.

## Local Machine Testing
SpExServer is a conglomerate repository, that brings together other smaller
component repositories. On a local machine, we can individually control 
which branch and commit is checked out for the component repositories.
This *time-machine* allows us to test developments before deploying to the
server.

### Changing Component git branches and 
For example: the .git files SpExServer/.git, SpExServer/SpExo-FrontEnd/.git,
and SpExServer/SpExwebsite/.git can all be controlled independently simple by
using 'cd' to get into that directory. There are editors that can visually
demonstrate this selection process, we recommend https://www.jetbrains.com/edu-products/download/#section=idea
but this editor has many advance features that may be difficult to learn.

- git cheatsheet https://education.github.com/git-cheat-sheet-education.pdf
- the command to check out a branch https://git-scm.com/docs/git-checkout
  - `git checkout your_branch_name`

### Building with Docker-Compose
After updating the component repositories, you will want to test, 
and thus build, the website. For this we need only a few, `docker-compose`
commands (when everything is going right.) Note, docker-compose is a
python package the 'bolts-on-top-of' the Docker Engine, but is not the
Docker Engine itself. The scope of `docker-compose` is the assembly of
my docker images to make a deployment of docker containers, a website 
and an APT in our case.

`docker-comopse` always looks for a docker-compose.yml file for
instructions. So we 
```angular2html
cd SpExServer
```
to be in the same directory as 
SpExServer/docker-compose.yml

*End the Old Docker-Compose Deployment*
Gracefully shut down any existing containers and networks with:
```angular2html
docker-compose down
```

*Build the Docker Images from the Repositories*
Build the Images from the repositories and their Dockerfiles, locations
specified in SpExServer/docker-compose.yml.
```angular2html
docker-compose build
```

*Deploy the Docker images into running Containers*
With a successful container deployment, check `localhost` 
on a browser, and you should see the deployed website and API.docker-compose
```angular2html
docker-compose up
```

A variation of `docker-compose up` with `-d` (detach argument) to disconnect the terminal session from the docker-compose
deployment (remember to clean up with `docker-compose down` after).
```angular2html
docker-compose up -d
```

A variation of `docker-compose up` with `--build` (build argument) 
to automatically *build* the images and then bring *up* the containers.
```angular2html
docker-compose up --build
```

*Check the status of a detected Docker-Compose Build:
```angular2html
docker-compose ps
```
