"""
File-safe CSV reader for kt-masterlog master logs.

The writer (`kt_masterlog.MasterEpochLogger`) appends one row per epoch
per trial to a flat CSV. This module reads that CSV in a way that is
safe to call while the writer is mid-append — `on_bad_lines='skip'`
tolerates the rare case of a partial last row caught mid-write. On
POSIX, single-row writes smaller than PIPE_BUF (4 KiB) are atomic
under O_APPEND, so this concern is mostly defensive.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# Columns that are NEVER hyperparameters, regardless of name.
RESERVED_COLUMNS = frozenset({"trial_id", "epoch"})

# Substrings that identify a column as a metric rather than a hyperparameter.
# Heuristic — kt-masterlog doesn't tag metrics explicitly, so this is the best
# we can do without breaking the "any CSV with this schema" contract.
METRIC_INDICATORS = (
    "loss",
    "accuracy",
    "acc",
    "auc",
    "mae",
    "mse",
    "rmse",
    "f1",
    "precision",
    "recall",
    "iou",
    "dice",
)


def load_master_csv(path: str | Path) -> pd.DataFrame:
    """Read a master CSV, tolerant of partial last rows from a live writer.

    Partial-row behavior: pandas pads missing trailing fields with NaN.
    A row caught mid-write will show up immediately with its identity
    columns (``trial_id``, ``epoch``) populated and ``NaN`` for any
    fields the writer hadn't reached yet. Line charts render NaN as
    gaps; ``idxmin`` / ``idxmax`` ignore NaN — both are the desired
    behavior for a live dashboard.

    Parameters
    ----------
    path : str or Path
        Path to the master CSV file produced by kt-masterlog.

    Returns
    -------
    pandas.DataFrame
        Empty if the file has only a header row.

    Raises
    ------
    FileNotFoundError
        If the path does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Master CSV not found: {path}")

    return pd.read_csv(path, on_bad_lines="skip")


def detect_hyperparameter_columns(df: pd.DataFrame) -> list[str]:
    """Return column names that look like hyperparameters.

    A column is treated as a hyperparameter if it is not in
    ``RESERVED_COLUMNS`` and its lowercased name contains none of the
    substrings in ``METRIC_INDICATORS``. Extra static fields from
    ``TunerConfig.extra_fields`` (e.g. ``dataset``, ``git_sha``) will
    also pass this filter — that's intentional; they're useful to
    group/filter by in the dashboard.
    """
    return [
        c
        for c in df.columns
        if c not in RESERVED_COLUMNS
        and not any(m in c.lower() for m in METRIC_INDICATORS)
    ]


def detect_metric_columns(df: pd.DataFrame) -> list[str]:
    """Return column names that look like training/validation metrics."""
    return [
        c
        for c in df.columns
        if c not in RESERVED_COLUMNS
        and any(m in c.lower() for m in METRIC_INDICATORS)
    ]
