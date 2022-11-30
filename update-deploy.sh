#!/bin/bash
clear
echo "SpExServer Update Script"
cd /opt/bitnami/projects/ || return
git checkout main
git pull origin main
./update_repos.sh
# use the server configs for the deployment repository builds
./write_deploy_configs.sh
# try to build new images before taking down the old ones
docker compose -f compose-deploy.yaml build
docker compose -f compose-deploy.yaml down
docker compose -f compose-deploy.yaml up -d
echo "completed: SpExServer Update Script"