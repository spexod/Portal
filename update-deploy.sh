#!/bin/bash
clear
echo "SpExServer Update Script"
cd /opt/bitnami/projects/ || return
git checkout main
git pull origin main
# try to build new images before taking down the old ones
docker login ghcr.io
docker compose -f compose-deploy.yaml pull
docker compose -f compose-deploy.yaml down
docker compose -f compose-deploy.yaml up -d
docker system prune --force --all
echo "completed: SpExServer Update Script"