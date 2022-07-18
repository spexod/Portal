#!/bin/bash
echo "SpExServer Update Script"
echo "Updating SpExo-FrontEnd Repository"
cd SpExo-FrontEnd
git restore .
git pull origin main
git checkout main
cd ../


echo "Updating SpExWebsite Repository"
cd SpExWebsite
git restore .
git pull origin main
git checkout main

./update_repos.sh
cd ../
echo "completed: SpExServer Update Script"
