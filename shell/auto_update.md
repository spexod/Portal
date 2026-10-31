# One-time setup for Automatic Updates for Ubuntu cloud server
This needs to be setup once on the server to allow automatic updates
## install packages (usually these are already installed)
```
sudo apt-get install unattended-upgrades update-notifier-common
```
## enable automatic updates (this launches an interactive prompt)
See detailed in instructions: https://help.ubuntu.com/community/AutomaticSecurityUpdates

```
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

Select `yes` when the interactive prompt launch to enable updates.
THis creates a file we can open in an editor.

## open the file in an editor, to enable automatic reboots

```
sudo nano /etc/apt/apt.conf.d/50unattended-upgrades
```

Uncomment the line the about automatic reboots and set to `true`,
the final line should look like this:

```
Unattended-Upgrade::Automatic-Reboot "true";'
```

and

```
Unattended-Upgrade::Automatic-Reboot-WithUsers "true";
```

Save the file and exit.

## check the status of the automatic updates

```
apt-config dump APT::Periodic::Unattended-Upgrade
```

Which should return something like:

```
>>> APT::Periodic::Unattended-Upgrade "1";
```

Now the server will automatically update
and reboot as needed.

# Automatic updates for the website itself

The operating system is covered by `unattended-upgrades` above. The containers are updated in layers:

| Layer | What updates it | How often |
|---|---|---|
| Ubuntu packages | `unattended-upgrades` (this file) | daily |
| Python dependencies and the backend base image | `.github/dependabot.yml` opens PRs; `.github/workflows/security.yml` audits them (pip-audit, Trivy) and rebuilds and publishes `ghcr.io/spexod/backend:LATEST` (plus a `sha-<commit>` tag) from `main` | PRs weekly, rebuild Mondays |
| nginx image | `docker compose pull` (nginx follows `stable`) | nightly |
| Running containers | `shell/auto-deploy.sh` through the `spexodisks-auto-deploy` timer, see below | nightly at 04:00 |

**Not automatic, on purpose:**

- **MySQL** stays on `MYSQL_VERSION`; `auto-deploy.sh` never pulls or recreates `mysqlDB`. Even a patch
  release upgrades the data files in place at 04:00 with nobody watching. Update it by hand, see
  "MySQL Version Upgrades" in README.md.
- **The frontend image** is not rebuilt in GitHub Actions, because its build needs the live API
  (see `deploy.sh`). Dependabot PRs in the SpExo-FrontEnd repository still need `./deploy.sh` to reach
  the site; once published, the nightly update picks the new image up.

## What `shell/auto-deploy.sh` does

1. Pulls the images of the long-running services of the enabled profiles (`backend`, `frontend`, `nginx`)
   and stops if none changed.
2. Before a backend update: dumps the database (`./mysql/upgrade.sh dump`, keeps the last `KEEP_DUMPS=3`
   dumps in `mysql/`) because the new image applies its migrations at start, and empties the Django
   static-files volume, which is only filled from the image when empty.
3. Recreates the containers with new images, waits for the backend healthcheck and runs the smoke test
   (`tests/smoke.py`) against `SMOKE_BASE_URL` (default `https://spexodisks.com`).
4. If the smoke test fails: re-tags the previous images, recreates the changed containers, runs the smoke
   test again and exits with an error either way. The unit's `OnFailure=` then runs
   `shell/notify-failure.sh`, which saves the log to `logs/` and posts it to `ALERT_WEBHOOK_URL` from `.env`
   when set (plain-text POST; `https://ntfy.sh/<your-topic>` works without any setup).

It never runs `docker compose down` and never removes volumes.

## One-time setup on the server

```
sudo install -m 644 shell/systemd/spexodisks-* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now spexodisks-auto-deploy.timer
```

Repeat the first two commands after changing a file in `shell/systemd/`. The `OnFailure=` alerts need
the units installed again (the certbot units got it too).

Test it once by hand: `sudo systemctl start spexodisks-auto-deploy.service`, then
`journalctl -u spexodisks-auto-deploy`. The server needs to be logged in to ghcr.io (`shell/ghcr-login.sh`)
for private images. To get alerts, add `ALERT_WEBHOOK_URL=...` to `.env` and test with
`./shell/notify-failure.sh spexodisks-auto-deploy.service`.

## One-time setup on GitHub

The image build in `security.yml` needs `backend/data/reference_data` from the private `spexod/data`
repository. In the Portal repository settings add the Actions secret `DATA_REPO_TOKEN`: a fine-grained
personal access token with *Contents: read* on `spexod/data` and nothing else. Then run the workflow
once from the Actions tab (*Run workflow*): it publishes `ghcr.io/spexod/backend:LATEST` only from
`main` and only on the schedule or that manual run, never from a plain push.
