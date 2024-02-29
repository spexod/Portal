#!/bin/bash
# bring up the the backend and nginx server
docker compose up --detach backend nginx
read -r -p "Build a local API (backend) and NGINX-server if completed, press any key to build the frontend..."
# build the frontend on the local machine (we need the cache from this for the docker-build later)
cd SpExo-FrontEnd || exit
rm -rf .next
npm install
npm run build
cd ../ || exit
read -r -p "Local Build for frontend completed (needed for fetch-cache), press any key to launch the test-website and continue..."
# build in the docker container
docker compose build frontend
