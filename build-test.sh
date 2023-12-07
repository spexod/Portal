#!/bin/bash
clear
read -r -p "SpExServer TEST Build Script, press any key to continue..."
# test the build on a local machine
./shell/write-test-configs.sh
docker compose build
# stop here to look for error messages
echo " "
read -r -p "Test Build completed, press any key to launch the test-website and continue..."
docker compose up
docker compose down
echo " "
read -r -p "completed: SpExServer TEST Build Script, press any key to continue..."
