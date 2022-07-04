#!/bin/bash
clear
echo "SpExServer Update Script"
cd /opt/bitnami/projects/ || return
git checkout main
git pull origin main
./update_repos.sh
# try to build new images before taking down the old ones
docker-compose -f docker-compose-deploy.yml build
docker-compose -f docker-compose-deploy.yml down
docker-compose -f docker-compose-deploy.yml up -d
echo "completed: SpExServer Update Script"