#!/bin/bash
clear
read -r -p "SpExServer Data Upload Script, press any key to continue..."
# upload the fits and text files
rsync -avz -e "ssh -i spexod-us-est-1.pem" ./backend/output ubuntu@spexodisks.com:/home/ubuntu/SpExServer/backend/output
# upload data files
rsync -avz -e "ssh -i spexod-us-est-1.pem" ./backend/data ubuntu@spexodisks.com:/home/ubuntu/SpExServer/backend/data