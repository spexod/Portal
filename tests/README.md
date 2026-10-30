# Tests

## Smoke tests: `smoke.py`

Requests every frontend page and every API endpoint the frontend loads, and checks the security
settings of the site. It needs only Python 3 (standard library), so it runs on the server, on a
laptop, and in CI without installing anything. It sends GET requests plus one login attempt with
wrong credentials; nothing on the site is changed.

```
python3 tests/smoke.py                                 # production, https://spexodisks.com
python3 tests/smoke.py --base-url http://localhost     # a local docker compose stack
python3 tests/smoke.py --strict                        # security warnings fail the run
python3 tests/smoke.py --help
```

Check groups:

| Group | What is checked | Failure means |
|---|---|---|
| `pages` | every page in `SpExo-FrontEnd/app/(SharedContext)` returns HTML without a rendered error, including one real `/ExploreData/<object>` page | exit status 1 |
| `api` | every table in `SpExo-FrontEnd/context/fetch_data.js` returns non-empty JSON, one per-spectrum and one per-isotopologue table, the tables agree with each other, static files are served | exit status 1 |
| `auth` | requests without a token, or with wrong credentials, are refused | exit status 1 |
| `security` | security headers, hidden server version, `robots.txt`, the download endpoint requires a login, unknown API paths are 404, dot-files are refused, http redirects to https | warning, or exit status 1 with `--strict` |

Exit status 2 means the site could not be reached at all.

### Where it runs

- **After the nightly update** on the server: `shell/auto-deploy.sh` runs it after the containers are
  recreated and rolls the backend back when it fails. The URL is `SMOKE_BASE_URL`, default
  `https://spexodisks.com`. Set it in the systemd unit if the server cannot reach its own public address.
- **After `./deploy.sh` and `./deploy_update.sh`**: run it by hand against production.
- **While developing**: run it against the local stack. A local stack without the production data
  fails the `api` group, which is expected.

### Adding a check

Add a page to `PAGES`, an endpoint to `API_TABLES`, or a `results.check(group, name, passed, detail)`
call to one of the `check_*` functions. A new frontend page is not tested until it is added here.

## Unit tests: `backend/tests/`

Tests for the pure parts of the backend, which need no database and no Django:

```
cd backend && python3 -m unittest discover tests      # numpy is needed for test_spectrum_format
```

| File | Covers |
|---|---|
| `test_sql_values.py` | `science/db/sql_values.py`: identifier validation (SQL injection attempts are rejected) and the conversion of Python/numpy values to query parameters |
| `test_spectrum_format.py` | `science/analyze/spectrum_format.py`: null points in wavelength gaps, isolated points, bad flux values |

Code that talks to MySQL (`science/db/sql.py`, the Django views) has no unit tests yet; it needs a
test database. The smoke test covers the views end to end against a running stack.

## Baseline

First run against production on 2026-10-30, before the security fixes: 40 checks, 32 passed,
0 failed, 8 warnings. The warnings were the missing security headers, the nginx version in the
`Server` header, `/robots.txt` returning 404, the download endpoint answering without a login, and
unknown `/api/` paths returning the index page with HTTP 200.
