# Next round of work: plan for unattended sessions

Written 2026-11-01, after the security release went live and the automatic updates were switched on.
This is the working plan for the assistant: the user reads it, settles the decisions in section 2 at a
check-in, and the assistant then works through the packages in section 4 without supervision, under the
rules in section 1, keeping the status table in section 5 current. `shell/deploy_plan.md` keeps the history
of the security deployment and the short list this plan grew from.

## 1. Rules for unattended work

- **Branches.** One branch per work package, named `claude-<package>` (for example `claude-wp1-tooling`; git
  allows no `claude/...` branches beside the old `claude` branch),
  branched from `main`. Commits are small and described; nothing is pushed, merged or deployed by the
  assistant. The user merges after review, as before. A package that touches both repositories gets the same
  branch name in both.
- **Never touches production.** No ssh to the server, no `deploy.sh`, `deploy_update.sh`, `data.sh` against
  the production database, no registry push, no GitHub settings. Read-only use of the GitHub API and of
  `gh` (runs, logs, pull requests, alerts) is fine. The production site may be read with GET requests
  (`tests/smoke.py --strict`, screenshots).
- **Every change is verified before it is called done**, with the checks that fit it: `./shell/local-test.sh
  --no-update` (smoke and account flow against the local database) for backend changes,
  `./shell/local-test.sh --frontend --no-update` plus screenshots at 1280 and 390 px for frontend changes,
  `python3 -m unittest discover tests` in `backend/` for the pipeline, a Trivy scan of a rebuilt image when the
  Dockerfile changes, and an `auto-deploy.sh` dry run against the local stack once WP1 provides it. Results
  go into the commit message and the status table.
- **Stop and ask** (write the question into the status table and the final message, continue with another
  package) when: a change would alter the database schema of production, a dependency upgrade changes
  behaviour the tests do not cover, a credential or an account decision is needed, a package's scope turns
  out materially larger than planned, or two packages conflict.
- **Scope discipline.** Fix what the package says; note other findings in section 6 instead of fixing them
  in passing. Dead code found on the way is removed only if a test covers the area.
- **Record keeping.** Section 5 is updated at the end of every session: what was done, what was verified,
  what is open. Memory notes hold only what the next session needs to resume.

## 2. Decisions and inputs needed at the check-in

| # | Needed | Why | Default if not decided |
|---|---|---|---|
| D1 | **Decided 2026-11-01: a read-only fine-grained token** (Actions, Contents, Pull requests, Checks, Dependabot alerts: read; 7 days), handed over with `sbx secret set github --sandbox spexo -t ...`. No write permission on the repositories: the assistant never merges or re-runs jobs; it proposes, the user clicks | `gh` in the sandbox: logs of failed runs, the private frontend repository, Dependabot alerts (WP4) | until the token exists: the public API only |
| D2 | EmailJS: use the 2022 public key from the git history, or a new key from the account owner | WP6 contact form | put the old key in `.env.deploy`, test after the next frontend deploy, report |
| D3 | **Decided 2026-11-01: upgrade.** `requirements.txt` says `spexod>=0.3.0` (the unpinned build already installed 0.3.0; the smoke and download tests ran on it). Dependabot PR #4 closes itself after the push | WP1 pins and WP3 vendors the two files the API uses | |
| D4 | **Done 2026-11-01 (close-out task):** `mysql/users.sql` + `mysql/create-users.sh`, the `MYSQL_API_*` / `MYSQL_PIPELINE_*` variables in compose, settings and the entrypoint, tested on the local stack. The user runs `./mysql/create-users.sh` on the server and the upload computer and sets the four values in each `.env` (section 7 of this file) | the app connects as root today | |
| D5 | Off-site backup target for the database dumps and `backend/output` (WP10): an S3-compatible bucket, another machine over ssh, or none for now | the server holds the only copy of the download files | plan and script written for rsync-over-ssh to a host the user names; nothing scheduled |
| D6 | **Decided 2026-11-01: email.** `notify-failure.sh` sends an email through the Django mail account when `ALERT_EMAIL` is set in the server's `.env` (the webhook stays optional). The user sets `ALERT_EMAIL` and tests with `./shell/notify-failure.sh spexodisks-auto-deploy.service` | the failure unit already writes logs; alerts need a target | |
| D7 | Priority among the frontend packages: visual fixes (WP5) before accessibility (WP6), or together | both touch the same components | WP5 first, the accessibility pass on each page right after its visual fix |
| D8 | **Decided 2026-11-01: be honest with the visitors.** First check whether a cookieless setup is possible (GA4 consent mode without storage still sends data to Google, so the honest options are an opt-in banner that loads GA only after consent, or a self-hosted cookieless analytics such as Umami/Plausible in compose). Implement the opt-in banner in WP6 (keyboard-accessible), evaluate the self-hosted option in WP9 | privacy; also an accessibility item for the banner | opt-in banner |
| D9 | Order of the big ones: WP2 (CI builds) before WP3 (pipeline split) | WP3 changes the Dockerfile targets WP2 builds | WP2 first for the frontend (independent), the backend half of WP2 after WP3 |

## 3. Suggestions beyond the list (new findings from the survey)

- **Version policy (decided 2026-11-01, the HySite pattern).** Git holds only *what to follow*: the
  package lists with a major-version ceiling per package (`Django>=6,<7`, `numpy>=2,<3`, `next` with a caret
  range) and the image lines (`python:3.14-alpine`, `node:26-alpine`, `mysql:9.7`, `nginx:stable`). Exact
  versions are resolved at build time by a script like HySite's `scripts/refresh_versions.py` (a lock file
  compiled with `uv pip compile` inside the base image, the image tags with their digests in a
  `versions.env`), recorded in the image labels and in a deployments log, never edited by hand and not
  committed. The weekly CI build is the automated minor and patch update; the nightly `auto-deploy.sh` with
  its smoke test and rollback is the rollback test; a build or a deploy that fails keeps the previously
  tested versions. A new major line (Python 3.15, MySQL 10, Django 7, Next 17) is an administrator's
  decision: Dependabot keeps opening PRs for majors and for security advisories only (`ignore:
  version-update:semver-minor` and `semver-patch` for pip, npm and docker; GitHub Actions stay fully
  automatic). Today `requirements.txt` has no ceilings and `package.json` uses `>=` everywhere, so a build
  follows majors too. (WP1)
- **Django migrations are gitignored and regenerated at every image build.** A model change on two machines
  can generate two different migration files for the same change, and the token-blacklist incident
  (bigint vs int) was only caught on production. Commit the migrations, drop the `makemigrations` step from
  the Dockerfile, and add `makemigrations --check` to CI. (WP9)
- **The API lists are unpaginated** (`spectra`, `curated`, `objectnamealiases` return everything): fine at
  1197 rows, a memory and latency problem as the catalogue grows, and the frontend loads them all at start
  anyway. Add DRF pagination with a large page size and a `page_size` cap, keep the frontend reading all
  pages, and measure. (WP9, after the frontend reads pages)
- **The database user is root** for the API, the pipeline and the upload computer. A read-only user for
  the API and a schema-scoped user for the pipeline removes the worst case of an API compromise. Needs D4. (WP9)
- **Rollback by image id.** `auto-deploy.sh` rolls back to the image id it recorded, which is lost after a
  prune. With CI publishing `sha-<commit>` tags, record and roll back by tag, and the server can also be
  pinned to a known tag by hand. (WP2)
- **`API_BASE_SERVER` is baked into the frontend image** from `.env.production` at build time. With dynamic
  rendering it is read at run time, so it belongs in compose's `environment:` (it already has the right
  value, `http://backend:8000/`), and the image is then the same for the local test site and production;
  only `NEXT_PUBLIC_*` values are compiled in, and those are public. Needed for the CI build. (WP2)
- **No off-site copy of anything.** The database dumps and the 1.3 GB of download files live on the server
  only; the data repository has the inputs but not the outputs. (WP10, D5)
- **No uptime check from outside.** The nightly script notices a broken site only when it runs. A free
  external check (an uptime service hitting `/api/stats_total/`) plus the ntfy alert covers the other
  23 hours. (WP10, D6)
- **`.git_token.txt` on the server** holds a personal GitHub token for the registry login in `update.sh`;
  with public images the login is unnecessary, with private ones a fine-grained token with `read:packages`
  only should replace it. (WP9)
- **Labels on the images.** `org.opencontainers.image.source` and `.revision` on both images link each
  published image to its commit; GitHub also uses the source label to connect a package to its repository.
  (WP2)
- **The SIMBAD part of autostar** still carries the sim-script translation layer; the plan agreed on
  2026-10-31 to port HySite's SIMBAD module (Apache-2.0, needs a NOTICE file) stands and fits WP7, since the
  canonical-name cache is the same question as the MD5 manifest. (WP7, later)
- **Ten TODO/FIXME markers** in the code, to be read and either done or turned into section-6 notes during
  the code review. (WP8)
- **The README is 612 lines with two "Initial Setup" sections** and the operational knowledge is spread over
  README.md, shell/*.md and this plan. A `docs/` directory with one page per topic (setup, data pipeline,
  deployment, operations, testing) and a short README that links them. (WP11)

## 4. Work packages

Estimates are in unattended sessions of a few hours each. "Needs deploy" says what has to happen on the
user's side for the change to reach the site.

### WP1. Deployment tooling and reproducible builds
*Goal: the scripts cannot take the site down again, every build is reproducible, and the tests cover the
update path.* Sessions: 2. Needs deploy: `update.sh` on the server picks the scripts up with `git pull`;
the Dockerfile and pins need a `deploy.sh` or a CI publish.
1. `local-test.sh --auto-deploy`: builds the backend image with a changed label, retags it as the compose
   image, runs `auto-deploy.sh` with `SMOKE_BASE_URL=http://localhost` against the local stack, and checks
   that the update and the rollback paths both leave the site healthy (a deliberately broken image for the
   rollback).
2. `update.sh --check`: pull, `docker compose config --quiet`, image pull, no `down`; a dry run that catches
   a missing `.env` value before the site goes down.
3. `data.sh` prints the staging schemas it wrote; `deploy.sh` shows what it is about to commit; both refuse
   to run when `.env` points at the wrong database for the step.
4. Dockerfile: drop the unused venv/virtualenv steps, `pip uninstall pip` at the end of the runtime stage,
   remove the entries from `.trivyignore`; `python:3.14-alpine` pinned to a digest that Dependabot updates.
5. The version policy (section 3): major ceilings in `requirements.txt` and caret ranges in `package.json`;
   `shell/refresh_versions.py` after HySite's (lock compiled in the base image, image digests in
   `versions.env`, both gitignored); the Dockerfiles take `REQUIREMENTS` and `BASE_IMAGE` build args;
   `security.yml` and the frontend workflow run the refresh before the build and write the resolved
   versions into the image labels; a `deployments.log` on the server written by `auto-deploy.sh` (image
   digest, date, result); Dependabot limited to majors and security advisories; `npm update` out of
   `display.sh`.
6. Verification: local-test in all three modes; Trivy clean without the ignore entries; image size noted.

### WP2. Build and publish both images on GitHub
*Goal: a merge to `main` produces scanned, tagged images without a developer computer.* Sessions: 2.
Needs deploy: the server pulls what CI publishes; `deploy.sh` keeps only the data steps.
1. SpExo-FrontEnd: `API_BASE_SERVER` moves to compose `environment:`; `NEXT_PUBLIC_*` become build args with
   the production defaults; `.env.deploy`/`.env.display` shrink to the build args. An `image` job in
   `audit.yml`: build (`linux/amd64`), Trivy, publish `ghcr.io/spexod/frontend:LATEST` and `sha-<commit>` on
   push to `main` and on dispatch, with the same job separation as the backend workflow. Labels on the image.
2. Portal: `security.yml` publishes on push to `main` as well; labels; `auto-deploy.sh` records and rolls
   back by tag; `deploy.sh` loses the image steps (or gets `--images` for the emergency case).
3. Documentation: auto_update.md, deploy_plan.md section 3, README "Scripts".
4. Verification: the frontend image built in the sandbox from the same Dockerfile and args passes
   local-test; a dispatch run on a branch (publish skipped) shows the jobs green; the first real publish is
   watched by the user.

### WP3. Pipeline split (existing plan, branch `pipeline-split`)
*Goal: the server runs an API image without the science stack.* Sessions: 3. Needs deploy: a backend image
publish and `update.sh`; `data.sh` and `local-test.sh` switch to the `pipeline` service.
The plan in `shell/pipeline_split_plan.md` (on that branch) stands: the three imports that bind the API to
the pipeline, `requirements-api.txt`/`requirements-pipeline.txt`, Dockerfile targets `api` and `pipeline`, the
`pipeline` compose service, dead dependencies removed (channels, daphne, drf-generators, crispy, bootstrap4,
dpd, whitenoise, pytz, click, wheel). Rebase it on `main` first (the dead-code removal and the pins from WP1
overlap). Verification as written there, plus WP1's auto-deploy dry run with the new image.

### WP4. The GitHub feed, handled autonomously
*Goal: nobody reads Actions or Dependabot by hand.* Sessions: 1, then recurring. Needs: D1.
1. Dependabot `groups` in both repositories (all GitHub Actions in one PR; minor and patch npm/pip updates
   in one PR; majors alone) to cut the PR count.
2. The routine, as a checklist in this file and a script around `github-status.sh`: after each push and
   weekly, read runs and alerts; failed run: read the log, fix on a branch; Dependabot PR: check the run and
   the release notes, recommend the merge (the token is read-only by decision D1: the user merges and
   re-runs), stage runtime dependencies for the next deploy; `.trivyignore` review dates; a short note
   into section 5.
3. The same routine on a schedule (a scheduled cloud agent or a sandbox cron) once it has run by hand twice.

### WP5. Frontend visual fixes and a screenshot harness
*Goal: the explore page works on a phone, nothing overlaps, and a screenshot run catches regressions.*
Sessions: 3. Needs deploy: a frontend image. Decision: D7.
1. `tests/screenshots.mjs` (Playwright, checked in; `npm install playwright` in `tests/` or a dev
   dependency of the frontend): every page at 1280 and 390 px, full page, plus the explore page after
   selecting a star, saved to `logs/screenshots/<date>/`; `local-test.sh --frontend --screenshots` runs it.
2. Fixes, one page per commit, each verified by screenshot: the explore page's heading and the staged-
   download notice drawn over the plot and the navigation bar; the explore page at phone width (table
   columns, button row, "Add Columns" strip); the home page carousel overlap and the HITRAN box text wrap.
3. A simple comparison: pixel difference against the previous run's screenshots, reported, not failing.

### WP6. Accessibility and the contact form
*Goal: the site is usable with a keyboard and a screen reader; the contact form works.* Sessions: 3.
Needs deploy: a frontend image. Decisions: D2, D7.
1. `@axe-core/playwright` in the screenshot harness; a baseline report per page committed as text.
2. Per page: focus order and visible focus styles, skip link, labels and roles for the custom dropdowns,
   buttons and the plot controls, `alt` text, colour contrast in `spexostrap/Colors.css`, reduced motion.
3. The contact form: the public key in `.env.deploy` (D2), a `aria-live` status instead of `alert()`.
4. A manual screen-reader pass on the explore page, documented, for the user to repeat.

### WP7. Incremental data updates
*Goal: `update.py` processes only what changed, and a changed file with an unchanged handle is re-uploaded.*
Sessions: 3. Needs deploy: pipeline only, no server change.
1. A manifest (`data/manifest.json`, committed to the data repository): path, size, mtime, MD5 for
   `spectral_data/**` and the reference files; `update.py --manifest` compares and lists new, changed,
   removed.
2. `ObjectCollection` and `write_spectra` take the list: process and upload only those; a changed file with
   an existing handle replaces its rows and output files; removed files are reported, not deleted.
3. `deploy.sh` uses the same list to say what the rsync will move.
4. Verification: a full run and an incremental run against the local database give identical tables
   (compare dumps); timing before and after.
5. Later, with the same cache idea: the HySite SIMBAD port.

### WP8. Code review
*Goal: a full review of both code bases, findings fixed or recorded.* Sessions: 3. Needs deploy: per fix.
1. Backend: `/code-review` at high effort over `backend/science`, `backend/djangoAPI`, `backend/core`,
   `backend/autostar`, then `/simplify`; the ten TODO/FIXME markers resolved or recorded; unit tests for
   the pure functions found on the way (spectrum formatting, SQL value helpers, star-name parsing).
2. Frontend: the same over `app`, `components`, `context`; ESLint with `eslint-config-next` run clean;
   the `context/dataProvider.js` fetch paths and the auth context in particular.
3. Shell: `shellcheck` over `shell/*.sh` and the top-level scripts, fixes committed.
4. Findings that need a decision go into section 6.

### WP9. Security review, second pass
*Goal: the items the first review left open, plus the findings from the survey.* Sessions: 2. Needs deploy:
per item; D4 for the database user.
1. `/security-review` over the current `main` of both repositories; Dependabot alerts read (D1).
2. The database user (D4): SQL for an API user (SELECT on the published schemas, the users schema for
   Django) and a pipeline user; compose and `.env` changes; a migration path for the server.
3. Migrations committed, `makemigrations --check` in CI (section 3).
4. Pagination on the list endpoints, with the frontend reading pages (section 3).
5. A Content-Security-Policy for the frontend (nonce for the analytics script, plot library inline styles),
   measured with the smoke test's security group.
6. `.git_token.txt` replaced; secrets inventory (server `.env`, GitHub secrets, EmailJS key) documented with
   rotation dates; `.trivyignore` review.
7. Analytics consent (D8).

### WP10. Operations: backups, monitoring, retention
*Goal: a lost server is recoverable and an outage is noticed.* Sessions: 1. Needs: D5, D6, and the user
runs the server-side setup.
1. `shell/backup.sh`: nightly dump (the auto-deploy already dumps before an update) plus `backend/output`
   and `backend/data` rsync to the D5 target, retention, a restore test documented; a systemd timer.
2. External uptime check documented; `ALERT_WEBHOOK_URL` set (D6); the failure unit tested end to end.
3. Disk usage: image prune policy, dump retention, log rotation for `logs/`.

### WP11. Documentation review and update (last)
*Goal: every document matches the code and the scripts as they are after the packages above; one place per
topic; a short README.* Sessions: 2. Runs last, so it describes the end state once.
1. Review: every `*.md` in both repositories (README.md, shell/*.md, backend/autostar/README.md,
   tests/README.md, SpExo-FrontEnd/README.md, .env.example files) read against the code: every command,
   script option, environment variable, file path and port checked by running or grepping it; stale
   statements fixed or removed; the two "Initial Setup" sections merged.
2. Restructure: `docs/` with setup, data pipeline, deployment, operations (automatic updates, backups,
   certificates, alerts), testing, architecture (one diagram of the services and the data flow); README
   trimmed to an overview that links them; the shell/*.md files moved into it; `deploy_plan.md` and this
   plan kept as history under `docs/history/`.
3. Verification: a fresh clone following the setup page in the sandbox reaches a passing
   `local-test.sh --frontend`; every link checked.

### WP12. Tests
*Goal: the parts that broke this week are covered.* Sessions: 2. Spread over the packages above, listed
here so they are not forgotten: the auto-deploy dry run (WP1); API tests with Django's test client against
the local database (`local-test.sh --api-tests`): the auth flow as unit tests, pagination, throttles,
download permissions; the frontend end-to-end flow in Playwright (register, login, select a spectrum,
download, logout) against the local stack; CI runs the unit tests and `makemigrations --check`.

## 5. Status

| Package | Branch | Status | Verified by | Open |
|---|---|---|---|---|
| WP1 | | not started | | |
| WP2 | | not started | | D9 |
| WP3 | `pipeline-split` | plan written 2026-10-31, needs rebase on `main` | | |
| WP4 | | `github-status.sh` on `main`; routine not started | | D1 |
| WP5 | | screenshots taken 2026-11-01, findings in deploy_plan.md | | D7 |
| WP6 | | not started | | D2, D7 |
| WP7 | | not started | | |
| WP8 | | not started | | |
| WP9 | | not started | | D4, D8 |
| WP10 | | not started | | D5, D6 |
| WP11 | | not started; runs last | | |
| WP12 | | not started | | |

Proposed order for the first unattended sessions, if the check-in settles the defaults: WP1 (1 and 2: the
test harness for the scripts, then 4 and 5), WP4 (1 and 2), WP2 frontend half, WP5, WP6, WP8, WP9, WP3,
WP2 backend half, WP7, WP10, WP12 leftovers, and WP11 last: the documentation review and update is the
closing package, after the code and the scripts have stopped moving. Each session ends with the status
table updated and a message naming what was verified and what needs the user.

## 6. Findings and questions parked during the work

(empty)

## 7. Switching the server and the upload computer to the least-privilege database accounts

Prepared 2026-11-01, tested on the local stack. Nothing changes until the `.env` values are set.

1. Choose two passwords without single quotes. On the server, add to `/home/ubuntu/Portal/.env`:
   `MYSQL_API_USER="spexo_api"`, `MYSQL_API_PASSWORD=...`, `MYSQL_PIPELINE_USER="spexo_pipeline"`,
   `MYSQL_PIPELINE_PASSWORD=...` (`MYSQL_USER`/`MYSQL_PASSWORD` stay: the container's root password).
2. On the server, with the stack running: `./mysql/create-users.sh` (creates the accounts as root inside the
   container and prints their grants).
3. `./shell/update.sh` or `docker compose up --detach --force-recreate backend` so the backend reads the new
   variables; `python3 tests/smoke.py --strict` and a login afterwards (the API now connects as `spexo_api`,
   the start-up steps as `spexo_pipeline`).
4. On the upload computer, the same four values in its `.env` (it connects to the server's MySQL over
   TLS): `data.sh` and `deploy.sh` then run as `spexo_pipeline`.
5. Once both are switched and have run: `DROP USER IF EXISTS 'root'@'%';` in the MySQL client inside the
   container (`docker compose exec mysqlDB mysql -uroot -p`). Root remains usable inside the container,
   which is what `mysql/upgrade.sh` uses. Reversal at any point: remove the four values from `.env` and
   recreate the backend.
