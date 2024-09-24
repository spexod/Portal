#!/bin/bash
clear
read -r -p "Portal Data Upload Script, press any key to continue..."
# upload the fits and text files
rsync -avz -e "ssh -i spexo-ssh-key.pem" ./backend/output ubuntu@spexodisks.com:/home/ubuntu/Portal/backend/output
# upload data files
rsync -avz -e "ssh -i spexo-ssh-key.pem" ./backend/data ubuntu@spexodisks.com:/home/ubuntu/Portal/backend/data