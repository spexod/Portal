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
| Python dependencies and the backend base image | `.github/dependabot.yml` opens PRs; `.github/workflows/security.yml` audits them (pip-audit, Trivy) and rebuilds and publishes `ghcr.io/spexod/backend:LATEST` | PRs weekly, rebuild Mondays |
| nginx and MySQL images | `docker compose pull` (nginx follows `stable`, MySQL stays on its pinned major version) | nightly |
| Running containers | `shell/auto-deploy.sh` through the `spexodisks-auto-deploy` timer: pulls, recreates changed containers, rolls the backend back if it is not healthy | nightly at 04:00 |

The frontend image is not rebuilt in GitHub Actions, because its build needs the live API (see `deploy.sh`).
It still needs `./deploy.sh` after dependency updates. Copy `.github/dependabot.yml` to the SpExo-FrontEnd
repository (ecosystems `npm` and `docker`) so it gets update PRs too.

## One-time setup on the server

```
sudo install -m 644 shell/systemd/spexodisks-auto-deploy.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now spexodisks-auto-deploy.timer
```

Test it once by hand: `sudo systemctl start spexodisks-auto-deploy.service`, then `journalctl -u spexodisks-auto-deploy`.
The server needs to be logged in to ghcr.io (`shell/ghcr-login.sh`) for private images.
