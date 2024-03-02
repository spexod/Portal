#!/bin/bash
echo "SpExServer Update Script"
echo "Updating SpExo-FrontEnd Repository"
cd SpExo-FrontEnd || exit
git restore .
git pull origin main
git checkout main
cd ../

cd backend || exit
git restore .
git pull origin main
git checkout main
cd ../
echo "completed: SpExServer Update Script"
