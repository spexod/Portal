#!/bin/bash
clear
read -r -p "Portal TEST Build Script, press any key to continue..."
# take and currently running containers offline and delete any volumes from the last build
docker compose --profile web --profile api down
# delete the (to remake) the Django static files
./shell/rm_volumes.sh
# bring up the the backend and nginx server
docker compose --profile api up --build --detach || exit
echo "Build a local API (backend) and NGINX-server completed, building the frontend..."
# build the frontend on the local machine (we need the cache from this for the docker-build later)
cd SpExo-FrontEnd || exit
# remove the .next folder to ensure a clean build
rm -rf .next || return
# copy production environment variables
rm .env.production || return
cp .env.display .env.production || exit
# update the packages in package-lock.json (this requires node https://nodejs.org/en/download/package-manager)
npm update || exit
cd ../ || exit
# build in the docker container
echo -r -p "Local Build for frontend completed (needed for fetch-cache), launching the test-website..."
docker compose build frontend || exit
# test the build on a local machine
# stop here to look for error messages
echo " "
read -r -p "Frontend Build completed, press any key to launch the test-website and continue..."
# launch the test website
docker compose up
# use control-c to stop the test website, then docker down is called
docker compose --profile web --profile api down || exit
echo " "
echo "completed: Portal TEST Build Script"
