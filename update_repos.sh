#!/bin/bash
echo "SpExServer Update Script"
echo "Updating SpExo-FrontEnd Repository"
cd SpExo-FrontEnd
git pull origin main
git checkout main
cd ../


echo "Updating SpExWebsite Repository"
cd SpExWebsite
git pull origin master
git checkout master
cd ../

# echo "Updating SpExoDisks Repository"
# cd SpExoDisks
# git pull origin main
# git checkout main
# cd ../
# echo "completed: SpExServer initialization Script"