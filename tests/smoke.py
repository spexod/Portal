#!/usr/bin/env python3
"""Smoke tests for spexodisks.com: every page and API endpoint answers, plus security checks.

Only the Python standard library is used, so this runs on the server without installing anything.
Only GET requests and one deliberately failing login POST are sent; nothing is changed on the site.

    python3 tests/smoke.py                                  # the production site
    python3 tests/smoke.py --base-url http://localhost      # a local docker compose stack
    python3 tests/smoke.py --strict                         # security warnings fail the run too

Exit status 0: every page and API check passed (and, with --strict, every security check).
The nightly update (shell/auto-deploy.sh) runs this and rolls back when it fails.
"""
import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

# The frontend pages, see SpExo-FrontEnd/app/(SharedContext)/*/page.js*
PAGES = [
    "/",
    "/ExploreData",
    "/DataInfo",
    "/Tutorials",
    "/Skymap",
    "/Contact",
    "/DevTeam",
    "/Login",
    "/Register",
    "/ResetPasswordRequest",
    "/ResetPassword",
]
# The API tables the frontend loads at startup (SpExo-FrontEnd/context/fetch_data.js): endpoint, expected JSON type
API_TABLES = [
    ("stats_total", list),
    ("stats_instrument", list),
    ("available_isotopologues", list),
    ("available_params_and_units", list),
    ("default_spectrum", dict),
    ("default_spectrum_info", list),
    ("curated", list),
    ("spectra", list),
    ("objectnamealiases", list),
]
SECURITY_HEADERS = ["strict-transport-security", "x-content-type-options", "x-frame-options", "referrer-policy"]
# text Next.js renders when a page crashes on the client or server
ERROR_MARKERS = ["Application error", "Internal Server Error", "This page could not be found"]


class Response:
    def __init__(self, status, headers, body, final_url):
        self.status, self.headers, self.body, self.url = status, headers, body, final_url

    def json(self):
        return json.loads(self.body.decode("utf-8"))

    def header(self, name):
        return self.headers.get(name, "")


class Site:
    def __init__(self, base_url, timeout, follow_redirects=True, insecure=False):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        handlers = []
        if not follow_redirects:
            handlers.append(_NoRedirect())
        if insecure:
            handlers.append(urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
        self.opener = urllib.request.build_opener(*handlers)

    def get(self, path, method="GET", data=None, headers=None, url=None):
        url = url or self.base_url + path
        req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
        req.add_header("User-Agent", "spexodisks-smoke-test")
        try:
            with self.opener.open(req, timeout=self.timeout) as res:
                return Response(res.status, _lower_keys(res.headers), res.read(), res.geturl())
        except urllib.error.HTTPError as err:
            return Response(err.code, _lower_keys(err.headers), err.read(), err.geturl())


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _lower_keys(headers):
    return {key.lower(): value for key, value in headers.items()}


class Results:
    def __init__(self):
        self.rows = []

    def check(self, group, name, passed, detail=""):
        self.rows.append((group, name, bool(passed), detail))
        return bool(passed)

    def report(self, strict):
        failed = 0
        for group, name, passed, detail in self.rows:
            if passed:
                status = "PASS"
            elif group == "security" and not strict:
                status = "WARN"
            else:
                status = "FAIL"
                failed += 1
            print(f"{status:4} [{group:8}] {name}" + (f" -- {detail}" if detail else ""))
        warned = sum(1 for g, _, p, _ in self.rows if not p and g == "security" and not strict)
        print(f"\n{len(self.rows)} checks: {len(self.rows) - failed - warned} passed, {failed} failed, {warned} warnings")
        return failed == 0


def check_page(site, results, path):
    res = site.get(path)
    body = res.body.decode("utf-8", errors="replace")
    ok = res.status == 200 and "text/html" in res.header("content-type") and "<html" in body
    detail = f"HTTP {res.status}, {res.header('content-type')}, {len(body)} bytes"
    # Next.js embeds its not-found page in the script payload of every page, so only look at the visible HTML
    visible = re.sub(r"<script\b.*?</script>", "", body, flags=re.DOTALL)
    marker = next((m for m in ERROR_MARKERS if m in visible), None)
    if ok and marker:
        ok, detail = False, f"page rendered an error: '{marker}'"
    results.check("pages", f"GET {path}", ok, detail)


def check_api_table(site, results, endpoint, expected_type):
    res = site.get(f"/api/{endpoint}/?format=json")
    detail = f"HTTP {res.status}, {res.header('content-type')}"
    data = None
    ok = res.status == 200 and "application/json" in res.header("content-type")
    if ok:
        try:
            data = res.json()
            ok = isinstance(data, expected_type) and len(data) > 0
            detail = f"{len(data)} {'rows' if expected_type is list else 'keys'}"
        except ValueError as err:
            ok, detail = False, f"not JSON: {err}"
    results.check("api", f"GET /api/{endpoint}/", ok, detail)
    return data if ok else None


def check_api(site, results):
    tables = {endpoint: check_api_table(site, results, endpoint, kind) for endpoint, kind in API_TABLES}

    # the per-spectrum and per-isotopologue tables, which djangoAPI/dynamic_data.py builds at startup
    spectra = tables.get("spectra") or []
    if spectra:
        handle = spectra[0].get("spectrum_handle", "")
        res = site.get(f"/api/{urllib.parse.quote(handle.lower())}/?format=json")
        results.check("api", f"GET /api/<spectrum handle>/ ({handle})", res.status == 200, f"HTTP {res.status}")
    isotopologues = tables.get("available_isotopologues") or []
    if isotopologues:
        name = isotopologues[0].get("name", "")
        res = site.get(f"/api/isotopologue_{urllib.parse.quote(name.lower())}/?format=json")
        results.check("api", f"GET /api/isotopologue_<name>/ ({name})", res.status == 200, f"HTTP {res.status}")

    # the frontend joins these tables by spexodisks_handle, so they have to agree
    curated = tables.get("curated") or []
    if curated and spectra:
        curated_handles = {row.get("spexodisks_handle") for row in curated}
        orphans = {row.get("spexodisks_handle") for row in spectra} - curated_handles
        results.check("api", "every spectrum belongs to a curated object", not orphans,
                      f"{len(orphans)} spectra with no curated object" if orphans else f"{len(curated_handles)} objects")
        # a page for one real object
        check_page(site, results, f"/ExploreData/{urllib.parse.quote(curated[0]['spexodisks_handle'])}")

    stats = tables.get("stats_total") or [{}]
    results.check("api", "stats_total has counts", all(k in stats[0] for k in ("total_spectra", "total_stars")) if stats else False,
                  ", ".join(f"{k}={v}" for k, v in stats[0].items()) if stats else "")

    # static files for the Django site
    res = site.get("/api/static/admin/css/base.css")
    results.check("api", "GET /api/static/ (collected static files)", res.status == 200, f"HTTP {res.status}")


def check_auth(site, results):
    res = site.get("/api/users/me")
    results.check("auth", "GET /api/users/me without a token is refused", res.status == 401, f"HTTP {res.status}")
    body = json.dumps({"email": "smoke-test@example.com", "password": "not-a-real-password"}).encode()
    res = site.get("/api/users/token/", method="POST", data=body, headers={"Content-Type": "application/json"})
    results.check("auth", "POST /api/users/token/ with wrong credentials is refused", res.status in (400, 401), f"HTTP {res.status}")


def check_security(site, results, no_redirect):
    res = site.get("/")
    for name in SECURITY_HEADERS:
        results.check("security", f"{name} header", bool(res.header(name)), res.header(name) or "missing")
    server = res.header("server")
    results.check("security", "server header hides the nginx version", not re.search(r"\d", server), server or "absent")

    res = site.get("/robots.txt")
    results.check("security", "GET /robots.txt is served", res.status == 200, f"HTTP {res.status}")

    # the download endpoint requires a login (djangoAPI/views.py download_spectra)
    res = site.get("/api/datadownload/?spectra=smoke-test-handle")
    results.check("security", "GET /api/datadownload/ without a token is refused", res.status in (401, 403), f"HTTP {res.status}")

    # logout revokes the refresh token on the server (djangoAPI/views.py LogoutView); no token given here
    res = site.get("/api/users/logout/", method="POST", data=b"{}", headers={"Content-Type": "application/json"})
    results.check("security", "POST /api/users/logout/ exists (server-side logout)", res.status == 205, f"HTTP {res.status}")

    # unknown API paths are 404, not the catch-all index page (core/urls.py)
    res = site.get("/api/no-such-endpoint-smoke-test/")
    results.check("security", "unknown /api/ path is 404", res.status == 404, f"HTTP {res.status}")

    for path in ("/.env", "/api/.env", "/.git/config"):
        res = site.get(path)
        results.check("security", f"GET {path} is refused", res.status in (403, 404), f"HTTP {res.status}")

    if site.base_url.startswith("https://"):
        http_url = "http://" + site.base_url[len("https://"):] + "/"
        res = no_redirect.get("", url=http_url)
        location = res.header("location")
        results.check("security", "http redirects to https", res.status in (301, 308) and location.startswith("https://"),
                      f"HTTP {res.status} -> {location or 'no Location header'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="https://spexodisks.com", help="site to test (default: %(default)s)")
    parser.add_argument("--timeout", type=float, default=30, help="seconds per request (default: %(default)s)")
    parser.add_argument("--strict", action="store_true", help="security findings fail the run instead of warning")
    parser.add_argument("--insecure", action="store_true", help="skip TLS certificate verification (local stacks)")
    args = parser.parse_args()

    site = Site(args.base_url, args.timeout, insecure=args.insecure)
    no_redirect = Site(args.base_url, args.timeout, follow_redirects=False, insecure=args.insecure)
    results = Results()
    print(f"Smoke test of {site.base_url}\n")
    try:
        for path in PAGES:
            check_page(site, results, path)
        check_api(site, results)
        check_auth(site, results)
        check_security(site, results, no_redirect)
    except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
        print(f"FAIL could not reach {site.base_url}: {err}")
        return 2
    return 0 if results.report(args.strict) else 1


if __name__ == "__main__":
    sys.exit(main())
