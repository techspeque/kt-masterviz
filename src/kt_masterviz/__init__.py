"""
kt-masterviz: Live dashboard for kt-masterlog master CSV files.

Companion package to kt-masterlog. Reads any CSV that follows the
master-log schema (trial_id, epoch, hyperparameter columns, metric
columns) and renders a Streamlit dashboard with trial summaries and
training curves. Tolerant of partial last rows so it can safely tail
a CSV being written live by a running tuner.
"""

from kt_masterviz.loader import detect_hyperparameter_columns, load_master_csv
from kt_masterviz.registry import Run, latest_run, list_runs

__all__ = [
    "load_master_csv",
    "detect_hyperparameter_columns",
    "list_runs",
    "latest_run",
    "Run",
]

__version__ = "0.1.1"
