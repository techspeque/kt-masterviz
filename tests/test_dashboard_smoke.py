"""Playwright smoke test for the Streamlit dashboard.

Launches `kt-masterviz` against a fixture CSV in a subprocess, opens the
page in headless Chromium, and asserts the dashboard rendered without
errors. This is the class of bug only a real browser render can find:
deprecated Streamlit APIs that fail at render time, server-side
exceptions during a rerun, breaking changes in transitive dependencies.

If this test fails locally with "Executable doesn't exist", install the
browser binary:
    uv run playwright install chromium
(prereqs.sh does this automatically.)
"""

from __future__ import annotations

import socket
import subprocess
import time
import urllib.request
from contextlib import closing
from pathlib import Path
from typing import Iterator

import pytest
from playwright.sync_api import sync_playwright


def _free_port() -> int:
    """Find an unused TCP port to bind the dashboard server to."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _wait_until_healthy(url: str, timeout_s: float = 30.0) -> bool:
    """Poll Streamlit's health endpoint until it responds 'ok' or we time out."""
    health = f"{url}/_stcore/health"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health, timeout=1) as resp:
                if resp.read() == b"ok":
                    return True
        except Exception:
            time.sleep(0.3)
    return False


@pytest.fixture
def running_dashboard(sample_csv: Path) -> Iterator[str]:
    """Spawn `kt-masterviz` against the sample CSV, yield its URL, tear down."""
    port = _free_port()
    url = f"http://localhost:{port}"

    proc = subprocess.Popen(
        ["kt-masterviz", str(sample_csv), "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        if not _wait_until_healthy(url):
            output = ""
            if proc.stdout is not None:
                try:
                    output = proc.stdout.read().decode(errors="replace")
                except Exception:
                    pass
            raise RuntimeError(
                f"dashboard did not become healthy within 30s\n{output}"
            )
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_dashboard_renders_without_errors(running_dashboard: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(running_dashboard)

            # Title proves the script ran past st.title().
            page.wait_for_selector("text=kt-masterviz", timeout=15_000)
            # Metric label proves the loader ran and the DataFrame was
            # processed without an exception.
            page.wait_for_selector("text=Trials seen", timeout=15_000)

            content = page.content()
        finally:
            browser.close()

    # Streamlit renders Python tracebacks verbatim in a red error box.
    # If a server-side exception slipped through, the literal Python
    # traceback header will be present in the rendered DOM.
    assert "Traceback (most recent call last)" not in content
