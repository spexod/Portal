#!/usr/bin/env python3
"""
End-to-end test of the user accounts API against a LOCAL stack (shell/local-test.sh).

It registers a throwaway user and walks through the whole token lifecycle:
register -> login -> /users/me -> refresh (rotation revokes the old refresh token) -> an authenticated
download -> password change (revokes every token) -> login with the new password -> logout (revokes
the refresh token). Standard library only.

The user it creates stays in the database, so the script refuses any host other than localhost unless
--remote is given. Eight requests go to the throttled 'auth' endpoints (10 per minute per address, see
REST_FRAMEWORK in core/settings.py): wait a minute between runs.

    python3 tests/auth_flow.py --base-url http://localhost
"""
import argparse
import json
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


class Api:
    def __init__(self, base_url, timeout):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def call(self, method, path, body=None, token=None):
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as err:
            return err.code, err.headers, err.read()

    def json(self, method, path, body=None, token=None):
        status, headers, raw = self.call(method, path, body, token)
        try:
            payload = json.loads(raw) if raw else None
        except ValueError:
            payload = raw[:200]
        return status, payload


class Checks:
    def __init__(self):
        self.failed = 0

    def check(self, name, passed, detail=""):
        if not passed:
            self.failed += 1
        print(f"{'PASS' if passed else 'FAIL'} {name}" + (f" -- {detail}" if detail else ""))
        return passed


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", required=True, help="the local stack, e.g. http://localhost")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--remote", action="store_true", help="allow a host other than localhost (creates a user there)")
    args = parser.parse_args()
    host = urllib.parse.urlsplit(args.base_url).hostname or ""
    if host not in ("localhost", "127.0.0.1", "::1") and not args.remote:
        parser.error(f"{host} is not a local stack; this test creates a user (--remote to run anyway)")

    api = Api(args.base_url, args.timeout)
    checks = Checks()
    email = f"auth-flow-{int(time.time())}@example.invalid"
    password = "Test-" + secrets.token_urlsafe(12)
    new_password = "Test-" + secrets.token_urlsafe(12)
    print(f"Account API test of {api.base_url} as {email}\n")

    # 1. register
    status, user = api.json("POST", "/api/users/register", {
        "first_name": "Auth", "last_name": "Flow", "email": email, "institution": "tests/auth_flow.py",
        "password": password})
    checks.check("register", status == 201 and isinstance(user, dict) and user.get("email") == email, f"HTTP {status} {user}")
    if status == 429:
        print("\nthrottled by the 'auth' scope: wait a minute and run again")
        return 2

    # 2. login
    status, tokens = api.json("POST", "/api/users/token/", {"email": email, "password": password})
    ok = checks.check("login returns access and refresh tokens",
                      status == 200 and isinstance(tokens, dict) and {"access", "refresh"} <= set(tokens), f"HTTP {status}")
    if not ok:
        print(f"\ncannot continue without tokens: {tokens}")
        return 1
    access, refresh = tokens["access"], tokens["refresh"]

    # 3. the access token identifies the user
    status, me = api.json("GET", "/api/users/me", token=access)
    checks.check("/users/me with the access token", status == 200 and me.get("email") == email, f"HTTP {status} {me}")
    checks.check("/users/me never returns the password", isinstance(me, dict) and "password" not in me)

    # 4. refresh rotates the token pair, the old refresh token is revoked
    status, rotated = api.json("POST", "/api/users/token/refresh/", {"refresh": refresh})
    ok = checks.check("refresh returns a new pair (ROTATE_REFRESH_TOKENS)",
                      status == 200 and isinstance(rotated, dict) and "refresh" in rotated and rotated["refresh"] != refresh,
                      f"HTTP {status}")
    status, _ = api.json("POST", "/api/users/token/refresh/", {"refresh": refresh})
    checks.check("the old refresh token is revoked after rotation", status == 401, f"HTTP {status}")
    if ok:
        access, refresh = rotated["access"], rotated["refresh"]

    # 5. an authenticated download
    status, spectra = api.json("GET", "/api/default_spectrum_info/")
    handle = spectra[0].get("spectrum_handle") if status == 200 and spectra else None
    if handle:
        status, headers, raw = api.call("GET", f"/api/datadownload/?spectra={urllib.parse.quote(handle)}", token=access)
        checks.check("datadownload with a token returns a zip",
                     status == 200 and "zip" in (headers.get("Content-Type") or "") and raw[:2] == b"PK",
                     f"HTTP {status}, {headers.get('Content-Type')}, {len(raw)} bytes")
    else:
        checks.check("datadownload (no spectrum handle found to download)", False, f"HTTP {status}")
    status, _, _ = api.call("GET", "/api/datadownload/?spectra=nothing", token=access)
    checks.check("datadownload of an unknown spectrum does not crash", status in (200, 400, 404), f"HTTP {status}")

    # 6. password change: wrong old password refused, then success revokes every refresh token
    status, body = api.json("PUT", "/api/change-password/", {"old_password": "wrong-" + password, "new_password": new_password},
                            token=access)
    checks.check("password change with the wrong old password is refused", status == 400, f"HTTP {status} {body}")
    status, body = api.json("PUT", "/api/change-password/", {"old_password": password, "new_password": "short"}, token=access)
    checks.check("password change to a weak password is refused", status == 400, f"HTTP {status} {body}")
    status, body = api.json("PUT", "/api/change-password/", {"old_password": password, "new_password": new_password}, token=access)
    checks.check("password change", status == 200, f"HTTP {status} {body}")
    status, _ = api.json("POST", "/api/users/token/refresh/", {"refresh": refresh})
    checks.check("the refresh token is revoked by the password change", status == 401, f"HTTP {status}")

    # 7. login with the new password, then logout revokes the refresh token
    status, tokens = api.json("POST", "/api/users/token/", {"email": email, "password": new_password})
    ok = checks.check("login with the new password", status == 200 and isinstance(tokens, dict) and "refresh" in tokens, f"HTTP {status}")
    if ok:
        status, _ = api.json("POST", "/api/users/logout/", {"refresh": tokens["refresh"]})
        checks.check("logout", status == 205, f"HTTP {status}")
        status, _ = api.json("POST", "/api/users/token/refresh/", {"refresh": tokens["refresh"]})
        checks.check("the refresh token is revoked by the logout", status == 401, f"HTTP {status}")

    print(f"\n{checks.failed} failed")
    return 1 if checks.failed else 0


if __name__ == "__main__":
    sys.exit(main())
