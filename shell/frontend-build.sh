#!/bin/bash
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
