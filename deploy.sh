#!/bin/bash
clear
read -r -p "Portal Data Upload Script, press any key to continue..."
# upload the output FITs and TXT files
rsync -avz -e "ssh -i spexo-ssh-key.pem" ./backend/output ubuntu@spexodisks.com:/home/ubuntu/Portal/backend
# upload input data files
rsync -avz -e "ssh -i spexo-ssh-key.pem" ./backend/data ubuntu@spexodisks.com:/home/ubuntu/Portal/backend
echo "Portal Deployment Build Script"
# take and currently running containers offline and delete any volumes from the last build
docker compose --profile web --profile api down
# delete the (to remake) the Django static files
./shell/rm_volumes.sh
# delete the output and upload directory contents
rm -rf ./backend/output/*
rm -rf ./backend/uploads/*
# build the API, NGINX server first
docker compose build backend || exit
# bring up the the backend and nginx server
docker compose --profile api up --detach || exit
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
docker compose down
# stop here to look for error messages
echo -e "\nDevelopment Build completed,"
echo -r -p "Pushing the new images to the container repository"
./shell/ghcr-login.sh
docker compose push || exit
# once everything else is competed, we mark the database as ready to be updated
docker compose run --build --rm backend python science/db/commit_data.py || exit
echo " completed the push to the container repository, continue the update with ./deploy_update.sh"