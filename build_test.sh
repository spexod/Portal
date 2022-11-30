#!/bin/bash
clear
read -r -p "SpExServer TEST Build Script, press any key to continue..."
# test the build on a local machine
./write_test_configs.sh
docker compose build
echo " "
read -r -p "Test Build completed, press any key to launch the test-website and continue..."
docker compose up
docker compose down
echo " "
read -r -p "completed: SpExServer TEST Build Script, press any key to continue..."
