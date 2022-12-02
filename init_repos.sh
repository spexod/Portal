#!/bin/bash
echo "SpExServer initialization Script"
echo "Downloading SpExo-FrontEnd Repository"
git clone https://github.com/spexod/SpExo-FrontEnd
cd SpExo-FrontEnd
git checkout main
cd ../
chmod -R 777 SpExo-FrontEnd

echo "Downloading SpExWebsite Repository"
git clone https://github.com/spexod/SpExWebsite
cd SpExWebsite
git checkout main
cp ../sql_config.py .
./init_spexodisks.sh
cd ../

echo "completed: SpExServer repository initialization script."