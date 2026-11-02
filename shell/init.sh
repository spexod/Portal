#!/bin/bash
clear
read -r -p "Portal Initialization Script, press any key to continue..."
# checkout the main branch
git checkout main
# run the repository initialisation (download) script
echo "Portal initialization Script"
echo "Downloading SpExo-FrontEnd Repository"
git clone git@github.com:spexod/SpExo-FrontEnd.git

echo "Downloading Data Repository"
cd backend || exit
# private: needs an ssh key with access to spexod/data (README, "Uploading new data")
git clone git@github.com:spexod/data.git
cd ../

echo "completed: Portal repository initialization script."
# build the docker images
read -r -p  "completed: Portal Initialization Script, press any key to exit."
