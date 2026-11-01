#!/bin/bash
clear
read -r -p "Portal Data Upload Script, press any key to continue..."
# upload the output FITs and TXT files
rsync -avz -e "ssh -i spexo-ssh-key.pem" ./backend/output ubuntu@spexodisks.com:/home/ubuntu/Portal/backend
# upload input data files
rsync -avz -e "ssh -i spexo-ssh-key.pem" ./backend/data ubuntu@spexodisks.com:/home/ubuntu/Portal/backend
echo "Portal Deployment Build Script"
# take and currently running containers offline and delete any volumes from the last build
docker compose --profile web --profile api down
# delete the (to remake) the Django static files
./shell/rm_volumes.sh
# delete the output directory contents
rm -rf ./backend/output/*
# build the backend image
./shell/build.sh backend || exit
# the frontend image: the pages are rendered on request, so the build needs no API; its settings are the
# build args in compose.yaml (NEXT_PUBLIC_*) and the run-time environment, not env files
rm -rf SpExo-FrontEnd/.next SpExo-FrontEnd/.env.production || exit
# build in the docker container
./shell/build.sh frontend --no-cache || exit
# stop here to look for error messages
echo -e "\nDevelopment Build completed,"
read -r -p "Pushing the new images to the container repository"
./shell/ghcr-login.sh
docker compose push || exit
# once everything else is competed, we mark the database as ready to be updated
./shell/data-status.sh || exit
read -r -p "commit the staged data above (the backend moves it live at its next start)? press any key to continue, control-c to stop..."
# (DB_INIT_ON_START=false: only the status flag changes here, the schema steps of the entrypoint are not needed)
docker compose run --rm -e DB_INIT_ON_START=false backend python -m science.db.commit_data || exit
echo " completed the push to the container repository, continue the update with ./deploy_update.sh"