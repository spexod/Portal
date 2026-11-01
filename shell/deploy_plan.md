# Deployment plan: the security review branch (`claude`, 2026-10-31)

The order matters: the server's `.env` has to be completed **before** `shell/update.sh` runs, because
the new compose file and settings fail closed instead of starting with insecure defaults.

## Checklist (status 2026-11-02)

Done:
- [x] `data.sh` against the production database (after the token-blacklist clean-up); Django migrations applied
- [x] `deploy.sh`: backend and frontend images pushed to ghcr.io as `LATEST`, staged data marked committed
- [x] database dump on the server (`mysql/dump-<time>.sql.gz`)
- [x] pull request `claude` → `main` opened; `security.yml` ran: `audit` passed, `image` failed on the missing secret

Remaining, in order:
1. [ ] GitHub secret `DATA_REPO_TOKEN` (section 6), then "Re-run failed jobs" on the pull request run
2. [ ] Code review of the pull request. **If any commit is added**, run `./deploy.sh` again before the server
       update so the `LATEST` images match `main` (`data.sh` is not needed again)
3. [ ] Merge both repositories into `main` and push (section 1; also SpExo-FrontEnd `claude` → `main`)
4. [ ] Server `.env` completed and `docker compose config --quiet` passes (section 2)
5. [ ] `./deploy_update.sh`; do not confirm the prune prompt yet (section 4)
6. [ ] `python3 tests/smoke.py --strict`, login, spectrum download, logout (section 5); then confirm the prune
7. [ ] systemd units and timer, `ghcr-login.sh`, one manual `workflow_dispatch` of `security.yml` (section 6)

Until step 5 nothing on the server changes: the server only pulls new images when `update.sh` runs, and the
nightly timer is not installed yet. One side effect of step "deploy.sh" is already in place: the staged data is
committed, so if the current (old) backend container restarts before the update, its entrypoint moves that
data live. That is harmless, the data is meant to go live.

## What is being deployed

Portal, 15 commits (`git log main..claude`):

| Area | Change | Visible effect |
|---|---|---|
| nginx | TLS 1.2/1.3 only, security headers (HSTS 1 year, nosniff, frame, referrer, permissions), server version hidden, requests for other host names dropped (444), real client address forwarded | headers on every response; the IP address no longer serves the site |
| Django | `DJANGO_SECRET_KEY` required when `DEBUG=false`; refresh tokens rotate and can be revoked (logout, password change, password reset); 10 requests/minute per address on login, register, logout, reset (60/minute on refresh); password rules on password change; reset request never reveals whether an email exists; `/api/datadownload/` needs a login; unknown `/api/...` paths are 404 | sessions keep working; a logout now ends the session on the server; brute force is slowed down |
| compose | `MYSQL_PASSWORD` required; `no-new-privileges`; nginx config read-only; `DEBUG` and `API_USE_NEW_TABLES` default to false; MySQL port bindable to one address; frontend healthcheck fixed (`HOSTNAME=0.0.0.0`) | compose refuses to start without the password |
| data pipeline | parameterised SQL, atomic table swap, schema init / Django migrations / staged-data migration at container start (not at image build), `update_mode` keeps the output directory | the first backend start applies two new Django migrations (token blacklist tables) |
| autostar | moved into `backend/autostar`; SIMBAD lookups work with current astroquery; `SIMBAD_SERVER` selects the CDS site or the Harvard mirror | only the development computer runs it |
| operations | `shell/auto-deploy.sh` nightly update with rollback, database dump and alerts; `security.yml` audits and publishes the backend image; `shell/update.sh` waits for health and runs the smoke test | see "After the deployment" |
| tests | `tests/smoke.py`, `tests/auth_flow.py`, `shell/local-test.sh`, `backend/tests` | |

SpExo-FrontEnd, 6 commits: Dependabot and npm audit, forms never submit natively, token refresh shared
across tabs with server-side logout, last good data kept when a revalidation fails, labels rendered
without raw HTML, external links checked, contact form key from `NEXT_PUBLIC_EMAILJS_PUBLIC_KEY`.

## 1. On the development computer, before merging

1. `backend/.gitignore` used to ignore `autostar`. If a `backend/autostar` directory exists in your
   checkout (an old clone of the package), move it away first or the merge refuses to overwrite it:
   `mv backend/autostar ~/autostar-old`.
2. Merge, both repositories fast-forward:
   ```
   cd Portal && git checkout main && git merge --ff-only claude
   cd SpExo-FrontEnd && git checkout main && git merge --ff-only claude && cd ..
   ```
3. Check your `.env` (this computer builds the images that go to the server):
   - **no** `DOCKER_PLATFORM`, or `DOCKER_PLATFORM=linux/amd64`: the server is amd64. An image built
     for arm64 would be pushed as `LATEST` and the server could not run it.
   - `SIMBAD_SERVER=simbad.harvard.edu` while CDS Strasbourg is offline (only matters for `data.sh`).
   - `MYSQL_HOST="spexodisks.com"` and the production password as before.
4. `SpExo-FrontEnd/.env.deploy`: `NEXT_PUBLIC_EMAILJS_PUBLIC_KEY=` is empty. The form on `main` used the
   placeholder `YOUR_PUBLIC_KEY`, so it did not work before either; fill in the real EmailJS public key
   now if you have it, otherwise the contact page shows a message that the form is not configured.
5. Optional but recommended, 15 minutes: `./shell/local-test.sh --frontend` against a local database
   (needs a second `.env` with `MYSQL_HOST="mysqlDB"`, see `.env.example`).
6. Push both repositories. Pushing Portal `main` runs `security.yml` (pip-audit, image build, Trivy).
   The image job needs the `DATA_REPO_TOKEN` secret (section 6); until it is set that job fails, which
   has no effect on the site.

## 2. On the server: complete `.env` first

`ssh -i spexo-ssh-key.pem ubuntu@spexodisks.com`, then edit `/home/ubuntu/Portal/.env`:

| Variable | Required value | Why |
|---|---|---|
| `DJANGO_SECRET_KEY` | a new 50+ character secret: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` | **new, required**: with `DEBUG=false` the backend refuses to start on the built-in key. Changing the key logs every user out once (their tokens were signed with the old key) |
| `MYSQL_PASSWORD` | the existing password | compose fails without it (`${MYSQL_PASSWORD:?}`) |
| `DEBUG` | `false` | |
| `DATA_MIGRATE_FROM_STAGED` | `true` | staged data goes live at the backend start; already set on the server |
| `API_USE_NEW_TABLES` | `false` (or absent) | the default changed to false, production reads the live tables |
| `NGINX_CONFIG_FILE` | `deploy.conf` | as before |
| `MYSQL_CONFIG_FILE` | `deploy.cnf` | as before |
| `COMPOSE_PROFILES` | as before (`db,web,api`) | |
| `MYSQL_BIND_ADDRESS` | optional: the server's address if MySQL should not listen on every interface | the upload computer connects to port 3306 over TLS |
| `ALERT_WEBHOOK_URL` | optional, e.g. `https://ntfy.sh/<topic>` | failure alerts from the nightly update |
| `DOCKER_PLATFORM`, `SIMBAD_SERVER`, `JUPYTER_TOKEN` | leave unset | |

Then, still on the server, check that compose accepts the file **with the current (old) checkout**, which
already tolerates the new variables:
```
cd /home/ubuntu/Portal && docker compose config --quiet && echo ok
```
and take a database dump that the rollback can use:
```
sudo ./mysql/upgrade.sh dump        # writes mysql/dump-<time>.sql.gz
```

### Clean up after the failed `data.sh` run of 2026-10-31

The first `data.sh` with the new image stopped in the Django migrations with MySQL error 3780: the
token-blacklist table's `user_id` was created as `bigint` while the production user table has a
32-bit `id`. The model now declares that id type explicitly, but the failed migration left its two
tables behind on the production server, and the next migration run would stop at "table already
exists". In the MySQL client (on the server: `docker compose exec mysqlDB mysql -uroot -p`):
```sql
SHOW CREATE TABLE users.djangoAPI_useraccount\G          -- expect:  `id` int NOT NULL AUTO_INCREMENT
SHOW TABLES FROM users LIKE 'token_blacklist%';          -- the two orphan tables
DROP TABLE IF EXISTS users.token_blacklist_blacklistedtoken, users.token_blacklist_outstandingtoken;
SELECT app, name FROM users.django_migrations WHERE app = 'token_blacklist';   -- expect no rows
```
If the first statement shows `bigint` instead of `int`, stop and say so before deploying: the model
change would then be wrong.

## 3. Build and publish the images (development computer)

`./deploy.sh` as before. It rsyncs `backend/output` and `backend/data` to the server, builds the backend
image, starts the local API for the frontend build, builds the frontend with `.env.deploy`, pushes
both images to ghcr.io and marks staged data committed (prints "No staged data to commit" when
`data.sh` was not run, which is fine for this deployment).

**Downloads on the local test website are empty.** The test website that `display.sh` or `deploy.sh`
starts serves the zip downloads from `backend/output` on this computer. `data.sh` empties that directory
first (`rm -rf ./backend/output/*`) and, in update mode (`DATA_NEW_UPLOADS_ONLY=true`), `update.py`
only writes files for spectra that are new to the database. So a zip from the local test website holds only
`fits_read.py` and `FITSREAD.md`. This is not a fault of the build: the server keeps the complete set
(1197 spectra, `.fits` and `.txt`) in `/home/ubuntu/Portal/backend/output`, the rsync in `deploy.sh`
only adds to it, and the production download is checked in section 5. To have the files locally again:
`rsync -avz -e "ssh -i spexo-ssh-key.pem" ubuntu@spexodisks.com:/home/ubuntu/Portal/backend/output/ ./backend/output/`
(about 1.3 GB). That server directory is the only complete copy of the download files (the repository
ignores `output`), so include it in the server backups.

## 4. Update the server

`./deploy_update.sh` runs `shell/update.sh` on the server over ssh. Note: the script pulls `main`
first and bash keeps executing the **old** copy it opened, so this first run does not yet wait for
the healthchecks or run the smoke test. Watch it by hand:

```
ssh -i spexo-ssh-key.pem ubuntu@spexodisks.com
cd /home/ubuntu/Portal
docker compose ps                       # backend "healthy" takes up to a minute: schema init, Django migrations
docker compose logs backend | grep -E "docker-entrypoint|Applying|migrating|Tables updated|ERROR|Traceback"
```
Expected lines: `docker-entrypoint: creating MySQL schemas...`, `Applying token_blacklist.0001...` to
`0013`, `No staged and committed data to migrate.`, then gunicorn starting. **Do not confirm the prune
prompt** until section 5 passes; the old images are what a rollback needs.

## 5. Verify

From the laptop:
```
python3 tests/smoke.py --strict                       # expect 0 failed, 0 warnings (41 checks on production)
```
The baseline before this branch was 40 to 41 checks with 8 to 9 warnings. Then log in on the site with
your own account, open a spectrum, download it, log out and confirm the page returns to the logged-out
state. The account test `tests/auth_flow.py` creates a user, so run it against production only if
you delete that user afterwards (Django admin or `users` schema).

Confirm the prune prompt in `update.sh` once everything passes.

## 6. After the deployment: switch on the automatic updates

On the server, once:
```
sudo install -m 644 shell/systemd/spexodisks-* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now spexodisks-auto-deploy.timer
./shell/ghcr-login.sh                                  # the timer pulls from ghcr.io
sudo systemctl start spexodisks-auto-deploy.service && journalctl -u spexodisks-auto-deploy -n 30
```
The first manual run should end with `no new images, nothing to do`.

On GitHub, once: add the Actions secret `DATA_REPO_TOKEN` (fine-grained token, *Contents: read* on
`spexod/data` only) in the Portal repository settings, then run `security.yml` from the Actions tab.
It publishes `ghcr.io/spexod/backend:LATEST` and `sha-<commit>` from `main`; the nightly timer picks
new images up at 04:00 and rolls back when the smoke test fails. Details: `shell/auto_update.md`.

## 7. Rollback

- **Containers**: while the old images are still on the server (before the prune),
  `docker images ghcr.io/spexod/backend` lists them; `docker tag <old image id> ghcr.io/spexod/backend:LATEST`
  (same for the frontend), `docker compose down && docker compose up --detach`. After a prune, check out
  the previous `main` commit and run `./deploy.sh` and `./deploy_update.sh` again.
- **Database**: the new Django migrations only add the token-blacklist tables, which the old image
  ignores, so a container rollback needs no database change. If anything else went wrong:
  `./mysql/upgrade.sh restore mysql/dump-<time>.sql.gz` with the dump from section 2.
- **`.env`**: the old checkout runs with the new variables present, nothing to undo.

## Known behaviour changes to expect

- Every user is logged out once (new secret key); logins work normally afterwards.
- Login, register, logout and password-reset requests are limited to 10 per minute per address;
  token refresh has its own limit of 60 per minute per address.
- Spectrum downloads require a login (the frontend already asked for one).
- `https://<server IP>/` and unknown host names get no response instead of the site.
- Browsers remember HSTS for a year: the site is https-only from the first visit on.
