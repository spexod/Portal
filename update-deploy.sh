#!/bin/bash
clear
echo "SpExServer Update Script"
cd /opt/bitnami/projects/ || return
git checkout main
git pull origin main
# run the update script (pull-deploy.sh) from the pulled version of SpExServer repo
./pull-deploy.sh
# take the currently running continues offline
docker compose -f compose-server.yaml down
# start the new containers from the pull images
docker compose -f compose-server.yaml up -d
# clear the old images and cache to keep the disk usage down on the server computer
docker system prune --force --all
echo "completed: SpExServer Update Script"
read -r -p "press any key to exit."
