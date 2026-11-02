#!/bin/bash
# Put the data that data.sh staged live on spexodisks.com: copies the download files and the data
# directory to the server, marks the staged upload committed, restarts the backend there (its entrypoint
# moves the staged tables live) and checks the site. No image is built: since November 2026 the images
# come from GitHub (a merge to main), and a data upload needs no new image because the backend reads the
# tables and the data directory at start.
#
#   ./upload.sh            after a completed ./data.sh
#
# Needs: the server ssh access as "ssh spexo" (README, "Server ssh key"), or spexo-ssh-key.pem in this
# directory, and the .env that data.sh used (MYSQL_HOST="spexodisks.com").
set -euo pipefail
cd "$(dirname "$0")"

if [ -f spexo-ssh-key.pem ]; then
    ssh_command="ssh -i spexo-ssh-key.pem"
    server="ubuntu@spexodisks.com"
else
    ssh_command="ssh"
    server="spexo"
fi

echo "Portal Data Upload: puts the staged data live on spexodisks.com"
echo
echo "the database this computer's .env points to, and what is staged there now:"
./shell/data-status.sh
echo
read -r -p "upload the files, commit the staged data and restart the backend on the server? press any key to continue, control-c to stop..."

echo
echo "1. copying backend/output (the FITS and TXT files served as downloads) to the server..."
rsync -avz -e "$ssh_command" ./backend/output "$server":/home/ubuntu/Portal/backend
echo "2. copying backend/data (the input data) to the server..."
rsync -avz -e "$ssh_command" ./backend/data "$server":/home/ubuntu/Portal/backend

echo "3. marking the staged data committed (the backend moves it live at its next start)..."
# DB_INIT_ON_START=false: only the status flag changes here, the schema steps of the entrypoint are not needed
docker compose run --rm -e DB_INIT_ON_START=false backend python -m science.db.commit_data

echo "4. restarting the backend on the server (it waits for MySQL, moves the staged tables live and starts the API)..."
$ssh_command "$server" "cd /home/ubuntu/Portal && docker compose restart backend && docker compose up --detach --wait backend"

echo "5. checking the site..."
sleep 10   # nginx re-resolves the backend's address (resolver valid=30s in nginx/deploy.conf)
python3 tests/smoke.py --base-url https://spexodisks.com --only api
echo
echo "live now:"
curl -s "https://spexodisks.com/api/stats_total/?format=json"; echo
echo "completed: Portal Data Upload"
