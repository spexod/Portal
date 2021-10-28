#!/bin/bash
clear
echo "SpExServer Initialization Script"

cd /opt/bitnami/ || return
PROJECT=projects
cd $PROJECT/ || return && docker-compose down && cd ../
rm $PROJECT -rf
mkdir $PROJECT && chmod 755 $PROJECT && cd $PROJECT/ || exit
cp /home/bitnami/sql_config.py .
git clone https://github.com/chw3k5/SpExServer .
git checkout main
chmod 744 init_repos.sh init.sh update_repos.sh update.sh
cp update.sh ~/.
./init_repos.sh
docker-compose build
docker-compose up -d
echo "completed: SpExServer Initialization Script"