#!/bin/bash
clear
read -r -p "SpExServer Initialization Script, press any key to continue..."
# checkout the main branch
git checkout main
# run the repository initialisation (download) script
./shell/init-repos.sh
# build the docker images
read -r -p  "completed: SpExServer Initialization Script, press any key to exit."
