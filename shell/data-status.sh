#!/bin/bash
# Print which database the pipeline scripts talk to and the state of the staged data, so data.sh and
# deploy.sh say what they are about to do before they do it.
#   ./shell/data-status.sh
cd "$(dirname "$0")/.."
docker compose run --rm -T -e DB_INIT_ON_START=false backend python - <<'PY' 2>/dev/null | grep -E "^(database|account|staged|committed|migrated)"
from science.db.sql import MYSQL_HOST, MYSQL_USER, update_mode
from science.db.data_status import get_data_status_mysql
staged, committed, migrated = get_data_status_mysql()
print(f"database: {MYSQL_HOST}  (DATA_NEW_UPLOADS_ONLY={update_mode}: {'only new spectra are uploaded' if update_mode else 'everything is re-uploaded'})")
print(f"account:  {MYSQL_USER}")
print(f"staged:   {staged}   (update.py wrote the new_* schemas and output files)")
print(f"committed:{committed}   (deploy.sh marked the staging ready; the backend moves it live at its next start)")
print(f"migrated: {migrated}   (the last staging went live)")
PY
