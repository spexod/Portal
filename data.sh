#!/bin/bash
clear
read -r -p "SpExServer Data Processing Script, press any key to continue..."
# delete the old fits and text files
rm -rf ./backend/output/*
# take and currently running containers offline and delete any volumes from the last build (not the db)
docker compose --profile web --profile api down --volumes
# build and start the backend, wait for it to finish processing
docker compose run --build --rm backend python update.py
# bring down the backend
docker compose --profile web --profile api down --volumes
