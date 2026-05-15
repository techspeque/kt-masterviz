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

import altair as alt
import streamlit as st

from kt_masterviz.loader import (
    detect_hyperparameter_columns,
    detect_metric_columns,
    load_master_csv,
)
from kt_masterviz.registry import list_runs


SELECTED_KEY = "selected_csv_path"
# Set by the sidebar "Switch run" button. Forces the picker even when the
# CLI was invoked with an explicit CSV path or --latest — without this,
# Switch run would no-op back to the same argv-provided CSV.
FORCE_PICKER_KEY = "force_picker"


def _argv_csv_path() -> Path | None:
    """Streamlit forwards args after `--` into sys.argv. Empty string = picker."""
    if len(sys.argv) < 2 or sys.argv[1] == "":
        return None
    return Path(sys.argv[1])


def _resolve_csv_path() -> Path | None:
    """Resolution order:
    1. The "Switch run" override (force picker, regardless of argv).
    2. The user's explicit picker selection from this session.
    3. The CSV path the CLI was launched with.
    """
    if st.session_state.get(FORCE_PICKER_KEY):
        return None
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
        # Picker selection wins over the "force picker" flag set by
        # Switch run; clear it so the new selection actually renders.
        st.session_state.pop(FORCE_PICKER_KEY, None)
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
            # Force picker even when argv supplied an explicit CSV path —
            # otherwise the resolver would fall back to argv and the
            # button would visibly do nothing.
            st.session_state[FORCE_PICKER_KEY] = True
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
                # Altair chart with X ticks pinned to the actual epoch
                # integers in the data. Altair's auto-tick placement on a
                # small numeric range inserts half-integer ticks (1.5,
                # 2.5) that look like duplicate integer labels once
                # `format="d"` truncates them. Passing explicit `values`
                # eliminates that entirely. If a run has lots of epochs
                # (>30) the labels start to crowd; the `labelOverlap`
                # setting lets d3 thin them automatically.
                chart_df = df[["trial_id", "epoch", metric]].copy()
                chart_df["trial_id"] = chart_df["trial_id"].astype(str)
                epoch_ticks = sorted(chart_df["epoch"].unique().tolist())
                chart = (
                    alt.Chart(chart_df)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X(
                            "epoch:Q",
                            title="Epoch",
                            axis=alt.Axis(
                                values=epoch_ticks,
                                format="d",
                                labelOverlap="greedy",
                            ),
                        ),
                        y=alt.Y(f"{metric}:Q", title=metric),
                        color=alt.Color("trial_id:N", title="trial_id"),
                    )
                )
                st.altair_chart(chart, width="stretch")
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
