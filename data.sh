#!/bin/bash
clear
read -r -p "SpExServer Data Upload Script, press any key to continue..."
# write test configs
./shell/write-test-configs.sh
# delete the old fits and text files
rm -rf ./backend/output/*
# take and currently running containers offline and delete any volumes from the last build
docker compose down --volumes
# build and start the backend, wait for it to finish processing
docker compose run --build --rm backend python update.py
# bring down the backend
docker compose down --volumes
# upload the fits and text files
rsync -avz -e "ssh -i spexod-us-est-1.pem" ./backend/output ubuntu@spexodisks.com:/home/ubuntu/SpExServer/backend/output
# upload data files
rsync -avz -e "ssh -i spexod-us-est-1.pem" ./backend/data ubuntu@spexodisks.com:/home/ubuntu/SpExServer/backend/data