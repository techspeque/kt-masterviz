"""
Reader for kt-masterlog's run registry.

Discovers run manifests written by kt-masterlog at
``~/.kt-masterlog/runs/<run_id>.json`` (or the path in
``$KT_MASTERLOG_REGISTRY_DIR``).

Stale-entry handling: a manifest with ``status="running"`` but a PID
that no longer exists is reported as ``"crashed"`` — the writer
process died (or was killed) without updating its status. We never
mutate the on-disk manifest from the reader; the stale promotion is
done at read time.

This module deliberately does NOT depend on kt-masterlog. We share
only the on-disk schema (see ``kt_masterlog.registry`` docstring for
the canonical spec). Versioned via ``schema_version`` — older
schemas are accepted; future incompatible ones can be rejected here.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_SCHEMA_VERSIONS = {1}

logger = logging.getLogger(__name__)


def registry_dir() -> Path:
    env = os.environ.get("KT_MASTERLOG_REGISTRY_DIR")
    if env:
        return Path(env)
    return Path.home() / ".kt-masterlog" / "runs"


@dataclass
class Run:
    run_id: str
    project_name: str
    csv_path: str
    pid: int
    hostname: str
    started_at: str
    ended_at: str | None
    status: str  # "running" | "completed" | "failed" | "crashed"
    schema_version: int


def _pid_alive(pid: int) -> bool:
    """Return True iff ``pid`` is a live process on this host (POSIX)."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # The PID exists but is owned by another user; still alive.
        return True
    except OSError:
        return False


def _effective_status(raw_status: str, pid: int) -> str:
    """Promote ``running`` to ``crashed`` when the writer process is gone."""
    if raw_status == "running" and not _pid_alive(pid):
        return "crashed"
    return raw_status


def _parse(path: Path) -> Run | None:
    """Parse a single manifest file. Returns None on any error (logged)."""
    try:
        data = json.loads(path.read_text())
        version = data.get("schema_version", 0)
        if version not in SUPPORTED_SCHEMA_VERSIONS:
            logger.debug(
                "Skipping manifest %s with unsupported schema_version=%s",
                path,
                version,
            )
            return None
        return Run(
            run_id=data["run_id"],
            project_name=data["project_name"],
            csv_path=data["csv_path"],
            pid=int(data["pid"]),
            hostname=data.get("hostname", ""),
            started_at=data["started_at"],
            ended_at=data.get("ended_at"),
            status=_effective_status(data["status"], int(data["pid"])),
            schema_version=version,
        )
    except (KeyError, ValueError, OSError):
        logger.debug("Skipping malformed manifest %s", path, exc_info=True)
        return None


def list_runs() -> list[Run]:
    """All discoverable runs, most-recent first.

    Skips malformed manifests silently — the dashboard should remain
    usable even if a corrupted file appears in the registry directory.
    """
    dir_ = registry_dir()
    if not dir_.exists():
        return []
    runs = [r for r in (_parse(p) for p in dir_.glob("*.json")) if r is not None]
    runs.sort(key=lambda r: r.started_at, reverse=True)
    return runs


def latest_run() -> Run | None:
    """The most-recently-started run, or None if the registry is empty."""
    runs = list_runs()
    return runs[0] if runs else None
