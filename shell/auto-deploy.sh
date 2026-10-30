#!/bin/bash
# Non-interactive update of the running website: pull the images, recreate only the containers whose
# image changed, and go back to the previous image if the backend does not become healthy.
#
# Run by the systemd unit spexodisks-auto-deploy.service (see "Automatic updates" in shell/auto_update.md).
# By hand on the server:  sudo systemctl start spexodisks-auto-deploy.service   (log: journalctl -u spexodisks-auto-deploy)
# Unlike shell/update.sh this never runs "docker compose down" and never prunes volumes.
set -euo pipefail
cd "$(dirname "$0")/.."

# never run two updates at once
exec 9>/tmp/spexodisks-auto-deploy.lock
flock -n 9 || { echo "another update is running"; exit 0; }

services=$(docker compose config --services)
# remember the image each service runs now, to roll back to it
declare -A before
for s in $services; do
    before[$s]=$(docker inspect --format '{{.Image}}' "$(docker compose ps -q "$s" 2>/dev/null | head -n1)" 2>/dev/null || true)
done

docker compose pull --quiet --ignore-pull-failures
# only containers with a new image (or changed compose.yaml) are recreated
docker compose up --detach --no-build --remove-orphans

# wait up to 5 minutes for the backend healthcheck
healthy=false
if [ -z "$(docker compose ps -q backend)" ]; then healthy=true; fi
for _ in $(seq 60); do
    [ "$healthy" = true ] && break
    state=$(docker inspect --format '{{.State.Health.Status}}' backend 2>/dev/null || echo none)
    if [ "$state" = healthy ]; then healthy=true; else sleep 5; fi
done

# the smoke test covers every page and API endpoint (tests/smoke.py), the container healthcheck only one
if [ "$healthy" = true ]; then
    sleep 10   # nginx re-resolves the container addresses every 30s (resolver valid=30s in nginx/deploy.conf)
    python3 tests/smoke.py --base-url "${SMOKE_BASE_URL:-https://spexodisks.com}" || healthy=false
fi

if [ "$healthy" != true ]; then
    echo "the site is not healthy after the update, rolling back" >&2
    if [ -n "${before[backend]:-}" ]; then
        docker tag "${before[backend]}" ghcr.io/spexod/backend:LATEST
        docker compose up --detach --no-build --force-recreate backend
    fi
    exit 1
fi

# remove replaced images only (volumes, including the certificates and the database files, are untouched)
docker image prune --force
echo "update completed"
