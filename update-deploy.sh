#!/bin/bash
clear
echo "SpExServer Update Script"
cd /opt/bitnami/projects/ || return
git checkout main
git pull origin main
# run the update script (pull-deploy.sh) from the freshly pulled version of SpExServer repo
./shell/pull-deploy.sh
# take the currently running continues offline
docker compose down --volumes
# start the new containers from the pull images
docker compose up -d
# clear the old images and cache to keep the disk usage down on the server computer
echo -e "\nCompleted: SpExServer Server Update Script,\ncheck the website at spexodisks.com.\nAfter confirming the site"
read -r -p  "press any-key prune docker cache (deleting any old docker image components)..."
docker system prune --force --all --volumes
echo "completed: SpExServer Update Script"
read -r -p "press any-key to exit."
