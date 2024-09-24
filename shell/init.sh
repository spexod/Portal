#!/bin/bash
clear
read -r -p "Portal Initialization Script, press any key to continue..."
# checkout the main branch
git checkout main
# run the repository initialisation (download) script
echo "Portal initialization Script"
echo "Downloading SpExo-FrontEnd Repository"
git clone https://github.com/spexod/SpExo-FrontEnd

echo "Downloading Data Repository"
cd backend || exit
git clone https://github.com/spexod/data
cd ../

echo "completed: Portal repository initialization script."
# build the docker images
read -r -p  "completed: Portal Initialization Script, press any key to exit."
