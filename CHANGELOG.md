# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Initial release of kt-masterviz — companion package to
[kt-masterlog](https://github.com/techspeque/kt-masterlog).

### Added

- **Live Streamlit dashboard** for kt-masterlog master CSV files. Renders
  a trial summary (sorted by objective metric, hyperparameter values
  inline), per-trial training curves switchable across detected metrics,
  and a collapsible raw-data view. Auto-refresh every few seconds with
  a sidebar interval slider.
- **`load_master_csv()`** — file-safe pandas reader. Tolerant of
  partial last rows from a writer mid-append (`pd.read_csv(...,
  on_bad_lines='skip')`) so it's safe to call while the tuner is still
  writing. Partial rows surface with identity columns populated and
  `NaN` in the missing fields.
- **Auto-discovery** via kt-masterlog's run registry — reads JSON
  manifests at `~/.kt-masterlog/runs/` (or `$KT_MASTERLOG_REGISTRY_DIR`)
  using the v1 schema. Stale entries (`status="running"` but writer PID
  is dead) are reported as `crashed`.
- **CLI** with three discovery modes:
  - `kt-masterviz path/to/log.csv` — explicit path
  - `kt-masterviz --latest` — most recent registered run
  - `kt-masterviz` (no args) — Streamlit picker over registered runs
  - `kt-masterviz --list` — print runs and exit (for scripting)
- **Helper functions** `detect_hyperparameter_columns()` and
  `detect_metric_columns()` for building custom viewers. Heuristic
  metric detection by name substring (`loss`, `accuracy`, `auc`, `mae`,
  etc.).
- **`Run` dataclass** + `list_runs()` / `latest_run()` for programmatic
  registry access.
- **Playwright smoke test** that loads the dashboard in headless
  Chromium and asserts the rendered DOM contains no Python tracebacks —
  catches deprecated Streamlit API breakages at render time.

### Independence from kt-masterlog

- kt-masterviz does **not** import kt-masterlog at runtime. The two
  packages share only the on-disk CSV schema and the registry manifest
  format. Install kt-masterviz alone if you have CSV files from another
  source that follow the same column convention.

[Unreleased]: https://github.com/techspeque/kt-masterviz/compare/HEAD...HEAD
