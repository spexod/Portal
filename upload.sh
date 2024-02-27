#!/bin/bash
clear
read -r -p "SpExServer Data Upload Script, press any key to continue..."
# write test configs
./shell/write-test-configs.sh
# take and currently running containers offline and delete any volumes from the last build
docker compose down --volumes
# build and start the backend, wait for it to finish processing
docker compose run --build backend python update.py
# ssh into the backend and restart the API
ssh bitnami@spexodisks.com -i spexod-us-est-1.pem "docker compose -f /opt/bitnami/projects/compose.yaml restart backend"
# bring down the backend
docker compose down --volumes