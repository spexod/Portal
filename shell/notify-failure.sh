#!/bin/bash
# Called by spexodisks-failed@.service when one of the SpExoDisks systemd units fails (OnFailure=).
# Saves the unit's recent log to logs/ and sends the end of it as an alert:
#   ALERT_EMAIL        an email through the Django mail account in .env (DJANGO_EMAIL_HOST, _PORT, _USER,
#                      _APP_PASSWORD, the same settings the password-reset emails use)
#   ALERT_WEBHOOK_URL  a POST with the text as the body (ntfy.sh works out of the box:
#                      ALERT_WEBHOOK_URL=https://ntfy.sh/<topic>)
# Both may be set. Test by hand:  ./shell/notify-failure.sh spexodisks-auto-deploy.service
set -uo pipefail
cd "$(dirname "$0")/.."
unit=${1:?unit name}

mkdir -p logs
log="logs/$(date +%Y-%m-%d_%H%M)-${unit%.service}-failed.log"
journalctl -u "$unit" --since "-2 hours" --no-pager > "$log" 2>&1 || true
echo "saved the log of the failed run to $log"

env_value() { grep -E "^$1=" .env 2>/dev/null | tail -n1 | cut -d= -f2- | tr -d "\"'"; }
email=$(env_value ALERT_EMAIL)
url=$(env_value ALERT_WEBHOOK_URL)
title="spexodisks.com: $unit failed"
body=$(printf '%s on %s, %s\n\nlast lines of the log (%s):\n\n%s\n' "$unit failed" "$(hostname)" "$(date -u +'%Y-%m-%d %H:%M UTC')" "$log" "$(tail -n 40 "$log")")
sent=0

if [ -n "$email" ]; then
    # the message and the credentials reach python through the environment, never the command line
    # (python reads its code from stdin here, so the body cannot come through a pipe)
    if ALERT_EMAIL="$email" ALERT_TITLE="$title" ALERT_BODY="$body" \
        SMTP_HOST="$(env_value DJANGO_EMAIL_HOST)" SMTP_PORT="$(env_value DJANGO_EMAIL_PORT)" \
        SMTP_USER="$(env_value DJANGO_EMAIL_USER)" SMTP_PASSWORD="$(env_value DJANGO_EMAIL_APP_PASSWORD)" \
        python3 - <<'PY'
import os, smtplib, ssl, sys
from email.message import EmailMessage
host, port = os.environ["SMTP_HOST"] or "smtp.gmail.com", int(os.environ["SMTP_PORT"] or 587)
user, password = os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"]
if not user or not password or user == "None":
    sys.exit("DJANGO_EMAIL_USER and DJANGO_EMAIL_APP_PASSWORD are not set in .env")
msg = EmailMessage()
msg["From"], msg["To"], msg["Subject"] = user, os.environ["ALERT_EMAIL"], os.environ["ALERT_TITLE"]
msg.set_content(os.environ["ALERT_BODY"])
with smtplib.SMTP(host, port, timeout=30) as smtp:
    # a verifying context: without one, starttls() accepts any certificate and the password would go to
    # whoever answers for the mail host (Django's mail backend verifies, core/settings.py)
    smtp.starttls(context=ssl.create_default_context())
    smtp.login(user, password)
    smtp.send_message(msg)
PY
    then echo "alert emailed to $email"; sent=1
    else echo "the alert email could not be sent" >&2
    fi
fi

if [ -n "$url" ]; then
    if curl -fsS --max-time 20 -H "Title: $title" --data-binary "$body" "$url" >/dev/null; then
        echo "alert posted to the webhook"; sent=1
    else
        echo "the webhook alert could not be sent" >&2
    fi
fi

[ "$sent" = 1 ] || [ -n "$email$url" ] || echo "neither ALERT_EMAIL nor ALERT_WEBHOOK_URL is set in .env, no alert sent"
