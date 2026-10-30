#!/bin/bash
clear
read -r -p "Portal Deployment Update (runs update script on remote server), press any key to continue..."
# ssh into the server and pull the new images
ssh ubuntu@spexodisks.com -i spexo-ssh-key.pem "/home/ubuntu/Portal/shell/update.sh"
read -r -p  "completed: Portal Deployment Build Script, press any key prune docker cache..."
# replaced images only, this runs on the development computer and must not touch other projects' volumes
docker image prune --force