"""
Command-line entry point.

Three ways to point at a run:

  kt-masterviz path/to/master_log.csv     # explicit path
  kt-masterviz --latest                   # most recent registered run
  kt-masterviz                            # no args → Streamlit picker
                                          #   over registered runs

Plus a non-launching listing for scripting:

  kt-masterviz --list                     # print registered runs and exit
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from kt_masterviz.registry import latest_run, list_runs


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="kt-masterviz",
        description="Live dashboard for kt-masterlog master CSV files.",
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=str,
        help="Path to a master CSV. Omit and pass --latest, or omit to open "
             "the run picker.",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Open the most recently registered run (no path needed).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print registered runs and exit (no dashboard).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Streamlit server port (default: 8501).",
    )
    parser.add_argument(
        "--address",
        type=str,
        default="localhost",
        help="Streamlit server address (default: localhost).",
    )
    args = parser.parse_args()

    if args.list:
        return _print_runs()

    csv_path = _resolve_csv_path(args)
    return _launch_dashboard(csv_path, args.port, args.address)


def _print_runs() -> int:
    runs = list_runs()
    if not runs:
        print("No registered runs found in", end=" ")
        from kt_masterviz.registry import registry_dir
        print(registry_dir())
        return 0
    print(f"{'STATUS':<10}  {'STARTED':<25}  {'PROJECT':<20}  CSV")
    print("-" * 100)
    for r in runs:
        print(f"{r.status:<10}  {r.started_at:<25}  {r.project_name:<20}  {r.csv_path}")
    return 0


def _resolve_csv_path(args) -> Path | None:
    """Resolve the CSV path from the CLI args, or return None for picker mode."""
    if args.csv_path and args.latest:
        print(
            "Error: pass either a csv_path or --latest, not both.",
            file=sys.stderr,
        )
        sys.exit(2)

    if args.csv_path:
        return Path(args.csv_path).resolve()

    if args.latest:
        run = latest_run()
        if run is None:
            print(
                "Error: --latest requested but no runs are registered. "
                "Run kt-masterlog with default settings to register one.",
                file=sys.stderr,
            )
            sys.exit(1)
        return Path(run.csv_path)

    # No args → picker mode (dashboard receives no CSV path)
    return None


def _launch_dashboard(
    csv_path: Path | None, port: int, address: str
) -> int:
    dashboard_path = Path(__file__).parent / "dashboard.py"
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(dashboard_path),
        "--server.port",
        str(port),
        "--server.address",
        address,
        # Disable Streamlit's source-file watcher: we don't hot-reload the
        # dashboard for end users (our auto-refresh handles data updates),
        # and the watcher consumes inotify watches that can hit the system
        # limit on dev machines with many watches already active.
        "--server.fileWatcherType",
        "none",
        "--",
    ]
    # Pass empty string for picker mode — argv-len signaling avoids
    # surprises if a path happens to look like a flag.
    cmd.append(str(csv_path) if csv_path is not None else "")
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
