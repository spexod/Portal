#!/bin/bash
clear
echo "SpExServer Update Script"
cd /opt/bitnami/projects/ || exit
user='chw3k5'
# # permission must be set for the token to pull from the repo, this toke is only for the container registry
# auth_token=$(cat .git_token.txt)
# sudo git pull "https://${user}:${auth_token}@github.com/spexod/SpExServer"
# git checkout main
# git pull origin main
# log in to THe GitHub Container Registry
cat .git_token.txt | docker login ghcr.io --username "${user}" --password-stdin
# pull the fresh version from the container registry
docker compose pull
# take the currently running continues offline
docker compose down --volumes
# start the new containers from the pull images
docker compose up --detach
# clear the old images and cache to keep the disk usage down on the server computer
echo -e "\nCompleted: SpExServer Server Update Script,\ncheck the website at spexodisks.com.\nAfter confirming the site"
read -r -p  "press any-key prune docker cache (deleting any old docker image components)..."
docker system prune --force --all --volumes
echo "completed: SpExServer Update Script"
read -r -p "press any-key to exit."
