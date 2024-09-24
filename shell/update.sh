#!/bin/bash
clear
echo "SpExServer Update Script"
cd /home/ubuntu/Portal/ || exit
user='chw3k5'
# This is public repo, so we can pull without authentication, to update the compose file
git pull origin main
# log in to THe GitHub Container Registry
cat .git_token.txt | docker login ghcr.io --username "${user}" --password-stdin
# pull the fresh version from the container registry
docker compose pull
# take the currently running continues offline
docker compose down
# delete the (to remake) the Django static files and other temp files
./shell/rm_volumes.sh
# start the new containers from the pull images
docker compose up --detach
# clear the old images and cache to keep the disk usage down on the server computer
echo -e "\nCompleted: Portal Update Script, check the website at spexodisks.com. After confirming the site, press any-key prune"
read -r -p  "ocker cache (deleting any old docker image components)..."
docker system prune --force --all --volumes
echo "completed: Portal Update Script"
read -r -p "press any-key to exit."
