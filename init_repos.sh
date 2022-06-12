#!/bin/bash
echo "SpExServer initialization Script"
echo "Downloading SpExo-FrontEnd Repository"
git clone https://github.com/L-Key/SpExo-FrontEnd
cd SpExo-FrontEnd
git checkout down-data
chmod -R 777 .
cd ../

echo "Downloading SpExWebsite Repository"
git clone https://github.com/isaacj96/SpExWebsite
cd SpExWebsite
git checkout git down-data
chmod -R 777 .
cd ../
cp sql_config.py SpExWebsite/.

echo "Downloading SpExoDisks Repository"
cd SpExWebsite
git clone https://github.com/chw3k5/SpExoDisks
cd SpExoDisks
git checkout main
chmod -R 777 .
cd ../
cd ../
cp sql_config.py SpExWebsite/SpExoDisks/mypysql/.

echo "Downloading autostar Repository"
cd SpExWebsite
cd SpExoDisks
git clone https://github.com/chw3k5/autostar
cd autostar
git checkout main
chmod -R 777 .
cd ../
cd ../
cd ../
echo "completed: SpExServer repository initialization script."
