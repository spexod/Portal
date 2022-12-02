#!/bin/bash
# log in to the container repository on GitHub
unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     machine=Linux;;
    Darwin*)    machine=Mac;;
    CYGWIN*)    machine=Cygwin;;
    MINGW*)     machine=MinGw;;
    *)          machine="UNKNOWN:${unameOut}"
esac
if [ "$machine" = "Mac" ];
then
    read -r -p "BEFORE running this script - Use 'login ghcr.io' to enter you username and password for the container repository on GitHub. Press enter to continue. control-c to exit."
    # security unlock-keychain
    # docker login ghcr.io
else
  docker login ghcr.io
fi

# try to build new images before taking down the old ones
docker compose -f compose-server.yaml pull
# docker compose -f compose-server.yaml down
# docker compose -f compose-server.yaml up -d
# # clear the old images and cache to keep the disk usage down on the server computer
# docker system prune --force --all
