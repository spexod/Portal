#!/bin/bash
clear
echo "SpExServer Initialization Script"
cd /opt/bitnami/ || return
mkdir projects && chmod 751 projects && cd projects/ || exit
git clone https://github.com/chw3k5/SpExServer .
git checkout main
./int_repos.sh
docker-compose down
docker-compose build
docker-compose up -d
echo "completed: SpExServer Update Script"