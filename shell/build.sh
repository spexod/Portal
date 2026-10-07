#!/bin/bash
# Build Docker images for compose.yaml services with Docker Bake.
#
# Docker Compose v5+ always builds through Bake, and Bake refuses builds that use
# `build: network: host` unless the permission is granted explicitly. `docker compose`
# has no flag for that, so the scripts build with this helper and then run Compose
# commands without --build. (The frontend build uses host networking to reach the local API.)
#
# Usage (from the Portal directory):
#   ./shell/build.sh backend
#   ./shell/build.sh frontend --no-cache
#   ./shell/build.sh backend frontend
docker buildx bake -f compose.yaml --allow=network.host --load "$@"
