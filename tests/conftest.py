"""Shared fixtures for kt-masterviz tests."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    """Redirect registry reads/writes to tmp_path so tests don't touch
    the real ``~/.kt-masterlog/runs/`` directory."""
    monkeypatch.setenv("KT_MASTERLOG_REGISTRY_DIR", str(tmp_path / "_registry"))


def _write_manifest(registry_dir: Path, **overrides) -> Path:
    """Write a v1 manifest into ``registry_dir`` for test use."""
    registry_dir.mkdir(parents=True, exist_ok=True)
    base = {
        "schema_version": 1,
        "run_id": "abc123",
        "project_name": "test_proj",
        "csv_path": "/tmp/test.csv",
        "pid": os.getpid(),
        "hostname": socket.gethostname(),
        "started_at": "2026-05-15T20:00:00+00:00",
        "ended_at": None,
        "status": "running",
    }
    base.update(overrides)
    path = registry_dir / f"{base['run_id']}.json"
    path.write_text(json.dumps(base, indent=2))
    return path


@pytest.fixture
def write_manifest():
    """Test helper: write a manifest file with default values + overrides."""
    return _write_manifest


@pytest.fixture
def sample_csv(tmp_path) -> Path:
    """A small master CSV: 2 trials, 3 epochs each, with hp + metric columns."""
    path = tmp_path / "log.csv"
    path.write_text(
        "trial_id,epoch,lr,units,dataset,loss,val_loss,accuracy,val_accuracy\n"
        "0001,1,0.001,64,mnist,0.82,0.91,0.72,0.68\n"
        "0001,2,0.001,64,mnist,0.65,0.74,0.78,0.75\n"
        "0001,3,0.001,64,mnist,0.51,0.62,0.84,0.80\n"
        "0002,1,0.0003,128,mnist,0.79,0.85,0.74,0.71\n"
        "0002,2,0.0003,128,mnist,0.60,0.70,0.81,0.77\n"
        "0002,3,0.0003,128,mnist,0.45,0.58,0.86,0.83\n"
    )
    return path


@pytest.fixture
def csv_with_partial_last_line(tmp_path) -> Path:
    """A master CSV where the writer was caught mid-row.

    Simulates the race where a reader picks up the file while the writer
    is between writing the value-list and the trailing newline.
    """
    path = tmp_path / "log.csv"
    path.write_text(
        "trial_id,epoch,lr,loss\n"
        "0001,1,0.001,0.82\n"
        "0001,2,0.001,0.65\n"
        "0002,1,0.0003"  # partial row, no newline, missing two fields
    )
    return path


@pytest.fixture
def empty_csv(tmp_path) -> Path:
    """A master CSV with only the header row."""
    path = tmp_path / "log.csv"
    path.write_text("trial_id,epoch,lr,units,loss,val_loss\n")
    return path
