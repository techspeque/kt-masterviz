# kt-masterviz

Live Streamlit dashboard for [kt-masterlog](https://github.com/techspeque/kt-masterlog) master CSV files. Companion package — separate install so you don't pay the dashboard's dependency footprint when you only want the logger.

## What it does

Point `kt-masterviz` at any master CSV produced by `kt-masterlog` (or any CSV that follows the schema: `trial_id`, `epoch`, hyperparameter columns, metric columns) and get a live Streamlit dashboard showing:

- **Trial summary** — one row per trial, sorted by the objective metric, with hyperparameter values inline.
- **Training curves** — per-trial loss/accuracy lines, switchable across any detected metric.
- **Raw data** — the full DataFrame, for ad-hoc filtering.

The reader is **file-safe**: tolerant of partial last rows from a writer mid-append, so you can launch the dashboard against a CSV that's still being written by a running tuner.

## Install

With pip:

```bash
pip install kt-masterviz
```

With uv:

```bash
uv add kt-masterviz
```

## Usage

```bash
kt-masterviz path/to/master_log.csv
```

Opens the dashboard at http://localhost:8501. The page auto-refreshes every few seconds (configurable in the sidebar) so trials show up as the tuner writes them.

The CSV doesn't need to exist when you launch — the dashboard polls and renders a waiting state until the writer produces the first row. Useful for starting the viewer before kicking off a long sweep.

### Programmatic use

If you'd rather build your own viewer, the loader is the reusable bit:

```python
from kt_masterviz import load_master_csv, detect_hyperparameter_columns

df = load_master_csv("runs/sweep_master_log.csv")
hp_cols = detect_hyperparameter_columns(df)
# ... your own pandas / plotly / altair code
```

## CSV schema

`kt-masterviz` works with any CSV that has:

| Column | Required | Purpose |
|--------|----------|---------|
| `trial_id` | yes | Identifies a single tuning trial |
| `epoch` | yes | Epoch number within the trial |
| `loss` / `val_loss` / `accuracy` / etc. | no (auto-detected) | Training/validation metrics |
| anything else | no | Treated as a hyperparameter or extra field |

Detection of "metric vs hyperparameter" is heuristic — a column counts as a metric if its lowercased name contains any of: `loss`, `accuracy`, `acc`, `auc`, `mae`, `mse`, `rmse`, `f1`, `precision`, `recall`, `iou`, `dice`. Everything else is treated as a hyperparameter or static field (and shown in the trial summary).

## Requirements

- Python 3.12 (tested; 3.13+ may work but is not yet verified)
- pandas ≥ 2.0
- streamlit ≥ 1.28

No dependency on `kt-masterlog` itself — `kt-masterviz` reads its file format but doesn't import its code.

## License

MIT.
