#!/bin/bash
echo -e "API_BASE_SERVER=http://backend:8000/\nNEXT_PUBLIC_API_BASE_CLIENT=http://localhost/" > ./SpExo-FrontEnd/.env.production
sudo cp ./spexod-us-est-1.pem ./backend/spexod-us-est-1.pem
sudo chmod 400 ./backend/spexod-us-est-1.pem
