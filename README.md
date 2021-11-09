# SpExoDisks_Containerized
This is  an assembly repository that links the work of the SpExoDisks
development teams. This repository contains the linking and manage files
(docker-compose.yml,  nginx-setup.conf, nginx.conf) to set up a 
containerized sever on any computer with Docker and Docker-Compose.
## Running on a Sever or Your Local Machine
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
    (Issac or Caleb in 2021).
- Docker installation https://docs.docker.com/engine/install/
- Unix step: docker-compose installation (docker-compose comes with
Windows and Mac Installation) https://docs.docker.com/compose/install/.
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

```angular2html
# clone this repository
git clone https://github.com/chw3k5/SpExServer
# copy the sql_config.py to the SpExServer directory
cp sql_config.py SpExSever/.
# change directory to SpExServer
cd SpExServer
# modify all the shell scripts to be allowed to be executed
chmod 744 *.sh
# call the initialization script, that takes care of the rest.
sudo ./init.sh
```

Depending on how you use your computer or if you are on a unix server,
you may have to enter your Github.com `username` and paste your 
`personal access token`.


