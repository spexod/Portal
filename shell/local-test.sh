#!/bin/bash
# Reproduce the production database on the local MySQL container and test the API against it.
#
# The same steps as data.sh followed by the backend half of display.sh, without the prompts:
#   1. start mysqlDB and wait until it is healthy
#   2. build the backend image (shell/build.sh)
#   3. update.py processes backend/data and stages the result in the new_* schemas
#   4. commit_data.py marks the staged upload ready
#   5. backend + nginx start; the entrypoint moves the staged tables live (DATA_MIGRATE_FROM_STAGED=true)
#   6. tests/smoke.py checks the API (the frontend pages are not part of this: see display.sh)
#   7. tests/auth_flow.py registers a throwaway user and tests login, refresh, download, logout
#
# Needs: backend/data (the data repository, see shell/init.sh) and a .env for the local stack, see
# .env.example: MYSQL_HOST="mysqlDB", MYSQL_USER="root", any MYSQL_PASSWORD, DEBUG=true and, on an
# arm64 machine, DOCKER_PLATFORM=linux/arm64. The profiles, nginx config and data flags are set here.
#
# Usage (from the Portal directory):
#   ./shell/local-test.sh              full run; update.py takes about ten minutes
#   ./shell/local-test.sh --no-update  skip steps 2-4, test the data already in the local database
#   ./shell/local-test.sh --frontend   also build the frontend image against the local API (as display.sh
#                                      does, with SpExo-FrontEnd/.env.display), start it and test the pages
#   ./shell/local-test.sh --auto-deploy  with --frontend: also run shell/auto-deploy.sh against the local stack
#                                      twice, with a changed backend image (an update) and with a broken one
#                                      (a rollback). The stack then runs its images from a registry container
#                                      on localhost:5000, and the two test images, built on top of the tested
#                                      one, reach it through "docker compose pull", as on the server
#   ./shell/local-test.sh --down       stop the containers afterwards (the database files stay in mysql/local)
# Exit status: 0 when the smoke test passes, 1 otherwise.
set -euo pipefail
cd "$(dirname "$0")/.."

run_update=true
down_after=false
with_frontend=false
with_auto_deploy=false
for arg in "$@"; do
    case "$arg" in
        --no-update) run_update=false ;;
        --frontend) with_frontend=true ;;
        --auto-deploy) with_auto_deploy=true ;;
        --down) down_after=true ;;
        -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown option: $arg (see --help)" >&2; exit 1 ;;
    esac
done

# ---- the .env must point at the local database, never at the production server
[ -f .env ] || { echo "no .env file; copy .env.example to .env and set MYSQL_HOST=\"mysqlDB\"" >&2; exit 1; }
env_value() { grep -E "^$1=" .env | tail -n1 | cut -d= -f2- | tr -d "\"'"; }
mysql_host=$(env_value MYSQL_HOST)
if [ "$mysql_host" != "mysqlDB" ]; then
    echo "MYSQL_HOST is \"$mysql_host\" in .env; this script only runs against the local container (MYSQL_HOST=\"mysqlDB\")" >&2
    exit 1
fi
[ -d backend/data/reference_data ] || { echo "backend/data is missing, see shell/init.sh" >&2; exit 1; }

if [ "$with_auto_deploy" = true ] && [ "$with_frontend" = false ]; then
    echo "--auto-deploy needs --frontend: auto-deploy.sh checks every page" >&2; exit 1
fi

# the shell environment takes precedence over .env in compose, so the test settings go here
# local image names: the test stack never runs or pulls the registry's images (auto-deploy.sh's pull of
# the plain local names fails harmlessly, it ignores pull failures); with --auto-deploy the images live
# in a registry container, so that a pull really delivers a new image
registry=127.0.0.1:5000
if [ "$with_auto_deploy" = true ]; then
    export BACKEND_IMAGE=localhost:5000/spexodisks/backend:LATEST
    export FRONTEND_IMAGE=localhost:5000/spexodisks/frontend:LATEST
    docker rm -f spexodisks-test-registry >/dev/null 2>&1 || true
    docker run -d --rm --name spexodisks-test-registry -p "$registry:5000" registry:2 >/dev/null
    trap 'docker rm -f spexodisks-test-registry >/dev/null 2>&1' EXIT
    until curl -s "http://$registry/v2/" >/dev/null; do sleep 1; done
else
    export BACKEND_IMAGE=spexodisks-local/backend:LATEST
    export FRONTEND_IMAGE=spexodisks-local/frontend:LATEST
fi
# an image under the name this run uses: built by this run, or tagged from the last local build / the registry
have_image() {
    docker image inspect "$1" >/dev/null 2>&1 && return 0
    local source
    for source in "spexodisks-local/$2:LATEST" "ghcr.io/spexod/$2:LATEST"; do
        docker image inspect "$source" >/dev/null 2>&1 && { docker tag "$source" "$1"; return 0; }
    done
    echo "no image for $2: run without --no-update first" >&2; return 1
}
export COMPOSE_PROFILES=db,api
export NGINX_CONFIG_FILE=setup.conf
export API_USE_NEW_TABLES=false            # as in production: the API reads the live schemas
export DATA_NEW_UPLOADS_ONLY="${DATA_NEW_UPLOADS_ONLY:-true}"
export DATA_MIGRATE_FROM_STAGED=false      # only the final start migrates (step 5)

step() { printf '\n==== %s\n' "$*"; }

step "1. MySQL"
docker compose up --detach --wait mysqlDB

if [ "$run_update" = true ]; then
    step "2. backend image"
    ./shell/build.sh backend
    docker compose --profile api stop backend nginx 2>/dev/null || true
    mkdir -p backend/output
    step "3. update.py (stages the data in the new_* schemas)"
    docker compose run --rm backend python update.py
    step "4. commit_data.py"
    docker compose run --rm -e DB_INIT_ON_START=false backend python -m science.db.commit_data
fi

have_image "$BACKEND_IMAGE" backend || exit 1
[ "$with_auto_deploy" = true ] && docker push -q "$BACKEND_IMAGE" >/dev/null
step "5. backend + nginx (migrates the staged tables live)"
DATA_MIGRATE_FROM_STAGED=true docker compose up --detach --wait --force-recreate backend nginx

groups=api,auth
if [ "$with_frontend" = true ]; then
    step "5b. frontend image (the build needs no API), started against the local API through nginx"
    [ -d SpExo-FrontEnd/app ] || { echo "SpExo-FrontEnd is missing, see shell/init.sh" >&2; exit 1; }
    rm -rf SpExo-FrontEnd/.next
    cp SpExo-FrontEnd/.env.display SpExo-FrontEnd/.env.production
    ./shell/build.sh frontend
    have_image "$FRONTEND_IMAGE" frontend || exit 1
    [ "$with_auto_deploy" = true ] && docker push -q "$FRONTEND_IMAGE" >/dev/null
    COMPOSE_PROFILES=db,api,web docker compose up --detach --wait --force-recreate frontend
    groups=pages,api,auth,security   # security findings only warn (nginx/setup.conf has no TLS)
fi

step "6. smoke test ($groups)"
status=0
python3 tests/smoke.py --base-url http://localhost --only "$groups" || status=$?
if [ "$status" = 2 ]; then
    # nginx may need a moment to resolve the recreated containers
    sleep 10
    python3 tests/smoke.py --base-url http://localhost --only "$groups" && status=0 || status=$?
fi

if [ "$status" = 0 ]; then
    step "7. account API test (creates a throwaway user in the local database)"
    python3 tests/auth_flow.py --base-url http://localhost || status=$?
fi

# ---- the nightly update script against this stack: an update, then a rollback
auto_deploy() {
    SMOKE_BASE_URL=http://localhost SMOKE_ONLY=pages,api,auth COMPOSE_PROFILES=db,api,web \
        BACKEND_HEALTHY_TIMEOUT=240 KEEP_DUMPS=1 DATA_MIGRATE_FROM_STAGED=true ./shell/auto-deploy.sh
}
running_label() { docker inspect --format '{{index .Config.Labels "org.spexodisks.test"}}' backend; }
# Build a test image on top of the one the stack runs and publish it as LATEST in the registry container,
# without touching the local tags: the running image keeps its tag until auto-deploy.sh pulls, as on the
# server (a local image that loses its tag is garbage-collected by the containerd image store).
publish_candidate() {   # $1: the label that identifies the image, $2: extra Dockerfile lines
    local candidate="${BACKEND_IMAGE%:*}:candidate" name="spexodisks/backend" type manifest
    printf 'FROM %s\nLABEL org.spexodisks.test="%s"\n%s\n' "$BACKEND_IMAGE" "$1" "$2" \
        | docker build --quiet --tag "$candidate" - >/dev/null
    docker push -q "$candidate" >/dev/null
    manifest=$(mktemp)
    type=$(curl -s -I -H "Accept: application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.docker.distribution.manifest.v2+json" \
                "http://$registry/v2/$name/manifests/candidate" | grep -i '^content-type:' | cut -d' ' -f2 | tr -d '\r')
    curl -s -H "Accept: $type" "http://$registry/v2/$name/manifests/candidate" -o "$manifest"
    curl -s -X PUT -H "Content-Type: $type" --data-binary @"$manifest" "http://$registry/v2/$name/manifests/LATEST" -o /dev/null
    rm -f "$manifest"
    docker rmi "$candidate" >/dev/null
}
if [ "$status" = 0 ] && [ "$with_auto_deploy" = true ]; then
    step "8. auto-deploy.sh: a new backend image in the registry (one layer on top of the tested one) must go live"
    publish_candidate "update $(date -u +%FT%TZ)" ""
    if auto_deploy && case "$(running_label)" in update*) true ;; *) false ;; esac; then
        echo "update: ok, the backend runs the new image (label: $(running_label))"
    else
        echo "update FAILED: auto-deploy.sh did not put the new image live (label: '$(running_label)')" >&2
        status=1
    fi
    step "9. auto-deploy.sh: a broken backend image (never healthy) must be rolled back"
    good_label=$(running_label)
    publish_candidate "broken" 'CMD ["sh", "-c", "echo broken test image; sleep 600"]'
    if auto_deploy; then
        echo "rollback FAILED: auto-deploy.sh reported success with a broken image" >&2
        status=1
    elif [ "$(running_label)" = "$good_label" ]; then
        echo "rollback: ok, the previous image is running again (label: $good_label)"
    else
        echo "rollback FAILED: running label '$(running_label)', expected '$good_label'" >&2
        status=1
    fi
    # a last look at the site on the restored image
    python3 tests/smoke.py --base-url http://localhost --only pages,api,auth || status=$?
fi

if [ "$down_after" = true ]; then
    docker compose --profile api --profile web --profile db down
fi
if [ "$status" = 0 ]; then
    echo; echo "local test passed: the API serves the data processed from backend/data"
else
    echo; echo "local test FAILED (smoke test exit status $status)" >&2
    echo "backend log: docker compose logs backend" >&2
fi
exit "$status"
