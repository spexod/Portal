#!/bin/bash
clear
read -r -p "SpExServer Data Processing Script, press any key to continue..."
# delete the old fits and text files
rm -rf ./backend/output/* || exit
# take and currently running containers offline
docker compose --profile web --profile api down || return
# delete the (to remake) the Django static files, and other cache/generated files
./shell/rm_volumes.sh || return
# build and start the backend, wait for it to finish processing
docker compose run --build --rm backend python update.py || exit
# bring down the backend
docker compose --profile web --profile api down || exit
