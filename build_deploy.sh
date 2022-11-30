#!/bin/bash
clear
echo "SpExServer Deployment Build Script"
# test the build on a local machine
./write_deploy_configs.sh
# try to build new images before taking down the old ones
docker compose -f compose-deploy.yaml build
docker compose -f compose-deploy.yaml down
docker compose -f compose-deploy.yaml up -d
echo "completed: SpExServer Deployment Build Script"