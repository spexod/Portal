#!/bin/bash
echo "SpExServer initialization Script"
cp ../sql_config.py .
echo "Downloading SpExo-FrontEnd Repository"
git clone https://github.com/spexod/SpExo-FrontEnd
cd SpExo-FrontEnd
git checkout main
cd ../

cd SpExWebsite
git clone https://github.com/spexod/data
cd ../

echo "completed: SpExServer repository initialization script."
