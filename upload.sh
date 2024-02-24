#!/bin/bash
clear
read -r -p "SpExServer Data Upload Script, press any key to continue..."
# take and currently running containers offline and delete any volumes from the last build
docker compose down --volumes
# build and start the backend, wait for it to finish processing
docker compose run --build backend python science/db/process.py