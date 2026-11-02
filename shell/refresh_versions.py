#!/usr/bin/env python3
"""Resolve the software Portal runs to exact versions, for a build that can be tested and reproduced.

Git holds only what to follow (the version policy in shell/next_round_plan.md, section 3):
  - the image lines in compose.yaml, e.g. ${BACKEND_BASE_IMAGE:-python:3.15-alpine}: the runtimes are
    pinned to a line, moving to a new line is an administrator's decision
  - backend/requirements.txt, unpinned, and SpExo-FrontEnd/package.json with open ranges: packages follow
    the newest release, majors included; the image build, the smoke test and the nightly rollback are
    the safety net

This script resolves those to exact versions:
  - versions.env (gitignored): every *_IMAGE variable of compose.yaml with the digest its tag points to
    today, and REQUIREMENTS=requirements.lock so the backend build installs the lock file
  - backend/requirements.lock (gitignored): every Python package at an exact version, compiled with uv
    inside the backend's base image, so it matches that Python version and platform (Alpine, musl)
  - SpExo-FrontEnd/package-lock.json (tracked): updated within the ranges of package.json, inside the
    frontend's base image (npm update --package-lock-only); skipped with --no-npm

The build scripts read versions.env (shell/build.sh); the image workflow runs this before the build and
records the result in the image labels. Needs Docker with buildx.

    python3 shell/refresh_versions.py [--no-npm] [--no-lock]
    python3 shell/refresh_versions.py --check     # only check that the declarations agree (below)

Before resolving anything, the script checks the declarations that exist in more than one place: the Python
line in compose.yaml and backend/Dockerfile, the Node line in compose.yaml, the frontend Dockerfile and its
package.json "engines", and the frontend build arguments of compose.yaml against the Dockerfile's ARGs
(the frontend's own workflow checks its build-args against the same Dockerfile).
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COMPOSE_FILE = REPO / "compose.yaml"
VERSIONS_FILE = REPO / "versions.env"
BACKEND_DIR = REPO / "backend"
FRONTEND_DIR = REPO / "SpExo-FrontEnd"
# image variables with their default tag in compose.yaml, e.g. ${NGINX_IMAGE:-nginx:stable}
IMAGE_VARIABLE = re.compile(r"\$\{(\w+_IMAGE):-([^}]+)\}")
COMPILE_COMMAND = "python3 shell/refresh_versions.py"
BACKEND_DOCKERFILE = BACKEND_DIR / "Dockerfile"
FRONTEND_DOCKERFILE = FRONTEND_DIR / "Dockerfile"
FRONTEND_PACKAGE = FRONTEND_DIR / "package.json"


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout


def proxy_args() -> list[str]:
    """Pass the proxy settings of this computer into the containers (a sandbox, a corporate network)."""
    args = []
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy"):
        if name in os.environ:
            args += ["--env", name]
    return args


def image_tags() -> dict[str, str]:
    """The image tag to follow for each *_IMAGE variable in compose.yaml, except the application's own
    images (BACKEND_IMAGE, FRONTEND_IMAGE): those are what the builds produce, not what they follow."""
    return {variable: tag for variable, tag in IMAGE_VARIABLE.findall(COMPOSE_FILE.read_text())
            if not tag.startswith("ghcr.io/spexod/")}


def compose_default(variable: str) -> str:
    """The default of ${VARIABLE:-default} in compose.yaml."""
    match = re.search(r"\$\{" + variable + r":-([^}]+)\}", COMPOSE_FILE.read_text())
    if not match:
        sys.exit(f"compose.yaml does not declare a default for {variable}")
    return match.group(1)


def compose_build_args(service: str) -> set[str]:
    """The names in the build "args:" list of a compose.yaml service."""
    text = COMPOSE_FILE.read_text()
    block = re.search(r"^  " + service + r":\n(.*?)(?=^  \w|\Z)", text, re.S | re.M)
    if not block:
        sys.exit(f"compose.yaml has no service {service}")
    return set(re.findall(r'^\s+- "(\w+)=', block.group(1), re.M))


def dockerfile_args(path: Path) -> dict[str, str]:
    """ARG name -> default of a Dockerfile (an empty string for an ARG without a default)."""
    return {name: default for name, default in re.findall(r"^ARG (\w+)=?(.*)$", path.read_text(), re.M)}


def check_declarations() -> None:
    """The declarations that exist in more than one place agree with each other (see the module docstring)."""
    problems = []
    python_line = compose_default("BACKEND_BASE_IMAGE")
    backend_arg = dockerfile_args(BACKEND_DOCKERFILE).get("BASE_IMAGE")
    if backend_arg != python_line:
        problems.append(f"the Python line is {python_line} in compose.yaml and {backend_arg} in backend/Dockerfile")
    if FRONTEND_DOCKERFILE.exists():
        node_line = compose_default("FRONTEND_BASE_IMAGE")
        frontend_args = dockerfile_args(FRONTEND_DOCKERFILE)
        if frontend_args.get("BASE_IMAGE") != node_line:
            problems.append(f"the Node line is {node_line} in compose.yaml and {frontend_args.get('BASE_IMAGE')} "
                            "in the frontend Dockerfile")
        node_major = re.search(r"node:(\d+)", node_line)
        engines = json.loads(FRONTEND_PACKAGE.read_text()).get("engines", {}).get("node", "")
        if node_major and engines != f">={node_major.group(1)}":
            problems.append(f'package.json "engines" says node "{engines}", the line is {node_line}')
        compose_args = compose_build_args("frontend") - {"BASE_IMAGE"}
        dockerfile_build_args = set(frontend_args) - {"BASE_IMAGE"}
        if compose_args != dockerfile_build_args:
            problems.append("the frontend build arguments differ: compose.yaml passes "
                            f"{sorted(compose_args)}, the Dockerfile declares {sorted(dockerfile_build_args)}")
    else:
        print(f"  (no {FRONTEND_DIR.name} checkout: the Node line and the frontend build arguments are not checked)")
    if problems:
        sys.exit("The declarations disagree:\n  " + "\n  ".join(problems))
    print("  the Python line, the Node line and the frontend build arguments agree")


def resolve_digest(tag: str) -> str:
    """The digest the tag points to now (the multi-platform index, so it works on any CPU)."""
    manifest = json.loads(run(["docker", "buildx", "imagetools", "inspect", tag, "--format", "{{json .Manifest}}"]))
    return manifest["digest"]


def in_image(image: str, directory: Path, script: str) -> None:
    """Run a shell script inside an image with the directory mounted, as the current user."""
    run(["docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}", "--env", "HOME=/tmp",
         *proxy_args(), "--volume", f"{directory}:/work", "--workdir", "/work", image, "sh", "-c", script])


def compile_lock(image: str) -> None:
    """backend/requirements.txt -> backend/requirements.lock, inside the backend's base image."""
    print(f"  backend/requirements.lock in {image.split('@')[0]}")
    in_image(image, BACKEND_DIR,
             "python -m pip install --quiet --disable-pip-version-check --target /tmp/uv uv"
             " && UV_CACHE_DIR=/tmp/uv-cache /tmp/uv/bin/uv pip compile requirements.txt --upgrade --quiet"
             f" --output-file requirements.lock --custom-compile-command '{COMPILE_COMMAND}'")


def update_npm_lock(image: str) -> None:
    """SpExo-FrontEnd/package-lock.json updated within package.json's ranges, inside the frontend's base image."""
    print(f"  SpExo-FrontEnd/package-lock.json in {image.split('@')[0]}")
    in_image(image, FRONTEND_DIR,
             "npm_config_cache=/tmp/npm-cache npm update --package-lock-only --no-audit --no-fund --silent")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--no-npm", action="store_true", help="leave package-lock.json alone")
    parser.add_argument("--no-lock", action="store_true", help="resolve the images only, no requirements.lock")
    parser.add_argument("--check", action="store_true", help="only check that the declarations agree")
    args = parser.parse_args()

    print("Checking the declarations")
    check_declarations()
    if args.check:
        return

    print("Resolving the image lines of compose.yaml")
    pinned = {}
    for variable, tag in image_tags().items():
        pinned[variable] = f"{tag}@{resolve_digest(tag)}"
        print(f"  {variable} = {pinned[variable]}")

    lines = [
        "# Exact versions for Portal, made by shell/refresh_versions.py. Do not edit by hand.",
        f"# Resolved {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        *(f"{variable}={image}" for variable, image in pinned.items()),
    ]
    if not args.no_lock:
        print("Compiling the Python lock file")
        compile_lock(pinned["BACKEND_BASE_IMAGE"])
        lines.append("REQUIREMENTS=requirements.lock")
    if not args.no_npm:
        print("Updating the npm lock file")
        update_npm_lock(pinned["FRONTEND_BASE_IMAGE"])
    VERSIONS_FILE.write_text("\n".join(lines) + "\n")
    print(f"Wrote {VERSIONS_FILE.name}")


if __name__ == "__main__":
    main()
