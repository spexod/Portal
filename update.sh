#!/bin/bash
clear
echo "SpExServer Update Script"
cd /opt/bitnami/projects/ || return
git checkout main
git pull origin main
./update_repos.sh
echo "completed: SpExServer Update Script"
