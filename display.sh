#!/bin/bash
clear
read -r -p "SpExServer TEST Build Script, press any key to continue..."
# take and currently running containers offline and delete any volumes from the last build
docker compose down --volumes
# build the API, NGINX server first
docker compose build backend
# bring up the the backend and nginx server
docker compose up --detach backend nginx
echo "Build a local API (backend) and NGINX-server if completed, press any key to build the frontend..."
# build the frontend on the local machine (we need the cache from this for the docker-build later)
cd SpExo-FrontEnd || exit
# remove the .next folder to ensure a clean build
rm -rf .next || return
# copy production environment variables
rm .env.production || return
cp .env.display .env.production || exit
cd ../ || exit
# build in the docker container
echo -r -p "Local Build for frontend completed (needed for fetch-cache), press any key to launch the test-website and continue..."
docker compose build frontend || exit
# test the build on a local machine
# stop here to look for error messages
echo " "
read -r -p "Frontend Build completed, press any key to launch the test-website and continue..."
# launch the test website
docker compose up
# use control-c to stop the test website, then docker down is called
docker compose down
echo " "
read -r -p "completed: SpExServer TEST Build Script, press any key to continue..."
