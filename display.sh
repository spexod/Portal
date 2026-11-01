#!/bin/bash
clear
read -r -p "Portal TEST Build Script, press any key to continue..."
# take and currently running containers offline and delete any volumes from the last build
docker compose --profile web --profile api down
# delete the (to remake) the Django static files
./shell/rm_volumes.sh
# build the backend image
./shell/build.sh backend || exit
# the frontend image: the pages are rendered on request, so the build needs no API
cd SpExo-FrontEnd || exit
# remove the .next folder to ensure a clean build
rm -rf .next || exit
# copy production environment variables
rm -f .env.production || exit
cp .env.display .env.production || exit
cd ../ || exit
# the newest package versions within the ranges, and the exact base images, for this build
python3 shell/refresh_versions.py || exit
# build in the docker container
./shell/build.sh frontend || exit
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
