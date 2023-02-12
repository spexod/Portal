#!/bin/bash
echo "SpExServer initialization Script"
cp ../sql_config.py .
echo "Downloading SpExo-FrontEnd Repository"
git clone https://github.com/spexod/SpExo-FrontEnd
cd SpExo-FrontEnd
git checkout main
cd ../

echo "Downloading SpExWebsite Repository"
git clone https://github.com/spexod/SpExWebsite
cd SpExWebsite
git checkout main
cp ../sql_config.py .
./init-spexodisks.sh
cd ../

echo "completed: SpExServer repository initialization script."
