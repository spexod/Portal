#!/bin/bash
echo "SpExServer Update Script"
echo "Updating SpExo-FrontEnd Repository"
cd SpExo-FrontEnd
git restore .
git pull origin main
git checkout main
cd ../

cd SpExWebsite
git restore .
git pull origin main
git checkout main
cd ../
echo "completed: SpExServer Update Script"
