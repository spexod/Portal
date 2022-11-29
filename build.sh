#!/bin/bash
# test the build on a local machine
./write_test_configs.sh
# docker-compose build
docker-compose up
docker-compose down
# upload a production version of the website for the Server
./write_product_configs.sh
# docker build --file ./SpExWebsite/Dockerfile --tag backend:latest
# docker push  ghcr.io/spexod/backend:latest

docker build --file ./SpExo-FrontEnd/front-app/Dockerfile --tag frontend:latest
# docker push  ghcr.io/spexod/fontend:latest
