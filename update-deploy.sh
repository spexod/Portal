#!/bin/bash
clear
echo "SpExServer Update Script"
cd /opt/bitnami/projects/ || return
docker-compose -f docker-compose-deploy.yml down
git checkout main
git pull origin main
./update_repos.sh
docker-compose -f docker-compose-deploy.yml build
docker-compose -f docker-compose-deploy.yml down
docker-compose -f docker-compose-deploy.yml up -d
echo "completed: SpExServer Update Script"