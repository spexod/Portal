#!/bin/bash
echo "SpExServer initialization Script"
echo "Downloading SpExo-FrontEnd Repository"
git clone https://github.com/spexod/SpExo-FrontEnd
cd SpExo-FrontEnd || exit
git checkout main
cd ../

cd backend || exit
git clone https://github.com/spexod/data
cd ../

echo "completed: SpExServer repository initialization script."
