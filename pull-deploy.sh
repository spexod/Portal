#!/bin/bash
# login to the GitHub Container Repository
./ghcr-login.sh
# try to build new images before taking down the old ones
docker compose -f compose-server.yaml pull
# docker compose -f compose-server.yaml down
# docker compose -f compose-server.yaml up -d
# # clear the old images and cache to keep the disk usage down on the server computer
# docker system prune --force --all
