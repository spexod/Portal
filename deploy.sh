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
# bring up the the backend and nginx server
docker compose up --detach backend nginx
echo "Build a local API (backend) and NGINX-server if completed, press any key to build the frontend..."
# build the frontend on the local machine (we need the cache from this for the docker-build later)
cd SpExo-FrontEnd || exit
# remove the .next folder to ensure a clean build
rm -rf .next || return
# copy production environment variables
rm .env.production || return
cp .env.deploy .env.production || exit
cd ../ || exit
# build in the docker container
echo -r -p "Local Build for frontend completed (needed for fetch-cache), press any key to launch the test-website and continue..."
docker compose build frontend --no-cache || exit
# take down the old containers
docker compose down --volumes
# stop here to look for error messages
echo -e "\nDevelopment Build completed,"
echo -r -p "Pushing the new images to the container repository"
./shell/ghcr-login.sh
docker compose push || exit
# ssh into the server and pull the new images
ssh ubuntu@spexodisks.com -i spexod-us-est-1.pem "/home/ubuntu/SpExServer/shell/update.sh"
read -r -p  "completed: SpExServer Deployment Build Script, press any key prune docker cache..."
docker system prune --force --all --volumes