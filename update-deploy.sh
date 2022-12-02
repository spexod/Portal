#!/bin/bash
clear
echo "SpExServer Update Script"
cd /opt/bitnami/projects/ || return
git checkout main
git pull origin main
# run the update script (pull-deploy.sh) from the pulled version of SpExServer repo
./pull-deploy.sh
echo "completed: SpExServer Update Script"
