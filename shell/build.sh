#!/bin/bash
# Build Docker images for compose.yaml services with Docker Bake (what Docker Compose v5+ uses).
# Neither build needs network access to a running service: the backend reads data/reference_data
# at build time, the frontend renders its pages on request (SpExo-FrontEnd/app/layout.js).
#
# Usage (from the Portal directory):
#   ./shell/build.sh backend
#   ./shell/build.sh frontend --no-cache
#   ./shell/build.sh backend frontend
# versions.env (shell/refresh_versions.py) pins the exact base images and selects requirements.lock
if [ -f versions.env ]; then set -a; . ./versions.env; set +a; fi
docker buildx bake -f compose.yaml --load "$@"
