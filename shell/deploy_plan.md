# Deployment plan: the security review branch (`claude`, 2026-10-31)

The order matters: the server's `.env` has to be completed **before** `shell/update.sh` runs, because
the new compose file and settings fail closed instead of starting with insecure defaults.

## Checklist (status 2026-11-01, night: deployed)

Done:
- [x] `data.sh` against the production database (after the token-blacklist clean-up); Django migrations applied
- [x] database dump on the server (`mysql/dump-<time>.sql.gz`)
- [x] GitHub secret `DATA_REPO_TOKEN` set; `security.yml` and `audit.yml` pass (the five Trivy findings in pip's
      bundled libraries are accepted in `.trivyignore` until 2027-02-01)
- [x] code review of both repositories; review commits: Trivy ignore file, dead-code removal, deploy plan (Portal),
      Next.js 16.4.3 and fast-uri 3.1.9 in the lock file (SpExo-FrontEnd, fixes the critical `npm audit` findings)
- [x] both repositories merged into `main` and pushed; CI green on `main`; `deploy.sh` run after the last commits
- [x] server `.env` completed; `update.sh` run from an interactive session on the server (`ssh spexo`), after
      `deploy_update.sh` had died on `clear` (fixed on `claude`, see "Deployment workflow problems")
- [x] **the site is live on the new images**: `tests/smoke.py --strict` from outside gives 41 passed, 0 failed,
      0 warnings; the pages carry the security headers; the contact page shows the "not configured" message of
      the new frontend build

Remaining:
1. [ ] By hand on the site: login, spectrum download, logout (section 5); then the prune on the server
       (`docker image prune --force`, images only) and on the laptop
2. [ ] systemd units and timer, `ghcr-login.sh`, one manual `workflow_dispatch` of `security.yml` (section 6)
3. [ ] Fast-forward the commits on `claude` made after the merge into `main` (scripts, compose, docs, the
       frontend rendering change) and push; they reach the server with the next `update.sh` (the frontend
       change needs a new frontend image: `deploy.sh`, or the planned CI build)

Note on the repeated `data.sh`: it stages the processed data in the `new_*` schemas but does not mark it
committed; `deploy.sh` does that (`science.db.commit_data`). The backend's entrypoint only moves staged data
live when it is committed, so a `data.sh` run that is not followed by `deploy.sh` leaves the new staging in
place, unused, until the next `deploy.sh`. Harmless, but the output directory on the development computer is
emptied again (see section 3).

## Deployment workflow problems found during this deployment (fix before the next one)

0. **`update.sh` died on `clear`** (found on the first real run, fixed on `claude`): with `set -euo pipefail`
   and no terminal over ssh, `clear` fails on the missing `TERM` variable and ends the script before the
   pull; `deploy_update.sh` then went on to its prune prompt as if the update had run. The server was untouched.
   Fixed together with items 1 to 3: no `clear`, the pull in a separate ssh step, `ssh -t`, the ssh exit status
   checked, and the prune prompt only when a terminal exists.
1. **`update.sh` updates itself mid-run.** It pulls `main` and bash keeps executing the copy it already opened,
   so a change to `update.sh` only takes effect on the run after the one that pulls it. `deploy_update.sh`
   should pull in a separate ssh step first (`ssh ... "cd Portal && git pull origin main"`), then run the script;
   or `update.sh` should `exec` itself after the pull.
2. **`deploy_update.sh` ignores failures.** After the ssh step it goes straight to its own prune prompt, whether
   the server update succeeded, failed or was interrupted with Ctrl-C. It needs `set -e` or `|| exit` on the
   ssh command, so a failed server update stops the script and nothing on the laptop is pruned.
3. **The prompts in `update.sh` do not work over ssh.** `deploy_update.sh` calls ssh without `-t`, so the
   `read` prompts in `update.sh` get no terminal: `read` returns an error at end of input and `set -e` ends
   the script before the prune, and "press any-key to exit" never waits. Either call `ssh -t`, or better make
   `update.sh` non-interactive with a `--prune` flag that `deploy_update.sh` passes once the site is checked.
4. **`update.sh` logs in to ghcr.io from `.git_token.txt`.** `shell/ghcr-login.sh` is the documented way;
   `update.sh` should use it (or skip the login when the registry session is still valid) so there is one place
   that holds the token.
5. **`data.sh` and `deploy.sh` are coupled by the staged-data commit** (note above) and nothing records which
   `data.sh` run the committed staging came from. `data.sh` could print the staging schemas it wrote and
   `deploy.sh` could show what it is about to commit.
6. **The first run of a changed workflow is always the risky one.** `shell/local-test.sh` exercises the data and
   display steps against a local database, but there is no equivalent for `update.sh`; a dry-run mode
   (`update.sh --check`: pull, `docker compose config`, image pull, no `down`) would catch a missing `.env`
   value before the site goes down.

## Next round of work (not part of this deployment)

- **Contact form.** The live site ships the placeholder `YOUR_PUBLIC_KEY`, so the EmailJS form has failed since
  the 2026-05-31 commit that split the contact page; the new build shows "not configured, email
  info.spexodisks@gmail.com" instead. The key is in the git history of SpExo-FrontEnd (the contact page called
  `emailjs.sendForm('gmail', 'spexodisks', e.target, 'user_B1HRM3yK7kbsgFQ2zgKON')` from 2022 to May 2026;
  EmailJS renamed the User ID to Public Key and old values still work). Put it in `.env.deploy` as
  `NEXT_PUBLIC_EMAILJS_PUBLIC_KEY=user_B1HRM3yK7kbsgFQ2zgKON`, rebuild the frontend, and test with a real
  submission from the site. If it fails, the EmailJS account (probably the one for info.spexodisks@gmail.com)
  has rotated the key or lapsed: the owner finds the current key under Account > API Keys.
- **pip in the runtime image.** Drop the unused venv/virtualenv steps in `backend/Dockerfile` (every package
  installs into the system site-packages anyway) and `pip uninstall pip` at the end, which removes the bundled
  urllib3/msgpack/setuptools copies that `.trivyignore` accepts. Then delete the `.trivyignore` entries.
- **Pipeline split** (branch `pipeline-split`, `shell/pipeline_split_plan.md`): separate API and pipeline
  images, drop the dead dependencies.
- **Build the production images on GitHub, not on a developer computer.** Two steps:
  1. *Backend.* `security.yml` already builds, scans and publishes `ghcr.io/spexod/backend` from `main` on the
     weekly schedule and by hand. Publish on every push to `main` as well (keep the two-job separation: the
     third-party actions never run with a token that can write to the registry). The server's nightly timer,
     or `systemctl start spexodisks-auto-deploy.service` for an immediate update, becomes the deployment path;
     `deploy.sh` then only builds the backend for the frontend build (until step 2) and does the data steps.
  2. *Frontend.* Done on 2026-11-01: the pages are rendered on request (`dynamic = 'force-dynamic'` in
     `app/layout.js`), the tables come from the fetch data cache (120 s), and the build fetches nothing, so the
     image builds with no API, no database and no secrets; `deploy.sh`, `display.sh` and `compose.yaml` no
     longer start a local API or use host networking for it. Remaining: an `image` job in SpExo-FrontEnd's
     workflow that builds the image from `main`, scans it and publishes `ghcr.io/spexod/frontend`. Gain: both
     images reproducible from a commit, built for amd64 on a runner (the `DOCKER_PLATFORM` trap in section 1
     disappears), tagged with the commit SHA, independent of a laptop's state.
  After both steps, what remains on the development computer is data work: `data.sh`, the rsync of the
  download files and the staged-data commit, which the pipeline split separates from the API anyway.
- **Visual checks of the frontend.** Add headless Chromium (Playwright) to the test tooling so the pages can be
  screenshotted and compared: the smoke test only checks that pages answer and contain expected text, not how
  they look. Start with screenshots of every page at phone and desktop widths after a build (`local-test.sh
  --frontend`), then a comparison against the previous run to flag layout changes. Other frontend tooling may
  follow (an accessibility checker, see below; a bundle-size check). First findings from headless screenshots
  of the local site on 2026-11-01 (Playwright, Chromium 156, 1280 px and 390 px wide):
  - Explore page, desktop: the "Select spectra by hovering..." heading is drawn over the plot area, the
    "No Spectra Staged for Download" notice covers the navigation bar, and the staged-download icon covers
    the plot's flux axis.
  - Explore page, phone: the table columns are cut to two or three characters ("BD", "CRIR"), the four
    buttons above the table wrap into narrow pills, and the "Add Columns" control is a vertical strip of
    letters at the right edge; the page is not usable at this width.
  - Home page, phone: the instrument carousel's numbers and names overlap each other, and the text in the
    HITRAN box breaks into "importedHITRAN from".
  - Home page, desktop: no problems seen.
- **Faster data updates: process only what changed.** Today `DATA_NEW_UPLOADS_ONLY=true` only skips the *upload*
  of spectra whose handle is already in the `spectra` table: `update.py` still reads every FITS file, rebuilds
  every object's parameters (SIMBAD, Gaia, TIC lookups against the reference files) and all tables in the
  `new_*` schemas, about ten minutes, and a changed file that keeps its handle is never re-uploaded. Keep a
  manifest of MD5 sums (or sizes and mtimes as a fast pre-check) of `data/spectral_data` and the reference
  files, stored with the data repository or in a table, and have `update.py` process only the files whose sum
  changed or that are new, re-upload a spectrum when its file changed, and leave the rest untouched. The same
  sums can tell `deploy.sh` which output files the rsync will move before it starts.
- **The GitHub feed must be handled autonomously.** Since the security deployment GitHub produces a stream of
  things to act on: Dependabot pull requests (actions, pip, npm; five were opened within an hour of the first
  run), the weekly `security.yml` and `audit.yml` runs, failed jobs with their logs, Dependabot security alerts,
  and the manual re-runs after a fix. Reading all of that in the browser and relaying it by hand does not scale.
  Steps:
  1. *Read access from the sandbox* (done 2026-11-01 for reading, `shell/github-status.sh`): the script saves
     runs, the logs of failed jobs, open and recently closed pull requests and open security alerts for both
     repositories into `logs/github/` (gitignored). It runs on the development computer with `gh` logged in;
     in the sandbox it needs the GitHub token as a sandbox secret (`sbx secret set github --sandbox spexo
     -t "$(gh auth token)"` on the host, see CLAUDE.md), after which the assistant can run it, and `gh`, itself.
  2. *Routine, run by the assistant from the sandbox*: after each push and once a week, read the status; for a
     failed run read the log and propose or commit the fix; for a Dependabot PR check the run, read the release
     notes of a major-version bump, and merge it when green (actions and dev dependencies) or stage it for the
     next deployment (runtime dependencies, which need `deploy.sh`); keep `.trivyignore` and the review dates
     current; write a short note of what was done into the plan.
  3. *Scheduled*: the same routine as a scheduled cloud agent or a timer, so the weekly runs are followed up
     without anyone opening GitHub; a failed run or a critical alert becomes a message, everything else a
     weekly summary.
- **Accessibility.** Keyboard navigation and screen-reader support: a visible focus order through the explore
  page (drawer, tables, plot controls), labels and roles on the custom dropdowns and buttons, `alt` text on the
  images, skip links, and colour contrast in `spexostrap/Colors.css`. Measure with an automated checker in the
  test tooling (axe through Playwright, see above) and fix the findings page by page; then a manual pass with a
  screen reader on the explore page, which is the hardest one.

## What is being deployed

Portal, 25 commits (`git log main..claude`):

| Area | Change | Visible effect |
|---|---|---|
| nginx | TLS 1.2/1.3 only, security headers (HSTS 1 year, nosniff, frame, referrer, permissions), server version hidden, requests for other host names dropped (444), real client address forwarded | headers on every response; the IP address no longer serves the site |
| Django | `DJANGO_SECRET_KEY` required when `DEBUG=false`; refresh tokens rotate and can be revoked (logout, password change, password reset); 10 requests/minute per address on login, register, logout, reset (60/minute on refresh); password rules on password change; reset request never reveals whether an email exists; `/api/datadownload/` needs a login; unknown `/api/...` paths are 404 | sessions keep working; a logout now ends the session on the server; brute force is slowed down |
| compose | `MYSQL_PASSWORD` required; `no-new-privileges`; nginx config read-only; `DEBUG` and `API_USE_NEW_TABLES` default to false; MySQL port bindable to one address; frontend healthcheck fixed (`HOSTNAME=0.0.0.0`) | compose refuses to start without the password |
| data pipeline | parameterised SQL, atomic table swap, schema init / Django migrations / staged-data migration at container start (not at image build), `update_mode` keeps the output directory | the first backend start applies two new Django migrations (token blacklist tables) |
| autostar | moved into `backend/autostar`; SIMBAD lookups work with current astroquery; `SIMBAD_SERVER` selects the CDS site or the Harvard mirror | only the development computer runs it |
| operations | `shell/auto-deploy.sh` nightly update with rollback, database dump and alerts; `security.yml` audits and publishes the backend image; `shell/update.sh` waits for health and runs the smoke test | see "After the deployment" |
| tests | `tests/smoke.py`, `tests/auth_flow.py`, `shell/local-test.sh`, `backend/tests` | |

SpExo-FrontEnd, 7 commits (the last one updates the lock file to Next.js 16.4.3): Dependabot and npm audit, forms never submit natively, token refresh shared
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
4. `SpExo-FrontEnd/.env.deploy`: `NEXT_PUBLIC_EMAILJS_PUBLIC_KEY=` stays empty for this deployment (the
   contact page says the form is not configured and gives the email address); see "Next round of work".
5. Optional but recommended, 15 minutes: `./shell/local-test.sh --frontend` against a local database
   (needs a second `.env` with `MYSQL_HOST="mysqlDB"`, see `.env.example`).
6. Push both repositories. Pushing Portal `main` runs `security.yml` (pip-audit, image build, Trivy);
   the `DATA_REPO_TOKEN` secret is set and the run on the pull request passed.

## 2. On the server: complete `.env` first

`ssh spexo` (the `Host spexo` entry from README.md), then edit `/home/ubuntu/Portal/.env`:

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
image, builds the frontend with `.env.deploy` (no API needed since the pages render on request), pushes
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
ssh spexo
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
