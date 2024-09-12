#!/bin/bash
clear
echo "SpExServer Deployment Build Script"
# take and currently running containers offline and delete any volumes from the last build
docker compose down --volumes
# delete the output and upload directory contents
rm -rf ./backend/output/*
rm -rf ./backend/uploads/*
# build the API, NGINX server first
docker compose build backend || exit
# try to build new images before taking down the old ones
./shell/frontend-build.sh
# take down the old containers
docker compose down --volumes
# stop here to look for error messages
echo -e "\nDevelopment Build completed,"
echo -r -p "press any key to PUSH the new images to the container repository and continue..."
./shell/ghcr-login.sh
docker compose push || exit
# ssh into the backend and restart the API
ssh ubuntu@spexodisks.com -i spexod-us-est-1.pem "/home/ubuntu/SpExServer/shell/update.sh"
read -r -p  "completed: SpExServer Deployment Build Script, press any key prune docker cache..."
docker system prune --force --all --volumes