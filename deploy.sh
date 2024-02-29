#!/bin/bash
clear
echo "SpExServer Deployment Build Script"
# test the build on a local machine
./shell/write-deploy-configs.sh
# take and currently running containers offline and delete any volumes from the last build
docker compose down --volumes
# build the API, NGINX server first
docker compose build backend
# try to build new images before taking down the old ones
./shell/frontend-buildcache.sh
# stop here to look for error messages
echo -e "\nDevelopment Build completed,"
read -r -p "press any key to PUSH the new images to the container repository and continue..."
./shell/ghcr-login.sh
docker compose push
# ssh into the backend and restart the API
ssh bitnami@spexodisks.com -i spexod-us-est-1.pem "/opt/bitnami/projects/shell/update.sh"
read -r -p  "completed: SpExServer Deployment Build Script, press any key prune docker cache..."
docker system prune --force --all