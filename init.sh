#!/bin/bash
clear
echo "SpExServer Initialization Script"
cd /opt/bitnami/ || return
PROJECT=projects
rm $PROJECT -rf
mkdir $PROJECT && chmod 755 $PROJECT && cd $PROJECT/ || exit
git clone https://github.com/chw3k5/SpExServer .
git checkout main
./init_repos.sh
docker-compose down
docker-compose build
docker-compose up -d
echo "completed: SpExServer Update Script"