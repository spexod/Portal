#!/bin/sh
# Container entrypoint for the SpExoDisks backend.
#
# Runs before the image's CMD (gunicorn) and before any one-off command,
# e.g. `docker compose run --rm backend python update.py`.
# These steps used to run at image build time, which required a live database
# (and host networking) during the build and stored MySQL credentials in the image.
# Both steps are idempotent, so running them on every start is safe.
set -e

if [ "${DB_INIT_ON_START:-true}" = "true" ]; then
    echo "docker-entrypoint: creating MySQL schemas and tables if they do not exist..."
    python -m science.db.init
    echo "docker-entrypoint: applying Django migrations..."
    # the migrations change the users schema: run them with the pipeline account (core/settings.py reads
    # MYSQL_API_*; empty values fall back to MYSQL_USER/MYSQL_PASSWORD, as the pipeline account itself does)
    MYSQL_API_USER="${MYSQL_PIPELINE_USER:-}" MYSQL_API_PASSWORD="${MYSQL_PIPELINE_PASSWORD:-}" \
        python manage.py migrate --noinput
    # staged data from update.py + commit_data.py goes live here (only when DATA_MIGRATE_FROM_STAGED=true)
    echo "docker-entrypoint: migrating staged data, if any..."
    python -m science.db.migrate
fi

exec "$@"
