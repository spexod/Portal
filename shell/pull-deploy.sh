#!/bin/bash
# login to the GitHub Container Repository
./ghcr-login.sh
# try to build new images before taking down the old ones
docker compose pull
