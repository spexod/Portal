#!/bin/bash
# Non-interactive update of the running website.
#
# Pulls the images of the long-running services (not MySQL), recreates the containers whose image
# changed, checks the site with the smoke test (tests/smoke.py) and goes back to the previous images
# when it fails. Before a backend update it dumps the database and resets the Django static-files
# volume, which is only filled from the image when it is empty.
#
# Run by the systemd timer spexodisks-auto-deploy (see "Automatic updates" in shell/auto_update.md).
# By hand on the server:  sudo systemctl start spexodisks-auto-deploy.service
#                         journalctl -u spexodisks-auto-deploy
# Unlike shell/update.sh this never runs "docker compose down" and never prunes volumes.
#
# Environment: SMOKE_BASE_URL (default https://spexodisks.com), SMOKE_ONLY (check groups for tests/smoke.py,
# default all), KEEP_DUMPS (default 3), BACKEND_HEALTHY_TIMEOUT (seconds to wait for the backend's
# healthcheck, default 300). shell/local-test.sh --auto-deploy runs this script against the local stack.
set -euo pipefail
cd "$(dirname "$0")/.."

# never run two updates at once (the lock file is in the Portal directory, owned by the deploy user)
exec 9>.auto-deploy.lock
flock -n 9 || { echo "another update is running"; exit 0; }

smoke_base_url=${SMOKE_BASE_URL:-https://spexodisks.com}
keep_dumps=${KEEP_DUMPS:-3}
backend_timeout=${BACKEND_HEALTHY_TIMEOUT:-300}

# The services this script updates: the long-running ones of the enabled profiles, except MySQL.
# MySQL stays on the version in MYSQL_VERSION: a database upgrade at 04:00 has no way back
# (see "MySQL Version Upgrades" in README.md).
mapfile -t services < <(docker compose config --services | grep -vxE 'mysqlDB|certbot|ipython' || true)
if [ ${#services[@]} -eq 0 ]; then
    echo "no services to update (COMPOSE_PROFILES in .env)"
    exit 0
fi

container_of() { docker compose ps -aq "$1" 2>/dev/null | head -n1; }
# image ID a service's container runs, and the tag it was created from (empty when there is no container)
image_of() { docker inspect --format '{{.Image}}' "$(container_of "$1")" 2>/dev/null || true; }
tag_of() { docker inspect --format '{{.Config.Image}}' "$(container_of "$1")" 2>/dev/null || true; }
has() { local s; for s in "${@:2}"; do [ "$s" = "$1" ] && return 0; done; return 1; }

project=$(docker compose config --format json | python3 -c 'import json, sys; print(json.load(sys.stdin)["name"])')

# nginx serves the Django static files from this volume; it is filled from the backend image only
# when empty, so a backend update has to start with an empty volume (as shell/update.sh does)
reset_static_volume() {
    local volume
    volume=$(docker volume ls -q --filter "label=com.docker.compose.project=$project" \
                                 --filter "label=com.docker.compose.volume=django_static")
    [ -z "$volume" ] && return 0
    # Docker refuses to remove a volume while a container references it, stopped or not, so the two
    # containers that mount it go first ("docker compose up" below recreates them). The first real
    # backend update (2026-11-01) stopped here with "volume is in use" and left the site down.
    docker compose rm --force --stop backend nginx
    docker volume rm --force "$volume" >/dev/null
    echo "reset the static-files volume $volume"
}

wait_for_backend() {
    has backend "${services[@]}" || return 0
    local state _
    for _ in $(seq "$((backend_timeout / 5))"); do   # up to 5 minutes by default, the healthcheck needs the database
        state=$(docker inspect --format '{{.State.Health.Status}}' "$(container_of backend)" 2>/dev/null || echo none)
        [ "$state" = healthy ] && return 0
        sleep 5
    done
    echo "the backend did not become healthy (state: $state)" >&2
    return 1
}

# the smoke test covers every page and API endpoint, the container healthchecks only one URL each
site_is_healthy() {
    wait_for_backend || return 1
    sleep 10   # nginx re-resolves the container addresses every 30s (resolver valid=30s in nginx/deploy.conf)
    python3 tests/smoke.py --base-url "$smoke_base_url" ${SMOKE_ONLY:+--only "$SMOKE_ONLY"}
}

# ---- what is running now, to compare and to roll back to. The running image gets a "previous" tag:
# an image that loses its tag and its container is garbage-collected by Docker's containerd image
# store, so a rollback by image id alone can find nothing to roll back to (seen in local-test.sh
# --auto-deploy, 2026-11-01); a tagged image stays, and "docker image prune" leaves it alone
declare -A before before_tag previous_tag
for s in "${services[@]}"; do
    before[$s]=$(image_of "$s")
    before_tag[$s]=$(tag_of "$s")
    [ -z "${before_tag[$s]}" ] && continue
    previous_tag[$s]="${before_tag[$s]%:*}:previous"
    # a container whose image is gone from the store (pruned by hand) has nothing to keep: say so and go on
    docker tag "${before[$s]}" "${previous_tag[$s]}" \
        || echo "no image to keep as ${previous_tag[$s]} (the running one is not in the store)" >&2
done

docker compose pull --quiet --ignore-pull-failures "${services[@]}"

changed=()
for s in "${services[@]}"; do
    [ -z "${before_tag[$s]}" ] && continue   # no container yet, nothing to compare with
    new_image=$(docker image inspect --format '{{.Id}}' "${before_tag[$s]}" 2>/dev/null || true)
    if [ -n "$new_image" ] && [ "$new_image" != "${before[$s]}" ]; then
        changed+=("$s")
    fi
done
if [ ${#changed[@]} -eq 0 ]; then
    echo "no new images, nothing to do"
    exit 0
fi
echo "new images for: ${changed[*]}"

# ---- a backend update changes the database schema at start (docker-entrypoint.sh): keep a way back
dump_file=""
if has backend "${changed[@]}"; then
    if docker compose ps --services --status running | grep -qx mysqlDB; then
        ./mysql/upgrade.sh dump
        dump_file=$(ls -t mysql/dump-*.sql.gz | head -n1)
        echo "database dump before the update: $dump_file"
        # keep the last few dumps only
        ls -t mysql/dump-*.sql.gz | tail -n +"$((keep_dumps + 1))" | xargs -r rm --
    else
        echo "no local mysqlDB container, no database dump taken" >&2
    fi
    reset_static_volume || { echo "could not reset the static-files volume, starting the containers again" >&2
                             docker compose up --detach --no-build "${services[@]}"; exit 1; }
fi

# ---- recreate the containers with new images. From here on nothing may end the script early: the
# containers are down or half replaced, and the rollback below is the only way back
set +e
healthy=true
docker compose up --detach --no-build --remove-orphans "${services[@]}" || healthy=false
if [ "$healthy" = true ]; then
    site_is_healthy || healthy=false
fi

if [ "$healthy" = true ]; then
    # replaced images only (volumes, including the certificates and the database files, are untouched)
    docker image prune --force >/dev/null
    echo "update completed: ${changed[*]}"
    exit 0
fi

# ---- roll back every changed service to the image it ran before (kept under its "previous" tag)
echo "the site is not healthy after the update, rolling back: ${changed[*]}" >&2
for s in "${changed[@]}"; do
    docker tag "${previous_tag[$s]}" "${before_tag[$s]}"
done
if has backend "${changed[@]}"; then
    reset_static_volume
fi
docker compose up --detach --no-build --force-recreate "${changed[@]}" || true
# reset_static_volume stopped backend and nginx; start whatever is not running again (nginx is rarely in "changed")
docker compose up --detach --no-build "${services[@]}" || true
if site_is_healthy; then
    echo "rollback completed, the previous images are running again" >&2
else
    echo "ROLLBACK DID NOT RESTORE THE SITE, manual intervention needed" >&2
fi
if [ -n "$dump_file" ]; then
    echo "a new backend image may have changed the database schema; the dump from before the update is $dump_file" >&2
    echo "(restore with: ./mysql/upgrade.sh restore $dump_file)" >&2
fi
exit 1
