# Deployment 2 (2026-11-02): the next round, `claude-wp9-alignment` of both repositories

What goes live: everything on `claude-wp9-alignment` that `main` does not have yet (Portal 28 commits,
SpExo-FrontEnd 24): the version policy and tooling (WP1), the CI image builds (WP2), the Dependabot setup
(WP4), the visual rounds (WP5) and the second security pass (WP9: email confirmation for new accounts,
registration without enumeration, the streamed download zip, `MYSQL_BIND_ADDRESS` defaulting to the loopback,
HSTS with `includeSubDomains`). Both branches fast-forward onto `main`; the merge to `main` builds and
publishes both images (`security.yml`, `audit.yml`); the server takes them with `shell/auto-deploy.sh`,
started by hand here so that somebody watches, otherwise at 04:00 UTC.

**Prerequisites, confirmed 2026-11-02:** the server's `.env` has `MYSQL_BIND_ADDRESS=0.0.0.0` (the compose
default is now `127.0.0.1`, without it the upload computers would lose port 3306) and a working
`DJANGO_EMAIL_USER`/`DJANGO_EMAIL_APP_PASSWORD` (new accounts confirm their address by mail).

## Checklist

1. [ ] Development computer: `main` fast-forwarded in both repositories and pushed (section A)
2. [ ] CI green on both `main`s, `publish` included (section B); the frontend package may need "Manage
       Actions access" for the SpExo-FrontEnd repository on its first publish
3. [ ] Server: `update.sh --check` clean, `git pull`, `.env` values present (section C)
4. [ ] Server: `spexodisks-auto-deploy.service` run and completed, nginx reloaded (section D)
5. [ ] Verified from outside: `smoke.py --strict`, the headers, one registration confirmed by mail (section E)
6. [ ] Sandbox back on the `claude` branch for the next work package

## A. Development computer (the ssh key for GitHub lives here, so the push happens here)

```
cd ~/sandboxes/Portal
git status --short | grep -v '^??'            # must print nothing (the sandbox commits everything)
git checkout claude && git merge --ff-only claude-wp9-alignment
git checkout main   && git merge --ff-only claude
git push origin main
cd SpExo-FrontEnd
git checkout claude && git merge --ff-only claude-wp9-alignment
git checkout main   && git merge --ff-only claude
git push origin main
cd ..
```

`--ff-only` refuses if anything diverged; nothing should, `main` is an ancestor of `claude` in both.

## B. Watch the builds (about 15 minutes; the backend image is built without cache)

```
gh run list --repo spexod/Portal --limit 3
gh run list --repo spexod/SpExo-FrontEnd --limit 3
gh run watch --repo spexod/Portal              # pick the newest run, waits until it ends
gh run watch --repo spexod/SpExo-FrontEnd
```

Both runs must end with the `publish` job green. If the frontend's `publish` fails with
`permission_denied: write_package`: GitHub → organization spexod → Packages → `frontend` → Package settings →
Manage Actions access → add the SpExo-FrontEnd repository with *Write*, then `gh run rerun <run-id> --failed`.

## C. Server: check before touching anything

```
ssh spexo
cd ~/Portal
git rev-parse --short HEAD                     # the commit to go back to, note it
./shell/update.sh --check                      # lists the commits, validates main's compose with this .env
grep -E '^(MYSQL_BIND_ADDRESS|DJANGO_EMAIL_USER|PUBLIC_SITE_URL|REQUIRE_EMAIL_VERIFICATION)=' .env
git pull origin main
docker compose config --quiet && echo "compose + .env: ok"
```

`MYSQL_BIND_ADDRESS=0.0.0.0` and `DJANGO_EMAIL_USER=...` must be in the grep; `PUBLIC_SITE_URL` and
`REQUIRE_EMAIL_VERIFICATION` may be absent (defaults: `https://spexodisks.com`, on when a mail user is set).

## D. Server: update (after B is green)

```
sudo systemctl start spexodisks-auto-deploy.service
journalctl -u spexodisks-auto-deploy --since "10 min ago" --follow     # Ctrl-C when "update completed" shows
docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload   # the new deploy.conf (HSTS)
docker compose ps
```

The service dumps the database first (a few minutes), recreates `backend` and `frontend` with the new images
and the new compose settings, runs the smoke test against `https://spexodisks.com` and rolls back by itself
if that fails. It does not touch `mysqlDB` and does not reload nginx, hence the reload line. `docker compose
ps` must show `mysqlDB` with `0.0.0.0:3306->3306/tcp`.

## E. Verify from outside

```
cd ~/sandboxes/Portal
python3 tests/smoke.py --strict
curl -sI https://spexodisks.com/ | grep -iE 'strict-transport|x-frame'
```

By hand, with an address you own: Register → the mail "Confirm your email address for SpExoDisks" → the
link opens `/VerifyEmail?token=...` → Confirm → Login → a download. Register once more with the same
address: the same on-screen answer, and the mail "Your SpExoDisks account" instead of a second account.

## F. Rollback (only if D's own rollback did not restore the site)

```
ssh spexo
cd ~/Portal
docker tag ghcr.io/spexod/backend:previous  ghcr.io/spexod/backend:LATEST
docker tag ghcr.io/spexod/frontend:previous ghcr.io/spexod/frontend:LATEST
git checkout <the commit noted in C>
docker compose up --detach --force-recreate backend frontend nginx
python3 tests/smoke.py --base-url https://spexodisks.com
```

The database dump from before the update is `mysql/dump-<version>-<time>.sql.gz` (restore with
`./mysql/upgrade.sh restore <file>`); this update adds no migration, so the dump should not be needed.

# Deployment plan: the security review branch (`claude`, 2026-10-31)

The order matters: the server's `.env` has to be completed **before** `shell/update.sh` runs, because
the new compose file and settings fail closed instead of starting with insecure defaults.

## Checklist (status 2026-11-01, night: deployed, automatic updates on)

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

- [x] login, spectrum download, logout by hand; prunes on the server and the laptop
- [x] systemd units installed, `spexodisks-auto-deploy.timer` enabled (04:00 UTC, the certbot timer and the
      certificate watcher were already active); `auto-deploy.sh` needed its execute bit (fixed)
- [x] manual `workflow_dispatch` of `security.yml`: `publish` failed with `permission_denied: write_package`
      until the backend package granted the Portal repository *Write* access (documented in auto_update.md);
      the rerun published the CI-built `LATEST` and `sha-c6b90d0...`
- [x] first automatic update (`systemctl start spexodisks-auto-deploy.service`, 18:06 UTC): dump taken (582M,
      3.5 min), then the script failed on the static-files volume and left backend and nginx stopped, about two
      minutes of downtime until `docker compose up --detach backend nginx`; the backend came up on the CI image;
      `smoke.py --strict` 41/41 afterwards. The script is fixed (see "Deployment workflow problems", item 00)
- [x] `claude` merged into `main` in both repositories (Portal: merge commit a138488; SpExo-FrontEnd fast-forward)

Remaining:
1. [ ] Push Portal `main` (the fixed `auto-deploy.sh`, `github-status.sh`) and `git pull origin main` on the
       server, so the nightly timer runs the fixed script
2. [ ] Push SpExo-FrontEnd `main`; the dynamic-rendering change reaches the site with the next frontend image
       (`deploy.sh`, or the planned CI build)
3. [ ] Dependabot PR #4, `spexod` 0.1.1 to 0.3.0 in `backend/requirements.txt`: a runtime dependency, check the
       release notes and the image build on the PR, then merge; the nightly update ships it after the next
       `publish` (weekly schedule, or by hand)

Note on the repeated `data.sh`: it stages the processed data in the `new_*` schemas but does not mark it
committed; `deploy.sh` does that (`science.db.commit_data`). The backend's entrypoint only moves staged data
live when it is committed, so a `data.sh` run that is not followed by `deploy.sh` leaves the new staging in
place, unused, until the next `deploy.sh`. Harmless, but the output directory on the development computer is
emptied again (see section 3).

## Deployment workflow problems found during this deployment (fix before the next one)

00. **`auto-deploy.sh` took the site down on its first real update** (2026-11-01 18:10 UTC, fixed on `main`
   right after): it stops backend and nginx and then removes the Django static-files volume, but Docker refuses
   to remove a volume that a stopped container still references, and with `set -e` the script ended between
   the stop and the start. The containers stayed stopped until `docker compose up --detach backend nginx` by
   hand. Fix: the two containers are removed before the volume (`docker compose rm --force --stop`), a failure
   there restarts the containers, and from the recreate step on `set -e` is off so the rollback path is always
   reached. The sandbox tests never exercised a backend update through this script: `local-test.sh` should
   get a mode that runs `auto-deploy.sh` against the local stack with a changed image.
000. **`auto-deploy.sh` rolled back to an image that no longer existed** (found by `local-test.sh --auto-deploy`
   on 2026-11-01, fixed on `claude-wp1-tooling`): it remembered the running image by id, but an image that has
   lost its tag (the new image took it) and its container (removed for the volume reset) is garbage-collected
   by Docker's containerd image store, so the rollback found nothing. The running image now gets a `previous`
   tag before the update and the rollback uses that tag; `docker image prune` leaves tagged images alone.
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
  EmailJS renamed the User ID to Public Key and old values still work). Set the GitHub repository variable
  `NEXT_PUBLIC_EMAILJS_PUBLIC_KEY=user_B1HRM3yK7kbsgFQ2zgKON` in SpExo-FrontEnd (the CI build reads it; a local
  `deploy.sh` build reads the same name from Portal's `.env`), rebuild the frontend, and test with a real
  submission from the site. If it fails, the EmailJS account (probably the one for info.spexodisks@gmail.com)
  has rotated the key or lapsed: the owner finds the current key under Account > API Keys.
- **pip in the runtime image.** Drop the unused venv/virtualenv steps in `backend/Dockerfile` (every package
  installs into the system site-packages anyway) and `pip uninstall pip` at the end, which removes the bundled
  urllib3/msgpack/setuptools copies that `.trivyignore` accepts. Then delete the `.trivyignore` entries.
- **Pipeline split** (branch `pipeline-split`, `shell/pipeline_split_plan.md`): separate API and pipeline
  images, drop the dead dependencies.
- **Build the production images on GitHub, not on a developer computer.** Two steps:
  1. *Backend.* Done 2026-11-01 (branch `claude-wp2-ci-builds`): `security.yml` publishes on every push to
     `main` as well as on the schedule and by hand, with the same job separation; the nightly timer, or
     `systemctl start spexodisks-auto-deploy.service`, is the deployment path.
  2. *Frontend.* Done 2026-11-01: the pages render on request, the image's settings are build args
     (`NEXT_PUBLIC_*`, public) and the run-time environment (`API_BASE_SERVER`), and SpExo-FrontEnd's
     `audit.yml` builds the image with the newest packages within the ranges, scans it and publishes it from
     `main`. Remaining once: the frontend package on ghcr.io grants the SpExo-FrontEnd repository write access,
     and the first publish is watched.
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
  All of the above fixed on 2026-11-01 (SpExo-FrontEnd branch `claude-wp5-visual`), with more found and fixed
  along the way: the download cart moved from a floating corner icon into the header, the explore page
  became one scroll region, the forms, team, contact and tutorial pages were laid out for a phone.
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
- **Code review, full pass** over both code bases (backend science, API, autostar; frontend app, components,
  context; the shell scripts with shellcheck), with the ten TODO/FIXME markers resolved and unit tests for the
  pure functions found on the way. See `shell/next_round_plan.md`, WP8.
- **Security review, second pass**: the items the first review left open (MySQL root as the application user,
  unpaginated list endpoints, migrations regenerated at build), a Content-Security-Policy, the registry token
  on the server, a secrets inventory with rotation dates, Dependabot alerts. See `shell/next_round_plan.md`, WP9.
- **The detailed plan for all of the above**, with the rules for unattended work and the decisions needed at
  the check-in, is `shell/next_round_plan.md`.
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
4. The EmailJS key stays unset for this deployment (the contact page says the form is not configured and
   gives the email address); see "Next round of work".
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
| `MYSQL_BIND_ADDRESS` | `0.0.0.0` (**required on the server since WP9**: the default became `127.0.0.1`) | the upload computer connects to port 3306 over TLS; without it the nightly update recreates mysqlDB listening on the loopback only |
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
image, builds the frontend from compose's build args (no API needed since the pages render on request), pushes
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
