#!/bin/bash
echo "SpExServer Update Script"
echo "Updating SpExServer Repository"
# make sure the script is running from the correct directory
cd ../SpExServer || exit
git restore .
git pull origin main
git checkout main

echo "Updating SpExo-FrontEnd Repository"
cd SpExo-FrontEnd || exit
git restore .
git pull origin main
git checkout main
cd ../

cd backend/data || exit
git restore .
git pull origin main
git checkout main
cd ../
echo "completed: SpExServer Update Script"
