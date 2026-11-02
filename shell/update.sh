#!/bin/bash
# Update the server to the current main and the current images, then check the site.
#   ./shell/update.sh            the update
#   ./shell/update.sh --check    dry run: fetch main (the checkout stays as it is), validate main's compose
#                                configuration with the server's .env, and list the images an update would
#                                pull; nothing is pulled, stopped or started, so the nightly update is not
#                                triggered either (run it before an update that changes compose.yaml or
#                                needs new .env values)
# stop at the first failure: a failed pull must not take the running site down
set -euo pipefail
check=false
[ "${1:-}" = "--check" ] && check=true
# no "clear": over the ssh in deploy_update.sh there is no terminal, clear fails on the missing TERM,
# and with set -e that ended the script before the pull (2026-11-01)
echo "SpExServer Update Script"
cd /home/ubuntu/Portal/ || exit
user='chw3k5'
if [ "$check" = true ]; then
    git fetch --quiet origin main
    echo "commits an update would bring in:"
    git log --oneline HEAD..origin/main | cat
    compose_check=$(mktemp --suffix=.yaml)
    git show origin/main:compose.yaml > "$compose_check"
    docker compose -f "$compose_check" --env-file .env config --quiet && echo "main's compose configuration with this .env: ok"
    echo "images an update would pull:"
    docker compose -f "$compose_check" --env-file .env config --images
    rm -f "$compose_check"
    echo "check passed: nothing was pulled, stopped or started"
    exit 0
fi
# This is public repo, so we can pull without authentication, to update the compose file
git pull origin main
# log in to THe GitHub Container Registry
cat .git_token.txt | docker login ghcr.io --username "${user}" --password-stdin
# the compose file and the .env agree (a missing required value fails here, not after "down")
docker compose config --quiet && echo "compose configuration: ok"
# pull the fresh version from the container registry
docker compose pull
# take the currently running continues offline
docker compose down
# delete the (to remake) the Django static files and other temp files
./shell/rm_volumes.sh
# start the new containers from the pulled images; --wait returns when the healthchecks pass
# (the backend first creates missing schemas, applies Django migrations and moves staged data live, see
# backend/docker-entrypoint.sh)
docker compose up --detach --wait
# every page and API endpoint, then the security settings (a failure stops the script before the prune)
sleep 10   # nginx re-resolves the container addresses (resolver valid=30s in nginx/deploy.conf)
python3 tests/smoke.py --base-url "${SMOKE_BASE_URL:-https://spexodisks.com}"
# clear the old images and cache to keep the disk usage down on the server computer
echo -e "\nCompleted: Portal Update Script, check the website at spexodisks.com."
# the prune needs a terminal for the prompt (ssh -t in deploy_update.sh, or an interactive session);
# without one the script ends here and the replaced images stay until "docker image prune --force"
if [ -t 0 ]; then
    read -r -p "After confirming the site, press any key to prune the docker cache (deleting replaced docker images)..."
    # images only: never volumes (the Let's Encrypt certificates live in one)
    docker image prune --force
else
    echo "no terminal: skipping the prune prompt; run 'docker image prune --force' on the server after checking the site"
fi
echo "completed: Portal Update Script"
