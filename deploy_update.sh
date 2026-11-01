#!/bin/bash
clear
read -r -p "Portal Deployment Update (runs update script on remote server), press any key to continue..."
# pull main on the server first, in its own step: update.sh is part of the checkout, and a script that
# updates itself while bash is executing it keeps running the old copy (2026-11-01)
ssh -i spexo-ssh-key.pem ubuntu@spexodisks.com "cd /home/ubuntu/Portal && git pull origin main" || exit
# run the update with a terminal (-t): update.sh prompts before the prune. A failed update (pull, image
# pull, healthcheck, smoke test) stops here, with nothing pruned on either computer
ssh -t -i spexo-ssh-key.pem ubuntu@spexodisks.com "/home/ubuntu/Portal/shell/update.sh" || {
    echo "the server update failed, see the output above (docker compose ps / logs backend on the server)" >&2
    exit 1
}
read -r -p  "completed: Portal Deployment Update, press any key to prune the docker cache on this computer..."
# replaced images only, this runs on the development computer and must not touch other projects' volumes
docker image prune --force