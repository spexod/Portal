#!/bin/bash
echo "SpExServer initialization Script"
echo "Downloading SpExo-FrontEnd Repository"
git clone https://github.com/L-Key/SpExo-FrontEnd
git checkout main

echo "Downloading SpExWebsite Repository"
git clone https://github.com/isaacj96/SpExWebsite
git checkout main
cp sql_config.py SpExWebsite/.

echo "Downloading SpExoDisks Repository"
git clone https://github.com/chw3k5/SpExoDisks
git checkout main
cp sql_config.py SpExoDisks/mypysql/.

echo "Downloading autostar Repository"
git clone https://github.com/chw3k5/autostar SpExoDisks/autostar
git checkout main
echo "completed: SpExServer repository initialization script."
