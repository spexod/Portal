#!/bin/bash
clear
echo "SpExServer Deployment Build Script"
# test the build on a local machine
./write_deploy_configs.sh
# try to build new images before taking down the old ones
docker compose -f compose-deploy.yaml build
# stop here to look for error messages
echo " "
read -r -p "Test Build completed, press any key to launch the test-website and continue..."
docker login ghcr.io
docker compose -f compose-deploy.yaml push
read -r -p  "completed: SpExServer Deployment Build Script, press any key to continue..."