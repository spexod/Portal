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
#   ./shell/local-test.sh --down       stop the containers afterwards (the database files stay in mysql/local)
# Exit status: 0 when the smoke test passes, 1 otherwise.
set -euo pipefail
cd "$(dirname "$0")/.."

run_update=true
down_after=false
with_frontend=false
for arg in "$@"; do
    case "$arg" in
        --no-update) run_update=false ;;
        --frontend) with_frontend=true ;;
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

# the shell environment takes precedence over .env in compose, so the test settings go here
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

step "5. backend + nginx (migrates the staged tables live)"
DATA_MIGRATE_FROM_STAGED=true docker compose up --detach --wait --force-recreate backend nginx

groups=api,auth
if [ "$with_frontend" = true ]; then
    step "5b. frontend image, built against the local API through nginx (http://localhost/)"
    [ -d SpExo-FrontEnd/app ] || { echo "SpExo-FrontEnd is missing, see shell/init.sh" >&2; exit 1; }
    rm -rf SpExo-FrontEnd/.next
    cp SpExo-FrontEnd/.env.display SpExo-FrontEnd/.env.production
    ./shell/build.sh frontend
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
