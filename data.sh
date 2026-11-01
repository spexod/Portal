#!/bin/bash
clear
read -r -p "Portal Data Processing Script, press any key to continue..."
# say which database this run writes to, and what is staged there now, before anything is deleted
./shell/data-status.sh || exit
read -r -p "update.py will stage the processed data in that database's new_* schemas, press any key to continue..."
# delete the old fits and text files
rm -rf ./backend/output/* || exit
# take and currently running containers offline
docker compose --profile web --profile api down || exit
# delete the (to remake) the Django static files, and other cache/generated files
./shell/rm_volumes.sh || exit
# build and start the backend, wait for it to finish processing
./shell/build.sh backend || exit
docker compose run --rm backend python update.py || exit
echo "staged (not yet committed: ./deploy.sh commits it, the backend moves it live at its next start):"
./shell/data-status.sh || exit
# bring down the backend
docker compose --profile web --profile api down || exit
