#!/usr/bin/env python
"""Make sure the venv's Playwright can actually launch a browser.

Snapshot rendering (`cadgen step snapshot`, the CAD Viewer, every `* snapshot`
verb) drives a headless Chromium through Playwright. Playwright only accepts
the exact browser build its own version pins, and there are two ways to get one:

  * download it (`playwright install chromium`) — the normal path;
  * use a Chromium that is already on the machine — the only path in sandboxes
    that pre-install browsers under PLAYWRIGHT_BROWSERS_PATH and block the
    Playwright CDN.

For the second case the fix is to pin *Playwright* to the version that ships the
build already on disk, instead of pulling a build that matches Playwright. This
script figures out which of the two applies and does it.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

BROWSERS_JSON = (
    "https://raw.githubusercontent.com/microsoft/playwright/v{version}"
    "/packages/playwright-core/browsers.json"
)
PYPI_JSON = "https://pypi.org/pypi/playwright/json"


def chromium_launchable() -> bool:
    """True when Playwright's pinned Chromium build is present on disk."""
    probe = (
        "from playwright.sync_api import sync_playwright;"
        "import pathlib,sys;"
        "p=sync_playwright().start();"
        "sys.exit(0 if pathlib.Path(p.chromium.executable_path).exists() else 1)"
    )
    return subprocess.run([sys.executable, "-c", probe]).returncode == 0


def local_chromium_revisions() -> list[str]:
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if not root or not Path(root).is_dir():
        return []
    revisions = []
    for entry in sorted(Path(root).iterdir()):
        match = re.fullmatch(r"chromium-(\d+)", entry.name)
        if match:
            revisions.append(match.group(1))
    return revisions


def fetch(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def playwright_version_for(revision: str) -> str | None:
    """The newest Playwright release whose chromium pin is `revision`."""
    releases = fetch(PYPI_JSON)["releases"]
    stable = sorted(
        (v for v in releases if re.fullmatch(r"\d+\.\d+\.\d+", v)),
        key=lambda v: tuple(int(part) for part in v.split(".")),
        reverse=True,
    )
    for version in stable[:40]:
        try:
            browsers = fetch(BROWSERS_JSON.format(version=version))["browsers"]
        except Exception:
            continue
        for browser in browsers:
            if browser["name"] == "chromium" and browser["revision"] == revision:
                return version
    return None


def pip_install(*args: str) -> bool:
    return subprocess.run([sys.executable, "-m", "pip", "install", *args]).returncode == 0


def main() -> int:
    if chromium_launchable():
        print("chromium: already available to playwright")
        return 0

    for revision in local_chromium_revisions():
        version = playwright_version_for(revision)
        if not version:
            continue
        print(f"chromium: build {revision} is on disk; pinning playwright=={version}")
        if pip_install("-q", f"playwright=={version}") and chromium_launchable():
            return 0

    print("chromium: no local build matched; downloading playwright's own")
    if subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium", "chromium-headless-shell"]
    ).returncode == 0 and chromium_launchable():
        return 0

    print(
        "chromium: unavailable — CAD generation and inspection still work, "
        "but snapshots and the CAD Viewer will fail.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
