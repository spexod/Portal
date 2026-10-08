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
    python manage.py migrate --noinput
fi

exec "$@"
