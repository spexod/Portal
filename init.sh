#!/bin/bash
clear
echo "SpExServer Initialization Script"
# on the Server
[ -d "/opt/bitnami" ] && echo "  Server Initialization" && PROJECT=projects && cd /opt/bitnami
# on a local machine
[ ! -d "/opt/bitnami" ] && echo "  Local Machine Initialization" && PROJECT=SpExServer
# If the Project dir exists, stop any running container to free up resources
[ -d $PROJECT/ ] && cd $PROJECT/ && echo "  Stopping Running Containers in $(pwd)" && docker-compose down
[ -d ../$PROJECT/ ] && cd ../
# delete the old directory
echo "  Deleting the old directory $PROJECT in $(pwd)"
exit


# delete the old directory
echo "  Deleting the old directory $(PROJECT) in $(pwd)" && rm $PROJECT -rf
# make a new directory with the correct permissions
mkdir $PROJECT && chmod 755 $PROJECT && cd $PROJECT/ || exit
# clone SpExoServer repo
git clone https://github.com/chw3k5/SpExServer .
# checkout the main branch
git checkout main
# on the server only, get the sql_config file
[ -d "/home/bitnami/sql_config.py" ] && cp /home/bitnami/sql_config.py .
# on a local machine only, get the sql_config file
[ ! -d "/home/bitnami/sql_config.py" ] && cp ../sql_config.py .
# modify the scripts to be executable
chmod 744 *.sh
# on the Server, ad the update script to the home directory
[ -d "/home/bitnami" ] && cp update.sh /home/bitnami/.
# run the repository initialisation (download) script
./init_repos.sh
# build the docker images
docker-compose build
# deploy the images as docker containers on this system
docker-compose up -d
echo "completed: SpExServer Initialization Script"