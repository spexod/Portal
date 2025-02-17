#!/bin/bash
clear
read -r -p "Portal Data Upload Script, press any key to continue..."
# upload the output FITs and TXT files
rsync -avz -e "ssh -i spexo-ssh-key.pem" ./backend/output ubuntu@spexodisks.com:/home/ubuntu/Portal/backend
# upload input data files
rsync -avz -e "ssh -i spexo-ssh-key.pem" ./backend/data ubuntu@spexodisks.com:/home/ubuntu/Portal/backend