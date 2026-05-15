"""Smoke tests for the CLI entry point.

The dashboard itself is a Streamlit script tested by test_dashboard_smoke.py
with Playwright. These tests cover the CLI argument parsing and the
non-launching code paths (--list, error cases) since they exit before
spawning Streamlit and so are safe to run synchronously.
"""

from __future__ import annotations

import os
import subprocess
import sys


def _run_cli(*args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "kt_masterviz.cli", *args],
        capture_output=True,
        text=True,
        env=env,
    )


class TestCLIBasics:
    def test_help_succeeds(self):
        result = _run_cli("--help")
        assert result.returncode == 0
        assert "kt-masterviz" in result.stdout
        assert "csv_path" in result.stdout
        assert "--latest" in result.stdout
        assert "--list" in result.stdout

    def test_invalid_port_type_fails(self):
        result = _run_cli("/tmp/anything.csv", "--port", "not-a-number")
        assert result.returncode != 0


class TestListFlag:
    def test_list_with_empty_registry(self, tmp_path):
        """--list against an empty registry exits 0 with an informational message."""
        result = _run_cli(
            "--list",
            env_extra={"KT_MASTERLOG_REGISTRY_DIR": str(tmp_path / "empty")},
        )
        assert result.returncode == 0
        assert "No registered runs" in result.stdout

    def test_list_prints_registered_runs(self, tmp_path, write_manifest):
        registry = tmp_path / "registry"
        write_manifest(
            registry,
            run_id="r1",
            project_name="alpha_sweep",
            status="completed",
            started_at="2026-05-15T20:00:00+00:00",
        )
        write_manifest(
            registry,
            run_id="r2",
            project_name="beta_sweep",
            status="running",
            started_at="2026-05-15T21:00:00+00:00",
        )
        result = _run_cli(
            "--list",
            env_extra={"KT_MASTERLOG_REGISTRY_DIR": str(registry)},
        )
        assert result.returncode == 0
        assert "alpha_sweep" in result.stdout
        assert "beta_sweep" in result.stdout
        # Header present
        assert "STATUS" in result.stdout
        assert "PROJECT" in result.stdout


class TestLatestFlag:
    def test_latest_with_empty_registry_fails(self, tmp_path):
        result = _run_cli(
            "--latest",
            env_extra={"KT_MASTERLOG_REGISTRY_DIR": str(tmp_path / "empty")},
        )
        assert result.returncode != 0
        assert "no runs are registered" in result.stderr

    def test_latest_and_explicit_path_conflict(self, tmp_path):
        result = _run_cli(
            "/tmp/foo.csv",
            "--latest",
            env_extra={"KT_MASTERLOG_REGISTRY_DIR": str(tmp_path / "empty")},
        )
        assert result.returncode != 0
        assert "not both" in result.stderr
