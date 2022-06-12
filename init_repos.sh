#!/bin/bash
echo "SpExServer initialization Script"
echo "Downloading SpExo-FrontEnd Repository"
git clone https://github.com/L-Key/SpExo-FrontEnd
cd SpExo-FrontEnd
git checkout down-data
cd ../
chmod -R 777 SpExo-FrontEnd

echo "Downloading SpExWebsite Repository"
git clone https://github.com/isaacj96/SpExWebsite
cd SpExWebsite
git checkout down-data
cd ../

cd SpExWebsite
cp ../sql_config.py .
./init_repos.sh
cd ../
echo "completed: SpExServer repository initialization script."