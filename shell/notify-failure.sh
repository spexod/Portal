#!/bin/bash
# Called by spexodisks-failed@.service when one of the SpExoDisks systemd units fails (OnFailure=).
# Saves the unit's recent log to logs/ and, when ALERT_WEBHOOK_URL is set in .env, posts the end of
# it there as plain text (ntfy.sh works out of the box: ALERT_WEBHOOK_URL=https://ntfy.sh/<topic>).
#
#   ./shell/notify-failure.sh <unit>        e.g. spexodisks-auto-deploy.service
set -uo pipefail
cd "$(dirname "$0")/.."
unit=${1:?unit name}

mkdir -p logs
log="logs/$(date +%Y-%m-%d_%H%M)-${unit%.service}-failed.log"
journalctl -u "$unit" --since "-2 hours" --no-pager > "$log" 2>&1 || true
echo "saved the log of the failed run to $log"

url=$(grep -E '^ALERT_WEBHOOK_URL=' .env 2>/dev/null | head -n1 | cut -d= -f2- | tr -d '"'"'"')
if [ -z "$url" ]; then
    echo "ALERT_WEBHOOK_URL is not set in .env, no alert sent"
    exit 0
fi
if curl -fsS --max-time 20 -H "Title: spexodisks.com: $unit failed" --data-binary "$(tail -n 40 "$log")" "$url" >/dev/null; then
    echo "alert sent"
else
    echo "the alert could not be sent" >&2
fi
