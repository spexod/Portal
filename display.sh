#!/bin/bash
clear
read -r -p "Portal TEST Build Script, press any key to continue..."
# take and currently running containers offline and delete any volumes from the last build
docker compose --profile web --profile api down
# delete the (to remake) the Django static files
./shell/rm_volumes.sh
# the newest package versions within the ranges, and the exact base images, for both builds
python3 shell/refresh_versions.py || exit
# build the backend image
./shell/build.sh backend || exit
# the frontend image for the test website: the pages render on request, so the build needs no API, and
# the browser calls the API on the page's own origin (NEXT_PUBLIC_API_BASE_CLIENT defaults to "/")
rm -rf SpExo-FrontEnd/.next SpExo-FrontEnd/.env.production || exit
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
