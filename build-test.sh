#!/bin/bash
clear
read -r -p "SpExServer TEST Build Script, press any key to continue..."
./shell/write-test-configs.sh
# take and currently running containers offline and delete any volumes from the last build
docker compose down --volumes
# build the API, NGINX server first
docker compose build --no-cache backend
./shell/frontend-buildcache.sh
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
