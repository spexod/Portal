#!/bin/bash
clear
read -r -p "SpExServer Data Upload Script, press any key to continue..."
./shell/write-test-configs.sh
# take and currently running containers offline and delete any volumes from the last build
docker compose down --volumes
# start the database
docker compose up --build mysqlDB backend --detach
# build and start the backend, wait for it to finish processing
# docker compose exec backend bash "python science/db/process.py"