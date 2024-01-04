#!/bin/bash
# take and currently running containers offline and delete any volumes from the last build
docker compose down --volumes
# build the API, NGINX server first
docker compose up --build --detach backend nginx
read -r -p "Build a local API (backend) and NGINX-server if completed, press any key to build the frontend..."
# build the frontend on the local machine (we need the cache from this for the docker-build later)
cd SpExo-FrontEnd || exit
npm install
npm run build
cd ../ || exit
read -r -p "Local Build for frontend completed (needed for fetch-cache), press any key to launch the test-website and continue..."
# build in the docker container
docker compose build frontend
