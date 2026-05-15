"""
Streamlit dashboard script.

Not intended to be imported. Launched via the ``kt-masterviz`` CLI,
which invokes ``streamlit run`` on this file with the CSV path
forwarded as a positional argument after ``--``. An empty string in
that slot puts the dashboard in picker mode (list registered runs and
let the user choose).

To launch manually:
    streamlit run src/kt_masterviz/dashboard.py -- path/to/log.csv
    streamlit run src/kt_masterviz/dashboard.py -- ""    # picker
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import streamlit as st

from kt_masterviz.loader import (
    detect_hyperparameter_columns,
    detect_metric_columns,
    load_master_csv,
)
from kt_masterviz.registry import list_runs


SELECTED_KEY = "selected_csv_path"


def _argv_csv_path() -> Path | None:
    """Streamlit forwards args after `--` into sys.argv. Empty string = picker."""
    if len(sys.argv) < 2 or sys.argv[1] == "":
        return None
    return Path(sys.argv[1])


def _resolve_csv_path() -> Path | None:
    """Picker selections live in session_state; argv is the launch-time path."""
    if SELECTED_KEY in st.session_state:
        return Path(st.session_state[SELECTED_KEY])
    return _argv_csv_path()


def main() -> None:
    st.set_page_config(page_title="kt-masterviz", layout="wide")
    st.title("kt-masterviz")

    csv_path = _resolve_csv_path()
    if csv_path is None:
        _render_picker()
    else:
        _render_viewer(csv_path)


def _render_picker() -> None:
    st.caption("Select a registered run to view, or pass a CSV path on the CLI.")

    runs = list_runs()
    if not runs:
        st.info(
            "No registered runs found. Run a kt-masterlog tuner with default "
            "settings to register one, or launch with an explicit CSV path: "
            "`kt-masterviz path/to/master_log.csv`"
        )
        return

    rows = [
        {
            "status": r.status,
            "started_at": r.started_at,
            "project_name": r.project_name,
            "csv_path": r.csv_path,
            "run_id": r.run_id,
        }
        for r in runs
    ]
    st.dataframe(rows, width="stretch", hide_index=True)

    labels = [
        f"[{r.status}]  {r.project_name}  ({r.started_at})"
        for r in runs
    ]
    choice = st.selectbox("Open a run", options=labels, index=0)
    if st.button("Open"):
        idx = labels.index(choice)
        st.session_state[SELECTED_KEY] = runs[idx].csv_path
        st.rerun()


def _render_viewer(csv_path: Path) -> None:
    st.caption(f"Source: `{csv_path}`")

    with st.sidebar:
        st.header("Refresh")
        auto = st.checkbox("Auto-refresh", value=True)
        interval = st.slider("Interval (s)", 1, 30, 5)
        st.divider()
        if st.button("Switch run"):
            st.session_state.pop(SELECTED_KEY, None)
            st.rerun()

    if not csv_path.exists():
        st.warning(
            f"CSV does not exist yet: {csv_path}\n\n"
            "Waiting for the tuner to write the first row..."
        )
    else:
        df = load_master_csv(csv_path)

        if df.empty:
            st.info("CSV has a header but no rows yet — tuner is starting up.")
        else:
            n_trials = df["trial_id"].nunique()
            n_rows = len(df)

            col1, col2 = st.columns(2)
            col1.metric("Trials seen", n_trials)
            col2.metric("Rows (trial-epochs)", n_rows)

            hp_cols = detect_hyperparameter_columns(df)
            metric_cols = detect_metric_columns(df)

            st.subheader("Trial summary")
            objective = _pick_objective(df, metric_cols)
            if objective:
                best_per_trial = (
                    df.loc[df.groupby("trial_id")[objective].idxmin()]
                    [["trial_id", *hp_cols, objective]]
                    .sort_values(objective)
                    .reset_index(drop=True)
                )
                st.dataframe(best_per_trial, width="stretch")
            else:
                st.dataframe(
                    df[["trial_id", *hp_cols]].drop_duplicates(),
                    width="stretch",
                )

            st.subheader("Training curves")
            if metric_cols:
                metric = st.selectbox("Metric", metric_cols)
                chart_data = df.pivot(
                    index="epoch", columns="trial_id", values=metric
                )
                st.line_chart(chart_data)
            else:
                st.info("No metric columns detected in this CSV.")

            with st.expander("Raw data"):
                st.dataframe(df, width="stretch")

    if auto:
        time.sleep(interval)
        st.rerun()


def _pick_objective(df, metric_cols: list[str]) -> str | None:
    """Prefer val_loss, fall back to loss, then the first metric column."""
    for candidate in ("val_loss", "loss"):
        if candidate in df.columns:
            return candidate
    return metric_cols[0] if metric_cols else None


main()
