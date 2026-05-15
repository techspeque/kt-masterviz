"""Tests for the registry reader."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from kt_masterviz.registry import (
    SUPPORTED_SCHEMA_VERSIONS,
    Run,
    latest_run,
    list_runs,
    registry_dir,
)


class TestRegistryDir:
    def test_env_var_overrides_default(self, tmp_path, monkeypatch):
        monkeypatch.setenv("KT_MASTERLOG_REGISTRY_DIR", str(tmp_path / "custom"))
        assert registry_dir() == tmp_path / "custom"

    def test_default_is_under_home(self, monkeypatch):
        monkeypatch.delenv("KT_MASTERLOG_REGISTRY_DIR", raising=False)
        assert registry_dir() == Path.home() / ".kt-masterlog" / "runs"


class TestListRuns:
    def test_empty_when_no_dir(self):
        assert list_runs() == []

    def test_reads_valid_manifest(self, write_manifest):
        write_manifest(
            registry_dir(),
            run_id="run_a",
            project_name="alpha",
            status="completed",
            started_at="2026-05-15T20:00:00+00:00",
        )
        runs = list_runs()
        assert len(runs) == 1
        assert isinstance(runs[0], Run)
        assert runs[0].run_id == "run_a"
        assert runs[0].project_name == "alpha"
        assert runs[0].status == "completed"

    def test_sorts_most_recent_first(self, write_manifest):
        write_manifest(
            registry_dir(),
            run_id="older",
            started_at="2026-05-10T10:00:00+00:00",
            status="completed",
        )
        write_manifest(
            registry_dir(),
            run_id="newer",
            started_at="2026-05-15T15:00:00+00:00",
            status="completed",
        )
        runs = list_runs()
        assert [r.run_id for r in runs] == ["newer", "older"]

    def test_skips_malformed_manifest(self, write_manifest):
        # Valid run alongside a broken file
        write_manifest(registry_dir(), run_id="good", status="completed")
        (registry_dir() / "bad.json").write_text("{not valid json")
        runs = list_runs()
        assert [r.run_id for r in runs] == ["good"]

    def test_skips_unsupported_schema_version(self, write_manifest):
        write_manifest(
            registry_dir(),
            run_id="future",
            schema_version=999,
            status="completed",
        )
        write_manifest(
            registry_dir(),
            run_id="current",
            schema_version=next(iter(SUPPORTED_SCHEMA_VERSIONS)),
            status="completed",
        )
        runs = list_runs()
        assert [r.run_id for r in runs] == ["current"]


class TestStaleEntryPromotion:
    def test_running_with_live_pid_stays_running(self, write_manifest):
        write_manifest(
            registry_dir(),
            run_id="alive",
            status="running",
            pid=os.getpid(),  # this test process is definitely alive
        )
        assert list_runs()[0].status == "running"

    def test_running_with_dead_pid_promoted_to_crashed(self, write_manifest):
        # A PID very unlikely to be alive — but still well-formed.
        write_manifest(
            registry_dir(),
            run_id="dead",
            status="running",
            pid=2**31 - 1,  # max int32, almost certainly unused
        )
        assert list_runs()[0].status == "crashed"

    def test_completed_status_never_promoted(self, write_manifest):
        write_manifest(
            registry_dir(),
            run_id="done",
            status="completed",
            pid=2**31 - 1,
        )
        assert list_runs()[0].status == "completed"


class TestLatestRun:
    def test_returns_none_when_empty(self):
        assert latest_run() is None

    def test_returns_most_recent(self, write_manifest):
        write_manifest(
            registry_dir(),
            run_id="r1",
            started_at="2026-05-10T10:00:00+00:00",
            status="completed",
        )
        write_manifest(
            registry_dir(),
            run_id="r2",
            started_at="2026-05-12T10:00:00+00:00",
            status="completed",
        )
        assert latest_run().run_id == "r2"
